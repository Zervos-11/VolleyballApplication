"""Compare one non-anchor full-team shoe reference with the fixed-box proxy."""

import hashlib
import json
import math
from pathlib import Path

import cv2

from analyze_u5_fixed_box_court_proxy import FIELDS, project_xy
from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
MANUAL = BASE / 'dynamic_full_team_manual_qc.json'
PREVIOUS_MANUAL = BASE / 'dynamic_shoe_reference_manual_qc.json'
PROXY = BASE / 'fixed_box_court_proxy_pilot.json'
CALIBRATION = BASE / 'near_court_candidate.json'
OUT = BASE / 'dynamic_full_team_reference_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md'
VIDEO = ROOT / 'data/matches/yt_u5HnY2aNW14/source_720p.mp4'
OVERLAY = BASE / 'dynamic_shoe_reference_sheets/s3_p13_full_team_checked.jpg'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manual = json.loads(MANUAL.read_text(encoding='utf-8'))
    previous = json.loads(PREVIOUS_MANUAL.read_text(encoding='utf-8'))
    proxy = json.loads(PROXY.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    assert manual['source_sha256'] == proxy['source_sha256']
    if not (BASE / manual['source_frame_image']).exists():
        cap = cv2.VideoCapture(str(VIDEO))
        assert cap.isOpened()
        cap.set(cv2.CAP_PROP_POS_FRAMES, manual['source_frame'])
        ok, source = cap.read()
        cap.release()
        assert ok and cv2.imwrite(str(BASE / manual['source_frame_image']), source,
                                  [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert manual['source_frame_image_sha256'] == sha(BASE / manual['source_frame_image'])
    assert manual['existing_two_player_manual_sha256'] == sha(PREVIOUS_MANUAL)
    assert proxy['input_sha256']['calibration'] == sha(CALIBRATION)
    assert calibration['points_court_m'] == [[0, 0], [9, 0], [9, 9], [0, 9]]
    source_row = next(row for row in proxy['rows'] if
                      (row['set'], row['point_number']) ==
                      (manual['set'], manual['point_number']))
    frame = source_row['frames'][-1]
    assert frame['source_frame'] == manual['source_frame']
    keys = [str(key) for key in source_row['player_keys']]
    marks = {str(row['player_key']): row for row in manual['rows']}
    assert len(keys) == len(set(keys)) == len(marks) == 6
    assert set(keys) == set(marks)
    for key in ('14', '2'):
        original = next(row for row in previous['rows'] if
                        (row['set'], row['point_number'], row['source_frame'], str(row['player_key'])) ==
                        (manual['set'], manual['point_number'], manual['source_frame'], key))
        assert original['status'] == 'approximate_clear_pair'
        assert original['shoe_midpoint_px'] == marks[key]['shoe_midpoint_px']
    h = calibration['homography_image_to_court']
    rows = []
    manual_positions = []
    proxy_positions = []
    for i, key in enumerate(keys):
        image = marks[key]['shoe_midpoint_px']
        assert len(image) == 2 and all(0 <= v <= (1280 if j == 0 else 720)
                                       for j, v in enumerate(image))
        floor = project_xy(*image, h)
        predicted = tuple(frame['court_proxy_m'][i])
        manual_positions.append(floor)
        proxy_positions.append(predicted)
        rows.append({'player_key': source_row['player_keys'][i],
                     'manual_shoe_midpoint_px': image,
                     'manual_court_m': [round(v, 4) for v in floor],
                     'proxy_court_m': predicted,
                     'court_position_error_m': round(math.dist(floor, predicted), 4),
                     'note': marks[key]['note']})
    manual_metrics = metrics(manual_positions)
    proxy_metrics = metrics(proxy_positions)
    diffs = {field: round(proxy_metrics[field] - manual_metrics[field], 4)
             for field in FIELDS}
    out = {
        'status': 'one_approximate_non_anchor_six_player_reference_frame_not_trajectory_validation',
        'source_sha256': proxy['source_sha256'],
        'input_sha256': {'manual_qc': sha(MANUAL), 'previous_manual_qc': sha(PREVIOUS_MANUAL),
                         'fixed_box_proxy': sha(PROXY), 'calibration': sha(CALIBRATION)},
        'set': manual['set'], 'point_number': manual['point_number'],
        'source_frame': manual['source_frame'], 'manual_rule': manual['rule'],
        'summary': {'reviewed_players': 6,
                    'reused_existing_manual_marks': 2,
                    'new_manual_marks': 4,
                    'median_position_error_m': round(sorted(r['court_position_error_m'] for r in rows)[2] / 2 +
                                                     sorted(r['court_position_error_m'] for r in rows)[3] / 2, 4),
                    'maximum_position_error_m': round(max(r['court_position_error_m'] for r in rows), 4),
                    'manual_metric': {field: round(manual_metrics[field], 4) for field in FIELDS},
                    'proxy_metric': {field: round(proxy_metrics[field], 4) for field in FIELDS},
                    'proxy_minus_manual_metric': diffs},
        'rows': rows,
        'limitations': ('One selected clear source frame only. Manual marks are approximate and '
                        'single-reviewer; two marks are reused from the earlier non-anchor '
                        'reference. Same-frame team metrics do not validate the other four '
                        'samples in this window, full rallies, or outcome contrasts.')}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    image = cv2.imread(str(BASE / manual['source_frame_image']))
    assert image is not None
    for i, key in enumerate(keys):
        x, y = map(round, frame['fixed_box_bottom_px'][i])
        u, v = marks[key]['shoe_midpoint_px']
        cv2.drawMarker(image, (x, y), (0, 220, 0), cv2.MARKER_CROSS, 14, 2)
        cv2.drawMarker(image, (u, v), (0, 0, 230), cv2.MARKER_TILTED_CROSS, 14, 2)
        cv2.putText(image, key, (u + 8, v - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    .5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(image, key, (u + 8, v - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    .5, (0, 0, 230), 1, cv2.LINE_AA)
    assert cv2.imwrite(str(OVERLAY), image, [cv2.IMWRITE_JPEG_QUALITY, 97])
    labels = {'mean_pairwise_spacing_m': 'Pairwise spacing (m)',
              'convex_hull_area_m2': 'Hull area (m²)',
              'centroid_dispersion_m': 'Centroid dispersion (m)'}
    lines = [
        '# One non-anchor full-team shoe reference', '',
        'Set 3 point 13 at source frame 29952, 12 frames after the fixed-box anchor, '
        'shows all six near-side players with visually readable shoes. The '
        '[unboxed source frame](../data/matches/yt_u5HnY2aNW14/screening/'
        'dynamic_shoe_reference_sheets/full_f29952.jpg) and '
        '[manual marks](../data/matches/yt_u5HnY2aNW14/screening/'
        'dynamic_full_team_manual_qc.json) support this bounded check. '
        'Two marks reuse the earlier non-anchor check; four were added after inspecting '
        'enlarged source crops. This is one approximate single-reviewer team frame.', '',
        '![Six manual shoe midpoints in red and fixed-box proxies in green]'
        '(../data/matches/yt_u5HnY2aNW14/screening/'
        'dynamic_shoe_reference_sheets/s3_p13_full_team_checked.jpg)', '',
        f"The six position discrepancies have median **{out['summary']['median_position_error_m']:.3f} m** "
        f"and maximum **{out['summary']['maximum_position_error_m']:.3f} m**. "
        'The table compares each team metric from the same six manual points and six '
        'fixed-box proxies.', '',
        '| Metric | Manual shoes | Fixed-box proxy | Proxy minus manual |',
        '| --- | ---: | ---: | ---: |']
    for field in FIELDS:
        lines.append(f"| {labels[field]} | {manual_metrics[field]:.3f} | "
                     f"{proxy_metrics[field]:.3f} | {diffs[field]:+.3f} |")
    lines += ['', 'Individual positions and source hashes are in the '
              '[audit JSON](../data/matches/yt_u5HnY2aNW14/screening/'
              'dynamic_full_team_reference_audit.json). The manual shoe midpoints have '
              'about ±12 source-pixel reading uncertainty per axis. This is a selected '
              'clear frame, not a random sample; it does not validate the other four '
              'instants of the window, identity through unsampled frames, or any full rally. '
              'It also does not make the outcome comparison confirmatory.', '',
              'The adjacent +6-frame source image (frame 29946) was screened as a '
              'possible second team reference. Some shoe-to-floor contacts were '
              'ambiguous in that moving frame, so it was not counted as another '
              'complete grounded team frame.', '',
              'Reproduce with `python scripts/audit_u5_dynamic_full_team_reference.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(out['summary'])


if __name__ == '__main__':
    main()
