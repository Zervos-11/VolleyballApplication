"""Plot the longest six-raw-ID candidate run in each selected edited clip."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.matplotlib_cache'))

import matplotlib  # noqa: E402

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
AUDIT = BASE / 'full_clip_tracklet_audit.json'
SCREEN = BASE / 'full_clip_track_screen.json'
FIGURES = ROOT / 'DELIVERABLES/figures'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    assert audit['input_sha256']['full_clip_screen'] == sha(SCREEN)
    by_screen = {(p['set'], p['point_number']): p for p in screen['points']}
    assert len(by_screen) == len(audit['points']) == 18

    fig, axes = plt.subplots(3, 6, figsize=(17, 10), sharex=True, sharey=True)
    colors = plt.get_cmap('tab10')
    for ax, point in zip(axes.flat, audit['points']):
        run = point['longest_same_six_raw_id_run_full_clip']
        key = point['set'], point['point_number']
        ax.add_patch(Rectangle((0, 0), 9, 9, fill=False, edgecolor='black', lw=.8))
        ax.axhline(3, color='#bbbbbb', lw=.5, ls='--')
        ax.set_xlim(-.4, 9.4)
        ax.set_ylim(-.4, 9.4)
        ax.set_aspect('equal')
        ax.grid(alpha=.13, lw=.5)
        if run['sampled_frames']:
            rows = [r for r in by_screen[key]['rows']
                    if run['first_frame'] <= r['source_frame'] <= run['last_frame']]
            assert len(rows) == run['sampled_frames']
            for index, raw_id in enumerate(run['raw_track_ids']):
                points = []
                for row in rows:
                    matches = [p for p in row['proposals']
                               if p['net_side_status'] == 'near_floor_side_candidate'
                               and p['raw_track_id'] == raw_id]
                    assert len(matches) == 1
                    points.append(matches[0]['box_bottom_court_m'])
                xs, ys = zip(*points)
                color = colors(index)
                ax.plot(xs, ys, color=color, lw=1.4, alpha=.8)
                ax.scatter(xs[0], ys[0], marker='o', s=18, facecolors='white',
                           edgecolors=[color], linewidths=1)
                ax.scatter(xs[-1], ys[-1], marker='x', s=24, color=color,
                           linewidths=1.2)
        ax.set_title(f"S{key[0]} P{key[1]} | {'W' if point['near_team_won'] else 'L'} | "
                     f"{run['sampled_frames']} samples", fontsize=9)
    for ax in axes[-1]:
        ax.set_xlabel('Court proxy x (m)', fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel('Court proxy y (m)', fontsize=8)
    fig.suptitle('Longest same-six raw-ID run per selected edited clip\n'
                 '5 Hz box-bottom court proxies; circles=start, crosses=end; IDs are not validated people',
                 fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .94))
    FIGURES.mkdir(parents=True, exist_ok=True)
    for extension in ('png', 'pdf'):
        fig.savefig(FIGURES / f'u5_full_clip_candidate_six_runs.{extension}',
                    dpi=180 if extension == 'png' else None)
    plt.close(fig)
    print({'panels': len(audit['points']), 'audit_sha256': sha(AUDIT)})


if __name__ == '__main__':
    main()
