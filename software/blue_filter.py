"""
Demo to filter color with OpenCV

Color calibration instructions:
1. Open `camera_calibration.py`
2. Change the filename at the very bottom to open an image of the target
3. Mouse around to find the lower and uppwer bound of H, S, and V values
4. Enter those as the `lower_bound_hsv` and `upper_bound_hsv` values in this file
5. Run this script to preview the selection

Source: https://www.geeksforgeeks.org/filter-color-with-opencv/
"""

import cv2
import numpy as np
  
import lib.img_tools as img_tools
# scale = 0.1
scale = 0.2

# Color calibration

# Noodle
# Noodle is dark, so we'll take any hue and any saturation, as long as the value is close to 0.
# H: [0, 50]
# S: [0, 255]
# V: [0, 40]
# lower_bound_hsv = [0, 0, 0]         # White background
# upper_bound_hsv = [255, 255, 40]    # White background

# This one seems a bit too generous - gets cami's shadow
# lower_bound_hsv = [0, 60, 0]         # Gray background
# upper_bound_hsv = [255, 255, 140]    # gray background

# Target black spots on Noodle:
lower_bound_hsv = [0, 60, 0]        # Gray background
upper_bound_hsv = [255, 255, 50]    # gray background

# Cami
# Cami is orange-ish in color, so hue is the main factor. She's also fairly saturated and bright in value (especially vs Noodle).
# H: [10, 20]
# S: [150, 255]
# V: [80, 180]
# lower_bound_hsv = [10, 130, 80]     # White background
# upper_bound_hsv = [20, 255, 220]    # White background
# lower_bound_hsv = [0, 60, 120]      # Gray background
# upper_bound_hsv = [10, 110, 240]    # gray background


def filter_and_show(name, col, frame):
    # Scale down image
    frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
    
    # Perform white balance
    frame = img_tools.white_balance(frame)

    # It converts the BGR color space of image to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
      
    # Threshold of blue in HSV space
    lower_blue = np.array(lower_bound_hsv)
    upper_blue = np.array(upper_bound_hsv)
  
    # preparing the mask to overlay
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
      
    # The black region in the mask has the value of 0,
    # so when multiplied with original image removes all non-blue regions
    result = cv2.bitwise_and(frame, frame, mask = mask)
  
    frame_win = name + '-frame'
    mask_win = name + '-mask'
    result_win = name + '-result'

    height_px = frame.shape[0]
    width_px = frame.shape[1]

    cv2.imshow(frame_win, frame)
    cv2.imshow(mask_win, mask)
    cv2.imshow(result_win, result)
    cv2.moveWindow(frame_win,  col * width_px, 0 * (height_px + 25))
    cv2.moveWindow(mask_win,   col * width_px, 1 * (height_px + 25))
    cv2.moveWindow(result_win, col * width_px, 2 * (height_px + 25))
  

# Show all 3 images side by side
filter_and_show("cami", 0, cv2.imread('software/images/cami-gray_background.png'))
filter_and_show("noodle", 1, cv2.imread('software/images/noodle-gray_background.png'))
filter_and_show("empty", 2, cv2.imread('software/images/empty-gray_background.png'))

cv2.waitKey(0)
cv2.destroyAllWindows()
# cap.release()