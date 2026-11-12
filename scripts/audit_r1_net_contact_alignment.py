"""Compare saved near-net clicks with the held-out source-image net line."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
CALIBRATION_DIR = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration"
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
REVIEW = BASE / "r1_floor_contact_review.json"
FRAME = 21064


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads((CALIBRATION_DIR / "calibration_manifest.json").read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if manifest["match_id"] != review["match_id"] or review["rally_id"] != "r1":
        raise ValueError("Calibration and saved contacts refer to different sources")
    x1, y1, x2, y2 = manifest["camera_segments"]["camera_r1"]["heldout_net_line_px"]
    if x1 == x2:
        raise ValueError("Held-out net line must cross the image horizontally")
    records = review["records"][str(FRAME)]
    capture = cv2.VideoCapture(str(SOURCE))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, FRAME)
        okay, image = capture.read()
        if not okay:
            raise RuntimeError(f"Cannot decode source frame {FRAME}")
    finally:
        capture.release()

    overlay = image.copy()
    cv2.line(overlay, (round(x1), round(y1)), (round(x2), round(y2)),
             (0, 0, 255), 2, cv2.LINE_AA)
    observations = []
    for player in ("11", "12"):
        record = records[player]
        if record["state"] != "grounded_contact_visible" or record["footpoint_px"] is None:
            raise ValueError(f"No saved grounded point for #{player} at {FRAME}")
        x, y = record["footpoint_px"]
        line_y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
        difference = y - line_y
        observations.append({
            "player_id": player,
            "saved_point_px": [x, y],
            "heldout_net_line_y_at_point_x_px": round(line_y, 3),
            "point_minus_line_y_px": round(difference, 3),
            "direction_in_image": "above_line" if difference < 0 else "below_line",
            "interpretation": "Pixel separation from the recorded net-floor line; no in/out decision.",
        })
        center = (round(x), round(y))
        cv2.circle(overlay, center, 12, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.circle(overlay, center, 10, (0, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(overlay, f"#{player}: {difference:+.1f}px", (center[0] + 15, center[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(overlay, f"#{player}: {difference:+.1f}px", (center[0] + 15, center[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2, cv2.LINE_AA)

    crop = overlay[650:855, 950:1430]
    if crop.shape[:2] != (205, 480):
        raise ValueError("Unexpected source image dimensions")
    cv2.imwrite(str(BASE / "r1_net_contact_line_check.jpg"), cv2.resize(
        crop, (1440, 615), interpolation=cv2.INTER_LINEAR))
    result = {
        "status": "heldout_line_pixel_alignment_diagnostic_not_in_out_label",
        "match_id": review["match_id"], "rally_id": "r1", "frame_index": FRAME,
        "review_sha256": sha256(REVIEW),
        "calibration_manifest_sha256": sha256(CALIBRATION_DIR / "calibration_manifest.json"),
        "heldout_net_line_px": [x1, y1, x2, y2],
        "observations": observations,
        "source_crop": "r1_net_contact_line_check.jpg",
        "limitation": "The recorded line was inspected on median calibration frames, not independently redrawn on frame 21064. Source-camera stability was checked only at sampled frames. Shoe-floor click accuracy and net-line uncertainty are not measured; pixel separation alone cannot certify court side.",
        "official_annotations_changed": False,
        "production_metric_changed": False,
    }
    (BASE / "r1_net_contact_line_check.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print([(row["player_id"], row["point_minus_line_y_px"]) for row in observations])


if __name__ == "__main__":
    main()
