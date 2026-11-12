"""Experimental exact-height net-tape continuation measure.

Only measures image evidence. A bright jersey mark can still mimic tape.
"""

import cv2
import numpy as np


def line_continuity(image, box, line_px, hsv=None):
    x1, y1, x2, y2 = map(float, box)
    (ax, ay), (bx, by) = line_px
    if x2 <= x1 or bx == ax:
        return {'status': 'not_applicable', 'reason': 'invalid_geometry'}
    left = int(round(x1 + .2 * (x2 - x1)))
    right = int(round(x2 - .2 * (x2 - x1)))
    if right - left < 15:
        return {'status': 'not_applicable', 'reason': 'too_narrow'}
    xs = np.arange(left, right + 1, 2)
    ys = np.rint(ay + (xs - ax) * (by - ay) / (bx - ax)).astype(int)
    if (xs.min() < 0 or xs.max() >= image.shape[1] or
            ys.min() < max(int(y1) + 12, 16) or
            ys.max() > min(int(y2) - 12, image.shape[0] - 17)):
        return {'status': 'not_applicable', 'reason': 'tape_outside_box'}
    if hsv is None:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    def is_tape_hit(x, y):
        # Sample the calibrated line itself, with only 2 px tolerance.
        ridge = hsv[y-2:y+3, x]
        context = np.r_[hsv[y-16:y-10, x, 2], hsv[y+11:y+17, x, 2]]
        peak = int(ridge[:, 2].max())
        saturation = int(ridge[ridge[:, 2].argmax(), 1])
        return peak >= 170 and saturation <= 90 and peak >= float(np.median(context)) + 35

    hits = [is_tape_hit(int(x), int(y)) for x, y in zip(xs, ys)]
    flanks = {}
    for name, flank_xs in (
            ('left', range(int(x1) - 20, int(x1) - 4, 2)),
            ('right', range(int(x2) + 5, int(x2) + 21, 2))):
        valid = [x for x in flank_xs if max(0, min(ax, bx)) <= x <=
                 min(image.shape[1] - 1, max(ax, bx))]
        if len(valid) < 4:
            flanks[name] = None
            continue
        flank_hits = [is_tape_hit(x, int(round(ay + (x - ax) * (by - ay) / (bx - ax))))
                      for x in valid]
        flanks[name] = round(float(np.mean(flank_hits)), 3)
    longest = current = 0
    for hit in hits:
        current = current + 1 if hit else 0
        longest = max(longest, current)
    return {'status': 'measured',
            'exact_line_fraction': round(float(np.mean(hits)), 3),
            'longest_run_fraction': round(longest / len(hits), 3),
            'left_flank_fraction': flanks['left'],
            'right_flank_fraction': flanks['right'],
            'sampled_columns': len(hits)}
