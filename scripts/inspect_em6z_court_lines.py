"""List prominent near-court floor lines on the median source frame."""

import cv2
import numpy as np

image = cv2.imread('data/matches/yt_em6zFUxfYpc/pilot/court_median.jpg')
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 70, 170)
edges[:690] = 0
lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=75,
                        minLineLength=170, maxLineGap=90)
items = []
for (x1, y1, x2, y2), in lines:
    length = float(np.hypot(x2 - x1, y2 - y1))
    slope = (y2 - y1) / (x2 - x1) if x1 != x2 else float('inf')
    if length >= 200:
        items.append((round(length, 1), round(slope, 3),
                      (int(x1), int(y1), int(x2), int(y2))))
for item in sorted(items, reverse=True)[:90]:
    print(item)
