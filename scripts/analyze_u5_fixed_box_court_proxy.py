"""Exploratory court proxy from fixed-size translated player boxes."""

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
FILES = {
    'pilot': BASE / 'box_centre_flow_pilot.json',
    'review': BASE / 'flow_window_five_sample_audit.json',
    'geometry': BASE / 'flow_window_image_geometry.json',
    'calibration': BASE / 'near_court_candidate.json',
    'reference': BASE / 'heldout_box_floor_error.json',
}
OUT = BASE / 'fixed_box_court_proxy_pilot.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FIXED_BOX_COURT_PROXY.md'
FIELDS = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')
OFFSETS = (-12, -6, 0, 6, 12)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_xy(x, y, h):
    den = h[2][0]*x + h[2][1]*y + h[2][2]
    if abs(den) < 1e-12:
        raise ValueError('Point projects at infinity')
    return ((h[0][0]*x + h[0][1]*y + h[0][2])/den,
            (h[1][0]*x + h[1][1]*y + h[1][2])/den)


def fixed_bottom_at(player, frame):
    x1, _, x2, y2 = player['anchor_bbox_px']
    dx, dy = player['frames'][str(frame)]['translation_px']
    return ((x1+x2)/2+dx, y2+dy)


def equal_cell_difference(rows, field):
    groups = defaultdict(lambda: {True: [], False: []})
    for row in rows:
        groups[(row['set'], row['phase'])][row['near_team_won']].append(row['window_median'][field])
    eligible = [group for group in groups.values() if group[True] and group[False]]
    if not eligible:
        return None, 0
    return statistics.mean(statistics.mean(g[True])-statistics.mean(g[False])
                           for g in eligible), len(eligible)


def exact_label_reference(rows, field):
    cells = defaultdict(list)
    for i, row in enumerate(rows):
        cells[(row['set'], row['phase'])].append(i)
    choices = [list(itertools.combinations(indices,
                                           sum(rows[i]['near_team_won'] for i in indices)))
               for indices in cells.values()]
    observed, _ = equal_cell_difference(rows, field)
    values = []
    for assignment in itertools.product(*choices):
        winners = set(itertools.chain.from_iterable(assignment))
        relabelled = [{**row, 'near_team_won': i in winners} for i, row in enumerate(rows)]
        values.append(equal_cell_difference(relabelled, field)[0])
    return {'assignments': len(values),
            'two_sided_reference_fraction': round(sum(abs(v) >= abs(observed)-1e-12
                                                      for v in values)/len(values), 4)}


def main():
    data = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in FILES.items()}
    source = data['pilot']['source_sha256']
    assert source == data['review']['source_sha256'] == data['geometry']['source_sha256']
    assert source == data['reference']['source_sha256']
    assert data['review']['input_sha256']['image_geometry'] == sha(FILES['geometry'])
    assert data['review']['summary']['no_obvious_transfer_at_five_displayed_instants'] == 8
    assert data['calibration']['points_court_m'] == [[0, 0], [9, 0], [9, 9], [0, 9]]
    h = data['calibration']['homography_image_to_court']
    pilot = {(r['set'], r['point_number']): r for r in data['pilot']['rows']}
    geometry = {(r['set'], r['point_number']): r for r in data['geometry']['rows']}
    rows = []
    for review in data['review']['rows']:
        key = review['set'], review['point_number']
        assert review['visual_status'] == 'no_obvious_wrong_person_transfer_at_five_samples'
        candidate = pilot[key]
        assert candidate['all_six_tracked_at_all_five_samples']
        assert len(candidate['players']) == 6
        assert geometry[key]['source_window_frames'] == review['source_frames']
        frames = []
        paths = [[] for _ in range(6)]
        for offset in OFFSETS:
            frame = candidate['anchor_frame']+offset
            assert frame == review['source_frames'][OFFSETS.index(offset)]
            pixels = [fixed_bottom_at(player, frame) for player in candidate['players']]
            court = [project_xy(*point, h) for point in pixels]
            for path, point in zip(paths, court):
                path.append(point)
            values = metrics(court)
            frames.append({'source_frame': frame,
                           'fixed_box_bottom_px': [[round(x, 3), round(y, 3)] for x, y in pixels],
                           'court_proxy_m': [[round(x, 4), round(y, 4)] for x, y in court],
                           'six_inside_painted_court': all(0 <= x <= 9 and 0 <= y <= 9
                                                           for x, y in court),
                           'metrics': {field: round(values[field], 4) for field in FIELDS}})
        chords = [math.dist(path[0], path[-1]) for path in paths]
        polylines = [sum(math.dist(a, b) for a, b in zip(path, path[1:])) for path in paths]
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': candidate['near_team_won'],
                     'phase': geometry[key]['phase'], 'detector_pass': candidate['detector_pass'],
                     'player_keys': [p['anchor_player_key'] for p in candidate['players']],
                     'source_frames': review['source_frames'],
                     'window_median': {field: round(statistics.median(f['metrics'][field]
                                                                     for f in frames), 4)
                                       for field in FIELDS},
                     'median_player_endpoint_chord_m': round(statistics.median(chords), 4),
                     'median_player_sampled_polyline_m': round(statistics.median(polylines), 4),
                     'all_frames_six_inside_painted_court': all(f['six_inside_painted_court']
                                                                for f in frames),
                     'frames': frames})
    rows.sort(key=lambda r: (r['set'], r['point_number']))
    assert len(rows) == 8 and sum(r['near_team_won'] for r in rows) == 4
    baseline = {}
    for field in FIELDS:
        value, cells = equal_cell_difference(rows, field)
        assert cells == 3
        baseline[field] = {'equal_cell_win_minus_loss': round(value, 4),
                           **exact_label_reference(rows, field)}
    deletion = {}
    for field in FIELDS:
        values = [equal_cell_difference([r for r in rows if r is not dropped], field)[0]
                  for dropped in rows]
        deletion[field] = {'minimum': round(min(values), 4), 'maximum': round(max(values), 4)}
    movement_fields = ('median_player_endpoint_chord_m', 'median_player_sampled_polyline_m')
    movement_comparison = {}
    for field in movement_fields:
        motion_rows = [{**row, 'window_median': {field: row[field]}} for row in rows]
        value, cells = equal_cell_difference(motion_rows, field)
        assert cells == 3
        leave_one = [equal_cell_difference([r for r in motion_rows if r is not dropped], field)[0]
                     for dropped in motion_rows]
        movement_comparison[field] = {
            'equal_cell_win_minus_loss_m': round(value, 4),
            'one_point_deletion_minimum_m': round(min(leave_one), 4),
            'one_point_deletion_maximum_m': round(max(leave_one), 4),
            **exact_label_reference(motion_rows, field)}
    radius = data['reference']['summary']['maximum_box_to_shoe_distance_m']
    rng = random.Random(20261102)
    draws = {field: [] for field in FIELDS}
    for _ in range(1000):
        changed = []
        for row in rows:
            samples = []
            for frame in row['frames']:
                shifted = []
                for x, y in frame['court_proxy_m']:
                    angle = rng.uniform(0, 2*math.pi)
                    length = radius*math.sqrt(rng.random())
                    shifted.append((x+length*math.cos(angle), y+length*math.sin(angle)))
                samples.append(metrics(shifted))
            changed.append({**row, 'window_median': {field: statistics.median(s[field]
                                                                            for s in samples)
                                                    for field in FIELDS}})
        for field in FIELDS:
            draws[field].append(equal_cell_difference(changed, field)[0])
    scenario = {field: {'minimum': round(min(values), 4),
                        'maximum': round(max(values), 4),
                        'fraction_positive': round(sum(v > 0 for v in values)/len(values), 4)}
                for field, values in draws.items()}
    summary = {'frozen_points': 18, 'candidate_windows': 8, 'wins': 4, 'losses': 4,
               'matched_set_phase_cells': 3, 'source_frame_instances': 40,
               'candidate_player_positions': 240,
               'windows_with_six_proxies_inside_painted_court': sum(
                   r['all_frames_six_inside_painted_court'] for r in rows),
               'clear_shoe_reference_pairs': data['reference']['summary']['reviewed_clear_grounded_shoe_pairs']
                                             + data['reference']['summary']['earlier_clear_shoe_reference_boxes'],
               'independently_validated_dynamic_floor_positions': 0}
    out = {'status': 'exploratory_fixed_box_court_proxy_not_confirmatory',
           'source_sha256': source, 'input_sha256': {key: sha(path) for key, path in FILES.items()},
           'method': {'box': 'anchor dimensions fixed; optical-flow translation moves bottom centre',
                      'court': 'staged near-court 9 m floor homography',
                      'sample_offsets_frames': list(OFFSETS), 'sample_rate_hz': 5,
                      'position_status': 'proxy; pose and airborne motion can bias floor location'},
           'summary': summary, 'baseline': baseline, 'one_point_deletion': deletion,
           'movement_proxy_comparison': movement_comparison,
           'observed_clear_shoe_error_scenario': {'radius_m': radius, 'draws': 1000,
                                                  'results': scenario},
           'rows': rows,
           'interpretation': ('Fixed-size boxes provide a reproducible approximate court path. '
                              'Thirty clear-shoe references concern related static box-bottom error, '
                              'not dynamic propagated error. These eight windows were selected by '
                              'tracking availability, and full-window phase and floor positions '
                              'are not independently certified. Contrasts are exploratory only.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Fixed-box court-position proxy pilot', '',
             'This [source-bound pilot](../data/matches/yt_u5HnY2aNW14/screening/fixed_box_court_proxy_pilot.json) '
             'implements the proposed fixed-size player box. Each reviewed anchor box keeps its '
             'dimensions; optical flow translates its centre and its bottom-centre image point '
             'together. A staged 9 m floor homography maps that point to **approximate court '
             'metres**. The resulting paths are position proxies, not literal foot trajectories. '
             'The [five-instant source review](HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) found '
             'no obvious wrong-person transfer at the displayed samples.', '',
             '![Eight short approximate court paths](figures/u5_fixed_box_court_proxy_paths.png)', '',
             'The [print-ready figure](figures/u5_fixed_box_court_proxy_paths.pdf) shows '
             'five samples per player in each window. Open circles mark the first sample '
             'and crosses the last; these are fixed-box proxies, not manually marked feet.', '',
             'The frozen sample contains 18 points. This pilot covers eight 0.8 s windows '
             '(four wins and four losses), three matched set-and-phase cells, 40 team-frame '
             'samples and 240 player-position proxies. '
             + str(summary['windows_with_six_proxies_inside_painted_court'])
             + '/8 windows keep all six proxy positions inside the painted near-court square '
             'at every sample. Positions outside the lines are flagged and retained, not clamped.', '',
             '| Metric | Win minus loss | One-point deletion range | Observed-error scenario range |',
             '| --- | ---: | ---: | ---: |']
    labels = {'mean_pairwise_spacing_m': 'Mean pairwise spacing (m)',
              'convex_hull_area_m2': 'Formation hull area (m^2)',
              'centroid_dispersion_m': 'Centroid dispersion (m)'}
    for field in FIELDS:
        b, d, p = baseline[field], deletion[field], scenario[field]
        lines.append(f"| {labels[field]} | {b['equal_cell_win_minus_loss']:+.3f} | "
                     f"{d['minimum']:+.3f} to {d['maximum']:+.3f} | "
                     f"{p['minimum']:+.3f} to {p['maximum']:+.3f} |")
    lines += ['', '| Short-window movement proxy | Win minus loss | One-point deletion range |',
              '| --- | ---: | ---: |']
    for field, label in [('median_player_endpoint_chord_m', 'Median player first-to-last chord (m)'),
                         ('median_player_sampled_polyline_m', 'Median player sampled polyline (m)')]:
        c = movement_comparison[field]
        lines.append(f"| {label} | {c['equal_cell_win_minus_loss_m']:+.3f} | "
                     f"{c['one_point_deletion_minimum_m']:+.3f} to "
                     f"{c['one_point_deletion_maximum_m']:+.3f} |")
    lines += ['', 'The JSON also records the within-cell exact label reference (18 possible '
              'assignments). This is **not a confirmatory p-value** because windows were '
              'selected by tracker availability. The error scenario shifts each proxy by '
              'up to the largest discrepancy in the earlier static clear-shoe reference '
              '(0.632 m) over 1,000 seeded draws; that observed value is not a bound for '
              'jumps or low posture. '
              'The 30 clear-shoe pairs assess related static box-bottom error. A subsequent '
              '[non-anchor audit](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) finds 11 clear '
              'pairs and a larger 0.729 m maximum; its '
              '[updated sensitivity scenario](HONOURS_U5_DYNAMIC_ERROR_SENSITIVITY.md) '
              'uses that observation. Neither reference establishes an error bound or '
              'complete dynamic accuracy. The sampled chord and polyline lengths describe the proxy '
              'path, not actual foot travel or step count.', '',
              'A [direct anchor-reference audit](HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md) '
              'joins 16 of these pilot player points to the existing manual clear-shoe '
              'marks. Two anchor frames have all six players labelled, enabling direct '
              'team-metric error checks. The non-anchor audit checks selected propagated '
              'positions, but has no full six-player reference frame.', '',
              'This is an operational prototype for RQ1/RQ2 and a descriptive, exploratory '
              'RQ3 comparison. It has no rotation metric or reliable performance effect. '
              'Posture, missingness and selection limits contribute to RQ4.', '',
              'Reproduce with `python scripts/analyze_u5_fixed_box_court_proxy.py` after '
              'the short-flow and five-instant source reviews.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)
    print({field: baseline[field]['equal_cell_win_minus_loss'] for field in FIELDS})


if __name__ == '__main__':
    main()
