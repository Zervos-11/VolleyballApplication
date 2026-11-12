"""Independently screen all source frames inside the two long 5 Hz candidate runs."""

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402


BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
VIDEO = BASE / 'source_720p.mp4'
SOURCE_MANIFEST = BASE / 'primary_source_manifest.json'
CALIBRATION = SCREEN / 'near_court_candidate.json'
TRACKLETS = SCREEN / 'full_clip_tracklet_audit.json'
MODEL = ROOT / 'yolov8n.pt'
OUT = SCREEN / 'two_long_runs_30fps_screen.json'
SELECTED = ((1, 5), (3, 34))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    source = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    tracks = json.loads(TRACKLETS.read_text(encoding='utf-8'))
    assert source['video']['sha256'] == tracks['source_sha256'] == sha(VIDEO)
    transform = np.asarray(calibration['homography_image_to_court'], np.float64)
    net_y = calibration['points_px'][2][1]
    by_point = {(p['set'], p['point_number']): p for p in tracks['points']}
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    points = []
    try:
        for key in SELECTED:
            run = by_point[key]['longest_same_six_raw_id_run_full_clip']
            if getattr(model, 'predictor', None) and getattr(model.predictor, 'trackers', None):
                model.predictor.trackers[0].reset()
            rows = []
            for frame in range(run['first_frame'], run['last_frame'] + 1):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame + 1
                result = model.track(image, classes=[0], conf=.2, imgsz=960,
                                     tracker='bytetrack.yaml', persist=True, verbose=False)[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                scores = result.boxes.conf.cpu().numpy()
                ids = (result.boxes.id.int().cpu().tolist() if result.boxes.id is not None
                       else [None] * len(boxes))
                proposals = []
                for box, confidence, raw_id in zip(boxes, scores, ids):
                    x1, y1, x2, y2 = map(float, box)
                    floor = cv2.perspectiveTransform(
                        np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), transform)[0, 0]
                    if not np.isfinite(floor).all() or not ((floor >= -.25) & (floor <= 9.25)).all():
                        continue
                    proposals.append({'raw_track_id': raw_id,
                                      'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                      'box_bottom_court_m': [round(float(v), 3) for v in floor],
                                      'confidence': round(float(confidence), 3),
                                      'net_side_status': ('near_floor_side_candidate' if y2 >= net_y
                                                          else 'net_boundary_review')})
                near = [p for p in proposals if p['net_side_status'] == 'near_floor_side_candidate']
                rows.append({'source_frame': frame,
                             'near_candidate_count': len(near), 'proposals': proposals})
            hist = Counter(r['near_candidate_count'] for r in rows)
            point = {'set': key[0], 'point_number': key[1],
                     'source_frame_first': run['first_frame'],
                     'source_frame_last': run['last_frame'],
                     'source_frames_screened': len(rows),
                     'near_candidate_count_histogram': dict(sorted(hist.items())),
                     'rows': rows}
            points.append(point)
            print(f'S{key[0]} P{key[1]}: {len(rows)} source frames; six near candidates in {hist[6]}', flush=True)
    finally:
        cap.release()
    out = {'status': 'independent_30fps_raw_detector_screen_not_named_identity_review',
           'source_sha256': tracks['source_sha256'],
           'input_sha256': {'source_manifest': sha(SOURCE_MANIFEST),
                            'calibration': sha(CALIBRATION),
                            'tracklet_audit': sha(TRACKLETS), 'model': sha(MODEL)},
           'method': 'YOLOv8n conf .20 imgsz 960 ByteTrack at every decoded source frame; tracker reset at each selected run',
           'summary': {'runs': len(points),
                       'source_frames_screened': sum(p['source_frames_screened'] for p in points),
                       'exactly_six_near_candidate_frames': sum(
                           r['near_candidate_count'] == 6 for p in points for r in p['rows'])},
           'points': points}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(out['summary'], flush=True)


if __name__ == '__main__':
    main()
