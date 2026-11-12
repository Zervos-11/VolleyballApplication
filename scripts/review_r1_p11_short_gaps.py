"""Create source-only sheets for blue #11's short missing-box runs."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from review_r1_p11_long_gaps import BASE, SOURCE, VISUAL, CROP, TILE, sha256


OUT = BASE / "r1_p11_short_gap_source_review.json"
EXCLUDED_LONG_RUNS = {(21189, 21235), (21266, 21298)}
PER_SHEET = 12
AIRBORNE_MISSING_FRAMES = set(range(21239, 21245)) | {21255, 21256}


def missing_runs(frames: list[int]) -> list[tuple[int, int]]:
    runs = []
    start = end = frames[0]
    for frame in frames[1:]:
        if frame == end + 1:
            end = frame
        else:
            runs.append((start, end))
            start = end = frame
    runs.append((start, end))
    return runs


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    by_frame = {row["frame"]: row["players"]["11"] for row in visual["frame_records"]}
    runs = [run for run in missing_runs([frame for frame, player in by_frame.items()
                                         if player["box_status"] == "missing"])
            if run not in EXCLUDED_LONG_RUNS]
    frames = sorted({frame for start, end in runs for frame in range(start - 1, end + 2)})
    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    try:
        for frame in frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode source frame {frame}")
            x1, y1, x2, y2 = CROP
            tile = cv2.resize(image[y1:y2, x1:x2], TILE, interpolation=cv2.INTER_AREA)
            cv2.rectangle(tile, (0, 0), (145, 32), (0, 0, 0), -1)
            cv2.putText(tile, str(frame), (8, 24), cv2.FONT_HERSHEY_SIMPLEX,
                        .75, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    sheets = []
    blank = np.full_like(tiles[0], 30)
    for start in range(0, len(tiles), PER_SHEET):
        part = tiles[start:start + PER_SHEET]
        part += [blank] * (PER_SHEET - len(part))
        name = f"r1_p11_short_gap_source_sheet_{start // PER_SHEET + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 4]) for i in (0, 4, 8)]))
        sheets.append(name)
    result = {
        "status": "source_gap_review_complete",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "player_id": "11",
        "missing_runs_inclusive": [list(run) for run in runs],
        "source_crop_xyxy": list(CROP),
        "frames": [{"frame": frame, "candidate_box_status": by_frame[frame]["box_status"],
                    "identity_state": "blue_11_visible",
                    "floor_state": ("airborne" if frame in AIRBORNE_MISSING_FRAMES
                                    else "contact_unverified"),
                    "floor_point_px": None, "court_position_m": None,
                    "review_basis": "source_crop_sheet"} for frame in frames],
        "source_sheets": sheets,
        "review_summary": {
            "missing_frames_reviewed": sum(end - start + 1 for start, end in runs),
            "visible_identity_frames": len(frames),
            "airborne_missing_frames": sorted(AIRBORNE_MISSING_FRAMES),
            "conclusion": "Blue #11 is visible through all short missing-box runs. Two short runs coincide with blocking jumps. No missing detector box or floor path is reconstructed.",
        },
        "limitation": "Source crops assess visibility, not a full floor path or metric. Candidate boxes and official labels remain unchanged.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    assert sum(end - start + 1 for start, end in runs) == 23
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#11: {len(runs)} short runs, {len(frames)} source frames on {len(sheets)} sheets")


if __name__ == "__main__":
    main()
