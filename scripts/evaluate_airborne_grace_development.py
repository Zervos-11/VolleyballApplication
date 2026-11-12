"""Run the fixed jump-grace rule on two already reviewed pilot intervals."""

import csv
import json
from pathlib import Path

import cv2

from airborne_grace_filter import filter_window
from evaluate_pilot_tracker import image_to_court
from evaluate_team_appearance import filter_rally


MATCH = Path('data/matches/yt_FqE5pTJqx8g')
ROOT = Path('data/processed/pilot_tracker_evaluation')
OUT = ROOT / 'airborne_grace_development.json'
WINDOWS = (
    ('r4', 150240, 150290,
     ROOT / 'dense_identity_window_r4/tracker_predictions.json',
     ROOT / 'dense_identity_window_r4/full_team_150240_150290/assisted_paths.csv'),
    ('r2', 78100, 78150,
     ROOT / 'dense_identity_validation_r2/tracker_predictions.json',
     ROOT / 'dense_identity_validation_r2/assisted_paths.csv'),
)


def main():
    matrix = image_to_court(json.loads(
        (MATCH / 'pilot/calibration/camera_r2_r5.json').read_text()))
    video = cv2.VideoCapture(str(MATCH / 'source_FqE5pTJqx8g.mp4'))
    if not video.isOpened():
        raise FileNotFoundError('Development source video')
    results = {}
    try:
        fps = video.get(cv2.CAP_PROP_FPS)
        for name, first, last, prediction_path, review_path in WINDOWS:
            raw_all = json.loads(prediction_path.read_text())['predictions']
            raw = {str(frame): raw_all[str(frame)] for frame in range(first, last + 1)}
            schedule = {'frames': {str(frame): None for frame in range(first, last + 1)}}
            baseline, baseline_diagnostic = filter_rally(
                video, name, schedule, {'predictions': raw}, matrix)
            output, diagnostic = filter_window(
                video, raw, baseline['predictions'], matrix, first, last, fps)
            with review_path.open(newline='', encoding='utf-8') as stream:
                reviewed = {(int(row['frame_index']), int(row['candidate_track_id']))
                            for row in csv.DictReader(stream)
                            if row['candidate_track_id']}
            rescued = diagnostic['rescued']
            results[name] = {
                'raw_boxes': sum(map(len, raw.values())),
                'baseline_boxes': sum(map(len, baseline['predictions'].values())),
                'grace_boxes': sum(map(len, output.values())),
                'rescued': rescued,
                'rescued_matching_assisted_target_path': sum(
                    (row['frame'], row['track_id']) in reviewed for row in rescued),
                'baseline_seed_track_ids': baseline_diagnostic['seed_track_ids'],
            }
            print(name, {key: value for key, value in results[name].items()
                         if key not in ('rescued', 'baseline_seed_track_ids')})
    finally:
        video.release()
    OUT.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
