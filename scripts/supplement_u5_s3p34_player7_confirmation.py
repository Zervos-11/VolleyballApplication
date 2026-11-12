"""Record the student's collective source review of seven #7 gap proposals.

This supplements frozen tracker and annotation exports; it never edits them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
DIAGNOSTIC = SCREEN / "s3p34_player7_gap_diagnostic/candidate_recovery.json"
CROPS = SCREEN / "s3p34_player7_gap_diagnostic/sideways_7_crops.jpg"
GATE = SCREEN / "s3p34_candidate_gate_omission_audit.json"
LEDGER = SCREEN / "s3p34_six_player_observation_ledger.json"
OUT = SCREEN / "s3p34_player7_gap_diagnostic/student_box_confirmation.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_PLAYER7_BOX_CONFIRMATION.md"
EXPECTED = {36124, 36126, 36127, 36128, 36129, 36130, 36131}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    proposals = diagnostic["late_higher_resolution_proposals"]
    if {p["source_frame"] for p in proposals} != EXPECTED:
        raise ValueError("The reviewed seven-frame set has changed")
    if diagnostic["source_sha256"] != ledger["source_sha256"]:
        raise ValueError("Source video hashes disagree")
    frames = {f["source_frame"]: f for f in ledger["frames"]}
    gate_missing = {(p["source_frame"], p["jersey"]): p for p in gate["missing_slots"]}
    rows = []
    for item in proposals:
        frame = item["source_frame"]
        if frames[frame]["players"]["7"]["jersey_keyed_candidate_court_m"] is not None:
            raise ValueError(f"Frame {frame} already has an original #7 candidate")
        if gate_missing[(frame, "7")]["classification"] != "no_mapped_raw_id_box":
            raise ValueError(f"Unexpected original #7 raw box at {frame}")
        chosen = max(item["person_proposals"], key=lambda p: p["confidence"])
        rows.append({
            "source_frame": frame,
            "player_slot": 4,
            "ucla_jersey": "7",
            "selected_bbox_px": chosen["bbox_px"],
            "detector_confidence": chosen["confidence"],
            "selection_rule": "highest confidence proposal in the predeclared search region",
            "source_sequence_identity_verdict": "same_player_by_student_collective_crop_review",
            "digit_independently_readable_each_frame": None,
            "ground_status": None,
            "accepted_floor_court_m": None,
        })

    before = after_gate = after_student = 0
    recovered_by_gate = {(p["source_frame"], p["jersey"])
                         for p in gate["missing_slots"]
                         if p["classification"] == "raw_box_removed_by_net_boundary_gate"}
    recovered_by_student = {(p["source_frame"], "7") for p in rows}
    if recovered_by_gate & recovered_by_student:
        raise ValueError("Recovery sources overlap")
    for frame in ledger["frames"]:
        n = frame["source_frame"]
        original = {j for j, p in frame["players"].items()
                    if p["jersey_keyed_candidate_court_m"] is not None}
        with_gate = original | {j for f, j in recovered_by_gate if f == n}
        with_student = with_gate | {j for f, j in recovered_by_student if f == n}
        before += len(original) == 6
        after_gate += len(with_gate) == 6
        after_student += len(with_student) == 6

    result = {
        "status": "supplemental_single_reviewer_identity_confirmation_not_ground_validation",
        "reviewer": "student (Michael Zervos)",
        "review_provenance": "2026-11-08 chat reply: 'Yes, all seven follow player 4' after viewing the larger crop sheet",
        "review_scope": "collective source-sequence judgment over seven displayed yellow boxes; not seven independent digit readings or per-frame click annotations",
        "source_sha256": diagnostic["source_sha256"],
        "inputs_sha256": {"diagnostic": sha(DIAGNOSTIC), "reviewed_crop_sheet": sha(CROPS),
                          "gate_audit": sha(GATE), "original_ledger": sha(LEDGER)},
        "interval": {"first_frame": 36001, "last_frame": 36138,
                     "frames": 138, "player_slots": 828},
        "conditional_candidate_coverage": {
            "original_slots": 780,
            "with_12_raw_boundary_boxes_slots": 792,
            "with_12_raw_boundary_and_7_student_confirmed_boxes_slots": 799,
            "original_all_six_frames": before,
            "with_12_raw_boundary_boxes_all_six_frames": after_gate,
            "with_12_raw_boundary_and_7_student_confirmed_boxes_all_six_frames": after_student,
        },
        "confirmed_box_rows": rows,
        "limitation": "A source-reviewed person box supports identity continuity. It is not an accepted grounded floor coordinate, and these selected seven frames do not cover the entire rally or certify an event boundary.",
    }
    if (before, after_gate) != (gate["six_candidate_frames_original"], gate["six_candidate_frames_if_all_same_id_boundary_boxes_included"]):
        raise ValueError("Conditional counts disagree with the boundary audit")
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# S3 P34 player 4 / UCLA #7 box confirmation\n\n"
        "On 8 November 2026, the student reviewed the [larger source crop sheet]"
        "(../data/matches/yt_u5HnY2aNW14/screening/s3p34_player7_gap_diagnostic/sideways_7_crops.jpg) "
        "and confirmed that all seven yellow higher-resolution boxes follow player 4 / UCLA #7. "
        "This is one collective, candidate-assisted source-sequence judgment; it does not claim "
        "that jersey digits were independently readable in each frame. The [machine-readable supplement]"
        "(../data/matches/yt_u5HnY2aNW14/screening/s3p34_player7_gap_diagnostic/student_box_confirmation.json) "
        "records the selected boxes, source hashes and review provenance.\n\n"
        "| Candidate state | Player slots | All-six frames |\n| --- | ---: | ---: |\n"
        f"| Original jersey-keyed export | 780/828 | {before}/138 |\n"
        f"| Add twelve same-ID raw boxes omitted by court gate | 792/828 | {after_gate}/138 |\n"
        f"| Also add seven student-confirmed #7 boxes | 799/828 | {after_student}/138 |\n\n"
        "The second and third rows are **conditional candidate availability**, not revised validated "
        "floor coverage. The twelve boundary proposals still require source adjudication. All seven "
        "new #7 box rows retain null ground status and null accepted court position. The original "
        "tracking output and manually saved annotations are unchanged.\n",
        encoding="utf-8",
    )
    print(f"Student-confirmed #7 boxes: {len(rows)}; conditional all-six candidate frames {before} -> {after_gate} -> {after_student}/138")


if __name__ == "__main__":
    main()
