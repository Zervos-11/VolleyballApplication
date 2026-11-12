"""Score the frozen S1 P6 marks against the pre-existing refined transform."""

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SOURCE = SCREEN / 's1p6_fixed_window_source_review'
PACK = SCREEN / 's1p6_fixed_window_calibration_review'
PROTOCOL = PACK / 'protocol.json'
FORM = PACK / 'completed.csv'
CANDIDATE = SCREEN / 's3p34_calibration_review/refined_candidate.json'
REGISTRATION = SCREEN / 'selected_camera_registration.json'
OUT = PACK / 'score.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S1P6_CALIBRATION_CHECK.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    candidate = json.loads(CANDIDATE.read_text(encoding='utf-8'))
    registration = json.loads(REGISTRATION.read_text(encoding='utf-8'))
    assert protocol['candidate_transform_sha256'] == sha(CANDIDATE)
    assert protocol['source_video_sha256'] == registration['source_sha256']
    rule = protocol['decision_rule_frozen_before_new_marks']
    result = {'status': 'awaiting_source_landmark_marks', 'protocol_sha256': sha(PROTOCOL),
              'candidate_transform_sha256': sha(CANDIDATE), 'strict_metric_approval': False}
    if FORM.exists():
        with FORM.open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 12
        matrix = np.asarray(candidate['homography_image_to_court'], np.float64)
        scored = []
        for index, row in enumerate(rows):
            frame = protocol['frames'][index // 6]
            landmark = protocol['landmarks'][index % 6]
            assert int(row['source_frame']) == frame['frame']
            assert row['image'] == frame['image'] and row['image_sha256'] == frame['sha256']
            assert sha(SOURCE / frame['image']) == frame['sha256']
            assert row['landmark_code'] == landmark['code']
            assert [float(row['court_x_m']), float(row['court_y_m'])] == landmark['court_m']
            assert row['status'] in ('marked', 'uncertain', 'occluded')
            item = {'source_frame': frame['frame'], 'landmark_code': landmark['code'],
                    'status': row['status'], 'target_court_m': landmark['court_m']}
            if row['status'] == 'marked':
                x, y = float(row['x_px']), float(row['y_px'])
                assert math.isfinite(x) and math.isfinite(y) and 0 <= x < 1280 and 0 <= y < 720
                projected = cv2.perspectiveTransform(
                    np.asarray([[[x, y]]], np.float32), matrix)[0, 0]
                item.update({'source_px': [x, y],
                             'projected_court_m': [round(float(v), 4) for v in projected],
                             'projected_error_m': round(math.dist(projected, landmark['court_m']), 4)})
            else:
                assert not row['x_px'] and not row['y_px']
                item['projected_error_m'] = None
            scored.append(item)
        errors = [row['projected_error_m'] for row in scored if row['projected_error_m'] is not None]
        shift = registration['summary']['maximum_static_landmark_shift_px']
        passed = (len(errors) == rule['required_visible_landmarks'] and
                  bool(errors) and max(errors) <= rule['maximum_projected_landmark_error_m'] and
                  shift <= rule['maximum_static_camera_registration_shift_px'])
        result.update({'status': 'scored_out_of_point_single_reviewer_calibration_check',
                       'input_sha256': {'completed_form': sha(FORM), 'registration': sha(REGISTRATION)},
                       'marked_landmarks': len(errors),
                       'required_landmarks': rule['required_visible_landmarks'],
                       'median_projected_error_m': round(statistics.median(errors), 4) if errors else None,
                       'maximum_projected_error_m': max(errors) if errors else None,
                       'maximum_registered_static_shift_px': shift,
                       'operational_screen_passed': passed, 'decision_rule': rule, 'rows': scored,
                       'strict_metric_approval': False})
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if FORM.exists():
        summary = (f'**Frozen operational screen:** {"passed" if result["operational_screen_passed"] else "did not pass"}. '
                   f'{result["marked_landmarks"]}/12 landmarks marked; median residual '
                   f'{result["median_projected_error_m"]} m, maximum residual '
                   f'{result["maximum_projected_error_m"]} m. The prior camera-registration '
                   f'maximum was {result["maximum_registered_static_shift_px"]} px.')
    else:
        summary = '**Status:** awaiting twelve source-only landmark decisions on two S1 P6 frames.'
    REPORT.write_text('\n'.join([
        '# S1 P6 out-of-point court calibration check', '',
        'The [frozen protocol](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_calibration_review/protocol.json) '
        'tests the previously fitted S3 P34 refined transform on unboxed S1 P6 frames 1759 and 1783. '
        'The transform hash and a 0.2 m maximum landmark residual rule were frozen before these new '
        'clicks. All twelve landmarks must be visible and marked, with no more than 2 px prior static '
        'camera-registration shift. The same reviewer has seen earlier tracking and calibration work.', '',
        summary, '',
        ('The passed screen supports this transform as an operational court mapping across these '
         'checked source points. ' if result.get('operational_screen_passed') else
         'A passing screen would support this transform as an operational court mapping across '
         'these checked source points. ') +
        'It does not validate a true player floor point, repair the final airborne '
        'S1 P6 sample, certify all intervening identities, or establish an outcome association. '
        'The [machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_calibration_review/score.json) '
        'retains the decision and input hashes.', '',
        'Reproduce with `.\\.venv\\Scripts\\python.exe scripts/score_u5_s1p6_calibration_check.py`.',
    ]) + '\n', encoding='utf-8')
    print(result['status'])


if __name__ == '__main__':
    main()
