"""Compare provisional r1 raw tracks with saved sparse player annotations."""

import collections
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
LABELS = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r1.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2-x1) * max(0, y2-y1)
    area_a = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    area_b = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    return intersection / max(1e-9, area_a+area_b-intersection)


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    image_to_court = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32))
    start, end = raw["start_frame"], raw["end_frame_exclusive"]
    if set(raw["frames"]) != {str(f) for f in range(start, end)}:
        raise RuntimeError("Raw tracking does not cover the full candidate interval")
    identity = collections.defaultdict(list)
    sampled = []
    total_labels = 0
    total_matched = 0
    for frame_text, record in labels["frames"].items():
        frame = int(frame_text)
        if not start <= frame < end:
            continue
        people = [p for p in record["players"] if p.get("bbox") is not None]
        predictions = raw["frames"][frame_text]
        total_labels += len(people)
        pairs = []
        if people and predictions:
            scores = np.asarray([[iou(p["bbox"], d["bbox"])
                                  for d in predictions] for p in people])
            rows, cols = linear_sum_assignment(-np.where(scores >= 0.5, 1000+scores, scores))
            for i, j in zip(rows, cols):
                if scores[i, j] >= 0.5:
                    pair = {"player_id": people[i]["player_id"],
                            "track_id": predictions[j]["track_id"],
                            "iou": round(float(scores[i, j]), 3),
                            "position_status": people[i]["position_status"]}
                    pairs.append(pair)
                    identity[people[i]["player_id"]].append([frame, pair["track_id"]])
        total_matched += len(pairs)
        matched_players = {pair["player_id"] for pair in pairs}
        assigned_tracks = {pair["track_id"]: pair["player_id"] for pair in pairs}
        unmatched = []
        for person in people:
            if person["player_id"] in matched_players:
                continue
            best = max(predictions, key=lambda d: iou(person["bbox"], d["bbox"])) if predictions else None
            best_iou = iou(person["bbox"], best["bbox"]) if best else 0.0
            best_track = best["track_id"] if best else None
            unmatched.append({
                "player_id": person["player_id"],
                "position_status": person["position_status"],
                "best_raw_track_id": best_track,
                "best_iou": round(best_iou, 3),
                "best_track_assigned_to": assigned_tracks.get(best_track),
                "review_reason": ("shared_detection_overlap" if best_iou >= 0.5
                                  and best_track in assigned_tracks else
                                  "low_box_overlap_or_missing_detection"),
            })
        sampled.append({"frame": frame, "label_boxes": len(people),
                        "raw_person_boxes": len(predictions),
                        "matched_at_iou_0_5": len(pairs), "matches": pairs,
                        "unmatched_saved_boxes": unmatched})
    all_rows = [row for rows in raw["frames"].values() for row in rows]
    track_counts = collections.Counter(row["track_id"] for row in all_rows)
    floor_proxy_discrepancies = []
    for sample in sampled:
        frame_text = str(sample["frame"])
        for match in sample["matches"]:
            person = next(p for p in labels["frames"][frame_text]["players"]
                          if p["player_id"] == match["player_id"])
            if person["position_status"] != "visible" or person.get("footpoint") is None:
                continue
            prediction = next(p for p in raw["frames"][frame_text]
                              if p["track_id"] == match["track_id"])
            x1, _, x2, y2 = prediction["bbox"]
            points = cv2.perspectiveTransform(
                np.asarray([[person["footpoint"], [(x1+x2)/2, y2]]], dtype=np.float32),
                image_to_court)[0]
            floor_proxy_discrepancies.append({
                "frame": sample["frame"], "player_id": match["player_id"],
                "difference_m": round(float(np.linalg.norm(points[0]-points[1])), 3)})
    discrepancies = [item["difference_m"] for item in floor_proxy_discrepancies]
    unique_per_player = {pid: sorted({track for _, track in path})
                         for pid, path in identity.items()}
    people_per_track = collections.defaultdict(set)
    for pid, path in identity.items():
        for _, track in path:
            people_per_track[track].add(pid)
    cross_player_reuse = {str(track): sorted(people)
                          for track, people in people_per_track.items()
                          if len(people) > 1}
    result = {
        "status": "development_diagnostic_against_unreviewed_sparse_labels",
        "source_raw_tracks": str(RAW.relative_to(ROOT)).replace("\\", "/"),
        "start_frame": start, "end_frame_exclusive": end,
        "frames_processed": end-start,
        "raw_person_boxes": len(all_rows),
        "unique_raw_track_ids": len(track_counts),
        "raw_person_boxes_per_frame_min_median_max": [
            min(map(len, raw["frames"].values())),
            float(np.median([len(v) for v in raw["frames"].values()])),
            max(map(len, raw["frames"].values()))],
        "sparse_label_frames": len(sampled),
        "sparse_label_boxes": total_labels,
        "sparse_matched_at_iou_0_5": total_matched,
        "matched_fraction_of_saved_boxes": round(total_matched/max(1,total_labels), 4),
        "matched_raw_ids_per_saved_player": unique_per_player,
        "raw_ids_matched_to_multiple_saved_players": cross_player_reuse,
        "saved_footpoint_vs_raw_box_bottom": {
            "count_visible_matches": len(discrepancies),
            "median_m": round(float(np.median(discrepancies)), 3),
            "p90_m": round(float(np.percentile(discrepancies, 90)), 3),
            "largest_cases": sorted(floor_proxy_discrepancies,
                                    key=lambda item: item["difference_m"], reverse=True)[:5],
            "interpretation": "Discrepancy between two unvalidated floor proxies, not a measured position error."},
        "sampled_frame_matches": sampled,
        "limits": ["Sparse labels are not independent ground truth.",
                   "A raw tracker ID is not a verified player identity.",
                   "Bounding-box bottoms have not been verified as shoe-floor contacts.",
                   "No full-rally movement metric is derived from these boxes."],
    }
    (BASE/"r1_dense_audit.json").write_text(json.dumps(result, indent=2)+"\n",encoding="utf-8")

    capture = cv2.VideoCapture(str(VIDEO))
    for frame in (21050, 21200, 21250, 21400, 21450):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode overlay frame {frame}")
        item = next(row for row in sampled if row["frame"] == frame)
        match_ids = {m["track_id"]: m["player_id"] for m in item["matches"]}
        for prediction in raw["frames"][str(frame)]:
            box = list(map(int, prediction["bbox"]))
            track = prediction["track_id"]
            color = (0, 255, 0) if track in match_ids else (160, 160, 160)
            cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), color, 2)
            label = f"P{match_ids[track]} T{track}" if track in match_ids else f"T{track}"
            cv2.putText(image, label, (box[0], max(20, box[1]-5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        cv2.imwrite(str(BASE/f"r1_dense_overlay_{frame}.jpg"), image)
    capture.release()
    print(f"matched {total_matched}/{total_labels} saved boxes; "
          f"{len(track_counts)} raw IDs over {end-start} frames")


if __name__ == "__main__":
    main()
