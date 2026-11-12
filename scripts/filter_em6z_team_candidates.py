"""Apply the unchanged pilot near-court + HSV jersey rule to held-out tracks.

This reads only the source video, court calibration, and frozen predictions.
It must run before comparing with held-out ground-truth labels.
"""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_pilot_tracker import image_to_court
from evaluate_team_appearance import THRESHOLD, filter_rally


MATCH = Path('data/matches/yt_em6zFUxfYpc')
CALIBRATION = MATCH / 'pilot/calibration/near_court.json'
RAW = MATCH / 'pilot/heldout_tracker_predictions.json'
OUT = MATCH / 'pilot/heldout_team_filtered_predictions.json'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(f'Frozen filter output already exists: {OUT}')
    manifest = json.loads((MATCH / 'pilot/heldout_tracking_manifest.json').read_text())
    raw = json.loads(RAW.read_text())
    calibration = json.loads(CALIBRATION.read_text())
    if raw['source_sha256'] != manifest['source_sha256']:
        raise ValueError('Frozen predictions have a different source hash')
    matrix = image_to_court(calibration)
    video = cv2.VideoCapture(manifest['source_video'])
    if not video.isOpened():
        raise FileNotFoundError(manifest['source_video'])
    output = {
        'match_id': MATCH.name,
        'source_sha256': manifest['source_sha256'],
        'raw_predictions_sha256': sha256(RAW),
        'calibration_sha256': sha256(CALIBRATION),
        'method': ('Pilot near-court geometry + start-frame HSV torso exemplars; '
                   f'Bhattacharyya distance <= {THRESHOLD:.2f}; unchanged seed '
                   'and yellow-libero rules from evaluate_team_appearance.py'),
        'label_access': 'none',
        'windows': {},
    }
    try:
        for window in manifest['windows']:
            name = window['name']
            predictions = raw['windows'][name]['predictions']
            schedule = {'frames': {str(frame): None for frame in range(
                window['first_frame'], window['last_frame'] + 1)}}
            filtered, diagnostic = filter_rally(
                video, name, schedule, {'predictions': predictions}, matrix)
            output['windows'][name] = {
                'first_frame': window['first_frame'],
                'last_frame': window['last_frame'],
                'predictions': filtered['predictions'],
                'diagnostics': diagnostic,
            }
            print(f"{name}: {sum(map(len,predictions.values()))} raw -> "
                  f"{sum(map(len,filtered['predictions'].values()))} kept; "
                  f"{len(diagnostic['seed_track_ids'])} start seeds")
    finally:
        video.release()
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
