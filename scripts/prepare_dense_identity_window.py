"""Track every frame of an r4 identity-change window and make review images."""

import json
import os
from pathlib import Path

import cv2
import numpy as np


MATCH = Path("data/matches/yt_FqE5pTJqx8g")
OUT = Path("data/processed/pilot_tracker_evaluation/dense_identity_window_r4")
FIRST = 150190
LAST = 150290
RALLY_START = 149990
STRIDE = 10


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(Path("data/processed/ultralytics_config").resolve())
    from ultralytics import YOLO
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    video.set(cv2.CAP_PROP_POS_FRAMES, RALLY_START)
    model = YOLO("yolov8n.pt")
    predictions = {}
    frames = []
    try:
        for frame_index in range(RALLY_START, LAST + 1):
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame_index}")
            result = model.track(image, tracker="bytetrack.yaml", persist=True,
                                 conf=0.20, imgsz=960, verbose=False)[0]
            if frame_index < FIRST:
                continue
            boxes = result.boxes
            people = []
            if boxes is not None and len(boxes):
                xyxy = boxes.xyxy.cpu().numpy()
                cls = boxes.cls.cpu().numpy()
                conf = boxes.conf.cpu().numpy()
                ids = (boxes.id.cpu().numpy() if boxes.id is not None
                       else [-1] * len(boxes))
                for box, kind, confidence, track_id in zip(xyxy, cls, conf, ids):
                    if int(kind) == 0:
                        people.append({"bbox": [round(float(v), 3) for v in box],
                                       "confidence": round(float(confidence), 5),
                                       "track_id": int(track_id)})
            predictions[str(frame_index)] = people
            if (frame_index - FIRST) % STRIDE == 0:
                preview = cv2.resize(image, (640, 360))
                for person in people:
                    x1, y1, x2, y2 = [int(v / 3) for v in person["bbox"]]
                    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 230, 255), 1)
                    cv2.putText(preview, str(person["track_id"]),
                                (x1, max(15, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX,
                                .45, (0, 0, 0), 2)
                    cv2.putText(preview, str(person["track_id"]),
                                (x1, max(15, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX,
                                .45, (0, 230, 255), 1)
                cv2.putText(preview, str(frame_index), (8, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 0), 3)
                cv2.putText(preview, str(frame_index), (8, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 1)
                cv2.imwrite(str(OUT / f"frame_{frame_index}.jpg"), preview)
                frames.append(preview)
            if frame_index % 50 == 0:
                print(f"Tracked through {frame_index}", flush=True)
    finally:
        video.release()
    payload = {"rally_id": "r4", "first_frame": FIRST, "last_frame": LAST,
               "source_fps": 50, "tracker": "yolov8n.pt ByteTrack conf=0.20 imgsz=960",
               "predictions": predictions}
    (OUT / "tracker_predictions.json").write_text(json.dumps(payload, indent=2) + "\n")
    for page in range(0, len(frames), 6):
        group = frames[page:page + 6]
        canvas = 255 * np.ones((1080, 1280, 3), dtype="uint8")
        for index, image in enumerate(group):
            y, x = divmod(index, 2)
            canvas[y * 360:(y + 1) * 360, x * 640:(x + 1) * 640] = image
        cv2.imwrite(str(OUT / f"contact_sheet_{page // 6 + 1}.jpg"), canvas)
    print(f"Saved {len(predictions)} dense frames and {len(frames)} review thumbnails")


if __name__ == "__main__":
    main()
