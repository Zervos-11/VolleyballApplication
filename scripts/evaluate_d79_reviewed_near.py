"""Score frozen D79 boxes against the user's reviewed near-side labels.

The reviewer saw the frozen proposals and corrected wrong boxes. This is a
bounded, human-verified, model-assisted evaluation, not a blind test.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/processed/d79_new_source/raw_240_289.json"
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
OUTPUT = ROOT / "data/processed/d79_new_source/reviewed_near_evaluation.json"
FIRST, LAST = 240, 289


def iou(a, b):
    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    return overlap / max(1e-9, area_a + area_b - overlap)


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    if (raw["first_frame"], raw["last_frame"]) != (FIRST, LAST):
        raise ValueError("Unexpected frozen tracker window")
    if labels.get("annotated_side") != "near":
        raise ValueError("Expected near-side labels")
    matched_by_player = defaultdict(list)
    unmatched = []
    all_overlaps = []
    raw_count = 0
    no_box_slots = 0
    for frame in range(FIRST, LAST + 1):
        key = str(frame)
        record = labels["frames"].get(key)
        if not record or not record.get("all_players_accounted_for") or len(record["players"]) != 6:
            raise ValueError(f"Frame {frame} lacks six completed review slots")
        people = [p for p in record["players"] if p.get("bbox") is not None]
        no_box_slots += 6 - len(people)
        predictions = raw["predictions"][key]
        raw_count += len(predictions)
        if not people or not predictions:
            unmatched.extend({"frame": frame, "player_id": str(p["player_id"])} for p in people)
            continue
        scores = np.array([[iou(p["bbox"], d["bbox"]) for d in predictions] for p in people])
        # Prioritize valid 0.5-IoU pairs before maximizing overlap within them.
        rows, cols = linear_sum_assignment(-np.where(scores >= 0.5, 1000 + scores, scores))
        matches = {int(r): int(c) for r, c in zip(rows, cols) if scores[r, c] >= 0.5}
        for index, person in enumerate(people):
            pid = str(person["player_id"])
            if index not in matches:
                unmatched.append({"frame": frame, "player_id": pid,
                                  "best_iou": round(float(scores[index].max()), 4)})
                continue
            pred = predictions[matches[index]]
            overlap = float(scores[index, matches[index]])
            matched_by_player[pid].append({"frame": frame, "track_id": pred["track_id"], "iou": overlap})
            all_overlaps.append(overlap)
    matched = sum(map(len, matched_by_player.values()))
    total_labeled = matched + len(unmatched)
    player_results = {}
    for pid, observations in sorted(matched_by_player.items(), key=lambda item: int(item[0])):
        switches = []
        for previous, current in zip(observations, observations[1:]):
            if current["frame"] == previous["frame"] + 1 and current["track_id"] != previous["track_id"]:
                switches.append(current["frame"])
        player_results[pid] = {
            "matched_visible_boxes": len(observations),
            "raw_track_ids": sorted(set(row["track_id"] for row in observations)),
            "contiguous_visible_id_switch_frames": switches,
            "median_iou": round(float(np.median([row["iou"] for row in observations])), 4),
            "minimum_iou": round(min(row["iou"] for row in observations), 4),
        }
    result = {
        "scope": "human_verified_model_assisted_near_side_50_frames",
        "source_sha256": raw["source_sha256"],
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "frame_range_inclusive": [FIRST, LAST],
        "iou_matching_threshold": 0.5,
        "matching_method": "one-to-one maximum-IoU assignment per frame; no proposal-origin links used",
        "raw_person_boxes_all_people": raw_count,
        "completed_near_player_slots": 6 * (LAST - FIRST + 1),
        "near_slots_without_distinct_box": no_box_slots,
        "visible_near_reference_boxes": total_labeled,
        "matched_near_reference_boxes": matched,
        "near_reference_box_match_rate": round(matched / total_labeled, 4),
        "matched_iou_median": round(float(np.median(all_overlaps)), 4),
        "matched_iou_minimum": round(min(all_overlaps), 4),
        "matched_iou_at_least_0_75": sum(x >= 0.75 for x in all_overlaps),
        "matched_iou_at_least_0_9": sum(x >= 0.9 for x in all_overlaps),
        "unmatched_near_reference_boxes": unmatched,
        "players": player_results,
        "total_contiguous_visible_id_switches": sum(len(p["contiguous_visible_id_switch_frames"]) for p in player_results.values()),
        "known_identity_failure_outside_visible_near_reference": "Raw ID 2 reappears on a non-target player at frame 289 after near #9 becomes occluded; do not stitch it to #9.",
        "interpretation": "The annotator inspected and redrew wrong suggested boxes. This measures agreement with the human-verified near-side reference. Suggestions from the scored tracker were visible during annotation, so this is not a blind estimate. Raw predictions are unclassified people; near-team precision requires a final six-player output and can be scored against the checked near-side slots without annotating far-side identities.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("visible_near_reference_boxes", "matched_near_reference_boxes", "near_reference_box_match_rate", "matched_iou_median", "matched_iou_minimum", "matched_iou_at_least_0_75", "matched_iou_at_least_0_9", "total_contiguous_visible_id_switches")}, indent=2))


if __name__ == "__main__":
    main()
