"""Recompute the held-out court-line error and S3 P34 camera registration."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
COURT = BASE / "near_court_candidate.json"
REGISTRATION = BASE / "selected_camera_registration.json"
OUTPUT = BASE / "s3p34_calibration_readiness.json"


def read(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def main() -> None:
    court, court_hash = read(COURT)
    registration, registration_hash = read(REGISTRATION)
    assert court["use_for_final_metrics"] is False
    assert court["source_frame_within_excerpt"] == registration["reference_excerpt_frame"]
    assert registration["summary"]["reviewed_selected_frames"] == 24
    selected = [r for r in registration["rows"] if (r["set"], r["point_number"]) == (3, 34)]
    assert len(selected) == 1 and selected[0]["source_frame"] == 36072
    target_x = [0.0, 9.0]
    expected_y = float(court["held_out_expected_court_y_m"])
    distances = [
        math.hypot(float(point[0]) - x, float(point[1]) - expected_y)
        for point, x in zip(court["held_out_attack_line_projected_m"], target_x, strict=True)
    ]
    result = {
        "status": "staged_single_reviewer_calibration_not_approved_for_strict_metrics",
        "source_sha256": registration["source_sha256"],
        "input_sha256": {"court": court_hash, "registration": registration_hash},
        "held_out_intersection_errors_m": [round(x, 4) for x in distances],
        "maximum_held_out_intersection_error_m": round(max(distances), 4),
        "selected_frames_registered": registration["summary"]["frames_registered"],
        "maximum_static_landmark_shift_px": registration["summary"]["maximum_static_landmark_shift_px"],
        "s3p34_frame_36072_static_landmark_shift_px": selected[0]["maximum_static_landmark_shift_px"],
        "metric_use_approved": False,
        "limits": [
            "Only two held-out intersections on one attack line were marked.",
            "Court corners and held-out points were marked by one reviewer.",
            "Static image registration does not validate player floor anchors.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: held-out maximum {result['maximum_held_out_intersection_error_m']} m; strict approval false")


if __name__ == "__main__":
    main()
