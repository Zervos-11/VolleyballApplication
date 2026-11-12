"""Score frozen out-of-point landmarks against the previously refined homography."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = SCREEN / "s3p34_calibration_holdout"
CANDIDATE = SCREEN / "s3p34_calibration_review/refined_candidate.json"
REGISTRATION = SCREEN / "selected_camera_registration.json"
OUT = PACK / "score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_OUT_OF_POINT_CALIBRATION.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    form = PACK / "completed.csv"
    if not form.exists():
        print("Out-of-point court marks are pending")
        return
    protocol = json.loads((PACK / "protocol.json").read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    with form.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(str(f["frame"]), x["code"]) for f in protocol["frames"] for x in protocol["landmarks"]}
    if len(rows) != 12 or {(r["source_frame"], r["landmark_code"]) for r in rows} != expected:
        raise ValueError("Holdout must contain twelve unique frozen landmark rows")
    if candidate["source_frame_used_for_fit"] in {f["frame"] for f in protocol["frames"]}:
        raise ValueError("Fitted frame cannot be its own holdout")
    if protocol["source_video_sha256"] != registration["source_sha256"]:
        raise ValueError("Source video hashes disagree")
    matrix = np.asarray(candidate["homography_image_to_court"], dtype=np.float64)
    marks = []
    for row in rows:
        item = next(f for f in protocol["frames"] if str(f["frame"]) == row["source_frame"])
        if row["image_sha256"] != item["sha256"] or sha(PACK / item["image"]) != item["sha256"]:
            raise ValueError("Source image hash mismatch")
        result = {"source_frame": int(row["source_frame"]), "landmark_code": row["landmark_code"],
                  "status": row["status"], "error_m": None}
        if row["status"] == "marked":
            x, y = float(row["x_px"]), float(row["y_px"])
            mapped = cv2.perspectiveTransform(np.array([[[x, y]]], dtype=np.float64), matrix)[0, 0]
            target = np.array([float(row["court_x_m"]), float(row["court_y_m"])])
            result.update({"clicked_source_px": [x, y], "mapped_court_m": mapped.tolist(),
                           "target_court_m": target.tolist(), "error_m": float(np.linalg.norm(mapped-target))})
        marks.append(result)
    errors = [m["error_m"] for m in marks if m["error_m"] is not None]
    rule = protocol["decision_rule_frozen_before_new_marks"]
    shift = registration["summary"]["maximum_static_landmark_shift_px"]
    passed = (len(errors) == rule["required_visible_landmarks"] and
              max(errors) <= rule["maximum_projected_landmark_error_m"] and
              shift <= rule["maximum_static_camera_registration_shift_px"])
    result = {
        "status": "single_reviewer_out_of_point_operational_screen",
        "pass_operational_camera_calibration": passed,
        "formal_independent_validation": False,
        "marked_landmarks": len(errors), "required_landmarks": rule["required_visible_landmarks"],
        "maximum_error_m": max(errors) if errors else None,
        "median_error_m": float(np.median(errors)) if errors else None,
        "maximum_static_camera_shift_px": shift,
        "inputs_sha256": {"protocol": sha(PACK / "protocol.json"), "completed_marks": sha(form),
                          "refined_candidate": sha(CANDIDATE), "camera_registration": sha(REGISTRATION)},
        "marks": marks,
        "limitations": ["One previously exposed reviewer marked two other points from the same fixed camera.",
                        "A passed court-line check cannot validate box bottoms as player ground contacts.",
                        "The refined homography was fitted after the original calibration screen failed; this holdout was frozen before its new marks."],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    median_text = f"{result['median_error_m']:.4f} m" if errors else "unavailable"
    max_text = f"{result['maximum_error_m']:.4f} m" if errors else "unavailable"
    REPORT.write_text(
        "# S3 P34 out-of-point court calibration holdout\n\n"
        f"The source-only holdout marked **{len(errors)}/12** court intersections at frames 1422 and 29952, "
        "outside the point used to fit the refined transform. "
        f"Median error was **{median_text}** and maximum error "
        f"**{max_text}**. The frozen operational screen "
        f"**{'passed' if passed else 'did not pass'}**. "
        f"[Machine-readable marks and score](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_holdout/score.json).\n\n"
        "This is a same-camera, single-reviewer court-line check. It does not independently validate "
        "player floor anchors, exact event timing or use on other cameras. The earlier original-transform "
        "screen failure remains in the record.\n",
        encoding="utf-8",
    )
    print(f"Out-of-point operational screen: {'pass' if passed else 'fail'}; maximum {max_text}")


if __name__ == "__main__":
    main()
