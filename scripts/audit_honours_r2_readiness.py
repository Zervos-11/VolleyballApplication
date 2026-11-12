"""Audit frozen set-two point-two inputs against the honours spatial metric gates."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
SCORE = ROOT / 'data/processed/fqe_auto_score_timeline.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
BASE = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot'
BOUNDARY = BASE / 'boundary_review.json'
LABELS = BASE / 'player_annotations/r2.json'
CALIBRATION = BASE / 'calibration/camera_r2_r5.json'
CALIBRATION_MANIFEST = BASE / 'calibration/calibration_manifest.json'
SIDE = ROOT / 'data/processed/honours_near_side_assignment.json'
ROSTER_SCREEN = ROOT / 'data/processed/honours_r2_roster_source_screen.json'
LABEL_SOURCE_SCREEN = ROOT / 'data/processed/honours_r2_saved_label_source_screen.json'
USER_CONFIRMATION = ROOT / 'data/processed/honours_r2_user_confirmation.json'
CANDIDATE_SOURCE_REVIEW = ROOT / 'data/processed/honours_r2_candidate_source_review.json'
VISIBILITY_DRAFT_MANIFEST = ROOT / 'data/processed/honours_r2_visibility_draft_manifest.json'
OUTPUT = ROOT / 'data/processed/honours_r2_readiness.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_R2_READINESS.md'
SHEET = ROOT / 'data/processed/honours_r2_off_court_review.jpg'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def draw_off_court_sheet(source, labels, rows):
    flagged = [r for r in rows if r['off_court_projections']]
    canvas = np.full((1080, 1920, 3), 245, np.uint8)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Could not open source video for diagnostic sheet')
    try:
        for index, row in enumerate(flagged):
            number = row['frame']
            cap.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                raise RuntimeError(f'Could not decode source frame {number}')
            x0, y0 = (index % 2) * 960, (index // 2) * 540
            flagged_ids = {p['player_id'] for p in row['off_court_projections']}
            for player in labels['frames'][str(number)]['players']:
                if player['footpoint'] is None:
                    continue
                color = (20, 20, 220) if player['player_id'] in flagged_ids else (30, 170, 30)
                x1, y1, x2, y2 = [round(float(v)) for v in player['bbox']]
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                px, py = [round(float(v)) for v in player['footpoint']]
                cv2.circle(frame, (px, py), 10, color, -1)
                cv2.putText(frame, player['player_id'], (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, .9, color, 2)
            cv2.putText(frame, f'frame {number} | red = outside staged 9 m court',
                        (35, 65), cv2.FONT_HERSHEY_SIMPLEX, .85, (20, 20, 20), 3)
            canvas[y0:y0 + 540, x0:x0 + 960] = cv2.resize(frame, (960, 540),
                                                              interpolation=cv2.INTER_AREA)
    finally:
        cap.release()
    if not cv2.imwrite(str(SHEET), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError(f'Could not write {SHEET}')


def main():
    sample, score, source = [read(p) for p in (SAMPLE, SCORE, SOURCE)]
    boundary, labels, calibration, manifest, side, roster_screen, label_source_screen = [read(p) for p in
                                                                     (BOUNDARY, LABELS, CALIBRATION,
                                                                      CALIBRATION_MANIFEST, SIDE, ROSTER_SCREEN,
                                                                      LABEL_SOURCE_SCREEN)]
    assert sample['match_id'] == score['match_id'] == source['match_id'] == labels['match_id']
    assert sample['source_sha256'] == score['source_sha256'] == source['sha256'] == side['source_sha256']
    selected = next(r for r in sample['selected_points'] if (r['set'], r['point_number']) == (2, 2))
    point = next(r for r in score['points'] if (r['set'], r['point_number']) == (2, 2))
    assert selected['score_after'] == point['score_after'] == '2-0' and point['winner'] == 'ProVolley'
    assert selected['pilot_rally_id'] == labels['rally_id'] == 'r2'
    assert roster_screen['source_sha256'] == source['sha256']
    assert label_source_screen['source_sha256'] == source['sha256']
    label_sheet_dir = ROOT / 'data/processed/honours_r2_all_slots_source_sheets'
    for filename, expected_sha in label_source_screen['saved_frame_sheets'].items():
        assert sha(label_sheet_dir / filename) == expected_sha, f'Label source sheet changed: {filename}'
    assert sha(ROOT / label_source_screen['boundary_close_sheet']) == label_source_screen['boundary_close_sheet_sha256']
    for filename, expected_sha in roster_screen['source_sheets'].items():
        sheet_path = ROOT / 'data/processed/pilot_tracker_evaluation/dense_identity_validation_r2' / filename
        assert sha(sheet_path) == expected_sha, f'Roster source sheet changed: {filename}'
    assert sha(ROOT / roster_screen['source_spotcheck_sheet']) == roster_screen['source_spotcheck_sheet_sha256']
    assert sha(ROOT / roster_screen['boundary_side_spotcheck_sheet']) == roster_screen['boundary_side_spotcheck_sheet_sha256']
    assert sha(ROOT / roster_screen['slot42_overlap_sheet']) == roster_screen['slot42_overlap_sheet_sha256']
    sheet_dir = ROOT / 'data/processed/honours_r2_slot42_source_sheets'
    for filename, expected_sha in roster_screen['slot42_dense_source_sheets'].items():
        assert sha(sheet_dir / filename) == expected_sha, f'Dense slot-42 sheet changed: {filename}'
    assert sha(ROOT / roster_screen['slot42_sparse_source_sheet']) == roster_screen['slot42_sparse_source_sheet_sha256']
    dense_dir = ROOT / 'data/processed/pilot_tracker_evaluation/dense_identity_validation_r2'
    assert sha(dense_dir / 'visual_review.json') == roster_screen['existing_visual_review_sha256']
    assert sha(dense_dir / 'assisted_paths.csv') == roster_screen['assisted_paths_sha256']
    with (dense_dir / 'assisted_paths.csv').open(newline='', encoding='utf-8') as file:
        slot42_assisted = [r for r in csv.DictReader(file) if r['player_id'] == '42']
    assert len(slot42_assisted) == 51
    assert [int(r['frame_index']) for r in slot42_assisted if r['candidate_track_id'] == '10'] == list(range(78100, 78106))
    assert [int(r['frame_index']) for r in slot42_assisted if r['candidate_track_id'] == '221'] == list(range(78122, 78151))
    assert (labels['start_frame'], labels['end_frame_exclusive']) == (
        boundary['r2']['start_frame'], boundary['r2']['end_frame_exclusive'])
    assert 'r2' in manifest['camera_segments']['camera_r2_r5']['rallies']
    matrix = cv2.getPerspectiveTransform(np.asarray(calibration['points_px'], np.float32),
                                         np.asarray(calibration['points_court_m'], np.float32))
    heldout = manifest['camera_segments']['camera_r2_r5']['heldout_net_line_px']
    heldout_court = cv2.perspectiveTransform(
        np.asarray([[[heldout[0], heldout[1]], [heldout[2], heldout[3]]]], np.float32), matrix)[0]
    x_left, y_left = map(float, heldout_court[0])
    x_right, y_right = map(float, heldout_court[1])
    def net_depth_at(x):
        return y_left + (x - x_left) * (y_right - y_left) / (x_right - x_left)
    heldout_net_residual_m = [round(net_depth_at(x) - 9.0, 3) for x in (0.0, 9.0)]
    expected_ids = {'1', '4', '5', '7', '36', '42'}
    rows = []
    team_ids = Counter()
    position_statuses = Counter()
    for frame_str, frame in sorted(labels['frames'].items(), key=lambda kv: int(kv[0])):
        frame_number = int(frame_str)
        assert labels['start_frame'] <= frame_number < labels['end_frame_exclusive']
        players = frame['players']
        if len(players) != 6 or {p['player_id'] for p in players} != expected_ids:
            raise ValueError(f'Unexpected player roster on frame {frame_number}')
        team_ids.update(p['team_id'] for p in players)
        position_statuses.update(p['position_status'] for p in players)
        off_court = []
        footpoints = 0
        for player in players:
            point_px = player['footpoint']
            if point_px is None:
                continue
            footpoints += 1
            court = cv2.perspectiveTransform(np.asarray(point_px, np.float32).reshape(1, 1, 2), matrix)[0, 0]
            x, y = float(court[0]), float(court[1])
            if not (np.isfinite(x) and np.isfinite(y) and 0 <= x <= 9 and 0 <= y <= 9):
                off_court.append({'player_id': player['player_id'],
                                  'court_xy_m': [round(x, 3), round(y, 3)]})
        rows.append({'frame': frame_number, 'review_status': frame['review_status'],
                     'independent_review_status': frame['independent_review_status'],
                     'saved_footpoint_count': footpoints, 'in_court_footpoint_count': footpoints - len(off_court),
                     'off_court_projections': off_court,
                     'six_candidate_points_in_court': footpoints == 6 and not off_court})
    candidate_frames = [r['frame'] for r in rows if r['six_candidate_points_in_court']]
    slot42_78300 = next(p for p in labels['frames']['78300']['players'] if p['player_id'] == '42')
    slot42_px = np.asarray(slot42_78300['footpoint'], np.float32).reshape(1, 1, 2)
    slot42_court = cv2.perspectiveTransform(slot42_px, matrix)[0, 0]
    staged_net_px = cv2.perspectiveTransform(
        np.asarray([[[slot42_court[0], 9.0]]], np.float32), np.linalg.inv(matrix))[0, 0]
    slot42_net_excess_px = float(np.linalg.norm(slot42_px[0, 0] - staged_net_px))
    draw_off_court_sheet(source, labels, rows)
    gates = {
        'score_winner_known': True,
        'boundary_saved_by_annotator': boundary['r2']['boundary_status'] == 'checked_by_annotator',
        'boundary_independent_review_complete': boundary['r2']['independent_review_status'] != 'pending',
        'near_side_team_source_verified': roster_screen['near_team_for_r2_point'] == 'UTS'
            and roster_screen['near_team_for_r2_point_status'] == 'source_reviewed',
        'slot42_dense_identity_adjudicated': roster_screen['saved_player42_near_team_status'].startswith('source_reviewed'),
        'six_near_team_player_roster_verified': roster_screen['use_for_team_metrics'],
        'all_sampled_player_labels_reviewed': all(r['review_status'] == 'reviewed' for r in rows),
        'all_sampled_player_labels_independently_reviewed': all(
            r['independent_review_status'] == 'reviewed' for r in rows),
        'court_mapping_validated_for_metric_use': False,
        'continuous_six_player_floor_positions': False,
    }
    result = {
        'status': 'r2_spatial_readiness_audit_no_validated_team_metrics',
        'match_id': source['match_id'], 'source_sha256': source['sha256'],
        'set': 2, 'point_number': 2, 'pilot_rally_id': 'r2', 'winner': point['winner'],
        'frame_interval': [labels['start_frame'], labels['end_frame_exclusive']],
        'interval_frames': labels['end_frame_exclusive'] - labels['start_frame'],
        'saved_sparse_frames': len(rows), 'saved_player_slots': len(rows) * 6,
        'saved_footpoints': sum(r['saved_footpoint_count'] for r in rows),
        'off_court_projected_footpoints': sum(len(r['off_court_projections']) for r in rows),
        'slot42_frame78300_staged_net_excess_image_px': round(slot42_net_excess_px, 2),
        'six_candidate_points_in_court_frames': candidate_frames,
        'team_ids_in_saved_labels': dict(team_ids),
        'position_statuses': dict(position_statuses),
        'roster_screen': roster_screen,
        'saved_label_source_screen': label_source_screen,
        'identity_erratum': {'assisted_slot42_track10_wrong_team_frames': list(range(78100, 78106)),
                             'assisted_slot42_track221_near_uts_22_frames': [78122, 78150],
                             'historic_visual_review_276_claim_valid_for_target_identities': False},
        'calibration': {'status': 'staged_not_metric_validated',
                        'fit_basis': manifest['fit_landmarks'],
                        'heldout_net_line_vertical_error_px_left_right':
                            manifest['camera_segments']['camera_r2_r5']['heldout_vertical_error_px_left_right'],
                        'heldout_net_depth_residual_m_at_court_x0_x9': heldout_net_residual_m,
                        'heldout_net_depth_method': 'Project both held-out line endpoints and interpolate their court-plane line to x=0 and x=9; diagnostic of one landmark, not player-floor accuracy.'},
        'visual_screen': {'status': 'single_analyst_source_still_screen_not_annotation_adjudication',
                          'player_1': 'Near or beyond the right sideline on three sampled frames; an actual off-court movement is possible. Do not automatically call the saved footpoint wrong.',
                          'player_42': f'Near-side UTS #22 is at the net on frame 78300. The saved footpoint is {slot42_net_excess_px:.1f} source pixels beyond the staged net line, so its strict 9 m exclusion is boundary-sensitive, not proof of a wrong player.',
                          'metric_policy': 'Current strict in-court gate excludes these frames. Reconsider the estimand and validate extrapolation before including source-confirmed off-court player positions.'},
        'user_confirmation': read(USER_CONFIRMATION),
        'candidate_source_review': read(CANDIDATE_SOURCE_REVIEW),
        'visibility_draft_manifest': read(VISIBILITY_DRAFT_MANIFEST),
        'gates': gates, 'metric_input_ready': all(gates.values()),
        'frames': rows, 'off_court_review_sheet': str(SHEET.relative_to(ROOT)),
        'off_court_review_sheet_sha256': sha(SHEET),
        'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                         (SAMPLE, SCORE, SOURCE, BOUNDARY, LABELS, CALIBRATION, CALIBRATION_MANIFEST,
                          SIDE, ROSTER_SCREEN, LABEL_SOURCE_SCREEN, USER_CONFIRMATION,
                          CANDIDATE_SOURCE_REVIEW, VISIBILITY_DRAFT_MANIFEST)},
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    rows_md = '\n'.join(f"| {r['frame']} | {r['saved_footpoint_count']}/6 | "
                        f"{r['in_court_footpoint_count']}/6 | "
                        f"{', '.join(x['player_id'] for x in r['off_court_projections']) or '-'} |"
                        for r in rows)
    REPORT.write_text(f'''# Honours R2 point readiness: set 2, point 2

This [source-bound audit](../data/processed/honours_r2_readiness.json) tests the saved R2 pilot against the three-team-metric gate. The score outcome is **ProVolley 2-0**, with the point to ProVolley. The annotator saved a boundary at **frames {labels['start_frame']}-{labels['end_frame_exclusive'] - 1}**, but independent boundary review remains pending. The [sample sheet](../data/processed/honours_sample_sheets/set_2_sample_navigation.jpg) shows this point in its first row.

The [saved player annotations](../data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json) contain **{len(rows)} sparse frames** of the {result['interval_frames']}-frame interval, six named slots per saved frame, and **{result['saved_footpoints']}/{result['saved_player_slots']}** footpoints. All 12 frames remain marked `unreviewed`. The labels call 69 slots `away` and three `unknown`, but the source record does not verify home/away team identity; the [set-side map](../data/processed/honours_near_side_assignment.json) remains provisional.

The user [confirmed the proposed R2 starting setup](../data/processed/honours_r2_user_confirmation.json) as correct on 2 November. That reply did not name exact frames or certify individual foot clicks, visibility states, the full rally roster, or court landmarks. It records useful visual confirmation without changing the saved annotation review flags or the metric gates.

The [slot-42 source adjudication](../data/processed/honours_r2_roster_source_screen.json) resolves the overlap for the saved anchors: slot 42 follows near-side **UTS jersey #22**, visible in the [12-anchor sheet](../data/processed/honours_r2_slot42_source_sheets/saved_slot42_12_sparse_frames.jpg) and continuously across the [78100-78150 source sheets](../data/processed/honours_r2_slot42_source_sheets/frames_78139_78150.jpg). Its saved footpoint at 78100 lies by #22's shoe in the [saved-versus-raw overlay](../data/processed/honours_r2_slot42_overlap_78100.jpg). The assisted raw track 10 followed a **far-side blue player on frames 78100-78105**, whereas assisted track 221 follows near-side #22 on frames 78122-78150. Thus the historical [276-box continuity review](../data/processed/pilot_tracker_evaluation/dense_identity_validation_r2/visual_review.json) is not a 276/276 validation of intended player identities: at least those six assisted assignments are wrong. Saved slot 4 already covers near-side white/aqua jersey #2; saved slot IDs are not jersey numbers. The historical labels and tracker files were preserved, with this adjudication recorded as an erratum.

The [staged R2-R5 court transform](../data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json) projects **{result['off_court_projected_footpoints']}** saved footpoints outside the nominal 9 m near court. The [four-frame source overlay](../data/processed/honours_r2_off_court_review.jpg) marks those saved points in red for inspection. Only **{len(candidate_frames)}/{len(rows)} saved frames** have six candidate footpoints that project in court: **{', '.join(map(str, candidate_frames))}**. These are *candidate coordinates*, not accepted physical positions. The original held-out net-line check is reported in pixels; the court-metre conversion below is a line diagnostic. No independent player-floor position error or approval for metric use is recorded.

The overlay shows slot 1 at or beyond the **right sideline** on three sampled frames. This is plausible actual off-court movement, so its `x > 9 m` values do not by themselves imply bad footpoints. Slot 42 is UTS #22 near the net at frame 78300; its saved footpoint is only **{slot42_net_excess_px:.1f} source pixels** beyond the staged net boundary. That strict `y > 9 m` exclusion is sensitive to a small click or calibration change, not proof of wrong identity. The current strict metric gate excludes all four positions by design. If the research includes players outside the court, define that measure explicitly and validate homography extrapolation before changing the gate.

For this **R2 point only**, the near-side team is source-reviewed as **UTS**: near-side jerseys show UTS text, and the [boundary-side source sheet](../data/processed/honours_r2_boundary_side_spotcheck.jpg) supports a continuous side assignment through the sampled interval. The broader set-two side map remains provisional. ProVolley won this point, so a valid near-side spatial observation here would belong to the losing team.

The [12-frame label source screen](../data/processed/honours_r2_saved_label_source_screen.json) packages [all six saved slots](../data/processed/honours_r2_all_slots_source_sheets/saved_frames_01_04.jpg) and identifies status contradictions without rewriting the historical file: at frame **78500**, UTS #22 remains visible although saved slot 42 says `out_of_frame`; at **78521**, slot 7 has a short, crowded box and no verified floor point. Frames 78050 and 78100 look promising for a six-player still-frame check, but their footpoints have not been independently clicked. The [exact-frame ball sequence](../data/processed/honours_r2_boundary_close_78516_78525.jpg) shows the ball descending to the near-side floor around frames 78520-78522, supporting the saved 78522 exclusive end as plausible. The later score update is not a rally-end timestamp.

The [exact-frame candidate screen](HONOURS_R2_CANDIDATE_SOURCE_REVIEW.md) now inspects full-resolution boxes, shoe crops and court overlays at **78050, 78100 and 78400**. All six boxes visually correspond to near-side UTS players on each frame; shoe-level markers are plausible proposals, with overlap or stepping uncertainty near the net. The fitted court lines remain visually aligned on these exact frames. This source screen has not measured individual click error or changed any review gate.

A [versioned visibility draft](../data/processed/honours_r2_visibility_draft_manifest.json) corrects two source-visible but floor-unknown records: slot 42 at **78500** and slot 7 at **78521** move from `out_of_frame` to `uncertain` with partial occlusion. It adds no footpoints and keeps all 12 frames `unreviewed`. The historical saved annotations remain intact.

The held-out net line, projected into the staged court and evaluated at court x=0 and x=9, has depth residuals of **{heldout_net_residual_m[0]:+.3f} m** and **{heldout_net_residual_m[1]:+.3f} m** relative to y=9 m. This independent line diagnostic does not establish the error of player floor points or approve the homography for final metric use.

| Source frame | Saved footpoints | Inside staged court | Off-court player IDs |
| ---: | ---: | ---: | --- |
{rows_md}

**Result:** slot 42 is source-adjudicated as near-side #22 at the dense anchors, but the strict [team-metric calculator](HONOURS_METRIC_INPUT.md) still has **zero validated R2 team-metric frames**. The three rows with six projected candidate points remain unreviewed positions, not validated formations. Do not calculate a win/loss spatial comparison from them. The next source work is to check the remaining roster slots, the four flagged projections and missing footpoints, independent court landmarks in metres, and a denser six-player floor-position record over a reviewed analysis interval. Preserve unknown or airborne states rather than filling them with still positions.
''', encoding='utf-8')
    print(f'Wrote {OUTPUT} and {REPORT}')


if __name__ == '__main__':
    main()
