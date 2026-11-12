"""Apply the unchanged pilot near-court region gate to frozen held-out boxes.

This is a diagnostic separating geometry from the later jersey filter. No
held-out labels are read or used to select a threshold.
"""

import hashlib
import json
from pathlib import Path

from evaluate_pilot_tracker import image_to_court, in_target_region, project


MATCH = Path('data/matches/yt_em6zFUxfYpc')
CALIBRATION = MATCH / 'pilot/calibration/near_court.json'
RAW = MATCH / 'pilot/heldout_tracker_predictions.json'
OUT = MATCH / 'pilot/heldout_court_filtered_predictions.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    manifest = json.loads((MATCH / 'pilot/heldout_tracking_manifest.json').read_text())
    raw = json.loads(RAW.read_text())
    if raw['source_sha256'] != manifest['source_sha256']:
        raise ValueError('Raw predictions source hash mismatch')
    matrix = image_to_court(json.loads(CALIBRATION.read_text()))
    output = {
        'match_id': MATCH.name,
        'source_sha256': manifest['source_sha256'],
        'raw_predictions_sha256': sha256(RAW),
        'calibration_sha256': sha256(CALIBRATION),
        'method': 'Unchanged in_target_region from evaluate_pilot_tracker.py; first-window-frame service-zone bounds, then 1.5m court-edge allowance',
        'label_access': 'none',
        'windows': {},
    }
    for window in manifest['windows']:
        name, first = window['name'], window['first_frame']
        kept = {}
        for frame, predictions in raw['windows'][name]['predictions'].items():
            rows = []
            for prediction in predictions:
                x1, _, x2, y2 = prediction['bbox']
                xy_m = project([(x1 + x2) / 2, y2], matrix)
                if in_target_region(xy_m, int(frame) == first):
                    rows.append(prediction)
            kept[frame] = rows
        output['windows'][name] = {
            'first_frame': first, 'last_frame': window['last_frame'],
            'predictions': kept,
        }
        print(f'{name}: {sum(map(len,kept.values()))} of '
              f"{sum(map(len,raw['windows'][name]['predictions'].values()))} raw predictions kept")
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
