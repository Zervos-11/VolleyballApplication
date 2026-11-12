"""Freeze a source-only court-landmark review without changing prior marks."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
SOURCE_PACK = SCREEN / "s3p34_30fps_ground_review"
OUT = SCREEN / "s3p34_calibration_review"
FRAMES = (36073, 36101)
LANDMARKS = (
    {"code": "baseline_left", "label": "Near baseline × left sideline", "court_m": [0, 0]},
    {"code": "baseline_right", "label": "Near baseline × right sideline", "court_m": [9, 0]},
    {"code": "attack_left", "label": "Attack line × left sideline", "court_m": [0, 6]},
    {"code": "attack_right", "label": "Attack line × right sideline", "court_m": [9, 6]},
    {"code": "net_left", "label": "Floor net line × left sideline", "court_m": [0, 9]},
    {"code": "net_right", "label": "Floor net line × right sideline", "court_m": [9, 9]},
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((SOURCE_PACK / "manifest.json").read_text(encoding="utf-8"))
    existing = {row["frame"]: row for row in manifest["frames"]}
    frames = []
    for number in FRAMES:
        image = existing[number]
        path = SOURCE_PACK / image["image"]
        assert sha(path) == image["sha256"]
        frames.append({"frame": number, "image": image["image"], "sha256": image["sha256"]})
    protocol = {
        "status": "frozen_unmarked_single_reviewer_calibration_check",
        "source_video_sha256": manifest["source_video_sha256"],
        "purpose": "check_staged_image_to_court_transform_at_two_s3p34_times",
        "reviewer_context": "same human reviewer as player-position review; previously exposed to staged calibration",
        "frames": frames,
        "landmarks": LANDMARKS,
        "marking_rule": "Click centre of the painted court-line intersection on the unboxed native-resolution source image; use uncertain/occluded and null coordinates if it cannot be located.",
        "decision_rule_frozen_before_new_marks": {
            "maximum_projected_landmark_error_m": 0.2,
            "maximum_static_camera_registration_shift_px": 2.0,
            "required_visible_landmarks": 12,
            "scope": "operational_screen_for_this_camera_and_near_court_only",
            "basis": "Existing HONOURS_CALIBRATION_QC.md operational screen; passing does not validate player floor anchors or remove fixed-window selection bias.",
        },
    }
    OUT.mkdir(exist_ok=True)
    target = OUT / "protocol.json"
    rendered = json.dumps(protocol, indent=2) + "\n"
    if target.exists():
        assert target.read_text(encoding="utf-8") == rendered, "Frozen protocol changed"
    else:
        target.write_text(rendered, encoding="utf-8")
    print(f"Frozen {len(frames)} source frames and {len(frames) * len(LANDMARKS)} landmark slots")


if __name__ == "__main__":
    main()
