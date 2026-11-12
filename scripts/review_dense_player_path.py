"""Prepare an anchored, assisted player path for visual identity review."""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from evaluate_pilot_tracker import iou


MATCH = Path("data/matches/yt_FqE5pTJqx8g")
OUT = Path("data/processed/pilot_tracker_evaluation/dense_identity_window_r4")
ANCHORS = (150190, 150240, 150290)
PLAYER_ID = "13"


def expected_box(frame, boxes):
    left, right = (ANCHORS[0], ANCHORS[1]) if frame <= ANCHORS[1] else (ANCHORS[1], ANCHORS[2])
    weight = (frame - left) / (right - left)
    return (1 - weight) * boxes[left] + weight * boxes[right]


def main():
    labels = json.loads((MATCH / "pilot/player_annotations/r4.json").read_text())
    dense = json.loads((OUT / "tracker_predictions.json").read_text())
    boxes = {frame: np.asarray(next(player["bbox"] for player in
             labels["frames"][str(frame)]["players"]
             if player["player_id"] == PLAYER_ID), dtype=float)
             for frame in ANCHORS}
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    rows = []
    strips = []
    try:
        for frame in range(ANCHORS[0], ANCHORS[-1] + 1):
            expected = expected_box(frame, boxes)
            detections = dense["predictions"][str(frame)]
            ranked = sorted(((iou(expected, det["bbox"]), det) for det in detections),
                            key=lambda pair: -pair[0])
            best_overlap, best = ranked[0] if ranked else (0.0, None)
            second_overlap = ranked[1][0] if len(ranked) > 1 else 0.0
            if best_overlap < .25:
                best = None
            rows.append({"frame_index": frame, "player_id": PLAYER_ID,
                         "candidate_track_id": best["track_id"] if best else "",
                         "candidate_box": json.dumps(best["bbox"]) if best else "",
                         "anchor_iou": round(best_overlap, 4),
                         "runner_up_iou": round(second_overlap, 4),
                         "review_status": "assisted_unreviewed"})
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame}")
            center_x = int((expected[0] + expected[2]) / 2)
            center_y = int((expected[1] + expected[3]) / 2)
            left = max(0, min(image.shape[1] - 360, center_x - 180))
            top = max(0, min(image.shape[0] - 300, center_y - 150))
            crop = image[top:top + 300, left:left + 360].copy()
            if best:
                x1, y1, x2, y2 = [int(v) for v in best["bbox"]]
                cv2.rectangle(crop, (x1 - left, y1 - top), (x2 - left, y2 - top),
                              (0, 255, 0), 2)
            cv2.putText(crop, f"{frame} id:{best['track_id'] if best else '-'} IoU:{best_overlap:.2f}",
                        (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 3)
            cv2.putText(crop, f"{frame} id:{best['track_id'] if best else '-'} IoU:{best_overlap:.2f}",
                        (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            strips.append(crop)
    finally:
        video.release()
    with (OUT / "player13_assisted_path.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for start in range(0, len(strips), 12):
        page = np.full((900, 1440, 3), 255, dtype=np.uint8)
        for offset, image in enumerate(strips[start:start + 12]):
            y, x = divmod(offset, 4)
            page[y * 300:(y + 1) * 300, x * 360:(x + 1) * 360] = image
        cv2.imwrite(str(OUT / f"player13_review_{start // 12 + 1:02d}.jpg"), page)
    print(json.dumps({"frames": len(rows), "candidate_found": sum(bool(r["candidate_track_id"]) for r in rows),
                      "low_overlap": [r["frame_index"] for r in rows if r["anchor_iou"] < .4],
                      "track_ids": sorted({r["candidate_track_id"] for r in rows if r["candidate_track_id"]})},
                     indent=2))


if __name__ == "__main__":
    main()
