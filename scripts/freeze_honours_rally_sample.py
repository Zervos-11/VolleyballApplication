"""Freeze a score-only, within-match rally review sample before spatial analysis."""
import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORE = ROOT / 'data/processed/fqe_auto_score_timeline.json'
QUEUE = ROOT / 'data/processed/fqe_rally_review_queue.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUTPUT = ROOT / 'data/processed/honours_rally_sample.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_RALLY_SAMPLE.md'
SEED = 20261101
PER_SET_WINNER = 3


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    score, queue, source = read(SCORE), read(QUEUE), read(SOURCE)
    assert score['match_id'] == queue['match_id'] == source['match_id']
    assert score['source_sha256'] == queue['source_sha256'] == source['sha256']
    assert len(queue['rows']) == score['point_count'] == 123
    queue_by_key = {(r['set'], r['point_number']): r for r in queue['rows']}
    assert len(queue_by_key) == 123
    rng = random.Random(SEED)
    groups = []
    chosen = []
    for set_number in (1, 2, 3):
        for winner in ('ProVolley', 'UTS'):
            eligible = [p for p in score['points']
                        if p['set'] == set_number and p['winner'] == winner
                        and p['evidence'] == 'automatic_broadcast_score_transition']
            assert len(eligible) >= PER_SET_WINNER
            selected = sorted(rng.sample(eligible, PER_SET_WINNER), key=lambda p: p['point_number'])
            groups.append({'set': set_number, 'winner': winner, 'eligible_points': len(eligible),
                           'selected_points': PER_SET_WINNER,
                           'selection_probability': PER_SET_WINNER / len(eligible)})
            for point in selected:
                row = queue_by_key[(set_number, point['point_number'])]
                assert row['winner'] == winner and row['score_after'] == point['score_after']
                chosen.append({'set': set_number, 'point_number': point['point_number'],
                               'winner': winner, 'score_after': point['score_after'],
                               'seek_from_frame': row['seek_from_frame'],
                               'seek_to_frame_exclusive': row['seek_to_frame_exclusive'],
                               'score_flip_frame': row['score_flip_frame'],
                               'pilot_rally_id': row['pilot_rally_id'],
                               'boundary_status': row['boundary_status'],
                               'serve_contact_frame': row['serve_contact_frame'],
                               'end_frame_exclusive': row['end_frame_exclusive'],
                               'spatial_analysis_status': 'pending_source_review'})
    chosen.sort(key=lambda x: (x['set'], x['point_number']))
    assert len(chosen) == 18 and len({(x['set'], x['point_number']) for x in chosen}) == 18
    result = {'status': 'frozen_score_only_review_sample_not_spatial_analysis',
              'match_id': source['match_id'], 'source_sha256': source['sha256'],
              'seed': SEED, 'per_set_winner': PER_SET_WINNER,
              'eligibility': 'directly_observed_plus_one_broadcast_score_transition_only',
              'selection': 'simple_random_without_replacement_within_each_set_and_winner_group',
              'selection_before_spatial_metric_scoring': True,
              'group_counts': groups, 'selected_points': chosen,
              'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (SCORE, QUEUE, SOURCE)},
              'limits': ['Seek intervals are review navigation, not rally boundaries.',
                         'Point winner is not serving team, side-out status or phase.',
                         'Video eligibility and spatial missingness are not yet reviewed.',
                         'One match does not support population-level volleyball inference.']}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(
        f"| {r['set']} | {r['point_number']} | {r['score_after']} | {r['winner']} | "
        f"{r['seek_from_frame']}-{r['seek_to_frame_exclusive']} | {r['boundary_status']} |"
        for r in chosen)
    REPORT.write_text(f'''# Frozen honours rally review sample

This [machine-readable sample](../data/processed/honours_rally_sample.json) was selected using the automatic **score and point-winner records only**, before scoring team-position metrics. It contains three ProVolley-won and three UTS-won points from each set (**18 points**), using seed `{SEED}` and simple random sampling without replacement within each set/winner group. The first visible 1-0 point and inferred set-one 25-15 point were ineligible because their changes were not directly shown. The JSON records input hashes and each group's selection probability.

| Set | Point | Score after | Winner | Video seek frames | Boundary status |
| --- | ---: | ---: | --- | ---: | --- |
{table}

The seek frames are navigation aids; they are **not accepted rally boundaries**. The [source-frame screen](HONOURS_SAMPLE_SCREEN.md) provides three local stills per point and shows that the near-side uniforms change between sets. Every sampled point still needs source review for rally interval, near-side team and player identities, floor positions and calibration before it can contribute to a spatial metric. The sample is a target, not a claim that 18 analyzable rallies exist. Preserve exclusions and reasons; do not replace difficult rallies simply because tracking fails. Score winner alone does not establish near-side outcome, serving team, side-out, rotation or phase.

This is a balanced within-match development sample. It is not an unbiased estimate of the match's natural win/loss rate or of volleyball generally. Any eventual comparison must report the analyzed denominators and missingness by outcome and set.

Regenerate with `.\\.venv\\Scripts\\python.exe scripts/freeze_honours_rally_sample.py` only if intentionally creating a new sample version. Once player review begins, keep this selection frozen.
''', encoding='utf-8')
    print(f'Wrote {OUTPUT} and {REPORT}')


if __name__ == '__main__':
    main()
