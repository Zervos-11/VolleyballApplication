"""Measure sensitivity of source-reviewed single-frame box metrics to anchor error.

This is a diagnostic on 15 locally reviewed six-box snapshots. It is not a
rally-level outcome comparison, and random perturbations are not confidence
intervals or an empirically validated error distribution.
"""
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PATHS = {
    'review': SCREEN / 'bracketed_candidate_source_qc.json',
    'crops': SCREEN / 'selected_floor_qc/index.json',
    'floor_reference': SCREEN / 'floor_proxy_reference_audit.json',
    'heldout_reference': SCREEN / 'heldout_box_floor_error.json',
    'runs': SCREEN / 'interior_identity_run_availability.json',
    'visibility': SCREEN / 'source_visibility_ledger.json',
}
OUT = SCREEN / 'selected_proxy_sensitivity.json'
METRIC_NAMES = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')
N_DRAWS = 2000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[round(fraction * (len(ordered) - 1))]


def main():
    data = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in PATHS.items()}
    review = data['review']
    crops = data['crops']
    floor = data['floor_reference']
    heldout = data['heldout_reference']
    assert crops['bracketed_source_qc_sha256'] == sha(PATHS['review'])
    assert data['visibility']['input_sha256']['local_boxes'] == sha(PATHS['review'])
    assert data['visibility']['input_sha256']['runs'] == sha(PATHS['runs'])
    assert review['summary']['reviewed_local_frames'] == len(crops['entries']) == 15
    assert floor['summary']['reviewed_grounded_boxes'] == 9
    assert heldout['summary']['reviewed_clear_grounded_shoe_pairs'] == 21
    radius = max(floor['summary']['maximum_box_bottom_to_shoe_midpoint_m'],
                 heldout['summary']['maximum_box_to_shoe_distance_m'])
    roster = {(p['set'], p['point_number']): p for p in data['runs']['points']}
    reviewed = {(p['set'], p['point_number']): p for p in review['rows']}
    rng = random.Random(20261102)
    rows = []
    for entry in crops['entries']:
        key = entry['set'], entry['point_number']
        assert reviewed[key]['source_frame'] == entry['source_frame']
        assert len(entry['boxes']) == 6
        points = [tuple(box['box_bottom_court_m']) for box in entry['boxes']]
        if not all(0 <= v <= 9 for point in points for v in point):
            raise ValueError(f'Box-bottom coordinate outside 9 m near court at {key}')
        base = metrics(points)
        samples = {name: [] for name in METRIC_NAMES}
        for _ in range(N_DRAWS):
            # Independent direction and radius ≤ the largest observed discrepancy.
            # Clipping keeps simulated positions within the mapped near court.
            shifted = []
            for x, y in points:
                angle = rng.uniform(0, 2 * math.pi)
                distance = radius * math.sqrt(rng.random())
                shifted.append((min(9, max(0, x + distance * math.cos(angle))),
                                min(9, max(0, y + distance * math.sin(angle)))))
            trial = metrics(shifted)
            for name in METRIC_NAMES:
                samples[name].append(trial[name])
        rows.append({
            'set': key[0], 'point_number': key[1], 'source_frame': entry['source_frame'],
            'near_team_won': roster[key]['near_team_won'],
            'source_team_membership': 'six_correct_near_side_teammates_single_instant',
            'grounded_position_validation': 'not_validated',
            'box_bottom_snapshot_metrics': {name: round(base[name], 3) for name in METRIC_NAMES},
            'perturbation_p05_p95': {name: [round(percentile(samples[name], .05), 3),
                                             round(percentile(samples[name], .95), 3)]
                                     for name in METRIC_NAMES},
            'perturbation_max_absolute_change': {name: round(max(abs(v - base[name])
                                                             for v in samples[name]), 3)
                                                 for name in METRIC_NAMES},
        })
    wins = [r for r in rows if r['near_team_won']]
    losses = [r for r in rows if not r['near_team_won']]
    summary = {'source_reviewed_snapshot_points': len(rows),
               'near_team_win_snapshots': len(wins), 'near_team_loss_snapshots': len(losses),
               'frozen_points_without_local_six_box_snapshot': 3,
               'validated_grounded_metric_frames': 0,
               'perturbation_radius_m': radius, 'perturbation_draws_per_frame': N_DRAWS,
               'source_reference_boxes_for_radius': (floor['summary']['reviewed_grounded_boxes'] +
                                                     heldout['summary']['reviewed_clear_grounded_shoe_pairs'])}
    for name in METRIC_NAMES:
        summary[f'median_snapshot_{name}_by_near_team_outcome'] = {
            'win': round(statistics.median(r['box_bottom_snapshot_metrics'][name] for r in wins), 3),
            'loss': round(statistics.median(r['box_bottom_snapshot_metrics'][name] for r in losses), 3),
        }
        summary[f'median_perturbation_p05_p95_width_{name}'] = round(statistics.median(
            r['perturbation_p05_p95'][name][1] - r['perturbation_p05_p95'][name][0]
            for r in rows), 3)
    OUT.write_text(json.dumps({
        'status': 'single_frame_proxy_sensitivity_not_rally_outcome_analysis',
        'source_sha256': review['source_sha256'],
        'input_sha256': {key: sha(path) for key, path in PATHS.items()},
        'summary': summary, 'rows': rows,
        'interpretation': ('One locally source-reviewed frame per available point. The perturbation radius is the '
                           'largest discrepancy among 30 clear-shoe examples, not a validated bound. '
                           'The perturbation envelope probes sensitivity only; it is not an uncertainty interval. '
                           'No serving/ground state or full analysis interval is certified for these 15 frames. '
                           'Do not use the winner medians for inference or as the final contract result.'),
    }, indent=2) + '\n', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
