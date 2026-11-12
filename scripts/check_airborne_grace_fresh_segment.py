"""Run the frozen jump-grace rule on an unlabelled, separate video segment.

This is a qualitative false-alarm check, not a MOT accuracy evaluation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import cv2

from airborne_grace_filter import filter_window
from evaluate_pilot_tracker import image_to_court
from evaluate_team_appearance import filter_rally


MATCH = Path('data/matches/yt_em6zFUxfYpc')
OUT = Path('data/processed/heldout_crossing_eval_em6z/fresh_airborne_segment.json')
FIRST, LAST = 1030, 1079
WARMUP = 25


def main(first=FIRST, last=LAST, out=OUT):
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    if first < WARMUP or last < first:
        raise ValueError('Invalid frame interval')
    os.environ['YOLO_CONFIG_DIR'] = str(Path('data/processed/ultralytics_config').resolve())
    from ultralytics import YOLO

    manifest = json.loads((MATCH / 'pilot/heldout_tracking_manifest.json').read_text())
    source = manifest['source_video']
    calibration = json.loads((MATCH / 'pilot/calibration/near_court.json').read_text())
    matrix = image_to_court(calibration)
    model = YOLO('yolov8n.pt')
    video = cv2.VideoCapture(source)
    if not video.isOpened():
        raise FileNotFoundError(source)
    video.set(cv2.CAP_PROP_POS_FRAMES, first - WARMUP)
    raw = {}
    try:
        for frame in range(first - WARMUP, last + 1):
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            tracked = model.track(image, tracker='bytetrack.yaml', persist=True,
                                  conf=0.20, imgsz=960, verbose=False)[0]
            if frame < first:
                continue
            people = []
            boxes = tracked.boxes
            if boxes is not None and len(boxes):
                ids = (boxes.id.cpu().numpy() if boxes.id is not None
                       else [-1] * len(boxes))
                for box, cls, confidence, track_id in zip(
                        boxes.xyxy.cpu().numpy(), boxes.cls.cpu().numpy(),
                        boxes.conf.cpu().numpy(), ids):
                    if int(cls) == 0:
                        people.append({
                            'bbox': [round(float(value), 3) for value in box],
                            'confidence': round(float(confidence), 5),
                            'track_id': int(track_id)})
            raw[str(frame)] = people
        schedule = {'frames': {str(frame): None for frame in range(first, last + 1)}}
        base, base_diagnostic = filter_rally(
            video, 'fresh_airborne_segment', schedule, {'predictions': raw}, matrix)
        grace, grace_diagnostic = filter_window(
            video, raw, base['predictions'], matrix, first, last, manifest['fps'])
    finally:
        video.release()
    result = {
        'source_sha256': manifest['source_sha256'],
        'segment': [first, last], 'warmup_frames': WARMUP,
        'labels_available': False,
        'rule': 'airborne_grace_filter.py frozen after the scored-window diagnostic',
        'rule_sha256': hashlib.sha256(
            (Path(__file__).parent / 'airborne_grace_filter.py').read_bytes()).hexdigest(),
        'counts': {'raw': sum(map(len, raw.values())),
                   'court_jersey': sum(map(len, base['predictions'].values())),
                   'airborne_grace': sum(map(len, grace.values()))},
        'base_diagnostics': base_diagnostic,
        'grace_diagnostics': grace_diagnostic,
        'raw_predictions': raw, 'court_jersey_predictions': base['predictions'],
        'airborne_grace_predictions': grace,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['counts'])
    print(f"Rescued: {grace_diagnostic['rescued']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--first', type=int, default=FIRST)
    parser.add_argument('--last', type=int, default=LAST)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    main(args.first, args.last, args.out)
