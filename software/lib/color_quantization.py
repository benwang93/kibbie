"""
Functions related to identifying colors in an image and vizualizing them
"""

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
    height_px = quantized.shape[0]
    width_px = quantized.shape[1]
    unique,freq=np.unique(quantized.reshape(height_px*width_px, 3), return_counts=True, axis=0)
    return unique,freq

"""
Visualize unique colors in an image
"""
def plotDominantColors(img, unique, freq, img_name="dominant"):
    # Sort colors
    indices = np.argsort(freq)[::-1]

    dom_patch = np.zeros(shape=img.shape, dtype=np.uint8)
    start_row = 0
    for i in indices:
        bgr_color = unique[i]
        count = freq[i]
        # rgb_color = list(reversed(bgr_color))
        end_row = start_row + int(round(count / img.shape[1], 0))
        dom_patch[start_row:end_row, :, :] = bgr_color

        start_row = end_row

    # Display dominant colors
    cv2.imshow(img_name, dom_patch)