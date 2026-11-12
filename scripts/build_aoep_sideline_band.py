"""Retain a source-reviewed AoEP sideline player outside the strict court square."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
SOURCE_PATH = DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.json"
OUTPUT = DIR / "player5_sideline_band.json"
PREVIEW = DIR / "player5_sideline_band.jpg"
SHEETS = ["player5_source_qc_75180_75204.jpg", "player5_source_qc_75205_75229.jpg"]
BAND_M = 0.5
STEP_REVIEW_M = 0.3


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    for sheet in SHEETS:
        if not (DIR / sheet).is_file():
            raise FileNotFoundError(sheet)
    path = source["players"]["yellow_left_5"]
    frames = sorted(map(int, path))
    if frames != list(range(75180, 75230)):
        raise ValueError("unexpected sideline frame range")
    points = np.asarray([path[str(frame)]["court_position_m_diagnostic"] for frame in frames])
    if points.shape != (50, 2) or not np.isfinite(points).all():
        raise ValueError("expected 50 finite projected points")
    inside = np.all((points >= 0) & (points <= 9), axis=1)
    band = np.all((points >= -BAND_M) & (points <= 9 + BAND_M), axis=1)
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    breaks = [{"frame_index": frames[index + 1], "step_m": round(float(step), 2)}
              for index, step in enumerate(steps) if step > STEP_REVIEW_M]
    if not band.all():
        raise ValueError("a player position leaves the declared boundary band")
    result = {
        "status": "single_reviewer_sideline_band_trace_development_only",
        "source_sha256": source["source_sha256"],
        "candidate_path_sha256": sha256(SOURCE_PATH),
        "saved_annotations_sha256": source["saved_annotations_sha256"],
        "calibration_sha256": source["calibration_sha256"],
        "source_review_sheets": SHEETS,
        "frame_range_inclusive": [frames[0], frames[-1]],
        "visual_identity_review": "The same yellow #5 is visible in the frozen raw ID 8 box on all 50 source frames. This is single-reviewer development evidence, not independent ground truth.",
        "strict_court_points": int(inside.sum()),
        "boundary_band_points": int(band.sum()),
        "boundary_band_m": BAND_M,
        "projected_extent_m": {
            "xmin": round(float(points[:, 0].min()), 2),
            "xmax": round(float(points[:, 0].max()), 2),
            "ymin": round(float(points[:, 1].min()), 2),
            "ymax": round(float(points[:, 1].max()), 2),
        },
        "step_review_threshold_m_per_frame": STEP_REVIEW_M,
        "motion_breaks": breaks,
        "positions": [{"frame_index": frame, "court_position_m_diagnostic":
                       [round(float(value), 2) for value in point],
                       "inside_nominal_court": bool(inside[index])}
                      for index, (frame, point) in enumerate(zip(frames, points))],
        "speed_distance_coverage_published": False,
        "limitation": "Near-team visual identity continues across the sideline, but box-bottom and court-line errors prevent precise movement metrics. Outside the nominal 9m square is a location flag, not a far-team label or a reason to discard the player.",
        "preview": PREVIEW.name,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    image = np.full((850, 850, 3), 245, np.uint8)
    scale = 70
    def xy(point):
        return round(115 + point[0] * scale), round(735 - point[1] * scale)
    cv2.rectangle(image, xy((0, 9)), xy((9, 0)), (50, 50, 50), 2)
    cv2.rectangle(image, xy((-.5, 9.5)), xy((9.5, -.5)), (170, 170, 170), 1)
    cv2.line(image, xy((0, 6)), xy((9, 6)), (150, 150, 150), 1)
    for index in range(1, len(points)):
        if steps[index - 1] <= STEP_REVIEW_M:
            cv2.line(image, xy(points[index - 1]), xy(points[index]), (0, 140, 220), 3, cv2.LINE_AA)
    for index in (0, 10, 20, 30, 40, 49):
        cv2.circle(image, xy(points[index]), 5, (0, 90, 230), -1)
    cv2.putText(image, "Yellow #5: 50-frame sideline band", (35, 42),
                cv2.FONT_HERSHEY_SIMPLEX, .8, (30, 30, 30), 2)
    cv2.putText(image, "black = nominal court; grey = 0.5m band", (35, 785),
                cv2.FONT_HERSHEY_SIMPLEX, .58, (40, 40, 40), 1)
    cv2.putText(image, "line breaks flag >0.30m steps; no movement metric", (35, 815),
                cv2.FONT_HERSHEY_SIMPLEX, .5, (40, 40, 40), 1)
    if not cv2.imwrite(str(PREVIEW), image):
        raise OSError(PREVIEW)
    print(json.dumps({"strict_court_points": result["strict_court_points"],
                      "boundary_band_points": result["boundary_band_points"],
                      "motion_breaks": len(breaks)}))


if __name__ == "__main__":
    main()
