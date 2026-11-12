"""Apply the v2 image-continuity rule to already frozen raw and team boxes.

Labels are never read. Existing v1 outputs and benchmark inputs are preserved.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2

from airborne_grace_filter_v2 import filter_window
from evaluate_pilot_tracker import image_to_court


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
RULE = Path(__file__).parent / 'airborne_grace_filter_v2.py'
DEFAULT_OUT = PILOT / 'heldout_airborne_grace_v2_predictions.json'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(input_json=None, output=DEFAULT_OUT):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((PILOT / 'heldout_tracking_manifest.json').read_text())
    calibration_path = PILOT / 'calibration/near_court.json'
    matrix = image_to_court(json.loads(calibration_path.read_text()))
    source_hash = manifest['source_sha256']

    if input_json:
        input_json = Path(input_json)
        source = json.loads(input_json.read_text())
        if source['source_sha256'] != source_hash:
            raise ValueError('Source hash mismatch')
        first, last = source['segment']
        windows = [dict(name='segment', first_frame=first, last_frame=last)]
        raw_by_window = {'segment': source['raw_predictions']}
        base_by_window = {'segment': source['court_jersey_predictions']}
        input_hashes = {'input_json_sha256': sha256(input_json)}
    else:
        raw_path = PILOT / 'heldout_tracker_predictions.json'
        base_path = PILOT / 'heldout_team_filtered_predictions.json'
        raw = json.loads(raw_path.read_text())
        base = json.loads(base_path.read_text())
        if raw['source_sha256'] != source_hash or base['source_sha256'] != source_hash:
            raise ValueError('Source hash mismatch')
        if base['raw_predictions_sha256'] != sha256(raw_path):
            raise ValueError('Team filter was not generated from the frozen raw output')
        if base['calibration_sha256'] != sha256(calibration_path):
            raise ValueError('Team filter calibration mismatch')
        windows = manifest['windows']
        raw_by_window = {name: value['predictions'] for name, value in raw['windows'].items()}
        base_by_window = {name: value['predictions'] for name, value in base['windows'].items()}
        input_hashes = {'raw_predictions_sha256': sha256(raw_path),
                        'base_predictions_sha256': sha256(base_path)}

    video = cv2.VideoCapture(manifest['source_video'])
    if not video.isOpened():
        raise FileNotFoundError(manifest['source_video'])
    result = {
        'match_id': MATCH.name, 'source_sha256': source_hash,
        'calibration_sha256': sha256(calibration_path),
        'rule_sha256': sha256(RULE), **input_hashes,
        'method': ('v2: preserve same-ID image continuity through accepted padded-court '
                   'boxes while holding the last strict-court anchor stale; all other '
                   'jump-grace gates copied from v1'),
        'label_access': 'none', 'windows': {},
    }
    try:
        for window in windows:
            name, first, last = (window['name'], window['first_frame'],
                                 window['last_frame'])
            predictions, diagnostics = filter_window(
                video, raw_by_window[name], base_by_window[name], matrix,
                first, last, manifest['fps'])
            result['windows'][name] = {
                'first_frame': first, 'last_frame': last,
                'predictions': predictions, 'diagnostics': diagnostics}
            print(f"{name}: {diagnostics['rescued_count']} boxes rescued")
    finally:
        video.release()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-json', type=Path)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    main(args.input_json, args.output)
