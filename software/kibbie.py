import os
import time
from multiprocessing import Process, Queue

import cv2
import matplotlib.pyplot as plt
import numpy as np

import lib.ImgTools as ImgTools
import lib.KibbieServoUtils as Servo
from lib.Dispenser import Dispenser
from lib.KibbieSerial import KibbieSerial

from lib.Parameters import *

# Imports for web server
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
import threading
import argparse

########################
# Constants
########################

# Scale factor applied to the image dimensions to speed up processing
# and get the image to fit on the screen
#
# The results from this script will be scaled back up by this same scale
# so that kibbie.py can scale it back down according to its own scale.
# scale = 0.5 # For quality
# scale = 0.25
scale = 0.1 # For speed

# In addition to processing `scale` used above, scale up the display to this size:
display_scale = 0.25

# Amount of ms to wait after each frame before the next one
# Use this to intentionally slow down frame rate, or use 1 ms for fastest performance
FRAME_PERIOD_MS = 1
# FRAME_PERIOD_MS = 100

# Masks for left and right areas
# Use the "unscaled" coordinates from `camera_calibration.py`
# White background video:
# MASK_REGION_LEFT = [[676.0, 480.0], [680.0, 88.0], [752.0, 14.0], [1006.0, 16.0], [1102.0, 128.0], [1108.0, 372.0], [950.0, 408.0], [946.0, 482.0]] # "Noodle's side"
# MASK_REGION_RIGHT = [[630.0, 478.0], [314.0, 470.0], [312.0, 382.0], [84.0, 370.0], [68.0, 52.0], [630.0, 26.0]]                                    # "Cami's side"
# Gray background video on actual kibbie HW:
MASK_REGION_RIGHT = [[316.0, 378.0], [326.0, 26.0], [18.0, 30.0], [22.0, 286.0], [122.0, 286.0], [140.0, 364.0]]
MASK_REGION_LEFT = [[356.0, 376.0], [350.0, 20.0], [626.0, 22.0], [630.0, 296.0], [550.0, 302.0], [534.0, 372.0]]


# How often the servo process executes
SERVO_PROCESS_PERIOD_S = 0.05 # s, 20 Hz


########################
# Globals
########################

# Set up shared queues
servo_command_queue = Queue()   # Kibbie -> Servo queue for commands
servo_log_queue = Queue()       # Servo -> Kibbie queue for logs to write to disk
web_output_queue = Queue()      # Kibbie -> Web server queue for images


########################
# Main class
########################
class kibbie:
    # camera: string filepath or int representing video capture device index
    # config: config information, including (per cat):
    #   - Mask polygon (list of [x, y] points describing polygon on UNSCALED image)
    #   - Dispenses per day (float)
    def __init__(self, camera, log_filename, config, servo_command_queue, servo_log_queue, web_output_queue) -> None:
        # Open log file (append mode)
        self.logfile = open(log_filename, 'a')
        self.log("=====================================")
        self.log("Initializing kibbie...")

        # Save path to file or index of camera (used to open video capture object)
        self.camera = camera

        # Video capture object
        self.vid = None

        # Store per-cat masks here (mask polygon AND color in range)
        # Resulting white pixels mean that the color matched the cat and in the region of interest
        self.masks = []

        # Track a filtered number of pixels per corral per cat to make door less sensitive
        # Target something like 2s time constant?
        self.filtered_pixels = []
        self.filter_ratio = 0.90 # (every cycle, this fraction of new value will come from previous value)
                                    # Use 0.95 for ~20 FPS
                                    # Use 0.90 for 10 FPS

        # Track door open/close state per corral
        self.corral_door_open = [False for _ in config["corrals"]]

        # Track dispenser state per corral
        self.corral_dispensing = [False for _ in config["corrals"]]

        # Track per-corral dispenser state machines
        self.corral_dispensers = []

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

            # Initialize dispenser object for each corral
            dispenser = Dispenser(dispenses_per_day=corral["dispensesPerDay"], dispenser_name=corral["name"], logfile=self.logfile)
            self.corral_dispensers.append(dispenser)
        
        self.config = config

        # Placeholder for current scaled frame from camera
        self.images = {}
        self.img = None
        self.hsv_img = None

        # Placeholder for current scaled and quantized frame
        self.quantized = None

        # Timestamp of last frame - used to calculate FPS to display on debug image
        self.last_time_s = None

        # Variables to support periodic frame exports while door is open
        self.export_frame_on_timer = False          # Set to True while door is open to export
        self.next_export_frame_on_timer_time = 0    # Set to next time to export (time.time()) while self.export_frame_on_timer is True

        # Cache dimensions of scaled image
        self.height_px = 0
        self.width_px = 0

        # Variables for tracking state of cats in camera
        self.mask_has_allowed_cat = [False]*Servo.NUM_CHANNELS_USED
        self.mask_has_disallowed_cat = [False]*Servo.NUM_CHANNELS_USED

        # Initialize serial controller (and efuse controller)
        if IS_ARDUINO_MONITOR_ATTACHED:
            self.kbSerial = KibbieSerial()
        else:
            self.kbSerial = None

        # Wait a bit before initializing servos so efuse controller can stabilize
        time.sleep(0.5)

        # Variables for plotting current from serial
        self.current_history = []
        self.fig, self.ax = plt.subplots()

        # Initialize servo controller on a separate process (not hung up by main thread processing)
        # self.servo_command_queue = Queue()      # Kibbie -> Servo queue for commands
        # self.servo_log_queue = Queue()  # Servo -> Kibbie queue for logs to write to disk
        # self.servo_process_handle = Process(target=self.servo_process, args=(self.servo_command_queue, self.servo_log_queue,))
        # self.servo_process_handle.start()
        self.servo_command_queue = servo_command_queue      # Kibbie -> Servo queue for commands
        self.servo_log_queue     = servo_log_queue          # Servo -> Kibbie queue for logs to write to disk
        self.web_output_queue     = web_output_queue          # Kibbie -> web server queue for images

        self.print_help()
    

    def __del__(self):
        self.log("Kibbie shutting down...")
        self.logfile.close()

    #############################################################
    # Servo process methods
    #############################################################
    
    # Helper function to queue servo actions
    def queue_servo_angle_stepped(self, channel, target_angle, latch_channel, latch_angle_unlocked, latch_angle_locked, offset_seconds=0):
        self.servo_command_queue.put(["queue_angle_stepped", channel, target_angle, latch_channel, latch_angle_unlocked, latch_angle_locked, offset_seconds])
    
    def queue_servo_dispense_food(self, channel):
        self.servo_command_queue.put(["dispense_food", channel])
    
    def queue_servo_print_status(self):
        self.servo_command_queue.put(["print_status"])
    
    def queue_servo_exit(self):
        self.servo_command_queue.put(["exit"])
    
    # Periodic function to log servo output to log file
    def process_servo_log_queue(self):
        while not self.servo_log_queue.empty():
            output = self.servo_log_queue.get()
            self.logfile.write(f"{output}\n")
            self.logfile.flush()


    #############################################################
    # Main process methods
    #############################################################

    # Utility to write to the log file and print to console
    def log(self, s):
        output = f"[{time.asctime()}] {s}"
        self.logfile.write(f"{output}\n")
        self.logfile.flush()
        print(output)
    
    # Helper function to scale up images from processing scale to display scale
    def scale_for_display(self, image):
        return cv2.resize(image, (0, 0), fx=display_scale / scale, fy=display_scale / scale)

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

                # Scale up image for showing
                debug_mask = self.scale_for_display(debug_mask)

                debug_mask = cv2.putText(img=debug_mask, text=f'# pixels: {num_nonzero_px}',
                    org=(5, self.display_height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=display_scale,
                    color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
                debug_mask = cv2.putText(img=debug_mask, text=f'# pixels filt: {self.filtered_pixels[corral_idx][cat_idx]:.1f} / {corral["minPixelThreshold"]:.0f}',
                    org=(5, int(self.display_height_px - display_scale * 25 - 5)), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=display_scale,
                    color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
                debug_mask = cv2.putText(img=debug_mask, text=f'Detected: {self.mask_has_allowed_cat[corral_idx]}',
                    org=(int(self.display_width_px / 2), self.display_height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=display_scale,
                    color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)
                win_name = f'mask-{corral["name"]}-{cat["name"]}'
                cv2.imshow(win_name, debug_mask)
                cv2.moveWindow(win_name, (corral_idx + 1) * (self.display_width_px + 50), cat_idx * (self.display_height_px + 25))
                
                # Save images for debug
                self.images[win_name] = debug_mask

    # Check if there are any servo actions to perform
    # Includes door open/close and scheduled dispenser checks
    def check_and_operate_servos(self):
        # Check each region and perform door and dispenser actions
        for i,corral in enumerate(self.config["corrals"]):
            # Check for corral door-open conditions or actively dispensing
            if (self.mask_has_allowed_cat[i] and not self.mask_has_disallowed_cat[i]) or self.corral_dispensers[i].open_door_request:
                if not self.corral_door_open[i]:
                    # Detected a change - log and perform operations
                    self.log(f'Opening {corral["name"]} door')
                    self.queue_servo_angle_stepped(corral["doorServoChannel"], corral["doorServoAngleOpen"], corral["doorLatchServoChannel"], corral["doorLatchServoAngleUnlocked"], corral["doorLatchServoAngleLocked"])
                    
                    self.export_current_frame(postfix=f'opening-{corral["name"]}', annotated_only=True)
                    if self.config["saveSnapshotWhileDoorOpenPeriodSeconds"] > 0:
                        self.export_frame_on_timer = True
                        self.next_export_frame_on_timer_time = (time.time() + self.config["saveSnapshotWhileDoorOpenPeriodSeconds"])
                    
                    self.corral_door_open[i] = True

            else:
                if self.corral_door_open[i]:
                    # Detected a change - log and perform operations
                    self.log(f'Closing {corral["name"]} door')
                    self.queue_servo_angle_stepped(corral["doorServoChannel"], corral["doorServoAngleClosed"], corral["doorLatchServoChannel"], corral["doorLatchServoAngleUnlocked"], corral["doorLatchServoAngleLocked"])

                    self.export_frame_on_timer = False
                    self.export_current_frame(f'closing-{corral["name"]}', annotated_only=True)

                    self.corral_door_open[i] = False
            
            # Check for dispenser commands
            if self.corral_dispensers[i].dispense_request:
                if not self.corral_dispensing[i]:
                    self.corral_dispensing[i] = True

                    self.log(f'Dispensing food in corral {corral["name"]}')

                    # Request dispense once
                    self.dispense_food(corral["dispenserServoChannel"])
            else:
                # Reset flag
                self.corral_dispensing[i] = False
                    

    # Used as part of shut-down sequence
    def close_doors(self):
        for i,corral in enumerate(self.config["corrals"]):
            self.queue_servo_angle_stepped(corral["doorServoChannel"], corral["doorServoAngleClosed"], corral["doorLatchServoChannel"], corral["doorLatchServoAngleUnlocked"], corral["doorLatchServoAngleLocked"])
            self.log(f'Closing {corral["name"]} door')
        
        # self.servo.block_until_servos_done()
        # FIXME: Wait hard-coded time for doors to close until we can get feedback from servo process that doors are all closed
        time.sleep(5.0)
        self.log(f'Doors closed')


    # Used as part of manual servicing sequence
    def open_doors(self):
        for i,corral in enumerate(self.config["corrals"]):
            self.queue_servo_angle_stepped(corral["doorServoChannel"], corral["doorServoAngleOpen"], corral["doorLatchServoChannel"], corral["doorLatchServoAngleUnlocked"], corral["doorLatchServoAngleLocked"])
            self.log(f'Opening {corral["name"]} door')
        
        # We used to block until servos were done moving, but don't have a solution right now after moving servo to its own process
        # self.servo.block_until_servos_done()
        # self.log(f'Doors opened')


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
            curr_frame = cv2.putText(img=curr_frame, text=config["allowedCats"][0], org=[config["farthestLeftCoordinate"][0], config["farthestLeftCoordinate"][1] + 20], fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=scale, color=color, thickness=1, lineType=cv2.LINE_AA)
        
        # Scale up image for showing
        curr_frame = self.scale_for_display(curr_frame)

        # Calculate FPS
        curr_time_s = time.time()
        if (curr_time_s - self.last_time_s) > 0:
            fps = 1 / (curr_time_s - self.last_time_s)
        else:
            fps = 0.0
        self.last_time_s = curr_time_s
        curr_frame = cv2.putText(img=curr_frame, text=f"FPS: {fps:.2f}", org=(5, self.display_height_px - 5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=display_scale, color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)

        cv2.imshow("raw", self.scale_for_display(self.img))
        cv2.imshow("corrals", curr_frame)

        cv2.moveWindow("raw", 0, 0 * (self.display_height_px + 25))
        cv2.moveWindow("corrals", 0, 1 * (self.display_height_px + 25))

        # Save images for export if needed
        self.images["corrals"] = curr_frame
    

    # Helper function to run the dispenser state machine for each dispenser
    def dispenser_state_machine(self):
        # First see if any cats are in any corrals (don't want to open door if there's a cat nearby)
        any_mask_has_allowed_cat = False
        any_mask_has_disallowed_cat = False
        for i in range(len(self.corral_dispensers)):
            any_mask_has_allowed_cat |= self.mask_has_allowed_cat[i]
            any_mask_has_disallowed_cat |= self.mask_has_disallowed_cat[i]

        # Then update each state machine
        for i,dispenser in enumerate(self.corral_dispensers):
            dispenser.step(any_mask_has_allowed_cat, any_mask_has_disallowed_cat)
    

    # Helper function to export current frame to the `software/images/` folder
    def export_current_frame(self, postfix="", annotated_only=False):
        current_time = time.localtime(time.time())
        filename = time.strftime("%Y-%m-%d_%H-%M-%S", current_time)
        date_string = time.strftime("%Y-%m-%d", current_time)
        
        if postfix != "":
            filename += "-" + postfix
        
        if annotated_only:
            # Single frame export (intended for auto-export)
            folder = f"snapshots/{date_string}"
            os.makedirs(folder, exist_ok=True)

            # Only export the annotated frame of corrals
            cv2.imwrite(f"{folder}/{filename}.png", self.images["corrals"])

            self.log(f'Exported current frame to "f{folder}/{filename}.png"')
        else:
            # Export all frames (intended for user request)
            folder = f"snapshots/{filename}/"
            os.makedirs(folder, exist_ok=True)

            for key in self.images:
                cv2.imwrite(f"{folder}/{key}.png", self.images[key])
            
            self.plot_current(f"{folder}/current.png")

            self.log(f'Exported current frame to "{folder}/*.png"')


    # Helper function to get and handle keyboard input
    # Returns False if we need to quit
    def handle_keyboard_input(self):
        key = cv2.waitKey(FRAME_PERIOD_MS)
        if key == ord('d'):
            print("Enter corral number to dispense:")
            for i,corral in enumerate(self.config["corrals"]):
                print(f'{i}: {corral["name"]}')
            key2 = cv2.waitKey(0)
            for i,corral in enumerate(self.config["corrals"]):
                if key2 == ord(f'{i}'):
                    self.log(f'Forcing dispense for corral {corral["name"]}')
                    self.corral_dispensers[i].schedule_dispense_now()
        elif key == ord('e'):
            self.export_current_frame()
        elif key == ord('h'):
            self.print_help()
        elif key == ord('i'):
            self.plot_current()
        elif key == ord('o'):
            self.log("Manually opening doors...")
            self.open_doors()
            print("Press any key to resume operation")
            cv2.waitKey(0)
            self.close_doors()
        elif key == ord('p'):
            print("PAUSED. Press any key to continue...")
            cv2.waitKey(0)
        elif key == ord('s'):
            self.queue_servo_print_status()
            time.sleep(2 * SERVO_PROCESS_PERIOD_S)  # Wait for servo process to complete request
            self.process_servo_log_queue()
            for dispenser in self.corral_dispensers:
                dispenser.print_status()
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
            "  d<idx>   dispense corral at idx (will print corral index-name mapping)\n" +
            "  e        export current frame for debugging\n" +
            "  h        print this help\n" +
            "  i        save plot of current\n" +
            "  o        open the door (manual servicing)\n" +
            "  p        pause the video (to review debug HUD)\n" +
            "  s        print status (angle and food dispensed)\n" +
            "  q        quit\n"
        )


    # Helper function to sample 
    def sample_input(self):
        # Capture the video frame by frame
        ret, frame = self.vid.read()

        # Exit once video finishes
        if not ret:
            return False

        # Downsample for faster processing
        self.images["raw"] = frame
        self.img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        # Save image dimensions for later use
        if self.height_px != self.img.shape[0]:
            self.height_px = self.img.shape[0]
            self.width_px = self.img.shape[1]
            self.display_height_px = int(self.height_px * display_scale / scale)
            self.display_width_px = int(self.width_px * display_scale / scale)

        # Perform white balance
        if self.config["enableWhiteBalance"]:
            self.img = ImgTools.white_balance(self.img)
        
        self.hsv_img = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)

        return True


    def sample_current(self):
        NUM_CURRENT_SAMPLES_TO_SAVE = 1000

        # Add current sample
        if self.kbSerial:
            for i,channel_sample in enumerate(self.kbSerial.channel_current):
                # Initialize sample if it's the first time receiving it
                if i == len(self.current_history):
                    self.current_history.append([channel_sample])
                else:
                    self.current_history[i].append(channel_sample)

                # Remove oldest sample if too long
                if len(self.current_history[i]) > NUM_CURRENT_SAMPLES_TO_SAVE:
                    self.current_history[i] = self.current_history[i][1:]
    

    # Plot current on-demand
    def plot_current(self, filepath="snapshots/current.png"):
        self.fig, self.ax = plt.subplots()
        if len(self.current_history) >= 2:
            # self.ax.plot(range(len(self.current_history[0])), 'g^', self.current_history[0], self.current_history[0]) #, 'g^', x2, y2, 'g-')
            self.ax.plot(range(len(self.current_history[0])), self.current_history[0]) #, 'g^', x2, y2, 'g-')
            self.ax.plot(range(len(self.current_history[1])), self.current_history[1])

        self.ax.set(xlabel='sample number', ylabel='Current (A)',
            title='Kibbie Door Current')
        self.ax.grid()
        self.ax.set_ylim(-0.1, 2.0)

        self.fig.savefig(filepath)
        self.log(f"Saved plot of current to {filepath}")

    def main(self):
        # Open video capture object
        self.vid = cv2.VideoCapture(self.camera)

        # Track FPS
        self.last_time_s = time.time()

        # Similar to FPS, but to run periodically
        previous_run_time_s = 0
        
        while(True):
            # Slow down to run periodically
            run_freq = 10 # Hz
            while (time.time() - previous_run_time_s) < (1 / run_freq):
                time.sleep(0.001)
            previous_run_time_s = time.time()

            # Read camera frame and preprocess
            if not self.sample_input():
                break

            # Generate per-cat masks (intersection of polygon and color filter)
            self.update_cat_masks()

            # Display debug image
            self.refresh_image()

            # Update serial
            if self.kbSerial:
                self.kbSerial.update()
                self.sample_current()

            # Dispense food state machine
            self.dispenser_state_machine()

            # Check if there are any servo actions to perform
            # Includes door open/close and scheduled dispenser checks
            self.check_and_operate_servos()

            # Export current frame while door open, if enabled
            if self.export_frame_on_timer and self.next_export_frame_on_timer_time <= time.time():
                # Get names of open corrals
                open_corrals_str = ""
                for i,corral_open in enumerate(self.corral_door_open):
                    if corral_open:
                        open_corrals_str += f'-{self.config["corrals"][i]["name"]}'

                self.export_current_frame(postfix=f"open{open_corrals_str}", annotated_only=True)
                self.next_export_frame_on_timer_time = time.time() + self.config["saveSnapshotWhileDoorOpenPeriodSeconds"]

            # Log any output from servos
            self.process_servo_log_queue()
            
            # Handle key input
            if not self.handle_keyboard_input():
                break
        
        self.log("Kibbie exited main loop. Starting shutdown procedure...")
        
        # After the loop release the cap object
        self.vid.release()

        # Destroy all the windows
        cv2.destroyAllWindows()
        
        # Leave doors in a closed state when shut down
        # This is acceptable in the case of a manual system shutdown (hitting 'q')
        # In the case of a program crash or Ctrl+C, doors will remain in their
        # previous state
        self.close_doors()

        # Wait for doors to close, then exit child processes
        self.queue_servo_exit()


########################
# Servo process
########################

# Main servo process function
def servo_process( command_queue, log_queue):
    print(f"*** servo_process: Starting...")

    servo = Servo.KibbieServoUtils(log_queue)
    servo.init_servos()

    while(1):
        # Fetch any commands
        while not command_queue.empty():
            command = command_queue.get()
            opcode = command[0]

            print(f"*** servo_process: Executing '{opcode}'")

            # Process command / check for exit
            if opcode == "exit":
                return
            if opcode == "queue_angle_stepped":
                channel = command[1]
                target_angle = command[2]
                latch_channel = command[3]
                latch_angle_unlocked = command[4]
                latch_angle_locked = command[5]
                offset_seconds = command[6]
                servo.queue_angle_stepped(channel, target_angle, latch_channel, latch_angle_unlocked, latch_angle_locked, offset_seconds)

            elif opcode == "dispense_food":
                channel = command[1]
                servo.dispense_food(channel)
            
            elif opcode == "print_status":
                servo.print_status()
        
        servo.run_loop()
        
        # Run servos at 20 Hz
        time.sleep(SERVO_PROCESS_PERIOD_S)


########################
# Web server process
########################

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
outputFrame = None
left_current = None
right_current = None
left_next_dispense_time = None
right_next_dispense_time = None
lock = threading.Lock()
# initialize a flask object
app = Flask(__name__)
# initialize the video stream and allow the camera sensor to
# warmup
#vs = VideoStream(usePiCamera=1).start()
# vs = VideoStream(src=0).start()
# time.sleep(2.0)

@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")

def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock, web_output_queue
    # loop over frames from the output stream
    while True:
        last_image = None

        # Wait until we have an image
        while not web_output_queue.empty():
            last_image = web_output_queue.get()

        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

outputFrame = None

# def detect_motion():
#     global outputFrame
#     # loop over frames from the video stream
#     while True:
#         while not 
#         # read the next frame from the video stream, resize it,
#         # convert the frame to grayscale, and blur it
#         frame = vs.read()
#         frame = imutils.resize(frame, width=400)
#         # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#         # gray = cv2.GaussianBlur(gray, (7, 7), 0)
#         # grab the current timestamp and draw it on the frame
#         timestamp = datetime.datetime.now()
#         with lock:
#             outputFrame = cv2.putText(frame, timestamp.strftime(
#                 "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")


########################
# Kibbie process
########################

def kibbie_process(servo_command_queue, servo_log_queue, web_output_queue):
    
    kb = kibbie(
        camera=CAMERA_DEVICE,
        log_filename="kibbie.log",
        config={
            "enableWhiteBalance": True,
            "saveSnapshotOnDoorMovement": True,             # Set to True to save snapshots on every door open or close
            "saveSnapshotWhileDoorOpenPeriodSeconds": 10,   # Set to integer > 0 to save snapshots while door is open
            "cats":[
                {
                    "name": "Noodle",
                    # Test color filter HSV thresholds using blue_filter.py first
                    "lowerHSVThreshold": [0, 0, 0],
                    "upperHSVThreshold": [255, 255, 70],
                },
                {
                    "name": "Cami",
                    # Test color filter HSV thresholds using blue_filter.py first
                    "lowerHSVThreshold": [0, 60, 90],
                    "upperHSVThreshold": [20, 130, 250],
                },
            ],
            "corrals": [
                {
                    "name": "NOODLE_L",
                    "allowedCats": ["Noodle"],
                    # Use the "unscaled" coordinates from `camera_calibration.py`
                    "mask": MASK_REGION_LEFT,
                    # Number of pixels required for a cat to be "present", unscaled
                    "minPixelThreshold": 400 / 0.1, # (calibrated at 0.1 scale); Higher for Noodle due to ~100px of black from the aluminum rail
                    "dispensesPerDay": 3,
                    # Servo configuration
                    "dispenserServoChannel": Servo.CHANNEL_DISPENSER_LEFT,
                    "doorServoChannel": Servo.CHANNEL_DOOR_LEFT,
                    "doorServoAngleOpen": Servo.ANGLE_DOOR_LEFT_OPEN,
                    "doorServoAngleClosed": Servo.ANGLE_DOOR_LEFT_CLOSED,
                    "doorLatchServoChannel": Servo.CHANNEL_DOOR_LATCH_LEFT,
                    "doorLatchServoAngleUnlocked": Servo.ANGLE_DOOR_LATCH_LEFT_UNLOCKED,
                    "doorLatchServoAngleLocked": Servo.ANGLE_DOOR_LATCH_LEFT_LOCKED,
                },
                {
                    "name": "CAMI_R",
                    "allowedCats": ["Cami"],
                    "dispensesPerDay": 3,
                    # Use the "unscaled" coordinates from `camera_calibration.py`
                    "mask": MASK_REGION_RIGHT,
                    # Number of pixels required for a cat to be "present"
                    "minPixelThreshold": 300 / 0.1, # (calibrated at 0.1 scale)
                    # Servo configuration
                    "dispenserServoChannel": Servo.CHANNEL_DISPENSER_RIGHT,
                    "doorServoChannel": Servo.CHANNEL_DOOR_RIGHT,
                    "doorServoAngleOpen": Servo.ANGLE_DOOR_RIGHT_OPEN,
                    "doorServoAngleClosed": Servo.ANGLE_DOOR_RIGHT_CLOSED,
                    "doorLatchServoChannel": Servo.CHANNEL_DOOR_LATCH_RIGHT,
                    "doorLatchServoAngleUnlocked": Servo.ANGLE_DOOR_LATCH_RIGHT_UNLOCKED,
                    "doorLatchServoAngleLocked": Servo.ANGLE_DOOR_LATCH_RIGHT_LOCKED,
                }
            ],
        },
        servo_command_queue=servo_command_queue,
        servo_log_queue=servo_log_queue,
        web_output_queue=web_output_queue,
    )
    kb.main()

########################
# Main
########################
if __name__=="__main__":
    # construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, default="0.0.0.0",
        help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, default=80,
        help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-f", "--frame-count", type=int, default=32,
        help="# of frames used to construct the background model")
    args = vars(ap.parse_args())
    # start a thread that will perform motion detection
    # t = threading.Thread(target=detect_motion, )
    # t.daemon = True
    # t.start()
    # start the flask app
    app.run(host=args["ip"], port=args["port"], debug=True, threaded=True, use_reloader=False)

    # Set up kibbie process
    kibbie_process_handle = Process(target=kibbie_process, args=(servo_command_queue, servo_log_queue, web_output_queue))
    kibbie_process_handle.start()

    # Set up servo process
    servo_process_handle = Process(target=servo_process, args=(servo_command_queue, servo_log_queue,))
    servo_process_handle.start()
    
    # Wait for process to complete here
    kibbie_process_handle.join()
    servo_process_handle.join()
