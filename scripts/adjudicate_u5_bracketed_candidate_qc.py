"""Record a single-reviewer local source check of 15 bracketed six-box frames.

The review compares unboxed source and detector-overlay panels plus the
shoe-level crops. A second pass identified a wrong-team box in the original
set 1 point 37 selection and source-checked an earlier replacement.
Neither exact live boundaries nor whole-rally continuity are attested.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'bracketed_candidate_qc/index.json'
OUT = BASE / 'bracketed_candidate_source_qc.json'
REPLACEMENT_INDEX = BASE / 's1p37_replacement_review/index.json'

# Explicitly freeze the frames visually checked on the source/overlay sheets.
REVIEWED = {
    (1, 5): 1422, (1, 6): 1758, (1, 27): 7344, (1, 34): 9702,
    (1, 37): 10488, (2, 2): 12306, (2, 6): 13566,
    (2, 26): 18936, (2, 28): 19536, (2, 37): 22140,
    (3, 11): 29280, (3, 13): 29940, (3, 27): 34122,
    (3, 33): 35844, (3, 34): 36072,
}
REJECTED_FRAME = {'set': 1, 'point_number': 37, 'source_frame': 10722,
                  'wrong_team_raw_track_ids': [87],
                  'reason': 'Two white-uniform boxes selected alongside four blue UCLA boxes; only one white UCLA libero belongs to the near-side six.'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    if index['point_count'] != len(REVIEWED):
        raise ValueError('Selected review count changed')
    replacement = json.loads(REPLACEMENT_INDEX.read_text(encoding='utf-8'))
    if replacement['source_sha256'] != index['source_sha256'] or not any(
            10488 in page['frames'] and 10722 in page['frames']
            for page in replacement['pages']):
        raise ValueError('Replacement source review differs from current video or frames')
    rows = []
    for page in index['pages']:
        path = INDEX.parent / page['path']
        if digest(path) != page['sha256']:
            raise ValueError(f"Review sheet changed: {page['path']}")
        for item in page['items']:
            key = item['set'], item['point_number']
            if REVIEWED.get(key) != item['source_frame']:
                raise ValueError(f'Frozen reviewed frame differs: {key}')
            rows.append({'set': key[0], 'point_number': key[1],
                         'source_frame': item['source_frame'],
                         'source_second': item['source_second'],
                         'local_image_phase': 'active_looking_not_exact_event_review',
                         'near_side_six_box_membership': 'six_distinct_near_side_teammates_visible',
                         'wrong_team_raw_track_ids': [],
                         'jersey_identity_continuity': 'not_reviewed',
                         'ground_position_accuracy': 'not_reviewed',
                         'source_sheet': page['path'],
                         'source_sheet_sha256': page['sha256']})
    if {(r['set'], r['point_number']) for r in rows} != set(REVIEWED):
        raise ValueError('Missing or duplicate reviewed point')
    result = {
        'status': 'single_reviewer_local_source_box_membership_not_independent_validation',
        'source_sha256': index['source_sha256'],
        'review_index_sha256': digest(INDEX),
        'summary': {'reviewed_local_frames': len(rows),
                    'six_distinct_near_side_teammates_visible': sum(
                        r['near_side_six_box_membership'] == 'six_distinct_near_side_teammates_visible'
                        for r in rows),
                    'rejected_wrong_team_candidate_frames': 1,
                    'validated_whole_rally_trajectories': 0,
                    'validated_metric_frames': 0},
        'rejected_candidate': REJECTED_FRAME,
        'replacement_review_index_sha256': digest(REPLACEMENT_INDEX),
        'limitations': 'One source frame per point was reviewed against its detector overlay and shoe-level crops. Set 1 point 37 frame 10722 raw box 87 was rejected as a far-side white player; frame 10488 was visually checked as a replacement. Raw track IDs are not jersey identities. Neither the full interval nor court-ground positions were validated, and this is not an independent human reference.',
        'rows': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
