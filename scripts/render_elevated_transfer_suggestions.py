"""Visual spot check of unreviewed six-slot transfer suggestions."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/source_view_screen"
PACK = BASE / "elevated_transfer_review"
SELECTION = json.loads((BASE / "transfer_source_only_selection_2026-11-06.json")
                       .read_text(encoding="utf-8"))


def main():
    for case in SELECTION["cases"]:
        match_id = case["match_id"]
        data = json.loads((PACK / f"{match_id}_suggestions.json").read_text(encoding="utf-8"))
        rows = data["rows"]
        chosen = [rows[0], rows[len(rows) // 4], rows[len(rows) // 2],
                  rows[3 * len(rows) // 4], rows[-1]]
        cap = cv2.VideoCapture(str(ROOT / case["local_excerpt"]))
        tiles = []
        try:
            for row in chosen:
                cap.set(cv2.CAP_PROP_POS_FRAMES, row["excerpt_frame"])
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(row["excerpt_frame"])
                proposals = {p["raw_track_id"]: p for p in row["proposals"]}
                missing = []
                for slot in row["slots"]:
                    p = proposals.get(slot["suggested_raw_track_id"])
                    if p is None:
                        missing.append(str(slot["slot"]))
                        continue
                    x1, y1, x2, y2 = [round(v) for v in p["bbox_px"]]
                    cv2.rectangle(image, (x1, y1), (x2, y2), (50, 220, 255), 3)
                    label = f"P{slot['slot']} id {p['raw_track_id']}"
                    cv2.putText(image, label, (x1, max(y1 - 5, 22)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
                    cv2.putText(image, label, (x1, max(y1 - 5, 22)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 220, 255), 2)
                scale = min(1.0, 960 / image.shape[1])
                image = cv2.resize(image, None, fx=scale, fy=scale)
                cv2.rectangle(image, (0, 0), (image.shape[1], 28), (10, 20, 30), -1)
                title = f"frame {row['excerpt_frame']} | missing suggested slots: {','.join(missing) or 'none'}"
                cv2.putText(image, title, (7, 20), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 1)
                tiles.append(image)
        finally:
            cap.release()
        out = PACK / f"{match_id}_suggestion_spotcheck.jpg"
        if not cv2.imwrite(str(out), np.vstack(tiles)):
            raise OSError(out)
        print(out)


if __name__ == "__main__":
    main()
