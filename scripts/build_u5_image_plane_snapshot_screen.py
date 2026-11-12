"""Screen team geometry from one reviewed image box frame per frozen point.

All values are image pixels. Snapshot availability and phase are unequal, so the
within-set contrasts are descriptive diagnostics, not outcome estimates.
"""
import hashlib
import json
import statistics
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
FILES = {
    'sample': BASE / 'rally_sample_score_only.json',
    'visibility': BASE / 'source_visibility_ledger.json',
    'local_qc': BASE / 'bracketed_candidate_source_qc.json',
    'local_boxes': BASE / 'selected_floor_qc/index.json',
    'highres_qc': BASE / 'zero_run_high_res_source_qc.json',
    'highres_boxes': BASE / 'zero_run_high_res_detection/index.json',
    'phase_qc': BASE / 'snapshot_phase_source_qc.json',
}
OUT = BASE / 'image_plane_snapshot_screen.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_IMAGE_PLANE_SNAPSHOT_SCREEN.md'
KEYS = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')
UNITS = ('spacing_px', 'hull_area_px2', 'dispersion_px')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(boxes):
    assert len(boxes) == 6
    centres = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in boxes]
    bottoms = [((b[0] + b[2]) / 2, b[3]) for b in boxes]
    centre_result, bottom_result = metrics(centres), metrics(bottoms)
    return ({unit: round(centre_result[key], 2) for unit, key in zip(UNITS, KEYS)},
            {unit: round(bottom_result[key], 2) for unit, key in zip(UNITS, KEYS)})


def set_contrasts(rows, position_field='box_centre_metrics'):
    out = {}
    for metric in UNITS:
        per_set = {}
        for number in (1, 2, 3):
            wins = [r[position_field][metric] for r in rows
                    if r['set'] == number and r['near_team_won']]
            losses = [r[position_field][metric] for r in rows
                      if r['set'] == number and not r['near_team_won']]
            if not wins or not losses:
                raise ValueError('Outcome group empty in a frozen set')
            per_set[str(number)] = {'wins': len(wins), 'losses': len(losses),
                                    'mean_win_minus_loss': round(statistics.mean(wins) -
                                                                 statistics.mean(losses), 2)}
        out[metric] = {
            'by_set': per_set,
            'equal_set_mean_win_minus_loss': round(statistics.mean(
                v['mean_win_minus_loss'] for v in per_set.values()), 2),
        }
    return out


def main():
    d = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in FILES.items()}
    source = d['sample']['source_sha256']
    assert all(value['source_sha256'] == source for value in d.values()
               if 'source_sha256' in value)
    assert d['local_boxes']['bracketed_source_qc_sha256'] == sha(FILES['local_qc'])
    assert d['highres_qc']['detection_index_sha256'] == sha(FILES['highres_boxes'])
    assert d['local_qc']['summary']['reviewed_local_frames'] == 15
    assert d['highres_qc']['summary']['recovered_local_six_box_instants'] == 2
    visibility = {(r['set'], r['point_number']): r for r in d['visibility']['rows']}
    assert len(visibility) == len(d['sample']['selected_events']) == 18
    assert set(visibility) == {(r['set'], r['point_number']) for r in d['sample']['selected_events']}
    accepted_local = {(r['set'], r['point_number']): r for r in d['local_qc']['rows']}
    rows = []
    for entry in d['local_boxes']['entries']:
        key = entry['set'], entry['point_number']
        assert sha(FILES['local_boxes'].parent / entry['path']) == entry['sha256']
        assert accepted_local[key]['source_frame'] == entry['source_frame']
        assert accepted_local[key]['near_side_six_box_membership'] == 'six_distinct_near_side_teammates_visible'
        assert len({b['raw_track_id'] for b in entry['boxes']}) == 6
        boxes = [b['bbox_px'] for b in entry['boxes']]
        centre, bottom = geometry(boxes)
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': visibility[key]['near_team_won'],
                     'source_frame': entry['source_frame'], 'detector_pass': 'original',
                     'source_phase_status': 'active_looking_not_exact_event_review',
                     'box_centre_metrics': centre, 'box_bottom_image_metrics': bottom,
                     'final_outcome_eligible': False})
    high_index = {(e['set'], e['point_number']): e for e in d['highres_boxes']['entries']}
    for accepted in d['highres_qc']['rows']:
        if accepted['local_six_box_status'] != 'six_correct_near_side_boxes_single_instant':
            continue
        key = accepted['set'], accepted['point_number']
        assert key not in accepted_local
        overlay = FILES['highres_boxes'].parent / accepted['full_resolution_overlay']
        assert sha(overlay) == accepted['full_resolution_overlay_sha256']
        index = high_index[key]
        source_row = next(r for r in index['rows'] if r['source_frame'] == accepted['source_frame'])
        proposals = source_row['broad_person_proposals']
        boxes = [proposals[i]['bbox_px'] for i in accepted['accepted_near_team_proposal_indices']]
        centre, bottom = geometry(boxes)
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': visibility[key]['near_team_won'],
                     'source_frame': accepted['source_frame'], 'detector_pass': 'higher_resolution',
                     'source_phase_status': 'active_looking_single_instant_source_inspection',
                     'box_centre_metrics': centre, 'box_bottom_image_metrics': bottom,
                     'final_outcome_eligible': False})
    rows.sort(key=lambda r: (r['set'], r['point_number']))
    assert len(rows) == 17 and len({(r['set'], r['point_number']) for r in rows}) == 17
    phase_review = {(r['set'], r['point_number']): r for r in d['phase_qc']['rows']}
    assert len(phase_review) == 17
    assert set(phase_review) == {(r['set'], r['point_number']) for r in rows}
    for row in rows:
        review = phase_review[row['set'], row['point_number']]
        assert row['source_frame'] == review['source_frame']
        assert review['phase'] in d['phase_qc']['phase_definitions']
        row['source_phase_status'] = review['phase']
        row['source_phase_note'] = review['note']
    original = [r for r in rows if r['detector_pass'] == 'original']
    missing = sorted(set(visibility) - {(r['set'], r['point_number']) for r in rows})
    assert missing == [(3, 23)]
    original_contrasts = set_contrasts(original)
    augmented_contrasts = set_contrasts(rows)
    bottom_contrasts = set_contrasts(rows, 'box_bottom_image_metrics')
    leave_one_out = {}
    for metric in UNITS:
        values = [set_contrasts([x for x in rows if x is not held])[metric]
                  ['equal_set_mean_win_minus_loss'] for held in rows]
        leave_one_out[metric] = [round(min(values), 2), round(max(values), 2)]
    missing_win_observed_range = {}
    for metric in UNITS:
        observed = [r['box_centre_metrics'][metric] for r in rows]
        scenarios = []
        for candidate in (min(observed), max(observed)):
            assumed = {name: statistics.median(r['box_centre_metrics'][name] for r in rows)
                       for name in UNITS}
            assumed[metric] = candidate
            imputed = {'set': 3, 'point_number': 23, 'near_team_won': True,
                       'box_centre_metrics': assumed}
            scenarios.append(set_contrasts(rows + [imputed])[metric]
                             ['equal_set_mean_win_minus_loss'])
        missing_win_observed_range[metric] = [round(min(scenarios), 2), round(max(scenarios), 2)]
    output = {
        'status': 'image_plane_single_snapshot_diagnostic_not_final_outcome_analysis',
        'source_sha256': source,
        'input_sha256': {name: sha(path) for name, path in FILES.items()},
        'summary': {'frozen_points': 18, 'original_pass_snapshots': 15,
                    'higher_resolution_recoveries': 2, 'all_tested_snapshots': 17,
                    'missing_point': {'set': 3, 'point_number': 23, 'near_team_won': True},
                    'original_group_sizes': {'wins': sum(r['near_team_won'] for r in original),
                                             'losses': sum(not r['near_team_won'] for r in original)},
                    'all_tested_group_sizes': {'wins': sum(r['near_team_won'] for r in rows),
                                               'losses': sum(not r['near_team_won'] for r in rows)},
                    'final_outcome_eligible_points': 0},
        'original_pass_descriptive_contrasts': original_contrasts,
        'all_tested_descriptive_contrasts': augmented_contrasts,
        'all_tested_bottom_anchor_descriptive_contrasts': bottom_contrasts,
        'all_tested_leave_one_point_out_contrast_ranges': leave_one_out,
        'missing_win_observed_value_scenario_ranges': missing_win_observed_range,
        'rows': rows,
        'interpretation': ('One source-checked, availability-selected image-box snapshot per point. '
                           'Camera pixels provide a consistent image coordinate system but are not '
                           'court metres. Box centres are affected by height, posture and detector '
                           'box shape. Phases and detector settings differ, and the only missing '
                           'point is a win. Contrasts are method diagnostics, not estimated '
                           'winner effects; no significance test is valid under these screens.'),
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Primary-match image-plane snapshot screen', '',
        'The [source-bound result](../data/matches/yt_u5HnY2aNW14/screening/image_plane_snapshot_screen.json) '
        'uses one locally source-checked six-player box frame per available frozen '
        'point. All **18** score-selected points stay in the denominator. The '
        'original pass supplies 15 snapshots (6 wins, 9 losses); a higher-resolution '
        'pass supplies two more winning snapshots. Set-three point 23 remains '
        'missing because overlapping players are not six distinct boxes.', '',
        'Each player is represented by the **centre of the image box**. This allows '
        'airborne frames to contribute screen-space positions. The formulas measure '
        'pixel spacing, pixel-squared convex-hull area, and pixel dispersion. '
        'They are not 9 m court positions, movement trajectories, rotation states '
        'or rally-level summaries.', '',
        '| Set | Wins with boxes | Losses with boxes | Availability |',
        '| ---: | ---: | ---: | --- |',
    ]
    for number in (1, 2, 3):
        win_count = sum(r['set'] == number and r['near_team_won'] for r in rows)
        loss_count = sum(r['set'] == number and not r['near_team_won'] for r in rows)
        lines.append(f'| {number} | {win_count}/3 | {loss_count}/3 | '
                     f'{win_count + loss_count}/6 |')
    lines += ['', '## Descriptive stability check', '',
              'For each metric, the diagnostic contrast is the mean winning '
              'snapshot minus mean losing snapshot within each set, averaged '
              'equally over the three sets. The table compares the original '
              '15-frame subset with the augmented 17-frame subset, compares '
              'box-centre and box-bottom image anchors, and reports the range '
              'after removing each available point in turn. '
              'These are sensitivity checks, **not effect estimates**.', '',
              '| Image metric | Original 15 box-centre contrast | '
              'All 17 box-centre contrast | All 17 box-bottom contrast | '
              'All 17 box-centre leave-one-out range | Missing-win observed-range scenario |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    labels = {'spacing_px': 'Mean pairwise spacing (px)',
              'hull_area_px2': 'Convex hull area (px²)',
              'dispersion_px': 'Centroid dispersion (px)'}
    for metric in UNITS:
        first = original_contrasts[metric]['equal_set_mean_win_minus_loss']
        second = augmented_contrasts[metric]['equal_set_mean_win_minus_loss']
        bottom = bottom_contrasts[metric]['equal_set_mean_win_minus_loss']
        lo, hi = leave_one_out[metric]
        missing_lo, missing_hi = missing_win_observed_range[metric]
        lines.append(f'| {labels[metric]} | {first:+.2f} | {second:+.2f} | '
                     f'{bottom:+.2f} | '
                     f'{lo:+.2f} to {hi:+.2f} | '
                     f'{missing_lo:+.2f} to {missing_hi:+.2f} |')
    lines += ['', 'The available-frame rule leaves out one winning point and '
              'the recovered frames use a different detector setting. An '
              '[exact-frame source phase audit](HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md) '
              'finds eight defensive, seven offensive and two serve/reset '
              'snapshots; the snapshots do not align the same interval across '
              'points. The near-court image '
              'is stable, but perspective and body posture also affect pixel '
              'distances. The final column substitutes the missing winning '
              'snapshot with the minimum or maximum **observed** value for '
              'each metric; it is a scenario, not a statistical interval or '
              'measured value. Therefore no significance test, winner association '
              'or court-metre claim follows from this table.', '',
              '## Reproduction', '',
              'Run `python scripts/build_u5_image_plane_snapshot_screen.py`. '
              'The JSON lists every point, source frame, detector pass, both '
              'box-centre and box-bottom image metrics, input hashes and '
              'missingness.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
