"""Descriptive S1 P6 sample metrics after the frozen out-of-point court check.

This is an exploratory comparison of clicked shoes and reviewed box bottoms.
It does not promote the operational calibration screen to strict metric approval.
"""

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SOURCE = SCREEN / 's1p6_fixed_window_source_review'
CALIBRATION = SCREEN / 's1p6_fixed_window_calibration_review'
TRANSFORM = SCREEN / 's3p34_calibration_review/refined_candidate.json'
OUT = SOURCE / 'calibrated_sample_diagnostic.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S1P6_CALIBRATED_SAMPLES.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(matrix, point):
    result = cv2.perspectiveTransform(
        np.asarray([[point]], dtype=np.float64), matrix)[0, 0]
    return (float(result[0]), float(result[1]))


def main():
    score = json.loads((CALIBRATION / 'score.json').read_text(encoding='utf-8'))
    transform = json.loads(TRANSFORM.read_text(encoding='utf-8'))
    ledger = json.loads((SOURCE / 'box_and_floor_ledger.json').read_text(encoding='utf-8'))
    manifest = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
    assert score['operational_screen_passed'] is True
    assert score['strict_metric_approval'] is False
    assert score['candidate_transform_sha256'] == sha(TRANSFORM)
    assert score['input_sha256']['completed_form'] == sha(CALIBRATION / 'completed.csv')
    assert ledger['input_sha256']['source_review'] == sha(SOURCE / 'completed.csv')
    assert ledger['input_sha256']['paired_review'] == sha(SOURCE / 'paired_completed.csv')
    with (SOURCE / 'completed.csv').open(newline='', encoding='utf-8') as handle:
        source_rows = {(int(row['source_frame']), int(row['slot'])): row
                       for row in csv.DictReader(handle)}
    assert len(source_rows) == 30
    assert all(row['ground_status'] in ('grounded', 'airborne')
               for row in source_rows.values())
    matrix = np.asarray(transform['homography_image_to_court'], dtype=np.float64)
    frame_by_number = {row['source_frame']: row for row in ledger['rows']}
    rows = []
    all_position_errors = []
    for frame in manifest['five_sample_frames']:
        source_points = []
        proxy_points = []
        players = []
        for player in frame_by_number[frame]['players']:
            slot = player['slot']
            source = source_rows[(frame, slot)]
            accepted = (source['ground_status'] == 'grounded' and
                        player['reviewed_shoe_px'] is not None and
                        player['reviewed_grounded_box_bottom_proxy_px'] is not None)
            if accepted:
                shoe = project(matrix, player['reviewed_shoe_px'])
                proxy = project(matrix, player['reviewed_grounded_box_bottom_proxy_px'])
                difference = math.dist(shoe, proxy)
                source_points.append(shoe)
                proxy_points.append(proxy)
                all_position_errors.append(difference)
            else:
                shoe = proxy = difference = None
            players.append({'slot': slot, 'source_ground_status': source['ground_status'],
                            'manual_shoe_court_m': shoe, 'box_bottom_proxy_court_m': proxy,
                            'proxy_minus_shoe_distance_m': difference})
        complete = len(source_points) == len(proxy_points) == 6
        manual = metrics(source_points) if complete else None
        proxy = metrics(proxy_points) if complete else None
        difference = {key: proxy[key] - manual[key] for key in manual} if complete else None
        rows.append({'source_frame': frame, 'accepted_grounded_slots': len(source_points),
                     'complete_six_grounded': complete, 'manual_shoe_metrics': manual,
                     'box_bottom_proxy_metrics': proxy, 'proxy_minus_manual_metrics': difference,
                     'proxy_positions_outside_0_to_9_m': sum(
                         any(not 0 <= coordinate <= 9 for coordinate in point)
                         for point in proxy_points), 'players': players})
    complete_rows = [row for row in rows if row['complete_six_grounded']]
    assert len(complete_rows) == 4 and len(all_position_errors) == 28
    metric_names = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')
    summary = {
        'planned_sample_frames': len(rows),
        'source_state_reviewed_sample_frames': len(rows),
        'complete_six_grounded_frames': len(complete_rows),
        'team_metric_null_frames_due_to_observed_airborne_state': len(rows) - len(complete_rows),
        'accepted_player_positions': len(all_position_errors),
        'median_player_proxy_minus_shoe_distance_m': statistics.median(all_position_errors),
        'maximum_player_proxy_minus_shoe_distance_m': max(all_position_errors),
        'manual_shoe_four_frame_median_metrics': {
            name: statistics.median(row['manual_shoe_metrics'][name] for row in complete_rows)
            for name in metric_names},
        'box_bottom_four_frame_median_metrics': {
            name: statistics.median(row['box_bottom_proxy_metrics'][name] for row in complete_rows)
            for name in metric_names},
    }
    output = {
        'status': 'exploratory_source_reviewed_sample_metric_diagnostic',
        'five_sample_player_state_record_complete': True,
        'full_25_frame_player_state_review_complete': False,
        'calibration_operational_screen_passed': True,
        'strict_metric_approval': False,
        'input_sha256': {'calibration_score': sha(CALIBRATION / 'score.json'),
                         'source_review': sha(SOURCE / 'completed.csv'),
                         'paired_review': sha(SOURCE / 'paired_completed.csv'),
                         'box_and_floor_ledger': sha(SOURCE / 'box_and_floor_ledger.json'),
                         'transform': sha(TRANSFORM)},
        'summary': summary, 'frames': rows,
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# S1 P6 calibrated sampled-position diagnostic', '',
        'The [frozen out-of-point calibration screen](HONOURS_U5_S1P6_CALIBRATION_CHECK.md) '
        'passed on all 12 court landmarks (maximum residual 0.0506 m). The same reviewer '
        'marked the source intersections and player shoes; this is an operational mapping '
        'check, not independent physical ground truth or formal strict metric approval.', '',
        'All **five planned 5-Hz samples** have six source-reviewed player states. Four '
        'samples have six grounded shoe positions and paired same-player boxes, so their '
        'six-player floor geometry can be calculated. At the final sample, two blockers '
        'are observed airborne; their floor coordinates are structurally null and the '
        'six-player team metric is undefined there. This is a valid five-sample state '
        'record with four metric-eligible frames. The 20 intervening source frames have '
        'no per-frame ground-contact review, so this is not a certified 25-frame '
        'floor-position series.', '',
        '| Frame | Grounded slots | Shoe spacing (m) | Shoe hull (m²) | Shoe dispersion (m) | '
        'Proxy − shoe spacing (m) | Proxy − shoe hull (m²) | Proxy − shoe dispersion (m) |',
        '| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in rows:
        if row['complete_six_grounded']:
            m = row['manual_shoe_metrics']
            d = row['proxy_minus_manual_metrics']
            lines.append(
                f"| {row['source_frame']} | 6 | {m['mean_pairwise_spacing_m']:.3f} | "
                f"{m['convex_hull_area_m2']:.3f} | {m['centroid_dispersion_m']:.3f} | "
                f"{d['mean_pairwise_spacing_m']:+.3f} | {d['convex_hull_area_m2']:+.3f} | "
                f"{d['centroid_dispersion_m']:+.3f} |")
        else:
            lines.append(f"| {row['source_frame']} | {row['accepted_grounded_slots']} | "
                         '— | — | — | — | — | — |')
    lines += ['',
              f"Across 28 paired grounded positions, the median shoe-to-box-bottom court "
              f"distance is **{summary['median_player_proxy_minus_shoe_distance_m']:.3f} m** "
              f"and the largest observed distance is **{summary['maximum_player_proxy_minus_shoe_distance_m']:.3f} m**. "
              'These are same-reviewer, sampled proxy discrepancies. They do not measure '
              'position accuracy at unreviewed frames or bound future errors.', '',
              'At frame 1759, one reviewed grounded box-bottom proxy projects outside the '
              '0–9 m court square; the shoe point does not. The diagnostic retains that '
              'proxy for a transparent discrepancy comparison. It would fail the current '
              'strict calculator’s in-court coordinate gate. An airborne state is an '
              'observed state, not a tracking failure or a position to fill by holding '
              'the previous floor point.', '',
              'The [machine-readable diagnostic](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/calibrated_sample_diagnostic.json) '
              'contains all projected positions and input hashes. Reproduce with '
              '`.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s1p6_calibrated_samples.py`.',
              ]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"5/5 sampled states reviewed; {len(complete_rows)}/5 team-metric eligible; "
          f"median player proxy discrepancy {summary['median_player_proxy_minus_shoe_distance_m']:.3f} m")


if __name__ == '__main__':
    main()
