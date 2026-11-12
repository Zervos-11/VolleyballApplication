"""Render source checks for the remaining blue #10/#11 raw-ID changes."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
GROUPS = {
    "p10_early": (21096, 21099, 21105, 21115, 21125, 21134),
    "p10_later": (21280, 21284, 21288, 21292, 21300, 21450),
    "p11_middle": (21185, 21188, 21200, 21235, 21245, 21250),
    "p11_later": (21265, 21299, 21316, 21416, 21419, 21450),
}
TRACKS = {"10": (6, 125, 455), "11": (4, 337, 367, 498, 751)}


def runs(frames):
    output = []
    for frame in frames:
        if not output or frame > output[-1][1]+1:
            output.append([frame, frame])
        else:
            output[-1][1] = frame
    return output


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    coverage = {}
    for player, ids in TRACKS.items():
        coverage[player] = {}
        for track in ids:
            frames = [frame for frame in range(21050, 21464)
                      if any(row["track_id"] == track for row in raw["frames"][str(frame)])]
            coverage[player][str(track)] = {"raw_box_frames": len(frames), "runs_inclusive": runs(frames)}

    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    for group, frames in GROUPS.items():
        tiles = []
        for frame in frames:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source frame {frame}")
            crop = image[430:950, 300:1800].copy()
            for row in raw["frames"][str(frame)]:
                track = row["track_id"]
                if track not in TRACKS["10"] + TRACKS["11"]:
                    continue
                x1, y1, x2, y2 = (int(v) for v in row["bbox"])
                color = (40, 200, 40) if track in TRACKS["10"] else (0, 165, 255)
                cv2.rectangle(crop, (x1-300, y1-430), (x2-300, y2-430), color, 3)
                cv2.putText(crop, f"T{track}", (x1-300, max(20, y1-438)),
                            cv2.FONT_HERSHEY_SIMPLEX, .75, color, 2)
            cv2.putText(crop, str(frame), (12, 38), cv2.FONT_HERSHEY_SIMPLEX,
                        1.1, (255, 255, 255), 3)
            tiles.append(cv2.resize(crop, (900, 312)))
        sheet = np.vstack([np.hstack(tiles[i:i+2]) for i in range(0, len(tiles), 2)])
        cv2.imwrite(str(BASE / f"r1_{group}_identity_sheet.jpg"), sheet)
    capture.release()
    result = {
        "status": "raw_id_run_and_source_sheet_review_not_validated_identity",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1",
        "candidate_frames_inclusive": [21050, 21463],
        "raw_track_coverage": coverage,
        "source_review_frames": {key: list(value) for key, value in GROUPS.items()},
        "source_sheets": [f"r1_{key}_identity_sheet.jpg" for key in GROUPS],
        "source_findings": {
            "10": "At sampled frames, blue #10 remains visually identifiable through the 21099-21132 raw-ID gap. T125 and T455 overlap on #10 around 21284 before T455 takes over. The full 34-frame gap has not been checked frame by frame.",
            "11": "T4 follows blue #11 early. T337 boxes #11 during the block near 21265, while concurrent T367 boxes neighboring blue #13; at 21300 T367 overlaps #11's saved box. T367 therefore cannot be assigned wholesale to #11 without a source-reviewed switch. T498 includes partial upper-body boxes; T751 later boxes #11 at sampled frames.",
        },
        "decision": "Sampled source sheets only; do not stitch all raw IDs or infer floor positions without a full source check. In particular, withhold T367 as a continuous #11 track.",
        "production_metric_changed": False,
    }
    (BASE / "r1_remaining_identity_audit.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print({player: {track: row["raw_box_frames"] for track, row in tracks.items()}
           for player, tracks in coverage.items()})


if __name__ == "__main__":
    main()
