"""Render clean AoEP source frames for a predictor-free visibility review."""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4"
OUT = ROOT / "data/processed/aoep_new_source/heldout_source_review"
FIRST, LAST = 75180, 75229


def label(frame: np.ndarray, number: int) -> np.ndarray:
    cv2.putText(frame, str(number), (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                .9, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(frame, str(number), (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                .9, (0, 0, 0), 1, cv2.LINE_AA)
    return frame


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(SOURCE))
    sheets = []
    entrant_tiles = []
    centre_tiles = []
    try:
        for frame_no in range(FIRST, LAST + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Cannot decode source frame {frame_no}")
            sheets.append(label(cv2.resize(frame, (640, 360)), frame_no))
            entrant_tiles.append(label(cv2.resize(frame[230:560, 1080:1280], (400, 660)), frame_no))
            centre_tiles.append(label(cv2.resize(frame[240:540, 450:750], (600, 600)), frame_no))
    finally:
        cap.release()
    for index in range(10):
        cv2.imwrite(str(OUT / f"source_{index + 1:02d}.jpg"),
                    cv2.vconcat(sheets[index * 5:(index + 1) * 5]))
        cv2.imwrite(str(OUT / f"centre_{index + 1:02d}.jpg"),
                    cv2.hconcat(centre_tiles[index * 5:(index + 1) * 5]))
        cv2.imwrite(str(OUT / f"entrant_{index + 1:02d}.jpg"),
                    cv2.hconcat(entrant_tiles[index * 5:(index + 1) * 5]))
    print(f"rendered {LAST - FIRST + 1} source frames in {OUT}")


if __name__ == "__main__":
    main()
