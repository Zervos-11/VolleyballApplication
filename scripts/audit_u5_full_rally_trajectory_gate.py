"""Audit whether the two densely screened six-player runs cover a full rally.

This joins existing source-bound audits. It does not infer missing positions or
promote detector agreement to independent ground truth.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
INPUTS = {
    "cuts": "rally_cut_clip_register.json",
    "phases": "event_transition_source_qc.json",
    "runs": "full_clip_tracklet_audit.json",
    "identity": "full_run_identity_audit.json",
    "dense": "two_long_runs_30fps_audit.json",
    "dense_screen": "two_long_runs_30fps_screen.json",
    "bracketed_screen": "source_bracketed_30fps_screen.json",
    "live_reference": "full_rally_live_reference_audit.json",
    "sampled_review": "s3p34_reviewed_sample_ledger.json",
    "positions": "full_run_position_reference.json",
}
BRACKETS = BASE / "full_rally_validation_frames/source_event_brackets.json"
OUT = BASE / "full_rally_trajectory_gate_audit.json"
CANDIDATES = BASE / "full_rally_candidate_paths.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_FULL_RALLY_TRAJECTORY_VALIDATION.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def by_point(rows):
    return {(row["set"], row["point_number"]): row for row in rows}


def main():
    files = {key: BASE / name for key, name in INPUTS.items()}
    data = {key: json.loads(path.read_text(encoding="utf-8"))
            for key, path in files.items()}
    event_brackets = json.loads(BRACKETS.read_text(encoding="utf-8"))
    source_hashes = {item["source_sha256"] for item in data.values()}
    assert len(source_hashes) == 1, "Inputs refer to different source videos"
    cut = by_point(data["cuts"]["selected_clips"])
    phase = by_point(data["phases"]["points"])
    run = by_point(data["runs"]["points"])
    identity = by_point(data["identity"]["rows"])
    dense = by_point(data["dense"]["rows"])
    dense_screen = by_point(data["dense_screen"]["points"])
    extended = by_point(data["bracketed_screen"]["points"])
    brackets = by_point(event_brackets["points"])
    rows = []
    candidate_points = []
    for key in sorted(dense):
        assert key in cut and key in phase and key in run and key in identity
        assert key in dense_screen and key in extended and key in brackets
        c, p, r, i, d = cut[key], phase[key], run[key], identity[key], dense[key]
        extended_point = extended[key]
        bracket = brackets[key]
        assert extended_point["rows"][:len(dense_screen[key]["rows"])] == dense_screen[key]["rows"]
        first, last = d["source_frame_first"], d["source_frame_last"]
        candidate = r["longest_same_six_raw_id_run_full_clip"]
        assert (first, last) == (candidate["first_frame"], candidate["last_frame"])
        assert d["source_frames_screened"] == last - first + 1
        assert len(i["sampled_source_frames"]) == candidate["sampled_frames"]
        assert i["sampled_source_frames"][0] == first
        assert i["sampled_source_frames"][-1] == last
        assert len(i["players"]) == len(d["players"]) == 6
        live_first = p["conservative_interior_start_frame_inclusive"]
        live_end = p["conservative_interior_end_frame_exclusive"]
        overlap = max(0, min(last + 1, live_end) - max(first, live_first))
        live_length = live_end - live_first
        missing = d["frames_with_fewer_than_six_candidates"]
        complete = d["exactly_six_near_candidate_frames"]
        assert missing + complete == d["source_frames_screened"]
        manual = (data["positions"]["summary"]["clear_grounded_manual_pairs"]
                  if key == (data["positions"]["set"], data["positions"]["point_number"])
                  else 0)
        reference = data["live_reference"]
        has_reference = key == (reference["set"], reference["point_number"])
        six_reference = (reference["summary"]["six_player_reference_frames"]
                         if has_reference else 0)
        manual += reference["summary"]["reviewed_players"] if has_reference else 0
        last_reviewed_live = bracket["last_reviewed_live_frame"]
        first_post_point = bracket["first_reviewed_post_point_frame"]
        assert live_first <= last_reviewed_live < first_post_point
        assert extended_point["source_frame_end_exclusive"] == first_post_point + 1
        for image_key in ("live_image", "post_point_image"):
            assert (ROOT / "data/matches/yt_u5HnY2aNW14" / bracket[image_key]).exists()
        raw_to_jersey = {player["dense_raw_track_id"]: player["reviewed_jersey_number"]
                         for player in d["players"]}
        assert len(raw_to_jersey) == 6
        candidate_frames = []
        all_six_count = 0
        corrected_six_count = 0
        with_missing_count = 0
        extra_count = 0
        for frame in extended_point["rows"]:
            frame_number = frame["source_frame"]
            if not live_first <= frame_number <= last_reviewed_live:
                continue
            observed = {box["raw_track_id"]: box for box in frame["proposals"]
                        if box["net_side_status"] == "near_floor_side_candidate"}
            assert len(observed) == frame["near_candidate_count"]
            original_missing = [jersey for raw_id, jersey in raw_to_jersey.items()
                                if raw_id not in observed]
            corrected_observed = dict(observed)
            if key == (3, 34):
                # Source review: ID 78 is a second box/late replacement for
                # UCLA #7; ID 39 is a far-side player at the net.
                corrected_observed.pop(39, None)
                if frame_number >= 36117 and 9 not in corrected_observed and 78 in corrected_observed:
                    corrected_observed[9] = corrected_observed[78]
                corrected_observed.pop(78, None)
            missing_jerseys = [jersey for raw_id, jersey in raw_to_jersey.items()
                               if raw_id not in corrected_observed]
            extra_ids = sorted(raw_id for raw_id in corrected_observed
                               if raw_id not in raw_to_jersey)
            all_six_count += not original_missing
            corrected_six_count += not missing_jerseys
            with_missing_count += bool(original_missing)
            extra_count += bool(extra_ids)
            candidate_frames.append({
                "source_frame": frame_number,
                "court_box_bottom_by_jersey_m": {
                    jersey: (corrected_observed[raw_id]["box_bottom_court_m"]
                             if raw_id in corrected_observed else None)
                    for raw_id, jersey in raw_to_jersey.items()},
                "missing_jerseys": missing_jerseys,
                "extra_raw_ids": extra_ids,
            })
        assert len(candidate_frames) == last_reviewed_live - live_first + 1
        assert all_six_count + with_missing_count == len(candidate_frames)
        candidate_points.append({"set": key[0], "point_number": key[1],
                                 "interval_inclusive": [live_first, last_reviewed_live],
                                 "first_reviewed_post_point_frame": first_post_point,
                                 "frames": candidate_frames})
        rows.append({
            "set": key[0], "point_number": key[1],
            "edit_frame_interval_inclusive_exclusive": [c["clip_start_frame_inclusive"],
                                                        c["clip_end_frame_exclusive"]],
            "conservative_live_interval_inclusive_exclusive": [live_first, live_end],
            "dense_run_interval_inclusive": [first, last],
            "live_frames": live_length,
            "live_frames_inside_dense_run": overlap,
            "live_frames_outside_dense_run": live_length - overlap,
            "live_frame_coverage_fraction": round(overlap / live_length, 4),
            "dense_run_source_frames": d["source_frames_screened"],
            "dense_frames_with_six_boxes": complete,
            "dense_frames_with_missing_box": missing,
            "identity_checked_five_hz_frames": len(i["sampled_source_frames"]),
            "identity_checked_all_source_frames": 0,
            "manual_clear_shoe_marks_in_run": manual,
            "six_player_manual_reference_frames_in_run": six_reference,
            "last_reviewed_live_frame": last_reviewed_live,
            "first_reviewed_post_point_frame": first_post_point,
            "reviewed_span_frames": len(candidate_frames),
            "reviewed_span_frames_with_six_initial_raw_ids": all_six_count,
            "reviewed_span_frames_with_six_identity_corrected_candidates": corrected_six_count,
            "reviewed_span_frames_with_missing_initial_raw_id": with_missing_count,
            "reviewed_span_frames_with_extra_raw_id": extra_count,
            "exact_live_boundaries_certified": False,
            "full_rally_six_player_court_trajectory_validated": False,
        })
    assert len(rows) == 2
    candidate_output = {
        "status": "unvalidated_box_bottom_candidates_with_explicit_gaps",
        "source_sha256": next(iter(source_hashes)),
        "bracketed_screen_sha256": sha(files["bracketed_screen"]),
        "identity_mapping_basis": "initial 5 Hz jersey mapping; S3 P34 source-reviewed late ID 78 mapped to UCLA #7 where ID 9 is absent, and far-side ID 39 excluded; other unsampled 30 fps identities remain provisional",
        "position_rule": "detector box bottom mapped with staged 9 m homography; airborne and ground contact not validated",
        "missing_rule": "null means no identity-corrected near-side proposal; no interpolation or hold",
        "points": candidate_points,
    }
    CANDIDATES.write_text(json.dumps(candidate_output, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "full_rally_validation_gate_not_met",
        "source_sha256": source_hashes.pop(),
        "input_sha256": {**{key: sha(path) for key, path in files.items()},
                         "source_event_brackets": sha(BRACKETS),
                         "candidate_paths": sha(CANDIDATES)},
        "rule": ("A full-rally six-player court trajectory requires an exact live interval, "
                 "six named-player positions throughout it with explicit missing states, "
                 "and independent position checks distributed through that interval."),
        "summary": {
            "dense_runs_audited": len(rows),
            "full_rallies_validated": 0,
            "dense_source_frames": sum(x["dense_run_source_frames"] for x in rows),
            "dense_frames_with_six_boxes": sum(x["dense_frames_with_six_boxes"] for x in rows),
            "dense_frames_with_missing_box": sum(x["dense_frames_with_missing_box"] for x in rows),
            "conservative_live_frames": sum(x["live_frames"] for x in rows),
            "conservative_live_frames_outside_dense_runs": sum(
                x["live_frames_outside_dense_run"] for x in rows),
            "manual_clear_shoe_marks_in_runs": sum(
                x["manual_clear_shoe_marks_in_run"] for x in rows),
            "six_player_manual_reference_frames_in_runs": sum(
                x["six_player_manual_reference_frames_in_run"] for x in rows),
            "reviewed_span_frames": sum(x["reviewed_span_frames"] for x in rows),
            "reviewed_span_frames_with_six_initial_raw_ids": sum(
                x["reviewed_span_frames_with_six_initial_raw_ids"] for x in rows),
        },
        "rows": rows,
        "sampled_review_summary": data["sampled_review"]["summary"],
        "interpretation": (
            "The phase interiors are conservative approximations, not exact ball-live "
            "boundaries. These uncovered-frame counts therefore measure coverage of "
            "that approximation only. The expanded interval begins at the conservative "
            "start and ends at a reviewed live frame; exact serve and dead-ball frames "
            "remain uncertified. The 30 fps pass tests box availability and raw ID "
            "persistence, not every-frame jersey or grounded court-position accuracy."
        ),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Full-rally six-player trajectory validation gate",
        "",
        "This audit joins the [cut register](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_clip_register.json), "
        "[source phase review](../data/matches/yt_u5HnY2aNW14/screening/event_transition_source_qc.json), "
        "[run identity review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md), "
        "[30 fps box audit](HONOURS_U5_TWO_RUNS_30FPS_AUDIT.md), "
        "[reviewed end brackets](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/source_event_brackets.json), "
        "and [manual six-player reference](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md). "
        "The [machine-readable join](../data/matches/yt_u5HnY2aNW14/screening/full_rally_trajectory_gate_audit.json) "
        "records input hashes and exact intervals.",
        "",
        "| Point | Conservative live frames | In original 103-frame run | Outside original run | Box frames in original run | Manual six-player frames |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for x in rows:
        lines.append(
            f"| S{x['set']} P{x['point_number']} | {x['live_frames']} | "
            f"{x['live_frames_inside_dense_run']} ({100*x['live_frame_coverage_fraction']:.1f}%) | "
            f"{x['live_frames_outside_dense_run']} | "
            f"{x['dense_frames_with_six_boxes']}/{x['dense_run_source_frames']} | "
            f"{x['six_player_manual_reference_frames_in_run']} |"
        )
    lines += [
        "",
        "The conservative live intervals are **approximations** from source-image review, "
        "not exact serve-contact and dead-ball frames. Even against those approximate "
        "intervals, neither dense run covers the full period. S1 P5's run contains setup "
        "before the conservative live start; S3 P34 starts just before that start and "
        "ends before the conservative live end.",
        "",
        "The new 30 fps pass extends from the tracker anchor through the first reviewed "
        "post-point frame. For the span from each conservative start through the last "
        "reviewed live frame:",
        "",
        "| Point | Analysed frames | Six original IDs | Six after reviewed ID correction | Frames missing an original ID | Unassigned extra ID frames | Last live / first post-point |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for x in rows:
        lines.append(f"| S{x['set']} P{x['point_number']} | {x['reviewed_span_frames']} | "
                     f"{x['reviewed_span_frames_with_six_initial_raw_ids']} | "
                     f"{x['reviewed_span_frames_with_six_identity_corrected_candidates']} | "
                     f"{x['reviewed_span_frames_with_missing_initial_raw_id']} | "
                     f"{x['reviewed_span_frames_with_extra_raw_id']} | "
                     f"{x['last_reviewed_live_frame']} / {x['first_reviewed_post_point_frame']} |")
    lines += [
        "",
        "The [jersey-keyed candidate paths](../data/matches/yt_u5HnY2aNW14/screening/full_rally_candidate_paths.json) "
        "retain observed box-bottom candidates and explicit nulls. S3 P34 source review "
        "maps late raw ID 78 back to UCLA #7 where original ID 9 is absent and excludes "
        "far-side raw ID 39. This corrects candidate identity at the reviewed late "
        "transition, but does not make airborne box bottoms observed floor positions.",
        "",
        "The 5 Hz review checks the six visible jerseys at 18 displayed samples per "
        "original run. Five [six-player manual references](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md) "
        "distributed across S3 P34 yield a median box-bottom to shoe difference of "
        f"{data['live_reference']['summary']['median_player_position_difference_m']:.3f} m. "
        "Three of the five frames are supplementary unblinded checks; none are a "
        "second-reviewer reference. The [new sampled source ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reviewed_sample_ledger.json) "
        f"accepts {data['sampled_review']['summary']['accepted_exploratory_frames']}/"
        f"{data['sampled_review']['summary']['sampled_frames']} 5 Hz S3 P34 frames "
        "for exploratory six-grounded-player proxy metrics, with explicit exclusions. "
        "[Source frame 36120](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/frame_36120.png) "
        "shows front players airborne, making their "
        "box bottoms unsuitable as observed floor positions.",
        "",
        "The [S3 P34 source validation progress](HONOURS_U5_S3P34_SOURCE_VALIDATION_PROGRESS.md) "
        "records the serve/end brackets, sampled exclusions, late jersey correction and "
        "staged calibration. Exact event frames and independent full-rally floor references "
        "remain open.",
        "",
        "**Result: 0 full-rally six-player court trajectories validated.** The two runs "
        "remain useful short-span tracking diagnostics. The remaining validation requires "
        "exact live boundaries, source review of identity through the full interval, "
        "explicit gap handling, and multiple independent six-player position references "
        "including movement and occlusion. Missing positions must remain missing or "
        "clearly marked as estimates; they cannot count as observed accuracy.",
        "",
        "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/audit_u5_full_rally_trajectory_gate.py`.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
