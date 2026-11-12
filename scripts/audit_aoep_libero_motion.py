"""Quantify AoEP libero box-bottom jumps without converting them to speed."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
PATH = DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.json"
CALIBRATION = MATCH / "homography.json"
OUTPUT = DIR / "libero_motion_break_audit.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    rows = data["players"]["navy_libero_10"]
    frames = sorted(map(int, rows))
    points = np.asarray([rows[str(frame)]["bbox_bottom_centre_px"] for frame in frames], np.float32)
    if not np.isfinite(points).all() or not all(rows[str(frame)]["candidate_ground_position"] for frame in frames):
        raise ValueError("expected 50 continuous candidate pixel points")
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], np.float32),
        np.asarray(calibration["points_court_m"], np.float32),
    )
    court = cv2.perspectiveTransform(points.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    smoothed_px = np.asarray([
        np.median(points[max(0, index - 2):min(len(points), index + 3)], axis=0)
        for index in range(len(points))
    ], np.float32)
    smoothed_court = cv2.perspectiveTransform(
        smoothed_px.reshape(-1, 1, 2), matrix
    ).reshape(-1, 2)
    threshold = float(data["motion_review_threshold_m_per_frame"])
    original_step = np.linalg.norm(np.diff(court, axis=0), axis=1)
    smoothed_step = np.linalg.norm(np.diff(smoothed_court, axis=0), axis=1)
    breaks = []
    for index, metres in enumerate(original_step):
        if metres <= threshold:
            continue
        frame = frames[index + 1]
        previous = rows[str(frames[index])]
        current = rows[str(frame)]
        breaks.append({
            "frame_index": frame,
            "raw_track_id_previous": previous["raw_track_id_candidate"],
            "raw_track_id_current": current["raw_track_id_candidate"],
            "bbox_bottom_step_px": [round(float(v), 2) for v in points[index + 1] - points[index]],
            "projected_step_m": round(float(metres), 2),
            "five_frame_median_step_m": round(float(smoothed_step[index]), 2),
            "source_pair_review": "same_visible_navy_10_box_at_both_frames",
        })
    if [item["frame_index"] for item in breaks] != [
        item["frame_index"] for item in data["motion_discontinuities_by_player"]["navy_libero_10"]
    ]:
        raise ValueError("candidate path motion breaks changed")
    output = {
        "candidate_path_sha256": sha256(PATH),
        "calibration_sha256": sha256(CALIBRATION),
        "source_pair_sheet": "libero_all_motion_breaks_source.jpg",
        "frame_range_inclusive": [frames[0], frames[-1]],
        "review_threshold_m_per_adjacent_frame": threshold,
        "raw_break_count": len(breaks),
        "five_frame_median_remaining_break_count": int(np.count_nonzero(smoothed_step > threshold)),
        "largest_raw_step_m": round(float(np.max(original_step)), 2),
        "largest_five_frame_median_step_m": round(float(np.max(smoothed_step)), 2),
        "mean_median_adjustment_px": round(float(np.mean(np.linalg.norm(smoothed_px - points, axis=1))), 2),
        "breaks": breaks,
        "conclusion": "All 12 reviewed pairs show the same navy player, so these are not observed identity swaps. Changes in stance and box-bottom fit create metre-scale sensitivity. A five-frame median reduces but does not resolve the jump count; keep path breaks and do not publish speed or distance from this proxy.",
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in (
        "raw_break_count", "five_frame_median_remaining_break_count", "largest_raw_step_m"
    )}))


if __name__ == "__main__":
    main()
