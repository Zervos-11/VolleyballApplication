"""Render a reproducible contact sheet for the u5HnY2aNW14 excerpt."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
CLIP = BASE / 'clip_5m.mp4'
RECORD = BASE / 'source_screen.json'
OUT = BASE / 'clip_5m_contact.jpg'
PICKS = [0, 60, 120, 180, 240, 300]


def main():
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    if hashlib.sha256(CLIP.read_bytes()).hexdigest() != record['excerpt_sha256']:
        raise ValueError('Excerpt hash differs from source screen')
    cap = cv2.VideoCapture(str(CLIP))
    if not cap.isOpened() or round(cap.get(cv2.CAP_PROP_FPS)) != 30:
        raise RuntimeError('Excerpt unavailable or unexpected frame rate')
    canvas = np.full((2 * 394, 3 * 640, 3), 245, np.uint8)
    try:
        for i, number in enumerate(PICKS):
            cap.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                raise RuntimeError(f'Could not decode frame {number}')
            x, y = (i % 3) * 640, (i // 3) * 394
            canvas[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360), interpolation=cv2.INTER_AREA)
            cv2.putText(canvas, f'clip frame {number} | +{number / 30:.1f}s',
                        (x + 8, y + 384), cv2.FONT_HERSHEY_SIMPLEX, .65, (25, 25, 25), 2)
    finally:
        cap.release()
    if not cv2.imwrite(str(OUT), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError('Could not write contact sheet')
    print(OUT)


if __name__ == '__main__':
    main()
