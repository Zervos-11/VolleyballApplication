"""Freeze source observations for every sampled frame of seven interior runs."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'interior_run_review/index.json'
FULL_INDEX = BASE / 'all_interior_run_frames/index.json'
RUNS = BASE / 'interior_identity_run_availability.json'
OUT = BASE / 'interior_run_source_qc.json'
REVIEWED = {(1, 6), (1, 34), (1, 37), (2, 2), (2, 6), (2, 26), (3, 34)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    full_index = json.loads(FULL_INDEX.read_text(encoding='utf-8'))
    runs = json.loads(RUNS.read_text(encoding='utf-8'))
    if index['run_audit_sha256'] != sha(RUNS):
        raise ValueError('Review sheets differ from current interior run audit')
    if full_index['run_audit_sha256'] != sha(RUNS) or full_index['source_sha256'] != index['source_sha256']:
        raise ValueError('Full run sheets differ from current interior run audit')
    full_by_key = {(r['set'], r['point_number']): r for r in full_index['entries']}
    by_key = {(p['set'], p['point_number']): p for p in runs['points']}
    rows = []
    for page in index['pages']:
        if sha(INDEX.parent / page['path']) != page['sha256']:
            raise ValueError(f"Review sheet changed: {page['path']}")
        for item in page['items']:
            key = item['set'], item['point_number']
            if key not in REVIEWED or item['run_frames'] != by_key[key]['run_source_frames']:
                raise ValueError(f'Unexpected candidate run {key}')
            full = full_by_key[key]
            if full['source_frames'] != item['run_frames'] or sha(FULL_INDEX.parent / full['path']) != full['sha256']:
                raise ValueError(f'Full source sheet changed for {key}')
            rows.append({'set': key[0], 'point_number': key[1],
                         'run_frame_count': len(item['run_frames']),
                         'displayed_source_frames': item['displayed_frames'],
                         'three_anchor_team_membership': 'six_correct_near_side_teammates_at_each_anchor',
                         'all_sampled_frame_team_membership': 'six_correct_near_side_teammates_each_sampled_frame',
                         'all_sampled_source_frames': item['run_frames'],
                         'inter_sample_continuity': 'not_observed_between_five_hz_samples',
                         'named_jersey_continuity': 'source_reviewed_short_run'
                         if key == (1, 37) else 'not_individually_certified',
                         'ground_position_validation': 'pending',
                         'source_sheet': page['path'], 'source_sheet_sha256': page['sha256'],
                         'all_frames_source_sheet': full['path'],
                         'all_frames_source_sheet_sha256': full['sha256']})
    if {(r['set'], r['point_number']) for r in rows} != REVIEWED:
        raise ValueError('Missing or duplicated reviewed run')
    result = {'status': 'single_reviewer_all_sampled_frame_team_membership_not_ground_trajectory_validation',
              'source_sha256': index['source_sha256'],
              'run_audit_sha256': sha(RUNS), 'review_index_sha256': sha(INDEX),
              'full_frame_review_index_sha256': sha(FULL_INDEX),
              'summary': {'candidate_runs_reviewed': len(rows),
                          'runs_with_correct_team_at_three_anchors': len(rows),
                          'runs_with_correct_team_at_all_sampled_frames': len(rows),
                          'sampled_frames_source_reviewed': sum(r['run_frame_count'] for r in rows),
                          'short_runs_with_named_jersey_continuity_review': 1,
                          'validated_grounded_trajectories': 0},
              'limitations': 'Every 5 Hz source still in the seven runs was visually checked for six correct near-side teammates and box continuity. The unsampled frames between stills were not individually inspected. Named jersey continuity was recorded only for the separate set-one point-37 run. Grounded floor positions have not been validated.',
              'rows': rows}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
