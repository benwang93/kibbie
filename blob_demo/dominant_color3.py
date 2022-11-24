# Similar to dominant_color2.py, except it runs off of the webam and can identify 2 zones
# Source: https://stackoverflow.com/questions/5906693/how-to-reduce-the-number-of-colors-in-an-image-with-opencv

import cv2
import numpy as np
import matplotlib.pyplot as plt

def quantizeColors(img):
    # colorReduce()
    # div = 64
    div = 128
    quantized = img // div * div + div // 2
    return quantized

"""
Returns unique colors and count of each color given an image
"""
def getDominantColors(quantized):
    # Reshape from [x, y, 3] to [(x*y), 3] so that unique with an axis of 0 will return
    # unique colors (length 3 arrays)
    unique,freq=np.unique(quantized.reshape(240*320, 3), return_counts=True, axis=0)
    return unique,freq

"""
Visualize unique colors in an image
"""
def plotDominantColors(img, unique, freq):
    # Sort colors
    indices = np.argsort(freq)[::-1]

    dom_patch = np.zeros(shape=img.shape, dtype=np.uint8)
    start_row = 0
    for i in indices:
        bgr_color = unique[i]
        count = freq[i]
        rgb_color = list(reversed(bgr_color))
        end_row = start_row + int(round(count / img.shape[1], 0))
        dom_patch[start_row:end_row, :, :] = rgb_color

        start_row = end_row

    # Display dominant colors
    cv2.imshow("dominant", dom_patch)

def main():
    # define a video capture object
    vid = cv2.VideoCapture(0)
    
    while(True):
        # Capture the video frame
        # by frame
        ret, frame = vid.read()

        # Downsample for faster processing
        scale = 0.5 #0.1
        img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        quantized = quantizeColors(img)

        # cv2.imwrite('output.jpg', quantized)
        cv2.imshow("img", img)
        cv2.imshow("quantized", quantized)

        unique,freq = getDominantColors(quantized)
        plotDominantColors(img, unique, freq)
        
        # the 'q' button is set as the
        # quitting button you may use any
        # desired button of your choice
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # After the loop release the cap object
    vid.release()
    # Destroy all the windows
    cv2.destroyAllWindows()

if __name__=="__main__":
    main()
