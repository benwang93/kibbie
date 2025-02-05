# Source: https://stackoverflow.com/questions/5906693/how-to-reduce-the-number-of-colors-in-an-image-with-opencv

import cv2
import numpy as np

# img = cv2.imread('blob_demo/noodle.png')
img = cv2.imread('blob_demo/cami.png')
img = cv2.resize(img, (0, 0), fx=0.1, fy=0.1)
# img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)

# colorReduce()
# div = 64
div = 128
quantized = img // div * div + div // 2

def colorToHashable(bgr):
    return (bgr[0] * 256 + bgr[1]) * 256 + bgr[2]

def hashToColor(n):
    r = n % 256
    n = int(n/256)
    g = n%256
    b = int(n/256)
    return [b, g, r]

# Count unique colors
colors = {}
for row in quantized:
    for pixel in row:
        pixel = list(pixel)
        pixelHash = colorToHashable(pixel)
        assert hashToColor(pixelHash) == pixel
        if pixelHash in colors:
            colors[pixelHash] += 1
        else:
            colors[pixelHash] = 1

# max_count = 0
# color_mode = None
# for key in colors:
#     if colors[key] > max_count:
#         max_count = colors[key]
#         color_mode = key

# Sort colors
sorted_colors = sorted(colors.items(), key=lambda x:x[1], reverse=True)
# print(sorted_colors)

print(f"# unique colors {len(sorted_colors)}")
print(f"The most common color is {sorted_colors[0]}")
print(f"The least common color is {sorted_colors[-1]}")
print(sorted_colors)

# cv2.imwrite('output.jpg', quantized)
cv2.imshow("img", img)
cv2.imshow("quantized", quantized)

###########

import matplotlib.pyplot as plt

# avg_patch = np.ones(shape=img.shape, dtype=np.uint8)*np.uint8(average)

# indices = np.argsort(counts)[::-1]   
# freqs = np.cumsum(np.hstack([[0], counts[indices]/float(counts.sum())]))
# rows = np.int_(img.shape[0]*freqs)

dom_patch = np.zeros(shape=img.shape, dtype=np.uint8)
start_row = 0
for color,count in sorted_colors:
    bgr_color = hashToColor(color)
    rgb_color = list(reversed(bgr_color))
    end_row = start_row + int(round(count / img.shape[1], 0))
    dom_patch[start_row:end_row, :, :] = rgb_color

    start_row = end_row
# for i in range(len(rows) - 1):
#     dom_patch[rows[i]:rows[i + 1], :, :] += np.uint8(palette[indices[i]])
    
fig, (ax1) = plt.subplots(1, 1, figsize=(12,6))
# ax0.imshow(avg_patch)
# ax0.set_title('Average color')
# ax0.axis('off')
ax1.imshow(dom_patch)
ax1.set_title('Dominant colors')
ax1.axis('off')
# plt.show(fig)
plt.show()

cv2.waitKey(0)