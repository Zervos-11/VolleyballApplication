"""Inspect blue #10 through the 34-frame r1 detector gap in source video."""

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
FRAMES = [21098, 21100, 21116, 21132, 21133]
CROP = [1100, 560, 1420, 880]
CONTACTS = {
    # One visible planted pink shoe on blue #10. These are analyst proposals,
    # not saved user annotations or a two-foot body-centre estimate.
    21098: ([1228, 816], "visible_left_shoe_floor_contact"),
    21100: ([1231, 816], "visible_left_shoe_floor_contact"),
    21116: (None, "left_shoe_partly_occluded_by_blue_9"),
    21132: ([1220, 816], "partly_visible_left_shoe_contact_proposal"),
    21133: ([1220, 816], "partly_visible_left_shoe_contact_proposal"),
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
    players = {row["frame"]: row["players"]["10"] for row in visual["frame_records"]}
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    cap = cv2.VideoCapture(str(SOURCE))
    tiles, rows = [], []
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode source frame {frame}")
            x1, y1, x2, y2 = CROP
            tile = cv2.resize(image[y1:y2, x1:x2], (480, 480), interpolation=cv2.INTER_LINEAR)
            cv2.putText(tile, str(frame), (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                        .95, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(tile, str(frame), (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                        .95, (0, 255, 255), 2, cv2.LINE_AA)
            marked = CONTACTS.get(frame)
            point = marked[0] if marked and marked[0] is not None else None
            court = None
            if point is not None:
                if not (x1 <= point[0] < x2 and y1 <= point[1] < y2):
                    raise ValueError(f"Floor point outside crop at {frame}")
                court = cv2.perspectiveTransform(np.float32([[point]]), matrix)[0, 0]
                cv2.drawMarker(tile, (round((point[0] - x1) * 1.5), round((point[1] - y1) * 1.5)),
                               (0, 255, 255), cv2.MARKER_CROSS, 20, 2, cv2.LINE_AA)
            tiles.append(tile)
            rows.append({"frame_index": frame, "candidate_box_status": players[frame]["box_status"],
                         "raw_track_id": players[frame]["raw_track_id"],
                         "contact_px": point,
                         "source_state": marked[1] if marked else "pending_source_review",
                         "court_m_diagnostic": [round(float(v), 3) for v in court] if court is not None else None})
    finally:
        cap.release()
    endpoint_rows = (rows[0], rows[-1])
    endpoint_court = [row["court_m_diagnostic"] for row in endpoint_rows]
    if any(point is None for point in endpoint_court):
        raise AssertionError("Both source endpoints must have floor contacts")
    endpoint_displacement = float(np.linalg.norm(np.subtract(*endpoint_court)))
    tiles.append(np.full_like(tiles[0], 32))
    cv2.imwrite(str(BASE / "r1_p10_gap_source_sheet.jpg"), cv2.vconcat(
        [cv2.hconcat(tiles[:3]), cv2.hconcat(tiles[3:])]))
    result = {
        "status": "source_gap_review_in_progress" if not CONTACTS else "sampled_source_gap_review",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "10",
        "source_sha256": sha256(SOURCE), "visual_candidate_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "detector_gap_frames_inclusive": [21099, 21132],
        "gap_duration_s": 34 / 50,
        "source_endpoint_frames": [21098, 21133],
        "source_endpoint_displacement_m_approx": round(endpoint_displacement, 2),
        "endpoint_interpretation": "About 0.1 m net displacement of the selected left-shoe pixels under staged calibration; the ending shoe is partly occluded by #9. This is neither travel distance through the gap nor a body-centre trajectory.",
        "source_crop_xyxy": CROP, "rows": rows,
        "source_sheet": "r1_p10_gap_source_sheet.jpg",
        "limitation": "Source samples support the same blue #10 identity and a mostly stationary stance. The #9 foreground player partly occludes #10's left shoe at 21116 and the ending endpoint. Missing detector boxes remain missing and the movement path inside the gap is not observed.",
        "official_annotations_changed": False, "production_metric_changed": False,
    }
    (BASE / "r1_p10_gap_source_review.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#10 gap: {len(FRAMES)} source frames, {len(CONTACTS)} reviewed states")


if __name__ == "__main__":
    main()
