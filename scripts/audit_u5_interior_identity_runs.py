"""Find same-six raw-ID runs inside source-bounded live interiors only."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
CORE = BASE / 'cut_bounded_provisional_rally_metrics.json'
WINDOWS = BASE / 'event_transition_source_qc.json'
IDENTITY = BASE / 's1p37_short_identity_run.json'
OUT = BASE / 'interior_identity_run_availability.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    core = json.loads(CORE.read_text(encoding='utf-8'))
    windows = json.loads(WINDOWS.read_text(encoding='utf-8'))
    identity = json.loads(IDENTITY.read_text(encoding='utf-8'))
    assert core['dense_tracks_sha256'] == sha(TRACKS)
    assert tracks['source_sha256'] == core['source_sha256'] == windows['source_sha256']
    assert identity['tracks_sha256'] == sha(TRACKS)
    intervals = {(p['set'], p['point_number']): p for p in windows['points']}
    lookup = {(p['set'], p['point_number']): {r['source_frame']: r for r in p['rows']}
              for p in tracks['points']}
    result_rows = []
    for point in core['points']:
        key = point['set'], point['point_number']
        interior = intervals[key]
        start = interior['conservative_interior_start_frame_inclusive']
        end = interior['conservative_interior_end_frame_exclusive']
        current, best, previous_ids, previous_frame = [], [], None, None
        for candidate in point['frames']:
            frame = candidate['source_frame']
            if not start <= frame < end:
                continue
            ids = tuple(sorted(p['raw_track_id'] for p in lookup[key][frame]['proposals']
                               if p['net_side_status'] == 'near_floor_side_candidate'))
            if len(ids) != 6:
                raise ValueError(f'Geometric candidate has {len(ids)} IDs at {key} {frame}')
            if ids == previous_ids and previous_frame is not None and frame - previous_frame == 6:
                current.append(frame)
            else:
                current = [frame]
            if len(current) > len(best):
                best = current[:]
                best_ids = ids
            previous_ids, previous_frame = ids, frame
        result_rows.append({'set': key[0], 'point_number': key[1],
                            'near_team': point['near_team'],
                            'near_team_won': point['near_team_won'],
                            'longest_same_six_raw_id_run_frames': len(best),
                            'run_source_frames': best,
                            'raw_track_ids': list(best_ids) if best else [],
                            'source_identity_review_status': ('short_run_source_reviewed'
                                                              if key == (1, 37) and
                                                              best == identity['sampled_source_frames'] else
                                                              'not_source_reviewed'),
                            'ground_position_validation': 'pending'})
    assert sum(r['source_identity_review_status'] == 'short_run_source_reviewed'
               for r in result_rows) == 1
    output = {'status': 'interior_detector_run_availability_not_validated_trajectories',
              'source_sha256': tracks['source_sha256'],
              'tracks_sha256': sha(TRACKS), 'candidate_screen_sha256': sha(CORE),
              'live_interior_sha256': sha(WINDOWS),
              'short_identity_audit_sha256': sha(IDENTITY),
              'summary': {'frozen_points': len(result_rows),
                          'points_with_any_candidate_run': sum(r['longest_same_six_raw_id_run_frames'] > 0
                                                               for r in result_rows),
                          'points_with_at_least_five_samples': sum(r['longest_same_six_raw_id_run_frames'] >= 5
                                                                   for r in result_rows),
                          'long_run_near_team_wins': sum(r['longest_same_six_raw_id_run_frames'] >= 5 and
                                                         r['near_team_won'] for r in result_rows),
                          'long_run_near_team_losses': sum(r['longest_same_six_raw_id_run_frames'] >= 5 and
                                                           not r['near_team_won'] for r in result_rows),
                          'source_reviewed_short_identity_runs': 1,
                          'validated_grounded_trajectories': 0},
              'points': result_rows}
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
