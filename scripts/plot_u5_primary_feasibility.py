"""Create the primary-match measurement attrition figure from frozen-sample data."""
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR'] = str(ROOT / '.mplconfig')
(ROOT / '.mplconfig').mkdir(exist_ok=True)

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


SOURCE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/primary_feasibility_result.json'
OUT = ROOT / 'DELIVERABLES/figures'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    assert data['summary']['frozen_points'] == 18
    rows = data['rows']
    assert len(rows) == 18
    stages = [
        ('Six teammates visible in source', lambda r: r['six_player_source_visibility']),
        ('One correct six-box frame', lambda r: r['six_locally_correct_boxes_with_high_res_recovery']),
        ('Five or more same-ID samples', lambda r: r['at_least_five_sample_run_any_pass']),
        ('Validated court-metric point', lambda r: r['validated_six_player_metric_frames'] > 0),
    ]
    counts = [{'stage': name,
               'wins': sum(bool(test(r)) and r['near_team_won'] for r in rows),
               'losses': sum(bool(test(r)) and not r['near_team_won'] for r in rows)}
              for name, test in stages]
    assert [(r['wins'], r['losses']) for r in counts] == [(9, 9), (8, 9), (1, 7), (0, 0)]
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.0, 4.5), dpi=180)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    y = list(range(len(counts)))
    wins = [r['wins'] for r in counts]
    losses = [r['losses'] for r in counts]
    ax.barh(y, wins, color='#2563eb', height=.58, label='Near team won')
    ax.barh(y, losses, left=wins, color='#f59e0b', height=.58, label='Near team lost')
    for i, row in enumerate(counts):
        if row['wins']:
            ax.text(row['wins'] / 2, i, str(row['wins']), ha='center', va='center',
                    fontsize=10, fontweight='bold', color='white')
        if row['losses']:
            ax.text(row['wins'] + row['losses'] / 2, i, str(row['losses']),
                    ha='center', va='center', fontsize=10, fontweight='bold', color='#222222')
        if not row['wins'] and not row['losses']:
            ax.text(.3, i, '0 eligible points', ha='left', va='center',
                    fontsize=10, color='#6b7280')
    ax.set_yticks(y, [r['stage'] for r in counts])
    ax.invert_yaxis()
    ax.set_xlim(0, 18.7)
    ax.set_xticks([0, 3, 6, 9, 12, 15, 18])
    ax.set_xlabel('Frozen points (18 total)')
    ax.set_title('Primary match: attrition by outcome',
                 fontsize=14, fontweight='bold', loc='left', pad=17)
    ax.legend(loc='upper right', frameon=False, ncol=2, bbox_to_anchor=(1, 1.12))
    ax.grid(axis='x', color='#e5e7eb', linewidth=.7)
    ax.set_axisbelow(True)
    for spine in ('top', 'right', 'left'):
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#9ca3af')
    fig.text(.02, .015, 'One frame or a raw-ID run is a detector milestone, not a validated court trajectory.',
             fontsize=8.5, color='#374151')
    fig.subplots_adjust(left=.32, right=.98, top=.78, bottom=.18)
    png, pdf = OUT / 'u5_primary_feasibility_attrition.png', OUT / 'u5_primary_feasibility_attrition.pdf'
    fig.savefig(png, dpi=180, facecolor='white')
    fig.savefig(pdf, facecolor='white')
    plt.close(fig)
    manifest = {'status': 'aggregate_feasibility_figure_no_player_images',
                'source_sha256': data['source_sha256'],
                'input_sha256': sha(SOURCE), 'counts': counts,
                'files': {png.name: sha(png), pdf.name: sha(pdf)}}
    (OUT / 'u5_primary_feasibility_attrition.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(counts)


if __name__ == '__main__':
    main()
