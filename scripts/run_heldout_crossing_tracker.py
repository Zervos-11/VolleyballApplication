"""Freeze ByteTrack predictions for the separate-source crossing windows."""

import json
import os
from pathlib import Path

import cv2


MATCH = Path("data/matches/yt_em6zFUxfYpc")
MODEL = Path("yolov8n.pt")
OUT = MATCH / "pilot/heldout_tracker_predictions.json"


def main():
    os.environ["YOLO_CONFIG_DIR"] = str(Path("data/processed/ultralytics_config").resolve())
    from ultralytics import YOLO

    manifest = json.loads((MATCH / "pilot/heldout_tracking_manifest.json").read_text())
    if OUT.exists():
        raise FileExistsError(f"Frozen predictions already exist: {OUT}")
    result = {"match_id": MATCH.name, "source_sha256": manifest["source_sha256"],
              "tracker": "yolov8n.pt + bytetrack.yaml; conf=0.20; imgsz=960; fresh state per window",
              "windows": {}}
    for window in manifest["windows"]:
        start, last = window["first_frame"], window["last_frame"]
        warmup = max(0, start - 25)
        model = YOLO(str(MODEL))
        video = cv2.VideoCapture(manifest["source_video"])
        video.set(cv2.CAP_PROP_POS_FRAMES, warmup)
        predictions = {}
        try:
            for frame in range(warmup, last + 1):
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(f"Could not decode frame {frame}")
                tracked = model.track(image, tracker="bytetrack.yaml", persist=True,
                                      conf=0.20, imgsz=960, verbose=False)[0]
                if frame < start:
                    continue
                boxes = tracked.boxes
                people = []
                if boxes is not None and len(boxes):
                    xyxy = boxes.xyxy.cpu().numpy()
                    classes = boxes.cls.cpu().numpy()
                    confidences = boxes.conf.cpu().numpy()
                    ids = (boxes.id.cpu().numpy() if boxes.id is not None
                           else [-1] * len(boxes))
                    for box, cls, confidence, track_id in zip(xyxy, classes, confidences, ids):
                        if int(cls) == 0:
                            people.append({"bbox": [round(float(value), 3) for value in box],
                                           "confidence": round(float(confidence), 5),
                                           "track_id": int(track_id)})
                predictions[str(frame)] = people
        finally:
            video.release()
        result["windows"][window["name"]] = {
            "first_frame": start, "last_frame": last,
            "warmup_first_frame": warmup, "predictions": predictions}
        print(f"{window['name']}: {len(predictions)} frames, "
              f"{sum(map(len, predictions.values()))} person predictions", flush=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
