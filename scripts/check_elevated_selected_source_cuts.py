"""Flag abrupt adjacent-frame changes in the two frozen transfer excerpts.

This is a diagnostic hard-cut screen, not an event-boundary or camera proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "data/processed/source_view_screen/transfer_source_only_selection_2026-11-06_v2.json"
OUTPUT = ROOT / "data/processed/source_view_screen/transfer_selected_source_cut_screen_2026-11-06.json"
THRESHOLD_MEAN_GRAY_DIFF = 35.0


def inspect(case: dict) -> dict:
    video = ROOT / case["local_excerpt"]
    lo, hi = case["screen_interval_clip_frames_inclusive"]
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open {video}")
    capture.set(cv2.CAP_PROP_POS_FRAMES, lo)
    previous = None
    differences = []
    for frame_number in range(lo, hi + 1):
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot read {video} at excerpt frame {frame_number}")
        gray = cv2.cvtColor(cv2.resize(image, (320, 180)), cv2.COLOR_BGR2GRAY)
        if previous is not None:
            differences.append((frame_number - 1, frame_number, float(np.mean(cv2.absdiff(gray, previous)))))
        previous = gray
    capture.release()
    values = [item[2] for item in differences]
    return {
        "match_id": case["match_id"],
        "excerpt_sha256": case["local_excerpt_sha256"],
        "screen_interval_clip_frames_inclusive": [lo, hi],
        "adjacent_frame_pairs": len(differences),
        "median_mean_gray_difference": float(np.median(values)),
        "maximum_mean_gray_difference": max(values),
        "pairs_above_35_gray_levels": [
            {"from_frame": a, "to_frame": b, "mean_gray_difference": round(v, 3)}
            for a, b, v in differences if v > THRESHOLD_MEAN_GRAY_DIFF
        ],
        "largest_five_pairs": [
            {"from_frame": a, "to_frame": b, "mean_gray_difference": round(v, 3)}
            for a, b, v in sorted(differences, key=lambda item: item[2], reverse=True)[:5]
        ],
    }


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    result = {
        "selection_record": str(SELECTION.relative_to(ROOT)),
        "method": "Mean absolute 8-bit grayscale difference between consecutive 320x180 decoded frames, with a fixed 35-level diagnostic flag. Low differences do not prove there was no subtle edit.",
        "cases": [inspect(case) for case in selection["cases"]],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for case in result["cases"]:
        print(case["match_id"], "pairs", case["adjacent_frame_pairs"], "flags", len(case["pairs_above_35_gray_levels"]), "max", round(case["maximum_mean_gray_difference"], 3))


if __name__ == "__main__":
    main()
