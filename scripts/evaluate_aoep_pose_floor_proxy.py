"""Two-frame diagnostic: pose ankles versus box bottoms for AoEP players."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".server-logs" / "ultralytics"))

import cv2
import numpy as np
from ultralytics import YOLO


DIR = ROOT / "data/processed/aoep_new_source"
VIDEO = ROOT / "data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4"
PATHS = DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.json"
RAW = DIR / "raw_74880_75540.json"
CAL = ROOT / "data/matches/yt_AoEP-YiWRvc/homography.json"
MODEL = ROOT / "yolov8n-pose.pt"
OUTPUT = DIR / "pose_ankle_floor_proxy_75205_75229.json"
PREVIEW = DIR / "pose_ankle_floor_proxy_75205_75229.jpg"
FRAMES = (75205, 75229)
PLAYERS = ("yellow_centre_4", "navy_libero_10", "yellow_left_5")
LABELS = {"yellow_centre_4": "#4", "navy_libero_10": "#10", "yellow_left_5": "#5"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(pixel, matrix):
    return cv2.perspectiveTransform(np.asarray(pixel, np.float32).reshape(1, 1, 2), matrix).reshape(2)


def iou_one(box, boxes):
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area = (box[2] - box[0]) * (box[3] - box[1])
    other = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return intersection / np.maximum(1e-6, area + other - intersection)


def main():
    paths = json.loads(PATHS.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    if paths["source_sha256"] != sha256(VIDEO) or cal["source_sha256"] != paths["source_sha256"]:
        raise ValueError("source mismatch")
    matrix = cv2.getPerspectiveTransform(np.asarray(cal["points_px"], np.float32),
                                         np.asarray(cal["points_court_m"], np.float32))
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    rows, contact_sheet = [], []
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f"cannot read frame {frame}")
            result = model.predict(image, imgsz=960, conf=0.2, verbose=False)[0]
            boxes = result.boxes.xyxy.cpu().numpy()
            points = result.keypoints.xy.cpu().numpy()
            confidence = result.keypoints.conf.cpu().numpy()
            tiles = []
            for name in PLAYERS:
                path = paths["players"][name][str(frame)]
                track_id = path["raw_track_id_candidate"]
                matches = [item for item in raw["predictions"][str(frame)] if item["track_id"] == track_id]
                if len(matches) != 1:
                    raise ValueError(f"raw box mismatch {frame}/{name}")
                box = np.asarray(matches[0]["bbox"], dtype=float)
                overlap = iou_one(box, boxes)
                pose_index = int(np.argmax(overlap))
                if overlap[pose_index] < 0.5:
                    raise ValueError(f"weak pose match {frame}/{name}")
                ankle_xy = points[pose_index, [15, 16]]
                ankle_conf = confidence[pose_index, [15, 16]]
                chosen_index = int(np.argmax(ankle_conf))
                chosen = ankle_xy[chosen_index]
                bottom = np.asarray(path["bbox_bottom_centre_px"])
                court_ankle = project(chosen, matrix)
                court_bottom = np.asarray(path["court_position_m_diagnostic"])
                rows.append({
                    "frame_index": frame,
                    "visual_player_id": name,
                    "pose_box_iou": round(float(overlap[pose_index]), 2),
                    "ankle_keypoints_px": [[round(float(v), 1) for v in point] for point in ankle_xy],
                    "ankle_confidence": [round(float(v), 2) for v in ankle_conf],
                    "selected_ankle_index": [15, 16][chosen_index],
                    "ankle_above_box_bottom_px": round(float(bottom[1] - chosen[1]), 1),
                    "direct_ankle_projection_vs_box_bottom_m": round(float(np.linalg.norm(court_ankle - court_bottom)), 2),
                    "box_bottom_centre_px": path["bbox_bottom_centre_px"],
                })
                cx, cy = map(int, bottom)
                x0, x1 = max(0, cx - 95), min(image.shape[1], cx + 95)
                y0, y1 = max(0, cy - 145), min(image.shape[0], cy + 45)
                tile = image[y0:y1, x0:x1].copy()
                cv2.circle(tile, (cx - x0, cy - y0), 4, (0, 0, 255), -1)
                for point in ankle_xy:
                    cv2.circle(tile, (round(float(point[0])) - x0, round(float(point[1])) - y0), 4, (255, 0, 0), -1)
                cv2.putText(tile, f"{LABELS[name]} {frame}", (3, 20), cv2.FONT_HERSHEY_SIMPLEX, .55,
                            (255, 255, 255), 2)
                tiles.append(cv2.resize(tile, (380, 380)))
            contact_sheet.append(cv2.hconcat(tiles))
    finally:
        cap.release()
    cv2.imwrite(str(PREVIEW), cv2.vconcat(contact_sheet))
    output = {
        "status": "two_frame_pose_ankle_diagnostic_not_floor_contact",
        "source_sha256": paths["source_sha256"],
        "candidate_path_sha256": sha256(PATHS),
        "raw_sha256": sha256(RAW),
        "calibration_sha256": sha256(CAL),
        "pose_model_sha256": sha256(MODEL),
        "pose_settings": {"imgsz": 960, "detection_confidence": 0.2},
        "frames_reviewed": list(FRAMES),
        "preview": PREVIEW.name,
        "preview_sha256": sha256(PREVIEW),
        "preview_legend": "Blue dots are pose ankle joints; red dot is the box-bottom centre.",
        "observations": rows,
        "interpretation": "High-confidence ankle joints are above the visible shoe-floor contact. Directly homography-projecting an ankle as a floor point introduces a large spatial shift. Do not turn on use_pose_ankles for court metrics based on these samples; first derive and validate an actual ground-contact estimate.",
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    for row in rows:
        print(row["frame_index"], row["visual_player_id"], row["ankle_above_box_bottom_px"], row["direct_ankle_projection_vs_box_bottom_m"])


if __name__ == "__main__":
    main()
