#!/usr/bin/env python3
"""Select rallies reproducibly from a human-screened register, balanced across strata."""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def sample(rows, per_match=10, seed=20261009):
    if per_match < 1:
        raise ValueError('per-match must be positive')
    records = [dict(row) for row in rows]
    seen = set()
    groups = defaultdict(lambda: defaultdict(list))
    for row in records:
        key = row['match_id'], row['rally_id']
        if not all(key) or key in seen:
            raise ValueError(f'Empty or duplicate match/rally ID: {key}')
        seen.add(key)
        row.update(selected='false', sample_seed=str(seed), selection_probability='0')
        if row['eligible'] not in ('true', 'false'):
            raise ValueError(f'eligible must be true/false: {key}')
        if row['eligible'] == 'true':
            if row.get('split') not in ('development', 'evaluation') or row.get('dataset_stage') not in ('pilot', 'main'):
                raise ValueError(f'Assign dataset_stage and split before sampling: {key}')
            if row['dataset_stage'] == 'pilot' and row['split'] == 'evaluation':
                raise ValueError('Pilot data cannot be held-out evaluation data')
            start, end = int(row['start_frame']), int(row['end_frame_exclusive'])
            if not 0 <= start < end or not row.get('stratum'):
                raise ValueError(f'Invalid interval or missing stratum: {key}')
            groups[row['match_id']][row['stratum']].append(row)
    for match_id, strata in sorted(groups.items()):
        assignments = {(r['dataset_stage'], r['split']) for group in strata.values() for r in group}
        if len(assignments) != 1:
            raise ValueError(f'A match cannot cross dataset stages or splits: {match_id}')
        rng = random.Random(f'{seed}:{match_id}')
        names = sorted(strata)
        if len(names) > per_match:
            raise ValueError(f'Merge strata before sampling: {match_id} has more strata than sample slots')
        # Fixed allocation then random sampling: inclusion probability is n_h / N_h.
        quotas = dict.fromkeys(names, 0)
        count = min(per_match, sum(map(len, strata.values())))
        for _ in range(count):
            name = min((n for n in names if quotas[n] < len(strata[n])), key=lambda n: (quotas[n], n))
            quotas[name] += 1
        for name in names:
            candidates = sorted(strata[name], key=lambda row: row['rally_id'])
            for row in candidates:
                row['selection_probability'] = f'{quotas[name] / len(candidates):.8f}'
            for row in rng.sample(candidates, quotas[name]):
                row['selected'] = 'true'
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--per-match', type=int, default=10)
    parser.add_argument('--seed', type=int, default=20261009)
    args = parser.parse_args()
    if args.register.resolve() == args.out.resolve():
        parser.error('Use a separate output file to preserve the screened register')
    with args.register.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if not rows:
        parser.error('The register is empty; screen and label real rallies first')
    try:
        sampled = sample(rows, args.per_match, args.seed)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sampled)
    print(f"Selected {sum(r['selected'] == 'true' for r in sampled)} of {len(rows)} registered rallies")
