"""Visualize source-checked 5 Hz box-centre raw-ID paths in image pixels."""

import hashlib
import json
import math
import os
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
FILES = {
    'runs': BASE / 'interior_identity_run_availability.json',
    'tracks': BASE / 'dense_live_track_screen.json',
    'loss_qc': BASE / 'interior_run_source_qc.json',
    'win_runs': BASE / 'highres_winning_run_screen.json',
    'win_qc': BASE / 'highres_winning_run_source_qc.json',
    'phase': BASE / 'snapshot_phase_source_qc.json',
}
OUT = BASE / 'run_box_centre_trajectory_atlas.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_RUN_TRAJECTORY_ATLAS.md'
FIG = ROOT / 'DELIVERABLES/figures/u5_run_box_centre_trajectory_atlas.png'
PDF = FIG.with_suffix('.pdf')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_record(set_no, point_no, won, frame_numbers, ids, source_rows, detector_pass, phase):
    paths = {str(pid): [] for pid in sorted(ids)}
    for frame_no in frame_numbers:
        candidates = {p['raw_track_id']: p for p in source_rows[frame_no]
                      if p['raw_track_id'] in ids and p['net_side_status'] == 'near_floor_side_candidate'}
        assert set(candidates) == ids and len(candidates) == 6
        for pid in sorted(ids):
            x1, y1, x2, y2 = candidates[pid]['bbox_px']
            paths[str(pid)].append([round((x1+x2)/2, 2), round((y1+y2)/2, 2)])
    lengths = []
    max_step = 0
    for points in paths.values():
        steps = [math.dist(a, b) for a, b in zip(points, points[1:])]
        lengths.append(sum(steps))
        max_step = max(max_step, *steps)
    return {'set': set_no, 'point_number': point_no, 'near_team_won': won,
            'detector_pass': detector_pass, 'phase_at_reviewed_snapshot': phase,
            'sampled_frames': frame_numbers, 'sampled_duration_s': round((frame_numbers[-1]-frame_numbers[0])/30, 3),
            'raw_id_box_centre_px': paths,
            'median_raw_id_sampled_polyline_px': round(statistics.median(lengths), 2),
            'largest_consecutive_sample_step_px': round(max_step, 2),
            'identity_status': 'raw_id_continuity_at_checked_samples_not_full_frame_jersey_validated',
            'floor_position_status': 'not_applicable_image_plane'}


def main():
    data = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in FILES.items()}
    source = data['tracks']['source_sha256']
    assert all(d['source_sha256'] == source for d in data.values())
    assert data['runs']['tracks_sha256'] == sha(FILES['tracks'])
    assert data['loss_qc']['run_audit_sha256'] == sha(FILES['runs'])
    assert data['win_qc']['run_audit_sha256'] == sha(FILES['win_runs'])
    phase = {(r['set'], r['point_number']): r['phase'] for r in data['phase']['rows']}
    originals = {(p['set'], p['point_number']): {r['source_frame']: r['proposals']
                                              for r in p['rows']} for p in data['tracks']['points']}
    losses = {(r['set'], r['point_number']): r for r in data['loss_qc']['rows']}
    rows = []
    for run in data['runs']['points']:
        if run['longest_same_six_raw_id_run_frames'] < 5:
            continue
        key = run['set'], run['point_number']
        reviewed = losses[key]
        assert reviewed['all_sampled_frame_team_membership'] == 'six_correct_near_side_teammates_each_sampled_frame'
        assert reviewed['all_sampled_source_frames'] == run['run_source_frames']
        rows.append(run_record(*key, run['near_team_won'], run['run_source_frames'],
                               set(run['raw_track_ids']), originals[key], 'original', phase[key]))
    win = data['win_qc']
    key = win['set'], win['point_number']
    win_run = next(p for p in data['win_runs']['points'] if (p['set'], p['point_number']) == key)
    assert win['source_team_membership_status'] == 'six_correct_near_side_teammates_all_13_sampled_frames'
    win_rows = {r['source_frame']: r['near_floor_side_proposals'] for r in win_run['rows']}
    rows.append(run_record(*key, True, win['source_frames'],
                           {int(pid) for pid in win['raw_id_to_jersey']}, win_rows,
                           'higher_resolution', phase[key]))
    rows.sort(key=lambda r: (r['set'], r['point_number']))
    assert len(rows) == 8 and sum(r['near_team_won'] for r in rows) == 1
    assert sum(len(r['sampled_frames']) for r in rows) == 66
    assert sum(r['phase_at_reviewed_snapshot'] == 'serve_or_reset' for r in rows) == 1
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    fig, axes = plt.subplots(4, 2, figsize=(12, 14), constrained_layout=True)
    for ax, row in zip(axes.flat, rows):
        ax.add_patch(Polygon([(239, 648), (1122, 648), (1046, 313), (297, 313)],
                             closed=True, fill=False, lw=1.3, edgecolor='#555555'))
        for pid, points in row['raw_id_box_centre_px'].items():
            xs, ys = zip(*points)
            line, = ax.plot(xs, ys, marker='o', ms=2.8, lw=1.5, alpha=.85)
            ax.scatter([xs[0]], [ys[0]], marker='s', s=25, color=line.get_color())
            ax.text(xs[-1]+4, ys[-1], pid, fontsize=7, color=line.get_color())
        status = 'win' if row['near_team_won'] else 'loss'
        ax.set_title(f"S{row['set']} P{row['point_number']} {status} | "
                     f"{len(row['sampled_frames'])} samples | {row['phase_at_reviewed_snapshot'].replace('_',' ')}",
                     fontsize=10)
        ax.set_xlim(150, 1200)
        ax.set_ylim(690, 250)
        ax.set_aspect('equal', adjustable='box')
        ax.grid(alpha=.18)
        ax.set_xlabel('source image x (px)')
        ax.set_ylabel('source image y (px)')
    fig.suptitle('Source-checked six-person raw-ID box-centre paths at 5 Hz', fontsize=14)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=180)
    fig.savefig(PDF)
    plt.close(fig)
    summary = {'reviewed_runs': 8, 'winning_runs': 1, 'losing_runs': 7,
               'sampled_frame_instances': 66,
               'run_with_serve_or_reset_snapshot': {'set': 1, 'point_number': 34},
               'validated_full_frame_trajectories': 0,
               'validated_court_trajectories': 0}
    out = {'status': 'sampled_image_plane_raw_id_path_diagnostic', 'source_sha256': source,
           'input_sha256': {name: sha(path) for name, path in FILES.items()},
           'figure_sha256': {'png': sha(FIG), 'pdf': sha(PDF)},
           'summary': summary, 'runs': rows,
           'interpretation': ('Six team members were source checked at each displayed sample, '
                              'but raw IDs in most runs were not independently matched to named '
                              'jerseys and frames between 5 Hz samples were not reviewed. Box-centre '
                              'paths remain in image pixels, with different detector passes and phases; '
                              'the set-one point-34 anchor is serve/reset. Do not infer movement distance '
                              'on court or a winner effect from these lines.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Source-checked image-plane trajectory atlas', '',
             '![Eight six-player raw-ID path candidates](figures/u5_run_box_centre_trajectory_atlas.png)', '',
             'The [print-ready PDF](figures/u5_run_box_centre_trajectory_atlas.pdf) and '
             '[source-bound coordinate record](../data/matches/yt_u5HnY2aNW14/screening/run_box_centre_trajectory_atlas.json) '
             'show the **66 sampled frame instances** from eight runs with six visually correct '
             'near-side teammates at every displayed 5 Hz sample. Each coloured line follows one '
             'raw tracker ID by the centre of its image box; the square marks its first sample. '
             'The outlined quadrilateral is the near court in the source image. Airborne players '
             'remain valid screen-space box centres. Several front-row centres plot above the '
             'floor-plane net line because body centres are elevated; that visual gap is why '
             'the centres are not projected through the floor homography.', '',
             '| Set | Point | Result | Samples | Span (s) | Median raw-ID polyline (px) | Largest sample step (px) | Phase at selected snapshot |',
             '| ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |']
    for row in rows:
        lines.append(f"| {row['set']} | {row['point_number']} | "
                     f"{'Won' if row['near_team_won'] else 'Lost'} | "
                     f"{len(row['sampled_frames'])} | {row['sampled_duration_s']:.2f} | "
                     f"{row['median_raw_id_sampled_polyline_px']:.2f} | "
                     f"{row['largest_consecutive_sample_step_px']:.2f} | "
                     f"{row['phase_at_reviewed_snapshot'].replace('_', ' ')} |")
    lines += ['', 'The polyline sums only observed 0.2 s sample-to-sample image displacements. '
              'It is **not court movement distance** and can underestimate motion between samples. '
              'One run (set one, point 34) has a serve/reset snapshot; the whole-run live phase '
              'is not certified. There is only one winning run, from a different detector pass. '
              'Source review checked team membership at sampled frames, not every intervening '
              'video frame or named jersey identity for every path. These lines are candidate '
              'trajectories for evaluation, not validated court trajectories or outcome effects.', '',
              'Reproduce with `python scripts/build_u5_run_trajectory_atlas.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
