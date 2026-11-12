"""Compare full-clip raw box bottoms with existing manual shoes at one in-run frame."""

import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'full_clip_track_screen.json'
IDENTITY = BASE / 'full_run_identity_audit.json'
MANUAL = BASE / 'dynamic_shoe_reference_audit.json'
OUT = BASE / 'full_run_position_reference.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FULL_RUN_POSITION_REFERENCE.md'
FRAME = 36084


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    identity = json.loads(IDENTITY.read_text(encoding='utf-8'))
    manual = json.loads(MANUAL.read_text(encoding='utf-8'))
    assert screen['source_sha256'] == identity['source_sha256'] == manual['source_sha256']
    assert identity['input_sha256']['full_clip_screen'] == sha(SCREEN)
    point = next(p for p in screen['points'] if (p['set'], p['point_number']) == (3, 34))
    frame = next(r for r in point['rows'] if r['source_frame'] == FRAME)
    reviewed = next(r for r in identity['rows'] if (r['set'], r['point_number']) == (3, 34))
    assert FRAME in reviewed['sampled_source_frames']
    manual_rows = [r for r in manual['rows']
                   if (r['set'], r['point_number'], r['source_frame']) == (3, 34, FRAME)
                   and r['status'] == 'approximate_clear_pair']
    assert len(manual_rows) == 2
    jersey = {p['raw_track_id']: p['reviewed_visible_jersey_number']
              for p in reviewed['players']}
    proposals = [p for p in frame['proposals']
                 if p['raw_track_id'] in jersey and
                 p['net_side_status'] == 'near_floor_side_candidate']
    assert len(proposals) == 6
    rows = []
    used = set()
    for mark in manual_rows:
        def pixel_distance(p):
            x1, _, x2, y2 = p['bbox_px']
            return math.dist([(x1 + x2) / 2, y2], mark['manual_shoe_midpoint_px'])
        closest = min(proposals, key=pixel_distance)
        assert pixel_distance(closest) < 45
        assert closest['raw_track_id'] not in used
        used.add(closest['raw_track_id'])
        court_error = math.dist(closest['box_bottom_court_m'],
                                mark['manual_shoe_midpoint_court_m'])
        rows.append({'source_frame': FRAME,
                     'raw_track_id': closest['raw_track_id'],
                     'visually_reviewed_jersey_number': jersey[closest['raw_track_id']],
                     'existing_manual_player_key': mark['player_key'],
                     'manual_shoe_midpoint_px': mark['manual_shoe_midpoint_px'],
                     'manual_shoe_midpoint_court_m': mark['manual_shoe_midpoint_court_m'],
                     'current_box_bottom_court_m': closest['box_bottom_court_m'],
                     'current_box_to_manual_shoe_error_m': round(court_error, 3),
                     'current_box_to_manual_shoe_distance_px': round(pixel_distance(closest), 3),
                     'earlier_fixed_box_proxy_error_m': mark['court_position_error_m']})
    rows.sort(key=lambda r: r['raw_track_id'])
    out = {'status': 'two_existing_manual_clear_shoes_one_in_run_frame_not_trajectory_validation',
           'source_sha256': screen['source_sha256'],
           'input_sha256': {'full_clip_screen': sha(SCREEN),
                            'every_sample_identity_audit': sha(IDENTITY),
                            'existing_manual_reference': sha(MANUAL)},
           'set': 3, 'point_number': 34, 'source_frame': FRAME,
           'summary': {'clear_grounded_manual_pairs': 2,
                       'median_current_box_to_shoe_error_m': round(statistics.median(
                           r['current_box_to_manual_shoe_error_m'] for r in rows), 3),
                       'maximum_current_box_to_shoe_error_m': max(
                           r['current_box_to_manual_shoe_error_m'] for r in rows),
                       'validated_full_run_court_trajectories': 0},
           'rows': rows,
           'limitations': ['The two shoe marks are reused from the existing single-reviewer reference.',
                           'Only two clear grounded players in one sampled frame are compared.',
                           'No inference about all six players or other frames is supported.']}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Direct in-run position reference', '',
             'The [source-bound result](../data/matches/yt_u5HnY2aNW14/screening/full_run_position_reference.json) '
             'joins two existing clear-grounded manual shoe midpoints at S3 P34 '
             'source frame 36084 to the new full-clip raw-ID boxes. The nearest box '
             'match is unique within 45 image pixels and its jersey is confirmed in '
             'the [every-sample identity review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md). '
             'These are reused single-reviewer marks, not new independent labels.', '',
             '| Jersey | Raw ID | Current box to manual shoe | Earlier fixed-box proxy error |',
             '| --- | ---: | ---: | ---: |']
    for row in rows:
        lines.append(f"| #{row['visually_reviewed_jersey_number']} | "
                     f"{row['raw_track_id']} | "
                     f"{row['current_box_to_manual_shoe_error_m']:.3f} m | "
                     f"{row['earlier_fixed_box_proxy_error_m']:.3f} m |")
    lines += ['', f"The two current box-bottom errors have median "
              f"**{out['summary']['median_current_box_to_shoe_error_m']:.3f} m** "
              f"and maximum **{out['summary']['maximum_current_box_to_shoe_error_m']:.3f} m**. "
              'The earlier fixed-box numbers come from a different proxy method; '
              'their change is not a controlled accuracy improvement. Four teammates '
              'at this frame and every other frame in these runs lack a joined manual '
              'shoe check. This does not validate a full-rally court trajectory.', '',
              'Reproduce with `python scripts/audit_u5_full_run_position_reference.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(out['summary'])


if __name__ == '__main__':
    main()
