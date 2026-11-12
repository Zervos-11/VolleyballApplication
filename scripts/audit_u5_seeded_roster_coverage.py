"""Measure 5 Hz coverage of the six raw IDs seen at each selected U5 frame.

This is an upper-bound tracker continuity diagnostic, not a named roster audit.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
SELECTION = BASE / 'phase_six_candidate_review/selected.json'
PHASE = BASE / 'selected_phase_source_qc.json'
OUT = BASE / 'seeded_roster_coverage.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def longest_true_run(values):
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    selection = json.loads(SELECTION.read_text(encoding='utf-8'))
    phase = json.loads(PHASE.read_text(encoding='utf-8'))
    selected = {(r['set'], r['point_number']): r for r in selection['selected']}
    phase_qc = {(r['set'], r['point_number']): r for r in phase['rows']}
    rows = []
    for point in tracks['points']:
        key = (point['set'], point['point_number'])
        ids = selected[key]['raw_track_ids']
        if len(ids) != 6 or None in ids or len(set(ids)) != 6:
            raise ValueError(f'No six unique anchor raw IDs for {key}')
        roster = set(ids)
        observations = []
        for frame in point['rows']:
            current = {p['raw_track_id'] for p in frame['proposals']
                       if p['net_side_status'] == 'near_floor_side_candidate'}
            observations.append({'source_frame': frame['source_frame'],
                                 'anchor_ids_present': len(current & roster),
                                 'all_six_anchor_ids_present': roster <= current})
        complete = [r['all_six_anchor_ids_present'] for r in observations]
        rows.append({'set': key[0], 'point_number': key[1],
                     'selected_source_frame': selected[key]['source_frame'],
                     'selected_local_phase_status': phase_qc[key]['local_phase_status'],
                     'anchor_raw_track_ids': ids, 'sampled_frames': len(observations),
                     'frames_with_all_six_anchor_ids': sum(complete),
                     'longest_all_six_anchor_id_run_frames': longest_true_run(complete),
                     'frames_with_fewer_than_six_anchor_ids': len(observations) - sum(complete),
                     'per_frame': observations})
    output = {
        'status': 'anchor_raw_id_coverage_diagnostic_not_validated_roster',
        'dense_tracks_sha256': digest(TRACKS), 'selected_frame_sha256': digest(SELECTION),
        'source_phase_qc_sha256': digest(PHASE),
        'summary': {'points': len(rows),
                    'sampled_frames': sum(r['sampled_frames'] for r in rows),
                    'frames_with_all_six_anchor_ids': sum(r['frames_with_all_six_anchor_ids']
                                                          for r in rows),
                    'points_with_any_all_six_anchor_id_frame': sum(
                        r['frames_with_all_six_anchor_ids'] > 0 for r in rows)},
        'rows': rows,
        'limitations': [
            'Anchor raw IDs can switch identities or attach to wrong-team boxes away from the selected frame.',
            'The sampled core includes uncertain or dead-ball intervals.',
            'Presence of six raw IDs does not validate six grounded positions.',
            'Missing IDs are not filled by a stationary or interpolated position.'
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])
    for row in rows:
        print(f"S{row['set']} P{row['point_number']}: "
              f"{row['frames_with_all_six_anchor_ids']}/{row['sampled_frames']} "
              f"same-anchor-ID frames")


if __name__ == '__main__':
    main()
