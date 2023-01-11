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
MASK_REGION_LEFT = [[676.0, 480.0], [680.0, 88.0], [752.0, 14.0], [1006.0, 16.0], [1102.0, 128.0], [1108.0, 372.0], [950.0, 408.0], [946.0, 482.0]] # "Noodle's side"
MASK_REGION_RIGHT = [[630.0, 478.0], [314.0, 470.0], [312.0, 382.0], [84.0, 370.0], [68.0, 52.0], [630.0, 26.0]]                                    # "Cami's side"


########################
# Main class
########################
class kibbie:
    # camera: string filepath or int representing video capture device index
    # config: config information, including (per cat):
    #   - Mask polygon (list of [x, y] points describing polygon on UNSCALED image)
    #   - Dispenses per day (float)
    def __init__(self, camera, config) -> None:
        self.camera = camera

        # Store per-cat masks here (mask polygon AND color in range)
        # Resulting white pixels mean that the color matched the cat and in the region of interest
        self.masks = []

        # Preprocess the configuration
        for i,cat in enumerate(config["cats"]):
            # Pre-scale config values
            config["cats"][i]["mask"] = [[int(x[0] * scale), int(x[1] * scale)] for x in cat["mask"]]
            config["cats"][i]["minPixelThreshold"] = cat["minPixelThreshold"] * scale

            # Initialize mask for each cat
            self.masks.append(None)

            # Find farthest left coordinate for debug print
            farthestLeftCoordinate = [99999999999, 0] # Something very far left
            for point in cat["mask"]:
                if point[0] < farthestLeftCoordinate[0]:
                    farthestLeftCoordinate = point
            assert farthestLeftCoordinate != [99999999999, 0], "Could not find farthest left coordinate of mask for debug print"
            config["cats"][i]["farthestLeftCoordinate"] = farthestLeftCoordinate
        
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

        # Initialize servo controller
        self.servo = servo.kibbie_servo_utils()
        self.servo.init_servos()
        self.servo.print_help()
    

    # Compute the masks for each cat, where:
    # - Pixel location is within the mask polygon
    # - Pixel color is withtin the HSV filtter for the cat
    def update_cat_masks(self):
        # Generate per-cat masks (intersection of polygon and color filter)
        for i,cat in enumerate(self.config["cats"]):
            # First filter by polygon
            mask_shape = np.zeros(self.img.shape[0:2], dtype=np.uint8)
            cv2.drawContours(image=mask_shape, contours=[np.array([cat["mask"]])], contourIdx=-1, color=(255, 255, 255), thickness=-1, lineType=cv2.LINE_AA)

            # Then filter by cat color
            mask_color = cv2.inRange(self.hsv_img, np.array(cat["lowerHSVThreshold"]), np.array(cat["upperHSVThreshold"]))

            # Combine masks
            self.masks[i] = cv2.bitwise_and(mask_shape, mask_color)

            # Show mask for debug
            debug_mask = self.masks[i].copy()
            num_nonzero_px = cv2.countNonZero(debug_mask)
            debug_mask = cv2.putText(img=debug_mask, text=f'# pixels: {num_nonzero_px}',
                org=(5, self.height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5,
                color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
            debug_mask = cv2.putText(img=debug_mask, text=f'Detected: {num_nonzero_px > cat["minPixelThreshold"]}',
                org=(int(self.width_px / 2), self.height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5,
                color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
            win_name = f'mask-{cat["name"]}'
            cv2.imshow(win_name, debug_mask)
            cv2.moveWindow(win_name, self.width_px, i * (self.height_px + 25))


    # Presents image and overlays any masks
    def refresh_image(self):
        if self.img is None:
            return
        
        # Draw image
        curr_frame = self.img.copy()

        for config in self.config["cats"]:
            # Draw polygon masks
            # Polygon corner points coordinates
            pts = np.array(config["mask"], np.int32)
            pts = pts.reshape((-1, 1, 2))
        
            curr_frame = cv2.polylines(img=curr_frame, pts=[pts], 
                                isClosed=True, color=(255, 255, 255), thickness=2)
            
            # For debug print the cat's name over their polygon at the farthest left coordinate
            curr_frame = cv2.putText(img=curr_frame, text=config["name"], org=[config["farthestLeftCoordinate"][0], config["farthestLeftCoordinate"][1] + 20], fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
        
        # Calculate FPS
        curr_time_s = time.time()
        fps = 1 / (curr_time_s - self.last_time_s)
        self.last_time_s = curr_time_s
        curr_frame = cv2.putText(img=curr_frame, text=f"FPS: {fps:.2f}", org=(5, self.height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)

        cv2.imshow("img", self.img)
        cv2.imshow("quantized", curr_frame)

        cv2.moveWindow("img",       0, 0 * (self.height_px + 25))
        cv2.moveWindow("quantized", 0, 1 * (self.height_px + 25))


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

            # Display debug image
            self.refresh_image()
            
            # Hit 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # After the loop release the cap object
        vid.release()
        # Destroy all the windows
        cv2.destroyAllWindows()


########################
# Main
########################
if __name__=="__main__":
    kb = kibbie(camera="software/images/white_background_low_light_both_cats.mp4", config={
        "enableWhiteBalance": True,
        "cats":[
            {
                "name": "Noodle",
                # Use the "unscaled" coordinates from `camera_calibration.py`
                "mask": MASK_REGION_LEFT,
                # Number of pixels required for a cat to be "present", unscaled
                "minPixelThreshold": 2000 / 0.25, # (calibrated at 0.25 scale)
                # Test color filter HSV thresholds using blue_filter.py first
                "lowerHSVThreshold": [0, 0, 0],
                "upperHSVThreshold": [255, 255, 40],
                "dispensesPerDay": 3,
            },
            {
                "name": "Cami",
                # Use the "unscaled" coordinates from `camera_calibration.py`
                "mask": MASK_REGION_RIGHT,
                # Number of pixels required for a cat to be "present"
                "minPixelThreshold": 2000 / 0.25, # (calibrated at 0.25 scale)
                # Test color filter HSV thresholds using blue_filter.py first
                "lowerHSVThreshold": [10, 130, 80],
                "upperHSVThreshold": [20, 255, 220],
                "dispensesPerDay": 3,
            },
        ],
    })
    kb.main()
