"""Freeze raw ByteTrack boxes on an independent, calibrated match window."""

import hashlib
import json
import os
import argparse
from pathlib import Path

import cv2


SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
CALIBRATION = Path('data/matches/yt_ref_audio1/homography.json')
MODEL = Path('yolov8n.pt')
OUT = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1/raw_320_369.json')
FIRST, LAST, WARMUP = 320, 369, 25


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_window(first=FIRST, last=LAST, warmup=WARMUP, out=OUT,
                  source=SOURCE, calibration=CALIBRATION):
    if out.exists():
        raise FileExistsError(out)
    if first < 0 or last < first or warmup < 0 or first - warmup < 0:
        raise ValueError('Invalid frame interval or warm-up')
    os.environ['YOLO_CONFIG_DIR'] = str(Path('data/processed/ultralytics_config').resolve())
    from ultralytics import YOLO

    model = YOLO(str(MODEL))
    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise FileNotFoundError(source)
    measured_size = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    if calibration is not None:
        expected_size = tuple(json.loads(calibration.read_text(encoding='utf-8'))['image_size'])
        if measured_size != expected_size:
            raise ValueError(f'Source size {measured_size} disagrees with calibration {expected_size}')
    video.set(cv2.CAP_PROP_POS_FRAMES, first - warmup)
    predictions = {}
    try:
        for frame in range(first - warmup, last + 1):
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            result = model.track(image, tracker='bytetrack.yaml', persist=True,
                                 conf=0.20, imgsz=960, verbose=False)[0]
            if frame < first:
                continue
            people = []
            boxes = result.boxes
            if boxes is not None and len(boxes):
                ids = (boxes.id.cpu().numpy() if boxes.id is not None else
                       [-1] * len(boxes))
                for box, kind, confidence, track_id in zip(
                        boxes.xyxy.cpu().numpy(), boxes.cls.cpu().numpy(),
                        boxes.conf.cpu().numpy(), ids):
                    if int(kind) == 0:
                        people.append({
                            'bbox': [round(float(value), 3) for value in box],
                            'confidence': round(float(confidence), 5),
                            'track_id': int(track_id),
                        })
            predictions[str(frame)] = people
    finally:
        video.release()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        'status': 'frozen_before_side_review',
        'source_sha256': sha256(source),
        'calibration_sha256': sha256(calibration) if calibration is not None else None,
        'model_sha256': sha256(MODEL),
        'first_frame': first, 'last_frame': last, 'warmup_frames': warmup,
        'tracker': 'YOLOv8n + ByteTrack; conf=0.20; imgsz=960',
        'predictions': predictions,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Frozen {len(predictions)} frames and {sum(map(len, predictions.values()))} boxes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', type=int, default=FIRST)
    parser.add_argument('--last', type=int, default=LAST)
    parser.add_argument('--warmup', type=int, default=WARMUP)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--calibration', type=Path, default=CALIBRATION)
    parser.add_argument('--no-calibration', action='store_true',
                        help='Freeze raw detector boxes before a new source is calibrated')
    args = parser.parse_args()
    freeze_window(args.first, args.last, args.warmup, args.out,
                  args.source, None if args.no_calibration else args.calibration)


if __name__ == '__main__':
    main()
