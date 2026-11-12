"""Run the frozen YOLOv8n/ByteTrack setup over a source-bracketed D79 point."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
MODEL = ROOT / "yolov8n.pt"
BOUNDARY = ROOT / "data/processed/d79_new_source/point_boundary_candidate.json"
OUTPUT = ROOT / "data/processed/d79_new_source/raw_point_candidate_80_336.json"
WARMUP_FIRST = 55


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"candidate already frozen: {OUTPUT}")
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    if sha256(VIDEO) != boundary["source_sha256"]:
        raise ValueError("source video changed")
    start = boundary["candidate_start_frame_inclusive"]
    stop = boundary["candidate_end_frame_exclusive"]
    if (start, stop) != (80, 337):
        raise ValueError("unexpected candidate interval")
    model = YOLO(str(MODEL))
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.set(cv2.CAP_PROP_POS_FRAMES, WARMUP_FIRST):
        raise RuntimeError("could not seek to warmup start")
    predictions = {}
    try:
        for frame in range(WARMUP_FIRST, stop):
            good, image = capture.read()
            if not good:
                raise RuntimeError(f"missing source frame {frame}")
            result = model.track(image, tracker="bytetrack.yaml", persist=True,
                                 conf=0.20, imgsz=960, verbose=False)[0]
            if frame < start:
                continue
            rows = []
            boxes = result.boxes
            if boxes is not None and len(boxes):
                coords = boxes.xyxy.cpu().numpy()
                classes = boxes.cls.cpu().numpy()
                scores = boxes.conf.cpu().numpy()
                ids = boxes.id.cpu().numpy() if boxes.id is not None else np.full(len(boxes), -1)
                for box, kind, score, track_id in zip(coords, classes, scores, ids):
                    if int(kind) == 0:
                        rows.append({"bbox": [round(float(v), 3) for v in box],
                                     "confidence": round(float(score), 5),
                                     "track_id": int(track_id)})
            predictions[str(frame)] = rows
    finally:
        capture.release()
    if len(predictions) != stop - start:
        raise RuntimeError("incomplete candidate predictions")
    payload = {
        "status": "frozen_development_candidate_no_ground_truth_claim",
        "source_sha256": sha256(VIDEO), "model_sha256": sha256(MODEL),
        "boundary_candidate_sha256": sha256(BOUNDARY),
        "first_frame": start, "last_frame": stop - 1,
        "warmup_first_frame": WARMUP_FIRST,
        "tracker": "YOLOv8n + ByteTrack; conf=0.20; imgsz=960",
        "predictions": predictions,
    }
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Frozen {len(predictions)} frames, {sum(map(len, predictions.values()))} person boxes")


if __name__ == "__main__":
    main()
