"""Measure whether a calibrated bright line spans a complete person box."""

import cv2
import numpy as np


def full_box_tape_span(image, box, line_px, hsv=None):
    x1, y1, x2, y2 = map(float, box)
    (ax, ay), (bx, by) = line_px
    if x2 <= x1 or bx == ax:
        return {'status': 'not_applicable', 'reason': 'invalid_geometry'}
    left, right = int(round(x1)), int(round(x2))
    if right - left < 20 or left < 0 or right >= image.shape[1]:
        return {'status': 'not_applicable', 'reason': 'box_outside_image_or_narrow'}
    xs = np.arange(left, right + 1, 2)
    ys = np.rint(ay + (xs - ax) * (by - ay) / (bx - ax)).astype(int)
    if (ys.min() < max(int(y1) + 12, 17) or
            ys.max() > min(int(y2) - 12, image.shape[0] - 18)):
        return {'status': 'not_applicable', 'reason': 'tape_outside_box'}
    if hsv is None:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hits = []
    for x, y in zip(xs, ys):
        ridge = hsv[y-2:y+3, x]
        peak_idx = int(np.argmax(ridge[:, 2]))
        peak = int(ridge[peak_idx, 2])
        saturation = int(ridge[peak_idx, 1])
        context = np.r_[hsv[y-16:y-10, x, 2], hsv[y+11:y+17, x, 2]]
        hits.append(peak >= 170 and saturation <= 90 and
                    peak >= float(np.median(context)) + 35)
    n = len(hits)
    edge_n = max(3, int(round(n * .1)))
    longest_gap = gap = 0
    for hit in hits:
        gap = 0 if hit else gap + 1
        longest_gap = max(longest_gap, gap)
    return {'status': 'measured', 'sampled_columns': n,
            'full_width_fraction': round(float(np.mean(hits)), 3),
            'left_edge_fraction': round(float(np.mean(hits[:edge_n])), 3),
            'right_edge_fraction': round(float(np.mean(hits[-edge_n:])), 3),
            'largest_missing_gap_px': 2 * longest_gap}
