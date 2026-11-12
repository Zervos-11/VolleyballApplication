"""Compare raw box-bottom endpoints around missing named-player runs.

Endpoint differences are diagnostics only; they do not measure travel inside a
gap, and no missing frame receives a box or court position.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
OUT = BASE / "r1_missing_run_endpoint_diagnostic.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bottom(box: list[float]) -> list[float]:
    return [(box[0] + box[2]) / 2, box[3]]


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    cal = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    transform = cv2.getPerspectiveTransform(np.float32(cal["points_px"]),
                                             np.float32(cal["points_court_m"]))
    rows = visual["frame_records"]
    by_frame = {row["frame"]: row["players"] for row in rows}
    first, last = rows[0]["frame"], rows[-1]["frame"]
    results = {}
    for player in visual["slot_counts"]:
        missing = [row["frame"] for row in rows
                   if row["players"][player]["box_status"] != "raw_box_candidate"]
        runs = []
        for frame in missing:
            if runs and frame == runs[-1][1] + 1:
                runs[-1][1] = frame
            else:
                runs.append([frame, frame])
        items = []
        for start, end in runs:
            before = by_frame.get(start - 1, {}).get(player)
            after = by_frame.get(end + 1, {}).get(player)
            if not before or not after or before["box_status"] != "raw_box_candidate" or after["box_status"] != "raw_box_candidate":
                items.append({"missing_frames_inclusive": [start, end], "gap_frames": end - start + 1,
                              "bounded_by_valid_boxes": False, "endpoint_pixel_displacement": None,
                              "endpoint_box_bottom_court_proxy_displacement_m": None})
                continue
            points_px = np.float32([[bottom(before["bbox_px"]), bottom(after["bbox_px"])]])
            points_court = cv2.perspectiveTransform(points_px, transform)[0]
            items.append({
                "missing_frames_inclusive": [start, end], "gap_frames": end - start + 1,
                "bounded_by_valid_boxes": True,
                "before_frame": start - 1, "after_frame": end + 1,
                "before_raw_track_id": before["raw_track_id"],
                "after_raw_track_id": after["raw_track_id"],
                "before_box_bottom_px": [round(float(v), 2) for v in points_px[0, 0]],
                "after_box_bottom_px": [round(float(v), 2) for v in points_px[0, 1]],
                "before_box_bottom_court_proxy_m": [round(float(v), 2) for v in points_court[0]],
                "after_box_bottom_court_proxy_m": [round(float(v), 2) for v in points_court[1]],
                "both_proxy_endpoints_inside_nominal_court": bool(np.all((points_court >= 0) & (points_court <= 9))),
                "endpoint_pixel_displacement": round(float(np.linalg.norm(np.diff(points_px[0], axis=0))), 2),
                "endpoint_box_bottom_court_proxy_displacement_m": round(float(np.linalg.norm(np.diff(points_court, axis=0))), 2),
            })
        results[player] = items
    payload = {
        "status": "missing_run_box_endpoint_diagnostic_not_travel",
        "visual_candidate_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "candidate_frames_inclusive": [first, last],
        "players": results,
        "interpretation": "Endpoint box-bottom projection is sensitive to stance, occlusion and camera perspective. A small endpoint displacement does not prove no movement inside a gap, and a larger one does not supply the missing path. No position is imputed or metric released.",
        "official_annotations_changed": False,
        "production_metric_changed": False,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for player in ("10", "11", "12", "13", "20"):
        big = [row for row in results[player] if row["gap_frames"] >= 8]
        print(player, [(row["missing_frames_inclusive"], row["endpoint_box_bottom_court_proxy_displacement_m"]) for row in big])


if __name__ == "__main__":
    main()
