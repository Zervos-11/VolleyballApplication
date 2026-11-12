"""Audit non-anchor fixed-box proxy errors against bounded manual shoe marks."""

import hashlib
import json
import math
import statistics
from pathlib import Path

from analyze_u5_fixed_box_court_proxy import project_xy


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'dynamic_shoe_reference_sheets/index.json'
MANUAL = BASE / 'dynamic_shoe_reference_manual_qc.json'
PROXY = BASE / 'fixed_box_court_proxy_pilot.json'
CALIBRATION = BASE / 'near_court_candidate.json'
ANCHOR = BASE / 'fixed_box_anchor_reference_audit.json'
OUT = BASE / 'dynamic_shoe_reference_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    manual = json.loads(MANUAL.read_text(encoding='utf-8'))
    proxy = json.loads(PROXY.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    anchor = json.loads(ANCHOR.read_text(encoding='utf-8'))
    assert manual['review_index_sha256'] == sha(INDEX)
    assert index['proxy_sha256'] == sha(PROXY)
    assert index['pilot_sha256'] == proxy['input_sha256']['pilot']
    assert anchor['input_sha256']['pilot'] == sha(PROXY)
    assert index['source_sha256'] == proxy['source_sha256'] == anchor['source_sha256']
    assert proxy['input_sha256']['calibration'] == sha(CALIBRATION)
    assert calibration['points_court_m'] == [[0, 0], [9, 0], [9, 9], [0, 9]]
    h = calibration['homography_image_to_court']
    by_point = {(r['set'], r['point_number']): r for r in proxy['rows']}
    selected = {}
    for sheet in index['rows']:
        key = sheet['set'], sheet['point_number']
        assert sha(BASE / 'dynamic_shoe_reference_sheets' / sheet['sheet']) == sheet['sheet_sha256']
        assert sha(BASE / 'dynamic_shoe_reference_sheets' / sheet['identity_sheet']) == sheet['identity_sheet_sha256']
        assert sheet['source_frame'] == by_point[key]['source_frames'][-1]
        for item in sheet['selected']:
            slot = key + (sheet['source_frame'], str(item['player_key']))
            assert slot not in selected
            selected[slot] = item
    assert len(selected) == 16
    annotations = {}
    for row in manual['rows']:
        slot = row['set'], row['point_number'], row['source_frame'], str(row['player_key'])
        assert slot in selected and slot not in annotations
        annotations[slot] = row
    assert set(annotations) == set(selected)
    rows = []
    for slot, item in sorted(selected.items()):
        mark = annotations[slot]
        source_row = by_point[slot[:2]]
        frame = source_row['frames'][-1]
        i = item['player_index']
        assert str(source_row['player_keys'][i]) == slot[3]
        assert frame['fixed_box_bottom_px'][i] == item['proxy_bottom_px']
        status = mark['status']
        assert status in ('approximate_clear_pair', 'missing')
        result = {'set': slot[0], 'point_number': slot[1], 'source_frame': slot[2],
                  'player_key': source_row['player_keys'][i], 'status': status,
                  'note': mark['note'],
                  'fixed_box_bottom_px': item['proxy_bottom_px'],
                  'fixed_box_court_m': frame['court_proxy_m'][i]}
        if status == 'missing':
            assert mark['shoe_midpoint_px'] is None
        else:
            x, y = mark['shoe_midpoint_px']
            crop = item['crop']
            assert crop['left'] <= x <= crop['left']+crop['width']
            assert crop['top'] <= y <= crop['top']+crop['height']
            manual_court = project_xy(x, y, h)
            proxy_court = frame['court_proxy_m'][i]
            result.update({'manual_shoe_midpoint_px': [x, y],
                           'manual_shoe_midpoint_court_m': [round(v, 4) for v in manual_court],
                           'image_point_distance_px': round(math.dist(item['proxy_bottom_px'], [x, y]), 3),
                           'court_position_error_m': round(math.dist(proxy_court, manual_court), 4)})
        rows.append(result)
    accepted = [r for r in rows if r['status'] == 'approximate_clear_pair']
    assert len(accepted) == 11
    errors = sorted(r['court_position_error_m'] for r in accepted)
    image_errors = [r['image_point_distance_px'] for r in accepted]
    summary = {'selected_non_anchor_slots': len(rows),
               'single_reviewer_clear_grounded_pairs': len(accepted),
               'missing_uncertain_pairs': len(rows)-len(accepted),
               'points_with_at_least_one_manual_non_anchor_mark': len({(r['set'], r['point_number'])
                                                                     for r in accepted}),
               'median_image_point_distance_px': round(statistics.median(image_errors), 3),
               'median_court_position_error_m': round(statistics.median(errors), 4),
               'maximum_court_position_error_m': round(max(errors), 4),
               'anchor_median_error_m_for_context': anchor['summary']['median_position_error_m'],
               'manual_reading_uncertainty_px_per_axis': 12,
               'complete_six_player_dynamic_reference_frames': 0}
    out = {'status': 'bounded_single_reviewer_dynamic_shoe_reference_not_full_validation',
           'source_sha256': proxy['source_sha256'],
           'input_sha256': {'review_index': sha(INDEX), 'manual_qc': sha(MANUAL),
                            'fixed_box_proxy': sha(PROXY), 'calibration': sha(CALIBRATION),
                            'anchor_audit': sha(ANCHOR)},
           'selection': index['selection_rule'], 'manual_rule': manual['rule'],
           'summary': summary, 'rows': rows,
           'interpretation': ('A single reviewer marked clearly visible grounded shoe pairs '
                              'at +12 frames, with uncertain contacts preserved as missing. '
                              'Crops were chosen from the proxy position and identity sheets '
                              'were available, so labels are not blinded or independent. '
                              'The sample is visibility-selected and contains no complete '
                              'six-player dynamic reference frame. Anchor and non-anchor '
                              'error summaries have different selected players and should '
                              'not be read as paired drift estimates.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Non-anchor manual shoe check for fixed-box paths', '',
             'The [source crop index](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_sheets/) '
             'selects the frontmost and rearmost anchor boxes in each of eight short windows, '
             'then displays the unboxed source image 12 frames after the anchor. The '
             '[manual marks](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_manual_qc.json) '
             'record an approximate midpoint only when both shoes and ground contact appear '
             'clear. The [audit JSON](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_audit.json) '
             'binds the crops, proxy and court calibration by hash.', '',
             f"Of 16 selected non-anchor player views, **{len(accepted)}** have a usable "
             f"single-reviewer shoe midpoint and **{len(rows)-len(accepted)}** are missing "
             'because contact or identity is uncertain. The readable marks cover all eight '
             'short windows; this two-player-per-window subset has no complete '
             'six-player reference frame. A separate '
             '[one-frame team check](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) '
             'reuses two of these marks and adds four. '
             f"Median point discrepancy is **{summary['median_court_position_error_m']:.3f} m** "
             f"and the maximum is **{summary['maximum_court_position_error_m']:.3f} m** "
             'among the 11 accepted points. Approximate manual reading uncertainty is '
             '±12 source pixels per axis.', '',
             '| Point | Player key | Proxy-to-shoe discrepancy (m) | Review |',
             '| --- | --- | ---: | --- |']
    for row in rows:
        value = (f"{row['court_position_error_m']:.3f}" if row['status'] == 'approximate_clear_pair'
                 else 'missing')
        lines.append(f"| S{row['set']} P{row['point_number']} | {row['player_key']} | "
                     f"{value} | {row['note']} |")
    lines += ['', 'The earlier [anchor reference](HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md) '
              'has a 0.277 m median over 16 *different selected players*. Comparing these '
              'medians is not a direct drift estimate. The new marks are approximate, '
              'single-reviewer and not blinded to the identity crop. The evaluation '
              'excludes difficult contacts and does not validate all six players or full '
              'rallies. It does, however, measure the proposed fixed-box proxy away '
              'from its initialization frame and records failures as missing.', '',
              'Reproduce with `python scripts/render_u5_dynamic_shoe_reference_sheets.py` '
              'and `python scripts/audit_u5_dynamic_shoe_reference.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
