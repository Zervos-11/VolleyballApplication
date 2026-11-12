"""Audit why the remaining R1 player paths need source-floor anchors."""

import hashlib
import json
from itertools import groupby
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
VIDEO = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
OUT = BASE / "r1_p11_p13_distance_gate.json"
FRAMES = {
    "11": [21064, 21143, 21161, 21188, 21236, 21265, 21299, 21316,
           21332, 21413, 21419, 21463],
    "13": [21050, 21055, 21183, 21200, 21212, 21250, 21316, 21340,
           21354, 21423, 21440, 21463],
}
CROPS = {"11": (580, 390, 1200, 900), "13": (330, 390, 1100, 900)}
OVERSHOOT_M = 0.25


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(frames):
    result = []
    for frame in frames:
        if not result or frame != result[-1][-1] + 1:
            result.append([frame])
        else:
            result[-1].append(frame)
    return [[group[0], group[-1], len(group)] for group in result]


def render_sheet(capture, pid, slots):
    width, height = 520, 400
    canvas = np.full((3 * height, 4 * width, 3), 255, np.uint8)
    x1, y1, x2, y2 = CROPS[pid]
    for index, frame in enumerate(FRAMES[pid]):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Could not read source frame {frame}")
        item = slots[frame][pid]
        box = item["bbox_px"]
        if box is not None:
            left, top, right, bottom = (int(round(value)) for value in box)
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 255), 3)
        crop = cv2.resize(image[y1:y2, x1:x2], (width, height))
        label = f"#{pid} {frame} {item['box_status']} ID:{item['raw_track_id']}"
        cv2.rectangle(crop, (0, 0), (width, 30), (0, 0, 0), -1)
        cv2.putText(crop, label, (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.54,
                    (255, 255, 255), 1, cv2.LINE_AA)
        row, col = divmod(index, 4)
        canvas[row * height:(row + 1) * height, col * width:(col + 1) * width] = crop
    filename = f"r1_p{pid}_distance_gate_source_sheet.jpg"
    cv2.imwrite(str(BASE / filename), canvas, [cv2.IMWRITE_JPEG_QUALITY, 94])
    return filename


def main():
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    slots = {row["frame"]: row["players"] for row in visual["frame_records"]}
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Source video could not be opened")
    result = {
        "status": "remaining_player_distance_gate_source_review_needed",
        "visual_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "source_sha256_from_record": json.loads((VIDEO.parent / "source_record.json").read_text(
            encoding="utf-8"))["sha256"],
        "frames_inclusive": [21050, 21463],
        "court_overshoot_limit_m": OVERSHOOT_M,
        "players": {},
        "distance_reported": False,
        "team_total_reported": False,
        "official_annotations_changed": False,
    }
    try:
        for pid in FRAMES:
            missing, offcourt, usable = [], [], []
            ids = {}
            for frame in range(21050, 21464):
                item = slots[frame][pid]
                box = item["bbox_px"]
                if item["box_status"] != "raw_box_candidate" or box is None:
                    missing.append(frame)
                    continue
                ids[str(item["raw_track_id"])] = ids.get(str(item["raw_track_id"]), 0) + 1
                point = np.float32([[[(box[0] + box[2]) / 2, box[3]]]])
                x, y = cv2.perspectiveTransform(point, matrix)[0, 0]
                if max(0, -x, x - 9, -y, y - 9) > OVERSHOOT_M:
                    offcourt.append(frame)
                else:
                    usable.append(frame)
            result["players"][pid] = {
                "raw_candidate_frames": len(usable) + len(offcourt),
                "in_court_box_bottom_frames": len(usable),
                "material_off_court_box_bottom_frames": len(offcourt),
                "missing_candidate_box_frames": len(missing),
                "missing_runs": runs(missing),
                "off_court_runs": runs(offcourt),
                "raw_id_box_counts": ids,
                "inspection_frames": FRAMES[pid],
                "source_sheet": render_sheet(capture, pid, slots),
                "floor_anchor_gate": "Needs source-grounded endpoint points at major gaps and posture changes; off-court box bottoms cannot be used as floor coordinates.",
                "estimate_status": "withheld_pending_source_floor_anchors",
            }
    finally:
        capture.release()
    result["players"]["11"]["identity_gate"] = (
        "Raw ID 367 boxes #13 near frame 21265 and later overlaps #11's candidate; "
        "do not assign the entire raw ID to #11. Existing source reviews confirm #11 is visible "
        "during all missing-box runs but record no floor path.")
    result["players"]["13"]["identity_gate"] = (
        "Source-reviewed IDs 563 and 625 hand off over 21316-21423 only. Earlier "
        "missing spans and the 21424-21463 terminal hold lack a reviewed floor path.")
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print({pid: {key: row[key] for key in ("in_court_box_bottom_frames",
                                      "material_off_court_box_bottom_frames",
                                      "missing_candidate_box_frames")}
           for pid, row in result["players"].items()})


if __name__ == "__main__":
    main()
