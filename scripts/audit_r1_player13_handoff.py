"""Inspect later r1 #13 detector handoff without inferring ground travel."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
FRAMES = (21336, 21340, 21342, 21345, 21350, 21353, 21354, 21360, 21400)
TRACKS = (563, 625)


def runs(numbers):
    if not numbers:
        return []
    result = []
    start = last = numbers[0]
    for number in numbers[1:]:
        if number > last + 1:
            result.append([start, last])
            start = number
        last = number
    result.append([start, last])
    return result


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    all_frames = list(range(21316, 21424))
    coverage = {str(track): [frame for frame in all_frames
                             if any(box["track_id"] == track
                                    for box in raw["frames"][str(frame)])]
                for track in TRACKS}
    union = sorted(set(coverage["563"]) | set(coverage["625"]))

    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    tiles = []
    for frame in FRAMES:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode source frame {frame}")
        # Cropping stays fixed so nearby players and relative positions are visible.
        crop = image[400:900, 300:1050].copy()
        for row in raw["frames"][str(frame)]:
            track = row["track_id"]
            if track not in (22, *TRACKS):
                continue
            x1, y1, x2, y2 = (int(v) for v in row["bbox"])
            color = {22: (210, 0, 210), 563: (0, 180, 0), 625: (0, 165, 255)}[track]
            cv2.rectangle(crop, (x1-300, y1-400), (x2-300, y2-400), color, 3)
            cv2.putText(crop, f"T{track}", (x1-300, max(20, y1-410)),
                        cv2.FONT_HERSHEY_SIMPLEX, .75, color, 2)
        cv2.putText(crop, str(frame), (12, 34), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255, 255, 255), 3)
        tiles.append(cv2.resize(crop, (600, 400)))
    capture.release()
    sheet = np.vstack([np.hstack(tiles[i:i+3]) for i in range(0, len(tiles), 3)])
    cv2.imwrite(str(BASE / "r1_player13_late_handoff_sheet.jpg"), sheet)

    record = {
        "status": "development_source_review_not_validated_track",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "13",
        "review_interval_inclusive": [all_frames[0], all_frames[-1]],
        "raw_track_runs": {track: runs(frames) for track, frames in coverage.items()},
        "union_coverage_frames": len(union),
        "union_missing_runs": runs(sorted(set(all_frames)-set(union))),
        "duplicate_detection_frames": sorted(set(coverage["563"]) & set(coverage["625"])),
        "source_review_frames": list(FRAMES),
        "source_sheet": "r1_player13_late_handoff_sheet.jpg",
        "source_observation": "In nine sampled source frames, blue #13 moves left of yellow #20. T563 and T625 both box her at 21340; T625 then covers her until 21353 and T563 resumes at 21354. This supports a local identity handoff, not an independently verified floor path.",
        "decision": "Candidate image identity continuity over 21316-21423 only; do not bridge earlier or later gaps or infer distance from box bottoms.",
        "production_metric_changed": False, "official_annotations_changed": False,
    }
    (BASE / "r1_player13_handoff_audit.json").write_text(
        json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print({"union_coverage_frames": len(union),
           "missing": record["union_missing_runs"],
           "duplicates": len(record["duplicate_detection_frames"])})


if __name__ == "__main__":
    main()
