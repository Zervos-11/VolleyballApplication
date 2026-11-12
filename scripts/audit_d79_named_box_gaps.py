"""Make source-frame review sheets for gaps in the six named near-side boxes."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/d79_new_source"
VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
NAMED = BASE / "named_near_boxes_80_336.json"
RAW = BASE / "raw_point_candidate_80_336.json"
OUT = BASE / "named_gap_review"


def runs(frames):
    groups = []
    for frame in frames:
        if not groups or frame > groups[-1][-1] + 1:
            groups.append([frame])
        else:
            groups[-1].append(frame)
    return [[group[0], group[-1], len(group)] for group in groups]


def read_frame(capture, frame):
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, image = capture.read()
    if not ok:
        raise RuntimeError(f"Cannot decode source frame {frame}")
    return image


def tile(image, frame, pid, named, raw):
    image = image.copy()
    for item in raw["predictions"][str(frame)]:
        x1, y1, x2, y2 = map(int, item["bbox"])
        cv2.rectangle(image, (x1, y1), (x2, y2), (145, 145, 145), 1)
    for key, slot in named["frames"][str(frame)].items():
        if slot["bbox"] is None:
            continue
        x1, y1, x2, y2 = map(int, slot["bbox"])
        cv2.rectangle(image, (x1, y1), (x2, y2), (30, 225, 75), 2)
        cv2.putText(image, f"#{key}", (x1, max(18, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, .55, (30, 225, 75), 2)
    cv2.rectangle(image, (0, 0), (460, 32), (0, 0, 0), -1)
    cv2.putText(image, f"#{pid} gap / frame {frame}", (8, 23), cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 2)
    return cv2.resize(image, (640, 360), interpolation=cv2.INTER_AREA)


def main():
    named = json.loads(NAMED.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if (named["frames_inclusive"], (raw["first_frame"], raw["last_frame"])) != ([80, 336], (80, 336)):
        raise ValueError("Source ranges do not agree")
    OUT.mkdir(exist_ok=True)
    capture = cv2.VideoCapture(str(VIDEO))
    records = []
    try:
        for pid in named["target_players"]:
            missing = [frame for frame in range(80, 337)
                       if named["frames"][str(frame)][pid]["bbox"] is None]
            for first, last, length in runs(missing):
                context = sorted({max(80, first - 1), first,
                                  first + (last - first) // 3,
                                  first + 2 * (last - first) // 3,
                                  last, min(336, last + 1)})
                tiles = [tile(read_frame(capture, frame), frame, pid, named, raw) for frame in context]
                sheet = f"p{pid}_{first}_{last}.jpg"
                if not cv2.imwrite(str(OUT / sheet), cv2.hconcat(tiles)):
                    raise RuntimeError(f"Cannot write {sheet}")
                records.append({"player_id": pid, "first_frame": first, "last_frame": last,
                                "missing_slots": length, "sample_frames": context,
                                "source_sheet": sheet,
                                "review_status": "source_samples_prepared_not_densely_reviewed"})
    finally:
        capture.release()
    result = {"status": "named_box_missing_run_source_review_queue",
              "source_sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
              "named_output_sha256": hashlib.sha256(NAMED.read_bytes()).hexdigest(),
              "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
              "frame_range_inclusive": [80, 336],
              "total_missing_slots": sum(record["missing_slots"] for record in records),
              "runs": sorted(records, key=lambda record: -record["missing_slots"]),
              "limits": "Sheets sample missing runs for source review. They do not prove a player is hidden on unsampled frames or authorize filling gaps."}
    (OUT / "gap_queue.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(records), "missing_slots": result["total_missing_slots"],
                      "longest": [(r["player_id"], r["first_frame"], r["last_frame"], r["missing_slots"])
                                  for r in result["runs"][:8]]}, indent=2))


if __name__ == "__main__":
    main()
