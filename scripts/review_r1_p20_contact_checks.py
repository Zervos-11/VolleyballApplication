"""Inspect source shoe states for yellow #20 across r1, including truncated boxes."""

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
FRAMES = [21100, 21140, 21180, 21220, 21260, 21300, 21308,
          21310, 21313, 21340, 21380, 21420, 21463]
CONTACTS = {
    # Approximate source-pixel floor points from the enlarged crop sheets.
    # 21310 has a visible planted shoe but no valid detector box.
    21100: ([786.0, 801.0], "two_sole_floor_midpoint"),
    21140: ([739.5, 806.5], "one_visible_planted_shoe"),
    21180: ([818.5, 800.0], "two_sole_floor_midpoint"),
    21220: ([823.0, 798.5], "two_sole_floor_midpoint"),
    21260: ([760.5, 792.5], "two_sole_floor_midpoint"),
    21300: ([752.5, 812.5], "one_visible_planted_shoe"),
    21308: ([754.0, 812.0], "one_visible_planted_shoe"),
    21310: ([744.0, 815.5], "one_visible_planted_shoe_box_invalid"),
    21313: ([749.0, 814.5], "one_visible_planted_shoe"),
    21340: ([645.0, 818.0], "two_sole_floor_midpoint"),
    21380: ([613.0, 828.5], "one_visible_planted_shoe"),
    21420: ([644.0, 805.5], "one_visible_planted_shoe"),
    21463: ([706.0, 786.25], "two_sole_floor_midpoint"),
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
    boxes = {row["frame"]: row["players"]["20"] for row in visual["frame_records"]}
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    try:
        for frame in FRAMES:
            candidate = boxes[frame]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode source frame {frame}")
            box = candidate["bbox_px"]
            if box is None and frame == 21310:
                # The detector truncates at 21309–21312. Use a source crop
                # location only, between the valid boxes at 21308 and 21313.
                box = [685, 600, 773, 820]
            if box is None:
                raise ValueError(f"No source crop location at {frame}")
            x1, _, x2, y2 = box
            left = max(0, min(image.shape[1] - 200, round((x1 + x2) / 2) - 100))
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
            box_court = None
            discrepancy = None
            if candidate["box_status"] == "raw_box_candidate":
                bx1, _, bx2, by2 = candidate["bbox_px"]
                box_court = cv2.perspectiveTransform(
                    np.float32([[[(bx1 + bx2) / 2, by2]]]), matrix)[0, 0]
                if court is not None:
                    discrepancy = float(np.linalg.norm(court - box_court))
            tiles.append(tile)
            rows.append({"frame_index": frame, "crop_source_xyxy": [left, top, left + 200, top + 140],
                         "candidate_box_status": candidate["box_status"],
                         "contact_px": point, "contact_state": marked[1] if marked else "pending_visual_review",
                         "court_m_diagnostic": [round(float(v), 3) for v in court] if court is not None else None,
                         "box_bottom_court_m_diagnostic":
                         [round(float(v), 3) for v in box_court] if box_court is not None else None,
                         "floor_vs_box_bottom_m_diagnostic": round(discrepancy, 3) if discrepancy is not None else None})
    finally:
        cap.release()
    for index in range(0, len(tiles), 4):
        group = tiles[index:index + 4]
        while len(group) < 4:
            group.append(np.full_like(group[0], 32))
        cv2.imwrite(str(BASE / f"r1_p20_contact_check_sheet_{index // 4 + 1}.jpg"), cv2.hconcat(group))
    reviewed = [row for row in rows if row["court_m_diagnostic"] is not None]
    sample_metrics = None
    if len(reviewed) >= 2:
        contacts = np.asarray([row["court_m_diagnostic"] for row in reviewed], dtype=float)
        offsets = [row["floor_vs_box_bottom_m_diagnostic"] for row in reviewed
                   if row["floor_vs_box_bottom_m_diagnostic"] is not None]
        sample_metrics = {
            "reviewed_grounded_frames": len(reviewed),
            "invalid_box_frames_with_visible_contact": [row["frame_index"] for row in reviewed
                                                       if row["candidate_box_status"] != "raw_box_candidate"],
            "sampled_contact_polyline_m": round(float(np.linalg.norm(np.diff(contacts, axis=0), axis=1).sum()), 3),
            "first_to_last_contact_displacement_m": round(float(np.linalg.norm(contacts[-1] - contacts[0])), 3),
            "valid_box_comparison_count": len(offsets),
            "floor_vs_valid_box_bottom_median_m": round(float(np.median(offsets)), 3) if offsets else None,
            "floor_vs_valid_box_bottom_max_m": round(float(max(offsets)), 3) if offsets else None,
            "inside_nominal_near_court_count": int(np.logical_and.reduce(
                (contacts[:, 0] >= 0, contacts[:, 0] <= 9,
                 contacts[:, 1] >= 0, contacts[:, 1] <= 9)).sum()),
            "interpretation": "Sparse source-selected floor points; step sum can reflect shoe switching and misses movement between samples. No full physical travel claim.",
        }
    result = {
        "status": "source_shoe_crops_pending_contact_review" if not CONTACTS else "analyst_sampled_floor_proposals",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "20",
        "source_sha256": sha256(SOURCE), "visual_candidate_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "sample_frames": FRAMES, "rows": rows, "sampled_diagnostics": sample_metrics,
        "sheets": [f"r1_p20_contact_check_sheet_{i}.jpg" for i in range(1, 5)],
        "limitation": "Source crop at frame 21310 uses a location inferred from adjacent valid boxes, not a repaired detector box. All sample contacts remain analyst proposals. Alternating a single planted shoe and two-shoe midpoints can inflate the sampled chord path; 40-frame gaps can miss turns. No dense physical travel or production metric is created.",
        "saved_review_modified": False, "official_annotations_changed": False,
    }
    (BASE / "r1_p20_contact_checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#20: {len(rows)} source crops, {len(CONTACTS)} marked contacts")


if __name__ == "__main__":
    main()
