"""Render shoe-level source crops for the 15 reviewed six-box navigation frames."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
BASE = MATCH / 'screening'
VIDEO = MATCH / 'source_720p.mp4'
TRACKS = BASE / 'dense_live_track_screen.json'
QC = BASE / 'bracketed_candidate_source_qc.json'
OUT = BASE / 'selected_floor_qc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    assert tracks['source_sha256'] == qc['source_sha256'] == sha(VIDEO)
    lookup = {(p['set'], p['point_number'], f['source_frame']): f
              for p in tracks['points'] for f in p['rows']}
    OUT.mkdir(exist_ok=True)
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError('Could not open source video')
    entries = []
    try:
        for item in qc['rows']:
            key = item['set'], item['point_number'], item['source_frame']
            row = lookup[key]
            boxes = [p for p in row['proposals']
                     if p['net_side_status'] == 'near_floor_side_candidate']
            if len(boxes) != 6:
                raise ValueError(f'Expected exactly six near-side proposals at {key}: {len(boxes)}')
            capture.set(cv2.CAP_PROP_POS_FRAMES, item['source_frame'])
            ok, source = capture.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {item["source_frame"]}')
            sheet = np.full((3 * 250, 2 * 330, 3), 245, np.uint8)
            crops = []
            for i, box in enumerate(sorted(boxes, key=lambda x: x['bbox_px'][0])):
                x1, y1, x2, y2 = box['bbox_px']
                center = (x1 + x2) / 2
                xa = max(0, int(round(center - 110)))
                xb = min(source.shape[1], int(round(center + 110)))
                ya = max(0, int(round(y2 - 155)))
                yb = min(source.shape[0], int(round(y2 + 35)))
                crop = source[ya:yb, xa:xb].copy()
                cv2.line(crop, (int(round(center - xa)) - 7, int(round(y2 - ya))),
                         (int(round(center - xa)) + 7, int(round(y2 - ya))), (0, 0, 255), 1)
                tile = cv2.resize(crop, (330, 210), interpolation=cv2.INTER_CUBIC)
                yy, xx = (i // 2) * 250, (i % 2) * 330
                sheet[yy:yy + 210, xx:xx + 330] = tile
                label = f'#{box["raw_track_id"]} ({box["box_bottom_court_m"][0]:.2f},{box["box_bottom_court_m"][1]:.2f})'
                cv2.putText(sheet, label, (xx + 8, yy + 235), cv2.FONT_HERSHEY_SIMPLEX,
                            .55, (20, 20, 20), 1, cv2.LINE_AA)
                crops.append({'raw_track_id': box['raw_track_id'],
                              'bbox_px': box['bbox_px'],
                              'box_bottom_court_m': box['box_bottom_court_m'],
                              'crop_origin_px': [xa, ya]})
            name = f's{item["set"]}_p{item["point_number"]:02d}_f{item["source_frame"]}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f'Could not write {path}')
            entries.append({'set': item['set'], 'point_number': item['point_number'],
                            'source_frame': item['source_frame'], 'path': name,
                            'sha256': sha(path), 'boxes': crops})
    finally:
        capture.release()
    manifest = {'status': 'single_frame_shoe_level_review_pack_not_position_validation',
                'source_sha256': tracks['source_sha256'],
                'tracks_sha256': sha(TRACKS), 'bracketed_source_qc_sha256': sha(QC),
                'entries': entries}
    (OUT / 'index.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(entries)} floor-level sheets')


if __name__ == '__main__':
    main()
