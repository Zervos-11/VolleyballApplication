"""Track from reviewed six-player anchors through conservative live interiors.

This is a detector proposal pass. Exact live-play boundaries and player floor
positions still require separate source review.
"""

import hashlib
import json
import os
import argparse
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402


BASE = ROOT / "data/matches/yt_u5HnY2aNW14"
SCREEN = BASE / "screening"
VIDEO = BASE / "source_720p.mp4"
MODEL = ROOT / "yolov8n.pt"
PHASE = SCREEN / "event_transition_source_qc.json"
RUNS = SCREEN / "full_clip_tracklet_audit.json"
CALIBRATION = SCREEN / "near_court_candidate.json"
OUT = SCREEN / "live_interiors_30fps_screen.json"
BRACKETS = SCREEN / "full_rally_validation_frames/source_event_brackets.json"
SELECTED = ((1, 5), (3, 34))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to-reviewed-dead-bracket", action="store_true")
    args = parser.parse_args()
    phases = json.loads(PHASE.read_text(encoding="utf-8"))
    runs = json.loads(RUNS.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert phases["source_sha256"] == runs["source_sha256"] == sha(VIDEO)
    by_phase = {(p["set"], p["point_number"]): p for p in phases["points"]}
    by_run = {(p["set"], p["point_number"]): p for p in runs["points"]}
    brackets = json.loads(BRACKETS.read_text(encoding="utf-8")) if args.to_reviewed_dead_bracket else None
    by_bracket = ({(p["set"], p["point_number"]): p for p in brackets["points"]}
                  if brackets else {})
    transform = np.asarray(calibration["homography_image_to_court"], np.float64)
    net_y = calibration["points_px"][2][1]
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    points = []
    try:
        for key in SELECTED:
            p = by_phase[key]
            run = by_run[key]["longest_same_six_raw_id_run_full_clip"]
            start = min(p["conservative_interior_start_frame_inclusive"], run["first_frame"])
            end = p["conservative_interior_end_frame_exclusive"]
            if args.to_reviewed_dead_bracket:
                bracket = by_bracket[key]
                assert bracket["last_reviewed_live_frame"] < bracket["first_reviewed_post_point_frame"]
                for field in ("live_image", "post_point_image"):
                    assert (BASE / bracket[field]).exists()
                end = bracket["first_reviewed_post_point_frame"] + 1
            assert start == run["first_frame"] and end > run["last_frame"]
            if getattr(model, "predictor", None) and getattr(model.predictor, "trackers", None):
                model.predictor.trackers[0].reset()
            cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            rows = []
            for frame in range(start, end):
                ok, image = cap.read()
                assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame + 1
                result = model.track(image, classes=[0], conf=.2, imgsz=960,
                                     tracker="bytetrack.yaml", persist=True,
                                     verbose=False)[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                scores = result.boxes.conf.cpu().numpy()
                ids = (result.boxes.id.int().cpu().tolist()
                       if result.boxes.id is not None else [None] * len(boxes))
                proposals = []
                for box, score, raw_id in zip(boxes, scores, ids):
                    x1, y1, x2, y2 = map(float, box)
                    floor = cv2.perspectiveTransform(
                        np.asarray([[[(x1 + x2) / 2, y2]]], np.float32),
                        transform)[0, 0]
                    if not np.isfinite(floor).all() or not ((floor >= -.25) & (floor <= 9.25)).all():
                        continue
                    proposals.append({
                        "raw_track_id": raw_id,
                        "bbox_px": [round(v, 1) for v in (x1, y1, x2, y2)],
                        "box_bottom_court_m": [round(float(v), 3) for v in floor],
                        "confidence": round(float(score), 3),
                        "net_side_status": ("near_floor_side_candidate" if y2 >= net_y
                                            else "net_boundary_review"),
                    })
                near = [x for x in proposals
                        if x["net_side_status"] == "near_floor_side_candidate"]
                rows.append({"source_frame": frame,
                             "near_candidate_count": len(near),
                             "proposals": proposals})
            points.append({"set": key[0], "point_number": key[1],
                           "source_frame_first": start,
                           "source_frame_end_exclusive": end,
                           "conservative_live_interval": [
                               p["conservative_interior_start_frame_inclusive"],
                               p["conservative_interior_end_frame_exclusive"]],
                           "reviewed_dead_transition_bracket": ([
                               by_bracket[key]["last_reviewed_live_frame"],
                               by_bracket[key]["first_reviewed_post_point_frame"]]
                               if args.to_reviewed_dead_bracket else None),
                           "previous_dense_run_interval_inclusive": [
                               run["first_frame"], run["last_frame"]],
                           "rows": rows})
            print(f"S{key[0]} P{key[1]}: {len(rows)} frames; "
                  f"{sum(x['near_candidate_count'] == 6 for x in rows)} with six candidates",
                  flush=True)
    finally:
        cap.release()
    out = {"status": ("source_bracketed_detector_proposals_not_validated_positions"
                      if args.to_reviewed_dead_bracket else
                      "conservative_live_interval_detector_proposals_not_validated_positions"),
           "source_sha256": phases["source_sha256"],
           "input_sha256": {"video": sha(VIDEO), "model": sha(MODEL),
                            "phase": sha(PHASE), "runs": sha(RUNS),
                            "calibration": sha(CALIBRATION),
                            **({"source_event_brackets": sha(BRACKETS)}
                               if args.to_reviewed_dead_bracket else {})},
           "method": "YOLOv8n conf .20 imgsz 960 ByteTrack 30fps, reset per selected point",
           "points": points}
    output = (SCREEN / "source_bracketed_30fps_screen.json"
              if args.to_reviewed_dead_bracket else OUT)
    output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
