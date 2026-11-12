"""Development-only coarse-zone audit for yellow #20 in the r1 point."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data/processed/.matplotlib_cache"))

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import median_filter

from audit_r1_zone_occupancy import zone


BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
LABELS = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r1.json"
START, END = 21100, 21464
BAD = range(21309, 21313)
WINDOWS = (5, 15, 31)


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32))
    pixels = []
    for frame in range(START, END):
        matches = [row for row in raw["frames"][str(frame)] if row["track_id"] == 22]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one #20 box on frame {frame}")
        x1, _, x2, y2 = matches[0]["bbox"]
        pixels.append([(x1+x2)/2, y2])
    court = cv2.perspectiveTransform(np.asarray([pixels], dtype=np.float32), matrix)[0]

    # The four source-checked truncated boxes are absent measurements. Interpolate
    # solely to keep the filters local; never publish their inferred zone.
    path = court.copy()
    for frame in BAD:
        weight = (frame-21308)/5
        path[frame-START] = (1-weight)*court[21308-START] + weight*court[21313-START]
    smoothed = {width: np.column_stack([
        median_filter(path[:, dim], size=width, mode="nearest")
        for dim in (0, 1)]) for width in WINDOWS}

    rows = []
    counts = {}
    for frame in range(START, END):
        index = frame-START
        choices = [zone(smoothed[width][index]) for width in WINDOWS]
        assigned = choices[0] if frame not in BAD and choices[0] is not None and len(set(choices)) == 1 else None
        name = assigned or "unresolved"
        counts[name] = counts.get(name, 0) + 1
        rows.append({"frame": frame, "zone": name,
                     "box_status": "truncated_withheld" if frame in BAD else "raw"})

    comparisons = []
    for frame_text, record in labels["frames"].items():
        frame = int(frame_text)
        if not START <= frame < END:
            continue
        player = next(p for p in record["players"] if p["player_id"] == "20")
        if player["position_status"] != "visible" or player["footpoint"] is None:
            continue
        saved = cv2.perspectiveTransform(
            np.asarray([[player["footpoint"]]], dtype=np.float32), matrix)[0, 0]
        comparisons.append({"frame": frame,
                            "saved_click_zone": zone(saved) or "unresolved",
                            "candidate_zone": rows[frame-START]["zone"]})

    result = {
        "status": "development_coarse_zone_candidate_not_validated",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "20",
        "track_id": 22, "source_frames_inclusive": [START, END-1],
        "zone_grid_m": [0, 3, 6, 9], "boundary_uncertainty_margin_m": 0.6,
        "median_filter_windows_frames": list(WINDOWS),
        "truncated_box_frames_withheld": [min(BAD), max(BAD)],
        "interpolation_use": "Filter support only; the four frames remain unresolved in the output.",
        "counts": counts, "saved_visible_footpoint_comparisons": comparisons,
        "per_frame": rows,
        "limits": ["The 0.6 m review margin is not a measured error bound.",
                   "Saved footpoints and staged calibration are single-reviewer development evidence.",
                   "Zones are not independently validated occupancy or physical travel."],
        "production_metric_changed": False, "official_annotations_changed": False,
    }
    (BASE / "r1_player20_zone_audit.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")

    path15 = smoothed[15]
    assigned = np.asarray([row["zone"] != "unresolved" for row in rows])
    fig, ax = plt.subplots(figsize=(6, 6))
    for line in (0, 3, 6, 9):
        ax.axhline(line, color="0.65", linewidth=1)
        ax.axvline(line, color="0.65", linewidth=1)
    ax.plot(path15[:, 0], path15[:, 1], color="#b26520", linewidth=1, alpha=.5)
    ax.scatter(path15[assigned, 0], path15[assigned, 1], s=7,
               color="#b26520", label="stable zone")
    ax.scatter(path15[~assigned, 0], path15[~assigned, 1], s=7,
               color="#666666", label="unresolved")
    ax.set(xlim=(-.3, 9.3), ylim=(-.3, 9.3), xlabel="court width (m)",
           ylabel="toward net (m)", title="Yellow #20: candidate coarse court zones")
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(BASE / "r1_player20_zone_audit.png", dpi=160)
    plt.close(fig)
    print(counts)


if __name__ == "__main__":
    main()
