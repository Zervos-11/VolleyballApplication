"""Render unboxed source sheets for the diagnostic S3 P34 30-fps segment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14"
OUT = BASE / "screening/s3p34_30fps_ground_review"
FIRST, LAST = 36066, 36102


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(BASE / "source_720p.mp4"))
    if not capture.isOpened():
        raise RuntimeError("Source video unavailable")
    tiles: list[np.ndarray] = []
    frame_rows: list[dict] = []
    sheet_rows: list[dict] = []
    for frame_number in range(FIRST, LAST + 1):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, source = capture.read()
        if not ok or source.shape[:2] != (720, 1280):
            raise RuntimeError(f"Cannot decode source frame {frame_number}")
        frame_path = OUT / f"unboxed_{frame_number}.png"
        cv2.imwrite(str(frame_path), source)
        frame_rows.append({"frame": frame_number, "image": frame_path.name, "sha256": sha256(frame_path)})
        crop = source[170:650, :].copy()
        tile = np.zeros((520, 1280, 3), dtype=np.uint8)
        cv2.putText(tile, f"SOURCE FRAME {frame_number} - UNBOXED", (25, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tile[40:520] = crop
        tiles.append(tile)
        if len(tiles) == 4 or frame_number == LAST:
            grid = np.zeros((1040, 2560, 3), dtype=np.uint8)
            for index, item in enumerate(tiles):
                row, col = divmod(index, 2)
                grid[row * 520 : (row + 1) * 520, col * 1280 : (col + 1) * 1280] = item
            sheet_path = OUT / f"sheet_{len(sheet_rows)+1:02d}.jpg"
            cv2.imwrite(str(sheet_path), grid, [cv2.IMWRITE_JPEG_QUALITY, 95])
            sheet_rows.append({"sheet": sheet_path.name, "first_frame": frame_number - len(tiles) + 1, "last_frame": frame_number, "sha256": sha256(sheet_path)})
            tiles = []
    capture.release()
    manifest = {"interval_inclusive": [FIRST, LAST],
                "purpose": "diagnostic_unboxed_ground_contact_review",
                "source_video_sha256": sha256(BASE / "source_720p.mp4"),
                "frames": frame_rows, "sheets": sheet_rows}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(frame_rows)} frames and {len(sheet_rows)} sheets to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
