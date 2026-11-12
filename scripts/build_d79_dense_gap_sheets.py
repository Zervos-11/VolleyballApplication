"""Render every unreviewed missing D79 player frame for source visibility audit."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/d79_new_source"
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
AUDIT = BASE / "named_gap_visibility_audit.json"
NAMED = BASE / "named_near_boxes_80_336.json"
OUT = BASE / "named_gap_review/dense_visibility"


def main():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    named = json.loads(NAMED.read_text(encoding="utf-8"))
    if audit["named_output_sha256"] != hashlib.sha256(NAMED.read_bytes()).hexdigest():
        raise ValueError("Visibility audit is stale")
    if hashlib.sha256(VIDEO.read_bytes()).hexdigest() != "ab65b96312a7b13a888a913995ef2201ff565b76b521bb0ef7a71d7f4cf72731":
        raise ValueError("Unexpected source video")
    OUT.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(VIDEO))
    manifest = []
    try:
        for run in audit["runs"]:
            pid = run["player_id"]
            first, last = run["frames_inclusive"]
            frames = [s["frame"] for s in audit["missing_slots"]
                      if s["player_id"] == pid and first <= s["frame"] <= last
                      and s["status"] in {"unreviewed_visibility_unknown", "source_visible_no_accepted_box",
                                           "source_not_distinct_no_accepted_box"}]
            for index in range(0, len(frames), 12):
                batch = frames[index:index + 12]
                tiles = []
                for frame in batch:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
                    ok, image = capture.read()
                    if not ok:
                        raise RuntimeError(f"Cannot decode frame {frame}")
                    for other, slot in named["frames"][str(frame)].items():
                        if slot["bbox"] is None:
                            continue
                        x1, y1, x2, y2 = map(int, slot["bbox"])
                        cv2.rectangle(image, (x1, y1), (x2, y2), (40, 220, 40), 1)
                        cv2.putText(image, f"{other}", (x1, max(20, y1 - 4)),
                                    cv2.FONT_HERSHEY_SIMPLEX, .55, (40, 220, 40), 2)
                    crop = image[150:600, 350:1050].copy()
                    cv2.rectangle(crop, (0, 0), (220, 34), (0, 0, 0), -1)
                    cv2.putText(crop, f"#{pid} frame {frame}", (7, 25),
                                cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
                    tiles.append(crop)
                blank = np.zeros((450, 700, 3), dtype=np.uint8)
                while len(tiles) < 12:
                    tiles.append(blank)
                sheet = cv2.vconcat([cv2.hconcat(tiles[row:row + 3]) for row in range(0, 12, 3)])
                filename = f"p{pid}_{first}_{last}_{index // 12 + 1:02}.jpg"
                if not cv2.imwrite(str(OUT / filename), sheet):
                    raise RuntimeError(f"Could not write {filename}")
                manifest.append({"player_id": pid, "run": [first, last], "frames": batch, "sheet": filename})
    finally:
        capture.release()
    (OUT / "manifest.json").write_text(json.dumps({"video_sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
                                                   "named_output_sha256": hashlib.sha256(NAMED.read_bytes()).hexdigest(),
                                                   "sheets": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(manifest)} dense sheets for {sum(len(x['frames']) for x in manifest)} unreviewed slots")


if __name__ == "__main__":
    main()
