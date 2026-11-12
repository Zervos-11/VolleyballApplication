"""Summarise candidate six-player continuity in the U5 dense track screen."""
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
SAMPLE = BASE / 'rally_sample_score_only.json'
OUT = BASE / 'dense_live_continuity_audit.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def longest_same_six_run(rows):
    longest = {'frames': 0, 'first_frame': None, 'last_frame': None, 'raw_track_ids': []}
    active = None
    for row in rows:
        candidates = [p for p in row['proposals']
                      if p['net_side_status'] == 'near_floor_side_candidate']
        ids = [p['raw_track_id'] for p in candidates]
        exact = len(ids) == 6 and None not in ids and len(set(ids)) == 6
        key = tuple(sorted(ids)) if exact else None
        if key is None:
            active = None
            continue
        if active is not None and active['raw_track_ids'] == list(key):
            active['frames'] += 1
            active['last_frame'] = row['source_frame']
        else:
            active = {'frames': 1, 'first_frame': row['source_frame'],
                      'last_frame': row['source_frame'], 'raw_track_ids': list(key)}
        if active['frames'] > longest['frames']:
            longest = dict(active)
    return longest


def main():
    data = json.loads(TRACKS.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    if data['source_sha256'] != sample['source_sha256']:
        raise ValueError('Different sources')
    selected = {(p['set'], p['point_number']): p for p in sample['selected_events']}
    results = []
    for point in data['points']:
        key = (point['set'], point['point_number'])
        outcome = selected[key]
        near_team = 'UCLA' if point['set'] in (1, 3) else 'Concordia'
        winner = 'UCLA' if outcome['winner_scoreboard_side'] == 'left' else 'Concordia'
        rows = point['rows']
        longest = longest_same_six_run(rows)
        results.append({
            'set': point['set'], 'point_number': point['point_number'],
            'winner': winner, 'near_team': near_team, 'near_team_won': winner == near_team,
            'sampled_frames': len(rows), 'frame_step': point['frame_step'],
            'six_geometric_candidate_frames': point['frames_with_six_geometric_candidates'],
            'exact_six_geometric_candidate_frames': sum(
                r['near_floor_side_candidate_count'] == 6 for r in rows),
            'frames_with_net_boundary_review': point['frames_with_any_net_boundary_review'],
            'longest_consecutive_exact_six_same_raw_ids': longest,
            'geometric_six_candidate_fraction': round(
                point['frames_with_six_geometric_candidates'] / len(rows), 4)
        })
    group = Counter((p['set'], p['near_team_won']) for p in results)
    output = {
        'status': 'candidate_identity_continuity_not_source_validated',
        'dense_track_screen_sha256': digest(TRACKS),
        'frozen_sample_sha256': digest(SAMPLE),
        'summary': {
            'points': len(results), 'sampled_frames': sum(p['sampled_frames'] for p in results),
            'six_geometric_candidate_frames': sum(p['six_geometric_candidate_frames'] for p in results),
            'points_with_any_six_geometric_candidates': sum(
                p['six_geometric_candidate_frames'] > 0 for p in results),
            'points_with_at_least_one_second_same_six_raw_ids': sum(
                p['longest_consecutive_exact_six_same_raw_ids']['frames'] >= 5 for p in results),
            'near_team_win_loss_by_set': {f'set_{s}_{"win" if won else "loss"}': group[s, won]
                                         for s in (1, 2, 3) for won in (True, False)},
        },
        'points': results,
        'limitations': [
            'Exact six raw IDs can still include wrong-team players or duplicates.',
            'Raw IDs are local to each selected point and may switch within it.',
            'Five-hertz screening misses motion between sampled frames.',
            'Geometric availability is not a reviewed six-player floor-position denominator.'
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])
    for p in results:
        run = p['longest_consecutive_exact_six_same_raw_ids']
        print(f"S{p['set']} P{p['point_number']}: six {p['six_geometric_candidate_frames']}/"
              f"{p['sampled_frames']}, longest stable raw-ID run {run['frames']} frames")


if __name__ == '__main__':
    main()
