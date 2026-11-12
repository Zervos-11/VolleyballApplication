"""Record conservative single-reviewer phase decisions for 18 selected frames.

Decisions use the unboxed +/-0.4 s context strips, not VideoMAE predictions.
They describe a local instant only, never exact rally start/end frames.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SELECTION = BASE / 'phase_six_candidate_review/selected.json'
CONTEXT = BASE / 'phase_six_candidate_review/context/index.json'
OUT = BASE / 'selected_phase_source_qc.json'
EXTENDED = BASE / 'phase_six_candidate_review/uncertain_context'
EXTENDED_KEYS = ((1, 5), (1, 18), (1, 27), (1, 34), (3, 11), (3, 27))
FOCUS = BASE / 'focus_phase_sequence/index.json'


# Evidence from motion across three source frames, with conservative unknowns.
DECISIONS = {
    (1, 5): ('visible_live_play', 'At 47.4 s the ball is in flight above the near court; the source sequence continues to a near attack.'),
    (1, 6): ('visible_live_play', 'Far-side attack and near-side defensive response across the strip.'),
    (1, 18): ('visible_live_play', 'Extended context shows the active exchange before players disperse by 180 s.'),
    (1, 27): ('visible_live_play', 'Extended context carries the same exchange into a near-side attack at 246.6 s.'),
    (1, 34): ('visible_live_play', 'At 322.4 s the far-side team is in a continuing exchange after the near-side serve, before its later attack.'),
    (1, 37): ('visible_live_play', 'Attack/block exchange and coordinated response across the strip.'),
    (2, 2): ('visible_live_play', 'Far-side player approaches and attacks; near team reacts.'),
    (2, 6): ('visible_live_play', 'Far-side attack and near-side defensive motion.'),
    (2, 14): ('after_point', 'The source sequence shows the near-side team beginning to gather and the far-side team walking at 535.8 s; the rally ended earlier.'),
    (2, 26): ('visible_live_play', 'Near-side players reposition toward an active exchange.'),
    (2, 28): ('visible_live_play', 'Near-side receive and far-side net attack/block motion.'),
    (2, 37): ('visible_live_play', 'Far-side net action and near-side defensive response.'),
    (3, 11): ('visible_live_play', 'Near-side reception has already occurred by 975.8 s and the selected 976.0 s frame shows the continuing exchange.'),
    (3, 13): ('visible_live_play', 'Far-side attacker and near-side response change across frames.'),
    (3, 23): ('after_point', 'Near-side server has returned and both teams walk/reset; live serve was earlier.'),
    (3, 27): ('visible_live_play', 'Extended context carries the exchange into a near-side block at 1139.4 s.'),
    (3, 33): ('visible_live_play', 'Far-side dive and near-side blocking/defensive action.'),
    (3, 34): ('visible_live_play', 'Far-side attack and near-side defensive response.'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    selection = json.loads(SELECTION.read_text(encoding='utf-8'))
    context = json.loads(CONTEXT.read_text(encoding='utf-8'))
    if context['selection_sha256'] != digest(SELECTION):
        raise ValueError('Context sheets do not match selected frames')
    focus = json.loads(FOCUS.read_text(encoding='utf-8'))
    if focus['selection_sha256'] != digest(SELECTION):
        raise ValueError('Focused source sequence does not match selected frames')
    for sheet in focus['sheets']:
        if digest(FOCUS.parent / sheet['path']) != sheet['sha256']:
            raise ValueError('Focused source sheet hash mismatch')
    keys = {(p['set'], p['point_number']) for p in selection['selected']}
    if keys != set(DECISIONS):
        raise ValueError('Not exactly the selected points')
    rows = []
    for p in selection['selected']:
        status, reason = DECISIONS[p['set'], p['point_number']]
        rows.append({'set': p['set'], 'point_number': p['point_number'],
                     'source_frame': p['source_frame'], 'source_second': p['source_second'],
                     'local_phase_status': status, 'review_note': reason,
                     'visual_six_distinct_near_boxes': True,
                     'geometric_candidate_count': p['geometric_candidate_count']})
    counts = Counter(r['local_phase_status'] for r in rows)
    result = {
        'status': 'single_reviewer_local_phase_screen_not_exact_rally_boundaries',
        'selection_sha256': digest(SELECTION), 'context_index_sha256': digest(CONTEXT),
        'extended_context_sha256': {
            f's{s}_p{p}': digest(EXTENDED / f's{s}_p{p}.jpg') for s, p in EXTENDED_KEYS},
        'focus_sequence_index_sha256': digest(FOCUS),
        'review_basis': 'Three unboxed source frames at selected frame +/-12 frames (0.4 s); '
                        'ambiguous and long-run cases additionally checked at +/-1 and +/-2 s and seven 5 Hz focus sequences',
        'summary': {'selected_points': len(rows), 'visible_live_play': counts['visible_live_play'],
                    'uncertain_phase': counts['uncertain_phase'],
                    'after_point': counts['after_point'],
                    'visual_six_distinct_near_boxes_at_selected_frame': len(rows)},
        'rows': rows,
        'limitations': [
            'Three-frame local motion does not identify exact serve and dead-ball frames.',
            'Uncertain instants must not be promoted to live-play metric frames.',
            'Six image boxes do not prove six grounded floor positions or stable identities.',
            'The selected instants were found using box availability and are not phase-matched outcome observations.'
        ]
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
