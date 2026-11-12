"""Apply a frozen temporal jump grace to raw boxes and the saved team filter."""

import hashlib
import json
from pathlib import Path

import cv2

from airborne_grace_filter import filter_window
from evaluate_pilot_tracker import image_to_court


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
RAW = PILOT / 'heldout_tracker_predictions.json'
BASE = PILOT / 'heldout_team_filtered_predictions.json'
CALIBRATION = PILOT / 'calibration/near_court.json'
OUT = PILOT / 'heldout_airborne_grace_predictions.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(f'Frozen output already exists: {OUT}')
    manifest = json.loads((PILOT / 'heldout_tracking_manifest.json').read_text())
    raw = json.loads(RAW.read_text())
    base = json.loads(BASE.read_text())
    source_hash = manifest['source_sha256']
    if raw['source_sha256'] != source_hash or base['source_sha256'] != source_hash:
        raise ValueError('Predictions have a different source video')
    if base['raw_predictions_sha256'] != sha256(RAW):
        raise ValueError('Team filter was not generated from these raw predictions')
    if base['calibration_sha256'] != sha256(CALIBRATION):
        raise ValueError('Team filter has a different court calibration')
    matrix = image_to_court(json.loads(CALIBRATION.read_text()))
    video = cv2.VideoCapture(manifest['source_video'])
    if not video.isOpened():
        raise FileNotFoundError(manifest['source_video'])
    result = {
        'match_id': MATCH.name, 'source_sha256': source_hash,
        'raw_predictions_sha256': sha256(RAW),
        'base_predictions_sha256': sha256(BASE),
        'calibration_sha256': sha256(CALIBRATION),
        'rule_sha256': sha256(Path(__file__).parent / 'airborne_grace_filter.py'),
        'method': ('Same-ID blue-team near-net jump grace on frozen court + jersey output; '
                   '0.5s maximum since last court-compatible anchor, 3-frame maximum gap, '
                   '>=3% box-height rise with >=8% on confirmation, >=70% of anchor box height, '
                   '<=25% box-height centre motion per frame, HSV torso distance '
                   '<=0.60; anchor from y=6..9m, projected box bottom beyond y=9.5m, '
                   'blue HSV hue 90..120 / saturation >=100 / value >=75, and two '
                   'rising observations required. No inferred floor measurement or ID change.'),
        'label_access': 'none', 'windows': {},
    }
    try:
        for window in manifest['windows']:
            name, first, last = (window['name'], window['first_frame'],
                                 window['last_frame'])
            predictions, diagnostics = filter_window(
                video, raw['windows'][name]['predictions'],
                base['windows'][name]['predictions'], matrix,
                first, last, manifest['fps'])
            result['windows'][name] = {
                'first_frame': first, 'last_frame': last,
                'predictions': predictions, 'diagnostics': diagnostics}
            print(f"{name}: {diagnostics['rescued_count']} jump candidates rescued")
    finally:
        video.release()
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
