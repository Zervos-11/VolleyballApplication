"""Create source-only contact sheets for blue #11's two long raw-box gaps."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
OUT = BASE / "r1_p11_long_gap_source_review.json"
RUNS = [(21189, 21235), (21266, 21298)]
FRAMES = [21188, *range(21189, 21236), 21236,
          21265, *range(21266, 21299), 21299]
CROP = (620, 425, 1120, 825)
TILE = (500, 400)
PER_SHEET = 12
AIRBORNE_FRAMES = set(range(21231, 21237))


def reviewed_state(frame: int) -> dict:
    """Visual assessment of the seven source sheets, without a floor coordinate."""
    return {
        "identity_state": "blue_11_visible",
        "floor_state": "airborne" if frame in AIRBORNE_FRAMES else "contact_unverified",
        "floor_point_px": None,
        "court_position_m": None,
        "review_basis": "source_crop_sheet",
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    by_frame = {row["frame"]: row["players"]["11"] for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    tiles, rows = [], []
    try:
        for frame in FRAMES:
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
            rows.append({"frame": frame, "candidate_box_status": by_frame[frame]["box_status"],
                         **reviewed_state(frame)})
    finally:
        cap.release()
    sheets = []
    blank = np.full_like(tiles[0], 30)
    for start in range(0, len(tiles), PER_SHEET):
        part = tiles[start:start+PER_SHEET]
        part += [blank] * (PER_SHEET - len(part))
        name = f"r1_p11_long_gap_source_sheet_{start//PER_SHEET+1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i+4]) for i in (0, 4, 8)]))
        sheets.append(name)
    result = {
        "status": "source_gap_review_complete",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "player_id": "11",
        "missing_runs_inclusive": [list(run) for run in RUNS],
        "source_crop_xyxy": list(CROP),
        "frames": rows,
        "source_sheets": sheets,
        "review_summary": {
            "missing_frames_reviewed": sum(row["candidate_box_status"] == "missing" for row in rows),
            "visible_identity_frames": sum(row["identity_state"] == "blue_11_visible" for row in rows),
            "airborne_frames": sorted(AIRBORNE_FRAMES),
            "conclusion": "Blue #11 remains visible through both missing-box runs. She jumps during the first run; the second contains nearby players and uncertain foot contact. No gap path length or zero-motion assumption is supported.",
        },
        "limitation": "Source crops can classify visibility and identity continuity but do not provide grounded shoe coordinates or a path length. Existing raw boxes and annotations remain unchanged.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    assert result["review_summary"]["missing_frames_reviewed"] == 80
    assert all(row["candidate_box_status"] == ("missing" if any(start <= row["frame"] <= end for start, end in RUNS) else "raw_box_candidate") for row in rows)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#11: {len(FRAMES)} source frames on {len(sheets)} sheets")


if __name__ == "__main__":
    main()
