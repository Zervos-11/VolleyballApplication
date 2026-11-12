"""Plot short fixed-box court-proxy paths for visual inspection."""

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SOURCE = BASE / 'fixed_box_court_proxy_pilot.json'
FIGURES = ROOT / 'DELIVERABLES/figures'
PNG = FIGURES / 'u5_fixed_box_court_proxy_paths.png'
PDF = FIGURES / 'u5_fixed_box_court_proxy_paths.pdf'
MANIFEST = BASE / 'fixed_box_court_proxy_paths_manifest.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    assert data['summary']['candidate_windows'] == len(data['rows']) == 8
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 4, figsize=(13, 8.2), sharex=True, sharey=True)
    palette = plt.get_cmap('tab10')
    for ax, row in zip(axes.flat, data['rows']):
        ax.plot([0, 9, 9, 0, 0], [0, 0, 9, 9, 0], color='black', linewidth=1.2)
        ax.plot([0, 9], [6, 6], color='0.65', linewidth=.8, linestyle='--')
        ax.plot([0, 9], [9, 9], color='0.25', linewidth=1.7)
        for i, key in enumerate(row['player_keys']):
            positions = [frame['court_proxy_m'][i] for frame in row['frames']]
            xs, ys = zip(*positions)
            color = palette(i)
            ax.plot(xs, ys, color=color, linewidth=1.3, alpha=.9)
            ax.scatter(xs, ys, color=color, s=12)
            ax.scatter(xs[0], ys[0], facecolor='white', edgecolor=color, s=42, linewidth=1.4)
            ax.scatter(xs[-1], ys[-1], color=color, marker='x', s=36, linewidth=1.4)
        outcome = 'WIN' if row['near_team_won'] else 'LOSS'
        ax.set_title(f"S{row['set']} P{row['point_number']} {outcome} | {row['phase']}", fontsize=9)
        ax.set_xlim(-.8, 9.8)
        ax.set_ylim(-.8, 9.8)
        ax.set_aspect('equal')
        ax.grid(alpha=.15)
    fig.supxlabel('Court x (m); camera left to right')
    fig.supylabel('Court y (m); near baseline 0, net 9')
    fig.suptitle('Fixed-box bottom proxy paths, five 5 Hz samples per point\n'
                 'Open circle = first sample; x = last sample; colours distinguish box IDs within each panel',
                 fontsize=12)
    fig.subplots_adjust(left=.065, right=.985, bottom=.11, top=.82,
                        hspace=.45, wspace=.22)
    fig.savefig(PNG, dpi=180)
    fig.savefig(PDF)
    plt.close(fig)
    manifest = {'status': 'court_proxy_visualization_not_ground_truth',
                'source_sha256': data['source_sha256'],
                'pilot_sha256': sha(SOURCE),
                'png_sha256': sha(PNG), 'pdf_sha256': sha(PDF),
                'plotted_windows': len(data['rows']),
                'positions_per_window': 30,
                'interpretation': 'Five sampled fixed-box bottom proxy paths per player; height, pose and floor uncertainty remain.'}
    MANIFEST.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(PNG)


if __name__ == '__main__':
    main()
