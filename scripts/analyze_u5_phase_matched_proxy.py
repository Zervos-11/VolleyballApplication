"""Exploratory set-and-phase matched box-bottom geometry for frozen points.

This is an availability-selected single-frame diagnostic. It is deliberately
separate from the strict six-player court-trajectory result.
"""

import hashlib
import itertools
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PATHS = {
    'snapshot': BASE / 'image_plane_snapshot_screen.json',
    'phase': BASE / 'snapshot_phase_balance_audit.json',
    'original': BASE / 'selected_floor_qc/index.json',
    'highres': BASE / 'zero_run_high_res_detection/index.json',
    'highres_qc': BASE / 'zero_run_high_res_source_qc.json',
    'calibration': BASE / 'near_court_candidate.json',
    'heldout_error': BASE / 'heldout_box_floor_error.json',
}
OUT = BASE / 'phase_matched_proxy_diagnostic.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_PHASE_MATCHED_PROXY.md'
METRICS = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')
LABELS = {'mean_pairwise_spacing_m': 'Mean pairwise spacing (m)',
          'convex_hull_area_m2': 'Convex hull area (m^2)',
          'centroid_dispersion_m': 'Centroid dispersion (m)'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(bbox, h):
    x = (bbox[0] + bbox[2]) / 2
    y = bbox[3]
    den = h[2][0] * x + h[2][1] * y + h[2][2]
    return [(h[0][0] * x + h[0][1] * y + h[0][2]) / den,
            (h[1][0] * x + h[1][1] * y + h[1][2]) / den]


def stat(rows, metric, labels=None):
    groups = defaultdict(lambda: [[], []])
    for i, row in enumerate(rows):
        won = labels[i] if labels is not None else row['near_team_won']
        groups[(row['set'], row['phase'])][int(won)].append(row['proxy_metrics'][metric])
    diffs = [statistics.mean(wins) - statistics.mean(losses)
             for losses, wins in groups.values() if wins and losses]
    return statistics.mean(diffs) if diffs else None


def exact_permutation(rows, metric):
    cells = defaultdict(list)
    for i, row in enumerate(rows):
        cells[(row['set'], row['phase'])].append(i)
    cells = list(cells.values())
    choices = [list(itertools.combinations(indices,
                                           sum(rows[i]['near_team_won'] for i in indices)))
               for indices in cells]
    observed = stat(rows, metric)
    values = []
    for assignment in itertools.product(*choices):
        winners = set(itertools.chain.from_iterable(assignment))
        values.append(stat(rows, metric, [i in winners for i in range(len(rows))]))
    return {'observed_equal_cell_win_minus_loss': round(observed, 4),
            'conditional_label_assignments': len(values),
            'two_sided_reference_fraction': round(
                sum(abs(value) >= abs(observed) - 1e-10 for value in values) / len(values), 4)}


def main():
    data = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in PATHS.items()}
    source = data['snapshot']['source_sha256']
    assert all(d['source_sha256'] == source for name, d in data.items()
               if 'source_sha256' in d)
    assert data['phase']['input_sha256']['image_plane_snapshot_screen'] == sha(PATHS['snapshot'])
    assert data['snapshot']['input_sha256']['local_boxes'] == sha(PATHS['original'])
    assert data['snapshot']['input_sha256']['highres_boxes'] == sha(PATHS['highres'])
    assert data['highres_qc']['detection_index_sha256'] == sha(PATHS['highres'])
    h = data['calibration']['homography_image_to_court']
    assert data['calibration']['points_court_m'] == [[0, 0], [9, 0], [9, 9], [0, 9]]
    original = {(r['set'], r['point_number']): r for r in data['original']['entries']}
    highres = {(r['set'], r['point_number']): r for r in data['highres']['entries']}
    high_qc = {(r['set'], r['point_number']): r for r in data['highres_qc']['rows']}
    phases = {(r['set'], r['point_number']): r for r in data['phase']['rows']}
    all_rows = []
    for snapshot in data['snapshot']['rows']:
        key = snapshot['set'], snapshot['point_number']
        phase = phases[key]
        assert snapshot['source_frame'] == phase['source_frame']
        if snapshot['detector_pass'] == 'original':
            entry = original[key]
            assert entry['source_frame'] == snapshot['source_frame']
            points = [b['box_bottom_court_m'] for b in entry['boxes']]
            # Check the stored metric coordinates against the calibration itself.
            assert all(math.dist(point, project(b['bbox_px'], h)) < .003
                       for point, b in zip(points, entry['boxes']))
        else:
            entry = highres[key]
            review = high_qc[key]
            assert entry['rows'][0]['source_frame'] == review['source_frame'] == snapshot['source_frame']
            proposals = entry['rows'][0]['broad_person_proposals']
            points = [project(proposals[i]['bbox_px'], h)
                      for i in review['accepted_near_team_proposal_indices']]
        assert len(points) == 6
        inside = all(-.05 <= v <= 9.05 for p in points for v in p)
        result = metrics([tuple(p) for p in points])
        all_rows.append({'set': key[0], 'point_number': key[1],
                         'near_team_won': snapshot['near_team_won'],
                         'source_frame': snapshot['source_frame'],
                         'detector_pass': snapshot['detector_pass'],
                         'phase': phase['phase'],
                         'box_bottom_court_proxy_m': [[round(v, 3) for v in p] for p in points],
                         'all_box_bottom_proxies_within_near_court': inside,
                         'proxy_metrics': {name: round(result[name], 4) for name in METRICS},
                         'ground_positions_validated': False})
    assert len(all_rows) == 17
    groups = defaultdict(list)
    for r in all_rows:
        groups[(r['set'], r['phase'])].append(r)
    matched_keys = {key for key, rows in groups.items()
                    if key[1] != 'serve_or_reset' and any(r['near_team_won'] for r in rows)
                    and any(not r['near_team_won'] for r in rows)}
    matched = [r for r in all_rows if (r['set'], r['phase']) in matched_keys]
    assert len(matched) == 13 and len(matched_keys) == 5
    comparison = {name: exact_permutation(matched, name) for name in METRICS}
    # A bounded sensitivity probe uses the largest observed clear-shoe discrepancy.
    # It is not a proven error bound and cannot represent airborne cases.
    radius = data['heldout_error']['summary']['maximum_box_to_shoe_distance_m']
    rng = random.Random(20261102)
    draws = {name: [] for name in METRICS}
    for _ in range(2000):
        shifted = []
        for row in matched:
            pts = []
            for x, y in row['box_bottom_court_proxy_m']:
                angle = rng.uniform(0, 2 * math.pi)
                distance = radius * math.sqrt(rng.random())
                pts.append((x + distance * math.cos(angle),
                            y + distance * math.sin(angle)))
            values = metrics(pts)
            shifted.append({**row, 'proxy_metrics': values})
        for name in METRICS:
            draws[name].append(stat(shifted, name))
    sensitivity = {name: {'minimum': round(min(values), 4),
                          'maximum': round(max(values), 4),
                          'fraction_positive': round(sum(v > 0 for v in values) / len(values), 4)}
                   for name, values in draws.items()}
    original_matched = [r for r in matched if r['detector_pass'] == 'original']
    assert len(original_matched) == 12
    original_only = {name: exact_permutation(original_matched, name) for name in METRICS}
    summary = {'frozen_points': 18, 'snapshots_with_six_boxes': 17,
               'phase_matched_open_play_snapshots': 13,
               'phase_matched_cells': 5,
               'serve_or_reset_excluded': 2,
               'unmatched_phase_excluded': 2,
               'missing_six_box_point': {'set': 3, 'point_number': 23, 'near_team_won': True},
               'matched_rows_inside_near_court_proxy': sum(r['all_box_bottom_proxies_within_near_court']
                                                            for r in matched),
               'validated_trajectories': 0,
               'validated_outcome_metrics': 0}
    out = {'status': 'exploratory_phase_matched_single_frame_floor_proxy_not_contract_outcome_result',
           'source_sha256': source,
           'input_sha256': {name: sha(path) for name, path in PATHS.items()},
           'summary': summary, 'equal_cell_comparison': comparison,
           'original_pass_only_comparison': original_only,
           'proxy_perturbation_scenario': {'radius_m': radius, 'draws': 2000,
                                          'results': sensitivity},
           'matched_set_phase_cells': [{'set': key[0], 'phase': key[1],
                                        'wins': sum(r['near_team_won'] for r in groups[key]),
                                        'losses': sum(not r['near_team_won'] for r in groups[key])}
                                       for key in sorted(matched_keys)],
           'rows': all_rows,
           'interpretation': ('One box-bottom proxy snapshot per available point. The reference fraction '
                              'enumerates outcome-label permutations within set and coarse phase, but '
                              'availability selection, small cells, unvalidated ground points and lack '
                              'of temporal trajectories preclude inferential winner claims. The position '
                              'perturbation radius is an observed clear-shoe discrepancy, not a bound.')}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Phase-matched court-proxy diagnostic', '',
             'This [source-bound analysis](../data/matches/yt_u5HnY2aNW14/screening/phase_matched_proxy_diagnostic.json) '
             'projects the bottom centre of six locally source-checked player boxes through the '
             'staged 9 m court transform. These are **approximate floor-plane proxies at one frame '
             'per point**, not verified shoe contacts or player trajectories. The separately '
             '[reviewed phase tags](HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md) restrict the calculation '
             'to open-play set-by-phase cells that contain both outcomes.', '',
             f"The frozen denominator is **18** points. There are 17 correct six-box snapshots, "
             f"of which {len(matched)} fall in {len(matched_keys)} comparable set-by-phase cells. "
             'Two serve/reset frames and two set-two defensive losses lack a within-cell '
             'counterpart; one set-three win has no six-box snapshot. None is silently replaced. '
             'One recovered set-one player projects 0.158 m beyond the sideline; court-relative '
             'coordinates can extend beyond painted court bounds during play. The convex hull '
             'is calculated from all six proxies and is not clipped to the painted 9 m square.', '',
             '| Court proxy | Equal-cell mean win minus loss | Two-sided conditional label reference | '
             'Observed-error perturbation range |',
             '| --- | ---: | ---: | ---: |']
    for name in METRICS:
        c = comparison[name]
        s = sensitivity[name]
        lines.append(f"| {LABELS[name]} | {c['observed_equal_cell_win_minus_loss']:+.3f} | "
                     f"{c['two_sided_reference_fraction']:.3f} ({c['conditional_label_assignments']} assignments) | "
                     f"{s['minimum']:+.3f} to {s['maximum']:+.3f} |")
    lines += ['', '## Detector-pass sensitivity', '',
              'Removing the one higher-resolution recovered snapshot in the matched group '
              'leaves 12 original-pass snapshots across the same five set-and-phase cells. '
              'The second higher-resolution recovery was a serve and was already excluded.', '',
              '| Court proxy | All 13 matched snapshots | Original-pass 12 only |',
              '| --- | ---: | ---: |']
    for name in METRICS:
        lines.append(f"| {LABELS[name]} | "
                     f"{comparison[name]['observed_equal_cell_win_minus_loss']:+.3f} | "
                     f"{original_only[name]['observed_equal_cell_win_minus_loss']:+.3f} |")
    lines += ['', 'The conditional reference enumerates all assignments of the observed number '
              'of wins within each set-and-phase cell. It is **not a valid confirmatory p-value**: '
              'the snapshots were selected where detector boxes were available, within-cell '
              'outcome exchangeability is unestablished, one winning point is missing, and the cells have only one or '
              'two observations per outcome. The last column perturbs each proxy by up to the '
              f'observed clear-shoe maximum of {radius:.3f} m across 2,000 seeded draws. It is a '
              'scenario range, not a confidence interval or guaranteed error bound, and does not '
              'cover airborne posture bias.', '',
              '**Conclusion:** This is the strongest reproducible *single-frame* court-proxy '
              'comparison presently available from the frozen sample. It cannot satisfy the '
              'signed requirement for validated trajectories, movement/transition measures or '
              'a reliable statistical outcome association. The strict court-metric result '
              'remains zero eligible points.', '',
              'Reproduce with `python scripts/analyze_u5_phase_matched_proxy.py` after the '
              'snapshot and phase audits.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)
    print(comparison)


if __name__ == '__main__':
    main()
