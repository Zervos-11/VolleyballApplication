"""Summarise the frozen primary-match sample without promoting proxy snapshots."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PATHS = {
    'sample': BASE / 'rally_sample_score_only.json',
    'visibility': BASE / 'source_visibility_ledger.json',
    'intervals': BASE / 'event_transition_source_qc.json',
    'runs': BASE / 'interior_identity_run_availability.json',
    'long_review': BASE / 'interior_run_source_qc.json',
    'short_review': BASE / 'winning_short_run_source_qc.json',
    'zero_review': BASE / 'zero_run_source_qc.json',
    'local_boxes': BASE / 'bracketed_candidate_source_qc.json',
    'camera': BASE / 'selected_camera_registration.json',
    'earlier_floor': BASE / 'floor_proxy_reference_audit.json',
    'heldout_floor': BASE / 'heldout_box_floor_error.json',
    'proxy': BASE / 'selected_proxy_sensitivity.json',
    'high_res_recovery': BASE / 'zero_run_high_res_source_qc.json',
    'high_res_runs': BASE / 'highres_winning_run_screen.json',
    'high_res_run_qc': BASE / 'highres_winning_run_source_qc.json',
    'motion_diagnostic': BASE / 'long_run_proxy_motion_diagnostic.json',
    'matched_pilot': BASE / 'matched_window_pilot_source_qc.json',
    'image_snapshot_screen': BASE / 'image_plane_snapshot_screen.json',
    'snapshot_phase_audit': BASE / 'snapshot_phase_balance_audit.json',
    'phase_proxy_diagnostic': BASE / 'phase_matched_proxy_diagnostic.json',
    'trajectory_atlas': BASE / 'run_box_centre_trajectory_atlas.json',
    'box_centre_flow_audit': BASE / 'box_centre_flow_audit.json',
    'flow_window_geometry': BASE / 'flow_window_image_geometry.json',
    'flow_five_sample_review': BASE / 'flow_window_five_sample_audit.json',
    'flow_window_sensitivity': BASE / 'flow_window_sensitivity.json',
    'fixed_box_court_proxy': BASE / 'fixed_box_court_proxy_pilot.json',
    'fixed_box_anchor_audit': BASE / 'fixed_box_anchor_reference_audit.json',
    'dynamic_shoe_audit': BASE / 'dynamic_shoe_reference_audit.json',
    'dynamic_error_sensitivity': BASE / 'dynamic_error_sensitivity.json',
    'dynamic_full_team_audit': BASE / 'dynamic_full_team_reference_audit.json',
    'dense_screen': BASE / 'dense_live_track_screen.json',
    'selected_clip_court_coverage': BASE / 'selected_clip_court_candidate_coverage.json',
    'full_clip_screen': BASE / 'full_clip_track_screen.json',
    'full_clip_tracklets': BASE / 'full_clip_tracklet_audit.json',
    'full_clip_spotcheck': BASE / 'full_clip_run_spotcheck_audit.json',
    'full_run_identity': BASE / 'full_run_identity_audit.json',
    'full_run_position': BASE / 'full_run_position_reference.json',
    'two_long_runs_30fps': BASE / 'two_long_runs_30fps_audit.json',
    'full_rally_gate': BASE / 'full_rally_trajectory_gate_audit.json',
    'live_six_reference': BASE / 'full_rally_live_reference_audit.json',
}
OUT_JSON = BASE / 'primary_feasibility_result.json'
OUT_MD = ROOT / 'DELIVERABLES/HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in PATHS.items()}
    sample = data['sample']
    assert len(sample['selected_events']) == 18
    assert all(value['source_sha256'] == sample['source_sha256'] for value in data.values()
               if 'source_sha256' in value)
    vis = {(r['set'], r['point_number']): r for r in data['visibility']['rows']}
    run = {(r['set'], r['point_number']): r for r in data['runs']['points']}
    interval = {(r['set'], r['point_number']): r for r in data['intervals']['points']}
    assert len(vis) == len(run) == len(interval) == 18
    long_checked = {(r['set'], r['point_number']) for r in data['long_review']['rows']}
    short_checked = {(r['set'], r['point_number']) for r in data['short_review']['rows']
                     if r['source_team_membership_status'] == 'six_correct_near_side_teammates_each_sampled_frame'}
    recovered = {(r['set'], r['point_number']) for r in data['high_res_recovery']['rows']
                 if r['local_six_box_status'] == 'six_correct_near_side_boxes_single_instant'}
    assert len(recovered) == 2 and recovered.isdisjoint(
        {(r['set'], r['point_number']) for r in data['local_boxes']['rows']})
    assert data['high_res_run_qc']['run_audit_sha256'] == sha(PATHS['high_res_runs'])
    assert len(data['high_res_run_qc']['earliest_five_active_looking_frames']) == 5
    highres_long_key = (data['high_res_run_qc']['set'], data['high_res_run_qc']['point_number'])
    assert highres_long_key == (3, 13)
    assert data['motion_diagnostic']['summary'] == {
        'reviewed_runs': 8, 'winning_runs': 1, 'losing_runs': 7,
        'sampled_frames': 66, 'validated_metric_frames': 0,
    }
    assert data['matched_pilot']['summary']['strict_eligible_windows'] == 0
    assert data['image_snapshot_screen']['summary']['all_tested_snapshots'] == 17
    assert data['image_snapshot_screen']['summary']['final_outcome_eligible_points'] == 0
    assert data['snapshot_phase_audit']['input_sha256']['image_plane_snapshot_screen'] == sha(PATHS['image_snapshot_screen'])
    assert data['snapshot_phase_audit']['summary']['source_checked_snapshots'] == 17
    assert data['snapshot_phase_audit']['summary']['strict_court_metric_eligible_points'] == 0
    assert data['phase_proxy_diagnostic']['input_sha256']['snapshot'] == sha(PATHS['image_snapshot_screen'])
    assert data['phase_proxy_diagnostic']['input_sha256']['phase'] == sha(PATHS['snapshot_phase_audit'])
    assert data['phase_proxy_diagnostic']['summary']['phase_matched_open_play_snapshots'] == 13
    assert data['phase_proxy_diagnostic']['summary']['validated_outcome_metrics'] == 0
    assert data['trajectory_atlas']['summary']['sampled_frame_instances'] == 66
    assert data['trajectory_atlas']['summary']['validated_court_trajectories'] == 0
    assert data['trajectory_atlas']['summary']['run_with_serve_or_reset_snapshot'] == {
        'set': 1, 'point_number': 34}
    assert data['box_centre_flow_audit']['summary']['reviewed_anchor_snapshots'] == 17
    assert data['box_centre_flow_audit']['summary']['visually_clear_open_play_set_phase_matched_windows'] == 8
    assert data['box_centre_flow_audit']['summary']['validated_court_trajectory_windows'] == 0
    assert data['flow_window_geometry']['input_sha256']['endpoint_audit'] == sha(PATHS['box_centre_flow_audit'])
    assert data['flow_window_geometry']['summary']['source_screened_candidate_windows'] == 8
    assert data['flow_window_geometry']['summary']['validated_court_metric_windows'] == 0
    assert data['flow_five_sample_review']['input_sha256']['image_geometry'] == sha(PATHS['flow_window_geometry'])
    assert data['flow_five_sample_review']['summary']['no_obvious_transfer_at_five_displayed_instants'] == 8
    assert data['flow_five_sample_review']['summary']['validated_court_trajectory_windows'] == 0
    assert data['flow_window_sensitivity']['input_sha256']['geometry'] == sha(PATHS['flow_window_geometry'])
    assert data['flow_window_sensitivity']['input_sha256']['source_review'] == sha(PATHS['flow_five_sample_review'])
    assert data['flow_window_sensitivity']['summary']['one_point_deletions'] == 8
    assert data['fixed_box_court_proxy']['input_sha256']['pilot'] == sha(BASE / 'box_centre_flow_pilot.json')
    assert data['fixed_box_court_proxy']['input_sha256']['review'] == sha(PATHS['flow_five_sample_review'])
    assert data['fixed_box_court_proxy']['summary']['candidate_player_positions'] == 240
    assert data['fixed_box_court_proxy']['summary']['independently_validated_dynamic_floor_positions'] == 0
    assert data['fixed_box_anchor_audit']['input_sha256']['pilot'] == sha(PATHS['fixed_box_court_proxy'])
    assert data['fixed_box_anchor_audit']['summary']['matching_clear_shoe_players'] == 16
    assert data['fixed_box_anchor_audit']['summary']['complete_six_player_reference_frames'] == 2
    assert data['dynamic_shoe_audit']['input_sha256']['fixed_box_proxy'] == sha(PATHS['fixed_box_court_proxy'])
    assert data['dynamic_shoe_audit']['summary']['single_reviewer_clear_grounded_pairs'] == 11
    assert data['dynamic_error_sensitivity']['input_sha256']['dynamic_shoe_audit'] == sha(PATHS['dynamic_shoe_audit'])
    assert data['dynamic_error_sensitivity']['input_sha256']['fixed_box_proxy'] == sha(PATHS['fixed_box_court_proxy'])
    assert data['dynamic_full_team_audit']['input_sha256']['fixed_box_proxy'] == sha(PATHS['fixed_box_court_proxy'])
    assert data['dynamic_full_team_audit']['summary']['reviewed_players'] == 6
    assert data['dynamic_full_team_audit']['source_frame'] == 29952
    assert data['selected_clip_court_coverage']['input_sha256']['dense'] == sha(PATHS['dense_screen'])
    assert data['selected_clip_court_coverage']['summary']['selected_points'] == 18
    assert data['selected_clip_court_coverage']['summary']['five_hz_grid_frames'] == 1005
    assert data['selected_clip_court_coverage']['summary']['strict_validated_six_player_metric_frames'] == 0
    assert data['full_clip_tracklets']['input_sha256']['full_clip_screen'] == sha(PATHS['full_clip_screen'])
    assert data['full_clip_tracklets']['summary']['sampled_frames'] == 1005
    assert data['full_clip_tracklets']['summary']['exactly_six_near_candidate_frames'] == 348
    assert data['full_clip_spotcheck']['input_sha256']['tracklet_audit'] == sha(PATHS['full_clip_tracklets'])
    assert data['full_clip_spotcheck']['summary']['wrong_team_raw_runs_rejected'] == 0
    assert data['full_clip_spotcheck']['summary']['raw_runs_with_no_obvious_transfer_at_displayed_frames'] == 2
    assert data['full_clip_spotcheck']['summary']['validated_full_rally_six_player_trajectories'] == 0
    assert data['full_run_identity']['input_sha256']['full_clip_tracklets'] == sha(PATHS['full_clip_tracklets'])
    assert data['full_run_identity']['summary']['sampled_person_boxes_reviewed'] == 216
    assert data['full_run_identity']['summary']['obvious_sampled_identity_switches'] == 0
    assert data['full_run_position']['input_sha256']['every_sample_identity_audit'] == sha(PATHS['full_run_identity'])
    assert data['full_run_position']['summary']['clear_grounded_manual_pairs'] == 2
    assert data['full_run_position']['summary']['validated_full_run_court_trajectories'] == 0
    assert data['two_long_runs_30fps']['input_sha256']['every_sample_identity_audit'] == sha(PATHS['full_run_identity'])
    assert data['two_long_runs_30fps']['summary']['source_frames_screened'] == 206
    assert data['two_long_runs_30fps']['summary']['frames_with_temporary_missing_candidate'] == 10
    assert data['two_long_runs_30fps']['summary']['source_visible_unboxed_missing_frames_reviewed'] == 10
    assert data['full_rally_gate']['summary']['full_rallies_validated'] == 0
    assert data['full_rally_gate']['summary']['reviewed_span_frames'] == 246
    assert data['full_rally_gate']['summary']['reviewed_span_frames_with_six_initial_raw_ids'] == 159
    assert data['full_rally_gate']['input_sha256']['live_reference'] == sha(PATHS['live_six_reference'])
    assert data['live_six_reference']['summary']['reviewed_players'] == 30
    assert data['live_six_reference']['summary']['six_player_reference_frames'] == 5
    rows = []
    for key, v in sorted(vis.items()):
        r = run[key]
        i = interval[key]
        assert r['near_team_won'] == v['near_team_won']
        evidence = v['six_player_visibility_evidence']
        rows.append({
            'set': key[0], 'point_number': key[1], 'near_team': v['near_team'],
            'near_team_won': v['near_team_won'],
            'six_player_source_visibility': True,
            'six_locally_correct_detector_boxes': evidence == 'source_reviewed_six_local_detector_boxes',
            'six_locally_correct_boxes_with_high_res_recovery': (
                evidence == 'source_reviewed_six_local_detector_boxes' or key in recovered),
            'conservative_interior_duration_s': i['interior_duration_s'],
            'longest_same_six_raw_id_run_5hz_samples': r['longest_same_six_raw_id_run_frames'],
            'at_least_five_sample_run': r['longest_same_six_raw_id_run_frames'] >= 5,
            'at_least_five_sample_run_any_pass': (r['longest_same_six_raw_id_run_frames'] >= 5
                                                 or key == highres_long_key),
            'source_reviewed_six_person_run': key in long_checked or key in short_checked,
            'camera_registration_point_checked': True,
            'validated_six_player_metric_frames': 0,
        })
    assert len(rows) == 18
    groups = []
    for set_number in (1, 2, 3):
        for won in (True, False):
            group = [r for r in rows if r['set'] == set_number and r['near_team_won'] == won]
            assert len(group) == 3
            groups.append({'set': set_number, 'near_team_won': won,
                           'frozen_points': len(group),
                           'source_visible_six_points': sum(r['six_player_source_visibility'] for r in group),
                           'correct_local_six_box_points': sum(r['six_locally_correct_detector_boxes'] for r in group),
                           'correct_local_six_box_points_any_pass': sum(
                               r['six_locally_correct_boxes_with_high_res_recovery'] for r in group),
                           'points_with_five_sample_run': sum(r['at_least_five_sample_run'] for r in group),
                           'points_with_source_checked_six_run': sum(r['source_reviewed_six_person_run'] for r in group),
                           'points_with_validated_metric_frame': 0})
    result = {
        'status': 'primary_match_feasibility_result_outcome_association_not_estimable',
        'source_sha256': sample['source_sha256'],
        'input_sha256': {key: sha(path) for key, path in PATHS.items()},
        'denominator_rule': '18 score-only frozen points, three per set and near-team outcome group; no point removed after spatial inspection.',
        'summary': {
            'frozen_points': 18, 'near_team_wins': 9, 'near_team_losses': 9,
            'points_with_source_visible_six': sum(r['six_player_source_visibility'] for r in rows),
            'points_with_correct_local_six_boxes': sum(r['six_locally_correct_detector_boxes'] for r in rows),
            'points_with_correct_local_six_boxes_any_pass': sum(
                r['six_locally_correct_boxes_with_high_res_recovery'] for r in rows),
            'high_res_single_frame_recoveries': len(recovered),
            'image_plane_source_checked_snapshot_points': data['image_snapshot_screen']['summary']['all_tested_snapshots'],
            'snapshot_phase_matched_open_play_points': data['snapshot_phase_audit']['summary']['snapshots_in_those_cells'],
            'phase_matched_proxy_snapshot_points': data['phase_proxy_diagnostic']['summary']['phase_matched_open_play_snapshots'],
            'source_checked_image_trajectory_sample_instances': data['trajectory_atlas']['summary']['sampled_frame_instances'],
            'long_run_points_with_serve_reset_snapshot_anchor': 1,
            'flow_five_sample_candidate_windows': data['box_centre_flow_audit']['summary']['six_algorithmic_flow_candidates_at_all_five_samples'],
            'flow_endpoint_clear_phase_matched_candidate_windows': data['box_centre_flow_audit']['summary']['visually_clear_open_play_set_phase_matched_windows'],
            'image_plane_five_sample_geometry_candidate_windows': data['flow_window_geometry']['summary']['source_screened_candidate_windows'],
            'flow_five_instants_visually_clear_candidate_windows': data['flow_five_sample_review']['summary']['no_obvious_transfer_at_five_displayed_instants'],
            'fixed_box_court_proxy_candidate_positions': data['fixed_box_court_proxy']['summary']['candidate_player_positions'],
            'fixed_box_anchor_manual_shoe_matches': data['fixed_box_anchor_audit']['summary']['matching_clear_shoe_players'],
            'fixed_box_non_anchor_manual_shoe_matches': data['dynamic_shoe_audit']['summary']['single_reviewer_clear_grounded_pairs'],
            'fixed_box_non_anchor_largest_observed_discrepancy_m': data['dynamic_shoe_audit']['summary']['maximum_court_position_error_m'],
            'fixed_box_complete_non_anchor_manual_team_frames': 1,
            'selected_clip_five_hz_grid_frames': data['selected_clip_court_coverage']['summary']['five_hz_grid_frames'],
            'selected_clip_exactly_six_unvalidated_candidate_frames': data['selected_clip_court_coverage']['summary']['exactly_six_candidates_unvalidated'],
            'full_clip_screened_five_hz_frames': data['full_clip_tracklets']['summary']['sampled_frames'],
            'full_clip_exactly_six_unvalidated_candidate_frames': data['full_clip_tracklets']['summary']['exactly_six_near_candidate_frames'],
            'full_clip_contiguous_raw_tracklet_segments': data['full_clip_tracklets']['summary']['raw_tracklet_segments'],
            'full_clip_points_with_five_sample_same_six_raw_id_run': data['full_clip_tracklets']['summary']['clips_with_five_sample_same_six_run_full'],
            'full_clip_spotchecked_runs_no_obvious_transfer_at_displayed_frames': data['full_clip_spotcheck']['summary']['raw_runs_with_no_obvious_transfer_at_displayed_frames'],
            'full_run_identity_reviewed_sampled_person_boxes': data['full_run_identity']['summary']['sampled_person_boxes_reviewed'],
            'full_run_identity_obvious_sampled_switches': data['full_run_identity']['summary']['obvious_sampled_identity_switches'],
            'full_run_position_clear_manual_pairs': data['full_run_position']['summary']['clear_grounded_manual_pairs'],
            'two_long_runs_30fps_source_frames_screened': data['two_long_runs_30fps']['summary']['source_frames_screened'],
            'two_long_runs_30fps_frames_with_temporary_missing_candidate': data['two_long_runs_30fps']['summary']['frames_with_temporary_missing_candidate'],
            'reviewed_span_frames_through_last_reviewed_live': data['full_rally_gate']['summary']['reviewed_span_frames'],
            'reviewed_span_frames_with_six_initial_raw_ids': data['full_rally_gate']['summary']['reviewed_span_frames_with_six_initial_raw_ids'],
            'in_rally_six_player_manual_reference_frames': data['full_rally_gate']['summary']['six_player_manual_reference_frames_in_runs'],
            'points_with_five_sample_six_id_run': sum(r['at_least_five_sample_run'] for r in rows),
            'five_sample_run_wins': sum(r['at_least_five_sample_run'] and r['near_team_won'] for r in rows),
            'five_sample_run_losses': sum(r['at_least_five_sample_run'] and not r['near_team_won'] for r in rows),
            'five_sample_run_points_any_pass': sum(r['at_least_five_sample_run_any_pass'] for r in rows),
            'five_sample_run_wins_any_pass': sum(r['at_least_five_sample_run_any_pass'] and
                                                 r['near_team_won'] for r in rows),
            'source_reviewed_run_points': sum(r['source_reviewed_six_person_run'] for r in rows),
            'camera_registered_review_frames': data['camera']['summary']['frames_registered'],
            'camera_registered_frozen_points': data['camera']['summary']['frozen_points_covered'],
            'clear_shoe_reference_boxes': (data['earlier_floor']['summary']['reviewed_grounded_boxes'] +
                                           data['heldout_floor']['summary']['reviewed_clear_grounded_shoe_pairs']),
            'largest_observed_box_to_shoe_discrepancy_m': data['heldout_floor']['summary']['maximum_box_to_shoe_distance_m'],
            'validated_six_player_metric_frames': 0,
            'validated_rally_or_fixed_window_metrics': 0,
            'within_set_outcome_association_estimable': False,
        },
        'groups': groups, 'rows': rows,
        'interpretation': ('All six near-side teammates are locally visible in every frozen point. '
                           'The tracker has uneven six-person continuity by outcome. Image registration is stable, '
                           'but point-level floor anchors and trajectories are not validated. No court-metric winner '
                           'effect or null effect can be estimated from the strict eligible sample.'),
    }
    assert result['summary']['points_with_five_sample_six_id_run'] == 7
    assert result['summary']['five_sample_run_wins'] == 0
    assert result['summary']['points_with_correct_local_six_boxes'] == 15
    assert result['summary']['points_with_correct_local_six_boxes_any_pass'] == 17
    assert result['summary']['five_sample_run_points_any_pass'] == 8
    assert result['summary']['five_sample_run_wins_any_pass'] == 1
    OUT_JSON.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(
        f"| {g['set']} | {'Won' if g['near_team_won'] else 'Lost'} | {g['frozen_points']} | "
        f"{g['source_visible_six_points']} | {g['correct_local_six_box_points']} | "
        f"{g['correct_local_six_box_points_any_pass']} | "
        f"{g['points_with_five_sample_run']} | {g['points_with_validated_metric_frame']} |"
        for g in groups)
    report = f'''# Primary-match feasibility result

The primary Concordia–UCLA recording has **18 score-only frozen points**, selected before spatial inspection: three near-team wins and three losses in each of three sets. The [machine-readable result](../data/matches/yt_u5HnY2aNW14/screening/primary_feasibility_result.json) binds every stage to source hashes and retains all 18 points. This is an empirical feasibility result, not a completed court-metric outcome analysis.

| Set | Near team result | Frozen points | Six visible in source | Correct boxes, original pass | Correct boxes, any tested pass | ≥5 six-ID samples, original pass | Validated metric frames |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

![Frozen-point attrition by outcome](figures/u5_primary_feasibility_attrition.png)

The [print-ready figure](figures/u5_primary_feasibility_attrition.pdf) is generated from the same source-hashed result. A six-ID run is still a detector milestone, not a validated court trajectory.

All **18/18** points show six near-side teammates at a source-reviewed instant; **15/18** had one locally correct six-box frame in the original detector pass. A higher-resolution, lower-threshold [source-checked recovery pass](../data/matches/yt_u5HnY2aNW14/screening/zero_run_high_res_source_qc.json) adds one correct instant in set-one point 18 and one in set-two point 14, bringing local six-box availability to **17/18** across tested settings. Set-three point 23 remains source-visible but its proposal boxes duplicate or merge overlapping players. None of the three has a recovered six-player trajectory. Longer six-ID runs occur in **7/18** points, all near-team losses. Source review finds correct team membership in 53 sampled frames across those seven longer runs, but only one run has named jersey continuity checked. Correct short winning runs cover five points; set-three point 33 has a rejected wrong-team run and a separate locally correct single frame.

A separate higher-resolution point-local tracking pass finds a [13-sample six-ID run in set-three point 13](../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_source_qc.json), a near-team win. Source review finds the same six UCLA teammates at all 13 sampled instants. The first five (0.8 s between first and last) appear active; later frames may include point-end movement. Across tested settings, this raises the number of points with at least five six-ID samples to **8/18: one win and seven losses**. Neither the early source phase nor the box-bottom floor positions are certified for final metric use. The one winning interval does not create a balanced rally-level outcome dataset.

The [eight-run motion diagnostic](HONOURS_U5_RUN_MOTION_DIAGNOSTIC.md) calculates the three implemented formulas on **66 sampled box-bottom proxy frames**, with no winner effect estimated. The winning run includes an airborne player in its early source frames, so its raw box bottoms cannot all be treated as grounded court coordinates. These diagnostic calculations contribute **zero validated metric frames**.

The [image-plane trajectory atlas](HONOURS_U5_RUN_TRAJECTORY_ATLAS.md) traces all six raw-ID box centres in the same 66 source-checked sampled instances, including the airborne player. It shows sampled image motion and the near-court outline, but most raw IDs have not been matched to named jerseys over unsampled frames. One of the eight longer runs, set-one point 34, has a serve/reset snapshot anchor; the other seven have open-play snapshot anchors, but their entire spans are not phase-certified. The only winning run uses the higher-resolution detector. The atlas is a reproducible tracking diagnostic, not six validated court trajectories.

A [short optical-flow pilot](HONOURS_U5_BOX_CENTRE_FLOW_PILOT.md) translates six reviewed source boxes through ±0.4 s around each of 17 anchors. It produces six image-plane candidates at all five 5 Hz samples for all 17. In 334 same-raw-ID comparisons, the median flow-to-detector centre difference is 5.10 px; this is correlated pipeline agreement, not independent accuracy. Source endpoint review finds 13 windows without an obvious wrong-person transfer and four with unresolved crossings or net overlap. After serve/reset and set-by-phase balancing, eight short windows remain candidate comparisons. None has manually certified named-player identity at every sample or validated court-floor positions, so the strict result remains zero.

A [five-sample image-plane geometry diagnostic](HONOURS_U5_FLOW_WINDOW_GEOMETRY.md) calculates the three spacing and spread formulas across those eight candidate windows (four wins, four losses). Its within-set-and-phase descriptive contrasts use pixel units and are sensitive to the sample time. The windows remain selected by box availability, and their intermediate identities and floor positions are not certified. These calculations do not establish a statistical winner association or meet the court-metric requirement.

A [five-instant source-image review](HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) inspected all eight candidate windows at their five displayed instants. No obvious wrong-person transfer was seen in these 40 displayed instances. This is a coarse visual screen: unsampled source frames, box-centre accuracy, named identities and court-floor positions remain unvalidated. One window has a player outside the sideline, and another has a low posture near the net. The strict court-trajectory result remains zero.

A [one-point deletion audit](HONOURS_U5_FLOW_WINDOW_SENSITIVITY.md) shows that the descriptive pixel contrasts change substantially with selected-point removal: spacing ranges from +12.306 to +59.268 px, hull area from -14588.302 to -1744.800 px², and dispersion from +8.252 to +40.070 px. Deleting the set-two winning window removes that entire matched phase cell. These ranges are selection checks, not uncertainty intervals or court-metric effects.

A [fixed-box court-position proxy pilot](HONOURS_U5_FIXED_BOX_COURT_PROXY.md) now operationalizes the proposed research-prototype measurement: each anchor box retains its size, optical flow translates its centre and bottom point, and the bottom point is mapped through the staged 9 m homography. It yields 240 approximate court-position proxies across 40 sampled team frames in eight short windows. The three planned geometry formulas run on those positions, with one-point deletion and observed-error perturbation checks. These are reported as exploratory approximate-court results. The 30 clear-shoe reference pairs measure related static box-bottom error; dynamic propagated floor accuracy, rotation, and comparable full-rally trajectories remain unresolved.

The same pilot also measures short-window proxy movement: median player first-to-last chord and sampled polyline length. Equal-cell winning-minus-losing differences are -0.069 m and -0.075 m, respectively; the one-point deletion range for the sampled polyline spans zero. These are movement of the **estimated box-floor points**, not counted steps, actual foot travel, or a transition-speed effect.

A [direct anchor-reference audit](HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md) matches 16 of the new pilot player points to existing manual clear-shoe marks on three source frames. Two frames contain all six marked teammates, allowing direct team-metric discrepancy calculations. The median matched player-position difference is 0.277 m and the maximum is 0.632 m. This reuses the existing single-reviewer reference; it does not validate propagated positions away from the anchor.

A [non-anchor manual audit](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) checks selected fixed-box positions 12 frames away from each anchor. Eleven clear grounded shoe pairs could be marked across all eight windows; five selected slots remain missing because the shoes or contact were uncertain. The median mapped difference is 0.216 m and the largest is 0.729 m, above the earlier static maximum. A [revised error scenario](HONOURS_U5_DYNAMIC_ERROR_SENSITIVITY.md) perturbs the 240 proxies using the new observed maximum. Spacing and dispersion contrasts cross zero in those draws; hull area remains negative in the simulated draws, which does not establish a winner effect.

The [one-frame full-team non-anchor check](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) adds four manual marks to two of the above marks at set-three point 13, frame 29952. All six selected near-side players have an approximate shoe midpoint there. Median player-position discrepancy is 0.468 m; fixed-box minus manual team spacing is +0.431 m, hull area +4.190 m² and dispersion +0.308 m. This single selected clear frame does not validate the other instants of that window, full rallies or the outcome contrast.

An earlier [core-only coverage export](HONOURS_U5_SELECTED_CLIP_COURT_COVERAGE.md) records every 5 Hz grid instant within all 18 frozen point clips. Across 1,005 grid instants, 370 were not part of that saved dense screen, 421 had fewer than six near-side candidates, 206 had exactly six raw box-bottom court candidates, and eight had more than six ambiguous candidates. The export retains these states and the available coordinates without inventing missing players. These 206 candidate frames are not validated six-player positions or certified live rallies; the strict metric count remains zero.

A subsequent [full-clip tracking pass](HONOURS_U5_FULL_CLIP_TRACKLET_AUDIT.md) screens all 1,005 grid instants after resetting ByteTrack at each edited clip. It finds 348 exactly-six near-side geometric candidate frames and 479 contiguous raw-ID tracklet segments. Seventeen clips contain at least five consecutive samples with the same six raw IDs somewhere in the full edit, but only ten do so within the conservative core. These counts use a different tracker start from the earlier core-only export, so the two candidate totals and raw IDs are separate diagnostics. The [candidate-path figure](figures/u5_full_clip_candidate_six_runs.png) shows the longest six-ID run in each clip. A [bounded source-frame spot check](HONOURS_U5_FULL_CLIP_SPOTCHECK.md) finds no obvious transfer at the first, middle and last frames of the two longest runs. White #28 in set-three point 34 is the near-side libero, not a far-side opponent. The intervening frames, exact live phase and grounded court positions remain unchecked; no full-rally six-person court trajectory has been validated from this pass.

An [expanded every-sample identity review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) checks all 18 sampled frames and six player crops in each of those two runs: 36 team frames and 216 person crops. Each raw ID stays with the same visible UCLA jersey at the sampled instants, with no obvious sampled identity switch. Five source frames between each pair of 5 Hz samples remain unchecked. A [direct in-run position comparison](HONOURS_U5_FULL_RUN_POSITION_REFERENCE.md) reuses two manual clear-shoe marks at set-three point 34 frame 36084; the current box-bottom discrepancies are 0.216 m and 0.523 m. These selected single-frame errors show that correct jersey identity does not imply exact court position. The full-rally trajectory gate remains open.

A separate [30 fps screen of both long runs](HONOURS_U5_TWO_RUNS_30FPS_AUDIT.md) checks every decoded source frame inside their 103-frame spans. Set-one point 5 has six near-side candidates with the same raw IDs in 103/103 frames. Set-three point 34 has six in 93/103 frames, with ten temporary missing detections affecting UCLA #7 and #21; the same ID values reappear, and no new near-side raw ID is introduced. Source-image review finds those missing teammates visible but unboxed at all ten frames. This dense raw-ID pass does not provide a human jersey check at every frame, and the missing positions are left blank rather than held still. Neither span has a certified exact live-rally boundary or complete grounded-position reference.

An [extended full-rally validation audit](HONOURS_U5_FULL_RALLY_TRAJECTORY_VALIDATION.md) screens source frames through reviewed point-end brackets. From each conservative live start through the last reviewed live frame, the original six raw IDs all have boxes in 63/108 frames at S1 P5 and 96/138 frames at S3 P34. These intervals do not certify exact serve or dead-ball frames. A later [S3 P34 source review](HONOURS_U5_S3P34_SOURCE_VALIDATION_PROGRESS.md) corrects UCLA #7's late tracker change from ID 9 to ID 78, excludes a far-side ID 39, and keeps airborne or missing positions null. Eleven of 24 sampled 5 Hz frames have exploratory six-grounded-player proxy metrics. Five [six-player manual shoe reference frames](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md) distributed through S3 P34 have 0.298 m median box-bottom discrepancy across 30 positions and 0.595 m maximum; three added frames are unblinded single-reviewer checks. The evidence remains insufficient to validate a complete six-player court trajectory or final metric input.

A [same-set matched-window pilot](HONOURS_U5_MATCHED_WINDOW_PILOT.md) then compared one winning and one losing point over equal 0.8 s sample spans. All displayed frames have six screen-space box-centre candidates, including airborne frames. The fixed first-run windows failed phase matching for an outcome comparison. A revised opponent-attack candidate improved phase similarity but was selected after inspecting source phases, and one point per outcome is insufficient for a reliable association. Neither attempt certified six-player floor anchors for metre-valued court metrics. **Neither attempt produced an eligible outcome-analysis window.**

An [18-point image-plane snapshot screen](HONOURS_U5_IMAGE_PLANE_SNAPSHOT_SCREEN.md) calculates box-centre geometry for 17 locally reviewed six-player frames, including the two higher-resolution recoveries. One winning point remains missing. An [exact-frame source phase audit](HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md) identifies eight near-side defensive frames, seven offensive frames, and two serve/reset frames. Only 13/18 frozen points fall in open-play set-by-phase cells with both outcomes; each cell has at most two snapshots per outcome. The original 15-frame and augmented 17-frame within-set contrasts are descriptive sensitivity checks selected by box availability. No significance test or court-metric outcome effect is inferred from these pixel values.

An [exploratory phase-matched court-proxy calculation](HONOURS_U5_PHASE_MATCHED_PROXY.md) projects box bottoms for those 13 single frames through the staged 9 m transform. Across five set-and-phase cells, the equal-cell mean win-minus-loss spacing is +0.104 m, hull area +0.309 m^2 and dispersion +0.032 m. Removing the one matched high-resolution recovery reverses all three signs; perturbing each proxy by up to the largest observed clear-shoe discrepancy also spans zero for each metric. These data are selected snapshots, not validated trajectories or a reliable statistical winner association. The strict court-metric result remains zero.

Static floor-image registration succeeds on **{result['summary']['camera_registered_review_frames']}** reviewed frames across all 18 points, with at most 0.293 px fitted landmark displacement. A 30-box clear-shoe reference finds a largest observed box-bottom to shoe-midpoint discrepancy of **{result['summary']['largest_observed_box_to_shoe_discrepancy_m']:.3f} m**; this is not a validated bound and excludes unclear contacts. The [snapshot sensitivity audit](../data/matches/yt_u5HnY2aNW14/screening/selected_proxy_sensitivity.json) probes the resulting metric instability, but its winner medians are selected single frames and are not outcome estimates.

## Decision under the signed question

The strict six-player court-metric input has **0 validated frames and 0 validated rallies or fixed analysis windows**. Thus the prespecified within-set outcome association is **not estimable**. This is missing measurement evidence, not evidence of no association. The edited clip cuts and conservative live-looking interiors remain navigation boundaries; exact events, continuous six-person identity and grounded positions are unverified. Camera-image stability alone cannot clear those gates.

The reproducible contribution now includes score-balanced selection, source-visible roster accounting, detector attrition by outcome, stable image registration, a bounded shoe-proxy discrepancy check, three implemented metric formulas and explicit exclusion of unsupported inference. The signed contract's validated trajectories and outcome comparison remain outstanding. A feasibility-focused thesis would require the academic scope decision described in [the decision draft](HONOURS_SCOPE_DECISION_DRAFT.md).

## Reproduction

```powershell
.\\.venv\\Scripts\\python.exe scripts/build_u5_primary_feasibility_result.py
.\\.venv\\Scripts\\python.exe scripts/plot_u5_primary_feasibility.py
```
'''
    OUT_MD.write_text(report, encoding='utf-8')
    print(f'Wrote {OUT_MD.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
