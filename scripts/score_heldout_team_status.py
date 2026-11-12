"""Score candidate/unknown status against existing near-player box labels."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluate_pilot_tracker import iou


MATCH = Path('data/matches/yt_em6zFUxfYpc')
STATUS = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial/heldout_team_status.json')
OUT = STATUS.with_name('heldout_team_status_score_corrected.json')


def match_frame(players, boxes):
    pairs = sorted(((iou(player['bbox'], box['bbox']), pi, bi)
                    for pi, player in enumerate(players)
                    for bi, box in enumerate(boxes)), reverse=True)
    used_players, used_boxes, matches = set(), set(), []
    for overlap, pi, bi in pairs:
        if overlap < .5:
            break
        if pi not in used_players and bi not in used_boxes:
            used_players.add(pi)
            used_boxes.add(bi)
            matches.append((pi, bi, overlap))
    return matches, used_players, used_boxes


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    trial = json.loads(STATUS.read_text())
    scored = {}
    for name, window in trial['windows'].items():
        labels_path = MATCH / 'pilot/player_annotations' / f'{name}.json'
        labels = json.loads(labels_path.read_text())
        counts = Counter()
        matched_unknown_reasons = Counter()
        per_frame = []
        for frame, record in labels['frames'].items():
            players = [player for player in record['players'] if player.get('bbox') is not None]
            boxes = window['frames'][frame]
            matches, used_players, _ = match_frame(players, boxes)
            candidates = [box for box in boxes if box['team_status'] == 'target_candidate']
            candidate_matches, candidate_players, candidate_boxes = match_frame(players, candidates)
            remaining = [player for index, player in enumerate(players)
                         if index not in candidate_players]
            unknown = [box for box in boxes if box['team_status'] == 'unknown']
            recovered, _, _ = match_frame(remaining, unknown)
            counts['visible_labels'] += len(players)
            counts['matched_raw'] += len(matches)
            counts['raw_misses'] += len(players) - len(used_players)
            counts['matched_target_candidate'] += len(candidate_matches)
            counts['candidate_misses'] += len(players) - len(candidate_players)
            counts['candidate_misses_recoverable_from_unknown'] += len(recovered)
            for pi, bi, overlap in recovered:
                matched_unknown_reasons[unknown[bi]['reason']] += 1
            for box in boxes:
                counts[f"{box['team_status']}_boxes"] += 1
            counts['unmatched_target_candidate_boxes'] += len(candidates) - len(candidate_boxes)
            per_frame.append({'frame': int(frame), 'visible_labels': len(players),
                              'matched_raw': len(matches),
                              'matched_target_candidate': len(candidate_matches),
                              'candidate_misses_recoverable_from_unknown': len(recovered)})
        scored[name] = {'labels_sha256': hashlib.sha256(labels_path.read_bytes()).hexdigest(),
                        'counts': dict(counts),
                        'matched_unknown_reasons': dict(matched_unknown_reasons),
                        'per_frame': per_frame}
    totals = Counter()
    reasons = Counter()
    for result in scored.values():
        totals.update(result['counts'])
        reasons.update(result['matched_unknown_reasons'])
    OUT.write_text(json.dumps({
        'status': 'development_score',
        'candidate_sha256': hashlib.sha256(STATUS.read_bytes()).hexdigest(),
        'matching': 'one-to-one greedy maximum IoU, threshold 0.5; match target candidates independently of raw boxes, then unknown boxes to remaining labels',
        'windows': scored, 'total_counts': dict(totals),
        'matched_unknown_reasons': dict(reasons),
    }, indent=2) + '\n', encoding='utf-8')
    print(dict(totals), dict(reasons))


if __name__ == '__main__':
    main()
