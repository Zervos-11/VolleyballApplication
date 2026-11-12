"""Independent-rally check of the frozen r4 duplicate-track merge rule."""

import argparse
import csv
import json
import os
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from evaluate_identity_cues import extract_observations
from evaluate_pilot_tracker import image_to_court, in_target_region, iou, project
from score_dense_identity_window import duplicate_track_aliases
from score_full_team_dense_review import score


MATCH = Path("data/matches/yt_FqE5pTJqx8g")
OUT = Path("data/processed/pilot_tracker_evaluation/dense_identity_validation_r2")
RALLY_START, FIRST, LAST = 78000, 78100, 78150
MIN_IOU = .20


def prepare():
    from ultralytics import YOLO
    OUT.mkdir(parents=True, exist_ok=True)
    labels = json.loads((MATCH / "pilot/player_annotations/r2.json").read_text())
    player_ids = sorted(player["player_id"] for player in labels["frames"][str(FIRST)]["players"])
    anchors = {frame: {player["player_id"]: np.asarray(player["bbox"], dtype=float)
                       for player in labels["frames"][str(frame)]["players"]}
               for frame in (FIRST, LAST)}
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    video.set(cv2.CAP_PROP_POS_FRAMES, RALLY_START)
    model = YOLO("yolov8n.pt")
    predictions = {}
    try:
        for frame in range(RALLY_START, LAST + 1):
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f"Cannot read r2 frame {frame}")
            result = model.track(image, tracker="bytetrack.yaml", persist=True,
                                 conf=.20, imgsz=960, verbose=False)[0]
            if frame < FIRST:
                continue
            boxes = result.boxes
            people = []
            if boxes is not None and len(boxes):
                xyxy = boxes.xyxy.cpu().numpy()
                cls = boxes.cls.cpu().numpy()
                confidence = boxes.conf.cpu().numpy()
                ids = (boxes.id.cpu().numpy() if boxes.id is not None
                       else [-1] * len(boxes))
                for box, kind, conf, track_id in zip(xyxy, cls, confidence, ids):
                    if int(kind) == 0:
                        people.append({"bbox": [round(float(v), 3) for v in box],
                                       "confidence": round(float(conf), 5),
                                       "track_id": int(track_id)})
            predictions[str(frame)] = people
    finally:
        video.release()
    sparse = json.loads((Path("data/processed/pilot_tracker_evaluation") /
                         "r2_tracker_predictions.json").read_text())
    for frame in (FIRST, LAST):
        if sparse["predictions"][str(frame)] != predictions[str(frame)]:
            raise ValueError(f"Dense tracker replay differs at saved frame {frame}")
    (OUT / "tracker_predictions.json").write_text(
        json.dumps({"rally_id": "r2", "first_frame": FIRST, "last_frame": LAST,
                    "source_fps": 50, "tracker": "yolov8n.pt ByteTrack conf=0.20 imgsz=960",
                    "predictions": predictions}, indent=2) + "\n")
    rows = []
    for frame in range(FIRST, LAST + 1):
        weight = (frame - FIRST) / (LAST - FIRST)
        expected = {key: ((1 - weight) * anchors[FIRST][key] +
                          weight * anchors[LAST][key]) for key in player_ids}
        detections = predictions[str(frame)]
        overlaps = np.asarray([[iou(expected[key], det["bbox"])
                                for det in detections] for key in player_ids])
        padded = np.pad(overlaps, ((0, 0), (0, len(player_ids))), constant_values=0)
        index_a, index_b = linear_sum_assignment(-padded)
        chosen = {player_ids[i]: j for i, j in zip(index_a, index_b)
                  if j < len(detections) and overlaps[i, j] >= MIN_IOU}
        for i, key in enumerate(player_ids):
            j = chosen.get(key)
            det = detections[j] if j is not None else None
            rows.append({"frame_index": frame, "player_id": key,
                         "candidate_track_id": det["track_id"] if det else "",
                         "candidate_box": json.dumps(det["bbox"]) if det else "",
                         "anchor_iou": round(float(overlaps[i, j]), 4) if j is not None else 0.0,
                         "review_status": "assisted_unreviewed"})
    with (OUT / "assisted_paths.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    try:
        for key in player_ids:
            player_rows = [row for row in rows if row["player_id"] == key]
            crops = []
            for row in player_rows:
                frame = row["frame_index"]
                video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(f"Cannot reread frame {frame}")
                weight = (frame - FIRST) / (LAST - FIRST)
                box = (json.loads(row["candidate_box"]) if row["candidate_box"] else
                       (1 - weight) * anchors[FIRST][key] + weight * anchors[LAST][key])
                center_x, center_y = int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)
                left = max(0, min(image.shape[1] - 300, center_x - 150))
                top = max(0, min(image.shape[0] - 300, center_y - 150))
                crop = image[top:top + 300, left:left + 300].copy()
                if row["candidate_box"]:
                    x1, y1, x2, y2 = [int(v) for v in box]
                    cv2.rectangle(crop, (x1-left, y1-top), (x2-left, y2-top), (0, 255, 0), 2)
                caption = (f"{frame} #{key} T{row['candidate_track_id']}"
                           if row["candidate_box"] else f"{frame} #{key} NO BOX")
                cv2.putText(crop, caption, (4, 22), cv2.FONT_HERSHEY_SIMPLEX,
                            .50, (0, 0, 0), 3)
                cv2.putText(crop, caption, (4, 22), cv2.FONT_HERSHEY_SIMPLEX,
                            .50, (255, 255, 255), 1)
                crops.append(crop)
            for start in range(0, len(crops), 20):
                page = np.full((1200, 1500, 3), 255, dtype=np.uint8)
                for offset, crop in enumerate(crops[start:start + 20]):
                    y, x = divmod(offset, 5)
                    page[y*300:(y+1)*300, x*300:(x+1)*300] = crop
                cv2.imwrite(str(OUT / f"player{key}_review_{start//20+1:02d}.jpg"), page)
    finally:
        video.release()
    result = {"frames": LAST-FIRST+1, "players": player_ids,
              "selected_boxes": sum(bool(row["candidate_box"]) for row in rows),
              "possible_player_frames": len(rows),
              "unassigned": [{"frame": row["frame_index"], "player_id": row["player_id"]}
                             for row in rows if not row["candidate_box"]],
              "low_iou": [{"frame": row["frame_index"], "player_id": row["player_id"],
                           "iou": row["anchor_iou"]} for row in rows
                          if row["candidate_box"] and row["anchor_iou"] < .4]}
    (OUT / "preparation_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def score_reviewed():
    with (OUT / "assisted_paths.csv").open(newline="", encoding="utf-8") as stream:
        reference = list(csv.DictReader(stream))
    review = json.loads((OUT / "visual_review.json").read_text())
    selected = sum(bool(row["candidate_box"]) for row in reference)
    if selected != review["selected_detection_identities_confirmed"]:
        raise ValueError("Reference changed after visual review")
    if len(reference) - selected != review["unassigned_player_slots_reviewed"]:
        raise ValueError("Unassigned slot count changed after visual review")
    dense = json.loads((OUT / "tracker_predictions.json").read_text())
    calibration = json.loads((MATCH / "pilot/calibration/camera_r2_r5.json").read_text())
    matrix = image_to_court(calibration)
    predictions = {}
    for frame, people in dense["predictions"].items():
        predictions[frame] = [pred for pred in people if in_target_region(
            project([(pred["bbox"][0] + pred["bbox"][2])/2,
                     pred["bbox"][3]], matrix), False)]
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    try:
        observations = extract_observations(
            video, "r2", {"frames": {frame: {} for frame in predictions}},
            {"predictions": predictions}, matrix)
    finally:
        video.release()
    aliases, evidence = duplicate_track_aliases(observations)
    methods = {"byte_track": lambda value: value,
               "duplicate_merge": lambda value: aliases.get(value, value)}
    report = {"window": "r2 frames 78100-78150 inclusive; 51 consecutive frames",
              "validation_note": "Frozen r4 duplicate merge thresholds and logic, no tuning on r2.",
              "reference_note": "Assisted detector boxes anchored at two saved frames; selected identity paths visually checked on all player close-up sheets. Conditional identity diagnostic, not formal IDF1.",
              "duplicate_merge_evidence": evidence, "methods": {}}
    details = []
    for method, transform in methods.items():
        rows = []
        for entry in reference:
            source_id = int(entry["candidate_track_id"]) if entry["candidate_track_id"] else None
            row = {"method": method, "frame_index": int(entry["frame_index"]),
                   "player_id": entry["player_id"],
                   "track_id": transform(source_id) if source_id is not None else None,
                   "source_track_id": source_id,
                   "review_status": ("visual_identity_verified" if source_id is not None
                                     else "unassigned_visual_reviewed")}
            rows.append(row)
            details.append(row)
        report["methods"][method] = score(rows, method)
    (OUT / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    with (OUT / "identity_assignments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    print(json.dumps(report["methods"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", action="store_true", help="score after visual review")
    args = parser.parse_args()
    os.environ["YOLO_CONFIG_DIR"] = str(Path("data/processed/ultralytics_config").resolve())
    if args.score:
        score_reviewed()
    else:
        prepare()


if __name__ == "__main__":
    main()
