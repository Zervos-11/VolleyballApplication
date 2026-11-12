from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np

# YOLOv8 from ultralytics
from ultralytics import YOLO

# Returns list of rows: (frame_idx, track_id, cx, cy)
def track_players(
    video_path: str,
    model_name: str = "yolov8n.pt",
    conf: float = 0.20,
    imgsz: int = 960,
    max_frames: Optional[int] = 1000,
    start_frame: int = 0,
    end_frame_exclusive: Optional[int] = None,
    # Reserved until ankle positions can be converted to validated floor contacts.
    use_pose_ankles: bool = False,
    pose_model_name: str = "yolov8n-pose.pt",
    pose_conf: float = 0.30,
) -> List[Tuple[int, int, float, float]]:
    """
    Run YOLOv8 + ByteTrack on a video and return FLOOR points for 'person' tracks.
    We use the bottom-center of the detected bounding box (xmid, y2) as the
    approximate foot contact point on the court plane so that homography to
    top-down stays within the court bounds. (Using box centers projects above
    the floor and often lands outside the rectangle.)
    Works on CPU (slower) or GPU if available.
    """
    if use_pose_ankles:
        raise ValueError(
            "use_pose_ankles cannot be used for court positions: ankle joints are above "
            "the floor and direct homography projection is unvalidated"
        )
    model = YOLO(model_name)

    out: List[Tuple[int, int, float, float]] = []
    import cv2
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    if start_frame < 0 or (end_frame_exclusive is not None and end_frame_exclusive <= start_frame):
        cap.release()
        raise ValueError("Invalid tracking frame interval")
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_idx = start_frame
    processed = 0

    try:
      while end_frame_exclusive is None or frame_idx < end_frame_exclusive:
        if max_frames is not None and processed >= max_frames:
            raise ValueError(f"Tracking interval exceeds max_frames={max_frames}; no partial result was saved")
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f"Video ended before requested frame {frame_idx}")
        result = model.track(
            frame, tracker="bytetrack.yaml", conf=conf, imgsz=imgsz,
            verbose=False, persist=True,
        )[0]

        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()  # [N,4]
            ids  = boxes.id.cpu().numpy() if boxes.id is not None else np.full((xyxy.shape[0],), -1)
            cls  = boxes.cls.cpu().numpy() if boxes.cls is not None else np.full((xyxy.shape[0],), -1)

            # keep only 'person' class if class ids are available (COCO class 0)
            keep = np.ones(xyxy.shape[0], dtype=bool)
            if np.all(cls >= 0):
                keep = (cls == 0)

            xyxy = xyxy[keep]
            ids  = ids[keep]

            if xyxy.size > 0:
                # Default footpoint = bottom-center of bbox
                cx = (xyxy[:, 0] + xyxy[:, 2]) * 0.5
                cy = xyxy[:, 3]

                for k in range(xyxy.shape[0]):
                    out.append((frame_idx, int(ids[k]) if ids[k] is not None else -1, float(cx[k]), float(cy[k])))

        frame_idx += 1
        processed += 1
    finally:
      cap.release()

    return out
