"""Experimental evidence that the lower net tape is visible over a person.

This reports only a possible far-side cue. A missing tape is ambiguous because
players, lighting, motion blur, and the image boundary can hide it.
"""

import cv2
import numpy as np


def tape_visibility(image, box, line_px, hsv=None):
    """Measure bright, low-saturation ridge continuity along a known tape line.

    `line_px` is two image points on the lower white net tape. The line must
    be calibrated for this camera before this diagnostic can be used.
    """
    x1, y1, x2, y2 = map(float, box)
    (ax, ay), (bx, by) = line_px
    if x2 <= x1 or bx == ax:
        return {'status': 'not_applicable', 'reason': 'invalid_geometry'}
    left = max(int(x1 + .20 * (x2 - x1)), int(min(ax, bx)))
    right = min(int(x2 - .20 * (x2 - x1)), int(max(ax, bx)))
    if right - left < 15:
        return {'status': 'not_applicable', 'reason': 'too_narrow'}
    xs = np.arange(left, right + 1, 2)
    ys = ay + (xs - ax) * (by - ay) / (bx - ax)
    if (np.min(ys) < y1 + 8 or np.max(ys) > y2 - 8
            or min(xs) < 0 or max(xs) >= image.shape[1]
            or min(ys) < 17 or max(ys) >= image.shape[0] - 17):
        return {'status': 'not_applicable', 'reason': 'tape_outside_body'}
    if hsv is None:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # A true tape is a narrow white ridge against the same body just above
    # and below it. Searching within six pixels tolerates slight tape sag.
    hits = []
    for x, approx_y in zip(xs, ys):
        y = int(round(approx_y))
        upper = np.median(hsv[y-16:y-9, x, 2])
        lower = np.median(hsv[y+10:y+17, x, 2])
        background = (upper + lower) / 2
        roi = hsv[y-6:y+7, x]
        hit = np.any((roi[:, 2] >= 170) & (roi[:, 1] <= 90)
                     & (roi[:, 2] >= background + 35))
        hits.append(bool(hit))
    fraction = float(np.mean(hits))
    longest = 0
    current = 0
    for hit in hits:
        current = current + 1 if hit else 0
        longest = max(longest, current)
    return {'status': 'measured', 'white_ridge_fraction': round(fraction, 3),
            'longest_white_run_fraction': round(longest / len(hits), 3),
            'sampled_columns': len(hits)}
