"""Prepare two dense, proposal-free annotation windows from a separate recording."""

import hashlib
import json
from pathlib import Path

import cv2


MATCH = Path("data/matches/yt_em6zFUxfYpc")
VIDEO = MATCH / "heldout_source_cfr.mp4"
# The second clip begins at frame 482 of the combined source.
WINDOWS = {"cross_a": (243, 268), "cross_b": (754, 779)}


def write_if_new(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError(f"Refusing to overwrite existing data: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    try:
        fps = video.get(cv2.CAP_PROP_FPS)
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        if count < max(end for _, end in WINDOWS.values()):
            raise ValueError("Selected windows exceed the source video")
        for start, end in WINDOWS.values():
            for frame in (start, end - 1):
                video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, _ = video.read()
                if not ok:
                    raise ValueError(f"Cannot decode frame {frame}")
    finally:
        video.release()
    digest = hashlib.sha256()
    with VIDEO.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    sha = digest.hexdigest()
    source = {
        "match_id": MATCH.name,
        "source_group_id": "youtube_em6zFUxfYpc",
        "source_url": "https://www.youtube.com/watch?v=em6zFUxfYpc",
        "video_file": VIDEO.as_posix(), "sha256": sha,
        "camera": {"width": width, "height": height, "fps": fps},
        "frame_count": count, "duration_s": count / fps,
        "split": "heldout_tracking_evaluation",
        "annotation_status": "awaiting_manual_dense_labels",
    }
    write_if_new(MATCH / "source_record.json", source)
    selection = {
        "match_id": MATCH.name, "dataset_stage": "heldout_tracking_evaluation",
        "split": "heldout", "source_sha256": sha,
        "design": "Two visually selected consecutive-frame windows in the same match; no detector proposals shown to annotator.",
        "rallies": [],
    }
    for name, (start, end) in WINDOWS.items():
        selection["rallies"].append({
            "rally_id": name, "start_frame": start, "end_frame_exclusive": end,
            "window_start_frame": start, "window_end_frame_exclusive": end,
            "target_half": "near_camera", "target_team": "blue team on the near court",
            "boundary_status": "codex_visual_selection",
            "notes": "Evaluation subwindow, not a complete rally. Label all six near-court players on every frame, including fully occluded players with no box.",
        })
    write_if_new(MATCH / "pilot/selection.json", selection)
    for name, (start, end) in WINDOWS.items():
        draft = {
            "match_id": MATCH.name, "rally_id": name,
            "start_frame": start, "end_frame_exclusive": end,
            "boundary_status": "codex_visual_selection",
            "source_sha256": sha, "fps": fps,
            "annotation_mode": "independent_manual_no_detector_proposals",
            "frames": [{"frame_index": frame, "time_s": round(frame / fps, 6),
                        "proposals": []} for frame in range(start, end)],
        }
        write_if_new(MATCH / "pilot/player_drafts" / f"{name}.json", draft)
    manifest = {
        "match_id": MATCH.name, "source_video": VIDEO.as_posix(),
        "source_sha256": sha, "fps": fps, "frame_size": [width, height],
        "windows": [{"name": name, "first_frame": start,
                     "last_frame": end - 1, "frame_count": end - start}
                    for name, (start, end) in WINDOWS.items()],
        "target_players": 6, "total_target_player_frames":
        6 * sum(end - start for start, end in WINDOWS.values()),
        "ground_truth_status": "not_annotated",
        "tracker_configuration_frozen": "yolov8n.pt + bytetrack.yaml, conf=0.20, imgsz=960; fresh tracker state for each window, warmed up on the preceding 25 frames",
    }
    write_if_new(MATCH / "pilot/heldout_tracking_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
