"""Add provisional high-resolution person boxes without changing reviewed raw IDs.

The second pass is only a selection aid. It neither assigns BYU identities nor
turns a box bottom into an accepted floor coordinate.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402

BASE = ROOT / "data/processed/source_view_screen"
MATCH = "yt_b1bJ5WN05Qw"
VIDEO = BASE / "usc_byu_selection.mp4"
RAW = BASE / f"{MATCH}_raw_5hz_candidates.json"
MODEL = ROOT / "yolov8n.pt"
OUTPUT = BASE / "elevated_transfer_review" / f"{MATCH}_hires_supplement.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def iou(a: list[float], b: list[float]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    return overlap / (area_a + area_b - overlap) if area_a + area_b > overlap else 0.0


def red_torso_fraction(image: np.ndarray, box: list[float]) -> float:
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    crop = image[int(y1 + .25 * height):int(y1 + .70 * height),
                 int(x1 + .20 * width):int(x1 + .80 * width)]
    if crop.size == 0:
        return 1.0
    blue, green, red = (channel.astype(np.float32) for channel in cv2.split(crop))
    mask = (red > 90) & (red > 1.3 * green) & (red > 1.25 * blue)
    return float(mask.mean())


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    model = YOLO(str(MODEL))
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise FileNotFoundError(VIDEO)
    rows = []
    try:
        for row in raw["rows"]:
            frame = row["excerpt_frame"]
            if 714 < frame < 780:
                continue
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"Unable to decode frame {frame}")
            result = model.predict(image, classes=[0], conf=.1,
                                   imgsz=1600, verbose=False)[0]
            existing = [p["bbox_px"] for p in row["proposals"]]
            extras = []
            for ordinal, (coords, confidence) in enumerate(zip(
                    result.boxes.xyxy.cpu().tolist(),
                    result.boxes.conf.cpu().tolist())):
                box = [round(float(value), 1) for value in coords]
                x1, _, x2, y2 = box
                if (confidence < .2 or x1 < 250 or x2 > 1500 or y2 < 520
                        or red_torso_fraction(image, box) > .30):
                    continue
                if any(iou(box, other) >= .50 for other in existing):
                    continue
                if any(iou(box, other["bbox_px"]) >= .50 for other in extras):
                    continue
                extras.append({
                    "raw_track_id": 200000 + frame * 100 + ordinal,
                    "bbox_px": box,
                    "confidence": round(float(confidence), 4),
                    "proposal_source": "high_resolution_single_frame",
                })
            rows.append({"excerpt_frame": frame, "proposals": extras})
    finally:
        capture.release()
    output = {
        "status": "provisional_detector_supplement_pending_source_review",
        "match_id": MATCH,
        "excerpt_sha256": digest(VIDEO),
        "original_raw_candidate_sha256": digest(RAW),
        "model_sha256": digest(MODEL),
        "method": {"detector": "YOLOv8n person, independent single-frame pass",
                   "image_size": 1600, "confidence": .1,
                   "retained_confidence": .2,
                   "existing_box_iou_exclusion": .5,
                   "red_torso_screen": .30},
        "limitations": [
            "Colour and geometric screens are heuristic and can reject BYU or retain USC.",
            "Extra IDs label one-frame proposals only; they do not imply identity continuity.",
            "The earlier source review and saved candidate IDs are unchanged.",
        ],
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} frames, {sum(len(row['proposals']) for row in rows)} extra provisional boxes")


if __name__ == "__main__":
    main()
