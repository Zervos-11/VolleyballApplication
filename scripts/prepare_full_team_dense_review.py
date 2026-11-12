"""Build all-six-player assisted identity paths in a 51-frame r4 window."""

import csv
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from evaluate_pilot_tracker import iou


MATCH = Path("data/matches/yt_FqE5pTJqx8g")
SOURCE = Path("data/processed/pilot_tracker_evaluation/dense_identity_window_r4")
OUT = SOURCE / "full_team_150240_150290"
FIRST, LAST = 150240, 150290
MIN_IOU = 0.20


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    labels = json.loads((MATCH / "pilot/player_annotations/r4.json").read_text())
    dense = json.loads((SOURCE / "tracker_predictions.json").read_text())
    player_ids = sorted(player["player_id"] for player in labels["frames"][str(FIRST)]["players"])
    anchors = {}
    for frame in (FIRST, LAST):
        anchors[frame] = {player["player_id"]: np.asarray(player["bbox"], dtype=float)
                          for player in labels["frames"][str(frame)]["players"]}
    visual = json.loads((OUT / "visual_keyframes.json").read_text())
    for frame, box in visual["boxes"].items():
        anchors[int(frame)] = {visual["player_id"]: np.asarray(box, dtype=float)}
    if any(anchors[frame][player_id].shape != (4,)
           for frame in (FIRST, LAST) for player_id in player_ids):
        raise ValueError("Both saved endpoint frames must have all six boxes")
    rows = []
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    review_frames = []
    colours = [(30, 200, 255), (255, 0, 255), (0, 255, 0),
               (255, 180, 0), (0, 0, 255), (255, 255, 0)]
    try:
        for frame in range(FIRST, LAST + 1):
            expected = {}
            for key in player_ids:
                known = sorted(index for index, values in anchors.items() if key in values)
                left = max(index for index in known if index <= frame)
                right = min(index for index in known if index >= frame)
                weight = (frame - left) / (right - left) if right > left else 0.0
                expected[key] = ((1 - weight) * anchors[left][key] +
                                 weight * anchors[right][key])
            detections = dense["predictions"][str(frame)]
            overlaps = np.asarray([[iou(expected[key], det["bbox"])
                                    for det in detections] for key in player_ids])
            padded = np.pad(overlaps, ((0, 0), (0, len(player_ids))), constant_values=0)
            index_a, index_b = linear_sum_assignment(-padded)
            selected = {player_ids[i]: j for i, j in zip(index_a, index_b)
                        if j < len(detections) and overlaps[i, j] >= MIN_IOU}
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f"Cannot read frame {frame}")
            preview = cv2.resize(image, (960, 540))
            cv2.putText(preview, str(frame), (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        .8, (255, 255, 255), 2)
            for index, key in enumerate(player_ids):
                j = selected.get(key)
                best = detections[j] if j is not None else None
                score = float(overlaps[index, j]) if j is not None else 0.0
                alternatives = sorted(overlaps[index], reverse=True)
                runner_up = float(alternatives[1]) if len(alternatives) > 1 else 0.0
                rows.append({"frame_index": frame, "player_id": key,
                             "candidate_track_id": best["track_id"] if best else "",
                             "candidate_box": json.dumps(best["bbox"]) if best else "",
                             "anchor_iou": round(score, 4),
                             "runner_up_iou": round(runner_up, 4),
                             "review_status": "assisted_unreviewed"})
                if best:
                    x1, y1, x2, y2 = [int(v / 2) for v in best["bbox"]]
                    cv2.rectangle(preview, (x1, y1), (x2, y2), colours[index], 2)
                    cv2.putText(preview, f"#{key} T{best['track_id']}",
                                (x1, max(20, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX,
                                .48, (0, 0, 0), 3)
                    cv2.putText(preview, f"#{key} T{best['track_id']}",
                                (x1, max(20, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX,
                                .48, colours[index], 1)
            if (frame - FIRST) % 5 == 0:
                review_frames.append(preview)
    finally:
        video.release()
    with (OUT / "assisted_paths.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for start in range(0, len(review_frames), 4):
        page = np.full((1080, 1920, 3), 255, dtype=np.uint8)
        for offset, image in enumerate(review_frames[start:start + 4]):
            y, x = divmod(offset, 2)
            page[y * 540:(y + 1) * 540, x * 960:(x + 1) * 960] = image
        cv2.imwrite(str(OUT / f"court_review_{start // 4 + 1:02d}.jpg"), page)
    crop_video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    try:
        for key in player_ids:
            player_rows = [row for row in rows if row["player_id"] == key]
            crops = []
            for row in player_rows:
                frame = row["frame_index"]
                crop_video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = crop_video.read()
                if not ok:
                    raise RuntimeError(f"Cannot reread frame {frame}")
                box = (json.loads(row["candidate_box"]) if row["candidate_box"]
                       else (1 - (frame - FIRST) / (LAST - FIRST)) * anchors[FIRST][key]
                       + (frame - FIRST) / (LAST - FIRST) * anchors[LAST][key])
                center_x = int((box[0] + box[2]) / 2)
                center_y = int((box[1] + box[3]) / 2)
                left = max(0, min(image.shape[1] - 300, center_x - 150))
                top = max(0, min(image.shape[0] - 300, center_y - 150))
                crop = image[top:top + 300, left:left + 300].copy()
                if row["candidate_box"]:
                    x1, y1, x2, y2 = [int(v) for v in box]
                    cv2.rectangle(crop, (x1 - left, y1 - top),
                                  (x2 - left, y2 - top), (0, 255, 0), 2)
                caption = (f"{frame} #{key} T{row['candidate_track_id']}"
                           if row["candidate_box"] else f"{frame} #{key} NO BOX")
                cv2.putText(crop, caption, (4, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, .50, (0, 0, 0), 3)
                cv2.putText(crop, caption, (4, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, .50, (255, 255, 255), 1)
                crops.append(crop)
            for start in range(0, len(crops), 20):
                page = np.full((1200, 1500, 3), 255, dtype=np.uint8)
                for offset, crop in enumerate(crops[start:start + 20]):
                    y, x = divmod(offset, 5)
                    page[y * 300:(y + 1) * 300, x * 300:(x + 1) * 300] = crop
                cv2.imwrite(str(OUT / f"player{key}_review_{start // 20 + 1:02d}.jpg"), page)
    finally:
        crop_video.release()
    weak = [row for row in rows if row["anchor_iou"] < .4]
    summary = {"frames": LAST - FIRST + 1, "players": player_ids,
               "candidate_boxes": sum(bool(row["candidate_box"]) for row in rows),
               "possible_boxes": len(rows),
               "weak_frames": [{"frame": row["frame_index"], "player_id": row["player_id"],
                                "iou": row["anchor_iou"]} for row in weak]}
    (OUT / "preparation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
