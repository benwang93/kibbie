import numpy as np
import cv2
import time

import lib.color_quantization as cq
import lib.img_tools as img_tools
import lib.kibbie_servo_utils as servo

########################
# Constants
########################

# Scale factor applied to the image dimensions to speed up processing
# and get the image to fit on the screen
#
# The results from this script will be scaled back up by this same scale
# so that kibbie.py can scale it back down according to its own scale.
# scale = 0.5 # For quality
scale = 0.25
# scale = 0.1 # For speed


# Masks for left and right areas
# Use the "unscaled" coordinates from `camera_calibration.py`
# White background video:
# MASK_REGION_LEFT = [[676.0, 480.0], [680.0, 88.0], [752.0, 14.0], [1006.0, 16.0], [1102.0, 128.0], [1108.0, 372.0], [950.0, 408.0], [946.0, 482.0]] # "Noodle's side"
# MASK_REGION_RIGHT = [[630.0, 478.0], [314.0, 470.0], [312.0, 382.0], [84.0, 370.0], [68.0, 52.0], [630.0, 26.0]]                                    # "Cami's side"
# Gray background video on actual kibbie HW:
MASK_REGION_RIGHT = [[316.0, 378.0], [326.0, 26.0], [18.0, 30.0], [22.0, 286.0], [122.0, 286.0], [140.0, 364.0]]
MASK_REGION_LEFT = [[356.0, 376.0], [350.0, 20.0], [626.0, 22.0], [630.0, 296.0], [550.0, 302.0], [534.0, 372.0]]


########################
# Main class
########################
class kibbie:
    # camera: string filepath or int representing video capture device index
    # config: config information, including (per cat):
    #   - Mask polygon (list of [x, y] points describing polygon on UNSCALED image)
    #   - Dispenses per day (float)
    def __init__(self, camera, log_filename, config) -> None:
        # Open log file (append mode)
        self.logfile = open(log_filename, 'a')
        self.log("=====================================")
        self.log("Initializing kibbie...")

        self.camera = camera

        # Store per-cat masks here (mask polygon AND color in range)
        # Resulting white pixels mean that the color matched the cat and in the region of interest
        self.masks = []

        # Track a filtered number of pixels per corral per cat to make door less sensitive
        # Target something like 2s time constant?
        self.filtered_pixels = []
        self.filter_ratio = 0.95 # (every cycle, this fraction of new value will come from previous value)

        # Track door open/close state per corral
        self.corral_door_open = [False for _ in config["corrals"]]

        # Preprocess the configuration
        for i,corral in enumerate(config["corrals"]):
            # Pre-scale config values
            print(f'[{corral["name"]}] Before scaling mask: {corral["mask"]}')
            config["corrals"][i]["mask"] = [[int(x[0] * scale), int(x[1] * scale)] for x in corral["mask"]]
            print(f'[{corral["name"]}] After scaling mask: {corral["mask"]}')
            config["corrals"][i]["minPixelThreshold"] = corral["minPixelThreshold"] * scale

            # Initialize mask for each corral
            cat_masks = []
            for _ in config["cats"]:
                cat_masks.append(None)
            self.masks.append(cat_masks)

            # Initialize weighted average number of pixels per cat
            self.filtered_pixels.append([0]*len(config["cats"]))

            # Find farthest left coordinate for debug print
            farthestLeftCoordinate = [99999999999, 0] # Something very far left
            for point in corral["mask"]:
                if point[0] < farthestLeftCoordinate[0]:
                    farthestLeftCoordinate = point
            assert farthestLeftCoordinate != [99999999999, 0], "Could not find farthest left coordinate of mask for debug print"
            config["corrals"][i]["farthestLeftCoordinate"] = farthestLeftCoordinate
        
        self.config = config

        # Placeholder for current scaled frame from camera
        self.img = None
        self.hsv_img = None

        # Placeholder for current scaled and quantized frame
        self.quantized = None

        # Timestamp of last frame - used to calculate FPS to display on debug image
        self.last_time_s = None

        # Cache dimensions of scaled image
        self.height_px = 0
        self.width_px = 0

        # Variables for tracking state of cats in camera
        self.mask_has_allowed_cat = [False]*servo.NUM_CHANNELS_USED
        self.mask_has_disallowed_cat = [False]*servo.NUM_CHANNELS_USED

        # Initialize servo controller
        self.servo = servo.kibbie_servo_utils()
        self.servo.init_servos()
        self.print_help()
    

    def __del__(self):
        self.log("Kibbie shutting down")
        self.logfile.close()
    

    # Utility to write to the log file and print to console
    def log(self, s):
        output = f"[{time.time():.3f}] {s}"
        self.logfile.write(f"{output}\n")
        self.logfile.flush()
        print(output)
    

    # Compute the masks for each corral, where:
    # - Pixel location is within the mask polygon
    # - Pixel color is withtin the HSV filtter for the cat
    def update_cat_masks(self):
        # Generate per-cat masks (intersection of polygon and color filter)
        # For each corral, check for each cat
        for corral_idx,corral in enumerate(self.config["corrals"]):# First filter by polygon
            # Save previous state for transition detection
            prev_allowed = self.mask_has_allowed_cat[corral_idx]
            prev_disallowed = self.mask_has_disallowed_cat[corral_idx]

            # Start with no cats detected
            self.mask_has_allowed_cat[corral_idx] = False
            self.mask_has_disallowed_cat[corral_idx] = False

            for cat_idx,cat in enumerate(self.config["cats"]):
                mask_shape = np.zeros(self.img.shape[0:2], dtype=np.uint8)
                cv2.drawContours(image=mask_shape, contours=[np.array([corral["mask"]])], contourIdx=-1, color=(255, 255, 255), thickness=-1, lineType=cv2.LINE_AA)
                
                # TODO: Iterate over all cats in each region to check for all cats (some operations require 0 or 1 cats)
                # Then filter by cat color
                mask_color = cv2.inRange(self.hsv_img, np.array(cat["lowerHSVThreshold"]), np.array(cat["upperHSVThreshold"]))

                # Combine masks
                self.masks[corral_idx][cat_idx] = cv2.bitwise_and(mask_shape, mask_color)

                # Check for cat
                num_nonzero_px = cv2.countNonZero(self.masks[corral_idx][cat_idx])

                # Perform filter
                num_nonzero_px_filt = (
                    self.filter_ratio * self.filtered_pixels[corral_idx][cat_idx] +
                    (1 - self.filter_ratio) * num_nonzero_px
                )
                self.filtered_pixels[corral_idx][cat_idx] = num_nonzero_px_filt

                # Cat detection logic
                cat_detected = (num_nonzero_px_filt > corral["minPixelThreshold"])
                if cat["name"] in corral["allowedCats"]:
                    cat_is_allowed = True
                    if prev_allowed != cat_detected:
                        self.log(f'Detected allowed cat {cat["name"]} {"entered" if cat_detected else "left"} {corral["name"]} corral')
                    self.mask_has_allowed_cat[corral_idx] |= cat_detected
                else:
                    cat_is_allowed = False
                    if prev_disallowed != cat_detected:
                        self.log(f'Detected disallowed cat {cat["name"]} {"entered" if cat_detected else "left"} {corral["name"]} corral')
                    self.mask_has_disallowed_cat[corral_idx] |= cat_detected

                # Show mask for debug
                debug_mask = self.masks[corral_idx][cat_idx].copy()

                # Make a green (allowed) or red (disallowed) image to display if cat detected
                if cat_detected:
                    if cat_is_allowed:
                        color = (0, 255, 0) # Green
                    else:
                        color = (0, 0, 255) # Red
                    debug_mask_bg = np.zeros(self.img.shape)
                    debug_mask_bg = cv2.rectangle(img=debug_mask_bg, pt1=(0, 0), pt2=(debug_mask_bg.shape[1], debug_mask_bg.shape[0]), color=color, thickness=-1)
                    debug_mask = cv2.bitwise_and(debug_mask_bg, debug_mask_bg, mask=debug_mask)

                debug_mask = cv2.putText(img=debug_mask, text=f'# pixels: {num_nonzero_px}',
                    org=(5, self.height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=scale,#0.5,
                    color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
                debug_mask = cv2.putText(img=debug_mask, text=f'# pixels filt: {self.filtered_pixels[corral_idx][cat_idx]:.1f} / {corral["minPixelThreshold"]:.0f}',
                    org=(5, int(self.height_px - scale * 25 - 5)), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=scale,#0.5,
                    color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
                debug_mask = cv2.putText(img=debug_mask, text=f'Detected: {self.mask_has_allowed_cat[corral_idx]}',
                    org=(int(self.width_px / 2), self.height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=scale,#0.5,
                    color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
                win_name = f'mask-{corral["name"]}-{cat["name"]}'
                cv2.imshow(win_name, debug_mask)
                cv2.moveWindow(win_name, (corral_idx + 1) * (self.width_px + 50), cat_idx * (self.height_px + 25))


    # Check if there are any servo actions to perform
    # Includes door open/close and scheduled dispenser checks
    def check_and_operate_servos(self):
        # Check each region and perform door and dispenser actions
        for i,corral in enumerate(self.config["corrals"]):
            # Check for corral
            if self.mask_has_allowed_cat[i] and not self.mask_has_disallowed_cat[i]:
                self.corral_door_open[i] = True
                if self.servo.queue_angle(corral["doorServoChannel"], corral["doorServoAngleOpen"]):
                    self.log(f'Opening {corral["name"]} door')
            else:
                self.corral_door_open[i] = False
                if self.servo.queue_angle(corral["doorServoChannel"], corral["doorServoAngleClosed"]):
                    self.log(f'Closing {corral["name"]} door')


    # Presents image and overlays any masks
    def refresh_image(self):
        if self.img is None:
            return
        
        # Draw image
        curr_frame = self.img.copy()

        for i,config in enumerate(self.config["corrals"]):
            # Draw polygon masks
            # Polygon corner points coordinates
            pts = np.array(config["mask"], np.int32)
            pts = pts.reshape((-1, 1, 2))
            
            # Set polygon color based on door open/close state
            if self.corral_door_open[i]:
                color = (0, 255, 0) # Green
            else:
                color = (0, 0, 255) # Red
        
            curr_frame = cv2.polylines(img=curr_frame, pts=[pts], 
                                isClosed=True, color=color, thickness=2)
            
            # For debug print the cat's name over their polygon at the farthest left coordinate
            curr_frame = cv2.putText(img=curr_frame, text=config["allowedCats"][0], org=[config["farthestLeftCoordinate"][0], config["farthestLeftCoordinate"][1] + 20], fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=color, thickness=1, lineType=cv2.LINE_AA)
        
        # Calculate FPS
        curr_time_s = time.time()
        if (curr_time_s - self.last_time_s) > 0:
            fps = 1 / (curr_time_s - self.last_time_s)
        else:
            fps = 0.0
        self.last_time_s = curr_time_s
        curr_frame = cv2.putText(img=curr_frame, text=f"FPS: {fps:.2f}", org=(5, self.height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)

        cv2.imshow("img", self.img)
        cv2.imshow("quantized", curr_frame)

        cv2.moveWindow("img",       0, 0 * (self.height_px + 25))
        cv2.moveWindow("quantized", 0, 1 * (self.height_px + 25))
    

    # Dispenser state machine:
    #
    #   init  ┌──────┐                      ┌───────────────┐
    #  ──────►│      │  on scheduled time   │               │
    #         │ Idle ├─────────────────────►│ Searching     │
    #    ┌───►│      │                      │               │
    #    │    └──────┘                      │ Wait for      │
    #    │                                  │ opportunity   │
    #    │                                  │               │
    #    │                                  └─────────┬─────┘
    #    │                                       ▲    │
    #    │                               on cat  │    │on no cats
    #    │                               detected│    │detected
    #    │                                       │    │
    #    │                                       │    ▼
    #    │  ┌──────────────────┐            ┌────┴──────────┐
    #    │  │                  │ on no cats │               │
    #    │  │ Dispensing       │ detected   │ Opening       │
    #    └──┤                  │◄───────────┤               │
    #       │ Command dispense │            │ Command door  │
    #       │ and close door   │            │ open          │
    #       │                  │            │               │
    #       └──────────────────┘            └───────────────┘
    def dispenser_state_machine(self):
        return
    

    # Helper function to get and handle keyboard input
    # Returns False if we need to quit
    def handle_keyboard_input(self):
        key = cv2.waitKey(1)
        if key == ord('h'):
            self.print_help()
        elif key == ord('p'):
            print("PAUSED. Press any key to continue...")
            cv2.waitKey(0)
        elif key == ord('s'):
            self.servo.print_status()
        elif key == ord('q'):
            # Return False to quit
            return False

        return True
    

    def print_help(self):
        print(
            "\n" +
            "==============\n" +
            "Kibbie\n" +
            "==============\n" +
            "\n" 
            "Commands:\n" 
            "\n" +
            # "  d    dispense\n" +
            "  h    print this help\n" +
            # "  c    close door\n" +
            # "  o    open door\n" +
            # "  n    go to neutral\n" +
            # "  1    go to dispense 1 position\n" +
            # "  2    go to dispense 2 position\n" +
            "  p    pause the video (to review debug HUD)\n"
            "  s    print status (angle and food dispensed)\n" +
            "  q    quit\n"
        )
    

    def main(self):
        # define a video capture object
        vid = cv2.VideoCapture(self.camera)
        
        # Track FPS
        self.last_time_s = time.time()
        
        while(True):
            # Capture the video frame by frame
            ret, frame = vid.read()

            # Exit once video finishes
            if not ret:
                break

            # Downsample for faster processing
            self.img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

            self.height_px = self.img.shape[0]
            self.width_px = self.img.shape[1]

            # Perform white balance
            if self.config["enableWhiteBalance"]:
                self.img = img_tools.white_balance(self.img)
            
            self.hsv_img = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)

            # Generate per-cat masks (intersection of polygon and color filter)
            self.update_cat_masks()

            # Check if there are any servo actions to perform
            # Includes door open/close and scheduled dispenser checks
            self.check_and_operate_servos()

            # Display debug image
            self.refresh_image()

            # TODO: Dispense food state machine
            self.dispenser_state_machine()

            # Run servos
            self.servo.run_loop()
            
            # Handle key input
            if not self.handle_keyboard_input():
                break
        
        # After the loop release the cap object
        vid.release()
        # Destroy all the windows
        cv2.destroyAllWindows()


########################
# Main
########################
if __name__=="__main__":
    kb = kibbie(
        # camera="software/images/white_background_low_light_both_cats.mp4",    # Playback for dev (white background)
        camera="software/images/20230114-kibbie_feeder.avi",                  # Playback for dev (real floor)
        # camera=0,                                                               # Real camera
        log_filename="kibbie.log",
        config={
            "enableWhiteBalance": True,
            "cats":[
                {
                    "name": "Noodle",
                    # Test color filter HSV thresholds using blue_filter.py first
                    "lowerHSVThreshold": [0, 60, 0],
                    "upperHSVThreshold": [255, 255, 50],
                },
                {
                    "name": "Cami",
                    # Test color filter HSV thresholds using blue_filter.py first
                    "lowerHSVThreshold": [0, 60, 120],
                    "upperHSVThreshold": [10, 110, 240],
                },
            ],
            "corrals": [
                {
                    "name": "NOODLE_L",
                    "allowedCats": ["Noodle"],
                    # Use the "unscaled" coordinates from `camera_calibration.py`
                    "mask": MASK_REGION_LEFT,
                    # Number of pixels required for a cat to be "present", unscaled
                    "minPixelThreshold": 1000 / 0.25, # (calibrated at 0.25 scale)
                    "dispensesPerDay": 3,
                    # Servo configuration
                    "dispenserServoChannel": servo.CHANNEL_DISPENSER_LEFT,
                    "doorServoChannel": servo.CHANNEL_DOOR_LEFT,
                    "doorServoAngleOpen": servo.ANGLE_DOOR_LEFT_OPEN,
                    "doorServoAngleClosed": servo.ANGLE_DOOR_LEFT_CLOSED,
                },
                {
                    "name": "CAMI_R",
                    "allowedCats": ["Cami"],
                    "dispensesPerDay": 3,
                    # Use the "unscaled" coordinates from `camera_calibration.py`
                    "mask": MASK_REGION_RIGHT,
                    # Number of pixels required for a cat to be "present"
                    "minPixelThreshold": 1000 / 0.25, # (calibrated at 0.25 scale)
                    # Servo configuration
                    "dispenserServoChannel": servo.CHANNEL_DISPENSER_RIGHT,
                    "doorServoChannel": servo.CHANNEL_DOOR_RIGHT,
                    "doorServoAngleOpen": servo.ANGLE_DOOR_RIGHT_OPEN,
                    "doorServoAngleClosed": servo.ANGLE_DOOR_RIGHT_CLOSED,
                }
            ],
        }
    )
    kb.main()
