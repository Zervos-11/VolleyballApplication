"""Build source-resolution shoe crops for sampled #9 floor-proxy checks."""

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
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
FRAMES = [21070, 21110, 21150, 21190, 21230, 21270,
          21310, 21350, 21390, 21430, 21463]
CONTACTS = {
    # Approximate source-pixel floor points from the enlarged crop sheets.
    # These are analyst proposals, not edits to the user's saved draft.
    21070: ([1526.0, 929.0], "one_visible_planted_shoe"),
    21110: ([1268.0, 885.0], "one_visible_planted_shoe"),
    21150: ([1126.0, 873.0], "two_sole_floor_midpoint"),
    21190: ([1026.5, 876.5], "two_sole_floor_midpoint"),
    21230: ([986.0, 880.0], "two_sole_floor_midpoint"),
    21270: ([981.5, 885.0], "two_sole_floor_midpoint"),
    21310: ([904.0, 908.5], "one_visible_planted_shoe"),
    21350: ([815.0, 904.0], "one_visible_planted_shoe"),
    21390: ([820.0, 857.0], "one_visible_planted_shoe"),
    21430: ([843.5, 844.0], "two_sole_floor_midpoint"),
    21463: ([829.0, 855.5], "two_sole_floor_midpoint"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    boxes = {row["frame"]: row["players"]["9"] for row in visual["frame_records"]}
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    try:
        for frame in FRAMES:
            candidate = boxes[frame]
            if candidate["box_status"] != "raw_box_candidate":
                raise ValueError(f"No usable #9 box at frame {frame}")
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode source frame {frame}")
            x1, _, x2, y2 = candidate["bbox_px"]
            cx = (x1 + x2) / 2
            left = max(0, min(image.shape[1] - 200, round(cx) - 100))
            top = max(0, min(image.shape[0] - 140, round(y2) - 120))
            tile = cv2.resize(image[top:top + 140, left:left + 200], (400, 280),
                              interpolation=cv2.INTER_LINEAR)
            cv2.putText(tile, str(frame), (8, 27), cv2.FONT_HERSHEY_SIMPLEX,
                        .75, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(tile, str(frame), (8, 27), cv2.FONT_HERSHEY_SIMPLEX,
                        .75, (0, 255, 255), 2, cv2.LINE_AA)
            marked = CONTACTS.get(frame)
            point = marked[0] if marked else None
            court = None
            if point is not None:
                if not (left <= point[0] < left + 200 and top <= point[1] < top + 140):
                    raise ValueError(f"Contact outside crop at {frame}")
                court = cv2.perspectiveTransform(np.float32([[point]]), matrix)[0, 0]
                px = (round((point[0] - left) * 2), round((point[1] - top) * 2))
                cv2.drawMarker(tile, px, (0, 255, 255), cv2.MARKER_CROSS, 20, 2, cv2.LINE_AA)
            tiles.append(tile)
            box_point = [(x1 + x2) / 2, y2]
            box_court = cv2.perspectiveTransform(np.float32([[box_point]]), matrix)[0, 0]
            discrepancy = float(np.linalg.norm(court - box_court)) if court is not None else None
            rows.append({"frame_index": frame, "crop_source_xyxy": [left, top, left + 200, top + 140],
                         "contact_px": point, "court_m_diagnostic":
                         [round(float(v), 3) for v in court] if court is not None else None,
                         "contact_state": marked[1] if marked else "pending_visual_review",
                         "box_bottom_court_m_diagnostic": [round(float(v), 3) for v in box_court],
                         "floor_vs_box_bottom_m_diagnostic": round(discrepancy, 3) if discrepancy is not None else None})
    finally:
        cap.release()
    for index in range(0, len(tiles), 4):
        group = tiles[index:index + 4]
        while len(group) < 4:
            group.append(np.full_like(group[0], 32))
        cv2.imwrite(str(BASE / f"r1_p9_contact_check_sheet_{index // 4 + 1}.jpg"), cv2.hconcat(group))
    reviewed = [row for row in rows if row["court_m_diagnostic"] is not None]
    sample_metrics = None
    if len(reviewed) >= 2:
        contacts = np.asarray([row["court_m_diagnostic"] for row in reviewed], dtype=float)
        box_bottoms = np.asarray([row["box_bottom_court_m_diagnostic"] for row in reviewed], dtype=float)
        offsets = [row["floor_vs_box_bottom_m_diagnostic"] for row in reviewed]
        sample_metrics = {
            "reviewed_grounded_frames": len(reviewed),
            "sampled_contact_polyline_m": round(float(np.linalg.norm(np.diff(contacts, axis=0), axis=1).sum()), 3),
            "sampled_box_bottom_polyline_m": round(float(np.linalg.norm(np.diff(box_bottoms, axis=0), axis=1).sum()), 3),
            "first_to_last_contact_displacement_m": round(float(np.linalg.norm(contacts[-1] - contacts[0])), 3),
            "floor_vs_box_bottom_median_m": round(float(np.median(offsets)), 3),
            "floor_vs_box_bottom_max_m": round(float(max(offsets)), 3),
            "inside_nominal_near_court_count": int(np.logical_and.reduce(
                (contacts[:, 0] >= 0, contacts[:, 0] <= 9,
                 contacts[:, 1] >= 0, contacts[:, 1] <= 9)).sum()),
            "interpretation": "Sparse straight-line chords and same-frame proxy differences; neither is a dense measured travel path or an error bound.",
        }
    result = {
        "status": "source_shoe_crops_pending_contact_review" if not CONTACTS else "analyst_sampled_floor_proposals",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "9",
        "source_sha256": sha256(SOURCE), "visual_candidate_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "sample_frames": FRAMES, "rows": rows,
        "sampled_diagnostics": sample_metrics,
        "sheets": [f"r1_p9_contact_check_sheet_{i}.jpg" for i in range(1, 4)],
        "limitation": "Eleven sampled, manually selected floor points are single-reviewer proposals, not independently validated contacts. The 40-frame spacing misses intervening steps, so their polygonal path is not full travel. Box-bottom differences on these frames do not bound error on every other frame or yield a confidence interval. No production metric is created.",
        "saved_review_modified": False, "official_annotations_changed": False,
    }
    (BASE / "r1_p9_contact_checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#9: {len(rows)} source crops, {len(CONTACTS)} marked contacts")


if __name__ == "__main__":
    main()
