"""Frozen, court-agnostic 5-Hz person screen on two additional match sources.

The selected source intervals precede this screen. Output is candidate boxes only;
team membership, phase, floor position and rally boundaries require source review.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402


CASES = (
    ("yt_AoEP-YiWRvc", "point_21m"),
    ("yt_FqE5pTJqx8g", "r3"),
)
MODEL = ROOT / "yolov8n.pt"
METHOD = {"detector": "YOLOv8n", "class": "person", "confidence": 0.2,
          "image_size": 960, "sampling_seconds": 0.2,
          "tracking": "ByteTrack, reset for each selected source interval"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    model = YOLO(str(MODEL))
    for match, rally_id in CASES:
        base = ROOT / "data/matches" / match
        record_path = base / "source_record.json"
        selection_path = base / "pilot/selection.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        rally = next(row for row in selection["rallies"] if row["rally_id"] == rally_id)
        source = ROOT / record["video_file"]
        assert source.is_file() and sha256(source) == record["sha256"]
        fps = float(record["camera"]["fps"])
        step = round(fps * METHOD["sampling_seconds"])
        assert abs(step / fps - 0.2) < 0.002
        start = rally["start_frame"]
        end = rally["end_frame_exclusive"]
        frames = list(range(start, end, step))
        if getattr(model, "predictor", None) and getattr(model.predictor, "trackers", None):
            model.predictor.trackers[0].reset()
        cap = cv2.VideoCapture(str(source))
        assert cap.isOpened()
        rows = []
        try:
            for number in frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f"Could not decode {match} frame {number}")
                result = model.track(image, classes=[0], conf=.2, imgsz=960,
                                     tracker="bytetrack.yaml", persist=True,
                                     verbose=False)[0]
                ids = (result.boxes.id.int().cpu().tolist()
                       if result.boxes.id is not None else [None] * len(result.boxes))
                boxes = result.boxes.xyxy.cpu().tolist()
                scores = result.boxes.conf.cpu().tolist()
                proposals = [{"raw_track_id": track_id,
                              "bbox_px": [round(float(v), 1) for v in bbox],
                              "confidence": round(float(score), 4)}
                             for track_id, bbox, score in zip(ids, boxes, scores)]
                rows.append({"source_frame": number, "time_s": round(number / fps, 3),
                             "all_person_candidate_count": len(proposals),
                             "proposals": proposals})
        finally:
            cap.release()
        output = base / "pilot/transfer_5hz_candidate_screen.json"
        data = {"status": "raw_person_candidates_pending_source_review",
                "match_id": match, "rally_id": rally_id,
                "source_sha256": record["sha256"],
                "source_record_sha256": sha256(record_path),
                "selection_sha256": sha256(selection_path),
                "model_sha256": sha256(MODEL), "method": METHOD,
                "interval_inclusive": [start, end - 1],
                "boundary_status": rally["boundary_status"],
                "frame_step": step, "fps": fps,
                "sampled_frames": len(rows), "rows": rows,
                "limitations": ["All-person boxes have not been assigned to the near-side six.",
                                "Raw IDs are not verified player identities.",
                                "No court coordinates or floor-contact verdicts are calculated.",
                                "Source event bounds are provisional."]}
        output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"{match} {rally_id}: {len(rows)} sampled frames, "
              f"{sum(len(row['proposals']) for row in rows)} all-person boxes", flush=True)


if __name__ == "__main__":
    main()
