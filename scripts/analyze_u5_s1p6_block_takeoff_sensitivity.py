"""Contrast last grounded marks with airborne box bottoms for two blockers."""

import csv
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PACK = SCREEN / 's1p6_fixed_window_source_review'
SOURCE = PACK / 'completed.csv'
PAIRED = PACK / 'paired_completed.csv'
DETECTOR = PACK / 'exact_30fps_candidates.json'
TRANSFORM = SCREEN / 's3p34_calibration_review/refined_candidate.json'
OUT = PACK / 'block_takeoff_sensitivity.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S1P6_BLOCK_TAKEOFF_SENSITIVITY.md'
TAKEOFF_FRAME = 1777
AIRBORNE_FRAME = 1783
SLOTS = (1, 2)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main():
    source = {(int(r['source_frame']), int(r['slot'])): r for r in rows(SOURCE)}
    paired = {(int(r['source_frame']), int(r['slot'])): r for r in rows(PAIRED)}
    detector = {r['source_frame']: r for r in json.loads(DETECTOR.read_text(encoding='utf-8'))['rows']}
    transform = json.loads(TRANSFORM.read_text(encoding='utf-8'))
    matrix = np.asarray(transform['homography_image_to_court'], np.float64)

    def mapped(point):
        return cv2.perspectiveTransform(np.asarray([[point]], np.float32), matrix)[0, 0]

    comparisons = []
    for slot in SLOTS:
        grounded = source[(TAKEOFF_FRAME, slot)]
        airborne = source[(AIRBORNE_FRAME, slot)]
        matched = paired[(TAKEOFF_FRAME, slot)]
        assert grounded['ground_status'] == 'grounded' and airborne['ground_status'] == 'airborne'
        assert matched['candidate_alignment'] == 'same_player' and matched['floor_alignment'] == 'plausible'
        track_id = int(matched['raw_track_id'])
        first = next(x for x in detector[TAKEOFF_FRAME]['detections'] if x['raw_track_id'] == track_id)
        last = next(x for x in detector[AIRBORNE_FRAME]['detections'] if x['raw_track_id'] == track_id)
        first_center = ((first['bbox_px'][0] + first['bbox_px'][2]) / 2,
                        (first['bbox_px'][1] + first['bbox_px'][3]) / 2)
        last_center = ((last['bbox_px'][0] + last['bbox_px'][2]) / 2,
                       (last['bbox_px'][1] + last['bbox_px'][3]) / 2)
        last_grounded = (float(grounded['shoe_x_px']), float(grounded['shoe_y_px']))
        airborne_bottom = ((last['bbox_px'][0] + last['bbox_px'][2]) / 2, last['bbox_px'][3])
        comparison = {'slot': slot, 'raw_track_id_from_last_grounded_pair': track_id,
                      'last_grounded_shoe_px': last_grounded,
                      'airborne_box_bottom_px': airborne_bottom,
                      'box_center_horizontal_shift_px': round(last_center[0] - first_center[0], 2),
                      'box_bottom_vertical_shift_px': round(last['bbox_px'][3] - first['bbox_px'][3], 2),
                      'exploratory_mapped_separation_m': round(float(math.dist(mapped(last_grounded),
                                                                                   mapped(airborne_bottom))), 3)}
        comparisons.append(comparison)
    result = {'status': 'illustrative_hold_last_grounded_position_sensitivity',
              'input_sha256': {'source': sha(SOURCE), 'paired': sha(PAIRED),
                               'detector': sha(DETECTOR), 'exploratory_transform': sha(TRANSFORM)},
              'last_grounded_source_frame': TAKEOFF_FRAME, 'airborne_source_frame': AIRBORNE_FRAME,
              'elapsed_frames': AIRBORNE_FRAME - TAKEOFF_FRAME,
              'strict_metric_approval': False, 'comparisons': comparisons,
              'interpretation': 'The last grounded shoe click is an observed position at frame 1777, not an observed landing point or true floor point at frame 1783. The mapped separation is between two proxy choices under an unapproved transform, not physical movement or measured error.'}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    lines = ['# S1 P6 blocking-jump footprint sensitivity', '',
             'At frame 1783, source slots 1 and 2 are airborne during a block. Both had grounded '
             'shoe clicks at frame 1777. Their earlier paired raw IDs remain present in the detector '
             'output at frame 1783, although the original paired-review page hid those boxes above '
             'its crude near-side cutoff. The table contrasts the earlier observed shoe points '
             'with the later airborne box bottoms.', '',
             '| Source slot | Horizontal box-centre shift, 1777→1783 | Box-bottom rise | Mapped separation: last grounded shoe vs airborne box bottom |',
             '| ---: | ---: | ---: | ---: |']
    for row in comparisons:
        lines.append(f'| {row["slot"]} | {row["box_center_horizontal_shift_px"]:+.2f} px | '
                     f'{-row["box_bottom_vertical_shift_px"]:.2f} px | '
                     f'{row["exploratory_mapped_separation_m"]:.3f} m |')
    lines += ['',
              'The small horizontal centre shifts are consistent with a largely vertical blocking '
              'jump over these six frames. Projecting the raised box bottom as if it were a floor '
              'contact shifts the candidate court point substantially relative to the previous '
              'grounded shoe mark. That does not prove the foot location remained fixed: a blocker '
              'can drift or land elsewhere. Carrying the previous grounded point to frame 1783 '
              'would be an **imputed takeoff-location scenario**, not an observed 1783 position.', '',
              'The metre differences use the exploratory refined transform, which has not passed '
              'the new out-of-point check. They are differences between proxy choices, not player '
              'travel, accuracy errors or uncertainty bounds. The strict frame remains null for '
              'the two airborne players. The [machine-readable result]'
              '(../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/block_takeoff_sensitivity.json) '
              'records source hashes and both proxy points.', '',
              'Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s1p6_block_takeoff_sensitivity.py`.']
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print([(x['slot'], x['box_center_horizontal_shift_px'],
            x['exploratory_mapped_separation_m']) for x in comparisons])


if __name__ == '__main__':
    main()
