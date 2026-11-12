"""Preserve raw detections with conservative near-team or unknown status.

This is a separate development candidate. It never labels a rejected box as
the opposing team and does not invent a box for an unobserved player.
"""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_pilot_tracker import image_to_court, in_target_region, iou, project
from evaluate_team_appearance import THRESHOLD, torso_histogram


MATCH = Path('data/matches/yt_em6zFUxfYpc')
RAW = MATCH / 'pilot/heldout_tracker_predictions.json'
BASELINE = MATCH / 'pilot/heldout_team_filtered_predictions.json'
CALIBRATION = MATCH / 'pilot/calibration/near_court.json'
MANIFEST = MATCH / 'pilot/heldout_tracking_manifest.json'
OUT = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial/heldout_team_status.json')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text())
    baseline = json.loads(BASELINE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    if raw['source_sha256'] != baseline['source_sha256'] or raw['source_sha256'] != manifest['source_sha256']:
        raise ValueError('Source hash mismatch')
    matrix = image_to_court(json.loads(CALIBRATION.read_text()))
    video = cv2.VideoCapture(manifest['source_video'])
    if not video.isOpened():
        raise FileNotFoundError(manifest['source_video'])
    windows = {}
    try:
        for window in manifest['windows']:
            name, first = window['name'], window['first_frame']
            predictions = raw['windows'][name]['predictions']
            selected = baseline['windows'][name]['predictions']
            seed_ids = set(baseline['windows'][name]['diagnostics']['seed_track_ids'])
            video.set(cv2.CAP_PROP_POS_FRAMES, first)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode first frame {first}')
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            seeds = []
            for pred in predictions[str(first)]:
                if pred['track_id'] in seed_ids:
                    appearance = torso_histogram(hsv, pred['bbox'])
                    if appearance is not None:
                        seeds.append(appearance[0])
            if not seeds:
                raise ValueError(f'{name}: no team seeds')
            frames = {}
            for frame in range(window['first_frame'], window['last_frame'] + 1):
                video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode frame {frame}')
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                key = str(frame)
                candidates = predictions[key]
                selected_ids = {pred['track_id'] for pred in selected[key]}
                rows = []
                for pred in candidates:
                    box = pred['bbox']
                    xy = project([(box[0] + box[2]) / 2, box[3]], matrix)
                    court_ok = bool(in_target_region(xy, frame == first))
                    appearance = torso_histogram(hsv, box)
                    distance = (min(cv2.compareHist(appearance[0], seed, cv2.HISTCMP_BHATTACHARYYA)
                                    for seed in seeds) if appearance is not None else None)
                    selected_by_baseline = pred['track_id'] in selected_ids
                    if frame == first and pred['track_id'] not in seed_ids and selected_by_baseline:
                        status, reason = 'unknown', 'unseeded_start_box'
                    elif selected_by_baseline:
                        status, reason = 'target_candidate', 'court_and_team_filter'
                    elif not court_ok:
                        status, reason = 'unknown', 'outside_target_region_or_airborne'
                    elif distance is None:
                        status, reason = 'unknown', 'appearance_unavailable'
                    elif distance > THRESHOLD:
                        status, reason = 'unknown', 'appearance_mismatch'
                    else:
                        status, reason = 'unknown', 'not_selected_by_baseline'
                    overlap_ids = [other['track_id'] for other in candidates
                                   if other['track_id'] != pred['track_id'] and
                                   iou(box, other['bbox']) >= .5]
                    rows.append({'track_id': pred['track_id'], 'bbox': box,
                                 'confidence': pred['confidence'],
                                 'court_xy_m_from_box_bottom': [round(float(x), 3) for x in xy],
                                 'in_target_region': court_ok,
                                 'appearance_distance_to_seed': round(float(distance), 3) if distance is not None else None,
                                 'team_status': status, 'reason': reason,
                                 'review_flags': ['overlapping_raw_boxes'] if overlap_ids else [],
                                 'overlapping_track_ids': overlap_ids})
                frames[key] = rows
            windows[name] = {'first_frame': window['first_frame'],
                             'last_frame': window['last_frame'],
                             'seed_track_ids': sorted(seed_ids), 'frames': frames}
    finally:
        video.release()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'status': 'development_candidate', 'match_id': MATCH.name,
        'source_sha256': raw['source_sha256'],
        'raw_predictions_sha256': sha256(RAW),
        'baseline_filtered_sha256': sha256(BASELINE),
        'calibration_sha256': sha256(CALIBRATION),
        'method': 'Existing court + HSV team filter; first-frame boxes without seed evidence become unknown. Rejected raw boxes remain unknown, never opponent. Overlapping raw boxes are flagged for review.',
        'appearance_threshold': THRESHOLD, 'overlap_iou_review_threshold': .5,
        'no_six_player_assumption': True, 'windows': windows,
    }, indent=2) + '\n', encoding='utf-8')
    for name, window in windows.items():
        rows = [row for frame in window['frames'].values() for row in frame]
        print(name, len(rows), 'target', sum(row['team_status'] == 'target_candidate' for row in rows),
              'unknown', sum(row['team_status'] == 'unknown' for row in rows),
              'overlap', sum(bool(row['review_flags']) for row in rows))


if __name__ == '__main__':
    main()
