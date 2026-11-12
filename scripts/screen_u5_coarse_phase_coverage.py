"""Measure detector availability inside the source-still phase brackets.

This is a navigation screen only. Frames inside a coarse bracket are not
individually source-adjudicated and cannot be promoted to final metrics.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
CANDIDATES = BASE / 'cut_bounded_provisional_rally_metrics.json'
BRACKETS = BASE / 'coarse_phase_brackets.json'
COUNTEREXAMPLES = BASE / 'provisional_core_phase_counterexamples.json'
DENSE = BASE / 'dense_live_track_screen.json'
OUT = BASE / 'coarse_phase_candidate_coverage.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidate = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    brackets = json.loads(BRACKETS.read_text(encoding='utf-8'))
    audit = json.loads(COUNTEREXAMPLES.read_text(encoding='utf-8'))
    dense = json.loads(DENSE.read_text(encoding='utf-8'))
    if not candidate['source_sha256'] == brackets['source_sha256'] == audit['source_sha256'] == dense['source_sha256']:
        raise ValueError('Different source videos')
    if candidate['dense_tracks_sha256'] != digest(DENSE):
        raise ValueError('Candidate screen differs from dense tracker')
    if audit['candidate_screen_sha256'] != digest(CANDIDATES):
        raise ValueError('Counterexample audit differs from candidate screen')
    by_key = {(r['set'], r['point_number']): r for r in brackets['points']}
    dense_by_key = {(r['set'], r['point_number']): r for r in dense['points']}
    if len(by_key) != 18:
        raise ValueError('Expected 18 coarse brackets')
    rows = []
    retained_ids = set()
    for point in candidate['points']:
        key = point['set'], point['point_number']
        bracket = by_key[key]
        first = bracket['first_obvious_active_frame']
        last = bracket['last_obvious_active_frame']
        frames = [r['source_frame'] for r in point['frames']
                  if first is not None and first - 1 <= r['source_frame'] <= last + 1]
        dense_in_bracket = [r for r in dense_by_key[key]['rows']
                            if first - 1 <= r['source_frame'] <= last + 1]
        geometric_six = sum(len([p for p in r['proposals'] if
                                 p['net_side_status'] == 'near_floor_side_candidate']) == 6
                            for r in dense_in_bracket)
        retained_ids.update((key[0], key[1], f) for f in frames)
        rows.append({'set': key[0], 'point_number': key[1],
                     'clip_candidate_frames': point['provisional_candidate_frames'],
                     'within_coarse_bracket_candidate_frames': len(frames),
                     'dense_sampled_frames_in_bracket': len(dense_in_bracket),
                     'dense_exact_six_geometric_frames_in_bracket': geometric_six,
                     'coarse_bracket_first_frame': first,
                     'coarse_bracket_last_frame': last})
    counterexample_ids = {(r['set'], r['point_number'], r['source_frame'])
                          for r in audit['counterexamples']}
    if retained_ids & counterexample_ids:
        raise ValueError('Confirmed non-live frame survived the coarse phase bracket')
    result = {
        'status': 'coarse_source_still_bracket_detector_availability_not_live_frame_validation',
        'source_sha256': candidate['source_sha256'],
        'candidate_screen_sha256': digest(CANDIDATES),
        'coarse_brackets_sha256': digest(BRACKETS),
        'counterexample_audit_sha256': digest(COUNTEREXAMPLES),
        'summary': {'frozen_points': len(rows),
                    'clip_candidate_frames': sum(r['clip_candidate_frames'] for r in rows),
                    'within_coarse_bracket_candidate_frames': len(retained_ids),
                    'points_with_bracketed_candidates': sum(r['within_coarse_bracket_candidate_frames'] > 0 for r in rows),
                    'short_clip_dense_exact_six_frames': sum(r['dense_exact_six_geometric_frames_in_bracket'] for r in rows
                                                             if (r['set'], r['point_number']) in ((2, 14), (3, 23))),
                    'confirmed_non_live_frames_excluded': len(counterexample_ids),
                    'validated_metric_frames': 0},
        'rule': 'Keep a geometric six-box candidate only between source-still active-looking marks, allowing one source-frame tolerance for the non-integer clip start. The two short clips have 5 Hz phase brackets but no candidate from the old live-anchor-gated screen, so their dense raw geometric-six availability is reported separately. This is a conservative screen, not an individually reviewed live interval.',
        'points': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
