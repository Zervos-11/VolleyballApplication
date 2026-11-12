"""Test a foreground-aware raw-box occlusion hold on the AoEP dense slice.

Only current and past frozen boxes are used to generate flags. A hold creates
no person box, court position, or player identity; it expires after eight frames.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluate_crossing_flags import MAX_HOLD_FRAMES, MIN_OVERLAP_OF_SMALLER, overlap_of_smaller


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
RAW = DIR / 'raw_74880_75540.json'
VIDEO = ROOT / 'data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4'
OUT = DIR / 'occlusion_hold_v2.json'
FIRST, LAST = 75180, 75229
REVIEW_IDS = (131, 517)
MAX_ABOVE_BOTTOM_HEIGHT_FRACTION = .10


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plausible_foreground_occluder(missing_box, current_box):
    height = missing_box[3] - missing_box[1]
    if height <= 0:
        return False
    return (overlap_of_smaller(missing_box, current_box) >= MIN_OVERLAP_OF_SMALLER and
            current_box[3] >= missing_box[3] - MAX_ABOVE_BOTTOM_HEIGHT_FRACTION * height)


def raw_flags(predictions, first, last, review_ids):
    last_seen = {}
    rows = {}
    for frame in range(first, last + 1):
        boxes = {int(row['track_id']): row['bbox'] for row in predictions[str(frame)]
                 if int(row['track_id']) >= 0}
        frame_rows = {}
        for track_id in review_ids:
            if track_id in boxes:
                frame_rows[str(track_id)] = {'status': 'visible_raw_box', 'hold_age_frames': 0,
                                             'candidate_occluder_ids': [], 'bbox': boxes[track_id]}
                continue
            previous = last_seen.get(track_id)
            age = frame - previous[0] if previous else None
            if previous is None or age > MAX_HOLD_FRAMES:
                frame_rows[str(track_id)] = {'status': 'no_raw_hold', 'hold_age_frames': age,
                                             'candidate_occluder_ids': [], 'bbox': None}
                continue
            old_box = previous[1]
            partners = [other for other, box in boxes.items()
                        if other != track_id and plausible_foreground_occluder(old_box, box)]
            frame_rows[str(track_id)] = {
                'status': 'possible_foreground_occlusion' if partners else 'missing_unknown',
                'hold_age_frames': age, 'candidate_occluder_ids': partners,
                'bbox': None,
            }
        last_seen.update({track_id: (frame, box) for track_id, box in boxes.items()})
        rows[str(frame)] = frame_rows
    return rows


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(VIDEO):
        raise ValueError('Source/prediction mismatch')
    rows = raw_flags(raw['predictions'], FIRST, LAST, REVIEW_IDS)
    summaries = {}
    for track_id in REVIEW_IDS:
        selected = [(int(frame), values[str(track_id)]) for frame, values in rows.items()]
        summaries[str(track_id)] = {
            'status_counts': dict(Counter(row['status'] for _, row in selected)),
            'possible_occlusion_frames': [frame for frame, row in selected
                                          if row['status'] == 'possible_foreground_occlusion'],
            'missing_unknown_frames': [frame for frame, row in selected
                                       if row['status'] == 'missing_unknown'],
        }
    payload = {
        'status': 'raw_only_occlusion_hold_diagnostic_not_identity',
        'source_sha256': raw['source_sha256'], 'raw_sha256': sha256(RAW),
        'frame_range_inclusive': [FIRST, LAST],
        'review_raw_track_ids': list(REVIEW_IDS),
        'thresholds': {'maximum_hold_frames': MAX_HOLD_FRAMES,
                       'minimum_overlap_of_smaller_box': MIN_OVERLAP_OF_SMALLER,
                       'maximum_occluder_bottom_above_missing_bottom_fraction_of_missing_height': MAX_ABOVE_BOTTOM_HEIGHT_FRACTION},
        'interpretation': 'A possible occlusion is a raw-only warning, not proof of the same person or a continuous raw identity. Elevated overlapping boxes fail the foreground check. Every held frame has null bbox and expires after eight frames; no court position is emitted.',
        'summaries': summaries,
        'frames': rows,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(summaries)


if __name__ == '__main__':
    main()
