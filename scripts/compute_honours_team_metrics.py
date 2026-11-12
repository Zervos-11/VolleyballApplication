"""Compute three strict six-player court metrics from reviewed ground anchors.

Input must follow the schema in DELIVERABLES/HONOURS_METRIC_INPUT.md.
This script never infers missing positions or rally boundaries.
"""
import argparse
import hashlib
import json
import math
import statistics
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
POSITION_STATUSES = {
    'reviewed_floor_contact': 'reviewed_floor_contact',
    'reviewed_grounded_box_bottom_proxy': 'reviewed_grounded_box_bottom_proxy',
}


def hull_area(points):
    ordered = sorted(set(points))
    if len(ordered) < 3:
        return 0.0

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower = []
    for p in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(hull, hull[1:] + hull[:1]))) / 2


def metrics(points):
    assert len(points) == 6
    pairs = [math.dist(a, b) for a, b in combinations(points, 2)]
    center = (sum(p[0] for p in points) / 6, sum(p[1] for p in points) / 6)
    return {'mean_pairwise_spacing_m': sum(pairs) / 15,
            'convex_hull_area_m2': hull_area(points),
            'centroid_dispersion_m': sum(math.dist(p, center) for p in points) / 6}


def selected_points(sample):
    """Normalize the historical and UCLA score-only frozen sample schemas."""
    if 'selected_points' in sample:
        return {(r['set'], r['point_number']): r['winner'] for r in sample['selected_points']}
    if 'selected_events' in sample:
        return {(r['set'], r['point_number']):
                ('UCLA' if r['winner_scoreboard_side'] == 'left' else 'Concordia')
                for r in sample['selected_events']}
    raise ValueError('Unknown frozen sample schema')


def compute(data, sample):
    sample_id = sample['match_id'] if 'match_id' in sample else f"yt_{sample['video_id']}"
    if data['match_id'] != sample_id or data['source_sha256'] != sample['source_sha256']:
        raise ValueError('Source does not match the frozen primary-match sample')
    selected = selected_points(sample)
    key = (data['set'], data['point_number'])
    if key not in selected:
        raise ValueError('Point is not in the frozen sample')
    teams = ('UCLA', 'Concordia') if 'selected_events' in sample else ('ProVolley', 'UTS')
    if data['near_team'] not in teams:
        raise ValueError('Near-side team must be source-verified')
    if data['near_team_evidence_status'] != 'source_reviewed':
        raise ValueError('Near-side team assignment is not source-reviewed')
    if data.get('near_roster_review_status') != 'source_reviewed_near_six':
        raise ValueError('Six-player near-side roster is not source-reviewed')
    if data['calibration_status'] != 'validated_for_metric_use':
        raise ValueError('Court calibration is not validated for metric use')
    position_method = data.get('position_method', 'reviewed_floor_contact')
    if position_method not in POSITION_STATUSES:
        raise ValueError('Unknown position method')
    accepted_status = POSITION_STATUSES[position_method]
    boundary_status = data.get('rally_boundary_status')
    interval_type = ('source_reviewed_full_rally' if boundary_status == 'source_reviewed' else
                     'source_reviewed_fixed_analysis_window' if
                     data.get('analysis_window_status') == 'source_reviewed_fixed_window' else None)
    if interval_type is None:
        raise ValueError('Rally boundaries or fixed analysis window are not source-reviewed')
    if data['winner'] != selected[key]:
        raise ValueError('Winner differs from the frozen score record')
    roster = data['near_player_ids']
    if len(roster) != 6 or len(set(roster)) != 6:
        raise ValueError('Exactly six distinct near-player IDs are required')
    start, end = data['start_frame'], data['end_frame_exclusive']
    if not isinstance(start, int) or not isinstance(end, int) or start >= end:
        raise ValueError('Invalid reviewed frame interval')
    rows = []
    seen = set()
    for frame in data['frames']:
        number = frame['frame']
        if not isinstance(number, int) or number < start or number >= end or number in seen:
            raise ValueError('Frame out of interval or duplicated')
        seen.add(number)
        positions = frame['players']
        if set(positions) != set(roster):
            raise ValueError(f'Frame {number} must contain exactly the six roster slots')
        points = []
        reasons = []
        for player_id in roster:
            entry = positions[player_id]
            if entry['status'] != accepted_status:
                reasons.append(f'{player_id}:{entry["status"]}')
                continue
            x, y = entry['x_m'], entry['y_m']
            if not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 9 for v in (x, y)):
                reasons.append(f'{player_id}:invalid_court_position')
                continue
            points.append((float(x), float(y)))
        rows.append({'frame': number, 'status': 'eligible' if not reasons else 'ineligible',
                     'reasons': reasons, 'metrics': metrics(points) if not reasons else None})
    rows.sort(key=lambda r: r['frame'])
    eligible = [r for r in rows if r['status'] == 'eligible']
    summary = {name: statistics.median(r['metrics'][name] for r in eligible) if eligible else None
               for name in ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')}
    return {'status': 'reviewed_input_descriptive_metrics_no_outcome_inference',
            'match_id': data['match_id'], 'set': data['set'], 'point_number': data['point_number'],
            'winner': data['winner'], 'near_team': data['near_team'],
            'interval_type': interval_type,
            'position_method': position_method,
            'near_team_won': data['near_team'] == data['winner'],
            'frame_interval': [start, end], 'expected_frame_count': end - start,
            'submitted_frame_count': len(rows), 'eligible_frame_count': len(eligible),
            'eligible_fraction_of_submitted_frames': (len(eligible) / len(rows)) if rows else None,
            'eligible_fraction_of_interval': len(eligible) / (end - start),
            'rally_median_metrics': summary, 'frames': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sample', type=Path, default=SAMPLE,
                        help='Frozen outcome sample; defaults to historical ProVolley sample')
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    sample = json.loads(args.sample.read_text(encoding='utf-8'))
    result = compute(data, sample)
    result['input_sha256'] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    result['sample_sha256'] = hashlib.sha256(args.sample.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {args.output}: {result["eligible_frame_count"]}/{result["submitted_frame_count"]} '
          f'eligible submitted frames across {result["expected_frame_count"]} source frames')


if __name__ == '__main__':
    main()
