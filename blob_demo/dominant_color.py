# Average color vs dominant color demo
# Source: https://stackoverflow.com/questions/43111029/how-to-find-the-average-colour-of-an-image-in-python-with-opencv

import cv2
import numpy as np
from skimage import io

import time

starttime = time.perf_counter()

# Read image
# img = io.imread("cats.png")
# img = io.imread("cami.png")
img = io.imread("noodle.png")
img = cv2.resize(img, (0, 0), fx=0.1, fy=0.1)

pixels = np.float32(img.reshape(-1, 3))

n_colors = 5
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
flags = cv2.KMEANS_RANDOM_CENTERS

_, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)
_, counts = np.unique(labels, return_counts=True)

dominant = palette[np.argmax(counts)]

endtime = time.perf_counter()
print(f"Duration: {(endtime - starttime) * 1000}ms")

import matplotlib.pyplot as plt

# avg_patch = np.ones(shape=img.shape, dtype=np.uint8)*np.uint8(average)

indices = np.argsort(counts)[::-1]   
freqs = np.cumsum(np.hstack([[0], counts[indices]/float(counts.sum())]))
rows = np.int_(img.shape[0]*freqs)

dom_patch = np.zeros(shape=img.shape, dtype=np.uint8)
for i in range(len(rows) - 1):
    dom_patch[rows[i]:rows[i + 1], :, :] += np.uint8(palette[indices[i]])
    
fig, (ax1) = plt.subplots(1, 1, figsize=(12,6))
# ax0.imshow(avg_patch)
# ax0.set_title('Average color')
# ax0.axis('off')
ax1.imshow(dom_patch)
ax1.set_title('Dominant colors')
ax1.axis('off')
# plt.show(fig)
plt.show()

cv2.imshow("Image resized", img)
cv2.waitKey(0)