"""
Demo to filter color with OpenCV

Source: https://www.geeksforgeeks.org/filter-color-with-opencv/
"""

import cv2
import numpy as np
  
import lib.img_tools as img_tools
scale = 0.1

# Color calibration

# Noodle
# H: [0, 50]
# S: [0, 255]
# V: [0, 40]
lower_bound_hsv = [0, 0, 0]
upper_bound_hsv = [50, 255, 40]

# Cami
# R: [80, 180]
# G: [60, 130]
# B: [20, 60]

def filter_and_show(name, col, frame):
    # Scale down image
    frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
    
    # Perform white balance
    frame = img_tools.white_balance(frame)

    # It converts the BGR color space of image to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
      
    # Threshold of blue in HSV space
    lower_blue = np.array(lower_bound_hsv) # np.array([60, 35, 140])
    upper_blue = np.array(upper_bound_hsv) # np.array([180, 255, 255])
  
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
    cv2.moveWindow(frame_win,  col * width_px, 0 * (height_px + 50))
    cv2.moveWindow(mask_win,   col * width_px, 1 * (height_px + 50))
    cv2.moveWindow(result_win, col * width_px, 2 * (height_px + 50))
  

# Show all 3 images side by side
filter_and_show("cami", 0, cv2.imread('software/images/cami.png'))
filter_and_show("noodle", 1, cv2.imread('software/images/noodle.png'))
filter_and_show("empty", 2, cv2.imread('software/images/empty.png'))

cv2.waitKey(0)
cv2.destroyAllWindows()
# cap.release()