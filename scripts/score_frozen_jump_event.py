"""Score one source-only visual jump label against pre-frozen predictions.

The track ID is matched visually after the labels are written. This is an
event-level diagnostic, not full-team MOT ground truth or HOTA.
"""

import hashlib
import json
from pathlib import Path

from evaluate_pilot_tracker import image_to_court, project


ROOT = Path('data/processed/heldout_crossing_eval_em6z')
MATCH = Path('data/matches/yt_em6zFUxfYpc')
LABELS = ROOT / 'jump_event_labels_150_239.json'
PREDICTIONS = ROOT / 'frozen_jump_segment_150_239.json'
OUT = ROOT / 'frozen_jump_event_score.json'
TRACK_ID = 179  # Visually matched to the blue-and-white hitter after labelling.


def expand(ranges):
    return {frame for first, last in ranges for frame in range(first, last + 1)}


def select(rows):
    found = [row for row in rows if row['track_id'] == TRACK_ID]
    if len(found) > 1:
        raise ValueError(f'Duplicate track {TRACK_ID} in one frame')
    return found[0] if found else None


def main():
    labels = json.loads(LABELS.read_text())
    predictions = json.loads(PREDICTIONS.read_text())
    if labels['source_sha256'] != predictions['source_sha256']:
        raise ValueError('Labels and predictions belong to different video sources')
    rule_path = Path('scripts/airborne_grace_filter.py')
    rule_hash = hashlib.sha256(rule_path.read_bytes()).hexdigest()
    if predictions['rule_sha256'] != rule_hash:
        raise ValueError('Frozen predictions used a different jump-grace rule')
    calibration = json.loads((MATCH / 'pilot/calibration/near_court.json').read_text())
    matrix = image_to_court(calibration)
    airborne = expand(labels['clearly_airborne_ranges_inclusive'])
    grounded = expand(labels['clearly_grounded_ranges_inclusive'])
    uncertain = expand(labels['uncertain_ranges_inclusive'])
    if airborne & grounded or airborne & uncertain or grounded & uncertain:
        raise ValueError('Visual-label ranges overlap')
    rows = []
    for frame in sorted(airborne | grounded):
        key = str(frame)
        raw = select(predictions['raw_predictions'][key])
        base = select(predictions['court_jersey_predictions'][key])
        grace = select(predictions['airborne_grace_predictions'][key])
        position = None
        if raw:
            box = raw['bbox']
            xy = project([(box[0] + box[2]) / 2, box[3]], matrix)
            position = [round(float(value), 3) for value in xy]
        rows.append({
            'frame': frame, 'visual_status': ('airborne' if frame in airborne else 'grounded'),
            'raw_box_present': raw is not None,
            'court_jersey_box_present': base is not None,
            'grace_box_present': grace is not None,
            'grace_flag': grace.get('court_position_status') if grace else None,
            'raw_box_bottom_projected_m': position,
        })
    def totals(status):
        subset = [row for row in rows if row['visual_status'] == status]
        return {
            'visual_frames': len(subset),
            'raw_boxes': sum(row['raw_box_present'] for row in subset),
            'court_jersey_boxes': sum(row['court_jersey_box_present'] for row in subset),
            'grace_boxes': sum(row['grace_box_present'] for row in subset),
            'grace_possible_airborne_flags': sum(
                row['grace_flag'] == 'possible_airborne' for row in subset),
        }
    result = {
        'source_sha256': labels['source_sha256'],
        'rule_sha256': rule_hash,
        'labels_file': str(LABELS),
        'predictions_file': str(PREDICTIONS),
        'visually_matched_raw_track_id': TRACK_ID,
        'matching_evidence': str(ROOT / 'jump_label_review/frozen_predictions_overlay.jpg'),
        'scope': ('One visually labelled jumper; boxes are not independent manual '
                  'ground truth, so this is event recall and box-retention accounting, '
                  'not TrackEval.'),
        'airborne': totals('airborne'),
        'grounded': totals('grounded'),
        'frames': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'airborne': result['airborne'],
                      'grounded': result['grounded']}, indent=2))


if __name__ == '__main__':
    main()
