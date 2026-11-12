"""Screen dense person-track continuity in all 18 frozen U5 live cores.

This is a reproducible tracking *proposal* pass. It does not certify player
identity, exact play phase or floor position for the strict metric calculator.
"""
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
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
CORE = BASE / 'screening/live_core_second_review.json'
CUTS = BASE / 'screening/rally_cut_clip_register.json'
CALIBRATION = BASE / 'screening/near_court_candidate.json'
MODEL = ROOT / 'yolov8n.pt'
OUT = BASE / 'screening/dense_live_track_screen.json'
FRAME_STEP = 6  # 5 Hz on the 30 fps source


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    core = json.loads(CORE.read_text(encoding='utf-8'))
    cut_register = json.loads(CUTS.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    if digest(VIDEO) != manifest['video']['sha256'] or core['source_sha256'] != manifest['video']['sha256']:
        raise ValueError('Source mismatch')
    if cut_register['source_sha256'] != manifest['video']['sha256']:
        raise ValueError('Rally-cut register source mismatch')
    clips = {(row['set'], row['point_number']): row
             for row in cut_register['selected_clips']}
    if len(clips) != len(core['rows']):
        raise ValueError('Cut register and reviewed cores have different point counts')
    transform = np.asarray(calibration['homography_image_to_court'], np.float64)
    net_y = calibration['points_px'][2][1]
    if calibration['points_px'][3][1] != net_y:
        raise ValueError('Expected horizontal staged floor centreline')
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    points = []
    try:
        for point in core['rows']:
            first = point['core_seconds_inclusive'][0] * 30
            stop = (point['core_seconds_inclusive'][1] + 1) * 30
            clip = clips[point['set'], point['point_number']]
            if not (clip['clip_start_frame_inclusive'] <= first < stop <= clip['clip_end_frame_exclusive']):
                raise ValueError(f"Coarse core crosses edited rally clip: S{point['set']} P{point['point_number']}")
            # The tracker is point-local; raw IDs must never be linked across points.
            if getattr(model, 'predictor', None) and getattr(model.predictor, 'trackers', None):
                model.predictor.trackers[0].reset()
            rows = []
            for number in range(first, stop, FRAME_STEP):
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f'Could not decode source frame {number}')
                result = model.track(image, classes=[0], conf=.2, imgsz=960,
                                     tracker='bytetrack.yaml', persist=True, verbose=False)[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                scores = result.boxes.conf.cpu().numpy()
                ids = (result.boxes.id.int().cpu().tolist() if result.boxes.id is not None
                       else [None] * len(boxes))
                proposals = []
                for box, confidence, track_id in zip(boxes, scores, ids):
                    x1, y1, x2, y2 = map(float, box)
                    floor = cv2.perspectiveTransform(
                        np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), transform)[0, 0]
                    if not np.isfinite(floor).all() or not ((floor >= -.25) & (floor <= 9.25)).all():
                        continue
                    proposals.append({
                        'raw_track_id': track_id,
                        'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                        'box_bottom_court_m': [round(float(v), 3) for v in floor],
                        'confidence': round(float(confidence), 3),
                        'net_side_status': ('near_floor_side_candidate' if y2 >= net_y
                                            else 'net_boundary_review')
                    })
                rows.append({'source_frame': number, 'source_second': round(number / 30, 3),
                             'near_floor_side_candidate_count': sum(
                                 p['net_side_status'] == 'near_floor_side_candidate'
                                 for p in proposals),
                             'net_boundary_review_count': sum(
                                 p['net_side_status'] == 'net_boundary_review'
                                 for p in proposals), 'proposals': proposals})
            histogram = Counter(r['near_floor_side_candidate_count'] for r in rows)
            points.append({'set': point['set'], 'point_number': point['point_number'],
                           'sampled_frame_range': [first, stop], 'frame_step': FRAME_STEP,
                           'frames': len(rows),
                           'frames_with_six_geometric_candidates': sum(
                               r['near_floor_side_candidate_count'] >= 6 for r in rows),
                           'frames_with_any_net_boundary_review': sum(
                               r['net_boundary_review_count'] > 0 for r in rows),
                           'candidate_count_histogram': dict(sorted(histogram.items())),
                           'rows': rows})
            print(f"S{point['set']} P{point['point_number']}: "
                  f"{points[-1]['frames_with_six_geometric_candidates']}/{len(rows)} "
                  f"six-candidate frames", flush=True)
    finally:
        cap.release()
    output = {
        'status': 'dense_tracking_proposals_not_validated_six_player_trajectories',
        'video_id': 'u5HnY2aNW14', 'source_sha256': manifest['video']['sha256'],
        'core_review_sha256': digest(CORE), 'calibration_sha256': digest(CALIBRATION),
        'model_sha256': digest(MODEL), 'frame_step': FRAME_STEP,
        'method': 'YOLOv8n conf .20 imgsz 960 plus ByteTrack at 5 Hz; point-local raw IDs; '
                  'staged court box-bottom gate and floor-centreline boundary screen',
        'points': points,
        'limitations': [
            'Coarse live cores are not exact source-reviewed rally boundaries.',
            'Raw track IDs and geometric candidates are not verified near-team players.',
            'Jump and overlap can move box bottoms over the net line or break tracks.',
            'Projected box bottoms are not validated ground positions.'
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}', flush=True)


if __name__ == '__main__':
    main()
