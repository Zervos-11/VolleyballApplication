"""Exploratory full-width net-tape check on reviewed near/far tracks."""

import hashlib
import json
from pathlib import Path

import cv2

from net_tape_full_box import full_box_tape_span


ROOT = Path('data/matches/yt_em6zFUxfYpc')
BASE = Path('data/processed/pilot_tracker_evaluation/net_cue_trial')
LABELS = BASE / 'fresh_side_labels_1030_1079.json'
PRED = Path('data/processed/heldout_crossing_eval_em6z/fresh_airborne_segment.json')
OUT = BASE / 'full_box_span_audit_y624.json'
LINE = ((70, 624), (1515, 624))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text())
    predictions = json.loads(PRED.read_text())
    source = ROOT / 'heldout_source_cfr.mp4'
    if hashlib.sha256(source.read_bytes()).hexdigest() != predictions['source_sha256']:
        raise ValueError('Source hash mismatch')
    groups = []
    for item in labels['tracks']:
        observations = []
        for frame in range(1030, 1080):
            observations.extend((frame, box['bbox']) for box in
                                predictions['raw_predictions'][str(frame)]
                                if box['track_id'] == item['track_id'])
        groups.append({**item, 'key': f"fresh:{item['track_id']}",
                       'observations': observations})
    for window in ('cross_a', 'cross_b'):
        annotations = json.loads((ROOT / 'pilot/player_annotations' / f'{window}.json').read_text())
        by_player = {}
        for frame, record in annotations['frames'].items():
            for player in record['players']:
                if player.get('bbox') is not None:
                    by_player.setdefault(player['player_id'], []).append(
                        (int(frame), player['bbox']))
        groups.extend({'key': f'{window}:{player_id}', 'side': 'near',
                       'description': 'existing near-side annotation',
                       'observations': values}
                      for player_id, values in by_player.items())

    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise FileNotFoundError(source)
    cache = {}
    try:
        for group in groups:
            rows = []
            for frame, box in sorted(group.pop('observations')):
                if frame not in cache:
                    video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                    ok, image = video.read()
                    if not ok:
                        raise RuntimeError(f'Cannot decode frame {frame}')
                    cache[frame] = image
                value = full_box_tape_span(cache[frame], box, LINE)
                candidate = (value['status'] == 'measured' and
                             value['full_width_fraction'] >= .9 and
                             value['left_edge_fraction'] >= .8 and
                             value['right_edge_fraction'] >= .8 and
                             value['largest_missing_gap_px'] <= 6)
                rows.append({'frame': frame, **value, 'candidate': candidate})
            longest = streak = 0
            previous = None
            for row in rows:
                if row['candidate']:
                    streak = streak + 1 if previous is not None and row['frame'] == previous + 1 else 1
                else:
                    streak = 0
                longest = max(longest, streak)
                previous = row['frame']
            group['rows'] = rows
            group['max_candidate_streak'] = longest
            group['flagged_as_possible_far'] = longest >= 5
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'exploratory_development_only',
        'source_sha256': predictions['source_sha256'],
        'labels_sha256': hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        'rule_sha256': hashlib.sha256(Path('scripts/net_tape_full_box.py').read_bytes()).hexdigest(),
        'line_px': LINE,
        'criterion': {'full_width_fraction_at_least': .9,
                      'each_box_edge_fraction_at_least': .8,
                      'largest_missing_gap_px_at_most': 6,
                      'consecutive_frames_at_least': 5},
        'groups': groups,
    }, indent=2) + '\n', encoding='utf-8')
    for group in groups:
        print(group['key'], group['side'], group['max_candidate_streak'],
              group['flagged_as_possible_far'])


if __name__ == '__main__':
    main()
