"""Embed the fixed six-slot candidate boxes in the local review page.

The stored slot keys are provisional labels from the original dense screen.
No image or reviewer annotation is changed by this script.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PAGE_JS = ROOT / "web/s3p34_ground_review.js"
SLOT_KEYS = ("28", "12", "15", "7", "19", "21")
START = "// BEGIN GENERATED NUMBERED TRACKER BOXES\n"
END = "// END GENERATED NUMBERED TRACKER BOXES"


def main():
    manifest = json.loads((SCREEN / "s3p34_30fps_ground_review/manifest.json").read_text(encoding="utf-8"))
    dense = json.loads((SCREEN / "two_long_runs_30fps_audit.json").read_text(encoding="utf-8"))
    screen = json.loads((SCREEN / "source_bracketed_30fps_screen.json").read_text(encoding="utf-8"))
    point = next(p for p in dense["rows"] if (p["set"], p["point_number"]) == (3, 34))
    raw_by_slot = {p["reviewed_jersey_number"]: p["dense_raw_track_id"] for p in point["players"]}
    assert set(raw_by_slot) == set(SLOT_KEYS)
    screen_point = next(p for p in screen["points"] if (p["set"], p["point_number"]) == (3, 34))
    rows = {p["source_frame"]: p for p in screen_point["rows"]}
    boxes = {}
    for item in manifest["frames"]:
        frame = item["frame"]
        near = {p["raw_track_id"]: p for p in rows[frame]["proposals"]
                if p["net_side_status"] == "near_floor_side_candidate"}
        if frame >= 36117 and 9 not in near and 78 in near:
            near[9] = near[78]
        ordered = []
        for key in SLOT_KEYS:
            proposal = near.get(raw_by_slot[key])
            ordered.append([round(v) for v in proposal["bbox_px"]] if proposal else None)
        boxes[str(frame)] = ordered
    source = PAGE_JS.read_text(encoding="utf-8")
    assert source.count(START) == 1 and source.count(END) == 1
    before, remainder = source.split(START, 1)
    _, after = remainder.split(END, 1)
    assignment = "const TRACKER_BOXES_BY_FRAME = " + json.dumps(boxes, separators=(",", ":")) + ";\n"
    PAGE_JS.write_text(before + START + assignment + END + after, encoding="utf-8")
    print(f"Embedded {len(boxes)} frames and {sum(b is not None for row in boxes.values() for b in row)} numbered boxes")


if __name__ == "__main__":
    main()
