"""Screen the post hoc USC–BYU side-out exemplar for person proposals at 5 Hz.

This output is a review queue. It does not assign teams, jerseys, floor points,
or a validated rally trajectory.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/source_view_screen/usc_byu_sideout_candidate_0751_0803.mp4"
OUTPUT = ROOT / "data/processed/source_view_screen/usc_byu_sideout_review/raw_5hz_candidates.json"
MODEL = ROOT / "yolov8n.pt"
EXPECTED_SOURCE_SHA = "19a22a123595bb95d2d033c798692c975572f169bf11f34f06d4d3a52501e072"
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if sha256(SOURCE) != EXPECTED_SOURCE_SHA:
        raise ValueError("Side-out clip hash changed")
    cap = cv2.VideoCapture(str(SOURCE))
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if abs(fps - 30) > 0.01 or count != 360:
        raise ValueError(f"Expected a 12-second, 30-fps clip; got {count} frames at {fps} fps")
    model = YOLO(str(MODEL))
    rows = []
    try:
        for frame in range(0, count, 6):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode frame {frame}")
            result = model.track(image, classes=[0], conf=0.2, imgsz=960,
                                 tracker="bytetrack.yaml", persist=True,
                                 verbose=False)[0]
            ids = (result.boxes.id.int().cpu().tolist()
                   if result.boxes.id is not None else [None] * len(result.boxes))
            proposals = [
                {"raw_track_id": ident,
                 "bbox_px": [round(float(x), 1) for x in box],
                 "confidence": round(float(score), 4)}
                for ident, box, score in zip(ids, result.boxes.xyxy.cpu().tolist(),
                                             result.boxes.conf.cpu().tolist())
            ]
            rows.append({"clip_frame": frame, "clip_time_s": round(frame / fps, 3),
                         "nominal_video_time_s": round(451 + frame / fps, 3),
                         "all_person_candidate_count": len(proposals),
                         "proposals": proposals})
    finally:
        cap.release()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "status": "raw_person_candidates_pending_source_review",
        "selection_kind": "post_hoc_source_selected_sideout_exemplar",
        "selection_record": "DELIVERABLES/HONOURS_USC_BYU_SIDEOUT_CANDIDATE_2026-11-07.md",
        "source_clip": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_clip_sha256": EXPECTED_SOURCE_SHA,
        "model_sha256": sha256(MODEL),
        "fps": fps,
        "frame_step": 6,
        "method": {"detector": "YOLOv8n person", "tracker": "ByteTrack",
                   "confidence": 0.2, "image_size": 960},
        "rows": rows,
        "limitations": [
            "All persons include USC, BYU, bench staff and officials.",
            "Raw track IDs and candidate boxes are not verified BYU player identities.",
            "A box bottom is not an accepted floor coordinate without source review.",
            "No comparison with point outcomes is supported by this selected exemplar.",
        ],
    }
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} frames and {sum(len(r['proposals']) for r in rows)} raw proposals")


if __name__ == "__main__":
    main()
