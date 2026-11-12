"""Attach source-reviewed anchor side to bridge proposals without publishing team IDs."""

import hashlib
import json
from pathlib import Path


BASE = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial')
QUEUE = BASE / 'team_bridge_side_review_queue.json'
REVIEWS = BASE / 'team_bridge_anchor_side_reviews.json'
OUT = BASE / 'team_bridge_reviewed_side_gate.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    queue = json.loads(QUEUE.read_text(encoding='utf-8'))
    reviews = json.loads(REVIEWS.read_text(encoding='utf-8'))
    if (queue['source_sha256'] != reviews['source_sha256'] or
            queue['trial_sha256'] != reviews['trial_sha256']):
        raise ValueError('Review provenance does not match the frozen proposal queue')
    by_key = {}
    for review in reviews['reviews']:
        key = (review['window'], int(review['track_id']), int(review['anchor_frame']))
        if key in by_key:
            raise ValueError(f'Duplicate review {key}')
        if review['observed_anchor_side'] not in ('near', 'far', 'uncertain'):
            raise ValueError(f'Invalid side for {key}')
        evidence = BASE / review['evidence']
        if not evidence.is_file():
            raise FileNotFoundError(evidence)
        by_key[key] = review
    leads = []
    counts = {'near_review_candidates': 0, 'far_withheld': 0, 'unresolved': 0}
    for lead in queue['leads']:
        key = (lead['window'], int(lead['track_id']), int(lead['anchor_frame']))
        review = by_key.pop(key, None)
        side = review['observed_anchor_side'] if review else 'uncertain'
        decision = {'near': 'near_anchor_review_candidate',
                    'far': 'withheld_far_anchor',
                    'uncertain': 'withheld_unresolved_anchor'}[side]
        count_key = {'near': 'near_review_candidates', 'far': 'far_withheld',
                     'uncertain': 'unresolved'}[side]
        counts[count_key] += len(lead['proposed_frames'])
        leads.append({
            'window': lead['window'], 'track_id': lead['track_id'],
            'anchor_frame': lead['anchor_frame'],
            'proposed_frames': lead['proposed_frames'],
            'observed_anchor_side': side, 'review_decision': decision,
            'team_status': 'unknown',
            'source_review_image': lead['source_review_image'],
            'review_basis': review['basis'] if review else None,
        })
    if by_key:
        raise ValueError(f'Reviews do not match any proposal: {list(by_key)}')
    OUT.write_text(json.dumps({
        'status': 'manual_side_gate_development_trial',
        'source_sha256': queue['source_sha256'],
        'trial_sha256': queue['trial_sha256'],
        'queue_sha256': sha256(QUEUE), 'review_sha256': sha256(REVIEWS),
        'policy': 'The review gate records side evidence but does not publish a team assignment. Same-ID continuity across all proposed frames remains unverified by manual side review.',
        'counts_by_proposed_box': counts, 'leads': leads,
    }, indent=2) + '\n', encoding='utf-8')
    print(counts)


if __name__ == '__main__':
    main()
