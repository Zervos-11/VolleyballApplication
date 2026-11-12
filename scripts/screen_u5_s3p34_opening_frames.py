"""Propose person boxes for the three S3 P34 frames before the reviewed tracker run.

This is a detector screen only. Nearest-box slot suggestions are not identity
verdicts or accepted floor coordinates.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402


SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
SOURCE = ROOT / "data/matches/yt_u5HnY2aNW14/source_720p.mp4"
MANIFEST = SCREEN / "s3p34_remaining_rally_review/manifest.json"
MODEL = ROOT / "yolov8n.pt"
OUTPUT = SCREEN / "s3p34_opening_frame_screen.json"
FRAMES = (35998, 35999, 36000)
SLOTS = ("28", "12", "15", "7", "19", "21")
SOURCE_HASH = "da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def centre(box: list[float]) -> np.ndarray:
    x1, y1, x2, y2 = box
    return np.array(((x1 + x2) / 2, (y1 + y2) / 2))


def main() -> None:
    assert sha(SOURCE) == SOURCE_HASH
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    first = next(x for x in manifest["frames"] if x["source_frame"] == 36001)
    references = np.array([centre(first["numbered_boxes"][slot]["bbox_px"]) for slot in SLOTS])
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(SOURCE))
    assert cap.isOpened()
    rows = []
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame + 1
            result = model.predict(image, classes=[0], conf=0.15, imgsz=1280, verbose=False)[0]
            boxes = result.boxes.xyxy.cpu().numpy().tolist()
            scores = result.boxes.conf.cpu().numpy().tolist()
            proposals = [{"bbox_px": [round(float(v), 1) for v in box],
                          "confidence": round(float(score), 3),
                          "suggested_slot": None,
                          "match_distance_px": None}
                         for box, score in zip(boxes, scores)]
            if proposals:
                detected = np.array([centre(p["bbox_px"]) for p in proposals])
                distance = np.linalg.norm(references[:, None, :] - detected[None, :, :], axis=2)
                slot_rows, box_cols = linear_sum_assignment(distance)
                for i, j in zip(slot_rows, box_cols):
                    if distance[i, j] <= 130:
                        proposals[j]["suggested_slot"] = SLOTS[i]
                        proposals[j]["match_distance_px"] = round(float(distance[i, j]), 1)
            rows.append({"source_frame": frame, "proposals": proposals})
    finally:
        cap.release()
    output = {"status": "detector_proposals_unreviewed",
              "source_sha256": SOURCE_HASH,
              "model_sha256": sha(MODEL),
              "reference_manifest_sha256": sha(MANIFEST),
              "method": "YOLOv8n person conf 0.15 imgsz 1280; Hungarian nearest-centre suggestion to frame 36001, max 130 px; no tracker or source identity review",
              "slots": list(SLOTS), "rows": rows}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print([(r["source_frame"], sum(p["suggested_slot"] is not None for p in r["proposals"]), len(r["proposals"])) for r in rows])


if __name__ == "__main__":
    main()
