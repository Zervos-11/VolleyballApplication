"""Anchor full-point D79 raw tracks to the checked 50-frame near-side slice."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/processed/d79_new_source/raw_point_candidate_80_336.json"
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
OUT = ROOT / "data/processed/d79_new_source"
FIRST, LAST = 80, 336


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (area_a + area_b - intersection)


def gaps(frames):
    return [[left + 1, right - 1] for left, right in zip(frames, frames[1:]) if right > left + 1]


def source_sheet(raw):
    capture = cv2.VideoCapture(str(VIDEO))
    selected = [80, 120, 180, 240, 289, 330, 336]
    tiles = []
    for frame in selected:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        good, image = capture.read()
        if not good:
            raise RuntimeError(f"source frame {frame} unavailable")
        for row in raw["predictions"][str(frame)]:
            if row["track_id"] not in (1, 5):
                continue
            x1, y1, x2, y2 = np.rint(row["bbox"]).astype(int)
            color = (0, 200, 0) if row["track_id"] == 1 else (255, 0, 200)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
            cv2.putText(image, "#8" if row["track_id"] == 1 else "#98",
                        (x1, max(25, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, color, 2)
        tile = cv2.resize(image, (640, 360))
        cv2.putText(tile, str(frame), (15, 35), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255, 255, 255), 2)
        tiles.append(tile)
    capture.release()
    tiles.append(np.full_like(tiles[0], 255))
    sheet = np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])])
    if not cv2.imwrite(str(OUT / "point_candidate_8_98_source_sheet.jpg"), sheet):
        raise RuntimeError("could not save source sheet")


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    if (raw["first_frame"], raw["last_frame"]) != (FIRST, LAST):
        raise ValueError("unexpected raw point interval")
    anchor = defaultdict(list)
    low = []
    for frame in range(240, 290):
        predictions = raw["predictions"][str(frame)]
        for row in labels["frames"][str(frame)]["players"]:
            if row["bbox"] is None:
                continue
            best = max(predictions, key=lambda candidate: iou(row["bbox"], candidate["bbox"]))
            overlap = iou(row["bbox"], best["bbox"])
            if overlap < 0.5:
                low.append({"frame": frame, "player_id": row["player_id"], "best_iou": round(overlap, 3)})
            anchor[str(row["player_id"])].append((frame, best["track_id"], overlap))
    all_ids = defaultdict(list)
    for frame in range(FIRST, LAST + 1):
        for row in raw["predictions"][str(frame)]:
            all_ids[row["track_id"]].append(frame)
    players = {}
    for pid, samples in sorted(anchor.items(), key=lambda item: int(item[0])):
        counts = Counter(track_id for _, track_id, _ in samples)
        dominant_id = counts.most_common(1)[0][0]
        frames = all_ids[dominant_id]
        players[pid] = {
            "checked_anchor_box_count": len(samples),
            "anchor_raw_id_counts": {str(k): v for k, v in counts.items()},
            "anchor_min_iou": round(min(overlap for _, _, overlap in samples), 3),
            "dominant_raw_id": dominant_id,
            "dominant_raw_id_frame_count": len(frames),
            "dominant_raw_id_first_last": [frames[0], frames[-1]],
            "dominant_raw_id_internal_gaps_inclusive": gaps(frames),
            "full_point_identity_status": (
                "source_sampled_continuity_candidate" if pid in ("8", "98")
                else "anchor_only_do_not_assume_full_point_identity"
            ),
        }
    result = {
        "status": "development_full_point_track_coverage_not_validated_distance",
        "source_sha256": raw["source_sha256"],
        "raw_candidate_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "checked_labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "active_play_candidate_frames_inclusive": [FIRST, LAST],
        "frames": LAST - FIRST + 1,
        "raw_boxes": sum(len(raw["predictions"][str(frame)]) for frame in range(FIRST, LAST + 1)),
        "saved_visible_anchor_boxes": sum(len(v) for v in anchor.values()),
        "anchor_best_iou_below_0_5": low,
        "players": players,
        "source_sample_sheet": "point_candidate_8_98_source_sheet.jpg",
        "forbidden_raw_identity_links": [
            {"saved_player_id": "9", "raw_track_id": 30, "from_frame": 289,
             "reason": "20-frame gap followed by far-side teal player; source-confirmed in shorter frozen run and visually present in point candidate"}
        ],
        "limits": "The 50-frame anchor labels were assisted by a separate frozen tracker run. ID continuity outside the checked window is a candidate; foot contact, airborne state, and other players' identities are not dense-reviewed. Do not publish full-point travel from these raw boxes.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    source_sheet(raw)
    (OUT / "point_candidate_track_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frames": result["frames"], "raw_boxes": result["raw_boxes"],
                      "anchor_low_iou": len(low),
                      "players": {pid: [p["dominant_raw_id"], p["dominant_raw_id_frame_count"]]
                                  for pid, p in players.items()}}, indent=2))


if __name__ == "__main__":
    main()
