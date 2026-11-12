"""Evaluate a small held-out shoe-midpoint reference for the U5 box proxy.

Marks are approximate single-reviewer source-image readings. Dynamic or
occluded shoes excluded before error calculation are recorded explicitly.
"""
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = SCREEN / 'heldout_shoe_reference/index.json'
CALIBRATION = SCREEN / 'near_court_candidate.json'
EARLIER = SCREEN / 'floor_proxy_reference_audit.json'
OUT = SCREEN / 'heldout_box_floor_error.json'

# Visible midpoints of clear grounded shoe pairs, estimated on gridded source
# crops. Reading uncertainty is approximately ±8 px. These are reference
# diagnostics only, not corrections to any tracker rows.
REFERENCE = {
    (1, 34, 59): (665, 339), (1, 34, 4): (678, 613),
    (1, 34, 16): (785, 326), (1, 34, 6): (830, 338),
    (1, 34, 44): (937, 459),
    (2, 28, 3): (475, 550), (2, 28, 5): (694, 580),
    (2, 28, 1): (844, 562), (2, 28, 7): (993, 472),
    (3, 13, 4): (384, 490), (3, 13, 14): (590, 339),
    (3, 13, 2): (702, 546), (3, 13, 7): (710, 327),
    (3, 13, 10): (865, 348), (3, 13, 6): (905, 455),
    (3, 34, 1): (348, 530), (3, 34, 5): (560, 341),
    (3, 34, 2): (697, 576), (3, 34, 7): (699, 334),
    (3, 34, 10): (811, 337), (3, 34, 8): (882, 465),
}
EXCLUDED = {
    (1, 34, 33): 'running_single_or_unclear_contact',
    (2, 28, 2): 'one_shoe_raised_no_clear_pair_midpoint',
    (2, 28, 12): 'running_motion_and_overlap_no_clear_pair_midpoint',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(H, pixel):
    point = np.asarray([[pixel]], np.float32)
    return cv2.perspectiveTransform(point, H)[0, 0].astype(float)


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    earlier = json.loads(EARLIER.read_text(encoding='utf-8'))
    assert index['source_sha256'] == earlier['source_sha256']
    assert index['selected_floor_index_sha256'] == sha(SCREEN / 'selected_floor_qc/index.json')
    assert len(index['entries']) == 4
    H = np.asarray(calibration['homography_image_to_court'], np.float64)
    rows, exclusions = [], []
    for entry in index['entries']:
        sheet = SCREEN / 'heldout_shoe_reference' / entry['sheet']
        assert sha(sheet) == entry['sha256']
        for box in entry['boxes']:
            key = entry['set'], entry['point_number'], box['raw_track_id']
            if key in EXCLUDED:
                exclusions.append({'set': key[0], 'point_number': key[1],
                                   'raw_track_id': key[2], 'reason': EXCLUDED[key]})
                continue
            reference = REFERENCE[key]
            xa, ya = box['crop_origin_px']
            xb, yb = box['crop_end_px']
            assert xa <= reference[0] < xb and ya <= reference[1] < yb, key
            x1, _, x2, y2 = box['bbox_px']
            bottom = ((x1 + x2) / 2, y2)
            court_bottom = project(H, bottom)
            court_reference = project(H, reference)
            rows.append({
                'set': key[0], 'point_number': key[1], 'source_frame': entry['source_frame'],
                'raw_track_id': key[2], 'box_bottom_px': [round(v, 1) for v in bottom],
                'reviewed_shoe_pair_midpoint_px': list(reference),
                'box_bottom_court_m': [round(float(v), 3) for v in court_bottom],
                'shoe_midpoint_court_m': [round(float(v), 3) for v in court_reference],
                'box_minus_shoe_court_dx_dy_m': [round(float(v), 3)
                                                 for v in court_bottom - court_reference],
                'pixel_distance': round(math.dist(bottom, reference), 2),
                'court_distance_m': round(float(np.linalg.norm(court_bottom - court_reference)), 3),
            })
    assert len(rows) == len(REFERENCE) == 21 and len(exclusions) == 3
    distances = [r['court_distance_m'] for r in rows]
    dx = [r['box_minus_shoe_court_dx_dy_m'][0] for r in rows]
    dy = [r['box_minus_shoe_court_dx_dy_m'][1] for r in rows]
    summary = {
        'source_frames': 4, 'reviewed_clear_grounded_shoe_pairs': len(rows),
        'excluded_unclear_shoe_pairs': len(exclusions),
        'median_box_to_shoe_distance_m': round(statistics.median(distances), 3),
        'maximum_box_to_shoe_distance_m': max(distances),
        'median_signed_box_minus_shoe_dx_m': round(statistics.median(dx), 3),
        'median_signed_box_minus_shoe_dy_m': round(statistics.median(dy), 3),
        'earlier_clear_shoe_reference_boxes': earlier['summary']['reviewed_grounded_boxes'],
        'validated_six_player_metric_frames': 0,
    }
    OUT.write_text(json.dumps({
        'status': 'heldout_single_reviewer_clear_shoe_proxy_error_not_final_validation',
        'source_sha256': index['source_sha256'],
        'input_sha256': {'review_index': sha(INDEX), 'calibration': sha(CALIBRATION),
                         'earlier_reference': sha(EARLIER)},
        'manual_reference_rule': 'Approximate midpoint of two visible grounded shoes; ±8 px visual reading uncertainty.',
        'summary': summary, 'rows': rows, 'excluded_boxes': exclusions,
        'limitations': ['Chosen frames were held out from the earlier nine-box reference, but the same reviewer marked both.',
                        'Only clear shoe pairs enter the error distribution; jumping, motion and overlap are underrepresented.',
                        'A midpoint between shoes is an operational ground anchor, not a physical centre of mass.',
                        'The staged court homography and shoe markings lack independent inter-observer validation.',
                        'No full point interval or six-player trajectory is validated by this bounded check.'],
    }, indent=2) + '\n', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
