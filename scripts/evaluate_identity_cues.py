"""Explore physical and colour cues for player identity on sparse pilot frames.

The assignment reads tracker detections and video pixels, never player labels.
Labels are used only afterward to count identity changes between observations.
This is a development diagnostic, not a dense MOT identity benchmark.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from evaluate_pilot_tracker import RALLIES, image_to_court, match_boxes, project
from evaluate_team_appearance import MATCH_DIR, TRACKER_DIR, filter_rally


OUTPUT_DIR = TRACKER_DIR / "identity_cue_trial"
REFERENCE_FRAME_GAP = 50  # approximately one second in this source video
MAX_MOVE_M = 5.0  # between two adjacent saved observations (~50 source frames)
MAX_TRACK_AGE = 150  # source frames; do not bridge long unseen periods


def hist_region(hsv, box, xlo, xhi, ylo, yhi):
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    left = max(0, int(x1 + xlo * width))
    right = min(hsv.shape[1], int(x1 + xhi * width))
    top = max(0, int(y1 + ylo * height))
    bottom = min(hsv.shape[0], int(y1 + yhi * height))
    roi = hsv[top:bottom, left:right]
    if roi.shape[0] < 5 or roi.shape[1] < 5:
        return None
    hist = cv2.calcHist([roi], [0, 1, 2], None, [12, 4, 4],
                        [0, 180, 0, 256, 0, 256])
    return cv2.normalize(hist, hist)


def colour_distance(a, b):
    if a is None or b is None:
        return None
    return float(cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA))


def extract_observations(video, rally, saved, filtered, matrix):
    observations = {}
    for frame in sorted(map(int, saved["frames"])):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = video.read()
        if not ok:
            raise RuntimeError(f"Cannot read {rally} frame {frame}")
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        current = []
        for pred in filtered["predictions"][str(frame)]:
            box = pred["bbox"]
            foot = [(box[0] + box[2]) / 2, box[3]]
            current.append({"prediction": pred, "xy": project(foot, matrix),
                            "jersey": hist_region(hsv, box, .25, .75, .15, .60),
                            "shoe": hist_region(hsv, box, .15, .85, .84, .99)})
        observations[frame] = current
    return observations


def assign_ids(observations, use_jersey, use_shoe, position_noise_m=0.0):
    tracks = {}
    assigned = {}
    next_id = 1
    for frame, detections in observations.items():
        track_ids = [key for key, track in tracks.items()
                     if frame - track["frame"] <= MAX_TRACK_AGE]
        costs = np.full((len(track_ids), len(detections)), 1e6)
        for i, key in enumerate(track_ids):
            track = tracks[key]
            gap = frame - track["frame"]
            allowed_m = MAX_MOVE_M * gap / REFERENCE_FRAME_GAP + position_noise_m
            for j, detection in enumerate(detections):
                distance_m = float(np.linalg.norm(track["xy"] - detection["xy"]))
                if distance_m > allowed_m:
                    continue
                cost = distance_m / max(allowed_m, 1e-6)
                if use_jersey:
                    jersey = colour_distance(track["jersey"], detection["jersey"])
                    if jersey is not None:
                        cost += .6 * jersey
                if use_shoe:
                    shoe = colour_distance(track["shoe"], detection["shoe"])
                    if shoe is not None:
                        cost += .2 * shoe
                if track["byte_id"] == detection["prediction"]["track_id"]:
                    cost -= .4
                costs[i, j] = cost
        ids = [None] * len(detections)
        if costs.size:
            rows, cols = linear_sum_assignment(costs)
            for i, j in zip(rows, cols):
                if costs[i, j] < 1e5:
                    ids[j] = track_ids[i]
        for j, detection in enumerate(detections):
            if ids[j] is None:
                ids[j] = next_id
                next_id += 1
            tracks[ids[j]] = {"frame": frame, "xy": detection["xy"],
                              "jersey": detection["jersey"], "shoe": detection["shoe"],
                              "byte_id": detection["prediction"]["track_id"]}
        assigned[frame] = ids
    return assigned


def score(saved, observations, assigned, rally, method):
    by_player = {}
    rows = []
    for frame, detections in observations.items():
        labels = [player for player in saved["frames"][str(frame)]["players"]
                  if player.get("bbox") is not None]
        matched = match_boxes(labels, [item["prediction"] for item in detections])
        for i, j, overlap in matched:
            player_id = str(labels[i]["player_id"])
            row = {"method": method, "rally_id": rally, "frame_index": frame,
                   "player_id": player_id,
                   "assigned_id": assigned[frame][j],
                   "byte_track_id": detections[j]["prediction"]["track_id"],
                   "iou": round(overlap, 4)}
            rows.append(row)
            by_player.setdefault(player_id, []).append(row)
    pairs = [ (a, b) for history in by_player.values()
              for a, b in zip(history, history[1:]) ]
    changes = sum(a["assigned_id"] != b["assigned_id"] for a, b in pairs)
    player_ids = sorted({row["player_id"] for row in rows})
    predicted_ids = sorted({row["assigned_id"] for row in rows})
    confusion = np.zeros((len(player_ids), len(predicted_ids)), dtype=int)
    player_index = {key: i for i, key in enumerate(player_ids)}
    predicted_index = {key: i for i, key in enumerate(predicted_ids)}
    for row in rows:
        confusion[player_index[row["player_id"]],
                  predicted_index[row["assigned_id"]]] += 1
    best_matches = 0
    if confusion.size:
        index_a, index_b = linear_sum_assignment(-confusion)
        best_matches = int(confusion[index_a, index_b].sum())
    mixed_ids = int(sum(np.count_nonzero(confusion[:, i]) > 1
                        for i in range(len(predicted_ids))))
    return {"matched": len(rows), "observed_pairs": len(pairs),
            "identity_changes": changes,
            "best_one_to_one_id_matches": best_matches,
            "mixed_identity_ids": mixed_ids}, rows


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((MATCH_DIR / "pilot/calibration/calibration_manifest.json").read_text())
    video = cv2.VideoCapture(str(MATCH_DIR / "source_FqE5pTJqx8g.mp4"))
    methods = {"byte_track": (False, False),
               "motion": (False, False),
               "motion_jersey": (True, False),
               "motion_jersey_shoe": (True, True)}
    summary = {"movement_gate": "5 m per 50 source frames (~1 s) between saved observations; scaled by elapsed frames; max unseen age 150 source frames",
               "method_note": "All motion assignments also use a modest ByteTrack ID continuity bonus. Shoe colour is sampled only when the lower box region has enough pixels.",
               "evaluation_note": "Sparse development frames only; labels used only for scoring; selected cues require separate-match validation.",
               "rallies": {}, "overall": {}}
    all_rows = []
    try:
        for rally in RALLIES:
            saved = json.loads((MATCH_DIR / "pilot/player_annotations" / f"{rally}.json").read_text())
            tracked = json.loads((TRACKER_DIR / f"{rally}_tracker_predictions.json").read_text())
            segment = next(v for v in manifest["camera_segments"].values()
                           if rally in v["rallies"])
            calibration = json.loads((MATCH_DIR / "pilot/calibration" /
                                      segment["homography_file"]).read_text())
            matrix = image_to_court(calibration)
            filtered, _ = filter_rally(video, rally, saved, tracked, matrix)
            observations = extract_observations(video, rally, saved, filtered, matrix)
            summary["rallies"][rally] = {}
            for method, (jersey, shoe) in methods.items():
                if method == "byte_track":
                    assigned = {frame: [d["prediction"]["track_id"] for d in detections]
                                for frame, detections in observations.items()}
                else:
                    assigned = assign_ids(observations, jersey, shoe)
                result, rows = score(saved, observations, assigned, rally, method)
                summary["rallies"][rally][method] = result
                all_rows.extend(rows)
    finally:
        video.release()
    for method in methods:
        summary["overall"][method] = {
            key: sum(summary["rallies"][rally][method][key] for rally in RALLIES)
            for key in ("matched", "observed_pairs", "identity_changes",
                        "best_one_to_one_id_matches", "mixed_identity_ids")}
        total = summary["overall"][method]
        total["best_one_to_one_id_fraction"] = round(
            total["best_one_to_one_id_matches"] / max(1, total["matched"]), 4)
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (OUTPUT_DIR / "label_matches.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    print(json.dumps(summary["overall"], indent=2))


if __name__ == "__main__":
    main()
