"""Bounded shoe-template experiment across blue #10's missing person boxes.

The source floor-point proposal identifies the player at the starting frame.
Subsequent points are image-template candidates, never confirmed floor contacts.
"""

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
OUT = BASE / "r1_p10_seeded_shoe_experiment.json"
SHEET_PREFIX = "r1_p10_seeded_shoe_sheet"
START, END = 21098, 21133
SEED = (1228, 816)  # Existing analyst left-pink-shoe contact proposal.
PATCH_HALF = (15, 11)
SEARCH_RADIUS = 24
MIN_SCORE = 0.55
MAX_STEP_PX = 12.0
CROP = (1160, 735, 1300, 850)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def patch_at(frame: np.ndarray, center: tuple[int, int]) -> np.ndarray:
    x, y = center
    hx, hy = PATCH_HALF
    return frame[y - hy:y + hy + 1, x - hx:x + hx + 1]


def locate(template: np.ndarray, frame: np.ndarray,
           previous: tuple[int, int]) -> tuple[tuple[int, int] | None, float]:
    x, y = previous
    hx, hy = PATCH_HALF
    x0, x1 = x - SEARCH_RADIUS - hx, x + SEARCH_RADIUS + hx + 1
    y0, y1 = y - SEARCH_RADIUS - hy, y + SEARCH_RADIUS + hy + 1
    if x0 < 0 or y0 < 0 or x1 > frame.shape[1] or y1 > frame.shape[0]:
        return None, 0.0
    scores = cv2.matchTemplate(frame[y0:y1, x0:x1], template,
                               cv2.TM_CCOEFF_NORMED)
    _, score, _, top_left = cv2.minMaxLoc(scores)
    point = (x0 + top_left[0] + hx, y0 + top_left[1] + hy)
    if score < MIN_SCORE or np.linalg.norm(np.subtract(point, previous)) > MAX_STEP_PX:
        return None, float(score)
    return point, float(score)


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    by_frame = {row["frame"]: row["players"]["10"] for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    frames: list[np.ndarray] = []
    try:
        for frame_no in range(START, END + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source frame {frame_no}")
            frames.append(frame)
    finally:
        cap.release()
    gray = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]
    template = patch_at(gray[0], SEED).copy()
    assert template.shape == (2 * PATCH_HALF[1] + 1, 2 * PATCH_HALF[0] + 1)
    points: list[tuple[int, int] | None] = [SEED]
    scores = [1.0]
    for image in gray[1:]:
        previous = points[-1]
        if previous is None:
            points.append(None)
            scores.append(0.0)
            continue
        point, score = locate(template, image, previous)
        points.append(point)
        scores.append(score)
    rows, tiles = [], []
    x0, y0, x1, y1 = CROP
    for index, frame_no in enumerate(range(START, END + 1)):
        point = points[index]
        row = {
            "frame": frame_no,
            "player_id": "10",
            "candidate_box_status": by_frame[frame_no]["box_status"],
            "shoe_template_centre_px": list(point) if point else None,
            "template_score": round(scores[index], 3),
            "state": "seed_contact_proposal" if index == 0 else
                     "unverified_image_match" if point else "no_match",
            "verified_floor_contact_px": None,
            "court_position_m": None,
        }
        rows.append(row)
        tile = cv2.resize(frames[index][y0:y1, x0:x1], (420, 345),
                          interpolation=cv2.INTER_LINEAR)
        if point is not None:
            xy = ((point[0] - x0) * 3, (point[1] - y0) * 3)
            cv2.drawMarker(tile, xy, (0, 255, 255), cv2.MARKER_CROSS, 16, 2)
        cv2.putText(tile, f"{frame_no} {scores[index]:.2f}", (8, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(tile, f"{frame_no} {scores[index]:.2f}", (8, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(tile)
    sheets = []
    for start in range(0, len(tiles), 12):
        group = tiles[start:start + 12]
        name = f"{SHEET_PREFIX}_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(group[i:i + 4]) for i in (0, 4, 8)]))
        sheets.append(name)
    result = {
        "status": "development_shoe_template_experiment_unverified",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "seed": {"frame": START, "player_id": "10", "left_shoe_floor_contact_proposal_px": list(SEED),
                 "basis": "r1_p10_gap_source_review.json analyst proposal"},
        "method": {"template_size_px": list(template.shape[::-1]),
                   "search_radius_px": SEARCH_RADIUS, "minimum_score": MIN_SCORE,
                   "maximum_step_px": MAX_STEP_PX,
                   "fixed_initial_grayscale_template": True},
        "frames": rows,
        "sheets": sheets,
        "limitation": "Template locations are image matches, not proof of the same shoe or a grounded contact. No court or movement metric is produced.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{sum(point is not None for point in points)}/{len(points)} template matches; {len(sheets)} sheets")


if __name__ == "__main__":
    main()
