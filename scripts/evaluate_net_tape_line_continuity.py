"""Exploratory exact-height tape check on existing near/far side labels."""

import hashlib
import json
from pathlib import Path

import cv2

from net_tape_line_continuity import line_continuity


ROOT = Path('data/matches/yt_em6zFUxfYpc')
BASE = Path('data/processed/pilot_tracker_evaluation/net_cue_trial')
LABELS = BASE / 'fresh_side_labels_1030_1079.json'
PRED = Path('data/processed/heldout_crossing_eval_em6z/fresh_airborne_segment.json')
OUT = BASE / 'line_continuity_audit_y624.json'
# Source-frame crop at frame 1030 puts the bright centre near y=624;
# the earlier y=618 calibration falls on its upper edge.
LINE = ((70, 624), (1515, 624))


def streaks(rows):
    streak = 0
    longest = 0
    previous = None
    for row in rows:
        if row['candidate'] and previous is not None and row['frame'] == previous + 1:
            streak += 1
        elif row['candidate']:
            streak = 1
        else:
            streak = 0
        longest = max(longest, streak)
        previous = row['frame']
    return longest


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text())
    pred = json.loads(PRED.read_text())
    source = ROOT / 'heldout_source_cfr.mp4'
    if hashlib.sha256(source.read_bytes()).hexdigest() != pred['source_sha256']:
        raise ValueError('Source hash mismatch')
    boxes = {}
    for frame in range(1030, 1080):
        for box in pred['raw_predictions'][str(frame)]:
            boxes.setdefault(('fresh', box['track_id']), []).append((frame, box['bbox']))
    groups = [{**item, 'key': f"fresh:{item['track_id']}",
               'observations': boxes.get(('fresh', item['track_id']), [])}
              for item in labels['tracks']]
    for window in ('cross_a', 'cross_b'):
        annotations = json.loads((ROOT / 'pilot/player_annotations' / f'{window}.json').read_text())
        keyed = {}
        for frame, record in annotations['frames'].items():
            for player in record['players']:
                if player.get('bbox') is not None:
                    keyed.setdefault(player['player_id'], []).append((int(frame), player['bbox']))
        groups.extend({'key': f'{window}:{player_id}', 'side': 'near',
                       'description': 'existing near-side annotation', 'observations': values}
                      for player_id, values in keyed.items())

    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise FileNotFoundError(source)
    frame_cache = {}
    try:
        for group in groups:
            rows = []
            for frame, box in sorted(group.pop('observations')):
                if frame not in frame_cache:
                    video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                    ok, image = video.read()
                    if not ok:
                        raise RuntimeError(f'Cannot decode frame {frame}')
                    frame_cache[frame] = image
                value = line_continuity(frame_cache[frame], box, LINE)
                candidate = (value['status'] == 'measured' and
                             value['exact_line_fraction'] >= .8 and
                             value['longest_run_fraction'] >= .4 and
                             value['left_flank_fraction'] is not None and
                             value['right_flank_fraction'] is not None and
                             value['left_flank_fraction'] >= .5 and
                             value['right_flank_fraction'] >= .5)
                rows.append({'frame': frame, **value, 'candidate': candidate})
            group['rows'] = rows
            group['max_candidate_streak'] = streaks(rows)
            group['flagged_as_possible_far'] = group['max_candidate_streak'] >= 5
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'exploratory_development_only',
        'source_sha256': pred['source_sha256'],
        'labels_sha256': hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        'rule_sha256': hashlib.sha256(Path('scripts/net_tape_line_continuity.py').read_bytes()).hexdigest(),
        'line_px': LINE,
        'candidate_criterion': {'inside_exact_line_fraction_at_least': .8,
                                'inside_longest_run_fraction_at_least': .4,
                                'both_flank_fractions_at_least': .5,
                                'consecutive_frames_at_least': 5},
        'groups': groups,
    }, indent=2) + '\n', encoding='utf-8')
    for group in groups:
        print(group['key'], group['side'], group['max_candidate_streak'],
              group['flagged_as_possible_far'])


if __name__ == '__main__':
    main()
