"""Compare tracker IDs on six assisted identity paths across 51 frames."""

import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from evaluate_identity_cues import extract_observations
from evaluate_pilot_tracker import image_to_court, in_target_region, project
from score_dense_identity_window import duplicate_track_aliases


MATCH = Path("data/matches/yt_FqE5pTJqx8g")
SOURCE = Path("data/processed/pilot_tracker_evaluation/dense_identity_window_r4")
OUT = SOURCE / "full_team_150240_150290"


def score(rows, method):
    observed = [row for row in rows if row["track_id"] is not None]
    by_player = defaultdict(list)
    for row in observed:
        by_player[row["player_id"]].append(row)
    changes = {}
    for key, history in by_player.items():
        history.sort(key=lambda row: row["frame_index"])
        changes[key] = sum(a["track_id"] != b["track_id"]
                           for a, b in zip(history, history[1:]))
    player_ids = sorted(by_player)
    track_ids = sorted({row["track_id"] for row in observed})
    confusion = np.zeros((len(player_ids), len(track_ids)), dtype=int)
    player_index = {key: index for index, key in enumerate(player_ids)}
    track_index = {key: index for index, key in enumerate(track_ids)}
    for row in observed:
        confusion[player_index[row["player_id"]], track_index[row["track_id"]]] += 1
    index_a, index_b = linear_sum_assignment(-confusion)
    agreement = int(confusion[index_a, index_b].sum())
    shared = [track_ids[index] for index in range(len(track_ids))
              if np.count_nonzero(confusion[:, index]) > 1]
    return {"method": method, "player_frames": len(rows),
            "detected_player_frames": len(observed),
            "unassigned_player_slots": len(rows) - len(observed),
            "observed_pairs": sum(max(0, len(history) - 1) for history in by_player.values()),
            "identity_changes": sum(changes.values()),
            "changes_by_player": changes,
            "best_one_to_one_id_matches": agreement,
            "best_one_to_one_id_fraction": round(agreement / len(observed), 4),
            "ids_shared_by_players": shared,
            "observed_track_ids_by_player": {
                key: sorted({row["track_id"] for row in history})
                for key, history in by_player.items()}}


def main():
    with (OUT / "assisted_paths.csv").open(newline="", encoding="utf-8") as stream:
        reference = list(csv.DictReader(stream))
    visual_review = json.loads((OUT / "visual_review.json").read_text())
    selected_count = sum(bool(row["candidate_box"]) for row in reference)
    if selected_count != visual_review["selected_detection_identities_confirmed"]:
        raise ValueError("Visual review count no longer matches the assisted path")
    unassigned = {(int(row["frame_index"]), row["player_id"]) for row in reference
                  if not row["candidate_box"]}
    reviewed_unassigned = {(row["frame"], row["player_id"])
                           for row in visual_review["unassigned_player_slots"]}
    if unassigned != reviewed_unassigned:
        raise ValueError("Unassigned player slots changed since visual review")
    dense = json.loads((SOURCE / "tracker_predictions.json").read_text())
    calibration = json.loads((MATCH / "pilot/calibration/camera_r2_r5.json").read_text())
    matrix = image_to_court(calibration)
    predictions = {}
    for frame, people in dense["predictions"].items():
        kept = []
        for pred in people:
            box = pred["bbox"]
            position = project([(box[0] + box[2]) / 2, box[3]], matrix)
            if in_target_region(position, False):
                kept.append(pred)
        predictions[frame] = kept
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    try:
        observations = extract_observations(
            video, "r4", {"frames": {frame: {} for frame in predictions}},
            {"predictions": predictions}, matrix)
    finally:
        video.release()
    aliases, merge_evidence = duplicate_track_aliases(observations)
    methods = {"byte_track": lambda value: value,
               "duplicate_merge": lambda value: aliases.get(value, value)}
    summary = {"window": "r4 frames 150240-150290 inclusive (51 consecutive frames)",
               "reference_note": "Six paths anchored at saved endpoint annotations and five visually chosen player #1 keyframes. All 18 player close-up review sheets were visually checked for identity continuity. Selected boxes come from the detector, not independent manual box drawing.",
               "scope_note": "Identity scoring is conditional on 298 visually checked assisted detection assignments; eight player-frame slots have no confidently assigned box. This is not formal MOT IDF1 or a held-out result.",
               "duplicate_merge_evidence": merge_evidence, "methods": {}}
    detailed = []
    for method, transform in methods.items():
        rows = []
        for entry in reference:
            track_id = (int(entry["candidate_track_id"])
                        if entry["candidate_track_id"] else None)
            row = {"method": method, "frame_index": int(entry["frame_index"]),
                   "player_id": entry["player_id"],
                   "track_id": transform(track_id) if track_id is not None else None,
                   "source_track_id": track_id,
                   "anchor_iou": entry["anchor_iou"],
                   "review_status": ("visual_identity_verified" if track_id is not None
                                     else "unassigned_visual_reviewed")}
            rows.append(row)
            detailed.append(row)
        summary["methods"][method] = score(rows, method)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (OUT / "identity_assignments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detailed[0]))
        writer.writeheader()
        writer.writerows(detailed)
    print(json.dumps(summary["methods"], indent=2))


if __name__ == "__main__":
    main()
