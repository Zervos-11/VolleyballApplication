"""Evaluate the torso-restricted tape cue on the two frozen dense windows."""

import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np

from evaluate_pilot_tracker import image_to_court, project
from net_tape_pose_flag import pose_tape_visibility


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
OUT = Path('data/processed/pilot_tracker_evaluation/net_cue_trial/pose_tape_audit.json')
TAPE_LINE_PX = ((70, 618), (1515, 618))


def summarize(rows, source):
    subset = [row for row in rows if row['source'] == source]
    measured = [row for row in subset if row['status'] == 'measured']
    fractions = [row['white_ridge_fraction'] for row in measured]
    return {'total_boxes': len(subset), 'eligible': len(measured),
            'median_fraction': round(float(np.median(fractions)), 3) if fractions else None,
            'p90_fraction': round(float(np.percentile(fractions, 90)), 3) if fractions else None,
            'fraction_at_least_0_5': sum(value >= .5 for value in fractions)}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    os.environ['YOLO_CONFIG_DIR'] = str(Path('data/processed/ultralytics_config').resolve())
    from ultralytics import YOLO
    model_path = Path('yolov8n-pose.pt')
    model = YOLO(str(model_path))
    manifest = json.loads((PILOT / 'heldout_tracking_manifest.json').read_text())
    raw = json.loads((PILOT / 'heldout_tracker_predictions.json').read_text())
    if manifest['source_sha256'] != raw['source_sha256']:
        raise ValueError('Source hash mismatch')
    matrix = image_to_court(json.loads((PILOT / 'calibration/near_court.json').read_text()))
    video = cv2.VideoCapture(manifest['source_video'])
    if not video.isOpened():
        raise FileNotFoundError(manifest['source_video'])
    windows = {}
    try:
        for name in ('cross_a', 'cross_b'):
            labels = json.loads((PILOT / 'player_annotations' / f'{name}.json').read_text())
            rows = []
            for key, frame in labels['frames'].items():
                video.set(cv2.CAP_PROP_POS_FRAMES, int(key))
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode frame {key}')
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                posed = model.predict(image, conf=.20, imgsz=960, verbose=False)[0]
                pose_boxes = posed.boxes.xyxy.cpu().numpy()
                xy = posed.keypoints.xy.cpu().numpy()
                conf = posed.keypoints.conf.cpu().numpy()
                for player in frame['players']:
                    box = player.get('bbox')
                    if box is None:
                        continue
                    measure = pose_tape_visibility(image, hsv, box, pose_boxes,
                                                   xy, conf, TAPE_LINE_PX)
                    rows.append({'frame': int(key), 'source': 'labelled_near',
                                 'player_id': player['player_id'], **measure})
                for pred in raw['windows'][name]['predictions'][key]:
                    box = pred['bbox']
                    position = project([(box[0] + box[2]) / 2, box[3]], matrix)
                    if float(position[1]) <= 11.0:
                        continue
                    measure = pose_tape_visibility(image, hsv, box, pose_boxes,
                                                   xy, conf, TAPE_LINE_PX)
                    rows.append({'frame': int(key), 'source': 'far_geometry_proxy',
                                 'track_id': pred['track_id'],
                                 'projected_box_bottom_y_m': round(float(position[1]), 3),
                                 **measure})
            windows[name] = {'near': summarize(rows, 'labelled_near'),
                             'far_proxy': summarize(rows, 'far_geometry_proxy'),
                             'rows': rows}
            print(name, windows[name]['near'], windows[name]['far_proxy'], flush=True)
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'source_sha256': manifest['source_sha256'],
        'pose_model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
        'rule_sha256': hashlib.sha256(Path('scripts/net_tape_pose_flag.py').read_bytes()).hexdigest(),
        'tape_line_px': TAPE_LINE_PX,
        'scope': 'Near player labels and a far-side geometry proxy; no independent far-side labels.',
        'windows': windows}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
