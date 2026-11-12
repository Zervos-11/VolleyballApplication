"""Screen clip-bounded, anonymous six-box rally geometry over coarse live cores.

These are provisional availability summaries. Neither a raw detector six nor a
coarse live core is a source-reviewed eligible metric frame.
"""
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
CUTS = BASE / 'rally_cut_clip_register.json'
PHASE = BASE / 'selected_phase_source_qc.json'
SAMPLE = BASE / 'rally_sample_score_only.json'
OUT = BASE / 'cut_bounded_provisional_rally_metrics.json'
NAMES = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlap_iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    intersection = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    return intersection / (area_a + area_b - intersection) if area_a + area_b > intersection else 0


def frame_rejection(row):
    people = [p for p in row['proposals'] if p['net_side_status'] == 'near_floor_side_candidate']
    if len(people) != 6:
        return 'not_exactly_six_geometric_candidates', None
    if row['net_boundary_review_count']:
        return 'additional_net_boundary_box_unresolved', None
    if any(not all(0 <= coordinate <= 9 for coordinate in p['box_bottom_court_m']) for p in people):
        return 'box_bottom_outside_strict_9m_court', None
    if any(overlap_iou(people[i]['bbox_px'], people[j]['bbox_px']) > .5
           for i in range(6) for j in range(i + 1, 6)):
        return 'possible_duplicate_high_box_overlap', None
    return None, [tuple(p['box_bottom_court_m']) for p in people]


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    cuts = json.loads(CUTS.read_text(encoding='utf-8'))
    phase = json.loads(PHASE.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    if len({len(tracks['points']), len(phase['rows']), len(cuts['selected_clips'])}) != 1:
        raise ValueError('Point counts differ')
    if len(tracks['points']) != 18 or not (tracks['source_sha256'] == cuts['source_sha256'] == sample['source_sha256']):
        raise ValueError('Expected 18 points from one source video')
    clip_by_key = {(r['set'], r['point_number']): r for r in cuts['selected_clips']}
    phase_by_key = {(r['set'], r['point_number']): r for r in phase['rows']}
    sample_by_key = {(r['set'], r['point_number']): r for r in sample['selected_events']}
    if not (set(clip_by_key) == set(phase_by_key) == set(sample_by_key) ==
            {(r['set'], r['point_number']) for r in tracks['points']}):
        raise ValueError('Point keys differ')
    rows = []
    for point in tracks['points']:
        key = point['set'], point['point_number']
        clip = clip_by_key[key]
        local_phase = phase_by_key[key]['local_phase_status']
        if any(not clip['clip_start_frame_inclusive'] <= r['source_frame'] < clip['clip_end_frame_exclusive']
               for r in point['rows']):
            raise ValueError(f'Sampled frame outside clip: {key}')
        winner = 'UCLA' if sample_by_key[key]['winner_scoreboard_side'] == 'left' else 'Concordia'
        near = 'UCLA' if key[0] in (1, 3) else 'Concordia'
        reasons = Counter()
        frames = []
        if local_phase == 'visible_live_play':
            for source in point['rows']:
                reason, positions = frame_rejection(source)
                if reason:
                    reasons[reason] += 1
                    continue
                values = metrics(positions)
                frames.append({'source_frame': source['source_frame'],
                               'source_second': source['source_second'],
                               'anonymous_box_positions_m': positions,
                               'provisional_metrics': {name: round(values[name], 3) for name in NAMES}})
        else:
            reasons['anchor_after_point_unverified_core_phase'] = len(point['rows'])
        medians = {name: (round(statistics.median(f['provisional_metrics'][name] for f in frames), 3)
                          if frames else None) for name in NAMES}
        rows.append({'set': key[0], 'point_number': key[1], 'near_team': near,
                     'near_team_won': near == winner, 'clip_start_frame': clip['clip_start_frame_inclusive'],
                     'clip_end_frame_exclusive': clip['clip_end_frame_exclusive'],
                     'anchor_phase': local_phase, 'sampled_core_frames': len(point['rows']),
                     'provisional_candidate_frames': len(frames),
                     'candidate_fraction_of_sampled_core': round(len(frames) / len(point['rows']), 3),
                     'rejection_counts': dict(reasons), 'provisional_core_medians': medians,
                     'frames': frames})
    groups = []
    for set_no in (1, 2, 3):
        for won in (True, False):
            cohort = [r for r in rows if r['set'] == set_no and r['near_team_won'] == won]
            available = [r for r in cohort if r['provisional_candidate_frames']]
            groups.append({'set': set_no, 'near_team_won': won, 'selected_points': len(cohort),
                           'points_with_provisional_core_median': len(available),
                           'median_of_point_core_medians': {
                               name: (round(statistics.median(r['provisional_core_medians'][name] for r in available), 3)
                                      if available else None) for name in NAMES}})
    result = {
        'status': 'exploratory_anonymous_box_geometry_not_validated_rally_metrics',
        'source_sha256': tracks['source_sha256'],
        'dense_tracks_sha256': digest(TRACKS), 'cut_register_sha256': digest(CUTS),
        'phase_qc_sha256': digest(PHASE), 'frozen_sample_sha256': digest(SAMPLE),
        'rule': 'For locally live-anchor points only, summarize 5 Hz coarse-core frames with exactly six geometric near-floor candidates, no unresolved net-boundary box, no box outside 0-9 m, and no pair of boxes with IoU >0.5; median per point. This is a detector availability screen, not a final six-person source review.',
        'summary': {'frozen_points': len(rows),
                    'points_with_provisional_core_median': sum(r['provisional_candidate_frames'] > 0 for r in rows),
                    'provisional_candidate_frames': sum(r['provisional_candidate_frames'] for r in rows),
                    'sampled_core_frames': sum(r['sampled_core_frames'] for r in rows),
                    'validated_metric_frames': 0, 'validated_rally_summaries': 0},
        'groups': groups, 'points': rows,
        'limitations': [
            'The coarse core boundaries are visually screened at one-second resolution, not exact live-ball intervals.',
            'Candidate frames may include a far player, a duplicate or an airborne player despite geometric filters.',
            'A single reviewed live anchor does not certify all other sampled core frames as live.',
            'The court homography and box-bottom ground proxy have not passed independent player-floor validation.',
            'Availability-selected candidate frames bias the per-point median and outcome groups.',
            'Raw tracker IDs are intentionally unused in the symmetric static formulas, but are still needed for movement, rotation and transition analyses.'
        ]}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])
    for group in groups:
        print(group['set'], group['near_team_won'], group['points_with_provisional_core_median'])


if __name__ == '__main__':
    main()
