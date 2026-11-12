"""Count gated person proposals at source-reviewed coarse live-core seconds."""
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
CALIBRATION = BASE / 'screening/near_court_candidate.json'
MODEL = ROOT / 'yolov8n.pt'
OUT = BASE / 'screening/live_core_box_screen.json'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    core = json.loads(CORE.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    if digest(VIDEO) != manifest['video']['sha256'] or core['source_sha256'] != manifest['video']['sha256']:
        raise ValueError('Source mismatch')
    matrix = np.asarray(calibration['homography_image_to_court'], np.float64)
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    rows = []
    try:
        for item in core['rows']:
            for second in range(item['core_seconds_inclusive'][0],
                                item['core_seconds_inclusive'][1] + 1):
                number = second * 30
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f'Could not decode frame {number}')
                result = model(image, classes=[0], conf=.2, imgsz=960, verbose=False)[0]
                accepted = []
                for box, confidence in zip(result.boxes.xyxy.cpu().numpy(),
                                           result.boxes.conf.cpu().numpy()):
                    x1, y1, x2, y2 = map(float, box)
                    floor = cv2.perspectiveTransform(
                        np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), matrix)[0, 0]
                    if not np.isfinite(floor).all() or not ((floor >= -0.25) & (floor <= 9.25)).all():
                        continue
                    accepted.append({'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                     'box_bottom_court_m': [round(float(v), 3) for v in floor],
                                     'confidence': round(float(confidence), 3)})
                rows.append({'set': item['set'], 'point_number': item['point_number'],
                             'source_second': second, 'source_frame': number,
                             'gated_person_proposal_count': len(accepted),
                             'proposals': accepted})
    finally:
        cap.release()
    summary = []
    for item in core['rows']:
        selected = [row for row in rows if row['set'] == item['set']
                    and row['point_number'] == item['point_number']]
        summary.append({'set': item['set'], 'point_number': item['point_number'],
                        'sampled_live_core_seconds': len(selected),
                        'seconds_with_at_least_six_proposals': sum(row['gated_person_proposal_count'] >= 6
                                                                   for row in selected),
                        'minimum_proposals': min(row['gated_person_proposal_count'] for row in selected),
                        'maximum_proposals': max(row['gated_person_proposal_count'] for row in selected)})
    histogram = Counter(row['gated_person_proposal_count'] for row in rows)
    output = {
        'status': 'coarse_live_second_person_proposals_not_validated_six_player_positions',
        'video_id': 'u5HnY2aNW14', 'source_sha256': manifest['video']['sha256'],
        'core_review_sha256': digest(CORE), 'calibration_sha256': digest(CALIBRATION),
        'model_sha256': digest(MODEL), 'method': 'YOLOv8n conf .20 imgsz 960, staged box-bottom near-court gate',
        'sampled_seconds': len(rows), 'count_histogram': dict(sorted(histogram.items())),
        'point_summary': summary, 'rows': rows,
        'limitations': ['Counts may include far-side players, duplicates or nonplayers.',
                        'Missing detections and off-court servers reduce near-team coverage.',
                        'One-second samples do not establish continuous six-player trajectories.',
                        'Court geometry and grounded player box bottoms are not independently validated.']
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print({'sampled_seconds': len(rows), 'at_least_six': sum(row['gated_person_proposal_count'] >= 6
                                                             for row in rows),
           'points_with_any_six_proposal_second': sum(item['seconds_with_at_least_six_proposals'] > 0
                                                       for item in summary)})


if __name__ == '__main__':
    main()
