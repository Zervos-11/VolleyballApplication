"""Audit a post-review S3 P34 court transform without approving final metrics."""

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
PACK = SCREEN / 's3p34_calibration_review'
GROUND = SCREEN / 's3p34_30fps_ground_review'
OUT = PACK / 'refined_candidate.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S3P34_REFINED_CALIBRATION_CANDIDATE.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(homography, xy):
    point = np.asarray([[xy]], dtype=np.float32)
    return cv2.perspectiveTransform(point, homography)[0, 0]


def main():
    protocol_path = PACK / 'protocol.json'
    completed_path = PACK / 'completed.csv'
    staged_path = SCREEN / 'near_court_candidate.json'
    ground_path = GROUND / 'single_reviewer_unsampled_completed.csv'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    staged = json.loads(staged_path.read_text(encoding='utf-8'))
    with completed_path.open(newline='', encoding='utf-8') as stream:
        marks = list(csv.DictReader(stream))
    assert len(marks) == 12
    assert [int(row['source_frame']) for row in marks] == [
        frame['frame'] for frame in protocol['frames'] for _ in protocol['landmarks']]
    assert [row['landmark_code'] for row in marks] == [
        landmark['code'] for _ in protocol['frames'] for landmark in protocol['landmarks']]
    assert all(row['status'] == 'marked' for row in marks)
    for row in marks:
        frame = next(item for item in protocol['frames'] if item['frame'] == int(row['source_frame']))
        assert row['image_sha256'] == frame['sha256'] == sha(GROUND / frame['image'])

    first_frame = protocol['frames'][0]['frame']
    fit_codes = ['baseline_left', 'baseline_right', 'net_right', 'net_left']
    by_frame = {str(frame['frame']): {
        row['landmark_code']: row for row in marks if int(row['source_frame']) == frame['frame']
    } for frame in protocol['frames']}
    fit_marks = by_frame[str(first_frame)]
    source = np.asarray([[float(fit_marks[code]['x_px']), float(fit_marks[code]['y_px'])]
                         for code in fit_codes], dtype=np.float32)
    target = np.asarray([[0, 0], [9, 0], [9, 9], [0, 9]], dtype=np.float32)
    refined = cv2.getPerspectiveTransform(source, target)
    old = np.asarray(staged['homography_image_to_court'], dtype=np.float64)

    comparisons = []
    for frame in protocol['frames']:
        for landmark in protocol['landmarks']:
            row = by_frame[str(frame['frame'])][landmark['code']]
            xy = [float(row['x_px']), float(row['y_px'])]
            predicted = project(refined, xy)
            comparison = {'source_frame': frame['frame'], 'landmark_code': landmark['code'],
                          'role': ('fitted_corner' if frame['frame'] == first_frame and
                                   landmark['code'] in fit_codes else 'held_out_check'),
                          'source_px': xy, 'target_court_m': landmark['court_m'],
                          'refined_projected_court_m': [round(float(v), 4) for v in predicted],
                          'refined_error_m': round(math.dist(predicted, landmark['court_m']), 4),
                          'staged_error_m': round(math.dist(project(old, xy),
                                                            landmark['court_m']), 4)}
            comparisons.append(comparison)
    held_out = [row['refined_error_m'] for row in comparisons if row['role'] == 'held_out_check']
    attack = [row['refined_error_m'] for row in comparisons if row['landmark_code'].startswith('attack_')]
    with ground_path.open(newline='', encoding='utf-8') as stream:
        ground_rows = list(csv.DictReader(stream))
    shifts = []
    for row in ground_rows:
        if row['shoe_midpoint_x_px'] and row['shoe_midpoint_y_px']:
            xy = [float(row['shoe_midpoint_x_px']), float(row['shoe_midpoint_y_px'])]
            shifts.append(math.dist(project(refined, xy), project(old, xy)))

    result = {
        'status': 'exploratory_post_review_refined_calibration_candidate',
        'source_frame_used_for_fit': first_frame,
        'fit_landmarks': fit_codes,
        'homography_image_to_court': refined.tolist(),
        'coordinate_rule': staged['coordinate_rule'],
        'strict_metric_approval': False,
        'use_for_final_metrics': False,
        'prior_frozen_operational_screen': 'failed_on_staged_transform_max_0.2037_m_vs_0.2_m',
        'input_sha256': {'protocol': sha(protocol_path), 'completed_marks': sha(completed_path),
                         'staged_transform': sha(staged_path), 'ground_review': sha(ground_path)},
        'held_out_count': len(held_out),
        'held_out_maximum_error_m': max(held_out),
        'attack_line_held_out_maximum_error_m': max(attack),
        'clicked_shoe_point_count': len(shifts),
        'old_to_refined_clicked_shoe_shift_median_m': round(statistics.median(shifts), 4),
        'old_to_refined_clicked_shoe_shift_maximum_m': round(max(shifts), 4),
        'comparisons': comparisons,
        'interpretation': ('Four first-frame corners were used for fitting. The other eight '
                           'source-image marks are holdout checks against this fitted transform, '
                           'but all marks come from one previously exposed reviewer and two '
                           'nearby frames. This refinement was made after seeing the frozen '
                           'staged-transform screen failure; its errors are diagnostic, not a '
                           'replacement prespecified test or independent physical validation.'),
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text('\n'.join([
        '# S3 P34 refined court calibration candidate', '',
        'The [frozen source-only review](HONOURS_U5_S3P34_CALIBRATION_REVIEW.md) marked 12/12 '
        'court-line intersections. Its predeclared operational screen **did not pass** for the '
        'original staged transform: one near-baseline/right-sideline mark missed the 0.200 m '
        'limit by 0.0037 m (maximum 0.2037 m). The two clicks on that landmark are only 0.58 px '
        'apart, while the second-frame residual is 0.1969 m. This tiny threshold crossing may '
        'reflect manual line-centre selection or the original manually chosen transform corners; '
        'the observations do not separate those causes. The original screen result is preserved.', '',
        f'A new candidate homography fits the four baseline and net-floor corners on source frame '
        f'{first_frame}. The other {len(held_out)} marks were not used to fit this candidate. '
        f'The largest held-out residual is **{max(held_out):.4f} m**, and the largest held-out '
        f'attack-line residual is **{max(attack):.4f} m**. The '
        '[machine-readable candidate](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/refined_candidate.json) '
        'stores the matrix, every residual and the source hashes.', '',
        f'At the {len(shifts)} clicked shoe points in the completed 30-fps ground review, '
        f'changing from the staged to this candidate mapping shifts a mapped coordinate by a '
        f'median **{statistics.median(shifts):.4f} m** and a maximum **{max(shifts):.4f} m**. '
        'Those are changes between transforms, not position errors against true floor locations.', '',
        'The net-floor line in these images is near source row 313, below the suspended net. '
        'A bright horizontal feature near row 200 is part of the net structure above the floor. '
        'The saved net-line clicks therefore follow the plausible floor feature. The four lines '
        'also retain similar geometry across the two reviewed frames.', '',
        '**Status:** exploratory calibration refinement only. The reviewer had seen an earlier '
        'calibration, the two frames are close in one point, and this fit was made after the '
        'original screen result was known. Neither transform is approved for final strict '
        'metre-valued metrics by this analysis. The fixed-window and full-rally gates remain open.', '',
        'Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s3p34_refined_calibration_candidate.py`.',
    ]) + '\n', encoding='utf-8')
    print(result['status'], result['held_out_maximum_error_m'])


if __name__ == '__main__':
    main()
