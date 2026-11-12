"""Audit what S3 P34 evidence can support under the strict six-player gate.

This is a readiness report. It never writes an approved metric input or
changes the source annotations that require independent review.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
OBSERVATIONS = BASE / "s3p34_six_player_observation_ledger.json"
SAMPLED = BASE / "s3p34_reviewed_sample_ledger.json"
CALIBRATION = BASE / "near_court_candidate.json"
EVENTS = BASE / "full_rally_validation_frames/source_event_brackets.json"
IDENTITY = BASE / "s3p34_full_span_review/candidate_identity_source_review.json"
GROUND_SCORE = BASE / "s3p34_30fps_ground_review/single_reviewer_score.json"
GROUND_FORM = BASE / "s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv"
OUT = BASE / "s3p34_validation_readiness.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_VALIDATION_READINESS.md"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(numbers, stride):
    result = []
    for number in sorted(numbers):
        if result and number == result[-1][-1] + stride:
            result[-1].append(number)
        else:
            result.append([number])
    return result


def main():
    observations, sampled, calibration, events, identity, ground_score = (
        read(path) for path in (OBSERVATIONS, SAMPLED, CALIBRATION, EVENTS, IDENTITY, GROUND_SCORE)
    )
    assert ground_score["status"] == "single_reviewer_form_scored_not_strict_approval"
    assert ground_score["completed_sha256"] == sha(GROUND_FORM)
    assert ground_score["accepted_intervening_slots"] == 180
    assert ground_score["intervening_frames_with_six_accepted_slots"] == 30
    assert ground_score["strict_metric_approval"] is False
    frames = observations["frames"]
    assert observations["interval_inclusive"] == [36001, 36138]
    assert [frame["source_frame"] for frame in frames] == list(range(36001, 36139))
    assert observations["summary"]["unsampled_source_sequence_reviewed_candidate_slots"] == 651
    assert calibration["use_for_final_metrics"] is False
    assert sampled["calibration_status"] == "staged_not_validated_for_final_metric_use"
    assert sampled["event_boundary_status"] == "exact_serve_contact_and_dead_ball_not_certified"
    assert "no independent human adjudication" in identity["reviewer_provenance"]
    event = next(p for p in events["points"] if (p["set"], p["point_number"]) == (3, 34))
    assert (event["last_reviewed_live_frame"], event["first_reviewed_post_point_frame"]) == (36138, 36150)

    candidate_runs = runs(
        [frame["source_frame"] for frame in frames if frame["six_candidate_boxes"]], 1
    )
    complete_samples = runs(
        [frame["source_frame"] for frame in sampled["frames"]
         if frame["all_six_grounded_proxy_status"] == "accepted_for_exploratory_comparison"],
        sampled["sample_stride_source_frames"],
    )
    candidate_run = max(candidate_runs, key=len)
    sampled_run = max(complete_samples, key=len)
    assert (sampled_run[0], sampled_run[-1], len(sampled_run)) == (36066, 36102, 7)
    assert all(frame["six_candidate_boxes"] for frame in frames
               if sampled_run[0] <= frame["source_frame"] <= sampled_run[-1])
    segment_frames = sampled_run[-1] - sampled_run[0] + 1
    segment_unsampled = segment_frames - len(sampled_run)
    assert segment_frames == 37 and segment_unsampled == 30
    assert any(frame["source_frame"] == 36112 and
               frame["players"]["15"]["source_reviewed_ground_court_m"] is None
               for frame in frames)

    result = {
        "status": "validation_readiness_audit_no_approved_full_rally_or_fixed_window",
        "point": "S3 P34",
        "source_sha256": observations["source_sha256"],
        "input_sha256": {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path)
                         for path in (OBSERVATIONS, SAMPLED, CALIBRATION, EVENTS, IDENTITY,
                                      GROUND_SCORE, GROUND_FORM)},
        "strict_gate": {
            "near_roster_source_review": "existing_source_review",
            "candidate_identity_sequence_review": "AI_assisted_no_independent_human_adjudication",
            "exact_full_rally_boundaries": "unresolved",
            "court_transform_validated_for_metric_use": False,
            "ground_positions_all_30fps_source_frames": False,
            "diagnostic_segment_all_37_frames_six_source_reviewed_proxies": True,
            "continuous_six_grounded_positions": False,
            "approved_full_rally_trajectory": False,
            "approved_fixed_window_result": False,
        },
        "availability": {
            "candidate_frames_with_six": observations["summary"]["frames_with_six_candidates"],
            "candidate_frames_total": observations["summary"]["source_frames"],
            "missing_candidate_slots": observations["summary"]["candidate_missing_slots"],
            "longest_consecutive_six_candidate_run_inclusive": [candidate_run[0], candidate_run[-1]],
            "longest_consecutive_six_candidate_run_frames": len(candidate_run),
            "longest_consecutive_5hz_six_grounded_sample_run_inclusive": [sampled_run[0], sampled_run[-1]],
            "consecutive_grounded_sample_count": len(sampled_run),
            "candidate_complete_frames_in_sample_run_span": segment_frames,
            "sampled_source_reviewed_ground_frames_in_segment": len(sampled_run),
            "additional_single_reviewer_ground_frames_in_segment": segment_unsampled,
            "additional_single_reviewer_ground_player_slots_in_segment": segment_unsampled * 6,
            "source_reviewed_six_grounded_frames_in_segment": segment_frames,
        },
        "decisive_counterexample": {
            "source_frame": 36112,
            "jersey": "15",
            "observation": "airborne_without_jersey_keyed_candidate",
            "consequence": "no_observed_ground_floor_coordinate_at_this_frame",
        },
        "interpretation": "The 36066-36102 segment is selected after tracking availability was known and therefore is a diagnostic target, not a prespecified strict fixed window. The one available human reviewer has now marked all 180 intervening player slots grounded with matching, plausible boxes; this supports a 37-frame source-reviewed diagnostic segment but is not independent adjudication. A full-rally six-grounded-position trajectory cannot be validated while airborne and missing positions remain null. A full-rally descriptive metric input could retain null frames only after exact interval and calibration review, but it would not be a continuous six-grounded trajectory.",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    a = result["availability"]
    REPORT.write_text("\n".join([
        "# S3 P34 strict validation readiness", "",
        "The [machine-readable audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_validation_readiness.json) "
        "checks the current observation ledger, sampled and 30-fps single-reviewer ground review, staged calibration, event brackets and AI-assisted identity sequence review. "
        "It does not approve new court positions or a metric input.", "",
        "| Gate | Current evidence | Decision |",
        "| --- | --- | --- |",
        "| Six near-side jerseys | Existing source roster review | Reviewed roster |",
        "| Candidate continuity | 651 previously unsampled candidates visually checked in 47 paired sheets; no independent human adjudication | Sequence-level support only |",
        f"| Box availability | {a['candidate_frames_with_six']}/{a['candidate_frames_total']} frames contain all six candidates; {a['missing_candidate_slots']} missing player slots | Incomplete |",
        "| Ground points | 11/24 five-Hz team frames complete; 180/180 intervening slots and all 37 frames in the selected segment pass the single-reviewer diagnostic rule | Segment reviewed; full rally incomplete |",
        "| Full-rally events | Serve contact unresolved; last live frame 36138 and first post-point frame 36150 | Exact interval unresolved |",
        "| Court calibration | Four-corner transform with 0.079 m held-out attack-line residual; single-reviewer corners | Staged, not approved |",
        "| Continuous six-grounded trajectory | #15 visibly airborne without a candidate at frame 36112 | Cannot pass current definition |",
        "", "The longest consecutive six-candidate run is "
        f"{a['longest_consecutive_six_candidate_run_inclusive'][0]}–{a['longest_consecutive_six_candidate_run_inclusive'][1]} "
        f"({a['longest_consecutive_six_candidate_run_frames']} source frames). "
        "The longest run of complete *sampled grounded* frames is 36066–36102 "
        "at six-frame intervals: seven reviewed frames over a 37-source-frame span. "
        "All 37 frames have six candidate boxes; the single-reviewer 30-fps pass accepted "
        "all 180 intervening player slots, adding 30 complete diagnostic frames. This span was "
        "identified after checking candidate availability, so it is a diagnostic "
        "segment rather than a prespecified strict fixed window. The reviewer had previously seen tracker results, "
        "and these source-first annotations do not provide independent blinded adjudication.", "",
        "**Result: zero validated full-rally trajectories and zero approved strict fixed-window results.** "
        "A six-player *observation* trajectory can retain airborne and missing states "
        "as null. To support a strict full-rally descriptive metric, exact event bounds "
        "and a court transform explicitly approved for metric use under a documented "
        "review protocol must be established, and each submitted metric frame needs "
        "six accepted grounded points. A continuous "
        "six-grounded-player trajectory across this rally is contradicted by the "
        "visible jump at frame 36112. The single-reviewer protocol supplies an "
        "internal selected-frame reference check; it does not convert the AI-assisted "
        "identity sequence verdict into an independently adjudicated human reference.", "",
        "Reproduce with `.\\.venv\\Scripts\\python.exe "
        "scripts/audit_u5_s3p34_validation_readiness.py`.",
    ]) + "\n", encoding="utf-8")
    print(json.dumps(result["availability"], indent=2))


if __name__ == "__main__":
    main()
