"""Score the frozen v2 rule on a separately labelled near-net block."""

import hashlib
import json
from pathlib import Path


ROOT = Path('data/processed/heldout_crossing_eval_em6z')
LABELS = ROOT / 'block_event_labels_860_960.json'
BASE = ROOT / 'frozen_block_segment_860_960.json'
V2 = ROOT / 'frozen_block_segment_v2_860_960.json'
OUT = ROOT / 'frozen_block_event_v2_score.json'
TRACK_ID = 96  # Matched to blue #9 using source frames and the saved overlay.


def expand(ranges):
    return {frame for first, last in ranges for frame in range(first, last + 1)}


def present(rows):
    found = [row for row in rows if row['track_id'] == TRACK_ID]
    if len(found) > 1:
        raise ValueError(f'Duplicate track {TRACK_ID}')
    return found[0] if found else None


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text())
    base = json.loads(BASE.read_text())
    v2 = json.loads(V2.read_text())
    if len({labels['source_sha256'], base['source_sha256'], v2['source_sha256']}) != 1:
        raise ValueError('Source mismatch')
    if v2['input_json_sha256'] != hashlib.sha256(BASE.read_bytes()).hexdigest():
        raise ValueError('Prediction input mismatch')
    rule_path = Path('scripts/airborne_grace_filter_v2.py')
    if v2['rule_sha256'] != hashlib.sha256(rule_path.read_bytes()).hexdigest():
        raise ValueError('V2 rule changed')
    airborne = expand(labels['clearly_airborne_ranges_inclusive'])
    grounded = expand(labels['clearly_grounded_ranges_inclusive'])
    uncertain = expand(labels['uncertain_ranges_inclusive'])
    if airborne & grounded or airborne & uncertain or grounded & uncertain:
        raise ValueError('Label ranges overlap')
    rows = []
    for frame in sorted(airborne | grounded):
        key = str(frame)
        raw = present(base['raw_predictions'][key])
        team = present(base['court_jersey_predictions'][key])
        v1 = present(base['airborne_grace_predictions'][key])
        candidate = present(v2['windows']['segment']['predictions'][key])
        rows.append({
            'frame': frame,
            'visual_status': 'airborne' if frame in airborne else 'grounded',
            'raw_box_present': raw is not None,
            'court_jersey_box_present': team is not None,
            'v1_box_present': v1 is not None,
            'v2_box_present': candidate is not None,
            'v2_possible_airborne': bool(candidate and candidate.get('court_position_status') == 'possible_airborne'),
        })
    def totals(status):
        subset = [row for row in rows if row['visual_status'] == status]
        return {
            'visual_frames': len(subset),
            'raw_boxes': sum(row['raw_box_present'] for row in subset),
            'court_jersey_boxes': sum(row['court_jersey_box_present'] for row in subset),
            'v1_boxes': sum(row['v1_box_present'] for row in subset),
            'v2_boxes': sum(row['v2_box_present'] for row in subset),
            'v2_possible_airborne_flags': sum(row['v2_possible_airborne'] for row in subset),
        }
    result = {
        'source_sha256': labels['source_sha256'],
        'labels_file': str(LABELS),
        'base_predictions_file': str(BASE),
        'v2_predictions_file': str(V2),
        'v2_rule_sha256': v2['rule_sha256'],
        'visually_matched_raw_track_id': TRACK_ID,
        'matching_evidence': str(ROOT / 'jump_label_review/block_predictions_overlay.jpg'),
        'scope': 'One source-only labelled blocker in the same match; event-level box retention, not six-player MOT ground truth.',
        'airborne': totals('airborne'),
        'grounded': totals('grounded'),
        'frames': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'airborne': result['airborne'], 'grounded': result['grounded']}, indent=2))


if __name__ == '__main__':
    main()
