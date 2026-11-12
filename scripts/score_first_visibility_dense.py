"""Summarize dense raw tracks matched to two first-visible labelled players."""

import hashlib
import json
from pathlib import Path

from evaluate_pilot_tracker import iou


MATCH = Path('data/matches/yt_FqE5pTJqx8g/pilot/player_annotations')
ROOT = Path('data/processed/pilot_tracker_evaluation/start_boundary_audit')
OUT = ROOT / 'first_visibility_dense_diagnostic.json'
EVENTS = {'r3': ('12', 96650), 'r5': ('8', 176290)}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    result = {'scope': ('Two visually checked first-visibility episodes. Raw track IDs '
                        'are matched at one annotated anchor; this is not dense manual '
                        'box ground truth or proof of identity in earlier frames.'),
              'events': {}}
    for rally, (player_id, anchor) in EVENTS.items():
        path = ROOT / f'{rally}_first_visibility_dense_raw.json'
        raw = json.loads(path.read_text())
        label_path = MATCH / f'{rally}.json'
        labels = json.loads(label_path.read_text())
        person = next(row for row in labels['frames'][str(anchor)]['players']
                      if str(row['player_id']) == player_id)
        matches = sorted(((iou(person['bbox'], row['bbox']), row['track_id'])
                          for row in raw['predictions'][str(anchor)]), reverse=True)
        overlap, track_id = matches[0]
        if overlap < .5:
            raise ValueError(f'{rally}: anchor box has no confident raw match')
        frames = [int(key) for key, rows in raw['predictions'].items()
                  if any(row['track_id'] == track_id for row in rows)]
        consecutive_runs = []
        start = previous = frames[0]
        for frame in frames[1:]:
            if frame != previous + 1:
                consecutive_runs.append([start, previous])
                start = frame
            previous = frame
        consecutive_runs.append([start, previous])
        result['events'][rally] = {
            'player_id': player_id, 'anchor_frame': anchor,
            'anchor_iou': round(overlap, 3), 'raw_track_id': track_id,
            'raw_track_first_frame': min(frames),
            'raw_track_last_frame': max(frames),
            'raw_track_observed_frames': len(frames),
            'raw_track_consecutive_runs': consecutive_runs,
            'raw_predictions_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'labels_sha256': hashlib.sha256(label_path.read_bytes()).hexdigest(),
            'source_review_sheet': str(ROOT / f'{rally}_first_visibility_source.jpg'),
            'overlay_sheet': str(ROOT / f'{rally}_first_visibility_tracker_overlay.jpg'),
        }
        print(rally, result['events'][rally]['raw_track_consecutive_runs'])
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
