"""Measure disagreement between saved foot points and box-bottom centres."""
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SCAN = ROOT / 'data/processed/honours_saved_game_state_scan.json'
CAL = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration'
OUT = ROOT / 'data/processed/honours_box_bottom_disagreement.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_BOX_BOTTOM_DISAGREEMENT.md'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, q):
    return float(np.percentile(np.asarray(values, float), q)) if values else None


def summary(rows):
    pixels = [r['pixel_disagreement'] for r in rows]
    metres = [r['nominal_court_disagreement_m'] for r in rows
              if r['nominal_court_disagreement_m'] is not None]
    return {'pairs': len(rows), 'nominal_court_pairs': len(metres),
            'median_pixels': round(statistics.median(pixels), 3) if pixels else None,
            'p90_pixels': round(percentile(pixels, 90), 3) if pixels else None,
            'median_nominal_metres': round(statistics.median(metres), 3) if metres else None,
            'p90_nominal_metres': round(percentile(metres, 90), 3) if metres else None}


def main():
    audit, scan = read(AUDIT), read(SCAN)
    if audit['source_sha256'] != scan['source_sha256'] or scan['completed_audit_sha256'] != sha(AUDIT):
        raise ValueError('Saved frame and phase scan inputs disagree')
    phases = {(r['set'], r['point_number'], r['frame']): r for r in scan['rows']}
    matrices = {}
    for set_number in (1, 2, 3):
        path = CAL / ('camera_r1.json' if set_number == 1 else 'camera_r2_r5.json')
        camera = read(path)
        matrices[set_number] = cv2.getPerspectiveTransform(
            np.asarray(camera['points_px'], np.float32),
            np.asarray(camera['points_court_m'], np.float32))
    rows = []
    six_frame_comparison = []
    for point in audit['points']:
        path = ROOT / point['label_file']
        if sha(path) != point['label_sha256']:
            raise ValueError(f'Saved labels changed: {path}')
        saved = read(path)
        for number, frame in saved['frames'].items():
            key = point['set'], point['point_number'], int(number)
            phase = phases[key]
            if phase['source_review_phase'] == 'live_play' and len(frame['players']) == 6:
                players = frame['players']
                if all(p['position_status'] == 'visible' and p['footpoint'] is not None
                       and p['bbox'] is not None for p in players):
                    foot_array = np.asarray([p['footpoint'] for p in players], np.float32).reshape(-1, 1, 2)
                    proxy_array = np.asarray([[(p['bbox'][0] + p['bbox'][2]) / 2, p['bbox'][3]]
                                              for p in players], np.float32).reshape(-1, 1, 2)
                    foot_court = cv2.perspectiveTransform(foot_array, matrices[point['set']])[:, 0, :]
                    proxy_court = cv2.perspectiveTransform(proxy_array, matrices[point['set']])[:, 0, :]
                    if (np.isfinite(foot_court).all() and np.isfinite(proxy_court).all()
                            and ((foot_court >= 0) & (foot_court <= 9)).all()
                            and ((proxy_court >= 0) & (proxy_court <= 9)).all()):
                        foot_metrics = metrics([tuple(map(float, xy)) for xy in foot_court])
                        proxy_metrics = metrics([tuple(map(float, xy)) for xy in proxy_court])
                        six_frame_comparison.append({
                            'set': key[0], 'point_number': key[1], 'frame': key[2],
                            'saved_footpoint_metrics': {k: round(v, 4) for k, v in foot_metrics.items()},
                            'box_bottom_metrics': {k: round(v, 4) for k, v in proxy_metrics.items()},
                            'absolute_metric_differences': {k: round(abs(proxy_metrics[k] - v), 4)
                                                            for k, v in foot_metrics.items()}})
            for player in frame['players']:
                if player['position_status'] != 'visible' or player['footpoint'] is None or player['bbox'] is None:
                    continue
                box = player['bbox']
                proxy = ((box[0] + box[2]) / 2, box[3])
                foot = tuple(player['footpoint'])
                pixel_error = math.dist(proxy, foot)
                projected = cv2.perspectiveTransform(
                    np.asarray([[proxy, foot]], np.float32), matrices[point['set']])[0]
                nominal = (math.dist(projected[0], projected[1])
                           if np.isfinite(projected).all() and
                           ((projected >= 0) & (projected <= 9)).all() else None)
                rows.append({'set': key[0], 'point_number': key[1], 'frame': key[2],
                             'player_id': player['player_id'],
                             'source_review_phase': phase['source_review_phase'],
                             'navigation_play': phase['navigation_play'],
                             'box_bottom_centre_px': [round(v, 2) for v in proxy],
                             'saved_footpoint_px': foot,
                             'pixel_disagreement': round(pixel_error, 3),
                             'nominal_court_disagreement_m': round(nominal, 3) if nominal is not None else None})
    live = [r for r in rows if r['source_review_phase'] == 'live_play']
    result = {'status': 'proxy_vs_saved_click_disagreement_not_ground_truth_accuracy',
              'source_sha256': audit['source_sha256'], 'audit_sha256': sha(AUDIT),
              'phase_scan_sha256': sha(SCAN), 'all_visible_pairs': summary(rows),
              'source_reviewed_live_pairs': summary(live), 'rows': rows,
              'six_player_live_metric_comparison': six_frame_comparison,
              'limitations': ['Saved foot points are not independently validated ground truth.',
                              'A visible status may still include airborne or posture-sensitive cases.',
                              'Nominal metres depend on staged calibration and are only computed when both projections fall within 0-9m.',
                              'This measures method disagreement, not a box-bottom error bound.']}
    a, b = result['all_visible_pairs'], result['source_reviewed_live_pairs']
    metric_names = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')
    medians = {name: statistics.median(row['absolute_metric_differences'][name]
                                      for row in six_frame_comparison) if six_frame_comparison else None
               for name in metric_names}
    result['six_player_live_median_absolute_metric_difference'] = medians
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text(f'''# Saved foot-point versus box-bottom proxy disagreement

For each saved visible player with both a box and a foot-point marker, this [source-bound audit](../data/processed/honours_box_bottom_disagreement.json) compares the marker with the centre of the box's bottom edge. Both positions are projected through the staged court transform only when both remain inside its nominal 9 m square. The source-reviewed live subset uses the [phase audit](HONOURS_CANDIDATE_PHASE_QC.md).

| Subset | Player pairs | Median / 90th percentile image disagreement | In-court projected pairs | Median / 90th percentile nominal court disagreement |
| --- | ---: | ---: | ---: | ---: |
| All saved visible | {a['pairs']} | {a['median_pixels']:.1f} / {a['p90_pixels']:.1f} px | {a['nominal_court_pairs']} | {a['median_nominal_metres']:.2f} / {a['p90_nominal_metres']:.2f} m |
| Source-reviewed live frames | {b['pairs']} | {b['median_pixels']:.1f} / {b['p90_pixels']:.1f} px | {b['nominal_court_pairs']} | {b['median_nominal_metres']:.2f} / {b['p90_nominal_metres']:.2f} m |

These are **disagreements between two proposals**, not measured position errors: the saved foot clicks themselves were not independently ground-truthed, and some visible labels may include airborne or unusual posture. The metre figures also inherit staged-calibration uncertainty. A body/box centre remains appropriate as an explicitly image-plane movement proxy; box-bottom court metres should be released only after a small independent grounded reference check defines acceptable error.

On {len(six_frame_comparison)} source-reviewed live frames where all six saved markers **and** box-bottom proxies project inside the nominal court, changing the anchor changes the three provisional team measures by a median absolute **{medians['mean_pairwise_spacing_m']:.2f} m** in mean spacing, **{medians['convex_hull_area_m2']:.2f} m²** in hull area, and **{medians['centroid_dispersion_m']:.2f} m** in centroid dispersion. The frame-level comparisons are in the JSON. These differences quantify proxy sensitivity, not either method's accuracy.
''', encoding='utf-8')
    print('all', a, 'source-reviewed live', b)


if __name__ == '__main__':
    main()
