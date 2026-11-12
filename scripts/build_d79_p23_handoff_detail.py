"""Enlarge raw candidate IDs around D79 near-player handoff gaps."""

import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
RAW = ROOT / "data/processed/d79_new_source/raw_point_candidate_80_336.json"
OUT = ROOT / "data/processed/d79_new_source/named_gap_review"
GROUPS = {
    "p23": ([194, 195, 197, 200, 203, 206, 209, 210, 211, 212], {7, 151, 152}),
    "p4": ([190, 191, 194, 200, 206, 211, 216, 217], {131}),
    "p9_p23": ([94, 95, 100, 105, 110, 115, 120, 124, 125, 128, 129, 136, 137, 140, 147, 148], {2, 7, 30}),
    "p15": ([183, 184, 190, 194, 200, 206, 212, 220, 226, 232, 233], {134}),
}


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    capture = cv2.VideoCapture(str(VIDEO))
    try:
        for (name, (frames, highlighted_ids)) in GROUPS.items():
          for frame in frames:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"Missing source frame {frame}")
            for person in raw["predictions"][str(frame)]:
                x1, y1, x2, y2 = map(int, person["bbox"])
                if x2 < 430 or x1 > 950 or y2 < 260:
                    continue
                color = (0, 220, 0) if person["track_id"] in highlighted_ids else (0, 0, 220)
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                cv2.putText(image, str(person["track_id"]), (x1, max(20, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2)
            crop = image[225:600, 400:1000]
            cv2.putText(crop, f"Frame {frame}", (6, 25), cv2.FONT_HERSHEY_SIMPLEX,
                        .8, (255, 255, 255), 2)
            if not cv2.imwrite(str(OUT / f"{name}_raw_detail_{frame}.jpg"), crop):
                raise RuntimeError(f"Could not write detail for {frame}")
    finally:
        capture.release()


if __name__ == "__main__":
    main()
