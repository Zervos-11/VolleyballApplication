"""Bounded six-frame person-box screen on the elevated-view backup excerpt."""
import hashlib
import json
import os
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402

BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
CLIP = BASE / 'clip_5m.mp4'
SCREEN = BASE / 'source_screen.json'
MODEL = ROOT / 'yolov8n.pt'
OUT = BASE / 'box_screen.json'
IMAGE_DIR = BASE / 'box_screen_frames'
FRAMES = [0, 60, 120, 180, 240, 300]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    if screen['excerpt_sha256'] != sha(CLIP):
        raise ValueError('Excerpt differs from screened source')
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(CLIP))
    if not cap.isOpened():
        raise RuntimeError('Excerpt unavailable')
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1:
                raise RuntimeError(f'Could not decode frame {frame}')
            result = model.predict(image, classes=[0], conf=.2, imgsz=960, verbose=False)[0]
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            proposals = []
            for i, (box, score) in enumerate(zip(boxes, scores)):
                x1, y1, x2, y2 = map(float, box)
                proposals.append({'index': i, 'bbox_px': [round(x, 1) for x in (x1, y1, x2, y2)],
                                  'confidence': round(float(score), 3)})
                cv2.rectangle(image, (round(x1), round(y1)), (round(x2), round(y2)), (0, 190, 0), 2)
                cv2.putText(image, str(i), (round(x1), max(20, round(y1) - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 255), 2)
            path = IMAGE_DIR / f'frame_{frame:03d}.jpg'
            if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                raise RuntimeError(f'Could not write {path}')
            rows.append({'excerpt_frame': frame, 'approx_source_time_s': 300 + frame / 30,
                         'raw_person_box_count': len(proposals), 'proposals': proposals,
                         'indexed_image': str(path.relative_to(ROOT)).replace('\\', '/')})
    finally:
        cap.release()
    output = {'status': 'unreviewed_person_proposals_not_six_player_tracks',
              'video_id': screen['video_id'], 'excerpt_sha256': sha(CLIP),
              'model_sha256': sha(MODEL), 'detector': 'YOLOv8n persons conf=.20 imgsz=960',
              'rows': rows,
              'limitations': ['Raw boxes can include officials and opponents or miss occluded players.',
                              'The selected frames span a point boundary and different phases.',
                              'No IDs, near-team roster, floor positions or court calibration are accepted.']}
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print([(row['excerpt_frame'], row['raw_person_box_count']) for row in rows])


if __name__ == '__main__':
    main()
