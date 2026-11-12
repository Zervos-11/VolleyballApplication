"""Triage the AoEP 50-frame draft against frozen, duplicate-adjusted boxes.

The draft is interpolated and unreviewed. This identifies source frames to
inspect; its counts must not be interpreted as detector recall or IDF1.
"""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from audit_aoep_visual_anchor_ids import compare_frame


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
RAW = DIR / 'raw_74880_75540.json'
ANCHORS = DIR / 'visual_anchors_75180_75229.json'
LEDGER = DIR / 'visual_anchor_id_ledger.json'
DRAFT = DIR / 'anchor_interpolation_75180_75229/draft.json'
DEDUP = DIR / 'duplicate_track_audit.json'
OUT = DIR / 'dense_review_gap_audit.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(frame_statuses):
    """Collapse sorted (frame, status) pairs into inclusive constant-status runs."""
    result = []
    for frame, status in frame_statuses:
        if result and status == result[-1]['status'] and frame == result[-1]['last_frame'] + 1:
            result[-1]['last_frame'] = frame
        else:
            result.append({'first_frame': frame, 'last_frame': frame, 'status': status})
    return result


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    anchors = json.loads(ANCHORS.read_text(encoding='utf-8'))
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    draft = json.loads(DRAFT.read_text(encoding='utf-8'))
    dedup = json.loads(DEDUP.read_text(encoding='utf-8'))
    if not (raw['source_sha256'] == anchors['source_sha256'] == draft['source_sha256'] ==
            dedup['source_sha256'] and draft['visual_anchors_sha256'] == sha256(ANCHORS) and
            dedup['raw_sha256'] == sha256(RAW) and
            dedup['visual_anchor_ledger_sha256'] == sha256(LEDGER)):
        raise ValueError('Input provenance mismatch')
    frames = {}
    by_player = defaultdict(list)
    status_counts = Counter()
    for frame_text, draft_rows in draft['frames'].items():
        frame = int(frame_text)
        selected_rows = dedup['derived_slice']['rows_by_frame'][frame_text]
        navigation = compare_frame(draft_rows, selected_rows)
        rows = []
        for source_row, match in zip(draft_rows, navigation):
            status = ('edge_transition_requires_source_review'
                      if source_row['draft_status'] == 'requires_source_frame_review' else
                      match['association_status'])
            row = {
                'visual_player_id': source_row['visual_player_id'],
                'draft_status': source_row['draft_status'],
                'draft_visibility': source_row['visibility'],
                'court_position_status': source_row['court_position_status'],
                'navigation_status': status,
                'candidate_raw_track_id': match['raw_track_id_one_to_one'],
                'overlap_for_navigation_only': match['iou_for_navigation_only'],
                'raw_box_options': match['raw_box_options'],
            }
            rows.append(row)
            by_player[row['visual_player_id']].append((frame, row))
            status_counts[status] += 1
        frames[frame_text] = rows
    player_summaries = {}
    review_spans = []
    for player_id, timeline in by_player.items():
        grouped = runs([(frame, row['navigation_status']) for frame, row in timeline])
        switches = []
        previous = None
        for frame, row in timeline:
            current = row['candidate_raw_track_id']
            if current is not None and previous is not None and current != previous[1]:
                switches.append({'frame': frame, 'previous_frame': previous[0],
                                 'from_raw_track_id': previous[1], 'to_raw_track_id': current})
            if current is not None:
                previous = (frame, current)
        player_summaries[player_id] = {
            'navigation_status_counts': dict(Counter(row['navigation_status'] for _, row in timeline)),
            'candidate_raw_id_counts': dict(Counter(str(row['candidate_raw_track_id'])
                                                    for _, row in timeline
                                                    if row['candidate_raw_track_id'] is not None)),
            'status_runs': grouped, 'candidate_raw_id_changes': switches,
        }
        for group in grouped:
            if group['status'] not in ('single_box_candidate', 'out_of_frame'):
                review_spans.append({'visual_player_id': player_id, **group})
        for change in switches:
            review_spans.append({'visual_player_id': player_id,
                                 'first_frame': change['frame'],
                                 'last_frame': change['frame'],
                                 'status': 'raw_id_change_requires_source_review',
                                 'details': change})
    review_spans.sort(key=lambda r: (r['first_frame'], r['visual_player_id'], r['status']))
    payload = {
        'status': 'review_navigation_only_not_accuracy',
        'source_sha256': raw['source_sha256'],
        'draft_sha256': sha256(DRAFT),
        'duplicate_adjusted_sha256': sha256(DEDUP),
        'minimum_box_overlap_for_navigation': ledger['thresholds']['minimum_navigation_iou'],
        'interpretation': 'These overlap and ID-change spans use unreviewed interpolated boxes. They direct source-frame review and are not misses, recall, precision, identity accuracy, or ground truth.',
        'navigation_status_counts': dict(status_counts),
        'player_summaries': player_summaries,
        'review_spans': review_spans,
        'frames': frames,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print('Navigation statuses:', dict(status_counts))
    for player_id, summary in player_summaries.items():
        print(player_id, summary['navigation_status_counts'],
              summary['candidate_raw_id_changes'])


if __name__ == '__main__':
    main()
