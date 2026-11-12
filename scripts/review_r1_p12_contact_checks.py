"""Inspect source floor-contact opportunities for blue #12 across r1 gaps."""

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
FRAMES = [21070, 21100, 21150, 21200, 21212, 21220, 21236, 21250,
          21300, 21308, 21311, 21350, 21400, 21450, 21463]
# Source crop location only. Missing detector boxes remain missing.
CROP_FALLBACK = {21220: [1290, 600, 1380, 780], 21311: [1190, 580, 1290, 770]}
CONTACTS = {
    21070: ([1305.0, 757.5], "two_sole_floor_midpoint_near_net"),
    21100: (None, "uncertain_sole_assignment_behind_9"),
    21150: ([1382.5, 758.5], "two_sole_floor_midpoint_near_net"),
    21200: ([1354.5, 756.5], "one_visible_planted_shoe_near_net"),
    21212: (None, "uncertain_contact_near_net"),
    21220: (None, "uncertain_fast_motion_box_missing"),
    21236: ([1238.0, 766.5], "one_visible_planted_shoe"),
    21250: ([1207.0, 777.0], "two_sole_floor_midpoint"),
    21300: (None, "uncertain_approach_foot_blur"),
    21308: (None, "uncertain_approach_foot_blur"),
    21311: (None, "uncertain_approach_box_missing"),
    21350: ([1320.0, 816.0], "one_visible_planted_shoe"),
    21400: ([1526.0, 847.5], "one_visible_planted_shoe"),
    21450: (None, "uncertain_moving_sole_blur"),
    21463: ([1319.5, 795.5], "two_sole_floor_midpoint"),
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
    candidates = {row["frame"]: row["players"]["12"] for row in visual["frame_records"]}
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    try:
        for frame in FRAMES:
            candidate = candidates[frame]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode source frame {frame}")
            box = candidate["bbox_px"] or CROP_FALLBACK.get(frame)
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
            point = marked[0] if marked and marked[0] is not None else None
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
                         "contact_px": point,
                         "contact_state": marked[1] if marked else "pending_visual_review",
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
        cv2.imwrite(str(BASE / f"r1_p12_contact_check_sheet_{index // 4 + 1}.jpg"), cv2.hconcat(group))
    grounded = [row for row in rows if row["court_m_diagnostic"] is not None]
    uncertain = [row for row in rows if row["court_m_diagnostic"] is None]
    offsets = [row["floor_vs_box_bottom_m_diagnostic"] for row in grounded
               if row["floor_vs_box_bottom_m_diagnostic"] is not None]
    summary = {
        "grounded_point_count": len(grounded),
        "uncertain_state_count": len(uncertain),
        "uncertain_frames": [row["frame_index"] for row in uncertain],
        "missing_box_uncertain_frames": [row["frame_index"] for row in uncertain
                                         if row["candidate_box_status"] != "raw_box_candidate"],
        "near_net_0_25m_grounded_frames": [row["frame_index"] for row in grounded
                                          if 8.75 <= row["court_m_diagnostic"][1] <= 9.25],
        "floor_vs_valid_box_bottom_median_m": round(float(np.median(offsets)), 3) if offsets else None,
        "floor_vs_valid_box_bottom_max_m": round(float(max(offsets)), 3) if offsets else None,
        "physical_distance_status": "withheld_due_to_uncertain_contacts_and_detector_gaps",
    }
    result = {
        "status": "source_contact_review_in_progress" if not CONTACTS else "analyst_sampled_floor_and_unknown_states",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "12",
        "source_sha256": sha256(SOURCE), "visual_candidate_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "sample_frames": FRAMES, "rows": rows, "sampled_diagnostics": summary,
        "sheets": [f"r1_p12_contact_check_sheet_{i}.jpg" for i in range(1, 5)],
        "limitation": "Missing detector boxes remain missing; fallback coordinates locate source crops only. Fast approach, overlap, blur, and near-net pixel sensitivity leave explicit uncertain states. Grounded shoe points are single-reviewer proposals, not official labels or a continuous validated path.",
        "saved_review_modified": False, "official_annotations_changed": False,
    }
    (BASE / "r1_p12_contact_checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#12: {len(rows)} source crops, {len(CONTACTS)} reviewed states")


if __name__ == "__main__":
    main()
