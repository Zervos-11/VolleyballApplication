"""Exploratory near-team uniform filter seeded from each rally's start frame.

Uses only video pixels, calibrated court position, and tracker predictions to
select team candidates. Saved player labels are used only for scoring.
"""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from evaluate_pilot_tracker import (
    RALLIES, evaluate_rally, image_to_court, in_target_region, iou, project, stats,
)


MATCH_DIR = Path("data/matches/yt_FqE5pTJqx8g")
TRACKER_DIR = Path("data/processed/pilot_tracker_evaluation")
OUTPUT_DIR = TRACKER_DIR / "appearance_trial"
THRESHOLD = 0.60


def torso_histogram(hsv, box):
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    x1 = max(0, int(x1 + 0.25 * width))
    x2 = min(hsv.shape[1], int(x1 + 0.5 * width))
    y1 = max(0, int(y1 + 0.15 * height))
    y2 = min(hsv.shape[0], int(y1 + 0.45 * height))
    roi = hsv[y1:y2, x1:x2]
    if roi.size < 100:
        return None
    histogram = cv2.calcHist([roi], [0, 1, 2], None, [12, 4, 4],
                             [0, 180, 0, 256, 0, 256])
    return cv2.normalize(histogram, histogram), np.median(roi.reshape(-1, 3), axis=0)


def filter_rally(video, rally, saved, tracked, matrix):
    first = min(map(int, saved["frames"]))
    seeds, seed_boxes, seed_ids = [], [], []
    filtered = {}
    diagnostics = {"seed_track_ids": [], "predictions_before": 0,
                   "predictions_after": 0, "removed_by_appearance": 0}
    for frame_index in sorted(map(int, saved["frames"])):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, image = video.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {rally} frame {frame_index}")
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        candidates = []
        for pred in tracked["predictions"][str(frame_index)]:
            box = pred["bbox"]
            xy_m = project([(box[0] + box[2]) / 2, box[3]], matrix)
            if not in_target_region(xy_m, frame_index == first):
                continue
            appearance = torso_histogram(hsv, box)
            if appearance is not None:
                hist, median_hsv = appearance
                candidates.append((pred, xy_m, hist, median_hsv))
        if frame_index == first:
            for pred, (x, y), hist, median_hsv in sorted(candidates,
                                              key=lambda item: -item[0]["confidence"]):
                # The libero's contrasting yellow kit can begin near the net.
                yellow_libero = (12 <= median_hsv[0] <= 38 and median_hsv[1] >= 85
                                 and median_hsv[2] >= 120)
                if (0 <= x <= 9 and -3 <= y <= (9.5 if yellow_libero else 6.5)
                        and all(iou(pred["bbox"], old) < 0.6 for old in seed_boxes)):
                    seeds.append(hist)
                    seed_boxes.append(pred["bbox"])
                    seed_ids.append(pred["track_id"])
            if not seeds:
                raise ValueError(f"{rally}: no reliable start-frame uniform seeds")
        kept = []
        for pred, xy_m, hist, median_hsv in candidates:
            if frame_index == first:
                kept.append(pred)  # keep start geometry even for a distinct libero kit
            elif min(cv2.compareHist(hist, seed, cv2.HISTCMP_BHATTACHARYYA)
                     for seed in seeds) <= THRESHOLD:
                kept.append(pred)
        diagnostics["predictions_before"] += len(candidates)
        diagnostics["predictions_after"] += len(kept)
        filtered[str(frame_index)] = kept
    diagnostics["seed_track_ids"] = seed_ids
    diagnostics["removed_by_appearance"] = (diagnostics["predictions_before"]
                                             - diagnostics["predictions_after"])
    return {**tracked, "predictions": filtered}, diagnostics


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((MATCH_DIR / "pilot/calibration/calibration_manifest.json").read_text())
    video = cv2.VideoCapture(str(MATCH_DIR / "source_FqE5pTJqx8g.mp4"))
    report = {"method": "start-frame near-court uniform exemplars including a bright yellow libero near the net; HSV torso histogram; Bhattacharyya distance <= 0.60",
              "threshold_note": "Exploratory threshold selected on the same development pilot; test on another match before adopting.",
              "identity_note": "This filters team candidates; matching uniforms cannot uniquely re-identify individual players.",
              "rallies": {}}
    all_ious, all_px, all_m, details = [], [], [], []
    try:
        for rally in RALLIES:
            saved = json.loads((MATCH_DIR / "pilot/player_annotations" / f"{rally}.json").read_text())
            tracked = json.loads((TRACKER_DIR / f"{rally}_tracker_predictions.json").read_text())
            segment = next(v for v in manifest["camera_segments"].values()
                           if rally in v["rallies"])
            calibration = json.loads((MATCH_DIR / "pilot/calibration" / segment["homography_file"]).read_text())
            matrix = image_to_court(calibration)
            filtered, diagnostic = filter_rally(video, rally, saved, tracked, matrix)
            metrics, matches, issues, ious, px, metres = evaluate_rally(
                rally, saved, filtered, matrix)
            report["rallies"][rally] = {**metrics, "appearance_filter": diagnostic}
            all_ious.extend(ious)
            all_px.extend(px)
            all_m.extend(metres)
            details.extend(matches)
    finally:
        video.release()
    keys = ("frames", "labelled_players", "visible_box_labels", "fully_occluded_labels",
            "predictions_in_target_region", "matched", "missed", "extra",
            "invalid_visible_footpoints", "sampled_identity_change_pairs",
            "sampled_identity_pairs")
    totals = {key: sum(part[key] for part in report["rallies"].values()) for key in keys}
    totals.update({"precision": round(totals["matched"] / max(1, totals["matched"]+totals["extra"]), 4),
                   "recall": round(totals["matched"] / max(1, totals["visible_box_labels"]), 4),
                   "matched_box_iou": stats(all_ious),
                   "matched_footpoint_error_px": stats(all_px),
                   "matched_court_error_m": stats(all_m)})
    report["overall"] = totals
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (OUTPUT_DIR / "label_matches.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    print(json.dumps({"rallies": {r: {"matched": v["matched"], "extra": v["extra"],
                                         "precision": v["precision"], "recall": v["recall"]}
                                  for r, v in report["rallies"].items()},
                      "overall": totals}, indent=2))


if __name__ == "__main__":
    main()
