"""Keep two seeded white-shoe windows distinct and tied to player #20."""

from __future__ import annotations

import argparse
import json
import sys

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256

sys.path.insert(0, str(BASE.parents[2]))
from services.inference.seeded_shoe_tracker import LabShoeProfile, SeededShoeTracker


START, END = 21300, 21463
SEEDS = {"image_left_planted": (752, 805), "image_right_airborne": (798, 787)}
PROFILE = LabShoeProfile(l_min=220, a_min=110, a_max=142, b_min=110, b_max=143)
CROP = (580, 735, 900, 850)


def main(guard_parent_box: bool = True) -> None:
    prefix = "r1_p20_two_shoe_guarded" if guard_parent_box else "r1_p20_two_shoe_exclusive"
    output = BASE / f"{prefix}_experiment.json"
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    boxes = {row["frame"]: row["players"]["20"] for row in visual["frame_records"]}
    trackers = {name: SeededShoeTracker(point, PROFILE) for name, point in SEEDS.items()}
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    try:
        for frame_no in range(START, END + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {frame_no}")
            previous = {name: tracker.last_candidate_px for name, tracker in trackers.items()}
            observed = {name: tracker.observe(frame) for name, tracker in trackers.items()}
            raw_box = boxes[frame_no]["bbox_px"]
            parent_rejected = []
            if guard_parent_box and boxes[frame_no]["box_status"] == "raw_box_candidate" and raw_box:
                for name, row in observed.items():
                    point = row["centre_px"]
                    if point and not (raw_box[0] - 6 <= point[0] <= raw_box[2] + 6 and
                                      raw_box[1] - 6 <= point[1] <= raw_box[3] + 6):
                        trackers[name].last_candidate_px = previous[name]
                        observed[name] = SeededShoeTracker._missing()
                        parent_rejected.append(name)
            points = [row["centre_px"] for row in observed.values()]
            separation = (float(np.linalg.norm(np.subtract(*points)))
                          if all(point is not None for point in points) else None)
            collision_rejected = None
            if separation is not None and separation < 14.0:
                # Both independent searches chose the same visible shoe region.
                # Keep the closer continuation; the other track becomes unknown.
                names = list(SEEDS)
                rejected = max(names, key=lambda name: (observed[name]["step_px"], name))
                trackers[rejected].last_candidate_px = previous[rejected]
                observed[rejected] = SeededShoeTracker._missing()
                collision_rejected = rejected
            inside = {name: (bool(raw_box and raw_box[0] <= row["centre_px"][0] <= raw_box[2]
                                  and raw_box[1] <= row["centre_px"][1] <= raw_box[3])
                             if row["centre_px"] is not None and
                                boxes[frame_no]["box_status"] == "raw_box_candidate"
                             else None)
                      for name, row in observed.items()}
            rows.append({"frame": frame_no, "raw_box_status": boxes[frame_no]["box_status"],
                         "shoes": observed, "candidate_inside_raw_player_box": inside,
                         "candidate_separation_px": round(separation, 1) if separation else None,
                         "collision_rejected_seed": collision_rejected,
                         "parent_box_rejected_seeds": parent_rejected,
                         "body_midpoint_from_shoes_px": None,
                         "court_position_m": None})
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (640, 230),
                              interpolation=cv2.INTER_LINEAR)
            for name, colour in (("image_left_planted", (0, 255, 255)),
                                 ("image_right_airborne", (255, 0, 255))):
                point = observed[name]["centre_px"]
                if point:
                    cv2.drawMarker(tile, (round((point[0] - x0) * 2),
                                          round((point[1] - y0) * 2)),
                                   colour, cv2.MARKER_CROSS, 14, 2)
            cv2.putText(tile, str(frame_no), (5, 23), cv2.FONT_HERSHEY_SIMPLEX,
                        .65, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    sheets = []
    blank = np.full_like(tiles[0], 30)
    for start in range(0, len(tiles), 12):
        part = tiles[start:start + 12]
        part += [blank] * (12 - len(part))
        name = f"{prefix}_sheet_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 3]) for i in (0, 3, 6, 9)]))
        sheets.append(name)
    summary = {
        "frames_both_candidates": sum(all(shoe["centre_px"] is not None for shoe in row["shoes"].values())
                                      for row in rows),
        "collision_rejection_frames": [row["frame"] for row in rows
                                       if row["collision_rejected_seed"]],
        "parent_box_rejection_frames": [row["frame"] for row in rows
                                         if row["parent_box_rejected_seeds"]],
        "distinct_candidate_frames": sum(all(shoe["centre_px"] is not None
                                             for shoe in row["shoes"].values())
                                         for row in rows),
        "outside_raw_box_frames_by_seed": {
            name: [row["frame"] for row in rows
                   if row["candidate_inside_raw_player_box"][name] is False]
            for name in SEEDS},
    }
    result = {
        "status": ("mutually_exclusive_parent_box_guarded_two_shoe_diagnostic"
                   if guard_parent_box else "mutually_exclusive_two_white_shoe_windows_diagnostic"),
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "seed": {"frame": START, "player_id": "20", "source_points_px": SEEDS,
                 "second_shoe_state": "airborne_at_seed"},
        "frames": rows, "sheets": sheets, "summary": summary,
        "limitation": ("Shared components and candidates beyond the parent box plus 6 px are withheld. A parent box does not prove shoe identity inside an overlap, and missing boxes cannot gate candidates. No body midpoint or distance is released."
                       if guard_parent_box else
                       "Shared components are withheld from one shoe track. Separation does not prove left/right foot identity or grounded contact. No body midpoint or distance is released."),
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unguarded", action="store_true",
                        help="Record the mutual-exclusion baseline without parent-box rejection")
    main(guard_parent_box=not parser.parse_args().unguarded)
