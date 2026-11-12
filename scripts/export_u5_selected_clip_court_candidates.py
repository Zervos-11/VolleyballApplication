"""Export sampled court candidates with explicit gaps across 18 edited point clips."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
FILES = {
    'clips': BASE / 'rally_cut_clip_register.json',
    'sample': BASE / 'rally_sample_score_only.json',
    'dense': BASE / 'dense_live_track_screen.json',
    'continuity': BASE / 'dense_live_continuity_audit.json',
    'calibration': BASE / 'near_court_candidate.json',
}
OUT = BASE / 'selected_clip_court_candidate_coverage.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_SELECTED_CLIP_COURT_COVERAGE.md'
FRAME_STEP = 6


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grid(start, end):
    """Five-Hz sample instants within an edited clip, end exclusive."""
    first = ((start + FRAME_STEP - 1) // FRAME_STEP) * FRAME_STEP
    return range(first, end, FRAME_STEP)


def classify(source_row):
    if source_row is None:
        return 'not_screened'
    count = source_row['near_floor_side_candidate_count']
    if count < 6:
        return 'fewer_than_six_candidates'
    if count == 6:
        return 'exactly_six_candidates_unvalidated'
    return 'more_than_six_candidates_ambiguous'


def main():
    data = {name: json.loads(path.read_text(encoding='utf-8'))
            for name, path in FILES.items()}
    source = data['sample']['source_sha256']
    assert source == data['clips']['source_sha256'] == data['dense']['source_sha256']
    assert data['clips']['frozen_sample_sha256'] == sha(FILES['sample'])
    assert data['continuity']['dense_track_screen_sha256'] == sha(FILES['dense'])
    assert data['continuity']['frozen_sample_sha256'] == sha(FILES['sample'])
    assert data['dense']['calibration_sha256'] == sha(FILES['calibration'])
    assert data['dense']['frame_step'] == FRAME_STEP
    clip_rows = {(r['set'], r['point_number']): r for r in data['clips']['selected_clips']}
    dense_rows = {(r['set'], r['point_number']): r for r in data['dense']['points']}
    continuity_rows = {(r['set'], r['point_number']): r for r in data['continuity']['points']}
    sample_rows = {(r['set'], r['point_number']): r for r in data['sample']['selected_events']}
    assert len(clip_rows) == len(dense_rows) == len(continuity_rows) == len(sample_rows) == 18
    assert set(clip_rows) == set(dense_rows) == set(continuity_rows) == set(sample_rows)
    points = []
    total = {'edited_source_frames': 0, 'five_hz_grid_frames': 0,
             'not_screened': 0, 'fewer_than_six_candidates': 0,
             'exactly_six_candidates_unvalidated': 0,
             'more_than_six_candidates_ambiguous': 0}
    for key in sorted(clip_rows):
        clip = clip_rows[key]
        dense = dense_rows[key]
        continuity = continuity_rows[key]
        assert clip['clip_start_frame_inclusive'] < clip['clip_end_frame_exclusive']
        assert continuity['sampled_frames'] == dense['frames'] == len(dense['rows'])
        frame_rows = {row['source_frame']: row for row in dense['rows']}
        assert len(frame_rows) == len(dense['rows'])
        instants = []
        for frame_number in grid(clip['clip_start_frame_inclusive'],
                                 clip['clip_end_frame_exclusive']):
            source_row = frame_rows.get(frame_number)
            status = classify(source_row)
            item = {'source_frame': frame_number, 'status': status}
            if source_row is not None:
                proposals = [p for p in source_row['proposals'] if
                             p['net_side_status'] == 'near_floor_side_candidate']
                assert len(proposals) == source_row['near_floor_side_candidate_count']
                item['near_floor_side_candidate_count'] = len(proposals)
                item['court_candidates'] = [
                    {'raw_track_id': p['raw_track_id'],
                     'court_m': p['box_bottom_court_m'],
                     'detector_confidence': p['confidence']}
                    for p in proposals]
            instants.append(item)
            total[status] += 1
        assert len(set(frame_rows) - {r['source_frame'] for r in instants}) == 0
        count = {status: sum(r['status'] == status for r in instants)
                 for status in ('not_screened', 'fewer_than_six_candidates',
                                'exactly_six_candidates_unvalidated',
                                'more_than_six_candidates_ambiguous')}
        source_frames = clip['clip_end_frame_exclusive'] - clip['clip_start_frame_inclusive']
        total['edited_source_frames'] += source_frames
        total['five_hz_grid_frames'] += len(instants)
        points.append({'set': key[0], 'point_number': key[1],
                       'near_team': continuity['near_team'],
                       'near_team_won': continuity['near_team_won'],
                       'edited_clip_start_frame': clip['clip_start_frame_inclusive'],
                       'edited_clip_end_frame_exclusive': clip['clip_end_frame_exclusive'],
                       'edited_source_frames': source_frames,
                       'five_hz_grid_frames': len(instants),
                       'status_counts': count,
                       'instants': instants})
    assert sum(total[name] for name in ('not_screened', 'fewer_than_six_candidates',
                                       'exactly_six_candidates_unvalidated',
                                       'more_than_six_candidates_ambiguous')) == total['five_hz_grid_frames']
    assert total['edited_source_frames'] == 6030
    assert total['five_hz_grid_frames'] == 1005
    assert total['not_screened'] == 370
    assert total['fewer_than_six_candidates'] == 421
    assert total['exactly_six_candidates_unvalidated'] == 206
    assert total['more_than_six_candidates_ambiguous'] == 8
    out = {'status': 'selected_edited_clip_court_candidates_not_validated_player_trajectories',
           'source_sha256': source,
           'input_sha256': {name: sha(path) for name, path in FILES.items()},
           'method': {'clip_bounds': 'score-aligned hard edits, not exact live-play boundaries',
                      'grid': 'every sixth source frame at 30 fps, inside each edited clip',
                      'positions': 'existing near-floor-side raw detector box-bottom court candidates',
                      'missingness': 'unscreened frames explicit; fewer than six not filled; more than six ambiguous',
                      'identity_status': 'raw IDs and side candidates are not independently source-validated for every instant'},
           'summary': {'selected_points': len(points), **total,
                       'screened_grid_frames': total['five_hz_grid_frames'] - total['not_screened'],
                       'strict_validated_six_player_metric_frames': 0},
           'points': points,
           'interpretation': ('This is a full edited-clip coverage register for the 18 frozen points. '
                              'It exports candidate court positions where the dense screen sampled '
                              'a frame and makes unscreened and incomplete frames explicit. '
                              'It does not infer missing players, select a six-person roster from '
                              'ambiguous proposals, certify live-play phase, or validate full-rally '
                              'trajectories or outcome metrics.')}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Court-candidate coverage across the 18 selected edited clips', '',
             'The [source-bound export](../data/matches/yt_u5HnY2aNW14/screening/'
             'selected_clip_court_candidate_coverage.json) joins the frozen score-only '
             'sample, score-aligned hard-edit clip boundaries and existing dense 5 Hz '
             'detector screen. It lists every sixth source frame **inside each edited '
             'clip**, including frames not screened by the dense pass. The edit bounds '
             'are not exact serve or point-end times. This is the earlier core-only '
             'screen; the later [full-clip tracklet pass](HONOURS_U5_FULL_CLIP_TRACKLET_AUDIT.md) '
             'screens all 1,005 grid instants with a new point-local tracker start, '
             'so its raw IDs and candidate totals are separate diagnostics.', '',
             '| Coverage state | 5 Hz instants | Meaning |',
             '| --- | ---: | --- |',
             f"| Not screened | {total['not_screened']} | No detector positions in the saved dense core |",
             f"| Fewer than six near-side candidates | {total['fewer_than_six_candidates']} | Partial raw proposals; no player filled in |",
             f"| Exactly six candidates | {total['exactly_six_candidates_unvalidated']} | Six raw box-bottom court points; identity and grounded status unvalidated |",
             f"| More than six candidates | {total['more_than_six_candidates_ambiguous']} | Ambiguous selection; no six-person subset chosen |",
             f"| **Total** | **{total['five_hz_grid_frames']}** | Across {len(points)} edited clips and {total['edited_source_frames']} source frames |",
             '', '| Set | Point | Near team won | 5 Hz instants | Not screened | <6 | Exactly 6 | >6 |',
             '| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for row in points:
        counts = row['status_counts']
        lines.append(f"| {row['set']} | {row['point_number']} | "
                     f"{'Yes' if row['near_team_won'] else 'No'} | "
                     f"{row['five_hz_grid_frames']} | {counts['not_screened']} | "
                     f"{counts['fewer_than_six_candidates']} | "
                     f"{counts['exactly_six_candidates_unvalidated']} | "
                     f"{counts['more_than_six_candidates_ambiguous']} |")
    lines += ['', 'The 206 exactly-six instants are **candidate court-coordinate data**, '
              'not six validated player positions. Raw track IDs can transfer, a box '
              'bottom can move away from the floor during a jump, and the clip includes '
              'pre- and post-play frames. The existing [eight-window fixed-box pilot]'
              '(HONOURS_U5_FIXED_BOX_COURT_PROXY.md) is the smaller source-screened '
              'analysis used for exploratory metrics. This full-clip register preserves '
              'missingness for all 18 selected points and cannot be used to infer a '
              'winner effect by treating candidate frames as reviewed rallies.', '',
              'Reproduce with `python scripts/export_u5_selected_clip_court_candidates.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(out['summary'])


if __name__ == '__main__':
    main()
