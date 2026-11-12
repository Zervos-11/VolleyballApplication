"""Bounded development path estimates for source-checked r1 anchor tracks.

Distances are smoothed detector-box-bottom paths, not validated player travel.
"""

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
WINDOWS = (3, 5, 9, 15, 21, 31)


def positions(raw, matrix, track_id, start, end):
    pixels = []
    for frame in range(start, end):
        boxes = [row for row in raw["frames"][str(frame)]
                 if row["track_id"] == track_id]
        if len(boxes) != 1:
            raise RuntimeError(f"Expected one box for T{track_id} on frame {frame}")
        x1, _, x2, y2 = boxes[0]["bbox"]
        pixels.append([(x1+x2)/2, y2])
    return cv2.perspectiveTransform(np.asarray([pixels], dtype=np.float32), matrix)[0]


def smooth(points, width):
    return np.column_stack([median_filter(points[:,dim], size=width, mode="nearest")
                            for dim in (0, 1)])


def distance(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def method_lengths(points):
    return {str(width): round(distance(smooth(points, width)), 3) for width in WINDOWS}


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32))
    end = raw["end_frame_exclusive"]

    # Source crops show #9 grounded by 21070 after the serve. Track 3 is present
    # on every source frame and was checked at the sparse labels plus 16 source crops.
    p9_start = 21070
    p9 = positions(raw, matrix, 3, p9_start, end)
    p9_lengths = method_lengths(p9)
    p9_differences = []
    for frame_text, frame in labels["frames"].items():
        frame_index = int(frame_text)
        if frame_index < p9_start or frame_index >= end:
            continue
        player = next(p for p in frame["players"] if p["player_id"] == "9")
        if player["position_status"] != "visible" or player["footpoint"] is None:
            continue
        saved = cv2.perspectiveTransform(
            np.asarray([[player["footpoint"]]], dtype=np.float32), matrix)[0, 0]
        p9_differences.append(round(float(np.linalg.norm(saved-p9[frame_index-p9_start])), 3))

    # Source frames 21308 and 21313 show yellow #20 on either side of a four-frame
    # box-height failure. Repair only this diagnostic path, with no released metric.
    p20_start = 21100
    p20 = positions(raw, matrix, 22, p20_start, end)
    repaired = p20.copy()
    for frame_index in range(21309, 21313):
        fraction = (frame_index-21308)/5
        repaired[frame_index-p20_start] = (
            (1-fraction)*p20[21308-p20_start]
            + fraction*p20[21313-p20_start])
    p20_lengths = method_lengths(repaired)

    record = {
        "status": "single_reviewer_development_estimate_not_validated_travel",
        "source_raw_tracks": str(RAW.relative_to(ROOT)).replace("\\", "/"),
        "calibration": str(CALIBRATION.relative_to(ROOT)).replace("\\", "/"),
        "fps_nominal": 50.0,
        "player_9": {
            "track_id": 3,
            "source_frames_inclusive": [p9_start, end-1],
            "frames_with_raw_box": len(p9),
            "identity_evidence": ["r1 dense audit anchors", "p9_serve_landing_sheet.jpg",
                                  "p9_dense_source_samples.jpg", "anchor_tracks_sheet.jpg"],
            "position_method": "Homography projection of raw box bottom; 15-frame median filter on court coordinates",
            "rough_smoothed_box_bottom_path_m": p9_lengths["15"],
            "method_sensitivity_median_width_frames_to_path_m": p9_lengths,
            "saved_footpoint_vs_box_bottom_visible_n": len(p9_differences),
            "saved_footpoint_vs_box_bottom_median_m": round(float(np.median(p9_differences)), 3),
            "saved_footpoint_vs_box_bottom_max_m": round(max(p9_differences), 3),
            "net_endpoint_displacement_m": round(float(np.linalg.norm(p9[-1]-p9[0])), 3),
            "limits": "Smoothing range is method sensitivity, not a confidence interval or validated physical travel. Sparse floor clicks are unreviewed."
        },
        "player_20": {
            "track_id": 22,
            "source_frames_inclusive": [p20_start, end-1],
            "frames_with_raw_box": len(p20),
            "bad_box_bottom_frames_inclusive": [21309, 21312],
            "repair": "Linear court-position interpolation between source-checked frames 21308 and 21313, diagnostic only",
            "raw_box_bottom_at_21310_court_m": [round(float(v), 3) for v in p20[21310-p20_start]],
            "method_sensitivity_after_repair_median_width_frames_to_path_m": p20_lengths,
            "distance_status": "withheld_due_to_pose_and_smoothing_sensitivity"
        },
        "production_metric_changed": False,
        "official_annotations_changed": False
    }
    (BASE/"r1_anchor_path_estimate.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")

    path = smooth(p9, 15)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0,9,9,0,0],[0,0,9,9,0],color="black",lw=1)
    ax.plot([0,9],[6,6],color="0.6",ls="--",lw=1)
    ax.plot([0,9],[9,9],color="0.5",lw=2)
    ax.plot(path[:,0], path[:,1],color="#165aa7",lw=1.8)
    ax.scatter(path[0,0],path[0,1],s=75,c="#2e8b57",label="grounded start",zorder=3)
    ax.scatter(path[-1,0],path[-1,1],s=75,c="#d04a35",label="point end",zorder=3)
    ax.set(xlim=(-0.3,9.3),ylim=(-0.3,9.3),xlabel="court width (m)",ylabel="toward net (m)",
           title="Blue #9: provisional box-bottom path")
    ax.set_aspect("equal");ax.grid(alpha=.2);ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(BASE/"r1_player9_candidate_path.png",dpi=160)
    plt.close(fig)
    print(f"#9 {p9_lengths['15']:.2f} m smoothed proxy; #20 metric withheld")


if __name__ == "__main__":
    main()
