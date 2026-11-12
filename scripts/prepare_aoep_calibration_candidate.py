"""Draw an unverified AoEP near-court line fit; do not install it as homography."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
OUT = MATCH / 'pilot/calibration'
IMAGE = OUT / 'source_median_74920_75420.jpg'

# Hough-supported dark line segments from the source-only median. Several
# other sports markings cross the floor; assignment remains provisional.
LINES = {
    'left_sideline': [[0, 598], [446, 371]],
    'right_sideline': [[934, 367], [1279, 511]],
    'near_baseline': [[68, 605], [1270, 608]],
    'near_attack_line': [[113, 496], [820, 496]],
}


def intersection(a, b):
    (x1, y1), (x2, y2) = a
    (x3, y3), (x4, y4) = b
    matrix = np.array([[x2 - x1, x3 - x4], [y2 - y1, y3 - y4]], float)
    rhs = np.array([x3 - x1, y3 - y1], float)
    t = np.linalg.solve(matrix, rhs)[0]
    return np.array([x1 + t * (x2 - x1), y1 + t * (y2 - y1)], float)


def interior(line, fraction):
    left = intersection(LINES['left_sideline'], line)
    right = intersection(LINES['right_sideline'], line)
    return (left + fraction * (right - left)).tolist()


def main():
    image = cv2.imread(str(IMAGE))
    if image is None:
        raise FileNotFoundError(IMAGE)
    pixel = [interior(LINES['near_baseline'], 1 / 9),
             interior(LINES['near_baseline'], 7 / 9),
             interior(LINES['near_attack_line'], 7 / 9),
             interior(LINES['near_attack_line'], 1 / 9)]
    court = [[1, 0], [7, 0], [7, 6], [1, 6]]
    inverse = cv2.getPerspectiveTransform(np.asarray(court, np.float32),
                                          np.asarray(pixel, np.float32))
    projected_net = cv2.perspectiveTransform(
        np.asarray([[[0, 9], [9, 9]]], np.float32), inverse)[0]
    if np.max(np.abs(projected_net[:, 1] - 463)) > 5:
        raise ValueError('Projected net misses the visible source centerline')
    overlay = image.copy()
    for y in (0, 3, 6, 9):
        p = cv2.perspectiveTransform(np.asarray([[[0, y], [9, y]]], np.float32), inverse)[0]
        cv2.line(overlay, tuple(np.rint(p[0]).astype(int)),
                 tuple(np.rint(p[1]).astype(int)), (0, 255, 255), 2, cv2.LINE_AA)
    for x in (0, 3, 6, 9):
        p = cv2.perspectiveTransform(np.asarray([[[x, 0], [x, 9]]], np.float32), inverse)[0]
        cv2.line(overlay, tuple(np.rint(p[0]).astype(int)),
                 tuple(np.rint(p[1]).astype(int)), (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(overlay, 'CANDIDATE ONLY: confirm court line family', (20, 48),
                cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2, cv2.LINE_AA)
    payload = {
        'schema_version': 'v1', 'image_size': [image.shape[1], image.shape[0]],
        'points_px': [[round(x, 3) for x in point] for point in pixel],
        'points_court_m': court,
        'court_coordinates': 'near baseline y=0m; attack line y=6m; net y=9m; left/right sidelines x=0/9m',
        'line_evidence_px': LINES,
        'method': '51-frame source-only median; Hough-supported sidelines, near baseline at y≈605px, and near attack line at y≈496px. The projected net floor line at y≈464px independently matches the visible centerline at y≈463px. Four interior points at court x=1m and x=7m avoid extrapolated corners outside the frame. A first y=428px attack-line hypothesis was rejected because it placed far-white feet on the near side of the projected net.',
        'camera_registration': 'Upper-wall phase correlation relative to frame 74970: frame 75180 dx=-0.016px dy=0.025px response=0.951; frame 75280 dx=0.019px dy=0.102px response=0.936.',
        'status': 'candidate_unverified_floor_marking_assignment',
        'use_for_metrics': False,
        'limitation': 'The floor has overlapping markings from other sports. A visual line-family and projected-grid check is required before installing a canonical homography or filtering teams.',
    }
    path = OUT / 'near_court_candidate.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8')) != payload:
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    overlay_path = OUT / 'near_court_candidate_overlay.jpg'
    if not overlay_path.exists() and not cv2.imwrite(str(overlay_path), overlay):
        raise OSError(overlay_path)
    print(path)
    print(overlay_path)


if __name__ == '__main__':
    main()
