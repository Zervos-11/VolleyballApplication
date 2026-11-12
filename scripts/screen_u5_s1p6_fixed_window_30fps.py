"""Screen the source-frozen S1 P6 window at exact 30-fps frames."""

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402


MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = MATCH / 'screening'
PACK = SCREEN / 's1p6_fixed_window_source_review'
VIDEO = MATCH / 'source_720p.mp4'
MODEL = ROOT / 'yolov8n.pt'
PROTOCOL = SCREEN / 'source_only_fixed_window_protocol.json'
REVIEW = PACK / 'completed.csv'
OUT = PACK / 'exact_30fps_candidates.json'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(f'Exact-frame candidate screen already exists: {OUT}')
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    window = next(row for row in protocol['rows'] if
                  (row['set'], row['point_number']) == (1, 6))
    assert REVIEW.exists(), 'Source-only review must be frozen first'
    assert sha(VIDEO) == protocol['source_sha256']
    start = window['window_start_frame_inclusive']
    end = window['window_end_frame_exclusive']
    model = YOLO(str(MODEL))
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError('Cannot open source video')
    rows = []
    try:
        for frame in range(start, end):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1:
                raise RuntimeError(f'Cannot decode source frame {frame}')
            result = model.track(image, classes=[0], conf=.2, imgsz=960,
                                 tracker='bytetrack.yaml', persist=True, verbose=False)[0]
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            ids = (result.boxes.id.int().cpu().tolist() if result.boxes.id is not None
                   else [None] * len(boxes))
            detections = []
            for box, score, raw_id in zip(boxes, scores, ids):
                x1, y1, x2, y2 = map(float, box)
                detections.append({'raw_track_id': raw_id,
                                   'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                   'confidence': round(float(score), 3),
                                   'near_floor_side_candidate': y2 >= 313})
            rows.append({'source_frame': frame,
                         'planned_five_hz_sample': frame in window['five_sample_frames'],
                         'person_box_count': len(detections),
                         'geometric_near_candidate_count': sum(
                             d['near_floor_side_candidate'] for d in detections),
                         'detections': detections})
    finally:
        capture.release()
    result = {
        'status': 'exact_30fps_detector_candidates_pending_source_pair_review',
        'source_sha256': protocol['source_sha256'],
        'input_sha256': {'window_protocol': sha(PROTOCOL), 'source_review': sha(REVIEW),
                         'model': sha(MODEL), 'video': sha(VIDEO)},
        'method': 'YOLOv8n conf .20 imgsz 960 ByteTrack on all 25 exact source frames; tracker reset at window start; bottom y>=313 is only a geometric near-side candidate gate',
        'source_frame_first': start, 'source_frame_last': end - 1,
        'planned_five_hz_sample_frames': window['five_sample_frames'],
        'sample_candidate_counts': {str(row['source_frame']): row['geometric_near_candidate_count']
                                    for row in rows if row['planned_five_hz_sample']},
        'all_25_frame_candidate_count_histogram': dict(sorted(Counter(
            row['geometric_near_candidate_count'] for row in rows).items())),
        'strict_metric_approval': False,
        'rows': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['sample_candidate_counts'])


if __name__ == '__main__':
    main()
