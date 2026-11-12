"""Render close crops to inspect the ambiguous S3 P34 raw ID 8."""

import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
screen = json.loads((BASE / 'screening/full_clip_track_screen.json').read_text())
point = next(p for p in screen['points'] if (p['set'], p['point_number']) == (3, 34))
rows = {r['source_frame']: r for r in point['rows']}
cap = cv2.VideoCapture(str(BASE / 'source_720p.mp4'))
out = BASE / 'screening/full_clip_run_spotcheck'
for frame in (36000, 36054, 36102):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    okay, image = cap.read()
    assert okay
    item = next(p for p in rows[frame]['proposals'] if p['raw_track_id'] == 8)
    x1, y1, x2, y2 = map(round, item['bbox_px'])
    crop = image[max(0, y1 - 20):min(image.shape[0], y2 + 20),
                 max(0, x1 - 20):min(image.shape[1], x2 + 20)]
    assert cv2.imwrite(str(out / f's3p34_id8_f{frame}.png'), crop)
cap.release()
