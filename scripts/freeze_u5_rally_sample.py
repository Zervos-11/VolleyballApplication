"""Freeze a balanced score-only candidate sample for the elevated match."""
import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
REGISTER = BASE / 'point_register_candidate.json'
OUT = BASE / 'rally_sample_score_only.json'
SEED = 20261102
PER_GROUP = 3


def main():
    source = json.loads(REGISTER.read_text(encoding='utf-8'))
    if source['anomaly_count'] or source['visible_point_count'] != 122:
        raise ValueError('Point register differs from reviewed candidate scan')
    rng = random.Random(SEED)
    selected = []
    strata = []
    for set_number in (1, 2, 3):
        for side in ('left', 'right'):
            eligible = [event for event in source['events']
                        if event['set'] == set_number and event['winner_scoreboard_side'] == side]
            picks = rng.sample(eligible, PER_GROUP)
            strata.append({'set': set_number, 'winner_scoreboard_side': side,
                           'eligible_count': len(eligible), 'selected_count': PER_GROUP,
                           'selection_probability': PER_GROUP / len(eligible)})
            selected.extend(picks)
    selected.sort(key=lambda event: (event['set'], event['point_number']))
    output = {
        'status': 'score_only_sample_frozen_from_candidate_register_pending_source_review',
        'video_id': source['video_id'], 'source_sha256': source['source_sha256'],
        'point_register_sha256': hashlib.sha256(REGISTER.read_bytes()).hexdigest(),
        'seed': SEED, 'sampling_rule': 'simple random sampling without replacement: 3 visible score changes per set and scoreboard winner side',
        'strata': strata, 'selected_events': selected,
        'restrictions': [
            'Selections precede spatial inspection of these points.',
            'The sampled second is a score-display change, not the rally end.',
            'Exact point intervals, player-side mapping and team identities remain to be source-reviewed.',
            'If an event fails review, record its exclusion; do not silently replace it with an easier rally.'
        ],
    }
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding='utf-8'))
        if previous != output:
            raise RuntimeError('Frozen sample already exists with different content')
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print([(e['set'], e['point_number'], e['winner_scoreboard_side'],
            e['score_change_first_sample_second']) for e in selected])


if __name__ == '__main__':
    main()
