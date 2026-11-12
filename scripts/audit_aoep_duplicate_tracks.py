"""Find simultaneous near-identical AoEP raw boxes in the dense slice.

Only a pair supported by two source-frame visual anchors is proposed for
same-person deduplication. All other overlaps stay unresolved.
"""

import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path

from audit_aoep_visual_anchor_ids import iou


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
RAW = DIR / 'raw_74880_75540.json'
LEDGER = DIR / 'visual_anchor_id_ledger.json'
OUT = DIR / 'duplicate_track_audit.json'
FIRST, LAST = 75180, 75229
MIN_BOX_IOU = .60
MIN_ANCHOR_SUPPORT_FRAMES = 2


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def anchor_support(ledger, pair):
    support = []
    for frame, rows in ledger['frames'].items():
        for row in rows:
            options = {r['raw_track_id']: r['iou'] for r in row['raw_box_options']}
            if all(track_id in options for track_id in pair):
                support.append({'frame': int(frame),
                                'visual_player_id': row['visual_player_id'],
                                'option_ious': {str(track_id): options[track_id]
                                                for track_id in pair}})
    return support


def suppress_supported_duplicates(rows, supported_pairs):
    """Return a derived per-frame view; raw rows are never modified."""
    by_id = {int(row['track_id']): row for row in rows}
    suppressed = []
    for first, second in supported_pairs:
        if first not in by_id or second not in by_id:
            continue
        if iou(by_id[first]['bbox'], by_id[second]['bbox']) < MIN_BOX_IOU:
            continue
        winner = max((first, second), key=lambda tid: (by_id[tid]['confidence'], -tid))
        loser = second if winner == first else first
        suppressed.append({'retained_raw_track_id': winner,
                           'suppressed_raw_track_id': loser})
    suppressed_ids = {item['suppressed_raw_track_id'] for item in suppressed}
    return [dict(row) for row in rows if int(row['track_id']) not in suppressed_ids], suppressed


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    if raw['source_sha256'] != ledger['source_sha256'] or ledger['raw_sha256'] != sha256(RAW):
        raise ValueError('Frozen evidence mismatch')
    pair_frames = defaultdict(list)
    for frame in range(FIRST, LAST + 1):
        for a, b in itertools.combinations(raw['predictions'][str(frame)], 2):
            overlap = iou(a['bbox'], b['bbox'])
            if overlap >= MIN_BOX_IOU:
                pair = tuple(sorted((int(a['track_id']), int(b['track_id']))))
                pair_frames[pair].append({'frame': frame, 'box_iou': round(overlap, 3)})
    pairs = []
    for pair, overlap_frames in sorted(pair_frames.items(), key=lambda item: (-len(item[1]), item[0])):
        support = anchor_support(ledger, pair)
        same_subject = {item['visual_player_id'] for item in support}
        status = ('same_person_duplicate_candidate' if
                  len(support) >= MIN_ANCHOR_SUPPORT_FRAMES and len(same_subject) == 1 else
                  'unresolved_overlap')
        pairs.append({'raw_track_ids': list(pair), 'cooccurring_high_overlap_frames': overlap_frames,
                      'source_visual_anchor_support': support,
                      'diagnostic_status': status})
    supported_pairs = [tuple(p['raw_track_ids']) for p in pairs
                       if p['diagnostic_status'] == 'same_person_duplicate_candidate']
    derived = {}
    suppression_events = []
    raw_count = 0
    for frame in range(FIRST, LAST + 1):
        rows = raw['predictions'][str(frame)]
        selected, suppressed = suppress_supported_duplicates(rows, supported_pairs)
        derived[str(frame)] = selected
        raw_count += len(rows)
        suppression_events.extend({'frame': frame, **item} for item in suppressed)
    payload = {
        'status': 'duplicate_diagnostic_no_raw_boxes_removed',
        'source_sha256': raw['source_sha256'], 'raw_sha256': sha256(RAW),
        'visual_anchor_ledger_sha256': sha256(LEDGER),
        'frame_range_inclusive': [FIRST, LAST],
        'thresholds': {'minimum_box_iou': MIN_BOX_IOU,
                       'minimum_visual_anchor_support_frames': MIN_ANCHOR_SUPPORT_FRAMES},
        'interpretation': 'Derived rows omit the lower-confidence box only when a source-anchor-supported pair overlaps in that frame. This is a development proposal, not an ID merge or ground truth. The frozen raw detections remain unchanged.',
        'pairs': pairs,
        'derived_slice': {'raw_box_count': raw_count,
                          'derived_box_count': sum(map(len, derived.values())),
                          'suppression_events': suppression_events,
                          'rows_by_frame': derived},
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print([(p['raw_track_ids'], len(p['cooccurring_high_overlap_frames']),
            p['diagnostic_status']) for p in pairs])


if __name__ == '__main__':
    main()
