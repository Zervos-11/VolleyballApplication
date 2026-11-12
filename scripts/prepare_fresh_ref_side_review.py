"""Render neutral ID overlays from a frozen raw tracking window for side review."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4'))
    parser.add_argument('--frames', type=int, nargs='+', required=True)
    args = parser.parse_args()
    raw = json.loads(args.raw.read_text(encoding='utf-8'))
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != raw['source_sha256']:
        raise ValueError('Frozen source hash mismatch')
    cap = cv2.VideoCapture(str(args.source))
    if not cap.isOpened():
        raise FileNotFoundError(args.source)
    try:
        for frame in args.frames:
            if str(frame) not in raw['predictions']:
                raise ValueError(f'Frame {frame} not in frozen window')
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise ValueError(f'Could not decode frame {frame}')
            for row in raw['predictions'][str(frame)]:
                x1, y1, x2, y2 = (int(round(v)) for v in row['bbox'])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(image, str(row['track_id']), (x1, max(24, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(image, str(row['track_id']), (x1, max(24, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
            out = args.raw.parent / f'raw_overlay_{frame}.jpg'
            if not cv2.imwrite(str(out), image):
                raise RuntimeError(f'Could not save {out}')
            print(out)
    finally:
        cap.release()


if __name__ == '__main__':
    main()
