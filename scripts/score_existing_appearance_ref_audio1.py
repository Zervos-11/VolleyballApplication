"""Score the pre-existing jersey filter on the separate match's reviewed runs."""

import hashlib
import json
from pathlib import Path


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
APPLIED = BASE / 'unchanged_court_jersey_candidates.json'
REVIEWS = BASE / 'reviewed_track_runs.json'
OUT = BASE / 'unchanged_court_jersey_reviewed_score.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    applied = json.loads(APPLIED.read_text(encoding='utf-8'))
    reviews = json.loads(REVIEWS.read_text(encoding='utf-8'))
    if applied['raw_sha256'] != reviews['raw_sha256']:
        raise ValueError('Frozen raw output differs between rule and reviews')
    counts = {'near': {'selected': 0, 'total': 0},
              'far': {'selected': 0, 'total': 0}}
    run_scores = []
    for review in reviews['runs']:
        selected = 0
        for frame in range(review['first_frame'], review['last_frame'] + 1):
            ids = {int(row['track_id']) for row in applied['predictions'][str(frame)]}
            selected += int(review['track_id'] in ids)
        side = review['side']
        total = review['last_frame'] - review['first_frame'] + 1
        counts[side]['selected'] += selected
        counts[side]['total'] += total
        run_scores.append({**review, 'selected': selected, 'total': total})
    OUT.write_text(json.dumps({
        'status': 'selected_reviewed_run_diagnostic',
        'applied_sha256': sha256(APPLIED), 'reviews_sha256': sha256(REVIEWS),
        'rule_sha256': applied['rule_sha256'],
        'warning': 'Only visually selected runs are scored; adjacent frames are correlated. This is a separate match, not a full MOT or team-classification accuracy estimate.',
        'counts': counts, 'run_scores': run_scores,
    }, indent=2) + '\n', encoding='utf-8')
    print(counts)
    print([(r['track_id'], r['side'], r['selected'], r['total']) for r in run_scores])


if __name__ == '__main__':
    main()
