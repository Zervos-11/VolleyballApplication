"""Source-preview a pose-guided shoe-contact candidate on six AoEP crops."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
POSE = DIR / "pose_ankle_floor_proxy_75205_75229.json"
CAL = ROOT / "data/matches/yt_AoEP-YiWRvc/homography.json"
VIDEO = ROOT / "data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4"
OUTPUT = DIR / "pose_guided_contact_trial_75205_75229.json"
PREVIEW = DIR / "pose_guided_contact_trial_75205_75229.jpg"
LABELS = {"yellow_centre_4": "#4", "navy_libero_10": "#10", "yellow_left_5": "#5"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(point, matrix):
    return cv2.perspectiveTransform(np.asarray(point, np.float32).reshape(1, 1, 2), matrix).reshape(2)


def main():
    pose = json.loads(POSE.read_text(encoding="utf-8"))
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    if pose["source_sha256"] != sha256(VIDEO) or pose["calibration_sha256"] != sha256(CAL):
        raise ValueError("source or calibration changed")
    matrix = cv2.getPerspectiveTransform(np.asarray(cal["points_px"], np.float32),
                                         np.asarray(cal["points_court_m"], np.float32))
    observations = []
    frame_rows = []
    cap = cv2.VideoCapture(str(VIDEO))
    try:
        for frame in pose["frames_reviewed"]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(frame)
            tiles = []
            for name in LABELS:
                row = next(item for item in pose["observations"] if item["frame_index"] == frame
                           and item["visual_player_id"] == name)
                ankles = np.asarray(row["ankle_keypoints_px"], dtype=float)
                lower = int(np.argmax(ankles[:, 1]))
                bottom = np.asarray(row["box_bottom_centre_px"], dtype=float)
                candidate = np.asarray([ankles[lower, 0], bottom[1]])
                old_court, new_court = project(bottom, matrix), project(candidate, matrix)
                observations.append({
                    "frame_index": frame,
                    "visual_player_id": name,
                    "selected_lower_ankle_index": [15, 16][lower],
                    "ankle_confidence": row["ankle_confidence"][lower],
                    "candidate_px": [round(float(x), 1) for x in candidate],
                    "box_bottom_centre_px": row["box_bottom_centre_px"],
                    "horizontal_shift_px": round(float(candidate[0] - bottom[0]), 1),
                    "court_shift_from_box_bottom_m": round(float(np.linalg.norm(new_court - old_court)), 2),
                })
                cx, cy = map(int, bottom)
                x0, x1 = max(0, cx - 95), min(image.shape[1], cx + 95)
                y0, y1 = max(0, cy - 145), min(image.shape[0], cy + 45)
                tile = image[y0:y1, x0:x1].copy()
                cv2.circle(tile, (round(float(bottom[0])) - x0, round(float(bottom[1])) - y0),
                           4, (0, 0, 255), -1)
                cv2.circle(tile, (round(float(candidate[0])) - x0, round(float(candidate[1])) - y0),
                           4, (0, 200, 0), -1)
                cv2.putText(tile, f"{LABELS[name]} {frame}", (3, 20), cv2.FONT_HERSHEY_SIMPLEX, .55,
                            (255, 255, 255), 2)
                tiles.append(cv2.resize(tile, (380, 380)))
            frame_rows.append(cv2.hconcat(tiles))
    finally:
        cap.release()
    if not cv2.imwrite(str(PREVIEW), cv2.vconcat(frame_rows)):
        raise OSError(PREVIEW)
    result = {
        "status": "two_frame_pose_guided_contact_candidate_not_validated",
        "source_sha256": pose["source_sha256"],
        "pose_diagnostic_sha256": sha256(POSE),
        "calibration_sha256": sha256(CAL),
        "source_preview": PREVIEW.name,
        "source_preview_sha256": sha256(PREVIEW),
        "preview_legend": "Green: lower-ankle x at box-bottom y. Red: original box-bottom centre.",
        "method": "Select the pose ankle with larger image y as the likely lower foot. Use only its x coordinate; retain the detector box bottom y as a shoe-level approximation.",
        "observations": observations,
        "source_review": "The green marker aligns more closely with a visible shoe than the centre marker in the wide-stance #4 crops and several stride crops. In some crops it remains below or beside the actual sole. The rule does not detect airborne status, true contact height, or which foot bears weight.",
        "decision": "Development contact-location cue only. Do not replace the body-location path or enable movement metrics; a planted-foot path alternates feet and can overstate player travel.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    for row in observations:
        print(row["frame_index"], row["visual_player_id"], row["court_shift_from_box_bottom_m"])


if __name__ == "__main__":
    main()
