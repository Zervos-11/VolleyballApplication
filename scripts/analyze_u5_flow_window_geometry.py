"""Exploratory image-plane geometry in source-screened short flow windows."""

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PILOT = BASE / 'box_centre_flow_pilot.json'
AUDIT = BASE / 'box_centre_flow_audit.json'
OUT = BASE / 'flow_window_image_geometry.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FLOW_WINDOW_GEOMETRY.md'
METRIC_MAP = {
    'mean_pairwise_spacing_m': 'spacing_px',
    'convex_hull_area_m2': 'hull_area_px2',
    'centroid_dispersion_m': 'dispersion_px',
}
LABELS = {'spacing_px': 'Mean pairwise spacing (px)',
          'hull_area_px2': 'Convex hull area (px^2)',
          'dispersion_px': 'Centroid dispersion (px)'}
DELTAS = (-12, -6, 0, 6, 12)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contrast(rows, field, metric):
    groups = defaultdict(lambda: [[], []])
    for row in rows:
        groups[(row['set'], row['phase'])][int(row['near_team_won'])].append(row[field][metric])
    assert all(win and loss for loss, win in groups.values())
    return statistics.mean(statistics.mean(win)-statistics.mean(loss)
                           for loss, win in groups.values())


def main():
    pilot = json.loads(PILOT.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    assert audit['input_sha256']['pilot'] == sha(PILOT)
    assert pilot['source_sha256'] == audit['source_sha256']
    accepted = {(r['set'], r['point_number']): r for r in audit['rows']
                if r['endpoint_visual_status'] == 'no_obvious_wrong_person_transfer'
                and r['phase_at_anchor'] != 'serve_or_reset'}
    cells = defaultdict(lambda: {'wins': [], 'losses': []})
    for key, row in accepted.items():
        cells[(row['set'], row['phase_at_anchor'])]['wins' if row['near_team_won'] else 'losses'].append(key)
    matched = {key for key, row in accepted.items()
               if cells[(row['set'], row['phase_at_anchor'])]['wins']
               and cells[(row['set'], row['phase_at_anchor'])]['losses']}
    assert len(matched) == audit['summary']['visually_clear_open_play_set_phase_matched_windows'] == 8
    rows = []
    for candidate in pilot['rows']:
        key = candidate['set'], candidate['point_number']
        if key not in matched:
            continue
        assert candidate['all_six_tracked_at_all_five_samples']
        assert candidate['anchor_frame'] == accepted[key]['anchor_frame']
        samples = []
        for delta in DELTAS:
            frame_no = candidate['anchor_frame'] + delta
            positions = [tuple(p['frames'][str(frame_no)]['predicted_box_centre_px'])
                         for p in candidate['players']]
            assert len(positions) == 6
            values = metrics(positions)
            samples.append({'source_frame': frame_no, 'offset_frames': delta,
                            'metrics': {renamed: round(values[original], 3)
                                        for original, renamed in METRIC_MAP.items()}})
        polylines = []
        for player in candidate['players']:
            points = [player['frames'][str(candidate['anchor_frame']+delta)]['predicted_box_centre_px']
                      for delta in DELTAS]
            polylines.append(sum(math.dist(a, b) for a, b in zip(points, points[1:])))
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': candidate['near_team_won'],
                     'phase': candidate['phase'],
                     'detector_pass': candidate['detector_pass'],
                     'source_window_frames': [candidate['anchor_frame']+d for d in DELTAS],
                     'median_image_metrics': {metric: round(statistics.median(
                         s['metrics'][metric] for s in samples), 3)
                         for metric in METRIC_MAP.values()},
                     'anchor_image_metrics': samples[2]['metrics'],
                     'median_six_player_sampled_polyline_px': round(statistics.median(polylines), 2),
                     'samples': samples,
                     'source_screen_status': 'no_obvious_wrong_person_transfer_at_displayed_endpoints',
                     'named_identity_and_floor_status': 'not_validated'})
    rows.sort(key=lambda r: (r['set'], r['point_number']))
    assert len(rows) == 8 and sum(r['near_team_won'] for r in rows) == 4
    comparisons = {}
    for metric in METRIC_MAP.values():
        median_result = contrast(rows, 'median_image_metrics', metric)
        anchor_result = contrast(rows, 'anchor_image_metrics', metric)
        offset_results = []
        for index, delta in enumerate(DELTAS):
            at_offset = [{**r, 'offset_metrics': r['samples'][index]['metrics']} for r in rows]
            offset_results.append({'offset_frames': delta,
                                   'equal_cell_win_minus_loss': round(contrast(at_offset, 'offset_metrics', metric), 3)})
        comparisons[metric] = {'equal_cell_median_window_win_minus_loss': round(median_result, 3),
                               'equal_cell_anchor_win_minus_loss': round(anchor_result, 3),
                               'five_offset_differences': offset_results}
    summary = {'frozen_points': 18, 'source_screened_candidate_windows': 8,
               'wins': 4, 'losses': 4, 'matched_set_phase_cells': 3,
               'five_hz_samples_per_window': 5, 'source_frame_instances': 40,
               'validated_court_metric_windows': 0}
    out = {'status': 'exploratory_image_plane_five_sample_geometry_not_contract_outcome_analysis',
           'source_sha256': pilot['source_sha256'],
           'input_sha256': {'pilot': sha(PILOT), 'endpoint_audit': sha(AUDIT)},
           'summary': summary, 'comparisons': comparisons, 'rows': rows,
           'interpretation': ('Eight availability-selected windows have no obvious wrong-person '
                              'transfer at three displayed source instants and share set-and-phase '
                              'cells with both outcomes. Unsampled-frame identities, full-window '
                              'phase and court-floor coordinates remain unvalidated. Pixel-space '
                              'geometry and sampled polylines are method diagnostics, not winner '
                              'effects or court movement distances.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Short-window image-plane geometry diagnostic', '',
             'The [source-bound calculation](../data/matches/yt_u5HnY2aNW14/screening/flow_window_image_geometry.json) '
             'uses the [optical-flow pilot](HONOURS_U5_BOX_CENTRE_FLOW_PILOT.md) at five '
             '5 Hz samples per window. Eight of the frozen 18 points remain after the '
             'displayed-endpoint, open-play-anchor and set-by-phase screens. The eight comprise '
             'four wins and four losses in three set-and-phase cells. Every metric here uses '
             'full image-box centres in **pixels**, including airborne people.', '',
             '| Image metric | Mean winning minus losing window median | At anchor only | Across five individual offsets |',
             '| --- | ---: | ---: | ---: |']
    for metric in METRIC_MAP.values():
        c = comparisons[metric]
        values = [r['equal_cell_win_minus_loss'] for r in c['five_offset_differences']]
        lines.append(f"| {LABELS[metric]} | {c['equal_cell_median_window_win_minus_loss']:+.3f} | "
                     f"{c['equal_cell_anchor_win_minus_loss']:+.3f} | "
                     f"{min(values):+.3f} to {max(values):+.3f} |")
    lines += ['', 'The comparison averages within-cell differences equally across the three '
              'set-and-phase cells. The five-offset range shows how the descriptive contrast '
              'changes when each of the five sample times is used alone; it is not an error '
              'interval. Box translations can drift when people cross or change pose, and '
              'four such windows were excluded by endpoint review. A later [five-instant source review]'
              '(HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) found no obvious wrong-person '
              'transfer in the eight retained windows at their five displayed samples. '
              'Unsampled frames, named identities and the entire live phase are not certified even in these '
              'eight. The sample was selected by detector and review availability, so these '
              'figures are **not a statistical association with winning**. Court positions '
              'and rotation/transition measures are still missing.', '',
              'Reproduce with `python scripts/analyze_u5_flow_window_geometry.py` after '
              'the optical-flow pilot and endpoint audit.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)
    print({k: v['equal_cell_median_window_win_minus_loss'] for k, v in comparisons.items()})


if __name__ == '__main__':
    main()
