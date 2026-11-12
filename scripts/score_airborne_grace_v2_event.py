"""Compare v2 with the frozen baseline on the source-only labelled jump."""

import hashlib
import json
from pathlib import Path


ROOT = Path('data/processed/heldout_crossing_eval_em6z')
LABELS = ROOT / 'jump_event_labels_150_239.json'
BASE = ROOT / 'frozen_jump_segment_150_239.json'
V2 = ROOT / 'frozen_jump_segment_v2_150_239.json'
OUT = ROOT / 'frozen_jump_event_v2_score.json'
TRACK_ID = 179


def expand(ranges):
    return {frame for first, last in ranges for frame in range(first, last + 1)}


def select(rows):
    found = [row for row in rows if row['track_id'] == TRACK_ID]
    if len(found) > 1:
        raise ValueError(f'Duplicate track {TRACK_ID} in one frame')
    return found[0] if found else None


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text())
    base = json.loads(BASE.read_text())
    candidate = json.loads(V2.read_text())
    if len({labels['source_sha256'], base['source_sha256'],
            candidate['source_sha256']}) != 1:
        raise ValueError('Source hash mismatch')
    if candidate['input_json_sha256'] != hashlib.sha256(BASE.read_bytes()).hexdigest():
        raise ValueError('Candidate input mismatch')
    rule = Path('scripts/airborne_grace_filter_v2.py')
    if candidate['rule_sha256'] != hashlib.sha256(rule.read_bytes()).hexdigest():
        raise ValueError('Candidate rule has changed')
    airborne = expand(labels['clearly_airborne_ranges_inclusive'])
    grounded = expand(labels['clearly_grounded_ranges_inclusive'])
    uncertain = expand(labels['uncertain_ranges_inclusive'])
    if airborne & grounded or airborne & uncertain or grounded & uncertain:
        raise ValueError('Overlapping label ranges')
    frames = []
    v2_predictions = candidate['windows']['segment']['predictions']
    for frame in sorted(airborne | grounded):
        key = str(frame)
        raw = select(base['raw_predictions'][key])
        team = select(base['court_jersey_predictions'][key])
        v1 = select(base['airborne_grace_predictions'][key])
        v2 = select(v2_predictions[key])
        frames.append({
            'frame': frame,
            'visual_status': 'airborne' if frame in airborne else 'grounded',
            'raw_box_present': raw is not None,
            'court_jersey_box_present': team is not None,
            'v1_box_present': v1 is not None,
            'v2_box_present': v2 is not None,
            'v2_possible_airborne': bool(v2 and v2.get('court_position_status') == 'possible_airborne'),
        })
    def totals(status):
        rows = [row for row in frames if row['visual_status'] == status]
        return {'visual_frames': len(rows),
                'raw_boxes': sum(row['raw_box_present'] for row in rows),
                'court_jersey_boxes': sum(row['court_jersey_box_present'] for row in rows),
                'v1_boxes': sum(row['v1_box_present'] for row in rows),
                'v2_boxes': sum(row['v2_box_present'] for row in rows),
                'v2_possible_airborne_flags': sum(row['v2_possible_airborne'] for row in rows)}
    result = {
        'source_sha256': labels['source_sha256'],
        'v2_rule_sha256': candidate['rule_sha256'],
        'labels_file': str(LABELS),
        'base_predictions_file': str(BASE),
        'v2_predictions_file': str(V2),
        'track_id': TRACK_ID,
        'scope': 'Single-player event diagnostic; v2 was developed after reviewing this event, so this is not independent validation.',
        'airborne': totals('airborne'),
        'grounded': totals('grounded'),
        'frames': frames,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'airborne': result['airborne'], 'grounded': result['grounded']}, indent=2))


if __name__ == '__main__':
    main()
