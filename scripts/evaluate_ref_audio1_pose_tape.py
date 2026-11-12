"""Transfer the existing pose-restricted tape visibility cue to a new match.

Only the camera-specific tape line is measured from source pixels. The pose
eligibility and ridge test are unchanged from the earlier em6z cue trial.
"""

import hashlib
import json
import os
from pathlib import Path

import cv2

from net_tape_pose_flag import pose_tape_visibility


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
REVIEWS = BASE / 'reviewed_track_runs.json'
SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
MODEL = Path('yolov8n-pose.pt')
RULE = Path('scripts/net_tape_pose_flag.py')
VISIBILITY = Path('scripts/net_tape_visibility.py')
OUT = BASE / 'pose_tape_transfer_audit.json'
TAPE_LINE = ((620, 516), (1390, 520))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    reviews = json.loads(REVIEWS.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(SOURCE) or reviews['raw_sha256'] != sha256(RAW):
        raise ValueError('Frozen source provenance mismatch')
    os.environ['YOLO_CONFIG_DIR'] = str(Path('data/processed/ultralytics_config').resolve())
    from ultralytics import YOLO

    model = YOLO(str(MODEL))
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    rows = []
    try:
        for frame in range(raw['first_frame'], raw['last_frame'] + 1):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            posed = model.predict(image, conf=.20, imgsz=960, verbose=False)[0]
            boxes = posed.boxes.xyxy.cpu().numpy()
            xy = posed.keypoints.xy.cpu().numpy()
            confidence = posed.keypoints.conf.cpu().numpy()
            reviewed = [(run['track_id'], run['side']) for run in reviews['runs']
                        if run['first_frame'] <= frame <= run['last_frame']]
            raw_rows = {int(row['track_id']): row for row in raw['predictions'][str(frame)]}
            for track_id, side in reviewed:
                measure = pose_tape_visibility(image, hsv, raw_rows[track_id]['bbox'],
                                               boxes, xy, confidence, TAPE_LINE)
                rows.append({'frame': frame, 'track_id': track_id,
                             'reviewed_side': side, **measure})
    finally:
        video.release()
    summary = {}
    for side in ('near', 'far'):
        subset = [row for row in rows if row['reviewed_side'] == side]
        measured = [row for row in subset if row['status'] == 'measured']
        summary[side] = {'reviewed_boxes': len(subset), 'eligible': len(measured),
                         'ridge_at_least_0_5': sum(row['white_ridge_fraction'] >= .5
                                                   for row in measured)}
    OUT.write_text(json.dumps({
        'status': 'transfer_diagnostic', 'source_sha256': raw['source_sha256'],
        'raw_sha256': sha256(RAW), 'reviews_sha256': sha256(REVIEWS),
        'pose_model_sha256': sha256(MODEL), 'pose_rule_sha256': sha256(RULE),
        'visibility_rule_sha256': sha256(VISIBILITY),
        'tape_line_px': TAPE_LINE,
        'criterion': 'pre-existing white_ridge_fraction >= 0.5 on pose-eligible body',
        'summary': summary, 'rows': rows,
    }, indent=2) + '\n', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
