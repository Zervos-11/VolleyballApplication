"""Evaluate the D79 named near-team box output on reviewed frames."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from evaluate_d79_reviewed_near import iou


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/d79_new_source"
NAMED = BASE / "named_near_boxes_80_336.json"
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
OUT = BASE / "named_near_reviewed_evaluation.json"


def main():
    named = json.loads(NAMED.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    if labels["annotated_side"] != "near" or set(named["target_players"]) != {"4", "8", "9", "15", "23", "98"}:
        raise ValueError("Unexpected near-side target set")
    reference_count = 0
    prediction_count = 0
    matches = []
    misses = []
    false_assignments = []
    by_player = defaultdict(lambda: {"reference_visible_boxes": 0, "matched_boxes": 0, "emitted_boxes": 0})
    for frame in range(240, 290):
        key = str(frame)
        record = labels["frames"][key]
        if not record["all_players_accounted_for"] or len(record["players"]) != 6:
            raise ValueError(f"Incomplete reference frame {frame}")
        reference = [p for p in record["players"] if p["bbox"] is not None]
        reference_count += len(reference)
        for p in reference:
            by_player[str(p["player_id"])]["reference_visible_boxes"] += 1
        predicted = [{"player_id": pid, "track_id": slot["raw_track_id"], "bbox": slot["bbox"]}
                     for pid, slot in named["frames"][key].items() if slot["bbox"] is not None]
        for candidate in predicted:
            by_player[candidate["player_id"]]["emitted_boxes"] += 1
        prediction_count += len(predicted)
        scores = np.array([[iou(p["bbox"], q["bbox"]) for q in predicted] for p in reference]) if reference and predicted else np.empty((len(reference), len(predicted)))
        assignments = {}
        if scores.size:
            rows, cols = linear_sum_assignment(-np.where(scores >= 0.5, 1000 + scores, scores))
            assignments = {int(r): int(c) for r, c in zip(rows, cols) if scores[r, c] >= 0.5}
        used = set(assignments.values())
        for index, person in enumerate(reference):
            pid = str(person["player_id"])
            if index not in assignments:
                misses.append({"frame": frame, "player_id": pid})
                continue
            candidate = predicted[assignments[index]]
            correct_identity = candidate["player_id"] == pid
            matches.append({"frame": frame, "reference_player_id": pid,
                            "predicted_player_id": candidate["player_id"],
                            "iou": round(float(scores[index, assignments[index]]), 4),
                            "correct_identity": correct_identity})
            if correct_identity:
                by_player[pid]["matched_boxes"] += 1
        for index, candidate in enumerate(predicted):
            if index not in used:
                false_assignments.append({"frame": frame, "predicted_player_id": candidate["player_id"],
                                          "raw_track_id": candidate["track_id"]})
    correct_id_matches = sum(item["correct_identity"] for item in matches)
    result = {
        "scope": "six_named_near_players_human_verified_model_assisted_50_frame_slice",
        "frame_range_inclusive": [240, 289],
        "matching": "One-to-one maximum-IoU at threshold 0.5 against the generated named near-team box output",
        "named_output_sha256": hashlib.sha256(NAMED.read_bytes()).hexdigest(),
        "raw_full_point_sha256": named["raw_sha256"],
        "identity_seed_sha256": named["seed_sha256"],
        "box_policy_sha256": named["box_policy_sha256"],
        "labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "visible_target_boxes": reference_count,
        "emitted_named_near_boxes": prediction_count,
        "matched_boxes": len(matches),
        "correct_identity_matches": correct_id_matches,
        "target_box_recall": round(len(matches) / reference_count, 4),
        "named_near_box_precision": round(len(matches) / prediction_count, 4) if prediction_count else None,
        "correct_identity_match_fraction": round(correct_id_matches / len(matches), 4) if matches else None,
        "misses": misses,
        "false_near_assignments": false_assignments,
        "players": dict(sorted(by_player.items(), key=lambda item: int(item[0]))),
        "limits": "The box-only #15 extension was chosen after reviewing frames 287–289, so re-scoring those same frames is a regression check, not new held-out validation. The output is a source-seeded development policy, not an autonomous tracker. The reviewer saw frozen suggestions. Only the checked near-side slice is scored; no far-side labels are required. Precision is for emitted named near-team boxes, not all raw person detections. Occluded no-box target slots are excluded from box recall.",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("visible_target_boxes", "emitted_named_near_boxes", "matched_boxes", "correct_identity_matches", "target_box_recall", "named_near_box_precision", "misses", "false_near_assignments")}, indent=2))


if __name__ == "__main__":
    main()
