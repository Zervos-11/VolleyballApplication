"""Screen source-selected elevated rallies for raw person candidates at 5 Hz.

The selection JSON is frozen before detector review. This script deliberately does
not assign teams, validate identities, estimate floor points or score outcomes.
"""

from __future__ import annotations

import hashlib
import json
import os
import argparse
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402


SELECTION = ROOT / "data/processed/source_view_screen/transfer_source_only_selection_2026-11-06_v2.json"
MODEL = ROOT / "yolov8n.pt"
METHOD = {
    "detector": "YOLOv8n person",
    "confidence": 0.2,
    "image_size": 960,
    "sampling_seconds": 0.2,
    "tracker": "ByteTrack, fresh model for each excerpt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", help="Screen one addendum case without rewriting earlier outputs")
    args = parser.parse_args()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    if selection["status"] != "source_only_selected_before_detector_review":
        raise ValueError("Selection has not been frozen")
    for case in selection["cases"]:
        if args.match_id and case["match_id"] != args.match_id:
            continue
        source = ROOT / case["local_excerpt"]
        if sha256(source) != case["local_excerpt_sha256"]:
            raise ValueError(f"Source hash mismatch: {source}")
        fps = case["excerpt_fps"]
        step = round(fps * METHOD["sampling_seconds"])
        if abs(step / fps - METHOD["sampling_seconds"]) > 0.002:
            raise ValueError(f"Grid does not divide source fps: {fps}")
        first, last = case["screen_interval_clip_frames_inclusive"]
        frames = list(range(first, last + 1, step))
        model = YOLO(str(MODEL))
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise FileNotFoundError(source)
        rows = []
        try:
            for number in frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {source} frame {number}")
                result = model.track(image, classes=[0], conf=METHOD["confidence"],
                                     imgsz=METHOD["image_size"], tracker="bytetrack.yaml",
                                     persist=True, verbose=False)[0]
                ids = (result.boxes.id.int().cpu().tolist()
                       if result.boxes.id is not None else [None] * len(result.boxes))
                proposals = [
                    {"raw_track_id": track_id,
                     "bbox_px": [round(float(v), 1) for v in bbox],
                     "confidence": round(float(score), 4)}
                    for track_id, bbox, score in zip(
                        ids, result.boxes.xyxy.cpu().tolist(),
                        result.boxes.conf.cpu().tolist())
                ]
                rows.append({"excerpt_frame": number,
                             "excerpt_time_s": round(number / fps, 3),
                             "all_person_candidate_count": len(proposals),
                             "proposals": proposals})
        finally:
            cap.release()
        out = SELECTION.parent / f"{case['match_id']}_raw_5hz_candidates.json"
        data = {
            "status": "raw_person_candidates_pending_source_review",
            "match_id": case["match_id"],
            "source_url": case["source_url"],
            "excerpt_sha256": case["local_excerpt_sha256"],
            "selection_sha256": sha256(SELECTION),
            "model_sha256": sha256(MODEL),
            "method": METHOD,
            "excerpt_fps": fps,
            "frame_step": step,
            "screen_interval_excerpt_frames_inclusive": [first, last],
            "rows": rows,
            "limitations": [
                "Person proposals include both teams and non-players.",
                "Raw track IDs are not source-reviewed player identities.",
                "The excerpt has not been aligned to exact full-video frame numbers.",
                "No floor-contact verdict or court transform is included.",
            ],
        }
        out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"{case['match_id']}: {len(rows)} grid frames, "
              f"{sum(len(row['proposals']) for row in rows)} all-person proposals")


if __name__ == "__main__":
    main()
