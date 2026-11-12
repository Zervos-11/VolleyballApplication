"""Locate scoreboard digit changes inside each six-second sampled interval."""

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "data/processed/fqe_score_timeline.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
OUTPUT = ROOT / "data/processed/fqe_score_flip_frames.json"


def main():
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Source video could not be opened")
    cache = {}

    def digit_mask(frame_number, winner):
        key = (frame_number, winner)
        if key not in cache:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
                raise RuntimeError(f"Cannot decode source frame {frame_number}")
            y = 93 if winner == "ProVolley" else 133
            patch = frame[y:y + 28, 403:446]
            cache[key] = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY) > 150
        return cache[key]

    changes = []
    try:
        points = [p for p in timeline["points"] if p["evidence"] == "broadcast_score_transition"]
        for i, point in enumerate(points, 1):
            before = round(point["graphic_change_after_s"] * 50)
            after = round(point["graphic_change_by_s"] * 50)
            winner = point["winner"]
            old, new = digit_mask(before, winner), digit_mask(after, winner)
            difference = int(np.count_nonzero(old != new))
            if difference < 25:
                raise RuntimeError(f"Score digits did not differ at set {point['set']} point {point['point_number']}")

            def new_like(frame_number):
                mask = digit_mask(frame_number, winner)
                return np.count_nonzero(mask != new) < np.count_nonzero(mask != old)

            left, right = before, after
            while left + 1 < right:
                middle = (left + right) // 2
                if new_like(middle):
                    right = middle
                else:
                    left = middle
            assert not new_like(left) and new_like(right)
            changes.append({
                "set": point["set"], "point_number": point["point_number"],
                "score_before": point["score_before"], "score_after": point["score_after"],
                "first_new_digit_frame": right,
                "sampled_change_after_frame": before,
                "sampled_change_by_frame": after,
                "digit_pixel_difference": difference,
                "pilot_rally_id": point["pilot_rally_id"],
                "method": "first_frame_closer_to_new_than_old_thresholded_digit_patch",
            })
            if i % 20 == 0:
                print(f"Located {i}/{len(points)} scoreboard changes", flush=True)
    finally:
        cap.release()

    assert len(changes) == 121
    output = {
        "match_id": timeline["match_id"],
        "source_sha256": timeline["source_sha256"],
        "purpose": "Refine broadcast graphic update timing. A digit flip is not the rally-end frame.",
        "method": "Binary search between adjacent sampled keyframes, classifying the changing score digit patch against old and new endpoint images. If the graphic animates, this is the first frame classified nearer the new digit appearance.",
        "changes": changes,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(changes)} refined score flips to {OUTPUT}")


if __name__ == "__main__":
    main()
