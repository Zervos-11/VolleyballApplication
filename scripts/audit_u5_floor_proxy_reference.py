"""Compare nine U5 box bottoms with manually estimated visible shoe midpoints.

This is a bounded single-reviewer diagnostic, not independent validation or a
tolerance decision. See the unboxed crop sheets for the pixel marks.
"""
import hashlib
import json
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'live_core_box_screen.json'
CALIBRATION = BASE / 'near_court_candidate.json'
CROPS = BASE / 'floor_reference_crops/index.json'
OUT = BASE / 'floor_proxy_reference_audit.json'

# Pixel midpoints estimated from visible shoes on the unboxed source crops.
# Excluded boxes have a foot hidden, moving without a clear contact, or a poorly
# resolved shoe pair. These marks have approximate +/-8 px reading uncertainty.
REFERENCE = {
    (449, 1): (573, 465), (449, 2): (805, 466),
    (449, 3): (909, 397), (449, 4): (650, 350),
    (1203, 1): (688, 572), (1203, 2): (881, 457),
    (1203, 3): (328, 521), (1203, 5): (827, 308),
    (1203, 6): (685, 336),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(matrix, pixel):
    arr = np.asarray([[[pixel[0], pixel[1]]]], np.float32)
    return cv2.perspectiveTransform(arr, matrix)[0, 0].astype(float).tolist()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    matrix = np.asarray(calibration['homography_image_to_court'], np.float64)
    source_rows = {r['source_second']: r for r in screen['rows']}
    rows = []
    for (second, number), reference in REFERENCE.items():
        proposal = source_rows[second]['proposals'][number - 1]
        x1, _, x2, y2 = proposal['bbox_px']
        box_pixel = [(x1 + x2) / 2, y2]
        box_court = project(matrix, box_pixel)
        reference_court = project(matrix, reference)
        rows.append({'source_second': second, 'box_number': number,
                     'box_bottom_px': [round(v, 1) for v in box_pixel],
                     'visual_shoe_midpoint_px': list(reference),
                     'box_bottom_court_m': [round(v, 3) for v in box_court],
                     'visual_shoe_midpoint_court_m': [round(v, 3) for v in reference_court],
                     'pixel_distance': round(float(np.linalg.norm(
                         np.asarray(box_pixel) - np.asarray(reference))), 2),
                     'court_distance_m': round(float(np.linalg.norm(
                         np.asarray(box_court) - np.asarray(reference_court))), 3)})
    distances = [r['court_distance_m'] for r in rows]
    output = {
        'status': 'single_reviewer_approximate_shoe_reference_diagnostic_not_validation',
        'source_sha256': screen['source_sha256'],
        'box_screen_sha256': digest(SCREEN), 'calibration_sha256': digest(CALIBRATION),
        'crop_index_sha256': digest(CROPS),
        'manual_reference_rule': 'Visible midpoint of grounded shoe pair on unboxed crop; '
                                 'approximate +/-8 px reading uncertainty',
        'summary': {'reviewed_grounded_boxes': len(rows),
                    'median_box_bottom_to_shoe_midpoint_m': round(statistics.median(distances), 3),
                    'maximum_box_bottom_to_shoe_midpoint_m': max(distances),
                    'minimum_box_bottom_to_shoe_midpoint_m': min(distances)},
        'rows': rows,
        'limitations': [
            'One reviewer estimated pixels visually; no second reviewer or adjudication.',
            'Only clear shoe pairs in two frames were sampled; net actions and occlusions were excluded.',
            'The staged court transform itself has not been independently validated for player positions.',
            'The result is proxy disagreement, not ground-truth accuracy or an acceptable-error threshold.'
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
