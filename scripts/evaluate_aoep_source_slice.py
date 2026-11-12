"""Reproduce the single-reviewer AoEP source-visibility and anchor audit.

The source visibility rules below were set after reviewing the ten clean,
five-frame source sheets. They are development observations, not independent
ground truth. Approximate anchor boxes were drawn after tracker output was seen.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/aoep_new_source"
REVIEW = BASE / "heldout_source_review"
SOURCE = ROOT / "data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4"
RAW = BASE / "raw_74880_75540.json"
ANCHORS = BASE / "visual_anchors_75180_75229.json"
DENSE = BASE / "dense_visibility_states.json"
PLAYERS = (
    "yellow_left_5", "yellow_centre_left", "yellow_centre_4",
    "yellow_setter_18", "navy_libero_10", "yellow_right_entrant",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def status(frame: int, player: str) -> str:
    if player == "yellow_right_entrant":
        if frame <= 75192:
            return "out_of_frame"
        if frame <= 75195:
            return "uncertain_edge_fragment"
        return "partly_visible_edge"
    if player == "yellow_centre_left" and frame >= 75206:
        return "partly_visible_behind_player"
    return "visible"


def iou(a: list[float], b: list[float]) -> float:
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    dense = json.loads(DENSE.read_text(encoding="utf-8"))
    source_hash = sha256(SOURCE)
    assert source_hash == raw["source_sha256"] == anchors["source_sha256"] == dense["source_sha256"]
    assert set(map(int, dense["frames"])) == set(range(75180, 75230))
    assert all((REVIEW / f"source_{i:02d}.jpg").exists() for i in range(1, 11))

    reference = {
        "status": "single_reviewer_source_visibility_development_reference_not_ground_truth",
        "source_sha256": source_hash,
        "frame_range_inclusive": [75180, 75229],
        "method": "One reviewer inspected all 50 clean source frames in ten source-only sheets at overview resolution; exact entry transition remains uncertain. Reviewer had previously seen tracker output. No boxes or floor points are created here.",
        "status_definitions": {
            "visible": "Recognisable player visible, possibly in a non-neutral pose.",
            "partly_visible_behind_player": "Same player remains partly visible behind another; full body box is intrinsically ambiguous.",
            "partly_visible_edge": "Player partly visible at right image edge; full body box is truncated.",
            "uncertain_edge_fragment": "Possible first fragment; excluded from binary coverage denominator.",
            "out_of_frame": "Not visible in image."
        },
        "players": {player: [
            {"frame": frame, "status": status(frame, player)}
            for frame in range(75180, 75230)
        ] for player in PLAYERS},
    }
    REVIEW.mkdir(exist_ok=True)
    (REVIEW / "visibility_reference_75180_75229.json").write_text(
        json.dumps(reference, indent=2) + "\n", encoding="utf-8")

    coverage = defaultdict(lambda: Counter())
    anomalies = []
    candidate_ids = defaultdict(list)
    for frame in range(75180, 75230):
        rows = {row["visual_player_id"]: row for row in dense["frames"][str(frame)]}
        assert set(rows) == set(PLAYERS)
        predictions = raw["predictions"][str(frame)]
        raw_ids = {p["track_id"] for p in predictions}
        for player in PLAYERS:
            state = status(frame, player)
            if state in ("out_of_frame", "uncertain_edge_fragment"):
                coverage[player][state] += 1
                continue
            raw_id = rows[player]["candidate_raw_track_id"]
            candidate = raw_id is not None and raw_id in raw_ids
            coverage[player]["source_visible_frames"] += 1
            coverage[player]["candidate_box_frames" if candidate else "no_named_candidate_frames"] += 1
            if state.startswith("partly_"):
                coverage[player]["partly_visible_frames"] += 1
            if candidate:
                candidate_ids[player].append(raw_id)
            else:
                anomalies.append({"frame": frame, "player": player, "source_status": state})

    anchor_rows = []
    matched_ious = []
    for frame_str, labels in anchors["frames"].items():
        frame = int(frame_str)
        boxes = raw["predictions"][frame_str]
        visible = [label for label in labels if label["bbox_source_px"] is not None]
        assert all(status(frame, label["visual_player_id"]) not in ("out_of_frame", "uncertain_edge_fragment") for label in visible)
        pairs = sorted(
            ((iou(label["bbox_source_px"], box["bbox"]), li, bi)
             for li, label in enumerate(visible) for bi, box in enumerate(boxes)),
            reverse=True,
        )
        used_labels, used_boxes = set(), set()
        matches = {}
        for overlap, li, bi in pairs:
            if li not in used_labels and bi not in used_boxes:
                used_labels.add(li)
                used_boxes.add(bi)
                matches[li] = (overlap, boxes[bi]["track_id"])
        for li, label in enumerate(visible):
            overlap, track_id = matches.get(li, (0.0, None))
            matched = overlap >= 0.5
            if matched:
                matched_ious.append(overlap)
            anchor_rows.append({
                "frame": frame, "player": label["visual_player_id"],
                "source_status": status(frame, label["visual_player_id"]),
                "iou": round(overlap, 4), "raw_track_id": track_id,
                "matched_at_iou_0_5": matched,
            })

    by_player = defaultdict(list)
    for row in anchor_rows:
        by_player[row["player"]].append(row)
    result = {
        "status": "development_diagnostic_not_independent_tracker_accuracy",
        "source_sha256": source_hash,
        "raw_sha256": sha256(RAW),
        "anchor_sha256": sha256(ANCHORS),
        "visibility_reference_sha256": sha256(REVIEW / "visibility_reference_75180_75229.json"),
        "scope": "50 source frames, six near-side visual player slots, six approximate sampled box-anchor frames",
        "limitations": [
            "Single reviewer saw previous tracker diagnostics; visibility record is not blinded.",
            "Dense named-candidate associations came from a tracker-informed development ledger, not independent frame labels.",
            "Six approximate box-anchor frames were drawn after tracker output was seen; overlap is agreement only.",
            "No exhaustive far-side or all-person boxes; no detector precision or formal recall/IDF1.",
            "No independently reviewed foot contacts or installed calibration; no position error or distance accuracy.",
        ],
        "coverage_by_player": {player: dict(coverage[player]) for player in PLAYERS},
        "candidate_unique_raw_ids_by_player": {player: sorted(set(candidate_ids[player])) for player in PLAYERS},
        "missing_named_candidate_rows": anomalies,
        "anchor_agreement": {
            "sampled_frames": sorted(map(int, anchors["frames"])),
            "visible_anchor_slots": len(anchor_rows),
            "matched_iou_at_least_0_5": sum(row["matched_at_iou_0_5"] for row in anchor_rows),
            "median_iou_of_matched": round(median(matched_ious), 4) if matched_ious else None,
            "sampled_raw_ids_by_player": {player: [
                {"frame": row["frame"], "raw_track_id": row["raw_track_id"],
                 "matched_at_iou_0_5": row["matched_at_iou_0_5"]}
                for row in by_player[player]
            ] for player in PLAYERS},
            "rows": anchor_rows,
        },
    }
    output = REVIEW / "development_audit_75180_75229.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output.relative_to(ROOT)),
        "coverage": result["coverage_by_player"],
        "anchor_slots": result["anchor_agreement"]["visible_anchor_slots"],
        "anchor_matches": result["anchor_agreement"]["matched_iou_at_least_0_5"],
        "anchor_median_iou": result["anchor_agreement"]["median_iou_of_matched"],
    }, indent=2))


if __name__ == "__main__":
    main()
