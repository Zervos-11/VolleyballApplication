"""Audit frozen D79 raw tracks against the user-checked assisted labels."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/processed/d79_new_source/raw_240_289.json"
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
OUT = ROOT / "data/processed/d79_new_source"


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (area_a + area_b - intersection)


def source_handoff_sheet(raw):
    capture = cv2.VideoCapture(str(VIDEO))
    tiles = []
    for frame in (268, 289):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        good, image = capture.read()
        if not good:
            raise RuntimeError(f"missing source frame {frame}")
        match = [p for p in raw["predictions"][str(frame)] if p["track_id"] == 2]
        if len(match) != 1:
            raise ValueError(f"expected one raw ID 2 box on frame {frame}")
        tile = image[300:520, 470:680].copy()
        x1, y1, x2, y2 = np.rint(match[0]["bbox"]).astype(int)
        cv2.rectangle(tile, (x1 - 470, y1 - 300), (x2 - 470, y2 - 300), (0, 0, 255), 2)
        cv2.putText(tile, f"raw ID 2 / frame {frame}", (3, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)
        tiles.append(tile)
    capture.release()
    if not cv2.imwrite(str(OUT / "raw_id2_handoff_source.jpg"), np.hstack(tiles)):
        raise RuntimeError("could not write handoff sheet")


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    by_player = defaultdict(list)
    edited = []
    all_raw_ids = defaultdict(list)
    for frame in range(240, 290):
        predictions = raw["predictions"][str(frame)]
        for item in predictions:
            all_raw_ids[item["track_id"]].append(frame)
        for person in labels["frames"][str(frame)]["players"]:
            pid = str(person["player_id"])
            box = person.get("bbox")
            origin = person.get("origin_proposal_id")
            if box is None:
                by_player[pid].append({"frame": frame, "raw_track_id": None, "position_status": person["position_status"]})
                continue
            if not origin or not origin.startswith(f"raw_{frame}_"):
                raise ValueError(f"missing source proposal for frame {frame} #{pid}")
            index = int(origin.rsplit("_", 1)[1])
            proposal = predictions[index]
            overlap = iou(box, proposal["bbox"])
            unchanged = np.allclose(box, proposal["bbox"], rtol=0, atol=1e-6)
            by_player[pid].append({"frame": frame, "raw_track_id": proposal["track_id"],
                                   "position_status": person["position_status"],
                                   "box_unchanged": bool(unchanged), "box_iou": round(overlap, 4)})
            if not unchanged:
                edited.append({"frame": frame, "player_id": pid, "raw_track_id": proposal["track_id"],
                               "box_iou": round(overlap, 4)})
    players = {}
    for pid, rows in sorted(by_player.items(), key=lambda item: int(item[0])):
        observed = [row for row in rows if row["raw_track_id"] is not None]
        players[pid] = {
            "visible_boxes_from_frozen_proposals": len(observed),
            "no_box_slots": len(rows) - len(observed),
            "raw_track_id_counts_on_labeled_boxes": dict(Counter(str(row["raw_track_id"]) for row in observed)),
            "unchanged_proposal_boxes": sum(row["box_unchanged"] for row in observed),
            "first_last_boxed_frames": [observed[0]["frame"], observed[-1]["frame"]] if observed else None,
        }
    result = {
        "status": "assisted_development_diagnostic_not_independent_detector_evaluation",
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "frame_range_inclusive": [240, 289],
        "raw_predictions_total": sum(len(raw["predictions"][str(frame)]) for frame in range(240, 290)),
        "visible_labeled_boxes": sum(p["visible_boxes_from_frozen_proposals"] for p in players.values()),
        "unchanged_proposal_boxes": sum(p["unchanged_proposal_boxes"] for p in players.values()),
        "edited_boxes": edited,
        "players": players,
        "raw_id_2_all_frames": all_raw_ids[2],
        "raw_id_2_handoff_source_review": {
            "last_associated_near_player_9_frame": 268,
            "raw_id_absent_frames_inclusive": [269, 288],
            "reappears_frame": 289,
            "source_observation": "At frame 289, raw ID 2 surrounds a far-side teal player while saved near-side #9 remains occluded. Do not reconnect raw ID 2 to #9.",
            "evidence_sheet": "raw_id2_handoff_source.jpg",
        },
        "forbidden_identity_links": [
            {"saved_player_id": "9", "raw_track_id": 2, "from_frame": 289,
             "reason": "source-checked raw ID 2 box belongs to far-side teal player after 20-frame gap"}
        ],
        "limits": "The user selected from visible frozen raw boxes; 230 boxes were retained unchanged. This audit describes proposal use and raw-ID continuity, not independent detection recall, precision, or tracker accuracy.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    source_handoff_sheet(raw)
    (OUT / "raw_assisted_label_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"raw_predictions": result["raw_predictions_total"],
                      "labeled_boxes": result["visible_labeled_boxes"],
                      "unchanged": result["unchanged_proposal_boxes"],
                      "edited": edited,
                      "track_id_counts": {pid: p["raw_track_id_counts_on_labeled_boxes"] for pid, p in players.items()}}, indent=2))


if __name__ == "__main__":
    main()
