"""Describe box-bottom motion in source-checked six-player runs.

These are detector diagnostics. Box bottoms are not accepted ground contacts,
and the run selection is outcome-dependent, so no winner effect is calculated.
"""
import hashlib
import json
import math
import statistics
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
FILES = {
    'runs': BASE / 'interior_identity_run_availability.json',
    'tracks': BASE / 'dense_live_track_screen.json',
    'loss_qc': BASE / 'interior_run_source_qc.json',
    'win_runs': BASE / 'highres_winning_run_screen.json',
    'win_qc': BASE / 'highres_winning_run_source_qc.json',
}
OUT = BASE / 'long_run_proxy_motion_diagnostic.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_RUN_MOTION_DIAGNOSTIC.md'
MEASURES = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def six_points(proposals, ids):
    matches = {p['raw_track_id']: p for p in proposals
               if p['raw_track_id'] in ids and p['net_side_status'] == 'near_floor_side_candidate'}
    if set(matches) != ids or len(matches) != 6:
        raise ValueError('A reviewed run frame does not contain the same six near-side IDs')
    points = {str(pid): matches[pid]['box_bottom_court_m'] for pid in sorted(ids)}
    if not all(len(point) == 2 and all(math.isfinite(v) and 0 <= v <= 9 for v in point)
               for point in points.values()):
        raise ValueError('A proxy point lies outside the strict near-court square')
    return points


def summarize_run(set_number, point_number, won, frames, ids, source_rows, pass_name):
    series = []
    for frame in frames:
        points = six_points(source_rows[frame], ids)
        values = metrics([tuple(points[str(pid)]) for pid in sorted(ids)])
        series.append({'source_frame': frame, 'box_bottom_court_m_by_raw_id': points,
                       'proxy_metrics': {k: round(values[k], 3) for k in MEASURES},
                       'ground_status': 'unvalidated_proxy'})
    steps = []
    for earlier, later in zip(series, series[1:]):
        for pid in ids:
            a = earlier['box_bottom_court_m_by_raw_id'][str(pid)]
            b = later['box_bottom_court_m_by_raw_id'][str(pid)]
            steps.append(math.dist(a, b))
    return {'set': set_number, 'point_number': point_number, 'near_team_won': won,
            'detector_pass': pass_name, 'source_reviewed_team_membership': True,
            'sampled_frames': len(frames), 'source_frame_span': [frames[0], frames[-1]],
            'sampled_duration_s': round((frames[-1] - frames[0]) / 30, 3),
            'maximum_consecutive_proxy_step_m': round(max(steps), 3),
            'median_proxy_metrics': {k: round(statistics.median(r['proxy_metrics'][k] for r in series), 3)
                                     for k in MEASURES},
            'validated_metric_frames': 0, 'frames': series}


def main():
    data = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in FILES.items()}
    source = data['tracks']['source_sha256']
    assert all(d['source_sha256'] == source for d in data.values())
    assert data['runs']['tracks_sha256'] == sha(FILES['tracks'])
    assert data['loss_qc']['run_audit_sha256'] == sha(FILES['runs'])
    assert data['win_qc']['run_audit_sha256'] == sha(FILES['win_runs'])
    old_rows = {(p['set'], p['point_number']): {r['source_frame']: r['proposals']
                                                for r in p['rows']} for p in data['tracks']['points']}
    reviewed_losses = {(p['set'], p['point_number']): p for p in data['loss_qc']['rows']}
    result = []
    for run in data['runs']['points']:
        if run['longest_same_six_raw_id_run_frames'] < 5:
            continue
        key = run['set'], run['point_number']
        qc = reviewed_losses[key]
        frames = run['run_source_frames']
        assert qc['all_sampled_source_frames'] == frames
        assert qc['all_sampled_frame_team_membership'] == 'six_correct_near_side_teammates_each_sampled_frame'
        result.append(summarize_run(*key, run['near_team_won'], frames,
                                    set(run['raw_track_ids']), old_rows[key], 'original'))
    win_qc = data['win_qc']
    key = win_qc['set'], win_qc['point_number']
    winning = next(p for p in data['win_runs']['points'] if (p['set'], p['point_number']) == key)
    frames = win_qc['source_frames']
    assert winning['longest_exact_six_same_raw_id_run'] == frames
    assert win_qc['source_team_membership_status'] == 'six_correct_near_side_teammates_all_13_sampled_frames'
    high_rows = {r['source_frame']: r['near_floor_side_proposals'] for r in winning['rows']}
    result.append(summarize_run(*key, True, frames,
                                {int(pid) for pid in win_qc['raw_id_to_jersey']},
                                high_rows, 'higher_resolution'))
    assert len(result) == 8 and sum(r['near_team_won'] for r in result) == 1
    assert all(r['validated_metric_frames'] == 0 for r in result)
    output = {'status': 'source_membership_checked_box_bottom_motion_not_ground_or_phase_validated',
              'source_sha256': source, 'input_sha256': {k: sha(v) for k, v in FILES.items()},
              'summary': {'reviewed_runs': len(result), 'winning_runs': 1, 'losing_runs': 7,
                          'sampled_frames': sum(r['sampled_frames'] for r in result),
                          'validated_metric_frames': 0},
              'runs': result,
              'interpretation': ('Raw-ID continuity and team membership are checked at sampled instants. '
                                 'Box-bottom court points are unvalidated floor proxies. Some sampled '
                                 'players are airborne, the exact comparable live phase is not certified, '
                                 'and outcome groups are 1 versus 7. These per-run metrics are diagnostic '
                                 'only; no winning association is estimated.')}
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Six-player run motion diagnostic', '',
        'The [source-bound data](../data/matches/yt_u5HnY2aNW14/screening/long_run_proxy_motion_diagnostic.json) '
        'calculate the three implemented geometry formulas on all **66 sampled instants** '
        'in the eight source-membership-checked long runs. These are box-bottom proxies '
        'from two detector settings, **not validated floor positions or final rally metrics**.', '',
        '| Set | Point | Near team result | Samples | Span (s) | Largest 0.2 s proxy step (m) | '
        'Median spacing (m) | Median hull (m²) | Median dispersion (m) |',
        '| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in result:
        med = row['median_proxy_metrics']
        lines.append(f"| {row['set']} | {row['point_number']} | {'Won' if row['near_team_won'] else 'Lost'} | "
                     f"{row['sampled_frames']} | {row['sampled_duration_s']:.1f} | "
                     f"{row['maximum_consecutive_proxy_step_m']:.3f} | "
                     f"{med['mean_pairwise_spacing_m']:.3f} | {med['convex_hull_area_m2']:.3f} | "
                     f"{med['centroid_dispersion_m']:.3f} |")
    lines += [
        '', '## Interpretation', '',
        'The one winning run is set-three point 13. Its [reviewed source sheets]'
        '(../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_review/) '
        'show a blue right-side player airborne in the early part of the run. '
        'A box bottom at that instant is not that player’s floor location. '
        'The seven losing runs came from the original detector pass; the winning run '
        'came from a higher-resolution pass. Their durations and phases also differ. '
        'The table is therefore an implementation and motion-continuity diagnostic, '
        'not a winner comparison. No outcome effect size or significance test is calculated.', '',
        'Every row retains **zero validated metric frames**. A final comparison still '
        'requires a fixed live phase, grounded source-reviewed positions for all six '
        'players at every included sample, a validated court transform, and enough '
        'eligible points in both outcome groups within sets.', '',
        'Reproduce with `python scripts/audit_u5_long_run_proxy_motion.py`.', '',
    ]
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
