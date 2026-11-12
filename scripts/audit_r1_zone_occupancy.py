"""Conservative coarse court-zone audit for the r1 blue #9 candidate path."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MPL_CACHE = ROOT / "data/processed/.matplotlib_cache"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import median_filter


BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
LABELS = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r1.json"
START, END = 21070, 21464
WINDOWS = (5, 15, 31)
MARGIN_M = 0.6


def zone(point, margin=MARGIN_M):
    x, y = map(float, point)
    if not (0 <= x <= 9 and 0 <= y <= 9):
        return None
    if any(abs(coord-line) < margin for coord in (x, y) for line in (3, 6)):
        return None
    columns = ("left", "middle", "right")
    rows = ("back", "middle", "front")
    return f"{rows[min(2, int(y//3))]}_{columns[min(2, int(x//3))]}"


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32))
    image_points = []
    for frame in range(START, END):
        matches = [row for row in raw["frames"][str(frame)] if row["track_id"] == 3]
        if len(matches) != 1:
            raise RuntimeError(f"Missing or duplicated #9 anchor on frame {frame}")
        x1, _, x2, y2 = matches[0]["bbox"]
        image_points.append([(x1+x2)/2, y2])
    court = cv2.perspectiveTransform(np.asarray([image_points], dtype=np.float32), matrix)[0]
    smoothed = {width: np.column_stack([
        median_filter(court[:,dim], size=width, mode="nearest")
        for dim in (0, 1)]) for width in WINDOWS}
    rows = []
    counts = {"back_middle": 0, "back_right": 0, "unresolved": 0}
    for index, frame in enumerate(range(START, END)):
        choices = [zone(smoothed[width][index]) for width in WINDOWS]
        assigned = choices[0] if choices[0] is not None and len(set(choices)) == 1 else None
        name = assigned or "unresolved"
        counts[name] = counts.get(name, 0)+1
        rows.append({"frame": frame, "zone": name})

    saved_comparisons = []
    for frame_text, record in labels["frames"].items():
        frame = int(frame_text)
        if not START <= frame < END:
            continue
        player = next(p for p in record["players"] if p["player_id"] == "9")
        if player["position_status"] != "visible" or player["footpoint"] is None:
            continue
        saved_xy = cv2.perspectiveTransform(
            np.asarray([[player["footpoint"]]], dtype=np.float32), matrix)[0, 0]
        saved_comparisons.append({"frame": frame, "saved_click_zone": zone(saved_xy) or "unresolved",
                                  "candidate_zone": rows[frame-START]["zone"]})

    result = {
        "status": "development_coarse_zone_candidate_not_validated",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "9",
        "source_frames_inclusive": [START, END-1],
        "zone_grid_m": {"width_boundaries": [0, 3, 6, 9],
                        "depth_boundaries_from_near_baseline": [0, 3, 6, 9]},
        "boundary_uncertainty_margin_m": MARGIN_M,
        "median_filter_windows_frames": list(WINDOWS),
        "rule": "Assign a 3 m zone only if every smoothed path is at least 0.6 m from both internal grid lines and all three windows agree; otherwise unresolved.",
        "counts": counts,
        "saved_visible_footpoint_comparisons": saved_comparisons,
        "per_frame": rows,
        "limits": ["0.6 m is a conservative review margin, not a measured error bound.",
                   "Source identity and court calibration are single-reviewer development evidence.",
                   "Zone counts are not production metrics or independently validated occupancy."],
        "production_metric_changed": False,
    }
    (BASE/"r1_player9_zone_audit.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")

    path = smoothed[15]
    unresolved = np.asarray([row["zone"] == "unresolved" for row in rows])
    fig, ax = plt.subplots(figsize=(6, 6))
    for line in (0, 3, 6, 9):
        ax.axhline(line, color="0.65", linewidth=1)
        ax.axvline(line, color="0.65", linewidth=1)
    ax.plot(path[:,0], path[:,1], color="#165aa7", linewidth=1, alpha=.5)
    ax.scatter(path[~unresolved,0], path[~unresolved,1], s=7, color="#165aa7", label="stable zone")
    ax.scatter(path[unresolved,0], path[unresolved,1], s=7, color="#dc8a24", label="unresolved")
    ax.set(xlim=(-.3,9.3), ylim=(-.3,9.3), xlabel="court width (m)",
           ylabel="toward net (m)", title="Blue #9: candidate coarse court zones")
    ax.set_aspect("equal");ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout();fig.savefig(BASE/"r1_player9_zone_audit.png", dpi=160);plt.close(fig)
    print(counts)


if __name__ == "__main__":
    main()
