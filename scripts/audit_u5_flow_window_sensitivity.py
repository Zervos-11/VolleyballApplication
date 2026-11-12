"""Assess deletion sensitivity of the exploratory five-sample pixel contrasts."""

import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
GEOMETRY = BASE / 'flow_window_image_geometry.json'
SOURCE_AUDIT = BASE / 'flow_window_five_sample_audit.json'
OUT = BASE / 'flow_window_sensitivity.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FLOW_WINDOW_SENSITIVITY.md'
METRICS = ('spacing_px', 'hull_area_px2', 'dispersion_px')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal_cell_contrast(rows, metric):
    groups = defaultdict(lambda: {True: [], False: []})
    for row in rows:
        groups[(row['set'], row['phase'])][row['near_team_won']].append(
            row['median_image_metrics'][metric])
    eligible = [(key, group) for key, group in groups.items()
                if group[True] and group[False]]
    return {'matched_cells': len(eligible),
            'matched_points': sum(len(g[True]) + len(g[False]) for _, g in eligible),
            'difference': round(statistics.mean(statistics.mean(g[True])-statistics.mean(g[False])
                                                for _, g in eligible), 3) if eligible else None}


def main():
    geometry = json.loads(GEOMETRY.read_text(encoding='utf-8'))
    audit = json.loads(SOURCE_AUDIT.read_text(encoding='utf-8'))
    assert audit['input_sha256']['image_geometry'] == sha(GEOMETRY)
    assert len(geometry['rows']) == audit['summary']['candidate_windows'] == 8
    baseline = {m: equal_cell_contrast(geometry['rows'], m) for m in METRICS}
    assert all(v['matched_cells'] == 3 for v in baseline.values())
    deletions = []
    for dropped in geometry['rows']:
        keep = [r for r in geometry['rows'] if r is not dropped]
        deletions.append({'excluded': {'set': dropped['set'], 'point_number': dropped['point_number']},
                          'metrics': {m: equal_cell_contrast(keep, m) for m in METRICS}})
    flagged = []
    for key, reason in [((1, 18), 'player_beyond_sideline'),
                        ((2, 28), 'low_posture_near_net')]:
        row = next(d for d in deletions if (d['excluded']['set'], d['excluded']['point_number']) == key)
        flagged.append({'excluded': row['excluded'], 'reason': reason, 'metrics': row['metrics']})
    ranges = {m: [min(d['metrics'][m]['difference'] for d in deletions),
                  max(d['metrics'][m]['difference'] for d in deletions)] for m in METRICS}
    out = {'status': 'selection_and_posture_sensitivity_not_statistical_inference',
           'source_sha256': geometry['source_sha256'],
           'input_sha256': {'geometry': sha(GEOMETRY), 'source_review': sha(SOURCE_AUDIT)},
           'summary': {'candidate_windows': 8, 'baseline_matched_cells': 3,
                       'one_point_deletions': 8, 'validated_court_metric_windows': 0},
           'baseline': baseline, 'one_point_deletions': deletions,
           'flagged_deletions': flagged, 'one_point_difference_ranges': ranges,
           'interpretation': ('After each point deletion, only cells retaining both outcomes '
                              'contribute. Thus deletion can change the cells being averaged; '
                              'these ranges are selection sensitivity, not confidence intervals. '
                              'All values remain source-image pixels and cannot establish '
                              'a court-metric winner effect.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Five-sample pixel comparison sensitivity', '',
             'The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/flow_window_sensitivity.json) '
             'recomputes the exploratory equal-set-and-phase contrast after deleting each '
             'of the eight short windows in turn. It also singles out S1 P18, where a '
             'player is beyond the sideline, and S2 P28, where a player is low near the net. '
             'The [five-instant source review](HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) '
             'found no obvious wrong-person transfer in either case, but it cannot validate '
             'court position or box-centre accuracy.', '',
             '| Metric | All eight | Range after one-point deletion | Delete S1 P18 | Delete S2 P28 |',
             '| --- | ---: | ---: | ---: | ---: |']
    for metric in METRICS:
        lo, hi = ranges[metric]
        lines.append(f"| {metric} | {baseline[metric]['difference']:+.3f} | "
                     f"{lo:+.3f} to {hi:+.3f} | "
                     f"{flagged[0]['metrics'][metric]['difference']:+.3f} "
                     f"({flagged[0]['metrics'][metric]['matched_cells']} cells) | "
                     f"{flagged[1]['metrics'][metric]['difference']:+.3f} "
                     f"({flagged[1]['metrics'][metric]['matched_cells']} cells) |")
    lines += ['', 'After a deletion, a set-and-phase cell contributes only if it still has '
              'both outcomes. Removing S2 P28 therefore removes the entire set-two offensive '
              'cell. The ranges reflect both point leverage and changing cell coverage; '
              'they are **not uncertainty intervals or significance tests**. These are '
              'pixel-space method diagnostics from selected windows. The validated '
              'court-trajectory count remains zero.', '',
              'Reproduce with `python scripts/audit_u5_flow_window_sensitivity.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(ranges)


if __name__ == '__main__':
    main()
