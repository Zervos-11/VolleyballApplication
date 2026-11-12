"""Read-only consistency check for the primary honours evidence package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
DELIVERABLES = ROOT / "DELIVERABLES"
EXPECTED_SOURCE_SHA256 = "da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b"


def read_json(name: str) -> dict:
    return json.loads((SCREEN / name).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    code_review_snapshot = "--code-review-snapshot" in sys.argv
    media_free_snapshot = code_review_snapshot or "--media-free-snapshot" in sys.argv
    names = {
        "sample": "rally_sample_score_only.json",
        "feasibility": "primary_feasibility_result.json",
        "proxy": "fixed_box_court_proxy_pilot.json",
        "ledger": "s3p34_reviewed_sample_ledger.json",
        "reference": "full_rally_live_reference_audit.json",
        "gate": "full_rally_trajectory_gate_audit.json",
    }
    data: dict[str, dict] = {}
    for label, name in names.items():
        try:
            data[label] = read_json(name)
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    if errors:
        return fail(errors)

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    for label, record in data.items():
        check(
            record.get("source_sha256") == EXPECTED_SOURCE_SHA256,
            f"{names[label]}: primary source hash differs",
        )

    sample = data["sample"]
    events = sample["selected_events"]
    strata = Counter((e["set"], e["winner_scoreboard_side"]) for e in events)
    check(len(events) == 18, "Frozen sample must contain 18 selected events")
    check(len(strata) == 6 and set(strata.values()) == {3}, "Frozen sample must have three events in each of six set/winner strata")
    check(len({(e["set"], e["point_number"]) for e in events}) == 18, "Frozen sample has duplicate set/point keys")

    feasibility = data["feasibility"]["summary"]
    check(feasibility["frozen_points"] == len(events), "Feasibility denominator differs from frozen sample")
    check(feasibility["points_with_source_visible_six"] == 18, "Source-visible six count differs")
    check(feasibility["points_with_correct_local_six_boxes_any_pass"] == 17, "Any-pass local six-box count differs")

    proxy = data["proxy"]
    psummary = proxy["summary"]
    check(psummary["candidate_windows"] == 8, "Pilot window count differs")
    check(psummary["wins"] == psummary["losses"] == 4, "Pilot outcome balance differs")
    check(psummary["source_frame_instances"] == 40, "Pilot team-frame count differs")
    check(psummary["candidate_player_positions"] == 240, "Pilot position count differs")
    check(psummary["candidate_player_positions"] == 6 * psummary["source_frame_instances"], "Pilot positions do not equal six times team frames")
    check(proxy["method"]["court"].startswith("staged"), "Pilot calibration status is no longer staged; review release claims")
    for metric, expected in [
        ("mean_pairwise_spacing_m", -0.0886),
        ("convex_hull_area_m2", -4.2121),
        ("centroid_dispersion_m", -0.1037),
    ]:
        actual = proxy["baseline"][metric]["equal_cell_win_minus_loss"]
        check(abs(actual - expected) < 0.0001, f"Pilot contrast changed for {metric}")

    ledger = data["ledger"]
    frames = ledger["frames"]
    slots = [player for frame in frames for player in frame["players"].values()]
    accepted_slots = sum(player["accepted_ground_coordinate_m"] is not None for player in slots)
    complete_frames = sum(all(player["accepted_ground_coordinate_m"] is not None for player in frame["players"].values()) for frame in frames)
    lsummary = ledger["summary"]
    check(len(frames) == lsummary["sampled_frames"] == 24, "S3 P34 sampled-frame count differs")
    check(len(slots) == lsummary["sampled_player_slots"] == 144, "S3 P34 player-slot count differs")
    check(accepted_slots == lsummary["accepted_individual_grounded_proxies"] == 126, "S3 P34 accepted-slot count differs")
    check(complete_frames == lsummary["accepted_exploratory_frames"] == 11, "S3 P34 complete-team count differs")
    check(len({tuple(sorted(frame["players"])) for frame in frames}) == 1, "S3 P34 sampled jersey roster changes")
    check(ledger["calibration_status"].startswith("staged"), "S3 P34 calibration status changed; review release claims")

    reference = data["reference"]
    refs = reference["frames"]
    reference_rows = sum(len(frame["rows"]) for frame in refs)
    check(len(refs) == reference["summary"]["six_player_reference_frames"] == 5, "Manual reference frame count differs")
    check(reference_rows == reference["summary"]["reviewed_players"] == 30, "Manual reference player count differs")
    check(reference["summary"]["median_player_position_difference_m"] == 0.298, "Manual reference median differs")
    check(reference["summary"]["maximum_player_position_difference_m"] == 0.595, "Manual reference maximum differs")

    gate = data["gate"]
    gate_rows = {(row["set"], row["point_number"]): row for row in gate["rows"]}
    check(gate["summary"]["full_rallies_validated"] == 0, "Full-rally status changed; review release claims")
    for key, initial, corrected, span in [((1, 5), 63, 63, 108), ((3, 34), 96, 104, 138)]:
        row = gate_rows.get(key, {})
        check(row.get("reviewed_span_frames") == span, f"{key}: reviewed span differs")
        check(row.get("reviewed_span_frames_with_six_initial_raw_ids") == initial, f"{key}: initial-ID count differs")
        check(row.get("reviewed_span_frames_with_six_identity_corrected_candidates") == corrected, f"{key}: corrected candidate count differs")
        check(row.get("full_rally_six_player_court_trajectory_validated") is False, f"{key}: validation status changed")

    reports = [
        "HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md",
        "HONOURS_U5_FIXED_BOX_COURT_PROXY.md",
        "HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md",
        "HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md",
        "HONOURS_U5_DYNAMIC_ERROR_SENSITIVITY.md",
        "HONOURS_U5_S3P34_SOURCE_VALIDATION_PROGRESS.md",
        "HONOURS_U5_FULL_RALLY_TRAJECTORY_VALIDATION.md",
        "HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md",
        "HONOURS_U5_THESIS_WORKING_DRAFT.md",
        "HONOURS_U5_THESIS_FINAL_DRAFT.md",
        "HONOURS_PROJECT_EVIDENCE_PACKAGE.md",
    ]
    for name in reports:
        if code_review_snapshot and name in {"HONOURS_U5_THESIS_WORKING_DRAFT.md",
                                             "HONOURS_U5_THESIS_FINAL_DRAFT.md"}:
            continue
        path = DELIVERABLES / name
        if not path.is_file():
            errors.append(f"Missing report: {name}")
            continue
        for link in ([] if media_free_snapshot else re.findall(
                r"!?(?:\[[^\]]*\])\(([^)]+)\)", path.read_text(encoding="utf-8"))):
            if link.startswith(("https://", "http://", "#")):
                continue
            target = link.split("#", 1)[0]
            if target and not (path.parent / target).exists():
                errors.append(f"Broken local link in {name}: {link}")

    if not code_review_snapshot:
        thesis = (DELIVERABLES / "HONOURS_U5_THESIS_FINAL_DRAFT.md").read_text(encoding="utf-8")
        for marker in ("[AUTHOR:", "[FIGURE PLACEHOLDER", "[confirm submission date]", "Editorial boundary"):
            check(marker not in thesis, f"Thesis still contains editorial marker: {marker}")
        check(thesis.count("![") >= 3, "Thesis is missing linked project figures")

    video = ROOT / "data/matches/yt_u5HnY2aNW14/source_720p.mp4"
    if not media_free_snapshot:
        check(video.is_file(), "Primary source video is missing")
    if "--hash-video" in sys.argv and video.is_file():
        digest = hashlib.file_digest(video.open("rb"), "sha256").hexdigest()
        check(digest == EXPECTED_SOURCE_SHA256, "Primary video bytes do not match recorded SHA-256")

    if errors:
        return fail(errors)
    print("PASS: 18 frozen points; 8 pilot windows/240 proxies; 126/144 accepted player slots; 11/24 complete team frames; 5 manual frames/30 positions; 0 validated full rallies.")
    if code_review_snapshot:
        print("PASS: code-review snapshot records and reports; thesis, source video and omitted-media links were not checked.")
    elif media_free_snapshot:
        print("PASS: included reports and numerical records; source video and omitted-media links were not checked.")
    else:
        print("PASS: primary source identifiers, key reports, local report links and source-video presence.")
    if "--hash-video" in sys.argv and video.is_file():
        print("PASS: primary video SHA-256.")
    elif not media_free_snapshot:
        print("NOTE: video bytes were not rehashed; run with --hash-video for that check.")
    return 0


def fail(errors: list[str]) -> int:
    for message in errors:
        print(f"FAIL: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
