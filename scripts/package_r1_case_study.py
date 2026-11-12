"""Bind the bounded r1 case-study readout to its local source and evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
FILES = (
    "data/matches/yt_FqE5pTJqx8g/source_record.json",
    "data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r1.json",
    "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json",
    "data/matches/yt_FqE5pTJqx8g/pilot/calibration/calibration_manifest.json",
    "data/processed/fqe_r1_boundary_recheck/REVIEW.json",
    "data/processed/fqe_r1_boundary_recheck/R1_CASE_STUDY_CANDIDATE.json",
    "data/processed/fqe_r1_boundary_recheck/r1_dense_raw_tracks.json",
    "data/processed/fqe_r1_boundary_recheck/r1_dense_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_anchor_path_estimate.json",
    "data/processed/fqe_r1_boundary_recheck/r1_d79_hold_policy_transfer.json",
    "data/processed/fqe_r1_boundary_recheck/r1_player9_zone_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_player20_zone_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_handoff_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_player13_handoff_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_p13_distance_gate.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_p13_anchor_feasibility.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_distance_gate_source_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p13_distance_gate_source_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/p13_foot_21316_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/p11_foot_21413_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/p11_foot_21419_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/p11_foot_21463_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/r1_remaining_identity_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_floor_feasibility_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_six_slot_visual_candidate.json",
    "data/processed/fqe_r1_boundary_recheck/r1_user_visual_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_floor_contact_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_saved_floor_contact_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_saved_floor_contacts_21064.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_net_contact_line_check.json",
    "data/processed/fqe_r1_boundary_recheck/r1_net_contact_line_check.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_sole_detail_21064.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_near_net_midpoint_proposals_21064.json",
    "data/processed/fqe_r1_boundary_recheck/r1_near_net_midpoint_proposals_21064.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p9_grounded_sample_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p9_floor_anchor_review_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p9_contact_checks.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p9_contact_check_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p9_contact_check_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p9_contact_check_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_contact_checks.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_contact_check_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_contact_check_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_contact_check_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_contact_check_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_checks.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_check_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_check_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_check_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_check_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_box_center_hybrid_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_jump_contact_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_prejump_gap_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p12_foot_21343_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/p12_second_gap_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/p12_21423_21436_gap_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/p12_foot_21339.png",
    "data/processed/fqe_r1_boundary_recheck/p12_foot_21423_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/p12_foot_21436_zoom.png",
    "data/processed/fqe_r1_boundary_recheck/p12_foot_21441.png",
    "data/processed/fqe_r1_boundary_recheck/p12_foot_21463.png",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_gap_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_gap_source_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_full_gap_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_full_gap_source_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_full_gap_source_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_full_gap_source_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_seeded_shoe_experiment.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_seeded_shoe_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_seeded_shoe_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_seeded_shoe_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_color_shoe_experiment.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_color_shoe_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_color_shoe_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_color_shoe_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_shoe_anchored_box_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_shoe_anchored_box_review.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_white_shoe_experiment.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_white_shoe_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_white_shoe_sheet_11.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_white_shoe_sheet_14.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_two_shoe_exclusive_experiment.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_two_shoe_exclusive_sheet_7.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_two_shoe_guarded_experiment.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_two_shoe_guarded_sheet_7.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_body_shoe_contact_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_body_shoe_contact_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_body_shoe_contact_sheet_7.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_body_shoe_contact_sheet_11.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_body_shoe_contact_sheet_14.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_identity_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_identity_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_identity_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_identity_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_identity_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_sheet_5.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_21402_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_21402_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_21402_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_local_reseed_21402_sheet_5.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_stationary_shoe_cue_audit.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_stationary_shoe_cue_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_stationary_shoe_cue_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_pose_ankle_association_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_pose_ankle_association_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_breakpoint_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_breakpoint_1_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_breakpoint_2_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_breakpoint_3_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_breakpoint_3_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_late_contact_anchor_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_late_contact_anchor_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_late_contact_anchor_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_late_contact_anchor_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_contact_ambiguity_recheck.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_late_anchor_path_consistency.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_level_center_distance_trial.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p20_foot_level_center_path.png",
    "data/processed/fqe_r1_boundary_recheck/r1_point_summary.json",
    "data/processed/fqe_r1_boundary_recheck/r1_six_player_proxy_scenario.json",
    "data/processed/fqe_r1_boundary_recheck/r1_occlusion_display_holds.json",
    "data/processed/fqe_r1_boundary_recheck/r1_occlusion_hold_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_occlusion_hold_source_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_occlusion_hold_source_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_occlusion_hold_source_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_missing_run_endpoint_diagnostic.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_5.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_6.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_long_gap_source_sheet_7.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_short_gap_source_review.json",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_short_gap_source_sheet_1.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_short_gap_source_sheet_2.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_short_gap_source_sheet_3.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_short_gap_source_sheet_4.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_short_gap_source_sheet_5.jpg",
    "data/processed/fqe_r1_end_to_end_pilot/metadata.json",
    "data/processed/fqe_r1_end_to_end_pilot/metrics.json",
    "data/processed/fqe_r1_end_to_end_pilot/processing_diagnostics.json",
    "data/processed/fqe_r1_end_to_end_pilot/tracks_centroids.csv",
    "data/processed/fqe_r1_end_to_end_pilot/AUDIT.json",
    "data/processed/fqe_r1_end_to_end_pilot/NAMED_CANDIDATE_COVERAGE.json",
    "data/processed/fqe_r1_end_to_end_pilot/source_overlay_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/focused_review/RESULT.json",
    "data/processed/fqe_r1_boundary_recheck/r1_contact_floor_evidence.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_calibration_live_overlay.jpg",
    "data/processed/fqe_r1_boundary_recheck/p9_ground_proxy_review_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player9_zone_audit.png",
    "data/processed/fqe_r1_boundary_recheck/r1_player20_zone_audit.png",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_all_21088_21098.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_all_21213_21235.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_all_21239_21244.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_all_21311_21311.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_all_21394_21397.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player12_gap_all_21451_21451.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_player13_late_handoff_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_early_identity_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p10_later_identity_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_middle_identity_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_p11_later_identity_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_endpoint_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_p9_landing_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_p13_overlap_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_block_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_p20_box_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_p12_motion_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_validation_late_left_source.jpg",
    "data/processed/fqe_r1_boundary_recheck/r1_visual_candidate_preview.mp4",
    "data/processed/fqe_r1_boundary_recheck/r1_visual_candidate_review_sheet.jpg",
    "data/processed/fqe_r1_boundary_recheck/R1_DENSE_REVIEW.md",
    "DELIVERABLES/R1_CASE_STUDY_READOUT.md",
    "DELIVERABLES/R1_POINT_SUMMARY.md",
    "DELIVERABLES/R1_D79_POLICY_TRANSFER.md",
    "DELIVERABLES/R1_END_TO_END_PILOT.md",
    "DELIVERABLES/R1_VALIDATION_QUEUE.md",
    "web/r1_case_study.html",
    "web/r1_case_study.js",
    "services/api/pilot_review.py",
    "scripts/audit_r1_player12_handoffs.py",
    "scripts/review_r1_player12_gaps.py",
    "scripts/audit_r1_player13_handoff.py",
    "scripts/audit_r1_player20_zones.py",
    "scripts/audit_r1_zone_occupancy.py",
    "scripts/audit_r1_remaining_identities.py",
    "scripts/review_r1_validation_queue.py",
    "scripts/render_r1_visual_candidate.py",
    "scripts/audit_r1_floor_contact_draft.py",
    "scripts/audit_r1_net_contact_alignment.py",
    "scripts/review_r1_near_net_shoes.py",
    "scripts/review_r1_p9_grounded_samples.py",
    "scripts/review_r1_p9_contact_checks.py",
    "scripts/review_r1_p20_contact_checks.py",
    "scripts/review_r1_p12_contact_checks.py",
    "scripts/review_r1_p10_gap_source.py",
    "scripts/review_r1_p10_full_gap.py",
    "scripts/experiment_r1_seeded_shoe.py",
    "scripts/experiment_r1_color_shoe.py",
    "scripts/review_r1_shoe_anchored_box.py",
    "scripts/experiment_r1_white_shoe.py",
    "scripts/experiment_r1_two_shoes.py",
    "scripts/experiment_r1_body_shoe_contacts.py",
    "scripts/experiment_r1_p20_foot_identity.py",
    "scripts/experiment_r1_p20_local_reseed.py",
    "scripts/audit_r1_p20_stationary_shoe_cues.py",
    "scripts/evaluate_r1_p20_pose_ankles.py",
    "scripts/review_r1_p20_breakpoints.py",
    "scripts/review_r1_p20_contact_anchors.py",
    "scripts/audit_r1_p20_anchor_path_consistency.py",
    "scripts/estimate_r1_p20_foot_level_center.py",
    "scripts/build_r1_point_summary.py",
    "scripts/trial_r1_p12_box_center_hybrid.py",
    "scripts/transfer_d79_hold_policy_to_r1.py",
    "scripts/audit_r1_p11_p13_distance_gate.py",
    "scripts/build_r1_six_player_proxy_scenario.py",
    "services/inference/seeded_shoe_tracker.py",
    "scripts/build_r1_occlusion_display_holds.py",
    "scripts/review_r1_occlusion_display_holds.py",
    "scripts/audit_r1_missing_run_endpoints.py",
    "scripts/review_r1_p11_long_gaps.py",
    "scripts/review_r1_p11_short_gaps.py",
    "tests/test_r1_occlusion_display_holds.py",
    "tests/test_pilot_review.py",
    "scripts/run_r1_end_to_end_pilot.py",
    "scripts/audit_r1_end_to_end_pilot.py",
    "scripts/audit_r1_named_candidate_coverage.py",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main():
    candidate = json.loads((BASE / "R1_CASE_STUDY_CANDIDATE.json").read_text(encoding="utf-8"))
    p12 = json.loads((BASE / "r1_player12_handoff_audit.json").read_text(encoding="utf-8"))
    gaps = json.loads((BASE / "r1_player12_gap_source_review.json").read_text(encoding="utf-8"))
    p13 = json.loads((BASE / "r1_player13_handoff_audit.json").read_text(encoding="utf-8"))
    p9 = json.loads((BASE / "r1_player9_zone_audit.json").read_text(encoding="utf-8"))
    p20 = json.loads((BASE / "r1_player20_zone_audit.json").read_text(encoding="utf-8"))
    visual = json.loads((BASE / "r1_six_slot_visual_candidate.json").read_text(encoding="utf-8"))
    floor_review = json.loads((BASE / "r1_floor_contact_review.json").read_text(encoding="utf-8"))
    floor_audit = json.loads((BASE / "r1_saved_floor_contact_audit.json").read_text(encoding="utf-8"))
    net_line_check = json.loads((BASE / "r1_net_contact_line_check.json").read_text(encoding="utf-8"))
    near_net_proposals = json.loads((BASE / "r1_near_net_midpoint_proposals_21064.json").read_text(encoding="utf-8"))
    p9_grounded = json.loads((BASE / "r1_p9_grounded_sample_review.json").read_text(encoding="utf-8"))
    p9_contacts = json.loads((BASE / "r1_p9_contact_checks.json").read_text(encoding="utf-8"))
    p20_contacts = json.loads((BASE / "r1_p20_contact_checks.json").read_text(encoding="utf-8"))
    p12_contacts = json.loads((BASE / "r1_p12_contact_checks.json").read_text(encoding="utf-8"))
    p10_gap = json.loads((BASE / "r1_p10_gap_source_review.json").read_text(encoding="utf-8"))
    p10_full_gap = json.loads((BASE / "r1_p10_full_gap_source_review.json").read_text(encoding="utf-8"))
    shoe_template = json.loads((BASE / "r1_p10_seeded_shoe_experiment.json").read_text(encoding="utf-8"))
    shoe_colour = json.loads((BASE / "r1_p10_color_shoe_experiment.json").read_text(encoding="utf-8"))
    shoe_box = json.loads((BASE / "r1_p10_shoe_anchored_box_review.json").read_text(encoding="utf-8"))
    white_shoe = json.loads((BASE / "r1_p20_white_shoe_experiment.json").read_text(encoding="utf-8"))
    two_shoe = json.loads((BASE / "r1_p20_two_shoe_exclusive_experiment.json").read_text(encoding="utf-8"))
    guarded_shoe = json.loads((BASE / "r1_p20_two_shoe_guarded_experiment.json").read_text(encoding="utf-8"))
    body_shoe = json.loads((BASE / "r1_p20_body_shoe_contact_trial.json").read_text(encoding="utf-8"))
    foot_identity = json.loads((BASE / "r1_p20_foot_identity_trial.json").read_text(encoding="utf-8"))
    local_21343 = json.loads((BASE / "r1_p20_local_reseed_trial.json").read_text(encoding="utf-8"))
    local_21402 = json.loads((BASE / "r1_p20_local_reseed_21402_trial.json").read_text(encoding="utf-8"))
    stationary_shoe = json.loads((BASE / "r1_p20_stationary_shoe_cue_audit.json").read_text(encoding="utf-8"))
    pose_ankles = json.loads((BASE / "r1_p20_pose_ankle_association_trial.json").read_text(encoding="utf-8"))
    breakpoint_review = json.loads((BASE / "r1_p20_breakpoint_source_review.json").read_text(encoding="utf-8"))
    late_contacts = json.loads((BASE / "r1_p20_late_contact_anchor_review.json").read_text(encoding="utf-8"))
    anchor_path = json.loads((BASE / "r1_p20_late_anchor_path_consistency.json").read_text(encoding="utf-8"))
    foot_centre = json.loads((BASE / "r1_p20_foot_level_center_distance_trial.json").read_text(encoding="utf-8"))
    point_summary = json.loads((BASE / "r1_point_summary.json").read_text(encoding="utf-8"))
    team_scenario = json.loads((BASE / "r1_six_player_proxy_scenario.json").read_text(encoding="utf-8"))
    display_holds = json.loads((BASE / "r1_occlusion_display_holds.json").read_text(encoding="utf-8"))
    hold_source_review = json.loads((BASE / "r1_occlusion_hold_source_review.json").read_text(encoding="utf-8"))
    missing_endpoints = json.loads((BASE / "r1_missing_run_endpoint_diagnostic.json").read_text(encoding="utf-8"))
    p11_gap = json.loads((BASE / "r1_p11_long_gap_source_review.json").read_text(encoding="utf-8"))
    p11_short_gap = json.loads((BASE / "r1_p11_short_gap_source_review.json").read_text(encoding="utf-8"))
    api_pilot = json.loads((ROOT / "data/processed/fqe_r1_end_to_end_pilot/metrics.json").read_text(encoding="utf-8"))
    api_audit = json.loads((ROOT / "data/processed/fqe_r1_end_to_end_pilot/AUDIT.json").read_text(encoding="utf-8"))
    named_coverage = json.loads((ROOT / "data/processed/fqe_r1_end_to_end_pilot/NAMED_CANDIDATE_COVERAGE.json").read_text(encoding="utf-8"))
    assert candidate["candidate_interval"]["end_frame_exclusive"]-candidate["candidate_interval"]["start_frame"] == 414
    assert p12["full_candidate_coverage"]["raw_target_box_frames"] == 368
    assert p12["full_candidate_coverage"]["missing_target_box_frames"] == gaps["reviewed_gap_frames"] == 46
    assert p12["full_candidate_coverage"]["missing_runs_inclusive"] == [row["frames_inclusive"] for row in gaps["gaps"]]
    assert p13["union_coverage_frames"] == 108
    assert sum(p9["counts"].values()) == 394
    assert sum(p20["counts"].values()) == 364
    assert len(visual["frame_records"]) == 414
    assert {player: row["raw_box_candidate"] for player, row in visual["slot_counts"].items()} == {
        "9": 414, "10": 380, "11": 311, "12": 368, "13": 142, "20": 410}
    assert all(sum(row.values()) == 414 for row in visual["slot_counts"].values())
    assert floor_audit["review_sha256"] == sha256(BASE / "r1_floor_contact_review.json")
    assert floor_audit["saved_frame_count"] == len(floor_review["records"])
    assert floor_audit["saved_player_frame_count"] == sum(len(players) for players in floor_review["records"].values())
    assert net_line_check["review_sha256"] == sha256(BASE / "r1_floor_contact_review.json")
    assert net_line_check["calibration_manifest_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/calibration_manifest.json")
    assert near_net_proposals["saved_review_sha256"] == sha256(BASE / "r1_floor_contact_review.json")
    assert near_net_proposals["calibration_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json")
    assert p9_grounded["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p9_grounded["anchor_path_sha256"] == sha256(BASE / "r1_anchor_path_estimate.json")
    assert p9_contacts["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p9_contacts["calibration_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json")
    assert p9_contacts["sampled_diagnostics"]["reviewed_grounded_frames"] == 11
    assert p20_contacts["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p20_contacts["calibration_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json")
    assert p20_contacts["sampled_diagnostics"]["invalid_box_frames_with_visible_contact"] == [21310]
    assert p12_contacts["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p12_contacts["calibration_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json")
    assert p12_contacts["sampled_diagnostics"]["uncertain_state_count"] == 7
    assert p10_gap["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p10_gap["calibration_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json")
    assert p10_gap["detector_gap_frames_inclusive"] == [21099, 21132]
    assert [row["candidate_box_status"] for row in p10_gap["rows"]] == [
        "raw_box_candidate", "missing", "missing", "missing", "raw_box_candidate"]
    assert p10_full_gap["source_sha256"] == sha256(SOURCE)
    assert p10_full_gap["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p10_full_gap["status"] == "source_gap_review_complete"
    assert p10_full_gap["review_summary"]["missing_frames_reviewed"] == 34
    assert {row["frame"] for row in p10_full_gap["frames"]
            if row["candidate_box_status"] == "missing"} == {
                row["frame"] for row in visual["frame_records"]
                if row["players"]["10"]["box_status"] == "missing"}
    assert all(row["identity_state"] == "blue_10_visible" and row["floor_point_px"] is None
               and row["court_position_m"] is None for row in p10_full_gap["frames"])
    assert shoe_template["source_sha256"] == shoe_colour["source_sha256"] == sha256(SOURCE)
    assert shoe_template["visual_candidate_sha256"] == shoe_colour["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert sum(row["shoe_template_centre_px"] is not None for row in shoe_template["frames"]) == 11
    assert shoe_colour["review_summary"]["colour_candidate_frames"] == 35
    assert shoe_colour["review_summary"]["no_candidate_frames"] == [21133]
    assert shoe_colour["review_summary"]["suspect_component_steps"] == [21115]
    assert all(row["court_position_m"] is None and row["verified_floor_contact_px"] is None
               for row in shoe_template["frames"] + shoe_colour["frames"])
    assert shoe_box["source_sha256"] == sha256(SOURCE)
    assert shoe_box["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert shoe_box["colour_experiment_sha256"] == sha256(BASE / "r1_p10_color_shoe_experiment.json")
    assert shoe_box["diagnostics"]["candidate_box_frames_in_missing_run"] == 34
    assert shoe_box["diagnostics"]["suspect_component_jump_frames"] == [21115]
    assert shoe_box["diagnostics"]["last_colour_box_vs_reappeared_raw_box_iou_one_frame_later"] < 0.5
    assert all(row["court_position_m"] is None and row["verified_person_box_px"] is None
               for row in shoe_box["frames"])
    assert white_shoe["source_sha256"] == two_shoe["source_sha256"] == guarded_shoe["source_sha256"] == sha256(SOURCE)
    assert white_shoe["visual_candidate_sha256"] == two_shoe["visual_candidate_sha256"] == guarded_shoe["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert white_shoe["summary"]["candidate_frames"] == 164
    assert white_shoe["summary"]["unlike_contact_target_frames"] == [21420, 21463]
    assert two_shoe["summary"]["distinct_candidate_frames"] == 93
    assert 21372 in two_shoe["summary"]["outside_raw_box_frames_by_seed"]["image_right_airborne"]
    assert guarded_shoe["summary"]["distinct_candidate_frames"] == 5
    assert 21372 in guarded_shoe["summary"]["parent_box_rejection_frames"]
    assert all(row["body_midpoint_from_shoes_px"] is None and row["court_position_m"] is None
               for row in two_shoe["frames"] + guarded_shoe["frames"])
    assert body_shoe["source_sha256"] == sha256(SOURCE)
    assert body_shoe["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert body_shoe["summary"]["valid_parent_box_frames"] == 160
    assert body_shoe["summary"]["frames_with_one_or_more_selected_regions"] == 159
    assert body_shoe["summary"]["frames_with_two_selected_regions"] == 130
    assert body_shoe["summary"]["body_pair_rejection_frames"] == []
    assert body_shoe["summary"]["late_lunge_expanded_search_frames"] == list(range(21449, 21464))
    assert sum(value is not None for value in body_shoe["summary"]["analyst_sample_comparison_px"].values()) == 6
    assert all(row["verified_floor_contact_px"] is None and row["court_position_m"] is None
               for row in body_shoe["frames"])
    assert foot_identity["source_sha256"] == sha256(SOURCE)
    assert foot_identity["shoe_trial_sha256"] == sha256(BASE / "r1_p20_body_shoe_contact_trial.json")
    assert foot_identity["summary"]["identity_lost_at_frame"] == 21333
    assert foot_identity["summary"]["frames_with_both_assigned"] == 25
    assert foot_identity["summary"]["frames_with_one_assigned"] == 4
    assert all(row["body_midpoint_px"] is None and row["ground_contact_px"] is None
               and row["court_position_m"] is None for row in foot_identity["frames"])
    assert all(all(point is None for point in row["feet"].values())
               for row in foot_identity["frames"] if row["frame"] >= 21333)
    for local, seed, lost, both in ((local_21343, 21343, 21393, 47),
                                    (local_21402, 21402, None, 56)):
        assert local["source_sha256"] == sha256(SOURCE)
        assert local["shoe_trial_sha256"] == sha256(BASE / "r1_p20_body_shoe_contact_trial.json")
        assert local["local_seed_frame"] == seed
        assert local["relationship_to_frame_21300_seed_feet"] == "unknown"
        assert local["summary"]["identity_lost_at_frame"] == lost
        assert local["summary"]["frames_with_both_assigned"] == both
        assert all(row["ground_contact_px"] is None and row["court_position_m"] is None
                   for row in local["frames"])
        if lost is not None:
            assert all(all(point is None for point in row["feet"].values())
                       for row in local["frames"] if row["frame"] >= lost)
    assert stationary_shoe["source_sha256"] == sha256(SOURCE)
    assert stationary_shoe["contact_anchor_sha256"] == sha256(BASE / "r1_p20_late_contact_anchor_review.json")
    assert all(stationary_shoe["segment_sha256"][name] == sha256(BASE / name)
               for name in stationary_shoe["segment_sha256"])
    assert stationary_shoe["summary"]["anchor_frames_with_stationary_shoe_cue"] == 7
    assert stationary_shoe["summary"]["uncertain_21440_has_stationary_cue"] is False
    assert next(row for row in stationary_shoe["anchor_comparison"]
                if row["frame"] == 21430)["nearest_stationary_cue_to_analyst_point_px"] > 90
    assert stationary_shoe["production_metric_changed"] is False
    assert pose_ankles["source_sha256"] == sha256(SOURCE)
    assert pose_ankles["shoe_trial_sha256"] == sha256(BASE / "r1_p20_body_shoe_contact_trial.json")
    assert pose_ankles["pose_model_sha256"] == sha256(ROOT / "yolov8n-pose.pt")
    assert pose_ankles["summary"]["pose_box_matched"] == 8
    assert pose_ankles["summary"]["distinct_shoe_association_frames"] == [21402, 21420, 21430, 21440]
    assert pose_ankles["summary"]["two_region_ambiguous_association_frames"] == [21300, 21343, 21390]
    assert all(row["ground_contact_px"] is None and row["court_position_m"] is None
               for row in pose_ankles["observations"])
    assert breakpoint_review["source_sha256"] == sha256(SOURCE)
    assert breakpoint_review["shoe_trial_sha256"] == sha256(BASE / "r1_p20_body_shoe_contact_trial.json")
    assert breakpoint_review["contact_anchor_sha256"] == sha256(BASE / "r1_p20_late_contact_anchor_review.json")
    assert breakpoint_review["summary"]["frames"] == breakpoint_review["summary"]["reviewed_states"] == 37
    assert breakpoint_review["summary"]["late_visible_frames_with_fewer_than_two_colour_regions"] == 0
    assert breakpoint_review["summary"]["with_ground_contact"] == 0
    assert all(row["visual_state"] != "pending_source_review" and row["court_position_m"] is None
               for row in breakpoint_review["frames"])
    assert late_contacts["source_sha256"] == sha256(SOURCE)
    assert late_contacts["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert late_contacts["shoe_trial_sha256"] == sha256(BASE / "r1_p20_body_shoe_contact_trial.json")
    assert late_contacts["existing_contact_review_sha256"] == sha256(BASE / "r1_p20_contact_checks.json")
    assert late_contacts["summary"] == {"sampled_frames": 18, "contact_proposals": 17,
                                        "uncertain_frames": [21440], "new_proposals": 11}
    assert late_contacts["dense_path_gate"]["distance_released"] is False
    assert anchor_path["source_sha256"] == sha256(SOURCE)
    assert anchor_path["contact_anchor_sha256"] == sha256(BASE / "r1_p20_late_contact_anchor_review.json")
    assert anchor_path["review_summary"]["large_disagreement_intervals"] == [
        [21380, 21390], [21390, 21400], [21410, 21420], [21460, 21463]]
    assert anchor_path["distance_released"] is False
    assert foot_centre["source_sha256"] == sha256(SOURCE)
    assert foot_centre["shoe_trial_sha256"] == sha256(BASE / "r1_p20_body_shoe_contact_trial.json")
    assert foot_centre["contact_anchor_sha256"] == sha256(BASE / "r1_p20_late_contact_anchor_review.json")
    assert foot_centre["method_counts"] == {"box_bottom_center": 280,
                                             "missing_parent_box": 4,
                                             "two_shoe_horizontal_midpoint_lower_shoe_height": 130}
    assert foot_centre["physical_distance_released"] is False
    assert foot_centre["single_reviewer_contact_comparison"]["comparable_count"] == 16
    assert all(row["court_position_m_diagnostic"] is None
               for row in foot_centre["per_frame"] if row["method"] == "missing_parent_box")
    assert point_summary["source_sha256"] == sha256(SOURCE)
    assert point_summary["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert point_summary["foot_centre_sha256"] == sha256(BASE / "r1_p20_foot_level_center_distance_trial.json")
    assert point_summary["summary"]["all_six_usable_box_frames"] == 108
    assert point_summary["summary"]["valid_player_box_slots"] == 2025
    assert point_summary["summary"]["players_with_approximate_distance"] == ["9", "10", "12", "20"]
    assert point_summary["p12_hybrid_sha256"] == sha256(BASE / "r1_p12_box_center_hybrid_trial.json")
    assert point_summary["transfer_sha256"] == sha256(BASE / "r1_d79_hold_policy_transfer.json")
    assert point_summary["p10_gap_review_sha256"] == sha256(BASE / "r1_p10_gap_source_review.json")
    assert team_scenario["point_summary_sha256"] == sha256(BASE / "r1_point_summary.json")
    assert team_scenario["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert team_scenario["displayed_six_player_sum_m"] == 65.9
    assert team_scenario["physical_team_distance_released"] is False
    assert display_holds["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert display_holds["hold_player_frame_count"] == 92
    assert display_holds["thresholds"]["max_hold_frames"] == 8
    assert all(held["bbox_px"] is None and held["court_position_m"] is None
               and held["hold_age_frames"] <= 8 and held["current_position_inferred"] is False
               for frame in display_holds["holds"].values() for held in frame.values())
    assert hold_source_review["hold_record_sha256"] == sha256(BASE / "r1_occlusion_display_holds.json")
    assert len(hold_source_review["samples"]) == 14
    assert all(row["source_state"] != "pending_source_review" for row in hold_source_review["samples"])
    assert missing_endpoints["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert missing_endpoints["calibration_sha256"] == sha256(
        ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json")
    assert next(row for row in missing_endpoints["players"]["11"]
                if row["missing_frames_inclusive"] == [21189, 21235])["both_proxy_endpoints_inside_nominal_court"] is False
    assert p11_gap["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p11_gap["source_sha256"] == sha256(SOURCE)
    assert p11_gap["status"] == "source_gap_review_complete"
    assert p11_gap["review_summary"]["missing_frames_reviewed"] == 80
    assert len(p11_gap["source_sheets"]) == 7
    assert all(row["identity_state"] == "blue_11_visible" and row["floor_point_px"] is None
               and row["court_position_m"] is None for row in p11_gap["frames"])
    assert p11_short_gap["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert p11_short_gap["source_sha256"] == sha256(SOURCE)
    assert p11_short_gap["status"] == "source_gap_review_complete"
    assert p11_short_gap["review_summary"]["missing_frames_reviewed"] == 23
    assert len(p11_short_gap["source_sheets"]) == 5
    assert all(row["identity_state"] == "blue_11_visible" and row["floor_point_px"] is None
               and row["court_position_m"] is None for row in p11_short_gap["frames"])
    all_missing_11 = {row["frame"] for row in visual["frame_records"]
                      if row["players"]["11"]["box_status"] == "missing"}
    reviewed_missing_11 = {row["frame"] for review in (p11_gap, p11_short_gap)
                           for row in review["frames"] if row["candidate_box_status"] == "missing"}
    assert all_missing_11 == reviewed_missing_11 and len(all_missing_11) == 103
    assert api_pilot["source_sha256"] == sha256(SOURCE)
    assert api_pilot["candidate_sha256"] == sha256(BASE / "R1_CASE_STUDY_CANDIDATE.json")
    assert api_pilot["per_rally"][0]["quality"]["frames_with_track_observations"] == 414
    assert api_pilot["per_rally"][0]["quality"]["team_identity_verified"] is False
    assert api_pilot["per_rally"][0]["quality"]["ground_positions_verified"] is False
    assert api_audit["frames_with_different_track_ids_or_counts"] == []
    assert api_audit["paired_observations"] == 8511
    assert api_audit["metrics_sha256"] == sha256(ROOT / "data/processed/fqe_r1_end_to_end_pilot/metrics.json")
    assert named_coverage["visual_candidate_sha256"] == sha256(BASE / "r1_six_slot_visual_candidate.json")
    assert named_coverage["api_tracks_sha256"] == sha256(ROOT / "data/processed/fqe_r1_end_to_end_pilot/tracks_centroids.csv")
    assert named_coverage["frames_by_valid_candidate_box_count"]["6"] == 108
    assert named_coverage["paired_candidate_boxes"] == 2025
    assert named_coverage["candidate_to_api_unmatched"] == []

    source_hash = sha256(SOURCE)
    expected = candidate["video_sha256_from_source_record"]
    if source_hash != expected:
        raise RuntimeError("Source video hash no longer matches the frozen candidate")
    hashes = {name: sha256(ROOT / name) for name in FILES}
    manifest = {
        "status": "bounded_development_case_study_complete_not_release",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1",
        "candidate_frames": [21050, 21464],
        "source_video": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_video_bytes": SOURCE.stat().st_size,
        "source_video_sha256_verified": source_hash,
        "evidence_sha256": hashes,
        "checks": {"candidate_frames": 414, "p12_scoped_box_frames": 368,
                   "p12_source_reviewed_gap_frames": 46,
                   "p13_local_handoff_frames": 108,
                   "p9_zone_frames": 394, "p20_zone_frames": 364,
                   "api_pilot_r1_frames_with_person_detections": 414,
                   "api_pilot_raw_person_observations": 8511,
                   "api_vs_frozen_track_mismatch_frames": 0,
                   "six_named_candidate_box_frames": 108,
                   "occlusion_display_hold_player_frames": 92,
                   "visual_candidate_boxes_by_player": {
                       player: row["raw_box_candidate"]
                       for player, row in visual["slot_counts"].items()},
                   "floor_review_snapshot": {
                       "saved_frames": floor_audit["saved_frame_count"],
                       "saved_player_frames": floor_audit["saved_player_frame_count"],
                       "players_with_two_or_more_reviewed_frames": floor_audit["players_with_two_or_more_reviewed_frames"]}},
        "production_metrics_released": False,
        "official_annotations_changed": False,
    }
    (BASE / "R1_CASE_STUDY_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(f"verified source SHA-256 and {len(hashes)} evidence files")


if __name__ == "__main__":
    main()
