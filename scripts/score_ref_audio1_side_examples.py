"""Score the existing strict near-court geometry on source-reviewed examples."""

import hashlib
import json
from pathlib import Path

from evaluate_pilot_tracker import image_to_court, project


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
LABELS = BASE / 'source_side_examples.json'
CALIBRATION = Path('data/matches/yt_ref_audio1/homography.json')
OUT = BASE / 'strict_court_side_diagnostic.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    if labels['raw_sha256'] != sha256(RAW):
        raise ValueError('Reviewed labels do not match frozen predictions')
    if raw['calibration_sha256'] != sha256(CALIBRATION):
        raise ValueError('Calibration changed')
    matrix = image_to_court(json.loads(CALIBRATION.read_text(encoding='utf-8')))
    counts = {'near_accepted': 0, 'near_total': 0,
              'far_accepted': 0, 'far_total': 0}
    rows = []
    for frame, review in labels['frames'].items():
        predictions = {int(row['track_id']): row for row in raw['predictions'][frame]}
        for side in ('near', 'far'):
            for track_id in review[f'{side}_track_ids']:
                box = predictions[track_id]['bbox']
                court_x, court_y = map(float, project(((box[0] + box[2]) / 2,
                                                        box[3]), matrix))
                accepted = 0 <= court_x <= 9 and 0 <= court_y <= 9.5
                counts[f'{side}_total'] += 1
                counts[f'{side}_accepted'] += int(accepted)
                rows.append({'frame': int(frame), 'track_id': track_id,
                             'source_reviewed_side': side,
                             'projected_box_bottom_court_m':
                                 [round(court_x, 3), round(court_y, 3)],
                             'strict_court_accepted': accepted})
    OUT.write_text(json.dumps({
        'status': 'small_source_reviewed_diagnostic',
        'raw_sha256': sha256(RAW), 'labels_sha256': sha256(LABELS),
        'calibration_sha256': sha256(CALIBRATION),
        'rule': 'bbox bottom centre projects to 0<=court_x<=9m and 0<=court_y<=9.5m; no jersey filter',
        'counts': counts, 'rows': rows,
    }, indent=2) + '\n', encoding='utf-8')
    print(counts)


if __name__ == '__main__':
    main()
