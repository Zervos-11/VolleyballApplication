"""Screen candidate near-side tracks on a selected backup excerpt window."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402

BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'source_screen.json'
CALIBRATION = BASE / 'near_court_candidate.json'
CLIP = BASE / 'clip_4m50.mp4'
MODEL = ROOT / 'yolov8n.pt'
IMAGE_DIR = BASE / 'live_track_screen_frames'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', type=int, default=345)
    parser.add_argument('--last', type=int, default=375)
    args = parser.parse_args()
    first, last = args.first, args.last
    if first < 0 or last < first:
        parser.error('Frame range must be nonnegative and ordered')
    out = BASE / f'live_track_screen_{first}_{last}.json'
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    if screen['extended_excerpt_sha256'] != sha(CLIP) or calibration['excerpt_sha256'] != sha(CLIP):
        raise ValueError('Source excerpt differs from screening/calibration records')
    matrix = np.asarray(calibration['homography_image_to_court'], np.float64)
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(CLIP))
    if not cap.isOpened():
        raise RuntimeError('Source excerpt unavailable')
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for number in range(first, last + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                raise RuntimeError(f'Could not decode frame {number}')
            result = model.track(image, classes=[0], conf=.2, imgsz=960,
                                 tracker='bytetrack.yaml', persist=True, verbose=False)[0]
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(boxes)
            accepted = []
            for box, score, track_id in zip(boxes, scores, ids):
                x1, y1, x2, y2 = map(float, box)
                floor = cv2.perspectiveTransform(
                    np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), matrix)[0, 0]
                if not np.isfinite(floor).all() or not ((floor >= -0.25) & (floor <= 9.25)).all():
                    continue
                accepted.append({'raw_track_id': track_id,
                                 'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                 'box_bottom_court_m': [round(float(v), 3) for v in floor],
                                 'confidence': round(float(score), 3)})
                if number % 5 == 0:
                    cv2.rectangle(image, (round(x1), round(y1)), (round(x2), round(y2)),
                                  (0, 190, 0), 2)
                    cv2.putText(image, f'raw {track_id}', (round(x1), max(20, round(y1) - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 255), 2)
            if number % 5 == 0:
                path = IMAGE_DIR / f'frame_{number:03d}.jpg'
                if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                    raise RuntimeError(f'Could not write {path}')
            rows.append({'excerpt_frame': number, 'near_court_proposal_count': len(accepted),
                         'near_court_proposals': accepted})
    finally:
        cap.release()
    counts = [r['near_court_proposal_count'] for r in rows]
    output = {'status': 'staged_near_court_track_proposals_not_reviewed_player_identities',
              'video_id': screen['video_id'], 'excerpt_sha256': sha(CLIP),
              'calibration_sha256': sha(CALIBRATION), 'detector_sha256': sha(MODEL),
              'frame_range_inclusive': [first, last],
              'method': 'YOLOv8n + ByteTrack, person conf=.20 imgsz=960, staged box-bottom near-court gate -0.25 to 9.25 m',
              'frames_with_at_least_six_proposals': sum(n >= 6 for n in counts),
              'frames_with_exactly_six_proposals': sum(n == 6 for n in counts),
              'minimum_near_court_proposals': min(counts),
              'maximum_near_court_proposals': max(counts),
              'rows': rows,
              'limitations': ['Staged homography is not validated for player-floor accuracy.',
                              'Raw track IDs are not jersey identities or independently reviewed.',
                              'Near-court gate can admit opponents or omit airborne/off-court teammates.',
                              'Candidate rally endpoints are bracketed visually, not exact frame labels.']}
    out.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print({k: output[k] for k in ('frames_with_at_least_six_proposals',
                                   'frames_with_exactly_six_proposals',
                                   'minimum_near_court_proposals',
                                   'maximum_near_court_proposals')})


if __name__ == '__main__':
    main()
