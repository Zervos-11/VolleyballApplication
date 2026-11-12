"""Test point-local high-resolution tracker continuity in nine frozen wins."""
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
MODEL = ROOT / 'yolov8n.pt'
CAL = SCREEN / 'near_court_candidate.json'
INTERVALS = SCREEN / 'event_transition_source_qc.json'
VIS = SCREEN / 'source_visibility_ledger.json'
OUT = SCREEN / 'highres_winning_run_screen.json'
STEP = 6


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def longest_exact_six(rows):
    best, current = [], []
    last_ids = None
    for row in rows:
        ids = [p['raw_track_id'] for p in row['near_floor_side_proposals']]
        exact = len(ids) == len(set(ids)) == 6 and None not in ids
        if exact and set(ids) == last_ids:
            current.append(row['source_frame'])
        elif exact:
            current = [row['source_frame']]
        else:
            current = []
        last_ids = set(ids) if exact else None
        if len(current) > len(best):
            best = current[:]
    return best


def main():
    intervals = json.loads(INTERVALS.read_text(encoding='utf-8'))
    visibility = json.loads(VIS.read_text(encoding='utf-8'))
    calibration = json.loads(CAL.read_text(encoding='utf-8'))
    assert intervals['source_sha256'] == visibility['source_sha256'] == sha(VIDEO)
    winners = {(r['set'], r['point_number']) for r in visibility['rows'] if r['near_team_won']}
    assert len(winners) == 9
    H = np.asarray(calibration['homography_image_to_court'], np.float64)
    net_y = calibration['points_px'][2][1]
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    points = []
    try:
        for interval in intervals['points']:
            key = interval['set'], interval['point_number']
            if key not in winners:
                continue
            if getattr(model, 'predictor', None) and getattr(model.predictor, 'trackers', None):
                model.predictor.trackers[0].reset()
            start = interval['conservative_interior_start_frame_inclusive']
            end = interval['conservative_interior_end_frame_exclusive']
            rows = []
            for frame in range(start, end, STEP):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1:
                    raise RuntimeError(f'Cannot decode exact source frame {frame}')
                result = model.track(image, classes=[0], conf=.10, imgsz=1280,
                                     tracker='bytetrack.yaml', persist=True, verbose=False)[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                scores = result.boxes.conf.cpu().numpy()
                ids = (result.boxes.id.int().cpu().tolist() if result.boxes.id is not None
                       else [None] * len(boxes))
                proposals = []
                for box, score, track_id in zip(boxes, scores, ids):
                    x1, y1, x2, y2 = map(float, box)
                    floor = cv2.perspectiveTransform(
                        np.asarray([[[(x1+x2)/2, y2]]], np.float32), H)[0, 0]
                    if not np.isfinite(floor).all() or not ((floor >= -.25) & (floor <= 9.25)).all():
                        continue
                    proposals.append({'raw_track_id': track_id,
                                      'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                      'confidence': round(float(score), 3),
                                      'box_bottom_court_m': [round(float(v), 3) for v in floor],
                                      'net_side_status': ('near_floor_side_candidate' if y2 >= net_y
                                                          else 'net_boundary_review')})
                near = [p for p in proposals if p['net_side_status'] == 'near_floor_side_candidate']
                rows.append({'source_frame': frame, 'near_floor_side_count': len(near),
                             'near_floor_side_proposals': near,
                             'net_boundary_count': len(proposals) - len(near)})
            best = longest_exact_six(rows)
            points.append({'set': key[0], 'point_number': key[1],
                           'sampled_frames': len(rows),
                           'frames_with_six_geometric_candidates': sum(r['near_floor_side_count'] >= 6 for r in rows),
                           'longest_exact_six_same_raw_id_run': best,
                           'longest_run_length': len(best), 'rows': rows})
            print(f'S{key[0]} P{key[1]}: {len(best)}-sample longest six-ID run', flush=True)
    finally:
        cap.release()
    assert len(points) == 9
    OUT.write_text(json.dumps({
        'status': 'high_resolution_winning_run_proposals_not_source_adjudicated',
        'source_sha256': intervals['source_sha256'],
        'input_sha256': {'video': sha(VIDEO), 'model': sha(MODEL), 'calibration': sha(CAL),
                         'intervals': sha(INTERVALS), 'visibility': sha(VIS)},
        'settings': {'frame_step': STEP, 'imgsz': 1280, 'confidence': .10,
                     'tracker': 'bytetrack.yaml', 'point_local_reset': True},
        'summary': {'winning_points': 9, 'sampled_frames': sum(p['sampled_frames'] for p in points),
                    'wins_with_at_least_five_sample_raw_run': sum(p['longest_run_length'] >= 5 for p in points)},
        'points': points,
        'limitations': 'Raw exact-six IDs are geometric proposals; opponents, officials, duplicates, airborne bottoms and after-point frames may contaminate runs. Source review is required before any interval or metric claim.',
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
