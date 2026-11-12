"""Project saved AoEP floor contacts for review without activating court metrics."""

from __future__ import annotations

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
OUTPUT = ROOT / "data/processed/aoep_new_source/saved_floor_contact_audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    labels = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32),
    )
    xmin, xmax, ymin, ymax = calibration["court_bounds_m"]
    observations = []
    per_player = defaultdict(set)
    for frame_key, frame in sorted(labels["frames"].items(), key=lambda item: int(item[0])):
        for player in frame["players"]:
            if player.get("position_status") != "visible" or player.get("footpoint") is None:
                continue
            foot = np.asarray(player["footpoint"], dtype=np.float32)
            if foot.shape != (2,) or not np.isfinite(foot).all():
                raise ValueError(f"invalid footpoint for {frame_key}/{player['player_id']}")
            court = cv2.perspectiveTransform(foot.reshape(1, 1, 2), matrix).reshape(2)
            frame_id, player_id = int(frame_key), player["player_id"]
            per_player[player_id].add(frame_id)
            visual_review = "not_checked"
            note = "Projection is diagnostic until source-visible shoe-floor contact is checked."
            if frame_id == 75180 and player_id == "18":
                visual_review = "airborne_conflict"
                note = "Source frame shows both shoes above the floor; the saved 'visible' floor contact appears to mark an airborne shoe. Exclude from ground paths pending correction."
            elif frame_id == 75180 and player_id == "5":
                visual_review = "boundary_review"
                note = "Foot appears near the left sideline; projected x is outside the nominal court. Keep the original label and inspect the line assignment/contact before using metres."
            elif frame_id == 75180 and player_id == "19":
                visual_review = "boundary_review"
                note = "Projected y is just beyond the net floor line. Inspect the contact and court-line assignment before using metres."
            observations.append({
                "frame_index": frame_id,
                "player_id": player_id,
                "footpoint_px": [round(float(value), 2) for value in foot],
                "court_position_m_diagnostic": [round(float(value), 2) for value in court],
                "inside_nominal_near_court": bool(xmin <= court[0] <= xmax and ymin <= court[1] <= ymax),
                "source_visual_review": visual_review,
                "note": note,
            })
    result = {
        "source_sha256": calibration["source_sha256"],
        "calibration_sha256": sha256(CALIBRATION),
        "annotations_sha256": sha256(ANNOTATIONS),
        "calibration_use_for_metrics": calibration["use_for_metrics"],
        "source_frame_preview": "saved_footpoints_75180.jpg",
        "saved_frames": len(labels["frames"]),
        "saved_contact_count": len(observations),
        "players_with_two_or_more_contact_frames": sorted(
            player_id for player_id, frames in per_player.items() if len(frames) >= 2
        ),
        "movement_path_available": False,
        "observations": observations,
        "limitation": "A single contact frame per player cannot give movement, speed, or coverage. The staged calibration is disabled for production metrics. Source-visual conflicts need correction before a court path is used.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved_contacts": len(observations),
                      "players_with_two_or_more_contact_frames": result["players_with_two_or_more_contact_frames"],
                      "airborne_conflicts": sum(row["source_visual_review"] == "airborne_conflict" for row in observations)}))


if __name__ == "__main__":
    main()
