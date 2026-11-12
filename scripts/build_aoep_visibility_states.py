"""Create six-slot review states for AoEP's dense slice without invented boxes."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
DRAFT = DIR / 'anchor_interpolation_75180_75229/draft.json'
GAPS = DIR / 'dense_review_gap_audit.json'
OUT = DIR / 'dense_visibility_states.json'
FIRST, LAST = 75180, 75229

# Source crops inspected alongside frozen raw boxes. These are development
# observations, not independent frame-by-frame annotations.
SOURCE_REVIEWED_GAPS = {
    'yellow_centre_left': (75206, 75229, 'partly_visible_behind_yellow_4_no_distinct_raw_box'),
    'yellow_right_entrant': (75216, 75226, 'visible_at_right_no_usable_full_player_raw_box'),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_for(frame, draft_row, navigation_row):
    player_id = draft_row['visual_player_id']
    if player_id in SOURCE_REVIEWED_GAPS:
        first, last, reviewed_status = SOURCE_REVIEWED_GAPS[player_id]
        if first <= frame <= last:
            return reviewed_status, None
    if draft_row['draft_status'] == 'requires_source_frame_review':
        return 'edge_first_visibility_unknown', None
    if draft_row['visibility'] == 'out_of_frame':
        return 'out_of_frame_provisional', None
    if navigation_row['navigation_status'] == 'single_box_candidate':
        return 'raw_box_candidate_unverified', navigation_row['candidate_raw_track_id']
    if navigation_row['navigation_status'] == 'ambiguous_close_boxes':
        return 'raw_box_ambiguous', None
    return 'visible_status_unresolved', None


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    draft = json.loads(DRAFT.read_text(encoding='utf-8'))
    gaps = json.loads(GAPS.read_text(encoding='utf-8'))
    if gaps['draft_sha256'] != sha256(DRAFT) or gaps['source_sha256'] != draft['source_sha256']:
        raise ValueError('Draft/gap provenance mismatch')
    frames = {}
    counts = Counter()
    for frame in range(FIRST, LAST + 1):
        draft_rows = draft['frames'][str(frame)]
        navigation = gaps['frames'][str(frame)]
        if len(draft_rows) != 6 or len(navigation) != 6:
            raise ValueError(f'Expected six player slots at frame {frame}')
        rows = []
        for source_row, nav_row in zip(draft_rows, navigation):
            if source_row['visual_player_id'] != nav_row['visual_player_id']:
                raise ValueError('Player order mismatch')
            status, candidate_id = state_for(frame, source_row, nav_row)
            rows.append({'visual_player_id': source_row['visual_player_id'],
                         'observation_status': status,
                         'candidate_raw_track_id': candidate_id,
                         'bbox': None,
                         'court_position': None,
                         'court_position_status': source_row['court_position_status']})
            counts[status] += 1
        frames[str(frame)] = rows
    payload = {
        'status': 'development_visibility_states_not_ground_truth_or_tracker_output',
        'source_sha256': draft['source_sha256'],
        'draft_sha256': sha256(DRAFT), 'gap_audit_sha256': sha256(GAPS),
        'frame_range_inclusive': [FIRST, LAST],
        'reviewed_gap_intervals': {player_id: {'frames_inclusive': [first, last], 'status': status}
                                   for player_id, (first, last, status) in SOURCE_REVIEWED_GAPS.items()},
        'evidence_crops': ['centre_left_gap_source_raw_review.jpg',
                           'right_entrant_gap_source_raw_review.jpg'],
        'interpretation': 'Each frame has six provisional visual-player slots. None supplies a new bbox or court coordinate; raw candidate IDs are navigation references only. An unboxed visible person must not be counted as a detector observation, assigned a new raw ID, or given a movement metric.',
        'observation_status_counts': dict(counts),
        'frames': frames,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(dict(counts))


if __name__ == '__main__':
    main()
