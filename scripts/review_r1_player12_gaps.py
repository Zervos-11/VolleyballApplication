"""Render every missing #12 raw-track frame for source-level gap review."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
RAW = BASE / "r1_dense_raw_tracks.json"
GAPS = ((21088, 21098), (21213, 21235), (21239, 21244),
        (21311, 21311), (21394, 21397), (21451, 21451))
SOURCE_NOTES = {
    21088: ("#12 upper body stays visible behind #9; feet are repeatedly obscured.",
            "overlap_with_near_teammate"),
    21213: ("#12 remains visible while moving behind #10; lower-body contact is not clear throughout.",
            "overlap_with_near_teammate"),
    21239: ("#12 remains visible close to #10; the raw box is absent during their crossing.",
            "nearby_teammate_crossing"),
    21311: ("#12 is visible in a fast, unusual posture; shoe contact is not established.",
            "single_frame_detector_dropout"),
    21394: ("#12 remains visible moving right; the target raw ID is absent for four frames.",
            "short_detector_dropout"),
    21451: ("#12 remains visible; the target raw ID is absent for one frame.",
            "single_frame_detector_dropout"),
}


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    reviews = []
    for start, end in GAPS:
        rect = (1080, 460, 1540, 850) if start < 21390 else (1080, 460, 1800, 850)
        tiles = []
        for frame in range(start, end+1):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source frame {frame}")
            left, top, right, bottom = rect
            crop = image[top:bottom, left:right].copy()
            # Show every raw person detection in the gap region. This makes
            # absence of a distinct #12 detection directly reviewable.
            for row in raw["frames"][str(frame)]:
                x1, y1, x2, y2 = [int(v) for v in row["bbox"]]
                if x2 < left or x1 > right or y2 < top or y1 > bottom:
                    continue
                color = (40, 200, 40) if row["track_id"] in (8, 72, 338) else (170, 170, 170)
                cv2.rectangle(crop, (x1-left, y1-top), (x2-left, y2-top), color, 2)
                cv2.putText(crop, f"T{row['track_id']}",
                            (x1-left, max(16, y1-top-4)),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
            cv2.putText(crop, str(frame), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, .9, (255, 255, 255), 3)
            tiles.append(crop)
        empty = np.zeros_like(tiles[0])
        while len(tiles) % 4:
            tiles.append(empty)
        sheet = np.vstack([np.hstack(tiles[i:i+4]) for i in range(0, len(tiles), 4)])
        sheet_name = f"r1_player12_gap_all_{start}_{end}.jpg"
        cv2.imwrite(str(BASE / sheet_name), sheet)
        target_id_presence = [frame for frame in range(start, end+1)
                              if any(row["track_id"] in (8, 72, 338)
                                     for row in raw["frames"][str(frame)])]
        if target_id_presence:
            raise RuntimeError(f"Expected an untracked gap, found IDs at {target_id_presence}")
        reviews.append({
            "frames_inclusive": [start, end],
            "frame_count": end-start+1,
            "source_sheet": sheet_name,
            "source_visibility": "blue_12_visually_present_in_all_reviewed_frames",
            "source_observation": SOURCE_NOTES[start][0],
            "shoe_floor_contact": "not_verified_frame_by_frame",
            "known_target_raw_ids_present": 0,
            "court_positions": "unknown",
            "review_cue": SOURCE_NOTES[start][1],
            "gap_cause": "not_established",
        })
    capture.release()
    record = {
        "status": "single_reviewer_source_gap_audit_not_ground_truth",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "12",
        "gaps": reviews,
        "reviewed_gap_frames": sum(row["frame_count"] for row in reviews),
        "decision": "Retain #12 visual identity across both gaps, but leave boxes and court positions null; do not interpolate movement for a released metric.",
        "production_metric_changed": False, "official_annotations_changed": False,
    }
    (BASE / "r1_player12_gap_source_review.json").write_text(
        json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(f"rendered all {record['reviewed_gap_frames']} gap frames")


if __name__ == "__main__":
    main()
