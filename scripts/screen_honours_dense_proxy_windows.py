"""Screen matched set-three windows for continuous six-box availability."""
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402

SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
MODEL = ROOT / 'yolov8n.pt'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json'
OUT = ROOT / 'data/processed/honours_dense_proxy_window_screen.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_DENSE_PROXY_WINDOW_SCREEN.md'
WINDOWS = [(5, 155799, 'ProVolley'), (37, 204263, 'UTS')]
HALF_WIDTH = 100
STEP = 10


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return overlap / (area_a + area_b - overlap)


def suppress_overlaps(candidates):
    accepted = []
    for candidate in sorted(candidates, key=lambda r: -r['confidence']):
        if all(iou(candidate['bbox_px'], other['bbox_px']) < .45 for other in accepted):
            accepted.append(candidate)
    return accepted


def main():
    source, sample, camera = map(read, (SOURCE, SAMPLE, CALIBRATION))
    if source['sha256'] != sample['source_sha256']:
        raise ValueError('Sample belongs to another source')
    selected = {(r['set'], r['point_number']): r for r in sample['selected_points']}
    matrix = cv2.getPerspectiveTransform(np.asarray(camera['points_px'], np.float32),
                                         np.asarray(camera['points_court_m'], np.float32))
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    points = []
    try:
        for point_number, center, winner in WINDOWS:
            chosen = selected[(3, point_number)]
            if chosen['winner'] != winner:
                raise ValueError('Winner differs from frozen sample')
            start = max(center - HALF_WIDTH, chosen['seek_from_frame'])
            stop = min(center + HALF_WIDTH, chosen['seek_to_frame_exclusive'] - 1)
            rows = []
            for number in range(start, stop + 1, STEP):
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f'Could not decode {number}')
                result = model.predict(image, classes=[0], conf=.20, imgsz=960, verbose=False)[0]
                boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else np.empty((0, 4))
                scores = result.boxes.conf.cpu().numpy() if result.boxes is not None else np.empty((0,))
                candidates = []
                for box, score in zip(boxes, scores):
                    x1, y1, x2, y2 = map(float, box)
                    if y2 - y1 < 35:
                        continue
                    projected = cv2.perspectiveTransform(
                        np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), matrix)[0, 0]
                    if np.isfinite(projected).all() and ((projected >= 0) & (projected <= 9)).all():
                        candidates.append({'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                           'confidence': round(float(score), 3)})
                filtered = suppress_overlaps(candidates)
                rows.append({'frame': number, 'raw_near_court_box_count': len(candidates),
                             'overlap_filtered_count': len(filtered),
                             'overlap_filtered_boxes': filtered})
            points.append({'set': 3, 'point_number': point_number, 'winner': winner,
                           'center_frame': center, 'sampled_frame_count': len(rows),
                           'raw_six_count_frames': sum(r['raw_near_court_box_count'] >= 6 for r in rows),
                           'filtered_six_count_frames': sum(r['overlap_filtered_count'] >= 6 for r in rows),
                           'filtered_six_frame_indices': [r['frame'] for r in rows
                                                          if r['overlap_filtered_count'] >= 6],
                           'rows': rows})
            print(f'S3 P{point_number}: {points[-1]["filtered_six_count_frames"]}/{len(rows)} '
                  'sampled frames have 6+ filtered near-court boxes', flush=True)
    finally:
        cap.release()
    result = {'status': 'dense_short_window_detector_screen_not_reviewed_near_team_tracks',
              'source_sha256': source['sha256'], 'sample_sha256': sha(SAMPLE),
              'detector_sha256': sha(MODEL), 'calibration_sha256': sha(CALIBRATION),
              'window_half_width_frames': HALF_WIDTH, 'sample_step_frames': STEP,
              'detector': 'YOLOv8n persons conf=.20 imgsz=960; box-bottom nominal near-court gate; extra IoU .45 overlap suppression',
              'points': points,
              'limitations': ['Counts may include opponents and may miss occluded or clipped teammates.',
                              'Overlap suppression may remove two genuinely overlapping players.',
                              'The selected centres were identified after visual review, and the two windows may represent different phases.',
                              'No trajectory identity or source-reviewed rally interval is established.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(f"| {p['point_number']} | {p['winner']} | {p['sampled_frame_count']} | "
                      f"{p['raw_six_count_frames']} | {p['filtered_six_count_frames']} | "
                      f"{', '.join(map(str, p['filtered_six_frame_indices'])) or 'none'} |"
                      for p in points)
    REPORT.write_text(f'''# Short-window six-box availability screen

The [source-bound record](../data/processed/honours_dense_proxy_window_screen.json) samples source frames every {STEP} frames across {2 * HALF_WIDTH + 1}-frame windows (4.0 s between endpoints) around the visually screened set-three ProVolley-won point 5 and UTS-won point 37 snapshots. It applies the same person detector and staged near-court gate, then an additional IoU 0.45 overlap filter. This tests whether a short six-box run is even available before attempting six-player trajectories.

| Point | Winner | Frames sampled | Raw frames with 6+ near-court boxes | Frames with 6+ after overlap filter | Candidate frame indices |
| ---: | --- | ---: | ---: | ---: | --- |
{table}

The counts are **upper-bound detector proposals**: far-side players can still pass the court gate, while real teammates can be hidden or merged. A six-box count does not establish six near-side players. The [source-image review](HONOURS_DENSE_PROXY_WINDOW_VISUAL_REVIEW.md) shows far-side contamination and missed near-side players in the later UTS-win frames. No outcome comparison is made from these counts.
''', encoding='utf-8')


if __name__ == '__main__':
    main()
