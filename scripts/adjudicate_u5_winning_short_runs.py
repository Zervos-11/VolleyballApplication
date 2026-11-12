"""Freeze source checks of all winning near-side short-run candidates."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'winning_short_run_review/index.json'
RUNS = BASE / 'interior_identity_run_availability.json'
FALSE_SOURCE = BASE / 'winning_short_run_review/s3_p33_f35826_source.jpg'
OUT = BASE / 'winning_short_run_source_qc.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    runs = json.loads(RUNS.read_text(encoding='utf-8'))
    if index['run_audit_sha256'] != sha(RUNS):
        raise ValueError('Winning review sheets differ from current run audit')
    by_key = {(p['set'], p['point_number']): p for p in runs['points'] if p['near_team_won']}
    assert len(by_key) == 9
    rows = []
    for item in index['entries']:
        key = item['set'], item['point_number']
        if key not in by_key or item['source_frames'] != by_key[key]['run_source_frames']:
            raise ValueError(f'Winning run changed: {key}')
        if item['path'] is not None and sha(INDEX.parent / item['path']) != item['sha256']:
            raise ValueError(f"Winning source sheet changed: {item['path']}")
        if not item['source_frames']:
            status, bad = 'no_six_id_run_in_interior', []
        elif key == (3, 33):
            if item['source_frames'] != [35826]:
                raise ValueError('Known wrong-team candidate moved')
            status, bad = 'wrong_team_box_in_six_candidate', [40]
        else:
            status, bad = 'six_correct_near_side_teammates_each_sampled_frame', []
        rows.append({'set': key[0], 'point_number': key[1],
                     'run_source_frames': item['source_frames'],
                     'source_team_membership_status': status,
                     'wrong_team_raw_track_ids': bad,
                     'source_sheet': item['path'], 'source_sheet_sha256': item['sha256'],
                     'ground_position_validation': 'pending'})
    if {(r['set'], r['point_number']) for r in rows} != set(by_key):
        raise ValueError('Missing or duplicate winner point')
    result = {'status': 'single_reviewer_winning_short_run_team_membership_not_floor_validation',
              'source_sha256': index['source_sha256'],
              'run_audit_sha256': sha(RUNS), 'review_index_sha256': sha(INDEX),
              'wrong_team_source_image': str(FALSE_SOURCE.relative_to(BASE)).replace('\\', '/'),
              'wrong_team_source_image_sha256': sha(FALSE_SOURCE),
              'summary': {'frozen_near_team_wins': len(rows),
                          'wins_with_correct_six_candidate_run': sum(
                              r['source_team_membership_status'] ==
                              'six_correct_near_side_teammates_each_sampled_frame' for r in rows),
                          'correct_win_candidate_frames_source_reviewed': sum(
                              len(r['run_source_frames']) for r in rows if
                              r['source_team_membership_status'] ==
                              'six_correct_near_side_teammates_each_sampled_frame'),
                          'wrong_team_candidate_runs': 1,
                          'wins_without_six_candidate_run': sum(
                              r['source_team_membership_status'] == 'no_six_id_run_in_interior'
                              for r in rows),
                          'validated_grounded_trajectories': 0},
              'limitations': 'One to three 5 Hz source stills were checked per usable winning point. Set-three point 33 raw box 40 is a far-side white player and does not replace the missing blue teammate. The source-reviewed frame 35844 in the separate one-frame QC remains valid, but it is not part of this longest same-ID run. These short windows do not establish a full rally trajectory or grounded coordinates.',
              'rows': rows}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
