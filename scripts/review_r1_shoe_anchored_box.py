"""Check a fixed-size #10 player box translated with her shoe-colour centre."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


COLOUR = BASE / "r1_p10_color_shoe_experiment.json"
OUT = BASE / "r1_p10_shoe_anchored_box_review.json"
SHEET = BASE / "r1_p10_shoe_anchored_box_review.jpg"
SAMPLES = [21098, 21105, 21110, 21114, 21115, 21120, 21126, 21132, 21133]
DISPLAY_CROP = (1120, 580, 1380, 855)


def translated_box(seed_box: list[float], seed_centre: list[float],
                   current_centre: list[float]) -> list[float]:
    dx = current_centre[0] - seed_centre[0]
    dy = current_centre[1] - seed_centre[1]
    return [round(value + (dx if index % 2 == 0 else dy), 1)
            for index, value in enumerate(seed_box)]


def intersection_over_union(a: list[float], b: list[float]) -> float:
    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    return overlap / (area_a + area_b - overlap) if area_a + area_b > overlap else 0.0


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    colour = json.loads(COLOUR.read_text(encoding="utf-8"))
    assert colour["source_sha256"] == sha256(SOURCE)
    assert colour["visual_candidate_sha256"] == sha256(VISUAL)
    slots = {row["frame"]: row["players"]["10"] for row in visual["frame_records"]}
    candidates = {row["frame"]: row for row in colour["frames"]}
    seed_box = slots[21098]["bbox_px"]
    seed_centre = candidates[21098]["selected_component"]["centre_px"]
    rows = []
    for frame in range(21098, 21134):
        candidate = candidates[frame]
        component = candidate["selected_component"]
        box = translated_box(seed_box, seed_centre, component["centre_px"]) if component else None
        rows.append({
            "frame": frame,
            "raw_box_status": slots[frame]["box_status"],
            "shoe_colour_centre_px": component["centre_px"] if component else None,
            "fixed_size_box_px": box,
            "continuity_suspect": candidate["continuity_suspect"],
            "box_state": "unverified_shoe_anchored_display_box" if box else "no_shoe_candidate",
            "verified_person_box_px": None,
            "verified_floor_contact_px": None,
            "court_position_m": None,
        })
    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    try:
        for frame in SAMPLES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {frame}")
            x0, y0, x1, y1 = DISPLAY_CROP
            tile = image[y0:y1, x0:x1].copy()
            row = next(row for row in rows if row["frame"] == frame)
            box = row["fixed_size_box_px"]
            if box:
                tl = (round(box[0] - x0), round(box[1] - y0))
                br = (round(box[2] - x0), round(box[3] - y0))
                cv2.rectangle(tile, tl, br, (0, 255, 255), 2)
                point = row["shoe_colour_centre_px"]
                cv2.drawMarker(tile, (round(point[0] - x0), round(point[1] - y0)),
                               (0, 255, 255), cv2.MARKER_CROSS, 12, 2)
            raw_box = slots[frame]["bbox_px"]
            if raw_box:
                cv2.rectangle(tile, (round(raw_box[0] - x0), round(raw_box[1] - y0)),
                              (round(raw_box[2] - x0), round(raw_box[3] - y0)),
                              (255, 255, 0), 2)
            cv2.putText(tile, str(frame), (6, 23), cv2.FONT_HERSHEY_SIMPLEX,
                        .65, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    blank = np.full_like(tiles[0], 30)
    tiles += [blank] * (12 - len(tiles))
    cv2.imwrite(str(SHEET), cv2.vconcat([
        cv2.hconcat(tiles[index:index + 3]) for index in (0, 3, 6, 9)]))
    at_21132 = next(row for row in rows if row["frame"] == 21132)
    result = {
        "status": "fixed_seed_box_shoe_translation_diagnostic",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "colour_experiment_sha256": sha256(COLOUR),
        "seed": {"frame": 21098, "player_id": "10", "raw_box_px": seed_box,
                 "shoe_colour_centre_px": seed_centre},
        "rule": "Translate the original whole-player box by the change in the selected shoe-colour component centre; keep width and height fixed.",
        "frames": rows,
        "source_sheet": SHEET.name,
        "diagnostics": {
            "candidate_box_frames_in_missing_run": sum(row["fixed_size_box_px"] is not None and
                                                       row["raw_box_status"] == "missing" for row in rows),
            "suspect_component_jump_frames": [row["frame"] for row in rows if row["continuity_suspect"]],
            "last_colour_box_vs_reappeared_raw_box_iou_one_frame_later": round(
                intersection_over_union(at_21132["fixed_size_box_px"], slots[21133]["bbox_px"]), 3),
        },
        "limitation": "The translated rectangle is a display hypothesis. Its shape cannot follow a bending body, and a changing visible shoe fragment shifts its centre. It does not replace a detector box or define floor travel.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["diagnostics"])


if __name__ == "__main__":
    main()
