"""Sample pose ankles as a possible #20 shoe-association cue, never floor points."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".server-logs" / "ultralytics"))

import cv2
import numpy as np
from ultralytics import YOLO

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


MODEL = ROOT / "yolov8n-pose.pt"
SHOES = BASE / "r1_p20_body_shoe_contact_trial.json"
OUT = BASE / "r1_p20_pose_ankle_association_trial.json"
PREVIEW = BASE / "r1_p20_pose_ankle_association_sheet.jpg"
FRAMES = (21300, 21333, 21343, 21390, 21402, 21420, 21430, 21440)
CROP = (560, 590, 850, 855)


def iou(box, boxes):
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area = (box[2] - box[0]) * (box[3] - box[1])
    other = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return intersection / np.maximum(1e-6, area + other - intersection)


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    shoes = json.loads(SHOES.read_text(encoding="utf-8"))
    assert shoes["source_sha256"] == sha256(SOURCE)
    assert shoes["visual_candidate_sha256"] == sha256(VISUAL)
    visual_rows = {row["frame"]: row for row in visual["frame_records"]}
    shoe_rows = {row["frame"]: row for row in shoes["frames"]}
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    try:
        for frame_no in FRAMES:
            target = visual_rows[frame_no]["players"]["20"]
            if target["box_status"] != "raw_box_candidate":
                raise ValueError(f"No usable #20 box at {frame_no}")
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {frame_no}")
            pose = model.predict(frame, imgsz=960, conf=0.2, verbose=False)[0]
            boxes = pose.boxes.xyxy.cpu().numpy()
            overlaps = iou(np.asarray(target["bbox_px"], float), boxes)
            index = int(np.argmax(overlaps)) if len(overlaps) else None
            valid = bool(index is not None and overlaps[index] >= 0.5)
            ankles = []
            if valid and pose.keypoints is not None:
                points = pose.keypoints.xy.cpu().numpy()[index]
                confidence = pose.keypoints.conf.cpu().numpy()[index]
                for keypoint in (15, 16):
                    point = points[keypoint]
                    ankles.append({"coco_keypoint": keypoint,
                                   "point_px": [round(float(v), 2) for v in point],
                                   "confidence": round(float(confidence[keypoint]), 3)})
            candidates = [region["sole_cue_px"] for region in shoe_rows[frame_no]["selected_regions"]]
            associations = []
            for ankle in ankles:
                distances = [math.dist(ankle["point_px"], point) for point in candidates]
                order = sorted(range(len(distances)), key=lambda i: distances[i])
                associations.append({"coco_keypoint": ankle["coco_keypoint"],
                                     "nearest_shoe_region_index": order[0] if order else None,
                                     "nearest_distance_px": round(distances[order[0]], 2) if order else None,
                                     "nearest_vs_second_margin_px": round(distances[order[1]] - distances[order[0]], 2)
                                     if len(order) > 1 else None})
            distinct = (len(candidates) == 2 and len(associations) == 2
                        and associations[0]["nearest_shoe_region_index"] !=
                        associations[1]["nearest_shoe_region_index"]
                        and all(a["nearest_vs_second_margin_px"] >= 5 for a in associations))
            row = {"frame": frame_no, "pose_box_iou": round(float(overlaps[index]), 3) if index is not None else None,
                   "pose_match_valid": valid, "ankles": ankles,
                   "body_shoe_regions_px": candidates,
                   "ankle_to_shoe_nearest_region": associations,
                   "distinct_shoe_association_with_5px_margin": distinct,
                   "ground_contact_px": None, "court_position_m": None}
            rows.append(row)
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (580, 530))
            for ankle in ankles:
                x, y = ankle["point_px"]
                colour = (255, 0, 255) if ankle["coco_keypoint"] == 15 else (0, 255, 255)
                cv2.circle(tile, (round((x - x0) * 2), round((y - y0) * 2)), 7, colour, -1)
            for x, y in candidates:
                cv2.circle(tile, (round((x - x0) * 2), round((y - y0) * 2)), 12, (0, 255, 0), 2)
            cv2.putText(tile, str(frame_no), (8, 26), cv2.FONT_HERSHEY_SIMPLEX,
                        .8, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    blank = np.full_like(tiles[0], 30)
    tiles += [blank] * (8 - len(tiles))
    cv2.imwrite(str(PREVIEW), cv2.vconcat([cv2.hconcat(tiles[i:i + 2])
                                         for i in (0, 2, 4, 6)]))
    summary = {"sampled_frames": len(rows),
               "pose_box_matched": sum(row["pose_match_valid"] for row in rows),
               "frames_with_two_confident_ankles": sum(sum(ankle["confidence"] >= .5
                                                          for ankle in row["ankles"]) == 2
                                                     for row in rows),
               "two_shoe_region_frames": sum(len(row["body_shoe_regions_px"]) == 2 for row in rows),
               "distinct_shoe_association_frames": [row["frame"] for row in rows
                                                     if row["distinct_shoe_association_with_5px_margin"]],
               "two_region_ambiguous_association_frames": [row["frame"] for row in rows
                                                          if len(row["body_shoe_regions_px"]) == 2
                                                          and not row["distinct_shoe_association_with_5px_margin"]]}
    result = {"status": "development_pose_ankle_shoe_association_trial",
              "source_sha256": sha256(SOURCE), "visual_candidate_sha256": sha256(VISUAL),
              "shoe_trial_sha256": sha256(SHOES), "pose_model_sha256": sha256(MODEL),
              "settings": {"imgsz": 960, "confidence": .2, "pose_box_iou_min": .5},
              "observations": rows, "preview": PREVIEW.name,
              "preview_legend": "Magenta and yellow dots are the pose model's COCO ankle joints 15 and 16; green circles are #20 white-shoe region candidates.",
              "summary": summary,
              "limitation": "Pose ankles can be missing, swapped, or associated with the wrong player. They are joints above the shoes and cannot be projected as floor contacts. This trial makes no distance estimate.",
              "production_metric_changed": False, "official_annotations_changed": False}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
