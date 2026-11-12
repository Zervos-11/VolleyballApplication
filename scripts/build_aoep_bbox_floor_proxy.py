"""Build a diagnostic box-bottom court view from saved AoEP player boxes.

This does not edit annotations or activate the staged calibration for metrics.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
ANNOTATIONS = MATCH / "pilot/player_annotations/point_21m.json"
CALIBRATION = MATCH / "homography.json"
OUTPUT = ROOT / "data/processed/aoep_new_source/saved_bbox_floor_proxy.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    labels = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    width, height = calibration["image_size"]
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], np.float32),
        np.asarray(calibration["points_court_m"], np.float32),
    )
    bounds = calibration["court_bounds_m"]
    rows = []
    eligible_frames = defaultdict(set)
    for frame_key, frame in sorted(labels["frames"].items(), key=lambda item: int(item[0])):
        for player in frame["players"]:
            box = player.get("bbox")
            if box is None:
                continue
            frame_index = int(frame_key)
            player_id = player["player_id"]
            x1, y1, x2, y2 = map(float, box)
            proxy = [(x1 + x2) / 2, y2]
            projected = cv2.perspectiveTransform(
                np.asarray(proxy, np.float32).reshape(1, 1, 2), matrix
            ).reshape(2)
            reasons = []
            if x1 <= 1 or x2 >= width - 1 or y2 >= height - 1:
                reasons.append("box_touches_image_edge")
            if player.get("occlusion") in ("partial", "full"):
                reasons.append("body_occluded")
            if player.get("position_status") in ("airborne", "occluded", "out_of_frame"):
                reasons.append("saved_non_ground_position")
            if frame_index == 75180 and player_id == "18":
                reasons.append("source_visible_airborne_setter")
            if player.get("position_status") == "uncertain":
                reasons.append("ground_contact_not_confirmed")
            inside = bool(bounds[0] <= projected[0] <= bounds[1]
                          and bounds[2] <= projected[1] <= bounds[3])
            if not inside:
                reasons.append("outside_nominal_near_court")
            eligible = not reasons
            if eligible:
                eligible_frames[player_id].add(frame_index)
            rows.append({
                "frame_index": frame_index,
                "player_id": player_id,
                "box_bottom_centre_px": [round(v, 2) for v in proxy],
                "court_position_m_diagnostic": [round(float(v), 2) for v in projected],
                "provisional_ground_proxy_eligible": eligible,
                "review_reasons": reasons,
            })
    multi_frame_players = sorted(
        player_id for player_id, frames in eligible_frames.items() if len(frames) >= 2
    )
    output = {
        "source_sha256": calibration["source_sha256"],
        "annotations_sha256": sha256(ANNOTATIONS),
        "calibration_sha256": sha256(CALIBRATION),
        "method": "bbox bottom centre (x1+x2)/2,y2 projected through the staged AoEP homography",
        "status": "diagnostic_provisional_ground_proxy_not_metrics",
        "saved_box_count": len(rows),
        "provisional_ground_proxy_count": sum(row["provisional_ground_proxy_eligible"] for row in rows),
        "players_with_multiple_eligible_frames": multi_frame_players,
        "candidate_multi_frame_path_available": bool(multi_frame_players),
        "movement_metrics_published": False,
        "rows": rows,
        "limitation": "Box bottoms estimate feet only for full, grounded players. The saved AoEP boxes have no multi-frame eligible player path. Raw tracker IDs and interpolated body centres are not verified identities or ground positions.",
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in (
        "saved_box_count", "provisional_ground_proxy_count",
        "players_with_multiple_eligible_frames", "candidate_multi_frame_path_available"
    )}))


if __name__ == "__main__":
    main()
