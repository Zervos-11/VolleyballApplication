"""Run the existing YOLOv8n + ByteTrack setup on pilot rallies and score sparse labels.

The tracker sees every source frame in each rally. Only manually labelled frames
are retained and scored. This is a development-set diagnostic, not an IDF1 test.
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment


MATCH = "yt_FqE5pTJqx8g"
RALLIES = ("r1", "r2", "r3", "r4", "r5")
IOU_THRESHOLD = 0.5
COURT_PAD_M = 1.5
START_SIDE_PAD_M = 0.5
START_SERVICE_DEPTH_M = 3.0
START_NET_PAD_M = 0.5


def image_to_court(calibration):
    return cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32),
    )


def project(point, matrix):
    return cv2.perspectiveTransform(
        np.asarray([[point]], dtype=np.float32), matrix,
    )[0, 0].astype(float)


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return overlap / max(1e-9, area_a + area_b - overlap)


def match_boxes(labels, predictions):
    """Maximize the number of >=0.5 IoU matches, then total IoU."""
    if not labels or not predictions:
        return []
    scores = np.asarray([[iou(label["bbox"], pred["bbox"])
                          for pred in predictions] for label in labels])
    weights = np.where(scores >= IOU_THRESHOLD, 1000.0 + scores, scores)
    rows, cols = linear_sum_assignment(-weights)
    return [(int(i), int(j), float(scores[i, j])) for i, j in zip(rows, cols)
            if scores[i, j] >= IOU_THRESHOLD]


def valid_label_footpoint(player):
    """Reject geometry inconsistent with the labelled visible-body box."""
    foot, box = player.get("footpoint"), player.get("bbox")
    if player.get("position_status") != "visible" or foot is None or box is None:
        return False
    x, y = foot
    x1, y1, x2, y2 = box
    return x1 - 10 <= x <= x2 + 10 and y1 - 10 <= y <= y2 + 20


def in_target_region(xy_m, is_start_frame):
    """At serve start, players occupy the near court or the service zone behind it."""
    x, y = map(float, xy_m)
    if is_start_frame:
        return (-START_SIDE_PAD_M <= x <= 9 + START_SIDE_PAD_M
                and -START_SERVICE_DEPTH_M <= y <= 9 + START_NET_PAD_M)
    return (-COURT_PAD_M <= x <= 9 + COURT_PAD_M
            and -COURT_PAD_M <= y <= 9 + COURT_PAD_M)


def stats(values):
    if not values:
        return {"n": 0, "median": None, "mean": None, "p90": None}
    return {"n": len(values), "median": round(statistics.median(values), 4),
            "mean": round(statistics.mean(values), 4),
            "p90": round(float(np.percentile(values, 90)), 4)}


def track_rally(model_path, model_sha256, video, rally, saved, output,
                warmup_frames=0):
    from ultralytics import YOLO

    model = YOLO(str(model_path))  # fresh ByteTrack state for each rally
    capture = cv2.VideoCapture(str(video))
    start, end = saved["start_frame"], saved["end_frame_exclusive"]
    if warmup_frames < 0:
        raise ValueError("warmup_frames must be nonnegative")
    warmup_first = max(0, start - warmup_frames)
    if not capture.set(cv2.CAP_PROP_POS_FRAMES, warmup_first):
        raise RuntimeError(f"Could not seek to {rally} frame {warmup_first}")
    labelled = set(map(int, saved["frames"]))
    recorded = {}
    try:
        for frame_index in range(warmup_first, end):
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Video ended at {rally} frame {frame_index}")
            result = model.track(frame, tracker="bytetrack.yaml", persist=True,
                                 conf=0.20, imgsz=960, verbose=False)[0]
            if frame_index < start or frame_index not in labelled:
                continue
            boxes = result.boxes
            predictions = []
            if boxes is not None and len(boxes):
                xyxy = boxes.xyxy.cpu().numpy()
                cls = boxes.cls.cpu().numpy()
                confidence = boxes.conf.cpu().numpy()
                ids = (boxes.id.cpu().numpy() if boxes.id is not None
                       else np.full(len(boxes), -1))
                for box, kind, score, track_id in zip(xyxy, cls, confidence, ids):
                    if int(kind) == 0:
                        predictions.append({"bbox": [round(float(v), 3) for v in box],
                                            "confidence": round(float(score), 5),
                                            "track_id": int(track_id)})
            recorded[str(frame_index)] = predictions
        if set(recorded) != set(saved["frames"]):
            raise RuntimeError(f"{rally}: missing labelled frames in tracker output")
        payload = {"rally_id": rally, "start_frame": start,
                   "end_frame_exclusive": end, "frames_processed": end-start,
                   "warmup_first_frame": warmup_first,
                   "warmup_frames_processed": start-warmup_first,
                   "model_sha256": model_sha256,
                   "tracker_settings": "bytetrack.yaml; conf=0.20; imgsz=960",
                   "predictions": recorded}
        temp = output.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temp.replace(output)
        return payload
    finally:
        capture.release()


def evaluate_rally(rally, saved, tracked, matrix):
    totals = {"frames": len(saved["frames"]), "labelled_players": 0,
              "visible_box_labels": 0, "fully_occluded_labels": 0,
              "predictions_in_target_region": 0, "matched": 0,
              "missed": 0, "extra": 0, "invalid_visible_footpoints": 0}
    ious, distances_m, distances_px, details, issues = [], [], [], [], []
    identity_observations = {}
    first_labelled_frame = min(map(int, saved["frames"]))
    for frame_index, frame in sorted(saved["frames"].items(), key=lambda pair: int(pair[0])):
        players = frame["players"]
        totals["labelled_players"] += len(players)
        labels = [player for player in players if player.get("bbox") is not None]
        totals["visible_box_labels"] += len(labels)
        totals["fully_occluded_labels"] += len(players) - len(labels)
        predictions = []
        for pred in tracked["predictions"][frame_index]:
            box = pred["bbox"]
            foot = [(box[0]+box[2])/2, box[3]]
            xy_m = project(foot, matrix)
            if in_target_region(xy_m, int(frame_index) == first_labelled_frame):
                predictions.append({**pred, "footpoint": foot, "court_position": xy_m})
        totals["predictions_in_target_region"] += len(predictions)
        matches = match_boxes(labels, predictions)
        totals["matched"] += len(matches)
        totals["missed"] += len(labels) - len(matches)
        totals["extra"] += len(predictions) - len(matches)
        by_label = {i: (j, overlap) for i, j, overlap in matches}
        for i, player in enumerate(labels):
            entry = {"rally_id": rally, "frame_index": int(frame_index),
                     "player_id": str(player["player_id"]),
                     "position_status": player["position_status"],
                     "matched": i in by_label, "iou": "", "track_id": "",
                     "footpoint_error_px": "", "court_error_m": ""}
            if player.get("position_status") == "visible" and not valid_label_footpoint(player):
                totals["invalid_visible_footpoints"] += 1
                issues.append({"rally_id": rally, "frame_index": int(frame_index),
                               "player_id": str(player["player_id"]),
                               "issue": "footpoint_outside_box_tolerance",
                               "footpoint": player.get("footpoint"), "bbox": player.get("bbox")})
            if i in by_label:
                j, overlap = by_label[i]
                pred = predictions[j]
                entry["iou"] = round(overlap, 4)
                entry["track_id"] = pred["track_id"]
                ious.append(overlap)
                if pred["track_id"] >= 0:
                    identity_observations.setdefault(str(player["player_id"]), []).append(
                        (int(frame_index), pred["track_id"]))
                if valid_label_footpoint(player):
                    gt_foot = np.asarray(player["footpoint"], dtype=float)
                    error_px = float(np.linalg.norm(np.asarray(pred["footpoint"])-gt_foot))
                    error_m = float(np.linalg.norm(pred["court_position"]-project(gt_foot, matrix)))
                    entry["footpoint_error_px"] = round(error_px, 4)
                    entry["court_error_m"] = round(error_m, 4)
                    distances_px.append(error_px)
                    distances_m.append(error_m)
            details.append(entry)
    changes = sum(a[1] != b[1] for observations in identity_observations.values()
                  for a, b in zip(observations, observations[1:]))
    pairs = sum(max(0, len(observations)-1) for observations in identity_observations.values())
    totals.update({"precision": round(totals["matched"] / max(1, totals["matched"]+totals["extra"]), 4),
                   "recall": round(totals["matched"] / max(1, totals["visible_box_labels"]), 4),
                   "matched_box_iou": stats(ious),
                   "matched_footpoint_error_px": stats(distances_px),
                   "matched_court_error_m": stats(distances_m),
                   "sampled_identity_change_pairs": changes,
                   "sampled_identity_pairs": pairs})
    return totals, details, issues, ious, distances_px, distances_m


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-dir", type=Path,
                        default=Path("data/matches") / MATCH)
    parser.add_argument("--model", type=Path, default=Path("yolov8n.pt"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/processed/pilot_tracker_evaluation"))
    parser.add_argument("--warmup-frames", type=int, default=0,
                        help="Track preceding source frames before scoring a rally")
    args = parser.parse_args()
    if args.warmup_frames < 0:
        parser.error("--warmup-frames must be nonnegative")
    if args.warmup_frames and args.output.resolve() == Path(
            "data/processed/pilot_tracker_evaluation").resolve():
        parser.error("Use a separate --output directory for a warm-up candidate")
    match_dir = args.match_dir.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config_dir = Path("data/processed/ultralytics_config").resolve()
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config_dir)
    video = match_dir / "source_FqE5pTJqx8g.mp4"
    if not video.exists() or not args.model.exists():
        raise FileNotFoundError("Source video and local yolov8n.pt model are required")
    manifest = json.loads((match_dir / "pilot/calibration/calibration_manifest.json").read_text(encoding="utf-8"))
    model_sha256 = hashlib.sha256(args.model.read_bytes()).hexdigest()
    report = {"match_id": MATCH, "model": str(args.model),
              "model_sha256": model_sha256,
              "tracker_warmup_frames": args.warmup_frames,
              "tracker": ("YOLOv8n + ByteTrack, conf=0.20, imgsz=960, "
                          f"{args.warmup_frames} pre-rally warm-up frames, all rally frames"),
              "matching": "one-to-one person-box assignment at IoU >= 0.5",
              "target_region": "first labelled frame: x=-0.5..9.5m, y=-3..9.5m (service zone behind baseline); later frames: court bounds plus 1.5m",
              "position": "predicted box-bottom centre versus annotated visible footpoint; inconsistent annotation footpoints excluded",
              "scope": "development pilot, 69 sparse labelled frames; sampled ID changes are diagnostic, not IDF1",
              "rallies": {}}
    all_details, all_issues, all_ious, all_px, all_m = [], [], [], [], []
    for rally in RALLIES:
        saved = json.loads((match_dir / "pilot/player_annotations" / f"{rally}.json").read_text(encoding="utf-8"))
        segment = next(segment for segment in manifest["camera_segments"].values()
                       if rally in segment["rallies"])
        calibration = json.loads((match_dir / "pilot/calibration" / segment["homography_file"]).read_text(encoding="utf-8"))
        matrix = image_to_court(calibration)
        predictions_path = output / f"{rally}_tracker_predictions.json"
        if predictions_path.exists():
            tracked = json.loads(predictions_path.read_text(encoding="utf-8"))
            if (tracked["start_frame"], tracked["end_frame_exclusive"]) != (saved["start_frame"], saved["end_frame_exclusive"]):
                raise ValueError(f"{rally}: cached predictions use different boundaries")
            if tracked.get("warmup_first_frame", saved["start_frame"]) != max(
                    0, saved["start_frame"] - args.warmup_frames):
                raise ValueError(f"{rally}: cached predictions use a different warm-up start")
            if tracked.get("model_sha256") != model_sha256 or tracked.get("tracker_settings") != "bytetrack.yaml; conf=0.20; imgsz=960":
                raise ValueError(f"{rally}: cached predictions use different tracker settings or model weights")
        else:
            print(f"Tracking {rally}: {saved['end_frame_exclusive']-saved['start_frame']} frames", flush=True)
            tracked = track_rally(args.model, model_sha256, video, rally, saved,
                                  predictions_path, args.warmup_frames)
        metrics, details, issues, ious, px, metres = evaluate_rally(rally, saved, tracked, matrix)
        report["rallies"][rally] = metrics
        all_details.extend(details)
        all_issues.extend(issues)
        all_ious.extend(ious)
        all_px.extend(px)
        all_m.extend(metres)
        print(f"{rally}: {metrics['matched']}/{metrics['visible_box_labels']} boxes matched; "
              f"{metrics['matched_court_error_m']['n']} positions scored", flush=True)
    keys = ("frames", "labelled_players", "visible_box_labels", "fully_occluded_labels",
            "predictions_in_target_region", "matched", "missed", "extra", "invalid_visible_footpoints",
            "sampled_identity_change_pairs", "sampled_identity_pairs")
    totals = {key: sum(part[key] for part in report["rallies"].values()) for key in keys}
    totals.update({"precision": round(totals["matched"] / max(1, totals["matched"]+totals["extra"]), 4),
                   "recall": round(totals["matched"] / max(1, totals["visible_box_labels"]), 4),
                   "matched_box_iou": stats(all_ious),
                   "matched_footpoint_error_px": stats(all_px),
                   "matched_court_error_m": stats(all_m)})
    report["overall"] = totals
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for filename, rows, fieldnames in [
        ("label_matches.csv", all_details, list(all_details[0])),
        ("annotation_issues.csv", all_issues,
         ["rally_id", "frame_index", "player_id", "issue", "footpoint", "bbox"]),
    ]:
        with (output / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(totals, indent=2), flush=True)


if __name__ == "__main__":
    main()
