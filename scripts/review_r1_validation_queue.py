"""Render source-only crops for the r1 ground-contact feasibility queue."""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
GROUPS = {
    "endpoint": ((21462, 21463, 21464), (750, 650, 1350, 1000)),
    "p9_landing": ((21065, 21070, 21100), (1250, 440, 1900, 1000)),
    "p13_overlap": ((21150, 21200, 21300), (550, 460, 1050, 920)),
    "block": ((21245, 21250, 21265), (650, 430, 1100, 900)),
    "p20_box": ((21308, 21310, 21313), (450, 460, 1000, 950)),
    "p12_motion": ((21304, 21308, 21311), (1050, 450, 1550, 920)),
    "late_left": ((21400, 21450), (350, 460, 1100, 940)),
}


def main():
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    for name, (frames, rect) in GROUPS.items():
        left, top, right, bottom = rect
        tiles = []
        for frame in frames:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame}")
            crop = image[top:bottom, left:right].copy()
            cv2.putText(crop, str(frame), (12, 38), cv2.FONT_HERSHEY_SIMPLEX,
                        1.1, (255, 255, 255), 3)
            tiles.append(crop)
        cv2.imwrite(str(BASE / f"r1_validation_{name}_source.jpg"), np.hstack(tiles))
    capture.release()
    print(f"rendered {len(GROUPS)} source-only review sheets")


if __name__ == "__main__":
    main()
