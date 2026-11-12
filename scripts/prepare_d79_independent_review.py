"""Prepare a source-only, unassisted evaluation slice from D79JrsJsFgs.

The 20-second excerpt begins at approximately 20:20 in the original YouTube
match. Its 50-frame dense window is 20:24.000–20:24.817, relative to the
original, and source frames 240–289 relative to the excerpt.
"""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_D79JrsJsFgs"
VIDEO = MATCH / "screening/screen_20m20.mp4"
SOURCE_URL = "https://www.youtube.com/watch?v=D79JrsJsFgs"
RALLY_ID = "in_play_20m24"
FIRST, LAST = 240, 289


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to replace existing review setup: {path}")
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if not VIDEO.is_file():
        raise FileNotFoundError(VIDEO)
    cap = cv2.VideoCapture(str(VIDEO))
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, LAST)
        readable, _ = cap.read()
    finally:
        cap.release()
    if (width, height, fps, count, readable) != (1280, 720, 60.0, 1200, True):
        raise ValueError(f"Unexpected excerpt properties: {width}x{height}, {fps} fps, {count} frames, last readable={readable}")
    source_hash = sha256(VIDEO)
    source = {
        "match_id": "yt_D79JrsJsFgs",
        "source_group_id": "youtube_D79JrsJsFgs",
        "source_url": SOURCE_URL,
        "source_title": "Premier League Mens | Game 2 | SUV X WSV vs NOVA | 19/04/26",
        "video_file": VIDEO.relative_to(ROOT).as_posix(),
        "sha256": source_hash,
        "camera": {"width": width, "height": height, "fps": fps},
        "frame_count": count,
        "duration_s": count / fps,
        "source_excerpt": {
            "original_start_time_s_approx": 1220.0,
            "original_end_time_s_approx": 1240.0,
            "original_url": SOURCE_URL,
            "video_only": True,
            "reencoded_from_youtube_720p60_hls": True,
        },
        "split": "new_video_independent_manual_evaluation",
        "rights_status": "pending",
        "privacy_review_status": "pending",
        "annotation_status": "not_started",
    }
    rally = {
        "rally_id": RALLY_ID,
        "start_frame": 180,
        "end_frame_exclusive": 480,
        "window_start_frame": 0,
        "window_end_frame_exclusive": count,
        "target_half": "near_camera",
        "target_team": "white jerseys on near court",
        "boundary_status": "source_only_visual_bracket_unverified",
        "notes": "Source-only screening shows an in-play exchange. The 50-frame evaluation slice is inside active play; exact serve and dead-ball boundaries are not claimed.",
    }
    selection = {
        "match_id": source["match_id"],
        "dataset_stage": "new_video_independent_manual_evaluation",
        "split": "heldout_new_video",
        "source_sha256": source_hash,
        "raw_prediction_sha256": None,
        "design": "Video supplied by user; 50 consecutive source frames selected visually before detector inference or labels. No detector proposals are prepared or shown.",
        "rallies": [rally],
        "dense_review_window": {"first_frame": FIRST, "last_frame": LAST, "target_players": 6, "status": "not_annotated"},
    }
    draft = {
        "match_id": source["match_id"],
        "rally_id": RALLY_ID,
        "start_frame": rally["start_frame"],
        "end_frame_exclusive": rally["end_frame_exclusive"],
        "boundary_status": rally["boundary_status"],
        "source_sha256": source_hash,
        "fps": fps,
        "annotation_mode": "independent_manual_no_detector_proposals",
        "frames": [
            {"frame_index": frame, "time_s": round(frame / fps, 6), "proposals": []}
            for frame in range(rally["start_frame"], rally["end_frame_exclusive"])
        ],
    }
    write_once(MATCH / "source_record.json", source)
    write_once(MATCH / "pilot/selection.json", selection)
    write_once(MATCH / f"pilot/player_drafts/{RALLY_ID}.json", draft)
    print(f"Prepared {source['match_id']} frames {FIRST}–{LAST}; source SHA-256 {source_hash}")


if __name__ == "__main__":
    main()
