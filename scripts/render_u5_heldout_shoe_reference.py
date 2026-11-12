"""Render enlarged source shoe regions for a held-out box-anchor check."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = MATCH / 'screening'
INDEX = SCREEN / 'selected_floor_qc/index.json'
VIDEO = MATCH / 'source_720p.mp4'
OUT = SCREEN / 'heldout_shoe_reference'
POINTS = {(1, 34), (2, 28), (3, 13), (3, 34)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    assert index['source_sha256'] == sha(VIDEO)
    entries = [e for e in index['entries'] if (e['set'], e['point_number']) in POINTS]
    assert len(entries) == 4
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    result = []
    try:
        for entry in entries:
            cap.set(cv2.CAP_PROP_POS_FRAMES, entry['source_frame'])
            ok, source = cap.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {entry["source_frame"]}')
            sheet = np.full((3 * 260, 2 * 480, 3), 245, np.uint8)
            boxes = []
            for i, box in enumerate(entry['boxes']):
                x1, _, x2, y2 = box['bbox_px']
                center = (x1 + x2) / 2
                xa = max(0, int(round(center - 95)))
                xb = min(source.shape[1], xa + 190)
                ya = max(0, int(round(y2 - 70)))
                yb = min(source.shape[0], ya + 95)
                crop = source[ya:yb, xa:xb].copy()
                for x in range((xa // 20 + 1) * 20, xb, 20):
                    xx = x - xa
                    cv2.line(crop, (xx, 0), (xx, crop.shape[0]-1), (40, 40, 40), 1)
                    cv2.putText(crop, str(x), (xx+1, 10), cv2.FONT_HERSHEY_SIMPLEX,
                                .23, (10, 10, 10), 1)
                for y in range((ya // 20 + 1) * 20, yb, 20):
                    yy = y - ya
                    cv2.line(crop, (0, yy), (crop.shape[1]-1, yy), (40, 40, 40), 1)
                    cv2.putText(crop, str(y), (2, yy-2), cv2.FONT_HERSHEY_SIMPLEX,
                                .23, (10, 10, 10), 1)
                cv2.circle(crop, (round(center)-xa, round(y2)-ya), 4, (0, 0, 255), 1)
                tile = cv2.resize(crop, (480, 220), interpolation=cv2.INTER_NEAREST)
                xx, yy = (i % 2)*480, (i // 2)*260
                sheet[yy:yy+220, xx:xx+480] = tile
                cv2.putText(sheet, f'raw {box["raw_track_id"]}  crop x={xa}..{xb} y={ya}..{yb}',
                            (xx+8, yy+246), cv2.FONT_HERSHEY_SIMPLEX,
                            .53, (20, 20, 20), 1)
                boxes.append({'raw_track_id': box['raw_track_id'], 'bbox_px': box['bbox_px'],
                              'crop_origin_px': [xa, ya], 'crop_end_px': [xb, yb]})
            name = f's{entry["set"]}_p{entry["point_number"]:02d}_f{entry["source_frame"]}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 96]):
                raise RuntimeError(f'Cannot save {path}')
            result.append({'set': entry['set'], 'point_number': entry['point_number'],
                           'source_frame': entry['source_frame'], 'sheet': name,
                           'sha256': sha(path), 'boxes': boxes})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'status': 'source_shoe_reference_review_pack_not_ground_truth',
        'source_sha256': index['source_sha256'],
        'selected_floor_index_sha256': sha(INDEX), 'entries': result,
    }, indent=2) + '\n', encoding='utf-8')
    print('Rendered 4 held-out shoe sheets')


if __name__ == '__main__':
    main()
