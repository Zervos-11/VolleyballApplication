"""Freeze sampled source evidence for the continuous #9 proxy path."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
ANCHOR = BASE / "r1_anchor_path_estimate.json"
FRAMES = [21064, 21070, 21100, 21200, 21300, 21400, 21450, 21463]
NOTES = {
    21064: "At least one white shoe appears planted after the serve.",
    21070: "Right white shoe is planted while the other foot is moving.",
    21100: "White sole-floor contact remains visible behind #10.",
    21200: "Both white shoes appear planted in a defensive stance.",
    21300: "At least one white shoe appears planted during the turn.",
    21400: "Both white shoes appear planted.",
    21450: "Both white shoes appear planted.",
    21463: "At least one white shoe appears planted during the lunge.",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    if visual["rally_id"] != "r1" or anchor["player_9"]["track_id"] != 3:
        raise ValueError("Unexpected r1 candidate or #9 track")
    boxes = {row["frame"]: row["players"]["9"] for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    observations = []
    try:
        for frame in FRAMES:
            candidate = boxes[frame]
            if candidate["box_status"] != "raw_box_candidate" or not candidate["bbox_px"]:
                raise ValueError(f"No candidate #9 box at {frame}")
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Cannot decode source frame {frame}")
            x1, y1, x2, y2 = candidate["bbox_px"]
            xa, xb = max(0, int(x1) - 35), min(image.shape[1], int(x2) + 35)
            ya, yb = max(0, int(y1) - 25), min(image.shape[0], int(y2) + 35)
            tile = cv2.resize(image[ya:yb, xa:xb], (300, 440), interpolation=cv2.INTER_LINEAR)
            cv2.putText(tile, str(frame), (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(tile, str(frame), (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
            observations.append({"frame_index": frame,
                                 "state": "at_least_one_visible_planted_shoe_source_sample",
                                 "source_observation": NOTES[frame],
                                 "candidate_box_px": candidate["bbox_px"]})
    finally:
        cap.release()
    sheet = cv2.vconcat([cv2.hconcat(tiles[i:i + 4]) for i in (0, 4)])
    cv2.imwrite(str(BASE / "r1_p9_floor_anchor_review_sheet.jpg"), sheet)
    result = {
        "status": "sampled_source_grounded_screen_not_dense_contact_labels",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "9",
        "source_video_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "anchor_path_sha256": sha256(ANCHOR),
        "observations": observations,
        "source_sheet": "r1_p9_floor_anchor_review_sheet.jpg",
        "existing_box_bottom_proxy_diagnostic": {
            "frames_inclusive": anchor["player_9"]["source_frames_inclusive"],
            "median_15_frame_path_m": anchor["player_9"]["rough_smoothed_box_bottom_path_m"],
            "median_5_to_31_frame_method_range_m": [
                anchor["player_9"]["method_sensitivity_median_width_frames_to_path_m"]["31"],
                anchor["player_9"]["method_sensitivity_median_width_frames_to_path_m"]["5"]],
        },
        "limitation": "Eight sampled grounded-looking source frames do not certify the other 386 frames of the raw track. No floor-level midpoint pixels were marked for these samples. The existing smoothed box-bottom path is a method-sensitive development proxy, not validated physical travel or a confidence interval.",
        "official_annotations_changed": False,
        "production_metric_changed": False,
    }
    (BASE / "r1_p9_grounded_sample_review.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"#9: {len(FRAMES)} source grounded samples; proxy path still provisional")


if __name__ == "__main__":
    main()
