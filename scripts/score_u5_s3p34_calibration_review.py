"""Score the frozen source-only court-line review against the staged transform."""

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
SOURCE_PACK = SCREEN / "s3p34_30fps_ground_review"
PACK = SCREEN / "s3p34_calibration_review"
PROTOCOL = PACK / "protocol.json"
FORM = PACK / "completed.csv"
COURT = SCREEN / "near_court_candidate.json"
REGISTRATION = SCREEN / "selected_camera_registration.json"
OUT = PACK / "score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_CALIBRATION_REVIEW.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    court = json.loads(COURT.read_text(encoding="utf-8"))
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    rule = protocol["decision_rule_frozen_before_new_marks"]
    result = {"status": "awaiting_completed_landmark_form",
              "protocol_sha256": sha(PROTOCOL), "strict_metric_approval": False}
    if FORM.exists():
        with FORM.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 12
        assert court["use_for_final_metrics"] is False
        assert protocol["source_video_sha256"] == registration["source_sha256"]
        matrix = np.asarray(court["homography_image_to_court"], np.float64)
        frame_map = {str(item["frame"]): item for item in protocol["frames"]}
        landmark_map = {item["code"]: item for item in protocol["landmarks"]}
        scored = []
        for index, row in enumerate(rows):
            frame = protocol["frames"][index // 6]
            landmark = protocol["landmarks"][index % 6]
            assert row["source_frame"] == str(frame["frame"])
            assert row["image"] == frame["image"]
            assert row["image_sha256"] == frame["sha256"]
            assert sha(SOURCE_PACK / frame["image"]) == frame["sha256"]
            assert row["landmark_code"] == landmark["code"]
            assert [float(row["court_x_m"]), float(row["court_y_m"])] == landmark["court_m"]
            assert row["status"] in ("marked", "uncertain", "occluded")
            item = {"source_frame": int(row["source_frame"]), "landmark_code": row["landmark_code"],
                    "status": row["status"], "target_court_m": landmark["court_m"]}
            if row["status"] == "marked":
                x, y = float(row["x_px"]), float(row["y_px"])
                assert math.isfinite(x) and math.isfinite(y) and 0 <= x < 1280 and 0 <= y < 720
                projected = cv2.perspectiveTransform(
                    np.asarray([[[x, y]]], np.float32), matrix)[0, 0]
                error = math.dist(projected, landmark["court_m"])
                item.update({"source_px": [x, y],
                             "projected_court_m": [round(float(v), 4) for v in projected],
                             "projected_error_m": round(error, 4)})
            else:
                assert not row["x_px"] and not row["y_px"]
                item["projected_error_m"] = None
            scored.append(item)
        assert set(frame_map) == {str(x["source_frame"]) for x in scored}
        assert set(landmark_map) == {x["landmark_code"] for x in scored}
        errors = [x["projected_error_m"] for x in scored if x["projected_error_m"] is not None]
        registered_shift = registration["summary"]["maximum_static_landmark_shift_px"]
        passed = (len(errors) == rule["required_visible_landmarks"] and
                  max(errors) <= rule["maximum_projected_landmark_error_m"] and
                  registered_shift <= rule["maximum_static_camera_registration_shift_px"])
        result.update({
            "status": "single_reviewer_calibration_operational_screen_scored",
            "input_sha256": {"completed_form": sha(FORM), "court": sha(COURT),
                             "registration": sha(REGISTRATION)},
            "marked_landmarks": len(errors), "required_landmarks": 12,
            "median_projected_error_m": round(statistics.median(errors), 4) if errors else None,
            "maximum_projected_error_m": max(errors) if errors else None,
            "maximum_registered_static_shift_px": registered_shift,
            "operational_screen_passed": passed,
            "decision_rule": rule,
            "rows": scored,
            "interpretation": "This is a single-reviewer operational court-line check. A threshold miss of 0.0037 m at one clicked landmark cannot distinguish click placement uncertainty from error in the original manually selected transform corners. The frozen pass/fail result is retained. This check does not independently validate player floor anchors, certify an availability-selected fixed window, or validate a full-rally trajectory.",
        })
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if FORM.exists():
        REPORT.write_text("\n".join([
            "# S3 P34 source-only calibration review", "",
            "The [frozen protocol](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/protocol.json) "
            "required twelve court-line intersections on two unboxed S3 P34 frames. The same reviewer "
            "marked these after earlier exposure to the staged calibration. The "
            "[machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/score.json) "
            "contains each projected residual and hashes the completed form.", "",
            f"**Operational screen:** {'passed' if result['operational_screen_passed'] else 'did not pass'}. "
            f"{result['marked_landmarks']}/12 intersections were marked. "
            f"Median projected residual: {result['median_projected_error_m']} m; "
            f"maximum: {result['maximum_projected_error_m']} m. The frozen rule required "
            f"all twelve, a maximum residual no greater than {rule['maximum_projected_landmark_error_m']} m, "
            f"and at most {rule['maximum_static_camera_registration_shift_px']} px static registration shift "
            f"over the existing sampled camera check (observed {result['maximum_registered_static_shift_px']} px).", "",
            "The only threshold exceedance is the first frame's near-baseline/right-sideline mark, "
            "0.0037 m above the 0.200 m limit. The same landmark in the second frame is 0.1969 m "
            "from its target, and the two source-image clicks are 0.58 px apart. Given manual "
            "line-centre selection and manually chosen original transform corners, this marginal "
            "difference cannot be attributed specifically to the click, the camera or the "
            "original transform. The frozen operational screen still records a failure.", "",
            "The court-line check is scoped to this camera and near-court mapping. It does not establish "
            "independent player floor-position truth or fix the post hoc selection of the 37-frame "
            "diagnostic segment. Strict full-rally and fixed-window approval remains separate.", "",
            "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/score_u5_s3p34_calibration_review.py`.",
        ]) + "\n", encoding="utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
