"""Audit phase balance of the exact-frame image-box snapshot diagnostic."""

import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'image_plane_snapshot_screen.json'
QC = BASE / 'snapshot_phase_source_qc.json'
CONTEXT = BASE / 'snapshot_phase_context/index.json'
OUT = BASE / 'snapshot_phase_balance_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md'
METRICS = ('spacing_px', 'hull_area_px2', 'dispersion_px')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    context = json.loads(CONTEXT.read_text(encoding='utf-8'))
    assert qc['source_sha256'] == screen['source_sha256']
    assert context['source_sha256'] == screen['source_sha256']
    srows = {(r['set'], r['point_number']): r for r in screen['rows']}
    qrows = {(r['set'], r['point_number']): r for r in qc['rows']}
    crows = {(r['set'], r['point_number']): r for r in context['rows']}
    assert len(srows) == len(qrows) == len(crows) == 17
    assert set(srows) == set(qrows) == set(crows)
    assert screen['summary']['frozen_points'] == 18
    groups = defaultdict(lambda: {'wins': [], 'losses': []})
    joined = []
    for key, row in sorted(srows.items()):
        review = qrows[key]
        ctx = crows[key]
        assert review['source_frame'] == ctx['source_frame'] == row['source_frame']
        assert row['source_phase_status'] == review['phase']
        assert ctx['near_team_won'] == row['near_team_won']
        assert ctx['context_frames'] == [row['source_frame'] + d for d in (-12, 0, 12)]
        assert review['phase'] in qc['phase_definitions']
        sheet = BASE / 'snapshot_phase_context' / ctx['sheet']
        joined.append({'set': key[0], 'point_number': key[1],
                       'near_team_won': row['near_team_won'],
                       'source_frame': row['source_frame'], 'phase': review['phase'],
                       'note': review['note'], 'context_sheet': ctx['sheet'],
                       'context_sheet_sha256': sha(sheet),
                       'box_centre_metrics': row['box_centre_metrics']})
        groups[(key[0], review['phase'])]['wins' if row['near_team_won'] else 'losses'].append(row)
    strata = []
    for (set_no, phase), samples in sorted(groups.items()):
        w, l = samples['wins'], samples['losses']
        contrasts = ({metric: round(statistics.mean(r['box_centre_metrics'][metric] for r in w)
                                    - statistics.mean(r['box_centre_metrics'][metric] for r in l), 2)
                      for metric in METRICS} if w and l else None)
        strata.append({'set': set_no, 'phase': phase, 'wins': len(w), 'losses': len(l),
                       'both_outcomes_present': bool(w and l),
                       'descriptive_win_minus_loss': contrasts})
    matched = [s for s in strata if s['both_outcomes_present'] and s['phase'] != 'serve_or_reset']
    summary = {'frozen_points': 18, 'source_checked_snapshots': 17,
               'missing_point': {'set': 3, 'point_number': 23, 'near_team_won': True},
               'near_defense': sum(r['phase'] == 'near_defense' for r in joined),
               'near_offense': sum(r['phase'] == 'near_offense' for r in joined),
               'serve_or_reset': sum(r['phase'] == 'serve_or_reset' for r in joined),
               'same_set_same_phase_cells_with_both_outcomes': len(matched),
               'snapshots_in_those_cells': sum(s['wins'] + s['losses'] for s in matched),
               'strict_court_metric_eligible_points': 0}
    out = {'status': 'phase_balanced_image_plane_diagnostic_not_outcome_inference',
           'source_sha256': screen['source_sha256'],
           'input_sha256': {'image_plane_snapshot_screen': sha(SCREEN),
                            'snapshot_phase_source_qc': sha(QC),
                            'snapshot_phase_context_index': sha(CONTEXT)},
           'review_basis': qc['review_basis'], 'phase_definitions': qc['phase_definitions'],
           'summary': summary, 'strata': strata, 'rows': joined,
           'interpretation': ('Source review at exact frames identifies gross phase imbalance. '
                              'Even same-set same-phase cells contain only 1-2 observations per '
                              'outcome and availability-selected single snapshots with no validated '
                              'court positions or temporal summaries. Cell differences are descriptive '
                              'screens, not a statistical association with winning.')}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Exact-frame phase audit of the primary-match snapshot screen', '',
             'The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/snapshot_phase_balance_audit.json) '
             'reviews the **exact** 17 six-box source frames, each with unboxed video at '
             '−12, 0 and +12 frames (±0.4 s). The [context sheets](../data/matches/yt_u5HnY2aNW14/screening/snapshot_phase_context/index.json) '
             'and [adjudications](../data/matches/yt_u5HnY2aNW14/screening/snapshot_phase_source_qc.json) '
             'retain the evidence and single-reviewer phase calls. The 18th frozen point, a win, '
             'has no correct six-player snapshot.', '',
             f"The {summary['source_checked_snapshots']} snapshots comprise "
             f"{summary['near_defense']} near-side defensive, "
             f"{summary['near_offense']} near-side offensive and "
             f"{summary['serve_or_reset']} serve/reset frames. "
             'The broad labels describe visible team posture and ball-control direction; they '
             'do not establish an exact touch, live-rally boundary or court-floor position.', '',
             '| Set | Near-side phase | Wins | Losses | Mean win − loss spacing (px) |',
             '| ---: | --- | ---: | ---: | ---: |']
    for s in strata:
        value = (f"{s['descriptive_win_minus_loss']['spacing_px']:+.2f}"
                 if s['descriptive_win_minus_loss'] is not None else '—')
        lines.append(f"| {s['set']} | {s['phase'].replace('_', ' ')} | "
                     f"{s['wins']} | {s['losses']} | {value} |")
    lines += ['', f"Only **{summary['snapshots_in_those_cells']}/18** frozen points fall in the "
              f"{summary['same_set_same_phase_cells_with_both_outcomes']} open-play set-by-phase "
              'cells containing both outcomes. Each outcome has at most two snapshots per cell. '
              'The table is a selection and phase diagnostic; its differences are not winner '
              'effects. The JSON also records hull-area and dispersion differences where both '
              'outcomes exist. The original all-snapshot contrasts pool incompatible phases, '
              'including serve/reset frames. Neither screen supports a significance test or '
              'court-metre association.', '',
              '## Reproduction', '',
              'Run `python scripts/render_u5_snapshot_phase_context.py`, inspect the '
              'source sheets, then `python scripts/audit_u5_snapshot_phase_balance.py`. '
              'Review labels are a separate manually adjudicated input; rerunning the '
              'rendering script does not invent them.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
