"""Summarize user-checked D79 floor points without assuming a court calibration."""

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
BACKGROUND = ROOT / "data/matches/yt_D79JrsJsFgs/screening/court_median_40s.jpg"
OUTPUT = ROOT / "data/processed/d79_new_source"
COLORS = {
    "98": (60, 210, 255), "8": (255, 150, 40), "9": (70, 220, 70),
    "23": (220, 70, 220), "4": (40, 70, 240), "15": (230, 230, 60),
}


def smoothed_path(points, width=5):
    half = width // 2
    return np.asarray([
        np.median(points[max(0, i - half):min(len(points), i + half + 1)], axis=0)
        for i in range(len(points))
    ])


def length(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()) if len(points) > 1 else 0.0


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    frames = range(240, 290)
    by_id = defaultdict(list)
    rows = []
    for frame in frames:
        record = data["frames"][str(frame)]
        if not record["all_players_accounted_for"]:
            raise ValueError(f"incomplete frame {frame}")
        for player in record["players"]:
            pid = str(player["player_id"])
            point = player.get("footpoint")
            visible = player.get("position_status") == "visible"
            if visible != (point is not None):
                raise ValueError(f"footpoint/status mismatch: {frame} #{pid}")
            if point is not None and (len(point) != 2 or not np.isfinite(point).all()):
                raise ValueError(f"invalid footpoint: {frame} #{pid}")
            by_id[pid].append((frame, point))
            rows.append({"frame": frame, "player_id": pid,
                         "position_status": player["position_status"],
                         "foot_x_px": "" if point is None else round(point[0], 3),
                         "foot_y_px": "" if point is None else round(point[1], 3)})

    background = cv2.imread(str(BACKGROUND))
    if background is None:
        raise FileNotFoundError(BACKGROUND)
    canvas = background.copy()
    canvas = cv2.addWeighted(canvas, 0.58, np.full_like(canvas, 255), 0.42, 0)
    summary = {"status": "user_checked_assisted_image_space_case_study",
               "source_annotations": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
               "annotations_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               "frame_range_inclusive": [240, 289], "fps": 60,
               "elapsed_s_between_endpoints": round(49 / 60, 4),
               "calibration_status": "none_confirmed_for_this_source",
               "distance_policy": "Only adjacent visible frames are joined. No path is inferred through occlusion. Pixel paths are descriptive and cannot be converted to metres without a validated court calibration. Five-frame medians are an image-space jitter diagnostic, not physical distance.",
               "players": {}}
    for pid, sequence in sorted(by_id.items(), key=lambda item: int(item[0])):
        if len(sequence) != 50:
            raise ValueError(f"missing player-frame slot for #{pid}")
        segments = []
        segment = []
        for frame, point in sequence:
            if point is None:
                if segment:
                    segments.append(segment)
                    segment = []
            else:
                segment.append((frame, point))
        if segment:
            segments.append(segment)
        raw = 0.0
        smooth = 0.0
        smoothed_segments = 0
        max_step = 0.0
        for segment in segments:
            points = np.asarray([point for _, point in segment], dtype=float)
            raw += length(points)
            if len(points) >= 5:
                smooth += length(smoothed_path(points))
                smoothed_segments += 1
            if len(points) > 1:
                max_step = max(max_step, float(np.linalg.norm(np.diff(points, axis=0), axis=1).max()))
            color = COLORS[pid]
            pix = np.rint(points).astype(int)
            if len(pix) > 1:
                cv2.polylines(canvas, [pix], False, color, 3, cv2.LINE_AA)
            cv2.circle(canvas, tuple(pix[0]), 6, color, -1, cv2.LINE_AA)
            cv2.circle(canvas, tuple(pix[-1]), 5, color, 2, cv2.LINE_AA)
            cv2.putText(canvas, f"#{pid}", tuple(pix[-1] + [8, -6]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
        summary["players"][pid] = {
            "visible_footpoints": sum(len(s) for s in segments),
            "occluded_frame_slots": 50 - sum(len(s) for s in segments),
            "observed_segments_inclusive": [[s[0][0], s[-1][0]] for s in segments],
            "joined_adjacent_steps": sum(max(0, len(s) - 1) for s in segments),
            "raw_image_path_px": round(raw, 2),
            "five_frame_median_path_px": round(smooth, 2) if smoothed_segments else None,
            "segment_endpoint_displacement_px": round(sum(
                float(np.linalg.norm(np.asarray(s[-1][1]) - np.asarray(s[0][1])))
                for s in segments
            ), 2),
            "largest_adjacent_step_px": round(max_step, 2),
        }
    cv2.putText(canvas, "D79 user-checked footpoints, frames 240-289", (30, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (10, 10, 10), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Paths stop at occlusion; pixels are not metres", (30, 67),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2, cv2.LINE_AA)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "checked_footpaths_240_289.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (OUTPUT / "checked_footpoints_240_289.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if not cv2.imwrite(str(OUTPUT / "checked_footpaths_240_289.jpg"), canvas):
        raise RuntimeError("could not write footpath overlay")
    print(json.dumps(summary["players"], indent=2))


if __name__ == "__main__":
    main()
