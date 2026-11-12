"""Fit the held-out near court from visible baseline, attack line, and sidelines."""

import json
from pathlib import Path

import cv2
import numpy as np


MATCH = Path('data/matches/yt_em6zFUxfYpc')
OUT = MATCH / 'pilot/calibration'
IMAGE = MATCH / 'pilot/court_median.jpg'

# At court x=1m and x=8m, points on the baseline and 6m attack line.
# These interior points are derived from the intersections of measured line
# equations, since the two baseline-sideline corners fall outside the image.
POINTS_PX = [[17.857, 1008.268], [1890.385, 1010.041],
             [1291.929, 769.672], [556.718, 786.450]]
POINTS_M = [[1, 0], [8, 0], [8, 6], [1, 6]]


def draw_line(image, inverse, a, b, color, width=3):
    points = cv2.perspectiveTransform(
        np.asarray([[a, b]], dtype=np.float32), inverse)[0]
    p1, p2 = [tuple(map(lambda x: int(round(x)), point)) for point in points]
    cv2.line(image, p1, p2, color, width, cv2.LINE_AA)


def main():
    image = cv2.imread(str(IMAGE))
    if image is None:
        raise FileNotFoundError(IMAGE)
    forward = cv2.getPerspectiveTransform(np.asarray(POINTS_PX, np.float32),
                                          np.asarray(POINTS_M, np.float32))
    inverse = cv2.getPerspectiveTransform(np.asarray(POINTS_M, np.float32),
                                          np.asarray(POINTS_PX, np.float32))
    if abs(np.linalg.det(forward)) < 1e-10:
        raise ValueError('Singular calibration')
    overlay = image.copy()
    for y in (0, 3, 6, 9):
        draw_line(overlay, inverse, [0, y], [9, y], (0, 255, 255), 3)
    for x in (0, 3, 6, 9):
        draw_line(overlay, inverse, [x, 0], [x, 9], (0, 255, 255), 3)
    cv2.putText(overlay, 'Near court: y=0 baseline, y=6 attack, y=9 net',
                (40, 1050), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)
    payload = {
        'schema_version': 'v1', 'image_size': [1920, 1080],
        'points_px': POINTS_PX, 'points_court_m': POINTS_M,
        'court_coordinates': 'near baseline y=0m; net y=9m; left sideline x=0m; right sideline x=9m',
        'method': 'Median image of 31 source frames; Hough-supported near baseline and volleyball attack line at approximately y=780px, with visible sidelines. Baseline corners are outside the image; four interior points at court x=1m and 8m are inferred from the fitted lines. A first y=875px candidate was rejected as a different floor marking.',
        'line_evidence_px': {
            'left_sideline': [[0, 930], [768, 690]],
            'right_sideline': [[1155, 690], [1919, 934]],
            'near_baseline': [[791, 1009], [1847, 1010]],
            'near_attack_line': [[445, 789], [1409, 767]],
        },
        'camera_registration': 'Static upper-frame phase correlation from frames 243 and 754: dx=0.38px, dy=-0.04px, response=0.94.',
        'status': 'visually_checked_court_line_fit_for_team_region_filter',
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'near_court.json'
    if path.exists():
        existing = json.loads(path.read_text(encoding='utf-8'))
        if existing != payload:
            archive = OUT / 'rejected_y875_line.json'
            if existing != json.loads(archive.read_text(encoding='utf-8')):
                raise FileExistsError('Calibration changed outside this correction; refusing to overwrite')
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    canonical = MATCH / 'homography.json'
    if canonical.exists():
        if json.loads(canonical.read_text(encoding='utf-8')) != payload:
            raise FileExistsError('Top-level match homography has different content')
    else:
        canonical.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    cv2.imwrite(str(OUT / 'near_court_overlay.jpg'), overlay)
    print(json.dumps({'calibration': str(path), 'overlay': str(OUT / 'near_court_overlay.jpg'),
                      'projected_net_corners_px': cv2.perspectiveTransform(
                          np.asarray([[[0, 9], [9, 9]]], np.float32), inverse)[0].tolist()}, indent=2))


if __name__ == '__main__':
    main()
