"""Test higher-resolution detection on source-visible, tracker-zero wins."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))

import cv2
import numpy as np
from ultralytics import YOLO


MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = MATCH / 'screening'
VIDEO = MATCH / 'source_720p.mp4'
INDEX = SCREEN / 'zero_run_source_review/index.json'
MODEL = ROOT / 'yolov8n.pt'
OUT = SCREEN / 'zero_run_high_res_detection'


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    assert index['source_sha256'] == sha(VIDEO)
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    OUT.mkdir(exist_ok=True)
    entries = []
    full_resolution_candidates = {(1, 18): 5371, (2, 14): 16032, (3, 23): 32757}
    try:
        for point in index['entries']:
            rows = []
            sheet = np.full((len(point['source_frames']) * 390, 640, 3), 245, np.uint8)
            for i, frame in enumerate(point['source_frames']):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode {frame}')
                result = model.predict(image, classes=[0], conf=.10, imgsz=1280, verbose=False)[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                scores = result.boxes.conf.cpu().numpy()
                proposals = []
                for box, score in zip(boxes, scores):
                    x1, y1, x2, y2 = map(float, box)
                    # Preserve off-court servers. This broad screen is not a
                    # court-floor membership or ground-contact decision.
                    if y2 < 313 or x2 < 100 or x1 > 1200:
                        continue
                    proposals.append({'bbox_px': [round(float(v), 1) for v in box],
                                      'confidence': round(float(score), 3)})
                proposals.sort(key=lambda p: p['bbox_px'][0])
                overlay = image.copy()
                for j, proposal in enumerate(proposals):
                    x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 210, 0), 2)
                    cv2.putText(overlay, str(j), (x1, max(18, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 190, 0), 2)
                if frame == full_resolution_candidates[point['set'], point['point_number']]:
                    full_name = f's{point["set"]}_p{point["point_number"]:02d}_f{frame}_full.jpg'
                    if not cv2.imwrite(str(OUT / full_name), overlay,
                                       [cv2.IMWRITE_JPEG_QUALITY, 96]):
                        raise RuntimeError(f'Cannot save {full_name}')
                sheet[i*390:i*390+360] = cv2.resize(overlay, (640, 360))
                cv2.putText(sheet, f'S{point["set"]} P{point["point_number"]} f{frame} proposals={len(proposals)}',
                            (8, i*390+382), cv2.FONT_HERSHEY_SIMPLEX, .55, (20, 20, 20), 1)
                rows.append({'source_frame': frame, 'broad_person_proposals': proposals})
            name = f's{point["set"]}_p{point["point_number"]:02d}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Cannot save {path}')
            entries.append({'set': point['set'], 'point_number': point['point_number'],
                            'sheet': name, 'sheet_sha256': sha(path), 'rows': rows})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'status': 'higher_resolution_detector_proposals_not_team_adjudicated',
        'source_sha256': index['source_sha256'], 'zero_run_index_sha256': sha(INDEX),
        'model_sha256': sha(MODEL), 'settings': {'imgsz': 1280, 'confidence': .10,
                                              'classes': [0], 'broad_gate': 'y2>=313, x2>=100, x1<=1200'},
        'entries': entries,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Processed {sum(len(e["rows"]) for e in entries)} source frames')


if __name__ == '__main__':
    main()
