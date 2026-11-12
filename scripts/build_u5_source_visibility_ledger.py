"""Join frozen points to local detector and source-only six-player evidence."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PATHS = {
    'sample': SCREEN / 'rally_sample_score_only.json',
    'local_boxes': SCREEN / 'bracketed_candidate_source_qc.json',
    'zero_run_source': SCREEN / 'zero_run_source_qc.json',
    'runs': SCREEN / 'interior_identity_run_availability.json',
}
OUT = SCREEN / 'source_visibility_ledger.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in PATHS.items()}
    selected = {(p['set'], p['point_number']): p for p in data['sample']['selected_events']}
    box_rows = {(p['set'], p['point_number']): p for p in data['local_boxes']['rows']}
    source_rows = {(p['set'], p['point_number']): p for p in data['zero_run_source']['rows']}
    run_rows = {(p['set'], p['point_number']): p for p in data['runs']['points']}
    assert len(selected) == 18 and len(box_rows) == 15 and len(source_rows) == 3
    assert set(box_rows).isdisjoint(source_rows) and set(box_rows) | set(source_rows) == set(selected)
    assert set(run_rows) == set(selected)
    rows = []
    for key, point in sorted(selected.items()):
        run = run_rows[key]
        if key in box_rows:
            evidence = 'source_reviewed_six_local_detector_boxes'
            frame = box_rows[key]['source_frame']
        else:
            evidence = 'source_visible_six_no_six_id_detector_run'
            frame = source_rows[key]['source_frames'][0]
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team': run['near_team'], 'near_team_won': run['near_team_won'],
                     'six_player_visibility_evidence': evidence,
                     'example_source_frame': frame,
                     'longest_same_six_raw_id_run_frames': run['longest_same_six_raw_id_run_frames'],
                     'grounded_metric_frames_validated': 0})
    wins = [r for r in rows if r['near_team_won']]
    losses = [r for r in rows if not r['near_team_won']]
    assert len(wins) == len(losses) == 9
    OUT.write_text(json.dumps({
        'status': 'visibility_coverage_only_no_trajectory_or_floor_validation',
        'source_sha256': data['sample']['source_sha256'],
        'input_sha256': {key: sha(path) for key, path in PATHS.items()},
        'summary': {'frozen_points': 18, 'near_team_wins': 9, 'near_team_losses': 9,
                    'points_with_six_source_visible_teammates': 18,
                    'points_with_six_locally_correct_detector_boxes': 15,
                    'points_source_visible_without_six_id_run': 3,
                    'validated_six_player_metric_frames': 0},
        'rows': rows,
    }, indent=2) + '\n', encoding='utf-8')
    print('Joined 18/18 source-visible points; 0 validated metric frames')


if __name__ == '__main__':
    main()
