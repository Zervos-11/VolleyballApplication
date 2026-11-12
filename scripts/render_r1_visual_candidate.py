"""Render a bounded six-slot r1 visual diagnostic from frozen raw tracks.

Identity links are source-sampled development candidates. Missing detections
remain null, and no box bottom is converted to a floor position or metric.
"""

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
START, END = 21050, 21464
FPS = 50.0
SIZE = (1280, 720)
REVIEW_FRAMES = (21050, 21100, 21265, 21310, 21340, 21450)
ROSTER = ("9", "10", "11", "12", "13", "20")
COLORS = {"9": (30, 190, 45), "10": (190, 190, 30),
          "11": (0, 160, 255), "12": (200, 70, 180),
          "13": (50, 80, 220), "20": (20, 220, 220)}


def scoped_track(player, frame):
    if player == "9":
        return 3
    if player == "20":
        return 22
    if player == "12":
        return (8 if frame <= 21087 else
                72 if 21099 <= frame <= 21212 else
                338 if frame >= 21236 else None)
    if player == "13":
        return (16 if 21050 <= frame <= 21055 else
                218 if 21183 <= frame <= 21212 else
                563 if 21316 <= frame <= 21340 or 21354 <= frame <= 21423 else
                625 if 21341 <= frame <= 21353 else None)
    if player == "10":
        return (6 if frame <= 21098 else
                125 if 21133 <= frame <= 21284 or 21287 <= frame <= 21291 else
                455 if frame >= 21284 else None)
    if player == "11":
        return (4 if frame <= 21188 else
                337 if 21236 <= frame <= 21265 else
                367 if 21299 <= frame <= 21316 else
                498 if 21317 <= frame <= 21416 else
                751 if frame >= 21419 else None)
    raise ValueError(player)


def draw_label(image, label, x, y, color):
    cv2.putText(image, label, (x, max(25, y-7)), cv2.FONT_HERSHEY_SIMPLEX,
                .75, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(image, label, (x, max(25, y-7)), cv2.FONT_HERSHEY_SIMPLEX,
                .75, color, 2, cv2.LINE_AA)


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if (raw["start_frame"], raw["end_frame_exclusive"]) != (START, END):
        raise RuntimeError("Frozen raw tracking interval changed")
    capture = cv2.VideoCapture(str(VIDEO))
    capture.set(cv2.CAP_PROP_POS_FRAMES, START)
    raw_preview = BASE / "r1_visual_candidate_preview_raw.mp4"
    browser_preview = BASE / "r1_visual_candidate_preview.mp4"
    writer = cv2.VideoWriter(str(raw_preview),
                             cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)
    if not capture.isOpened() or not writer.isOpened():
        raise RuntimeError("Could not open source or preview writer")

    slot_counts = {player: {"raw_box_candidate": 0, "invalid_truncated": 0,
                            "missing": 0} for player in ROSTER}
    frames = []
    review_tiles = []
    for frame in range(START, END):
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode source frame {frame}")
        rows = raw["frames"][str(frame)]
        by_id = {row["track_id"]: row for row in rows}
        slots = {}
        missing = []
        for player in ROSTER:
            track = scoped_track(player, frame)
            row = by_id.get(track) if track is not None else None
            status = ("invalid_truncated" if player == "20" and 21309 <= frame <= 21312 else
                      "raw_box_candidate" if row is not None else "missing")
            if status == "invalid_truncated" and row is None:
                raise RuntimeError(f"Expected truncated #20 box at frame {frame}")
            slot_counts[player][status] += 1
            slots[player] = {"raw_track_id": track if row is not None else None,
                             "bbox_px": row["bbox"] if status == "raw_box_candidate" else None,
                             "box_status": status, "court_position_m": None}
            if status == "raw_box_candidate":
                x1, y1, x2, y2 = (int(v) for v in row["bbox"])
                cv2.rectangle(image, (x1, y1), (x2, y2), COLORS[player], 3)
                draw_label(image, f"#{player}? T{track}", x1, y1, COLORS[player])
            else:
                missing.append(player)
        frames.append({"frame": frame, "players": slots})
        cv2.rectangle(image, (0, 0), (1180, 45), (0, 0, 0), -1)
        cv2.putText(image,
                    f"R1 DEVELOPMENT PREVIEW   frame {frame}   +{(frame-START)/FPS:.2f}s",
                    (15, 31), cv2.FONT_HERSHEY_SIMPLEX, .85,
                    (255, 255, 255), 2, cv2.LINE_AA)
        cv2.rectangle(image, (0, 1040), (1920, 1080), (0, 0, 0), -1)
        cv2.putText(image, "Candidate IDs only | no verified floor positions",
                    (15, 1068), cv2.FONT_HERSHEY_SIMPLEX, .8,
                    (255, 255, 255), 2, cv2.LINE_AA)
        if missing:
            cv2.putText(image, "No usable box: " + ", ".join("#"+p for p in missing),
                        (1000, 1068), cv2.FONT_HERSHEY_SIMPLEX, .7,
                        (255, 255, 255), 2, cv2.LINE_AA)
        output = cv2.resize(image, SIZE, interpolation=cv2.INTER_AREA)
        writer.write(output)
        if frame in REVIEW_FRAMES:
            review_tiles.append(cv2.resize(output, (640, 360)))

    capture.release()
    writer.release()
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode a browser-playable H.264 preview")
    try:
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw_preview),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(browser_preview)],
            check=True,
        )
    finally:
        raw_preview.unlink(missing_ok=True)
    if len(review_tiles) != len(REVIEW_FRAMES):
        raise RuntimeError("Could not render all review frames")
    cv2.imwrite(str(BASE / "r1_visual_candidate_review_sheet.jpg"),
                np.vstack([np.hstack(review_tiles[i:i+3]) for i in (0, 3)]))
    result = {
        "status": "development_six_slot_visual_candidate_not_validated_tracking",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1",
        "source_frames_inclusive": [START, END-1],
        "fps_nominal": FPS, "output_size_px": list(SIZE),
        "source_raw_tracks": str(RAW.relative_to(ROOT)).replace("\\", "/"),
        "preview": "r1_visual_candidate_preview.mp4",
        "review_sheet": "r1_visual_candidate_review_sheet.jpg",
        "review_frames": list(REVIEW_FRAMES),
        "slot_counts": slot_counts,
        "frame_records": frames,
        "identity_policy": [
            "All colored boxes are development candidates; question marks are intentional.",
            "Raw ID 8 is used for #12 only through frame 21087 because later reuse is ambiguous.",
            "Raw ID 367 is not used for #11 before frame 21299 because it boxes #13 near frame 21265.",
            "Duplicate candidate boxes are suppressed; one player slot appears at most once per frame.",
            "Four truncated #20 boxes remain invalid and are not drawn as usable boxes.",
            "Missing boxes and all court positions remain null; no interpolation is displayed."
        ],
        "production_metric_changed": False, "official_annotations_changed": False,
    }
    (BASE / "r1_six_slot_visual_candidate.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(slot_counts)


if __name__ == "__main__":
    main()
