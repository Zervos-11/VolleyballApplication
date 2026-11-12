"""Exploratory tape-height brightness profiles on translated body-row spans.

The five source-frame body spans were reviewed by hand. Later spans only
follow box-centre translation; they are not additional manual masks.
"""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


BASE = Path('data/processed/pilot_tracker_evaluation/net_cue_trial')
LABELS = BASE / 'manual_tape_row_spans.json'
OUT = BASE / 'tape_profile_time_audit.json'
SOURCE = Path('data/matches/yt_em6zFUxfYpc/heldout_source_cfr.mp4')
FRESH = Path('data/processed/heldout_crossing_eval_em6z/fresh_airborne_segment.json')
CROSS_B = Path('data/matches/yt_em6zFUxfYpc/pilot/player_annotations/cross_b.json')


def boxes_for(example, fresh, cross_b):
    if 'source_track_id' in example:
        track_id = example['source_track_id']
        return {int(frame): box['bbox'] for frame, boxes in fresh['raw_predictions'].items()
                for box in boxes if box['track_id'] == track_id}
    player_id = example['source_player_id'].split(':')[1]
    return {int(frame): player['bbox'] for frame, record in cross_b['frames'].items()
            for player in record['players']
            if player['player_id'] == player_id and player.get('bbox') is not None}


def profile_score(image, left, right):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if left < 0 or right > gray.shape[1] or right <= left:
        return None
    profile = np.median(gray[606:643, left:right], axis=1)
    center = float(np.mean(profile[622-606:627-606]))
    shoulders = float((np.mean(profile[615-606:619-606]) +
                       np.mean(profile[630-606:634-606])) / 2)
    return {'peak_minus_shoulders': round(center - shoulders, 1),
            'center_brightness': round(center, 1),
            'shoulder_brightness': round(shoulders, 1)}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text())
    fresh = json.loads(FRESH.read_text())
    cross_b = json.loads(CROSS_B.read_text())
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != fresh['source_sha256']:
        raise ValueError('Source hash mismatch')
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    groups = []
    try:
        for example in labels['examples']:
            boxes = boxes_for(example, fresh, cross_b)
            reference = boxes[example['frame']]
            reference_center = (reference[0] + reference[2]) / 2
            rows = []
            for frame, box in sorted(boxes.items()):
                if not box[1] + 12 <= 624 <= box[3] - 12:
                    continue
                shift = round((box[0] + box[2]) / 2 - reference_center)
                left, right = [x + shift for x in example['body_x_px']]
                video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode frame {frame}')
                score = profile_score(image, left, right)
                if score is not None:
                    rows.append({'frame': frame, 'translated_body_x_px': [left, right], **score})
            values = [row['peak_minus_shoulders'] for row in rows]
            groups.append({**example, 'eligible_frames': len(rows),
                           'median_peak_minus_shoulders': round(float(np.median(values)), 1) if values else None,
                           'p10_peak_minus_shoulders': round(float(np.percentile(values, 10)), 1) if values else None,
                           'p90_peak_minus_shoulders': round(float(np.percentile(values, 90)), 1) if values else None,
                           'rows': rows})
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'exploratory_development_only',
        'source_sha256': fresh['source_sha256'],
        'manual_spans_sha256': hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        'method': 'Translate each one-frame hand-reviewed body span by the box-centre displacement; compare mean gray level y=622..626 with y=615..618 and y=630..633.',
        'limitation': 'Translated spans are approximate; brightness is not a direct foreground-depth or team measurement.',
        'groups': groups,
    }, indent=2) + '\n', encoding='utf-8')
    for group in groups:
        print(group['key'], group['side'], group['eligible_frames'],
              group['median_peak_minus_shoulders'],
              group['p10_peak_minus_shoulders'], group['p90_peak_minus_shoulders'])


if __name__ == '__main__':
    main()
