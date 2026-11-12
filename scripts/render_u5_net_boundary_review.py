"""Render every net-boundary candidate for source-image adjudication."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
SCREEN = BASE / 'screening/net_side_gate_screen.json'
OUT = BASE / 'screening/net_boundary_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    rows = [r for r in screen['rows'] if r['net_boundary_review_count']]
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    crops = []
    try:
        for i in range(0, len(rows), 6):
            sheet = np.full((3 * 395, 2 * 640, 3), 240, np.uint8)
            for j, row in enumerate(rows[i:i + 6]):
                cap.set(cv2.CAP_PROP_POS_FRAMES, row['source_frame'])
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode frame {row['source_frame']}")
                cv2.line(image, (297, 313), (1046, 313), (0, 255, 255), 2)
                boundary_number = 0
                for proposal in row['proposals']:
                    x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                    boundary = proposal['net_side_status'] == 'net_boundary_review'
                    color = (0, 0, 255) if boundary else (0, 190, 0)
                    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                    if boundary:
                        boundary_number += 1
                        cv2.putText(image, str(boundary_number), (x1 + 3, y1 + 22),
                                    cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2)
                        xa, xb = max(0, x1 - 75), min(image.shape[1], x2 + 75)
                        ya, yb = max(0, y1 - 65), min(image.shape[0], y2 + 65)
                        crop = image[ya:yb, xa:xb]
                        tile = np.full((300, 280, 3), 240, np.uint8)
                        scale = min(280 / crop.shape[1], 270 / crop.shape[0])
                        resized = cv2.resize(crop, (round(crop.shape[1] * scale),
                                                     round(crop.shape[0] * scale)))
                        tile[:resized.shape[0], :resized.shape[1]] = resized
                        cv2.putText(tile, f"{row['source_second']}s box{boundary_number}",
                                    (5, 290), cv2.FONT_HERSHEY_SIMPLEX, .6, (10, 10, 10), 1)
                        crops.append(tile)
                x, y = (j % 2) * 640, (j // 2) * 395
                sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                           interpolation=cv2.INTER_AREA)
                cv2.putText(sheet, f"S{row['set']} P{row['point_number']} "
                            f"{row['source_second']}s near={row['near_floor_side_candidate_count']} "
                            f"review={row['net_boundary_review_count']}",
                            (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX, .58,
                            (20, 20, 20), 1)
            if not cv2.imwrite(str(OUT / f'sheet_{i // 6 + 1}.jpg'), sheet,
                               [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError('Could not write review sheet')
    finally:
        cap.release()
    crop_sheet = np.full((7 * 300, 4 * 280, 3), 240, np.uint8)
    for index, crop in enumerate(crops):
        x, y = (index % 4) * 280, (index // 4) * 300
        crop_sheet[y:y + 300, x:x + 280] = crop
    if not cv2.imwrite(str(OUT / 'boundary_crops.jpg'), crop_sheet,
                       [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise RuntimeError('Could not write boundary crop sheet')
    (OUT / 'index.json').write_text(json.dumps({
        'screen_sha256': digest(SCREEN), 'video_sha256': digest(VIDEO),
        'boundary_frames': len(rows), 'boundary_boxes': sum(r['net_boundary_review_count'] for r in rows),
        'sheets': [f'sheet_{i + 1}.jpg' for i in range((len(rows) + 5) // 6)] + ['boundary_crops.jpg'],
        'seconds': [r['source_second'] for r in rows]
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(rows)} boundary frames')


if __name__ == '__main__':
    main()
