"""Render the longer u5HnY2aNW14 excerpt around the candidate point."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
RECORD = BASE / 'source_screen.json'
CLIP = BASE / 'clip_4m50.mp4'
OUT = BASE / 'clip_4m50_context.jpg'
PICKS = list(range(0, 601, 60))
W, H, FOOT = 480, 270, 28


def sheet(cap, picks, out):
    canvas = np.full((3 * (H + FOOT), 4 * W, 3), 245, np.uint8)
    for i, number in enumerate(picks):
        cap.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, image = cap.read()
        if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
            raise RuntimeError(f'Could not decode frame {number}')
        x, y = (i % 4) * W, (i // 4) * (H + FOOT)
        canvas[y:y + H, x:x + W] = cv2.resize(image, (W, H), interpolation=cv2.INTER_AREA)
        cv2.putText(canvas, f'f{number} | +{number / 30:.1f}s', (x + 6, y + H + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, .5, (25, 25, 25), 1)
    if not cv2.imwrite(str(out), canvas, [cv2.IMWRITE_JPEG_QUALITY, 93]):
        raise RuntimeError(f'Could not write {out}')


def main():
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    if hashlib.sha256(CLIP.read_bytes()).hexdigest() != record['extended_excerpt_sha256']:
        raise ValueError('Excerpt hash differs from source record')
    cap = cv2.VideoCapture(str(CLIP))
    if not cap.isOpened() or round(cap.get(cv2.CAP_PROP_FPS)) != 30:
        raise RuntimeError('Excerpt unavailable or unexpected frame rate')
    try:
        sheet(cap, PICKS, OUT)
        sheet(cap, list(range(225, 390, 15)), BASE / 'clip_4m50_serve_search.jpg')
        sheet(cap, list(range(405, 515, 10)), BASE / 'clip_4m50_end_search.jpg')
    finally:
        cap.release()
    print(OUT)


if __name__ == '__main__':
    main()
