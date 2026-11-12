"""Reacquire blue #10's pink shoe after foreground overlap in a bounded gap.

Colour and proximity create image candidates only. This does not establish a
floor contact or general-purpose six-player tracking.
"""

from __future__ import annotations

import json
import sys

import cv2
import numpy as np

from experiment_r1_seeded_shoe import (BASE, SOURCE, VISUAL, START, END, SEED,
                                       sha256)
sys.path.insert(0, str(BASE.parents[2]))
from services.inference.seeded_shoe_tracker import LabShoeProfile, SeededShoeTracker


OUT = BASE / "r1_p10_color_shoe_experiment.json"
ROI = (1180, 788, 1270, 831)
PROFILE = LabShoeProfile(l_min=145, a_min=138, b_max=155)


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    by_frame = {row["frame"]: row["players"]["10"] for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    tracker = SeededShoeTracker(SEED, PROFILE)
    try:
        for frame_no in range(START, END + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source frame {frame_no}")
            observation = tracker.observe(frame)
            chosen = ({"centre_px": observation["centre_px"],
                       "bbox_px": observation["bbox_px"],
                       "area_px": observation["area_px"]}
                      if observation["centre_px"] is not None else None)
            rows.append({
                "frame": frame_no,
                "candidate_box_status": by_frame[frame_no]["box_status"],
                "pink_components_in_roi": observation["component_count"],
                "selected_component": chosen,
                "component_step_px": observation["step_px"],
                "continuity_suspect": observation["continuity_suspect"],
                "state": "seed_frame_colour_match" if frame_no == START and chosen else
                         "unverified_colour_candidate" if chosen else "no_colour_candidate",
                "verified_floor_contact_px": None,
                "court_position_m": None,
            })
            x0, y0, x1, y1 = ROI
            tile = cv2.resize(frame[y0 - 15:y1 + 15, x0 - 10:x1 + 10],
                              (440, 292), interpolation=cv2.INTER_LINEAR)
            if chosen:
                px, py = chosen["centre_px"]
                xy = (round((px - (x0 - 10)) * 4), round((py - (y0 - 15)) * 4))
                cv2.drawMarker(tile, xy, (0, 255, 255), cv2.MARKER_CROSS, 17, 2)
            cv2.putText(tile, str(frame_no), (5, 23), cv2.FONT_HERSHEY_SIMPLEX,
                        .65, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    sheets = []
    for start in range(0, len(tiles), 12):
        part = tiles[start:start + 12]
        name = f"r1_p10_color_shoe_sheet_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 4]) for i in (0, 4, 8)]))
        sheets.append(name)
    result = {
        "status": "development_colour_shoe_experiment_unverified",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "seed": {"frame": START, "player_id": "10", "left_shoe_floor_contact_proposal_px": list(SEED)},
        "method": {"initial_roi_xyxy": list(ROI),
                   "dynamic_roi_follows_last_candidate": True,
                   "lab_thresholds": {"l_min": PROFILE.l_min, "a_min": PROFILE.a_min,
                                      "b_max": PROFILE.b_max},
                   "minimum_component_area_px": PROFILE.min_area_px,
                   "maximum_component_distance_px": PROFILE.max_distance_px,
                   "suspicious_step_px": PROFILE.suspicious_step_px},
        "frames": rows, "sheets": sheets,
        "review_summary": {
            "colour_candidate_frames": sum(row["selected_component"] is not None for row in rows),
            "no_candidate_frames": [row["frame"] for row in rows if row["selected_component"] is None],
            "suspect_component_steps": [row["frame"] for row in rows if row["continuity_suspect"]],
            "interpretation": "The colour gate often reacquires the pink shoe after overlap, but a partial-to-full silhouette change shifts the component centre. These are shoe appearance candidates, not movement samples.",
        },
        "limitation": "A pink blob can be a shoe, reflection, or another player's garment. The colour thresholds were selected for this sample. No floor or movement metric is produced.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{sum(row['selected_component'] is not None for row in rows)}/{len(rows)} colour candidates")


if __name__ == "__main__":
    main()
