"""Render three local source frames with raw candidate boxes for visual QC."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/source_view_screen"
SELECTION = BASE / "transfer_source_only_selection_2026-11-06.json"


def main() -> None:
    selected = json.loads(SELECTION.read_text(encoding="utf-8"))
    for case in selected["cases"]:
        result = json.loads((BASE / f"{case['match_id']}_raw_5hz_candidates.json")
                                .read_text(encoding="utf-8"))
        source = ROOT / case["local_excerpt"]
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise FileNotFoundError(source)
        rows = result["rows"]
        chosen = [rows[0], rows[len(rows) // 2], rows[-1]]
        tiles = []
        try:
            for row in chosen:
                frame = row["excerpt_frame"]
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode frame {frame}")
                scale = min(1.0, 960 / image.shape[1])
                image = cv2.resize(image, None, fx=scale, fy=scale)
                for proposal in row["proposals"]:
                    x1, y1, x2, y2 = [round(v * scale) for v in proposal["bbox_px"]]
                    cv2.rectangle(image, (x1, y1), (x2, y2), (30, 235, 235), 1)
                    label = str(proposal["raw_track_id"])
                    cv2.putText(image, label, (x1, max(y1 - 3, 11)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3)
                    cv2.putText(image, label, (x1, max(y1 - 3, 11)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 235, 235), 1)
                title = f"excerpt frame {frame} | {len(row['proposals'])} all-person proposals"
                cv2.rectangle(image, (0, 0), (image.shape[1], 25), (15, 22, 30), -1)
                cv2.putText(image, title, (8, 18), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (255, 255, 255), 1, cv2.LINE_AA)
                tiles.append(image)
        finally:
            cap.release()
        sheet = np.vstack(tiles)
        out = BASE / f"{case['match_id']}_raw_candidate_spotcheck.jpg"
        if not cv2.imwrite(str(out), sheet):
            raise OSError(out)
        print(out)


if __name__ == "__main__":
    main()
