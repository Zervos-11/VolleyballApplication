"""Compare fixed-box pilot anchors with existing manual clear-shoe references."""

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PILOT = BASE / 'fixed_box_court_proxy_pilot.json'
REFERENCE = BASE / 'heldout_box_floor_error.json'
OUT = BASE / 'fixed_box_anchor_reference_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md'
FIELDS = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pilot = json.loads(PILOT.read_text(encoding='utf-8'))
    reference = json.loads(REFERENCE.read_text(encoding='utf-8'))
    assert pilot['input_sha256']['reference'] == sha(REFERENCE)
    assert pilot['source_sha256'] == reference['source_sha256']
    by_key = {(r['set'], r['point_number']): r for r in pilot['rows']}
    grouped = defaultdict(list)
    for ref in reference['rows']:
        key = ref['set'], ref['point_number']
        if key in by_key and ref['source_frame'] == by_key[key]['source_frames'][2]:
            grouped[key].append(ref)
    pairs = []
    team_frames = []
    for key, refs in sorted(grouped.items()):
        row = by_key[key]
        anchor = row['frames'][2]
        by_id = {ref['raw_track_id']: ref for ref in refs}
        matched = []
        for i, player_key in enumerate(row['player_keys']):
            if player_key not in by_id:
                continue
            ref = by_id[player_key]
            proxy = anchor['court_proxy_m'][i]
            stored = ref['box_bottom_court_m']
            assert math.dist(proxy, stored) < .003
            error = math.dist(proxy, ref['shoe_midpoint_court_m'])
            pair = {'set': key[0], 'point_number': key[1],
                    'source_frame': anchor['source_frame'], 'raw_track_id': player_key,
                    'proxy_court_m': proxy,
                    'manual_clear_shoe_midpoint_court_m': ref['shoe_midpoint_court_m'],
                    'position_error_m': round(error, 4)}
            pairs.append(pair)
            matched.append(pair)
        if len(matched) == 6:
            proxy_metrics = metrics([tuple(p['proxy_court_m']) for p in matched])
            manual_metrics = metrics([tuple(p['manual_clear_shoe_midpoint_court_m'])
                                      for p in matched])
            team_frames.append({'set': key[0], 'point_number': key[1],
                                'source_frame': anchor['source_frame'],
                                'near_team_won': row['near_team_won'],
                                'six_player_proxy_metrics': {f: round(proxy_metrics[f], 4)
                                                             for f in FIELDS},
                                'six_player_manual_clear_shoe_metrics': {f: round(manual_metrics[f], 4)
                                                                        for f in FIELDS},
                                'proxy_minus_manual': {f: round(proxy_metrics[f]-manual_metrics[f], 4)
                                                       for f in FIELDS}})
    assert len(pairs) == 16 and len(team_frames) == 2
    errors = [p['position_error_m'] for p in pairs]
    summary = {'matching_clear_shoe_players': len(pairs),
               'anchor_frames_with_any_match': len(grouped),
               'complete_six_player_reference_frames': len(team_frames),
               'median_position_error_m': round(statistics.median(errors), 4),
               'maximum_position_error_m': round(max(errors), 4),
               'independently_labelled_dynamic_frames': 0}
    out = {'status': 'existing_single_reviewer_anchor_reference_not_dynamic_validation',
           'source_sha256': pilot['source_sha256'],
           'input_sha256': {'pilot': sha(PILOT), 'manual_reference': sha(REFERENCE)},
           'summary': summary, 'matching_pairs': pairs, 'complete_team_frames': team_frames,
           'interpretation': ('This joins existing clear-shoe labels to fixed-box pilot anchor '
                              'frames; it is not new independent annotation. Two complete '
                              'team frames allow direct proxy-versus-manual geometry checks. '
                              'All references are single-reviewer, clearly grounded instances; '
                              'dynamic flow propagation, low posture and airborne frames are '
                              'not validated.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Fixed-box anchor versus manual shoe reference', '',
             'The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/fixed_box_anchor_reference_audit.json) '
             'joins the fixed-box pilot to **existing** single-reviewer shoe-midpoint marks '
             'on the same source frames. This is a direct anchor check, not a new or independent '
             'annotation. Sixteen players match across three anchor frames; two frames have '
             'clear grounded shoe marks for all six teammates.', '',
             f"Median court-position discrepancy is {summary['median_position_error_m']:.3f} m "
             f"and the largest is {summary['maximum_position_error_m']:.3f} m across the "
             '16 matched players. The existing reference includes only clearly visible '
             'grounded shoes and has approximate visual-reading uncertainty.', '',
             '| Frame | Proxy minus manually marked six-player spacing | Hull area | Dispersion |',
             '| --- | ---: | ---: | ---: |']
    for row in team_frames:
        d = row['proxy_minus_manual']
        lines.append(f"| S{row['set']} P{row['point_number']} f{row['source_frame']} | "
                     f"{d['mean_pairwise_spacing_m']:+.3f} m | "
                     f"{d['convex_hull_area_m2']:+.3f} m^2 | "
                     f"{d['centroid_dispersion_m']:+.3f} m |")
    lines += ['', 'These two complete frames illustrate how position-proxy error propagates '
              'into team metrics. They do not validate the other samples in each 0.8 s '
              'window, difficult poses, or full-rally trajectories. The figures remain '
              'exploratory measurements under the original research-prototype scope.', '',
              'Reproduce with `python scripts/audit_u5_fixed_box_anchor_reference.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
