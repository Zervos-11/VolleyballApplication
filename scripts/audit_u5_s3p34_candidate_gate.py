"""Find raw person boxes omitted by S3 P34's near-court candidate gate.

The output supplements the frozen jersey-keyed ledger. It does not change human
source verdicts, accept box bottoms as floor points, or impute missing players.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
RAW = SCREEN / "source_bracketed_30fps_screen.json"
LEDGER = SCREEN / "s3p34_six_player_observation_ledger.json"
MANIFEST = SCREEN / "s3p34_remaining_rally_review/manifest.json"
OUTPUT = SCREEN / "s3p34_candidate_gate_omission_audit.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_CANDIDATE_GATE_OMISSION_AUDIT.md"
EXPECTED_IDS = {"28": {1}, "12": {3}, "15": {6}, "7": {9, 78}, "19": {10}, "21": {13}}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    point = next(row for row in raw["points"] if (row["set"], row["point_number"]) == (3, 34))
    raw_frames = {row["source_frame"]: row for row in point["rows"]}
    if len(ledger["frames"]) != 138 or not {f["source_frame"] for f in ledger["frames"]} <= set(raw_frames):
        raise ValueError("Candidate-interval denominator changed")
    if raw["source_sha256"] != ledger["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Source hashes disagree")

    missing = []
    before_six = after_six = 0
    counts = Counter()
    for frame in ledger["frames"]:
        number = frame["source_frame"]
        proposals = raw_frames[number]["proposals"]
        before = sum(p["jersey_keyed_candidate_court_m"] is not None for p in frame["players"].values())
        after = before
        for jersey, player in frame["players"].items():
            if player["jersey_keyed_candidate_court_m"] is not None:
                continue
            same_id = [p for p in proposals if p["raw_track_id"] in EXPECTED_IDS[jersey]]
            if same_id and not all(p["net_side_status"] == "net_boundary_review" for p in same_id):
                raise ValueError(f"Unexpected ungated same-ID box at {number}/{jersey}")
            classification = "raw_box_removed_by_net_boundary_gate" if same_id else "no_mapped_raw_id_box"
            counts[classification] += 1
            counts[f"{jersey}_{classification}"] += 1
            after += bool(same_id)
            missing.append({"source_frame": number, "jersey": jersey,
                            "classification": classification,
                            "raw_proposals": [{"raw_track_id": p["raw_track_id"],
                                               "bbox_px": p["bbox_px"],
                                               "box_bottom_court_m_staged": p["box_bottom_court_m"],
                                               "confidence": p["confidence"]}
                                              for p in same_id]})
        before_six += before == 6
        after_six += after == 6
    if len(missing) != 48 or counts["raw_box_removed_by_net_boundary_gate"] != 12:
        raise ValueError("Original missing-slot and gate-omission counts changed")
    result = {
        "status": "candidate_gate_diagnostic_not_floor_validation",
        "interval_inclusive": [36001, 36138],
        "denominators": {"frames": 138, "player_slots": 828,
                         "original_missing_jersey_keyed_slots": 48},
        "counts": dict(counts),
        "six_candidate_frames_original": before_six,
        "six_candidate_frames_if_all_same_id_boundary_boxes_included": after_six,
        "assumptions": ["Known raw IDs are mapped to the six UCLA jerseys as in the frozen review manifest.",
                        "A same-ID raw box in the net-boundary class is a recoverable person-box proposal, not an accepted jersey or floor position.",
                        "No position or identity is imputed for a frame with no mapped raw-ID box."],
        "inputs_sha256": {"raw_screen": sha(RAW), "original_ledger": sha(LEDGER),
                          "review_manifest": sha(MANIFEST)},
        "missing_slots": missing,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# S3 P34 near-court candidate-gate audit\n\n"
        "The original 138-frame ledger has **48/828 missing jersey-keyed candidate slots**. "
        "A raw-proposal join found an already tracked same-ID person box in **12/48** of those slots. "
        "All twelve had been labelled `net_boundary_review` and omitted by the near-court "
        "box-bottom gate; **36/48** lack a mapped raw-ID box in that pass. "
        "[Machine-readable audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_candidate_gate_omission_audit.json).\n\n"
        "| UCLA jersey | Raw box removed by gate | No mapped raw-ID box |\n"
        "| --- | ---: | ---: |\n"
        + "\n".join(f"| #{j} | {counts[f'{j}_raw_box_removed_by_net_boundary_gate']} | "
                    f"{counts[f'{j}_no_mapped_raw_id_box']} |" for j in EXPECTED_IDS) + "\n\n"
        f"The original count is **{before_six}/138** frames with all six jersey-keyed candidate "
        f"boxes. Including these twelve same-ID boundary proposals would give **{after_six}/138** "
        "*conditional candidate* frames. This is a diagnostic recalculation, not a replacement "
        "for the frozen source-reviewed count. A near-court gate using box bottoms can reject "
        "a visible player at the net when posture moves the box bottom across the boundary. "
        "It does not prove the box bottom is a physical floor point, and the missing 36 slots "
        "still require separate detection or identity review.\n",
        encoding="utf-8",
    )
    print(f"Boundary gate omissions: {counts['raw_box_removed_by_net_boundary_gate']}/48; conditional six-candidate frames: {before_six} -> {after_six}/138")


if __name__ == "__main__":
    main()
