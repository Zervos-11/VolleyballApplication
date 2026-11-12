"""Convert a monotone candidate score scan into visible point-change events."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCAN = BASE / 'score_second_candidate.json'
OUT = BASE / 'point_register_candidate.json'


def main():
    source = json.loads(SCAN.read_text(encoding='utf-8'))
    rows = source['rows']
    if len(rows) != 1300 or rows[0]['candidate_score'] != [0, 0]:
        raise ValueError('Unexpected scan length or initial score')
    set_number = 1
    point_number = 0
    events = []
    resets = []
    anomalies = []
    for before, after in zip(rows, rows[1:]):
        old = before['candidate_score']
        new = after['candidate_score']
        if old == new:
            continue
        if new == [0, 0] and max(old) >= 24:
            resets.append({'completed_set': set_number, 'last_visible_score': old,
                           'first_zero_second': after['second']})
            set_number += 1
            point_number = 0
            continue
        delta = [b - a for a, b in zip(old, new)]
        if delta not in ([1, 0], [0, 1]):
            anomalies.append({'set': set_number, 'second': after['second'],
                              'before': old, 'after': new})
            continue
        point_number += 1
        events.append({'set': set_number, 'point_number': point_number,
                       'score_before': old, 'score_after': new,
                       'winner_scoreboard_side': 'left' if delta[0] else 'right',
                       'score_change_first_sample_second': after['second'],
                       'score_change_previous_sample_second': before['second'],
                       'rally_end_status': 'unknown_score_update_is_after_play'})
    output = {
        'status': 'candidate_visible_score_changes_not_independently_audited',
        'video_id': source['video_id'], 'source_sha256': source['source_sha256'],
        'score_scan_sha256': hashlib.sha256(SCAN.read_bytes()).hexdigest(),
        'visible_point_count': len(events), 'set_reset_count': len(resets),
        'anomaly_count': len(anomalies), 'set_resets': resets,
        'anomalies': anomalies, 'events': events,
        'limitations': [
            'The left and right school-name mapping is not yet source-verified.',
            'A score update gives the winner but not the exact serve or rally-end frame.',
            'Displayed final set points can be absent at recording or score-graphic cuts.',
            'Freeze a rally sample only after independent source checks of this register.'
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print({'visible_points': len(events), 'set_resets': len(resets),
           'anomalies': len(anomalies),
           'per_set': {i: sum(e['set'] == i for e in events) for i in (1, 2, 3)}})


if __name__ == '__main__':
    main()
