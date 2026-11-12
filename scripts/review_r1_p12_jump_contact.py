"""Make source crops around the R1 #12 airborne box-centre break."""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
OUTPUT = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_p12_jump_contact_sheet.jpg"
FRAMES = [21358, 21360, 21362, 21364, 21366, 21368,
          21370, 21372, 21374, 21376, 21378, 21380]
CROP = (1190, 470, 1590, 940)


def main():
    capture = cv2.VideoCapture(str(VIDEO))
    tiles = []
    try:
        for frame in FRAMES:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, source = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame}")
            x1, y1, x2, y2 = CROP
            tile = source[y1:y2, x1:x2].copy()
            cv2.rectangle(tile, (0, 0), (160, 42), (0, 0, 0), -1)
            cv2.putText(tile, str(frame), (12, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                        (255, 255, 255), 2)
            tiles.append(tile)
    finally:
        capture.release()
    sheet = np.vstack([np.hstack(tiles[index:index + 4]) for index in range(0, len(tiles), 4)])
    if not cv2.imwrite(str(OUTPUT), sheet):
        raise RuntimeError(f"Cannot write {OUTPUT}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
