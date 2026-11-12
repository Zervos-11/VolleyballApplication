"""Reproduce the D79 near-net source contact review sheet."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
OUTPUT = ROOT / "data/processed/d79_new_source/net_contact_source_sheet.jpg"
FRAMES = [240, 248, 256, 264, 272, 280, 287, 289]
COLORS = {"4": (0, 0, 255), "9": (0, 220, 0), "15": (255, 220, 0)}


def main():
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    capture = cv2.VideoCapture(str(VIDEO))
    tiles = []
    for frame in FRAMES:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        good, image = capture.read()
        if not good:
            raise RuntimeError(f"source frame {frame} unavailable")
        tile = image[300:560, 500:960].copy()
        net_line = lambda x: 504.5 - 0.0185 * x
        cv2.line(tile, (0, round(net_line(500) - 300)),
                 (460, round(net_line(960) - 300)), (0, 180, 255), 2)
        for player in labels["frames"][str(frame)]["players"]:
            pid = str(player["player_id"])
            point = player.get("footpoint")
            if pid not in COLORS or point is None:
                continue
            x, y = np.rint(point).astype(int)
            cv2.circle(tile, (x - 500, y - 300), 5, COLORS[pid], -1)
            cv2.putText(tile, pid, (x - 490, y - 310), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, COLORS[pid], 2)
        cv2.putText(tile, str(frame), (5, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)
        tiles.append(tile)
    capture.release()
    sheet = np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(OUTPUT), sheet):
        raise RuntimeError("could not write source sheet")


if __name__ == "__main__":
    main()
