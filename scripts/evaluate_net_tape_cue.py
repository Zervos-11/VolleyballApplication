"""Audit lower-net-tape visibility against held-out near-player labels.

The far-side comparison uses projected raw boxes as a rough proxy, not manual
far-team labels. Results are diagnostic and cannot establish precision.
"""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from evaluate_pilot_tracker import image_to_court, project
from net_tape_visibility import tape_visibility


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
OUT = Path('data/processed/pilot_tracker_evaluation/net_cue_trial/heldout_tape_audit.json')
TAPE_LINE_PX = ((70, 618), (1515, 618))  # Manual lower-tape estimate for this static camera.


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
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
            labels_path = PILOT / 'player_annotations' / f'{name}.json'
            labels = json.loads(labels_path.read_text())
            rows = []
            for key, frame in labels['frames'].items():
                video.set(cv2.CAP_PROP_POS_FRAMES, int(key))
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode frame {key}')
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                for player in frame['players']:
                    box = player.get('bbox')
                    if box is None:
                        continue
                    measure = tape_visibility(image, box, TAPE_LINE_PX, hsv)
                    rows.append({'frame': int(key), 'source': 'labelled_near',
                                 'player_id': player['player_id'], **measure})
                for pred in raw['windows'][name]['predictions'][key]:
                    box = pred['bbox']
                    position = project([(box[0] + box[2]) / 2, box[3]], matrix)
                    if float(position[1]) <= 11.0:
                        continue
                    measure = tape_visibility(image, box, TAPE_LINE_PX, hsv)
                    rows.append({'frame': int(key), 'source': 'far_geometry_proxy',
                                 'track_id': pred['track_id'],
                                 'projected_box_bottom_y_m': round(float(position[1]), 3),
                                 **measure})
            def summarize(source):
                subset = [row for row in rows if row['source'] == source]
                measured = [row for row in subset if row['status'] == 'measured']
                fractions = [row['white_ridge_fraction'] for row in measured]
                return {'total_boxes': len(subset), 'eligible': len(measured),
                        'median_fraction': round(float(np.median(fractions)), 3) if fractions else None,
                        'p90_fraction': round(float(np.percentile(fractions, 90)), 3) if fractions else None,
                        'fraction_at_least_0_5': sum(value >= .5 for value in fractions)}
            windows[name] = {
                'labels_sha256': hashlib.sha256(labels_path.read_bytes()).hexdigest(),
                'near': summarize('labelled_near'),
                'far_proxy': summarize('far_geometry_proxy'),
                'rows': rows,
            }
            print(name, windows[name]['near'], windows[name]['far_proxy'])
    finally:
        video.release()
    result = {
        'source_sha256': manifest['source_sha256'],
        'raw_predictions_sha256': hashlib.sha256((PILOT / 'heldout_tracker_predictions.json').read_bytes()).hexdigest(),
        'rule_sha256': hashlib.sha256(Path('scripts/net_tape_visibility.py').read_bytes()).hexdigest(),
        'tape_line_px': TAPE_LINE_PX,
        'scope': ('Near boxes are independently annotated. Far comparison uses only '
                  'projected raw-box position and can include airborne near players.'),
        'windows': windows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
