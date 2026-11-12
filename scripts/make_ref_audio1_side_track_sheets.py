"""Create every-frame crops for selected frozen reference-match tracks."""

import hashlib
import json
import math
import argparse
from pathlib import Path

import cv2
import numpy as np


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
OUT = BASE / 'track_review_sheets.json'
IDS = (1, 2, 3, 8, 11, 12, 33, 67, 81)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tile(image, frame, row):
    x1, y1, x2, y2 = (int(round(value)) for value in row['bbox'])
    width, height = image.shape[1], image.shape[0]
    mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
    left = max(0, min(width - 220, mid_x - 110))
    top = max(0, min(height - 220, mid_y - 110))
    crop = image[top:top + 220, left:left + 220].copy()
    cv2.rectangle(crop, (x1 - left, y1 - top), (x2 - left, y2 - top),
                  (0, 255, 255), 2)
    crop = cv2.resize(crop, (260, 260))
    cv2.rectangle(crop, (0, 0), (259, 34), (0, 0, 0), -1)
    cv2.putText(crop, f'ID {row["track_id"]} f{frame}', (8, 25),
                cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2,
                cv2.LINE_AA)
    return crop


def make_sheets(raw_path=RAW, out=OUT, ids=IDS, source=SOURCE):
    if out.exists():
        raise FileExistsError(out)
    data = json.loads(raw_path.read_text(encoding='utf-8'))
    if data['source_sha256'] != sha256(source):
        raise ValueError('Frozen predictions and source mismatch')
    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise FileNotFoundError(source)
    tiles = {track_id: [] for track_id in ids}
    frames = {track_id: [] for track_id in ids}
    try:
        for frame in range(data['first_frame'], data['last_frame'] + 1):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            rows = {int(row['track_id']): row for row in data['predictions'][str(frame)]}
            for track_id in ids:
                if track_id in rows:
                    tiles[track_id].append(tile(image, frame, rows[track_id]))
                    frames[track_id].append(frame)
    finally:
        video.release()
    output = []
    for track_id in ids:
        if not tiles[track_id]:
            continue
        cols = 7
        rows = math.ceil(len(tiles[track_id]) / cols)
        sheet = np.full((rows * 260, cols * 260, 3), 35, dtype=np.uint8)
        for i, part in enumerate(tiles[track_id]):
            y, x = divmod(i, cols)
            sheet[y * 260:(y + 1) * 260, x * 260:(x + 1) * 260] = part
        path = out.parent / f'track_{track_id}_all.jpg'
        if not cv2.imwrite(str(path), sheet):
            raise RuntimeError(f'Cannot save {path}')
        output.append({'track_id': track_id, 'frames': frames[track_id],
                       'sheet': path.name})
    out.write_text(json.dumps({
        'status': 'review_material', 'source_sha256': data['source_sha256'],
        'raw_sha256': sha256(raw_path), 'tracks': output,
    }, indent=2) + '\n', encoding='utf-8')
    print([(row['track_id'], len(row['frames'])) for row in output])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=RAW)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--ids', type=int, nargs='+', default=IDS)
    parser.add_argument('--source', type=Path, default=SOURCE)
    args = parser.parse_args()
    make_sheets(args.raw, args.out, tuple(args.ids), args.source)


if __name__ == '__main__':
    main()
