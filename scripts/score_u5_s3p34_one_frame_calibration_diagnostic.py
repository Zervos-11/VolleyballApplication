"""Score the saved first calibration holdout without changing the frozen two-frame rule."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = SCREEN / "s3p34_calibration_holdout"
DRAFT = PACK / "draft.json"
PROTOCOL = PACK / "protocol.json"
CANDIDATE = SCREEN / "s3p34_calibration_review/refined_candidate.json"
REGISTRATION = SCREEN / "selected_camera_registration.json"
OUT = PACK / "one_frame_diagnostic.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_ONE_FRAME_CALIBRATION_DIAGNOSTIC.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    assert set(draft["frames"]) == {"1422"}
    assert candidate["source_frame_used_for_fit"] != 1422
    assert protocol["source_video_sha256"] == registration["source_sha256"]
    frame = next(f for f in protocol["frames"] if f["frame"] == 1422)
    assert sha(PACK / frame["image"]) == frame["sha256"]
    targets = {x["code"]: x["court_m"] for x in protocol["landmarks"]}
    rows = draft["frames"]["1422"]["rows"]
    assert len(rows) == 6 and {x["code"] for x in rows} == set(targets)
    matrix = np.asarray(candidate["homography_image_to_court"], dtype=float)
    marks = []
    for row in rows:
        result = {"landmark_code": row["code"], "status": row["status"], "error_m": None}
        if row["status"] == "marked":
            x, y = float(row["x_px"]), float(row["y_px"])
            mapped = cv2.perspectiveTransform(np.array([[[x, y]]], dtype=float), matrix)[0, 0]
            target = np.asarray(targets[row["code"]], dtype=float)
            result.update({"clicked_px": [x, y], "mapped_court_m": mapped.tolist(),
                           "target_court_m": target.tolist(), "error_m": float(np.linalg.norm(mapped-target))})
        marks.append(result)
    errors = [r["error_m"] for r in marks if r["error_m"] is not None]
    rule = protocol["decision_rule_frozen_before_new_marks"]
    shift = registration["summary"]["maximum_static_landmark_shift_px"]
    result = {"status": "partial_one_frame_same_camera_diagnostic",
              "frame": 1422, "marked_landmarks": len(errors),
              "frozen_rule_required_landmarks": rule["required_visible_landmarks"],
              "frozen_two_frame_operational_pass": False,
              "single_frame_within_error_threshold": len(errors) == 6 and max(errors) <= rule["maximum_projected_landmark_error_m"],
              "maximum_error_m": max(errors) if errors else None,
              "median_error_m": float(np.median(errors)) if errors else None,
              "maximum_static_camera_shift_px": shift,
              "inputs_sha256": {"draft": sha(DRAFT), "protocol": sha(PROTOCOL),
                                "refined_candidate": sha(CANDIDATE), "camera_registration": sha(REGISTRATION)},
              "marks": marks,
              "limitations": ["Only the first of two frozen holdout frames was marked; the twelve-mark protocol did not pass.",
                              "The camera registration study supports stability over checked points but does not validate the transform corners.",
                              "Court-line residuals do not measure error in box-bottom player floor positions.",
                              "Marks came from one reviewer previously exposed to this camera and calibration work."]}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# S3 P34 one-frame court calibration diagnostic\n\n"
        "The reviewer marked all six frozen court-line intersections on out-of-point frame **1422**. "
        f"Against the previously refined transform, median mapped error is **{result['median_error_m']:.4f} m** "
        f"and maximum mapped error is **{result['maximum_error_m']:.4f} m**. "
        f"The separate camera-registration check had at most **{shift:.3f} px** fitted static-landmark shift "
        "over its checked frames. [Individual marks and source hashes](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_holdout/one_frame_diagnostic.json).\n\n"
        "The student chose to stop after one holdout frame because the camera does not appear to move. "
        "The frozen operational rule required **12 marks on two frames**, so that rule **was not completed or passed**. "
        "These six small line residuals support a qualified same-camera descriptive mapping check; "
        "they do not establish independent physical calibration, accuracy of player box-bottom anchors, "
        "or transfer to another camera. The second holdout remains unmarked.\n",
        encoding="utf-8",
    )
    print(f"6/12 marked; median {result['median_error_m']:.4f} m; max {result['maximum_error_m']:.4f} m; frozen rule incomplete")


if __name__ == "__main__":
    main()
