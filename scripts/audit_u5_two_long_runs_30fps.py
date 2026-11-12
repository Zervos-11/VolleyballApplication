"""Audit dense raw-ID coverage against the reviewed 5 Hz jersey anchors."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
DENSE = BASE / 'two_long_runs_30fps_screen.json'
FIVE_HZ = BASE / 'full_clip_track_screen.json'
IDENTITY = BASE / 'full_run_identity_audit.json'
GAP_QC = BASE / 'two_long_runs_30fps_gap_qc.json'
GAP_IMAGES = BASE / 'full_clip_run_spotcheck/s3_p34_30fps_missing_manifest.json'
OUT = BASE / 'two_long_runs_30fps_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_TWO_RUNS_30FPS_AUDIT.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (area_a + area_b - intersection)


def intervals(numbers):
    spans = []
    for number in numbers:
        if spans and number == spans[-1][-1] + 1:
            spans[-1][-1] = number
        else:
            spans.append([number, number])
    return spans


def main():
    dense = json.loads(DENSE.read_text(encoding='utf-8'))
    five = json.loads(FIVE_HZ.read_text(encoding='utf-8'))
    identity = json.loads(IDENTITY.read_text(encoding='utf-8'))
    gap_qc = json.loads(GAP_QC.read_text(encoding='utf-8'))
    gap_images = json.loads(GAP_IMAGES.read_text(encoding='utf-8'))
    assert dense['source_sha256'] == five['source_sha256'] == identity['source_sha256']
    assert identity['input_sha256']['full_clip_screen'] == sha(FIVE_HZ)
    assert gap_images['dense_screen_sha256'] == sha(DENSE)
    assert gap_images['source_sha256'] == dense['source_sha256']
    for sheet in gap_images['sheets']:
        assert sha(ROOT / 'data/matches/yt_u5HnY2aNW14' / sheet['image']) == sheet['image_sha256']
    by_five = {(p['set'], p['point_number']): p for p in five['points']}
    by_review = {(p['set'], p['point_number']): p for p in identity['rows']}
    rows = []
    for point in dense['points']:
        key = point['set'], point['point_number']
        reviewed = by_review[key]
        first = point['rows'][0]
        five_first = next(r for r in by_five[key]['rows']
                          if r['source_frame'] == first['source_frame'])
        dense_proposals = [p for p in first['proposals']
                           if p['net_side_status'] == 'near_floor_side_candidate']
        five_proposals = [p for p in five_first['proposals']
                          if p['net_side_status'] == 'near_floor_side_candidate']
        assert len(dense_proposals) == len(five_proposals) == 6
        jersey_by_five_id = {p['raw_track_id']: p['reviewed_visible_jersey_number']
                             for p in reviewed['players']}
        mapping = {}
        for candidate in dense_proposals:
            matched = max(five_proposals,
                          key=lambda p: iou(candidate['bbox_px'], p['bbox_px']))
            overlap = iou(candidate['bbox_px'], matched['bbox_px'])
            assert overlap > .5
            mapping[candidate['raw_track_id']] = {'five_hz_raw_track_id': matched['raw_track_id'],
                                                  'reviewed_jersey_number': jersey_by_five_id[matched['raw_track_id']],
                                                  'first_frame_box_iou': round(overlap, 3)}
        assert len(mapping) == 6
        assert len({v['five_hz_raw_track_id'] for v in mapping.values()}) == 6
        expected = set(mapping)
        seen = Counter()
        missing = {raw_id: [] for raw_id in expected}
        six_frames = 0
        for frame in point['rows']:
            ids = [p['raw_track_id'] for p in frame['proposals']
                   if p['net_side_status'] == 'near_floor_side_candidate']
            assert len(ids) == len(set(ids)) and set(ids) <= expected
            seen.update(ids)
            six_frames += len(ids) == 6
            for raw_id in expected - set(ids):
                missing[raw_id].append(frame['source_frame'])
        players = [{'dense_raw_track_id': raw_id, **mapping[raw_id],
                    'source_frames_with_near_candidate': seen[raw_id],
                    'missing_frame_intervals': intervals(missing[raw_id])}
                   for raw_id in sorted(expected)]
        rows.append({'set': key[0], 'point_number': key[1],
                     'source_frame_first': first['source_frame'],
                     'source_frame_last': point['rows'][-1]['source_frame'],
                     'source_frames_screened': len(point['rows']),
                     'exactly_six_near_candidate_frames': six_frames,
                     'frames_with_fewer_than_six_candidates': len(point['rows']) - six_frames,
                     'new_near_raw_ids_after_first_frame': 0,
                     'players': players})
    assert [(r['set'], r['point_number'], r['source_frames_screened'],
             r['exactly_six_near_candidate_frames']) for r in rows] == [
                 (1, 5, 103, 103), (3, 34, 103, 93)]
    assert (gap_qc['set'], gap_qc['point_number']) == (3, 34)
    gap_rows = {r['source_frame']: r for r in gap_qc['rows']}
    expected_gaps = sorted(frame for player in rows[1]['players']
                           for start, end in player['missing_frame_intervals']
                           for frame in range(start, end + 1))
    assert sorted(gap_rows) == expected_gaps
    assert sorted(frame for sheet in gap_images['sheets'] for frame in sheet['frames']) == expected_gaps
    for player in rows[1]['players']:
        for start, end in player['missing_frame_intervals']:
            for frame in range(start, end + 1):
                assert gap_rows[frame]['missing_reviewed_jersey_number'] == player['reviewed_jersey_number']
                assert gap_rows[frame]['source_visibility'] == 'visible_near_team_unboxed'
    out = {'status': 'dense_raw_id_coverage_audit_not_all_frame_jersey_or_floor_validation',
           'source_sha256': dense['source_sha256'],
           'input_sha256': {'dense_screen': sha(DENSE), 'five_hz_screen': sha(FIVE_HZ),
                            'every_sample_identity_audit': sha(IDENTITY),
                            'manual_gap_qc': sha(GAP_QC), 'gap_image_manifest': sha(GAP_IMAGES)},
           'summary': {'runs_screened': 2, 'source_frames_screened': 206,
                       'exactly_six_near_candidate_frames': 196,
                       'frames_with_temporary_missing_candidate': 10,
                       'source_visible_unboxed_missing_frames_reviewed': 10,
                       'new_near_raw_ids_after_first_frame': 0,
                       'all_source_frames_jersey_reviewed': 0,
                       'validated_full_rally_court_trajectories': 0},
           'rows': rows}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Thirty-frame-per-second screen of two long candidate runs', '',
             'The [source-bound dense audit](../data/matches/yt_u5HnY2aNW14/screening/two_long_runs_30fps_audit.json) '
             'reruns YOLOv8n and ByteTrack at every decoded source frame inside the '
             'two longest 5 Hz candidate spans. It independently resets tracking at '
             'each span and maps its first-frame raw IDs to the [reviewed 5 Hz jerseys]'
             '(HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) by unique box overlap above 0.5. '
             'The dense pass is an algorithmic continuity screen, not a human jersey '
             'check of every 30 fps frame.', '',
             '| Point | Source frames | Exactly six near-side candidates | Temporary missing frames | New raw IDs |',
             '| --- | ---: | ---: | ---: | ---: |']
    for row in rows:
        lines.append(f"| S{row['set']} P{row['point_number']} | "
                     f"{row['source_frames_screened']} | "
                     f"{row['exactly_six_near_candidate_frames']} | "
                     f"{row['frames_with_fewer_than_six_candidates']} | 0 |")
    lines += ['', '| S3 P34 jersey | Dense ID | Frames present | Missing source frames |',
              '| --- | ---: | ---: | --- |']
    for player in rows[1]['players']:
        gaps = ', '.join(f"{a}–{b}" if a != b else str(a)
                         for a, b in player['missing_frame_intervals']) or 'None'
        lines.append(f"| #{player['reviewed_jersey_number']} | "
                     f"{player['dense_raw_track_id']} | "
                     f"{player['source_frames_with_near_candidate']}/103 | {gaps} |")
    lines += ['', 'S1 P5 retains the same six raw IDs in all 103 decoded frames. '
              'S3 P34 retains the same six ID values when present, but #7 is missing '
              'for four frames and #21 for six frames. The missing states are explicit; '
              'no position is held still or interpolated. A [source-image check of all ten '
              'missing frames](../data/matches/yt_u5HnY2aNW14/screening/two_long_runs_30fps_gap_qc.json) '
              'finds the missing teammate visible but unboxed in each image; the '
              '[first five-frame sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_30fps_missing_1.png) '
              'and [second sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_30fps_missing_2.png) '
              'show the source evidence. Some players are adjacent; the precise '
              'detector-versus-tracker cause is not adjudicated. The every-sample 5 Hz crop '
              'review found stable jerseys at 18 anchor frames in each run, but the '
              'dense pass does not certify jersey identity in every inter-sample frame. '
              'The [manual position comparison](HONOURS_U5_FULL_RUN_POSITION_REFERENCE.md) '
              'has only two clear shoes at one source frame. Neither run is a validated '
              'full-rally grounded trajectory.', '',
              'Reproduce with `python scripts/screen_u5_two_long_runs_30fps.py` and '
              '`python scripts/audit_u5_two_long_runs_30fps.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(out['summary'])


if __name__ == '__main__':
    main()
