"""Render every source frame in blue #10's long missing-box run."""

from __future__ import annotations

import json

import cv2
import numpy as np

from review_r1_p10_gap_source import BASE, SOURCE, VISUAL, CROP, sha256


OUT = BASE / "r1_p10_full_gap_source_review.json"
FRAMES = list(range(21098, 21134))
TILE = (320, 320)
PER_SHEET = 12


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    by_frame = {row["frame"]: row["players"]["10"] for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode source frame {frame}")
            x1, y1, x2, y2 = CROP
            tile = cv2.resize(image[y1:y2, x1:x2], TILE, interpolation=cv2.INTER_AREA)
            cv2.rectangle(tile, (0, 0), (117, 27), (0, 0, 0), -1)
            cv2.putText(tile, str(frame), (6, 21), cv2.FONT_HERSHEY_SIMPLEX,
                        .6, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    sheets = []
    blank = np.full_like(tiles[0], 30)
    for start in range(0, len(tiles), PER_SHEET):
        part = tiles[start:start + PER_SHEET]
        part += [blank] * (PER_SHEET - len(part))
        name = f"r1_p10_full_gap_source_sheet_{start // PER_SHEET + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 4]) for i in (0, 4, 8)]))
        sheets.append(name)
    result = {
        "status": "source_gap_review_complete",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "player_id": "10",
        "missing_run_inclusive": [21099, 21132],
        "source_crop_xyxy": CROP,
        "frames": [{"frame": frame, "candidate_box_status": by_frame[frame]["box_status"],
                    "identity_state": "blue_10_visible",
                    "floor_state": "contact_unverified",
                    "floor_point_px": None, "court_position_m": None,
                    "review_basis": "source_crop_sheet"} for frame in FRAMES],
        "source_sheets": sheets,
        "review_summary": {
            "missing_frames_reviewed": 34,
            "visible_identity_frames": len(FRAMES),
            "conclusion": "The same bent blue #10 with pink shoes is visible in all 34 missing-box frames. Blue #9 partly overlaps her in later frames. No source-floor trajectory or zero-motion interval is established.",
        },
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    assert [row["candidate_box_status"] for row in result["frames"]] == [
        "raw_box_candidate", *["missing"] * 34, "raw_box_candidate"]
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#10: {len(FRAMES)} source frames on {len(sheets)} sheets")


if __name__ == "__main__":
    main()
