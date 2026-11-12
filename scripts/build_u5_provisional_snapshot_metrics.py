"""Demonstrate three court metrics on source-screened U5 live snapshots.

These are box-bottom *proxy* values from one availability-selected frame per
point. They are not strict final rally-level measurements or an outcome test.
"""
import hashlib
import json
import statistics
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
PHASE_QC = BASE / 'selected_phase_source_qc.json'
SAMPLE = BASE / 'rally_sample_score_only.json'
OUT = BASE / 'provisional_live_snapshot_metrics.json'
NAMES = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    qc = json.loads(PHASE_QC.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    if not (tracks['source_sha256'] == sample['source_sha256']):
        raise ValueError('Source mismatch')
    lookup = {(p['set'], p['point_number']): p for p in tracks['points']}
    outcome = {(e['set'], e['point_number']): e for e in sample['selected_events']}
    rows = []
    exclusions = []
    for reviewed in qc['rows']:
        if reviewed['local_phase_status'] != 'visible_live_play':
            continue
        key = (reviewed['set'], reviewed['point_number'])
        source = next(r for r in lookup[key]['rows']
                      if r['source_frame'] == reviewed['source_frame'])
        candidates = [p for p in source['proposals']
                      if p['net_side_status'] == 'near_floor_side_candidate']
        if len(candidates) != 6 or any(p['raw_track_id'] is None for p in candidates):
            exclusions.append({'set': key[0], 'point_number': key[1],
                               'source_frame': reviewed['source_frame'],
                               'reason': 'not_exactly_six_tracked_geometric_candidates'})
            continue
        positions = [p['box_bottom_court_m'] for p in candidates]
        if any(not all(0 <= coordinate <= 9 for coordinate in xy) for xy in positions):
            exclusions.append({'set': key[0], 'point_number': key[1],
                               'source_frame': reviewed['source_frame'],
                               'reason': 'at_least_one_box_bottom_outside_strict_9m_court'})
            continue
        measured = metrics([tuple(xy) for xy in positions])
        winner = 'UCLA' if outcome[key]['winner_scoreboard_side'] == 'left' else 'Concordia'
        near = 'UCLA' if reviewed['set'] in (1, 3) else 'Concordia'
        rows.append({'set': reviewed['set'], 'point_number': reviewed['point_number'],
                     'source_frame': reviewed['source_frame'], 'winner': winner,
                     'near_team': near, 'near_team_won': winner == near,
                     'raw_track_ids': [p['raw_track_id'] for p in candidates],
                     'box_bottom_court_positions_m': positions,
                     'provisional_snapshot_metrics': {name: round(measured[name], 3)
                                                      for name in NAMES}})
    groups = []
    for set_number in (1, 2, 3):
        for won in (True, False):
            selected = [r for r in rows if r['set'] == set_number and r['near_team_won'] == won]
            groups.append({'set': set_number, 'near_team_won': won, 'snapshots': len(selected),
                           'median_of_provisional_snapshots': {
                               name: (round(statistics.median(
                                   r['provisional_snapshot_metrics'][name] for r in selected), 3)
                                      if selected else None) for name in NAMES}})
    output = {
        'status': 'provisional_availability_selected_single_frame_metrics_not_final_outcome_analysis',
        'source_sha256': tracks['source_sha256'], 'dense_tracks_sha256': digest(TRACKS),
        'source_phase_qc_sha256': digest(PHASE_QC), 'frozen_sample_sha256': digest(SAMPLE),
        'summary': {'frozen_selected_points': len(sample['selected_events']),
                    'source_screened_live_snapshots_with_six_nominal_in_court_boxes': len(rows),
                    'source_visible_live_snapshots_excluded_by_nominal_geometry': len(exclusions),
                    'validated_metric_frames': 0, 'validated_rally_summaries': 0},
        'groups': groups, 'rows': rows, 'exclusions': exclusions,
        'limitations': [
            'One frame per selected point was chosen using box availability, so outcome comparisons are biased.',
            'The brief source phase screen does not certify exact rally boundaries or phase matching.',
            'Raw track IDs and every foot contact were not independently validated.',
            'Box-bottom projection is not validated ground position; values are method examples only.',
            'No significance test or winning-association claim is supported.'
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])
    print([(g['set'], g['near_team_won'], g['snapshots']) for g in groups])


if __name__ == '__main__':
    main()
