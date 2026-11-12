"""Freeze two out-of-point court-line images for a new calibration holdout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/matches/yt_u5HnY2aNW14/source_720p.mp4"
OUT = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_holdout"
FRAMES = (1422, 29952)
SOURCE_HASH = "da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b"
LANDMARKS = [
    ("baseline_left", "Near baseline x left sideline", [0, 0]),
    ("baseline_right", "Near baseline x right sideline", [9, 0]),
    ("attack_left", "Attack line x left sideline", [0, 6]),
    ("attack_right", "Attack line x right sideline", [9, 6]),
    ("net_left", "Floor net line x left sideline", [0, 9]),
    ("net_right", "Floor net line x right sideline", [9, 9]),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sha(VIDEO) != SOURCE_HASH:
        raise ValueError("Source video hash changed")
    OUT.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(VIDEO))
    records = []
    for n in FRAMES:
        capture.set(cv2.CAP_PROP_POS_FRAMES, n)
        ok, frame = capture.read()
        if not ok or frame.shape[:2] != (720, 1280):
            raise ValueError(f"Could not decode source frame {n}")
        path = OUT / f"unboxed_{n}.png"
        if not path.exists():
            cv2.imwrite(str(path), frame)
        records.append({"frame": n, "image": path.name, "sha256": sha(path)})
    capture.release()
    protocol = {
        "status": "frozen_before_new_holdout_marks",
        "source_video_sha256": SOURCE_HASH,
        "reviewer_context": "single reviewer previously exposed to original calibration; these two source frames were not used to fit the refined candidate",
        "purpose": "out_of_point_holdout_check_of_post_review_refined_homography",
        "frames": records,
        "landmarks": [{"code": code, "label": label, "court_m": xy}
                      for code, label, xy in LANDMARKS],
        "marking_rule": "Click the painted court-line intersection in each unboxed native-resolution source frame; uncertain or occluded marks remain null.",
        "decision_rule_frozen_before_new_marks": {
            "required_visible_landmarks": 12,
            "maximum_projected_landmark_error_m": 0.2,
            "maximum_static_camera_registration_shift_px": 2.0,
            "scope": "operational_use_of_refined_mapping_for_this_camera_and_near_court_only",
            "qualification": "Passing does not prove true player foot positions, independent inter-observer accuracy or match-to-match transferability."
        },
    }
    target = OUT / "protocol.json"
    if target.exists() and json.loads(target.read_text(encoding="utf-8")) != protocol:
        raise ValueError("Frozen holdout protocol already differs")
    if not target.exists():
        target.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen {len(records)} out-of-point frames and {len(LANDMARKS)} landmarks")


if __name__ == "__main__":
    main()
