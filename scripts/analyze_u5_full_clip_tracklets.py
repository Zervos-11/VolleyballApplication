"""Measure point-local raw track segments without filling missing player positions."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'full_clip_track_screen.json'
SAMPLE = BASE / 'rally_sample_score_only.json'
OUT = BASE / 'full_clip_tracklet_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FULL_CLIP_TRACKLET_AUDIT.md'
STEP = 6


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def six_id_key(row):
    near = [p for p in row['proposals'] if
            p['net_side_status'] == 'near_floor_side_candidate']
    ids = [p['raw_track_id'] for p in near]
    if len(ids) != 6 or None in ids or len(set(ids)) != 6:
        return None
    return tuple(sorted(ids))


def longest_six_run(rows, core_only=False):
    best = {'sampled_frames': 0, 'first_frame': None, 'last_frame': None,
            'raw_track_ids': []}
    active = None
    for row in rows:
        key = six_id_key(row) if not core_only or row['in_conservative_core'] else None
        if key is None:
            active = None
            continue
        if (active is not None and active['raw_track_ids'] == list(key)
                and row['source_frame'] == active['last_frame'] + STEP):
            active['sampled_frames'] += 1
            active['last_frame'] = row['source_frame']
        else:
            active = {'sampled_frames': 1, 'first_frame': row['source_frame'],
                      'last_frame': row['source_frame'], 'raw_track_ids': list(key)}
        if active['sampled_frames'] > best['sampled_frames']:
            best = dict(active)
    return best


def tracklets(rows):
    """Split every raw ID at a missing sample; never join across a gap."""
    active = {}
    finished = []
    for row in rows:
        frame = row['source_frame']
        near = [p for p in row['proposals'] if
                p['net_side_status'] == 'near_floor_side_candidate'
                and p['raw_track_id'] is not None]
        ids = [p['raw_track_id'] for p in near]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate raw track ID at frame {frame}')
        current = set(ids)
        for raw_id in list(active):
            if raw_id not in current:
                finished.append(active.pop(raw_id))
        for p in near:
            raw_id = p['raw_track_id']
            item = {'source_frame': frame,
                    'court_m': p['box_bottom_court_m'],
                    'in_conservative_core': row['in_conservative_core']}
            if raw_id not in active or frame != active[raw_id]['last_frame'] + STEP:
                if raw_id in active:
                    finished.append(active.pop(raw_id))
                active[raw_id] = {'raw_track_id': raw_id,
                                  'first_frame': frame, 'last_frame': frame,
                                  'observations': [item]}
            else:
                active[raw_id]['last_frame'] = frame
                active[raw_id]['observations'].append(item)
    finished.extend(active.values())
    finished.sort(key=lambda t: (t['first_frame'], t['raw_track_id']))
    for t in finished:
        t['sampled_frames'] = len(t['observations'])
        assert t['last_frame'] - t['first_frame'] == STEP * (t['sampled_frames'] - 1)
    return finished


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    assert screen['source_sha256'] == sample['source_sha256']
    assert screen['sample_sha256'] == sha(SAMPLE)
    assert screen['frame_step'] == STEP
    assert len(screen['points']) == len(sample['selected_events']) == 18
    selected = {(r['set'], r['point_number']): r for r in sample['selected_events']}
    points = []
    for point in screen['points']:
        key = point['set'], point['point_number']
        assert key in selected
        rows = point['rows']
        assert len(rows) == len(range(((point['clip_start_frame'] + STEP - 1) // STEP) * STEP,
                                      point['clip_end_frame_exclusive'], STEP))
        segments = tracklets(rows)
        full_run = longest_six_run(rows)
        core_run = longest_six_run(rows, core_only=True)
        near_team = 'UCLA' if key[0] in (1, 3) else 'Concordia'
        winner = 'UCLA' if selected[key]['winner_scoreboard_side'] == 'left' else 'Concordia'
        points.append({'set': key[0], 'point_number': key[1],
                       'near_team': near_team, 'near_team_won': winner == near_team,
                       'clip_start_frame': point['clip_start_frame'],
                       'clip_end_frame_exclusive': point['clip_end_frame_exclusive'],
                       'sampled_frames': len(rows),
                       'exactly_six_near_candidate_frames': sum(
                           r['near_floor_side_candidate_count'] == 6 for r in rows),
                       'exactly_six_in_conservative_core': sum(
                           r['in_conservative_core'] and r['near_floor_side_candidate_count'] == 6
                           for r in rows),
                       'longest_same_six_raw_id_run_full_clip': full_run,
                       'longest_same_six_raw_id_run_core': core_run,
                       'raw_tracklet_count': len(segments),
                       'raw_tracklets_at_least_five_samples': sum(
                           t['sampled_frames'] >= 5 for t in segments),
                       'tracklets': segments})
    assert len({(p['set'], p['point_number']) for p in points}) == 18
    all_tracks = [t for p in points for t in p['tracklets']]
    by_outcome = []
    for won in (True, False):
        subset = [p for p in points if p['near_team_won'] == won]
        by_outcome.append({'near_team_won': won, 'clips': len(subset),
                           'sampled_frames': sum(p['sampled_frames'] for p in subset),
                           'exactly_six_near_candidate_frames': sum(
                               p['exactly_six_near_candidate_frames'] for p in subset),
                           'clips_with_five_sample_same_six_run_core': sum(
                               p['longest_same_six_raw_id_run_core']['sampled_frames'] >= 5
                               for p in subset)})
    summary = {'selected_clips': 18, 'sampled_frames': sum(p['sampled_frames'] for p in points),
               'exactly_six_near_candidate_frames': sum(
                   p['exactly_six_near_candidate_frames'] for p in points),
               'raw_tracklet_segments': len(all_tracks),
               'raw_tracklet_segments_at_least_five_samples': sum(
                   t['sampled_frames'] >= 5 for t in all_tracks),
               'clips_with_five_sample_same_six_run_full': sum(
                   p['longest_same_six_raw_id_run_full_clip']['sampled_frames'] >= 5
                   for p in points),
               'clips_with_five_sample_same_six_run_core': sum(
                   p['longest_same_six_raw_id_run_core']['sampled_frames'] >= 5
                   for p in points),
               'validated_full_rally_team_trajectories': 0}
    assert summary['sampled_frames'] == screen['summary']['sampled_frames'] == 1005
    assert summary['exactly_six_near_candidate_frames'] == screen['summary']['exactly_six_near_candidates']
    out = {'status': 'full_edited_clip_raw_tracklets_not_named_player_trajectories',
           'source_sha256': screen['source_sha256'],
           'input_sha256': {'full_clip_screen': sha(SCREEN), 'frozen_sample': sha(SAMPLE)},
           'method': 'Point-local raw IDs split into contiguous five-Hz segments at every missing sample; '
                     'six-ID runs require exactly six distinct near-side candidate IDs at each sample.',
           'summary': summary, 'by_outcome': by_outcome, 'points': points,
           'limitations': ['Raw IDs can switch or attach to a wrong-team player.',
                           'A raw tracklet is a candidate box-bottom path, not a named grounded player path.',
                           'Edited clips include setup and aftermath; coarse core boundaries are not exact live-play boundaries.',
                           'Gaps are never joined or filled.']}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Full selected-clip raw tracklet audit', '',
             'The [source-bound JSON](../data/matches/yt_u5HnY2aNW14/screening/'
             'full_clip_tracklet_audit.json) segments point-local ByteTrack raw IDs '
             'across all 18 selected edited clips at 5 Hz. Each ID is split whenever '
             'it is missing at a sampled frame; gaps are not interpolated. A six-ID '
             'run requires exactly six distinct near-side geometric candidates at '
             'each consecutive sample.', '',
             f"The full pass has **{summary['sampled_frames']}** sampled clip frames and "
             f"**{summary['exactly_six_near_candidate_frames']}** exactly-six candidate "
             f"frames. It yields **{summary['raw_tracklet_segments']}** contiguous raw "
             f"tracklet segments, of which **{summary['raw_tracklet_segments_at_least_five_samples']}** "
             'last at least five samples. The longest same-six-ID run is a candidate '
             'continuity diagnostic, not source-reviewed named-player identity.', '',
             '| Set | Point | Near win | Full clip samples | Exactly six | Longest six-ID run, full clip | Longest six-ID run, coarse core |',
             '| ---: | ---: | --- | ---: | ---: | ---: | ---: |']
    for p in points:
        lines.append(f"| {p['set']} | {p['point_number']} | "
                     f"{'Yes' if p['near_team_won'] else 'No'} | {p['sampled_frames']} | "
                     f"{p['exactly_six_near_candidate_frames']} | "
                     f"{p['longest_same_six_raw_id_run_full_clip']['sampled_frames']} | "
                     f"{p['longest_same_six_raw_id_run_core']['sampled_frames']} |")
    lines += ['', '| Near team result | Clips | Sampled edit frames | Exactly-six candidates | Core runs of at least five samples |',
              '| --- | ---: | ---: | ---: | ---: |']
    for group in by_outcome:
        lines.append(f"| {'Won' if group['near_team_won'] else 'Lost'} | "
                     f"{group['clips']} | {group['sampled_frames']} | "
                     f"{group['exactly_six_near_candidate_frames']} | "
                     f"{group['clips_with_five_sample_same_six_run_core']} |")
    lines += ['', 'These are availability diagnostics, not outcome estimates: edit '
              'length and phase differ, and geometric counts include wrong-team candidates.']
    lines += ['', f"At least five consecutive same-six-ID samples occur in "
              f"{summary['clips_with_five_sample_same_six_run_full']}/18 full edited "
              f"clips and {summary['clips_with_five_sample_same_six_run_core']}/18 "
              'conservative cores. Full-clip runs can begin in setup or end after the '
              'point. The tracker reset at the edit cut changes raw IDs relative to '
              'the earlier core-only pass, so ID numbers must not be compared between '
              'passes. The [coverage register](HONOURS_U5_SELECTED_CLIP_COURT_COVERAGE.md) '
              'preserves the earlier core-only screen as a separate diagnostic.', '',
              '![Longest candidate six-ID runs](figures/u5_full_clip_candidate_six_runs.png)', '',
              'The [print-ready figure](figures/u5_full_clip_candidate_six_runs.pdf) '
              'shows the longest candidate run in each clip. Lines are box-bottom '
              'court proxies, circles mark first samples, and crosses mark last samples. '
              'This is a raw-ID visualization; a same-ID line can still switch people. '
              'A [bounded source-frame spot check](HONOURS_U5_FULL_CLIP_SPOTCHECK.md) '
              'finds no obvious identity transfer in the first, middle and last frames '
              'of the two longest runs. White jersey #28 is the near-side libero, '
              'not an opponent. Intervening identity remains unchecked.', '',
              '**No full-rally six-player trajectory is validated** by these raw-ID '
              'segments. Jumps, net overlap, jersey similarity and unsampled frames '
              'can still cause identity or floor-position error. The result deepens '
              'the full-clip tracking audit without promoting candidate paths to '
              'accepted court metrics.', '',
              'Reproduce with `python scripts/screen_u5_full_clip_tracks.py` and '
              '`python scripts/analyze_u5_full_clip_tracklets.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
