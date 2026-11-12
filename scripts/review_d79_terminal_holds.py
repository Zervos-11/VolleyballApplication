"""Create a source contact sheet for the unresolved D79 point-end player gaps."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
RAW = ROOT / "data/processed/d79_new_source/raw_point_candidate_80_336.json"
OUT = ROOT / "data/processed/d79_new_source/terminal_hold_source_sheet.jpg"
FRAMES = [268, 280, 289, 294, 304, 310, 316, 324, 336]
IDS = {30: "#9 old raw 30", 162: "#4 raw 162", 202: "#15 raw 202"}


def main():
    predictions = json.loads(RAW.read_text(encoding="utf-8"))["predictions"]
    capture = cv2.VideoCapture(str(VIDEO))
    tiles = []
    try:
        for frame in FRAMES:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, source = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame}")
            for person in predictions[str(frame)]:
                track_id = person["track_id"]
                if track_id not in IDS:
                    continue
                x1, y1, x2, y2 = map(round, person["bbox"])
                cv2.rectangle(source, (x1, y1), (x2, y2), (20, 230, 230), 3)
                cv2.putText(source, f"raw {track_id}", (x1, max(25, y1 - 7)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 230, 230), 3)
            source = cv2.resize(source, (640, 360), interpolation=cv2.INTER_AREA)
            cv2.rectangle(source, (0, 0), (640, 38), (0, 0, 0), -1)
            cv2.putText(source, f"Frame {frame}", (12, 27), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (255, 255, 255), 2)
            tiles.append(source)
    finally:
        capture.release()
    sheet = np.vstack([np.hstack(tiles[row:row + 3]) for row in range(0, len(tiles), 3)])
    if not cv2.imwrite(str(OUT), sheet):
        raise RuntimeError(f"Cannot write {OUT}")
    print(OUT)


if __name__ == "__main__":
    main()
