"""Exploratory team geometry on source-reviewed six-grounded S3 P34 frames."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import cv2
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib_cache"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
SCORE = SCREEN / "s3p34_reported_live_interval_score.json"
LEDGER = SCREEN / "s3p34_six_player_observation_ledger.json"
OPENING = SCREEN / "s3p34_opening_frame_review/manifest.json"
STAGED = SCREEN / "near_court_candidate.json"
REFINED = SCREEN / "s3p34_calibration_review/refined_candidate.json"
CALIBRATION = SCREEN / "s3p34_calibration_holdout/one_frame_diagnostic.json"
OUT = SCREEN / "s3p34_reported_live_geometry.json"
FIGURE = ROOT / "DELIVERABLES/figures/u5_s3p34_reported_live_geometry.png"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_REPORTED_LIVE_GEOMETRY.md"
SLOTS = ("28", "12", "15", "7", "19", "21")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mapped(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(points.reshape(1, -1, 2).astype(np.float64), matrix)[0]


def metrics(points: np.ndarray) -> dict[str, float]:
    distances = [float(np.linalg.norm(points[i] - points[j])) for i in range(6) for j in range(i + 1, 6)]
    hull = cv2.convexHull(points.astype(np.float32).reshape(-1, 1, 2))
    centre = points.mean(axis=0)
    return {"spacing_m": float(np.mean(distances)),
            "hull_area_m2": float(cv2.contourArea(hull)),
            "dispersion_m": float(np.mean(np.linalg.norm(points - centre, axis=1)))}


def main() -> None:
    score = json.loads(SCORE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    opening = json.loads(OPENING.read_text(encoding="utf-8"))
    staged = json.loads(STAGED.read_text(encoding="utf-8"))
    refined = json.loads(REFINED.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert score["interval_inclusive"] == [35998, 36137]
    assert refined["use_for_final_metrics"] is False
    assert calibration["frozen_two_frame_operational_pass"] is False
    assert ledger["source_sha256"] == opening["source_sha256"]
    old_matrix = np.asarray(staged["homography_image_to_court"], dtype=float)
    new_matrix = np.asarray(refined["homography_image_to_court"], dtype=float)
    inverse_old = np.linalg.inv(old_matrix)
    ledger_by_frame = {r["source_frame"]: r for r in ledger["frames"]}
    opening_by_frame = {r["frame"]: r for r in opening["rows"]}
    frames = []
    for frame in score["frames"]:
        n = frame["source_frame"]
        accepted = frame["accepted_grounded_proxies"] == 6
        result = {"source_frame": n, "eligible_six_grounded": accepted,
                  "accepted_grounded_proxies": frame["accepted_grounded_proxies"],
                  "staged_metrics": None, "refined_metrics": None,
                  "refined_minus_staged": None}
        if accepted:
            if n in opening_by_frame:
                boxes = opening_by_frame[n]["suggested_boxes"]
                pixels = np.array([[(boxes[slot][0] + boxes[slot][2]) / 2, boxes[slot][3]] for slot in SLOTS])
                staged_points = mapped(pixels, old_matrix)
                refined_points = mapped(pixels, new_matrix)
            else:
                old_court = np.asarray([ledger_by_frame[n]["players"][slot]["jersey_keyed_candidate_court_m"]
                                        for slot in SLOTS], dtype=float)
                pixels = mapped(old_court, inverse_old)
                staged_points = old_court
                refined_points = mapped(pixels, new_matrix)
            old = metrics(staged_points)
            new = metrics(refined_points)
            result.update({"staged_metrics": old, "refined_metrics": new,
                           "refined_minus_staged": {k: new[k] - old[k] for k in old},
                           "refined_court_positions_m": {slot: refined_points[i].round(4).tolist()
                                                         for i, slot in enumerate(SLOTS)}})
        frames.append(result)
    eligible = [r for r in frames if r["eligible_six_grounded"]]
    assert len(eligible) == score["counts"]["six_accepted_grounded_frames"] == 92
    summary = {}
    for key in ("spacing_m", "hull_area_m2", "dispersion_m"):
        values = np.array([r["refined_metrics"][key] for r in eligible])
        change = np.array([r["refined_minus_staged"][key] for r in eligible])
        summary[key] = {"median": float(np.median(values)), "minimum": float(values.min()),
                        "maximum": float(values.max()),
                        "median_absolute_refined_minus_staged": float(np.median(np.abs(change))),
                        "maximum_absolute_refined_minus_staged": float(np.max(np.abs(change)))}
    result = {"status": "exploratory_descriptive_same_camera_geometry_not_strict_metric_input",
              "interval_inclusive": score["interval_inclusive"],
              "eligible_frames": len(eligible), "total_frames": len(frames),
              "coordinate_rule": staged["coordinate_rule"],
              "input_sha256": {"reviewed_live_score": sha(SCORE), "candidate_ledger": sha(LEDGER),
                               "opening_manifest": sha(OPENING), "staged_transform": sha(STAGED),
                               "refined_transform": sha(REFINED), "one_frame_calibration": sha(CALIBRATION)},
              "summary": summary,
              "limitations": ["Metrics are null unless all six players have accepted grounded proxies.",
                              "The refined transform passed six marks on one out-of-point frame, not the frozen twelve-mark rule.",
                              "Existing candidate court points were rounded to 0.001 m before inverse mapping to source pixels; this adds small numerical rounding error.",
                              "The live interval's last frame comes from a reviewer statement, not an individually certified point-ending event.",
                              "One candidate-assisted reviewer supplied player and ground-state judgments; box bottoms are approximate floor proxies.",
                              "This one-rally time series cannot establish a winner effect or tactical quality."],
              "frames": frames}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(10, 6.4), sharex=True, constrained_layout=True)
    labels = (("spacing_m", "Pairwise spacing (m)"), ("hull_area_m2", "Convex-hull area (m²)"),
              ("dispersion_m", "Centroid dispersion (m)"))
    x = np.array([r["source_frame"] for r in frames])
    for ax, (key, label) in zip(axes, labels):
        y = np.array([r["refined_metrics"][key] if r["eligible_six_grounded"] else np.nan for r in frames])
        ax.plot(x, y, color="#12698a", lw=1.8, marker=".", ms=3)
        ax.set_ylabel(label)
        ax.grid(alpha=.22)
    axes[-1].set_xlabel("Source frame (30 fps)")
    fig.suptitle("S3 P34: six-grounded-frame geometry, with missing frames left blank")
    fig.savefig(FIGURE, dpi=170)
    plt.close(fig)
    text = "# S3 P34 exploratory rally-long team geometry\n\n"
    text += ("The [joined 140-frame state review](HONOURS_U5_S3P34_REPORTED_LIVE_INTERVAL_RESULT.md) has "
             "**92 frames with six accepted grounded box-bottom proxies**. The other 48 frames have null team metrics. "
             "The three team measures were calculated on those 92 frames using the post-review refined court transform. "
             "Its [one-frame out-of-point diagnostic](HONOURS_U5_S3P34_ONE_FRAME_CALIBRATION_DIAGNOSTIC.md) "
             "has six small court-line residuals but does not pass the frozen two-frame rule. "
             "This is therefore an exploratory same-camera geometry series, not a formally approved strict metric input.\n\n")
    text += "| Measure | Median | Observed range | Median absolute change from staged transform |\n| --- | ---: | ---: | ---: |\n"
    for key, label, unit in (("spacing_m", "Pairwise spacing", "m"),
                             ("hull_area_m2", "Convex-hull area", "m²"),
                             ("dispersion_m", "Centroid dispersion", "m")):
        s = summary[key]
        text += (f"| {label} | {s['median']:.3f} {unit} | {s['minimum']:.3f}–{s['maximum']:.3f} {unit} "
                 f"| {s['median_absolute_refined_minus_staged']:.3f} {unit} |\n")
    text += ("\n![S3 P34 team geometry over eligible frames](figures/u5_s3p34_reported_live_geometry.png)\n\n"
             "Gaps in the plot are frames with an airborne, missing or uncertain floor position. "
             "Values are geometric descriptions of six proxies, not reachable defensive area, rotation, "
             "measured foot travel or evidence that the rally outcome was caused by a formation. "
             "The last-live boundary rests on a broad single-reviewer statement; all player checks were candidate assisted. "
             "[Machine-readable per-frame metrics and source hashes](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reported_live_geometry.json).\n")
    REPORT.write_text(text, encoding="utf-8")
    print({k: {"median": round(v["median"], 3), "range": [round(v["minimum"], 3), round(v["maximum"], 3)]}
           for k, v in summary.items()})


if __name__ == "__main__":
    main()
