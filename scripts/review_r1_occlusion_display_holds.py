"""Render source crops around sampled r1 crossing display holds."""

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
HOLDS = BASE / "r1_occlusion_display_holds.json"
SAMPLES = [
    (21099, "10"), (21106, "10"),
    (21194, "11"), (21266, "11"), (21273, "11"), (21337, "11"),
    (21088, "12"), (21220, "12"), (21243, "12"), (21395, "12"),
    (21056, "13"), (21215, "13"), (21424, "13"), (21431, "13"),
]
SOURCE_STATES = {
    (21099, "10"): "target_visible_near_last_location_with_overlap",
    (21106, "10"): "target_visible_near_last_location_with_overlap",
    (21194, "11"): "target_visible_in_overlap_cluster",
    (21266, "11"): "target_in_cluster_location_uncertain",
    (21273, "11"): "target_in_cluster_location_uncertain",
    (21337, "11"): "target_in_cluster_location_uncertain",
    (21088, "12"): "target_visible_marker_on_foreground_player",
    (21220, "12"): "target_visible_marker_on_foreground_player",
    (21243, "12"): "target_visible_marker_on_foreground_player",
    (21395, "12"): "target_visible_marker_offset_from_target",
    (21056, "13"): "target_visible_near_last_location_with_overlap",
    (21215, "13"): "target_visible_near_last_location_with_overlap",
    (21424, "13"): "target_visible_moving_away_from_last_location",
    (21431, "13"): "target_visible_moving_away_from_last_location",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    holds = json.loads(HOLDS.read_text(encoding="utf-8"))
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    by_frame = {row["frame"]: row for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    rows = []
    try:
        for frame, player in SAMPLES:
            held = holds["holds"][str(frame)][player]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source frame {frame}")
            anchor = held["display_anchor_px"]
            x1 = max(0, min(image.shape[1] - 440, round(anchor[0] - 220)))
            y1 = max(0, min(image.shape[0] - 360, round(anchor[1] - 180)))
            crop = image[y1:y1+360, x1:x1+440].copy()
            for other in held["candidate_occluder_players"]:
                box = by_frame[frame]["players"][other]["bbox_px"]
                cv2.rectangle(crop, (round(box[0] - x1), round(box[1] - y1)),
                              (round(box[2] - x1), round(box[3] - y1)),
                              (0, 255, 255), 2)
            cv2.circle(crop, (round(anchor[0] - x1), round(anchor[1] - y1)),
                       16, (255, 0, 255), 3, cv2.LINE_AA)
            cv2.putText(crop, f"{frame} #{player} held {held['hold_age_frames']}f",
                        (8, 26), cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(crop, f"{frame} #{player} held {held['hold_age_frames']}f",
                        (8, 26), cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 0, 255), 2, cv2.LINE_AA)
            tiles.append(crop)
            rows.append({"frame": frame, "player": player,
                         "anchor_px": anchor,
                         "candidate_occluders": held["candidate_occluder_players"],
                         "hold_age_frames": held["hold_age_frames"],
                         "source_state": SOURCE_STATES[(frame, player)]})
    finally:
        cap.release()
    blank = np.full_like(tiles[0], 30)
    while len(tiles) % 6:
        tiles.append(blank)
    sheets = []
    for start in range(0, len(tiles), 6):
        name = f"r1_occlusion_hold_source_sheet_{start//6+1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(tiles[start:start+3]), cv2.hconcat(tiles[start+3:start+6])]))
        sheets.append(name)
    result = {
        "status": "sampled_source_hold_review_complete",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "hold_record_sha256": sha256(HOLDS),
        "samples": rows, "sheets": sheets,
        "legend": {"magenta_circle": "stale held image location, not observed player position",
                   "yellow_rectangle": "candidate overlapping player's current raw box"},
        "decision": "Overlap is useful as an identity review cue but does not establish a stationary current location. Several sampled markers lie on a foreground player while the target is visible elsewhere. Viewer wording must say last seen here, and no marker may enter movement metrics.",
    }
    (BASE / "r1_occlusion_hold_source_review.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(rows)} held samples on {len(sheets)} source sheets")


if __name__ == "__main__":
    main()
