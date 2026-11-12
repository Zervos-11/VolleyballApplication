"""Render unboxed shoe regions for a bounded box-bottom proxy reference check."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening/live_core_box_screen.json'
VIDEO = BASE / 'source_720p.mp4'
OUT = BASE / 'screening/floor_reference_crops'
SECONDS = (449, 1203)


def main():
    data = json.loads(SCREEN.read_text(encoding='utf-8'))
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    index = []
    try:
        for second in SECONDS:
            row = next(r for r in data['rows'] if r['source_second'] == second)
            cap.set(cv2.CAP_PROP_POS_FRAMES, row['source_frame'])
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f'Could not decode {second} s')
            sheet = np.full((2 * 220, 3 * 300, 3), 240, np.uint8)
            for i, proposal in enumerate(row['proposals']):
                x1, y1, x2, y2 = proposal['bbox_px']
                xa = max(0, round((x1 + x2) / 2) - 125)
                ya = max(0, round(y2) - 140)
                xb, yb = min(image.shape[1], xa + 250), min(image.shape[0], ya + 180)
                crop = image[ya:yb, xa:xb]
                tile = np.full((220, 300, 3), 240, np.uint8)
                tile[:crop.shape[0], :crop.shape[1]] = crop
                cv2.putText(tile, f"{second}s box{i + 1} origin=({xa},{ya})",
                            (5, 205), cv2.FONT_HERSHEY_SIMPLEX, .52, (20, 20, 20), 1)
                x, y = (i % 3) * 300, (i // 3) * 220
                sheet[y:y + 220, x:x + 300] = tile
                index.append({'second': second, 'box_number': i + 1,
                              'crop_origin_px': [xa, ya], 'bbox_px': proposal['bbox_px']})
            if not cv2.imwrite(str(OUT / f'feet_{second}.jpg'), sheet,
                               [cv2.IMWRITE_JPEG_QUALITY, 97]):
                raise RuntimeError('Could not write shoe sheet')
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({'rows': index}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
