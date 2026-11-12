"""Render the unreviewed S3 P34 source frames and provisional numbered boxes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
VIDEO = ROOT / "data/matches/yt_u5HnY2aNW14/source_720p.mp4"
OUT = SCREEN / "s3p34_remaining_rally_review"
ROSTER = ("28", "12", "15", "7", "19", "21")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    ledger_path = SCREEN / "s3p34_six_player_observation_ledger.json"
    screen_path = SCREEN / "source_bracketed_30fps_screen.json"
    coverage_path = SCREEN / "s3p34_whole_interval_coverage.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    raw = json.loads(screen_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert sha256(VIDEO) == ledger["source_sha256"] == raw["source_sha256"]
    assert coverage["inputs_sha256"]["observation_ledger"] == sha256(ledger_path)
    point = next(p for p in raw["points"] if (p["set"], p["point_number"]) == (3, 34))
    raw_by_frame = {r["source_frame"]: r for r in point["rows"]}
    ledger_by_frame = {r["source_frame"]: r for r in ledger["frames"]}
    remaining = [r["source_frame"] for r in coverage["frames"]
                 if r["source_state_reviewed_slots"] == 0]
    assert len(remaining) == 85
    OUT.mkdir(exist_ok=True)
    capture = cv2.VideoCapture(str(VIDEO))
    assert capture.isOpened()
    rows = []
    try:
        for number in remaining:
            capture.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, image = capture.read()
            if not ok or image.shape[:2] != (720, 1280):
                raise RuntimeError(f"Cannot decode source frame {number}")
            path = OUT / f"unboxed_{number}.jpg"
            if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 96]):
                raise RuntimeError(f"Cannot write {path}")
            proposals = raw_by_frame[number]["proposals"]
            used = set()
            boxes = {}
            for jersey in ROSTER:
                court = ledger_by_frame[number]["players"][jersey]["jersey_keyed_candidate_court_m"]
                if court is None:
                    boxes[jersey] = None
                    continue
                distances = sorted((sum((float(a)-float(b))**2 for a, b in zip(
                    p["box_bottom_court_m"], court)), index)
                    for index, p in enumerate(proposals) if index not in used)
                if not distances or distances[0][0] > 0.0002:
                    raise RuntimeError(f"Cannot link candidate box: frame {number}, slot {jersey}")
                index = distances[0][1]
                used.add(index)
                boxes[jersey] = {"bbox_px": proposals[index]["bbox_px"],
                                 "raw_track_id": proposals[index]["raw_track_id"],
                                 "candidate_court_m": court}
            rows.append({"source_frame": number, "image": path.name,
                         "image_sha256": sha256(path), "numbered_boxes": boxes})
    finally:
        capture.release()
    manifest = {"status": "review_packet_only_no_new_human_verdicts",
                "source_sha256": ledger["source_sha256"],
                "inputs_sha256": {"observation_ledger": sha256(ledger_path),
                                  "source_bracketed_30fps_screen": sha256(screen_path),
                                  "whole_interval_coverage": sha256(coverage_path)},
                "roster_slots_in_order": list(ROSTER),
                "description": "85 frames without individual source-state review in 36001-36138; source first, numbered candidate boxes second",
                "frames": rows}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(rows)} unboxed frames to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
