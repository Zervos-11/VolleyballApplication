"""Show every proposed bridge box for source-only identity continuity review."""

import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


BASE = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial')
TRIAL = BASE / 'team_membership_bridge_trial_v4.json'
QUEUE = BASE / 'team_bridge_side_review_queue.json'
SOURCE = Path('data/matches/yt_em6zFUxfYpc/heldout_source_cfr.mp4')
OUT = BASE / 'team_bridge_continuity_sheets.json'
SHEETS = BASE / 'continuity_review_frames'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tile(video, frame, box, track_id):
    video.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, image = video.read()
    if not ok:
        raise RuntimeError(f'Cannot decode frame {frame}')
    height, width = image.shape[:2]
    x1, y1, x2, y2 = (int(round(n)) for n in box)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    # Include nearby players and the net while keeping the tracked person large.
    crop_w = max(300, int((x2 - x1) * 3.8))
    crop_h = max(340, int((y2 - y1) * 2.1))
    left = max(0, min(width - crop_w, cx - crop_w // 2))
    top = max(0, min(height - crop_h, cy - crop_h // 2))
    crop = image[top:top + crop_h, left:left + crop_w].copy()
    cv2.rectangle(crop, (x1 - left, y1 - top), (x2 - left, y2 - top),
                  (0, 255, 255), 3)
    crop = cv2.resize(crop, (360, 360))
    cv2.rectangle(crop, (0, 0), (359, 40), (0, 0, 0), -1)
    cv2.putText(crop, f'ID {track_id} | frame {frame}', (9, 29),
                cv2.FONT_HERSHEY_SIMPLEX, .75, (255, 255, 255), 2,
                cv2.LINE_AA)
    return crop


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    queue = json.loads(QUEUE.read_text(encoding='utf-8'))
    trial = json.loads(TRIAL.read_text(encoding='utf-8'))
    if queue['source_sha256'] != sha256(SOURCE) or queue['trial_sha256'] != sha256(TRIAL):
        raise ValueError('Input provenance mismatch')
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    SHEETS.mkdir(parents=True, exist_ok=True)
    output = []
    try:
        for lead in queue['leads']:
            window, track_id = lead['window'], lead['track_id']
            tiles = []
            for frame in lead['proposed_frames']:
                rows = trial['windows'][window]['rescued'][str(frame)]
                row = next((r for r in rows if int(r['track_id']) == track_id), None)
                if row is None:
                    raise ValueError(f'Proposal missing: {window}, {track_id}, {frame}')
                tiles.append(tile(video, frame, row['bbox'], track_id))
            cols = 4
            rows = math.ceil(len(tiles) / cols)
            canvas = np.full((rows * 360, cols * 360, 3), 35, dtype=np.uint8)
            for i, part in enumerate(tiles):
                y, x = divmod(i, cols)
                canvas[y * 360:(y + 1) * 360, x * 360:(x + 1) * 360] = part
            path = SHEETS / f'{window}_track_{track_id}_all.jpg'
            if not cv2.imwrite(str(path), canvas):
                raise RuntimeError(f'Cannot write {path}')
            output.append({'window': window, 'track_id': track_id,
                           'frames': lead['proposed_frames'],
                           'sheet': str(path).replace('\\', '/')})
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'source_review_material', 'source_sha256': queue['source_sha256'],
        'trial_sha256': queue['trial_sha256'], 'queue_sha256': sha256(QUEUE),
        'tracks': output,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'{len(output)} continuity sheets')


if __name__ == '__main__':
    main()
