"""Score a frozen candidate filter on source-reviewed track runs without tuning it."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(raw_path, applied_path, sheets_path, reviews_path):
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    applied = json.loads(applied_path.read_text(encoding='utf-8'))
    sheets = json.loads(sheets_path.read_text(encoding='utf-8'))
    reviews = json.loads(reviews_path.read_text(encoding='utf-8'))
    if (reviews['raw_sha256'] != sha256(raw_path)
            or reviews['track_review_sheets_sha256'] != sha256(sheets_path)
            or reviews['source_sha256'] != raw['source_sha256']
            or sheets['raw_sha256'] != sha256(raw_path)
            or applied['raw_sha256'] != sha256(raw_path)
            or applied['label_access'] != 'none'):
        raise ValueError('Frozen prediction or review provenance mismatch')
    reviewed_frames = {int(row['track_id']): set(row['frames']) for row in sheets['tracks']}
    counts = {'near': {'selected': 0, 'total': 0}, 'far': {'selected': 0, 'total': 0}}
    run_scores, rows, seen = [], [], set()
    for run in reviews['runs']:
        side, track_id = run['side'], int(run['track_id'])
        if side not in counts:
            raise ValueError(f'Invalid side: {side}')
        selected_count = 0
        for frame in range(int(run['first_frame']), int(run['last_frame']) + 1):
            key = (frame, track_id)
            if key in seen or frame not in reviewed_frames.get(track_id, set()):
                raise ValueError(f'Duplicate or unreviewed detection: {key}')
            seen.add(key)
            raw_ids = {int(row['track_id']) for row in raw['predictions'][str(frame)]}
            selected_ids = {int(row['track_id']) for row in applied['predictions'][str(frame)]}
            if track_id not in raw_ids:
                raise ValueError(f'Frozen raw detection absent: {key}')
            selected = track_id in selected_ids
            selected_count += int(selected)
            counts[side]['total'] += 1
            counts[side]['selected'] += int(selected)
            rows.append({'frame': frame, 'track_id': track_id, 'reviewed_side': side,
                         'selected_as_near_candidate': selected})
        run_scores.append({**run, 'selected': selected_count,
                           'total': int(run['last_frame']) - int(run['first_frame']) + 1})
    return {
        'status': 'frozen_selected_run_diagnostic',
        'raw_sha256': sha256(raw_path), 'applied_sha256': sha256(applied_path),
        'reviews_sha256': sha256(reviews_path), 'rule_sha256': applied['rule_sha256'],
        'warning': 'These are visually selected, correlated boxes from the source named in the raw predictions. They are not full detection recall, team-classification precision, or player identity accuracy.',
        'counts': counts, 'run_scores': run_scores, 'rows': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--applied', type=Path, required=True)
    parser.add_argument('--sheets', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = score(args.raw, args.applied, args.sheets, args.reviews)
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['counts'])


if __name__ == '__main__':
    main()
