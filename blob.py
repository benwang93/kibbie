# Cat blob detection demo

# Source: https://learnopencv.com/blob-detection-using-opencv-python-c/
# Standard imports
import cv2
import numpy as np;
 
# Read image
im = cv2.imread("cats.png", cv2.IMREAD_GRAYSCALE)

im = cv2.resize(im, (0, 0), fx=0.2, fy=0.2)

# Setup SimpleBlobDetector parameters.
params = cv2.SimpleBlobDetector_Params()

# Change thresholds
params.minThreshold = 10
params.maxThreshold = 200
 
# Set up the detector with default parameters.
detector = cv2.SimpleBlobDetector(params)
 
# Detect blobs.
keypoints = detector.detect(im)
 
# Draw detected blobs as red circles.
# cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the size of blob
im_with_keypoints = cv2.drawKeypoints(im, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
 
# # Show keypoints
cv2.imshow("Keypoints", im)#im_with_keypoints)
cv2.waitKey(0)