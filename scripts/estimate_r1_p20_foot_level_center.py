"""Development distance proxy from #20's foot-level centre, with audit fields.

Two shoe cues supply the horizontal centre and the lower visible shoe supplies
the image height. A valid player box supplies the fallback foot-level centre.
Neither cue certifies ground contact or turns this into measured player travel.
"""

from __future__ import annotations

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

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


SHOES = BASE / "r1_p20_body_shoe_contact_trial.json"
ANCHORS = BASE / "r1_p20_late_contact_anchor_review.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
OUT = BASE / "r1_p20_foot_level_center_distance_trial.json"
PLOT = BASE / "r1_p20_foot_level_center_path.png"
START, END = 21050, 21464
COMPARISON_START = 21100
WINDOWS = (5, 15, 31)


def smoothed_length(points: np.ndarray, width: int) -> float:
    smoothed = np.column_stack([median_filter(points[:, axis], size=width, mode="nearest")
                                for axis in (0, 1)])
    return float(np.linalg.norm(np.diff(smoothed, axis=0), axis=1).sum())


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    shoes = json.loads(SHOES.read_text(encoding="utf-8"))
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert shoes["source_sha256"] == sha256(SOURCE)
    assert shoes["visual_candidate_sha256"] == sha256(VISUAL)
    assert anchors["shoe_trial_sha256"] == sha256(SHOES)
    assert calibration["image_size"] == [1920, 1080]
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    shoe_by_frame = {row["frame"]: row for row in shoes["frames"]}
    rows = []
    for record in visual["frame_records"]:
        frame = record["frame"]
        if not START <= frame < END:
            continue
        player = record["players"]["20"]
        box = player["bbox_px"] if player["box_status"] == "raw_box_candidate" else None
        point = None
        method = "missing_parent_box"
        if box is not None:
            point = [(box[0] + box[2]) / 2, box[3]]
            method = "box_bottom_center"
            regions = shoe_by_frame.get(frame, {}).get("selected_regions", [])
            if len(regions) == 2:
                cues = [region["sole_cue_px"] for region in regions]
                point = [(cues[0][0] + cues[1][0]) / 2, max(cues[0][1], cues[1][1])]
                method = "two_shoe_horizontal_midpoint_lower_shoe_height"
        rows.append({"frame": frame, "method": method,
                     "foot_level_center_px": [round(float(v), 2) for v in point] if point else None,
                     "court_position_m_diagnostic": None})
    assert [row["frame"] for row in rows] == list(range(START, END))

    observed = np.asarray([row["foot_level_center_px"] if row["foot_level_center_px"]
                           else [np.nan, np.nan] for row in rows], dtype=np.float32)
    missing = np.flatnonzero(~np.isfinite(observed[:, 0]))
    assert missing.tolist() == list(range(21309 - START, 21313 - START))
    # Source frames on either side show #20. Bridge the four invalid box frames
    # only in the diagnostic path; their per-frame positions stay unknown.
    filled = observed.copy()
    for index in missing:
        fraction = (index - (21308 - START)) / 5
        filled[index] = ((1 - fraction) * observed[21308 - START]
                         + fraction * observed[21313 - START])
    court = cv2.perspectiveTransform(filled[None, :, :], matrix)[0]
    for index, row in enumerate(rows):
        if row["foot_level_center_px"] is not None:
            row["court_position_m_diagnostic"] = [round(float(v), 3) for v in court[index]]

    distances = {}
    for label, begin in (("full_candidate_point", START), ("active_comparison_interval", COMPARISON_START)):
        part = court[begin - START:]
        distances[label] = {str(width): round(smoothed_length(part, width), 3)
                            for width in WINDOWS}
        distances[label]["unsmoothed"] = round(float(np.linalg.norm(
            np.diff(part, axis=0), axis=1).sum()), 3)

    methods = {name: sum(row["method"] == name for row in rows)
               for name in sorted({row["method"] for row in rows})}
    row_by_frame = {row["frame"]: row for row in rows}
    anchor_comparisons = []
    for anchor in anchors["frames"]:
        proposal = anchor["floor_point_proposal_px"]
        candidate = row_by_frame[anchor["frame"]]["foot_level_center_px"]
        if proposal is None or candidate is None:
            continue
        anchor_comparisons.append({
            "frame": anchor["frame"],
            "source_contact_type": anchor["source_visual_state"],
            "centre_vs_contact_px": round(float(np.linalg.norm(
                np.subtract(candidate, proposal))), 1),
        })
    anchor_differences = [row["centre_vs_contact_px"] for row in anchor_comparisons]
    result = {
        "status": "development_foot_level_center_distance_proxy",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "shoe_trial_sha256": sha256(SHOES),
        "contact_anchor_sha256": sha256(ANCHORS),
        "staged_calibration_sha256": sha256(CALIBRATION),
        "player_id": "20", "frames_inclusive": [START, END - 1], "fps_nominal": 50,
        "position_rule": "For two selected shoes, mean their image x coordinates and use the lower shoe sole-cue image y. Otherwise use the valid player-box bottom centre.",
        "missing_box_interpolation": "Frames 21309-21312 are bridged only to calculate smoothed diagnostic totals; their positions remain null in per_frame.",
        "method_counts": methods, "median_filter_width_frames": list(WINDOWS),
        "distance_proxy_m_by_interval_and_window": distances,
        "single_reviewer_contact_comparison": {
            "frames": anchor_comparisons,
            "comparable_count": len(anchor_comparisons),
            "median_pixel_difference": round(float(np.median(anchor_differences)), 1),
            "maximum_pixel_difference": round(max(anchor_differences), 1),
        },
        "per_frame": rows,
        "limits": ["Shoe regions and the box fallback are not independently verified floor contacts.",
                   "A raised or overlapping shoe can move the proxy; the lower image shoe is only a heuristic.",
                   "The four interpolated frames and the staged homography affect the total.",
                   "The smoothing range is method sensitivity, not an accuracy interval or validated travel."],
        "physical_distance_released": False,
        "production_metric_changed": False, "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 9, 9, 0, 0], [0, 0, 9, 9, 0], color="black", lw=1)
    ax.plot([0, 9], [6, 6], color="0.6", ls="--", lw=1)
    smooth = np.column_stack([median_filter(court[:, axis], size=15, mode="nearest")
                              for axis in (0, 1)])
    ax.plot(smooth[:, 0], smooth[:, 1], color="#b26520", lw=1.5)
    ax.scatter(smooth[0, 0], smooth[0, 1], color="green", s=50, label="candidate start")
    ax.scatter(smooth[-1, 0], smooth[-1, 1], color="red", s=50, label="candidate end")
    ax.set(xlim=(-0.5, 9.5), ylim=(-0.5, 9.5), xlabel="court width (m)",
           ylabel="toward net (m)", title="#20: provisional foot-level centre path")
    ax.set_aspect("equal")
    ax.grid(alpha=.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT, dpi=160)
    plt.close(fig)
    print({"method_counts": methods, "distances": distances})


if __name__ == "__main__":
    main()
