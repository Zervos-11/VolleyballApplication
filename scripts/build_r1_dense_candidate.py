"""Freeze raw person tracks for the provisional full-point r1 case study.

These are detector boxes and ByteTrack IDs, not reviewed player identities or
floor positions. The official pilot boundary and annotations are untouched.
"""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "data/processed/fqe_r1_boundary_recheck/R1_CASE_STUDY_CANDIDATE.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
MODEL = ROOT / "yolov8n.pt"
OUTPUT = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_dense_raw_tracks.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    start = candidate["candidate_interval"]["start_frame"]
    end = candidate["candidate_interval"]["end_frame_exclusive"]
    model_hash = sha256(MODEL)
    model = YOLO(str(MODEL))
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, start):
        raise RuntimeError("Could not open r1 source at candidate start")
    frames = {}
    try:
        for frame_index in range(start, end):
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Source ended before frame {frame_index}")
            result = model.track(frame, tracker="bytetrack.yaml", persist=True,
                                 conf=0.20, imgsz=960, verbose=False)[0]
            boxes = result.boxes
            rows = []
            if boxes is not None and len(boxes):
                xyxy = boxes.xyxy.cpu().numpy()
                kinds = boxes.cls.cpu().numpy()
                scores = boxes.conf.cpu().numpy()
                ids = (boxes.id.cpu().numpy() if boxes.id is not None
                       else np.full(len(boxes), -1))
                for box, kind, score, track_id in zip(xyxy, kinds, scores, ids):
                    if int(kind) == 0:
                        rows.append({"bbox": [round(float(v), 3) for v in box],
                                     "confidence": round(float(score), 5),
                                     "track_id": int(track_id)})
            frames[str(frame_index)] = rows
            if (frame_index - start + 1) % 100 == 0:
                print(f"processed {frame_index - start + 1}/{end - start}", flush=True)
    finally:
        capture.release()

    payload = {
        "status": "raw_detector_tracks_unreviewed",
        "match_id": candidate["source_match_id"],
        "source_sha256_from_record": candidate["video_sha256_from_source_record"],
        "candidate_record_sha256": sha256(CANDIDATE),
        "model_file": MODEL.name,
        "model_sha256": model_hash,
        "settings": {"tracker": "bytetrack.yaml", "confidence": 0.20, "imgsz": 960},
        "start_frame": start,
        "end_frame_exclusive": end,
        "frames_processed": end - start,
        "frames": frames,
    }
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)
    print(f"saved {len(frames)} frames to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
