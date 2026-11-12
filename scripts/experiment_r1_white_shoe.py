"""Test a shoe-seeded colour window on #20's non-distinct white shoes."""

from __future__ import annotations

import json
import sys

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256

sys.path.insert(0, str(BASE.parents[2]))
from services.inference.seeded_shoe_tracker import LabShoeProfile, SeededShoeTracker


CONTACT_REVIEW = BASE / "r1_p20_contact_checks.json"
OUT = BASE / "r1_p20_white_shoe_experiment.json"
START, END = 21300, 21463
PROFILE = LabShoeProfile(l_min=220, a_min=110, a_max=142, b_min=110, b_max=143)
CROP = (580, 735, 900, 850)


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    contacts = json.loads(CONTACT_REVIEW.read_text(encoding="utf-8"))
    assert contacts["source_sha256"] == sha256(SOURCE)
    assert contacts["visual_candidate_sha256"] == sha256(VISUAL)
    by_frame = {row["frame"]: row["players"]["20"] for row in visual["frame_records"]}
    reference = {row["frame_index"]: row for row in contacts["rows"]}
    seed = tuple(reference[START]["contact_px"])
    tracker = SeededShoeTracker(seed, PROFILE)
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    try:
        for frame_no in range(START, END + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {frame_no}")
            observation = tracker.observe(frame)
            centre = observation["centre_px"]
            box = by_frame[frame_no]["bbox_px"]
            in_box = (bool(box and box[0] <= centre[0] <= box[2] and
                           box[1] <= centre[1] <= box[3])
                      if centre and by_frame[frame_no]["box_status"] == "raw_box_candidate"
                      else None)
            contact = reference.get(frame_no)
            contact_px = contact["contact_px"] if contact else None
            comparison = ({21420: "other_planted_shoe",
                           21463: "floor_midpoint_between_shoes"}.get(
                               frame_no, "roughly_same_visible_shoe")
                          if contact_px else None)
            contact_error = (float(np.linalg.norm(np.subtract(centre, contact_px)))
                             if centre and contact_px else None)
            rows.append({"frame": frame_no,
                         "raw_box_status": by_frame[frame_no]["box_status"],
                         "shoe_colour_candidate": observation,
                         "candidate_inside_raw_player_box": in_box,
                         "analyst_contact_px": contact_px,
                         "contact_comparison_kind": comparison,
                         "candidate_centre_vs_contact_px": round(contact_error, 1)
                         if contact_error is not None else None})
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (640, 230),
                              interpolation=cv2.INTER_LINEAR)
            if centre:
                cv2.drawMarker(tile, (round((centre[0] - x0) * 2),
                                      round((centre[1] - y0) * 2)),
                               (0, 255, 255), cv2.MARKER_CROSS, 13, 2)
            if contact_px:
                cv2.drawMarker(tile, (round((contact_px[0] - x0) * 2),
                                      round((contact_px[1] - y0) * 2)),
                               (0, 0, 255), cv2.MARKER_TILTED_CROSS, 13, 2)
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
        name = f"r1_p20_white_shoe_sheet_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 3]) for i in (0, 3, 6, 9)]))
        sheets.append(name)
    result = {
        "status": "development_white_shoe_candidate_experiment",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "contact_review_sha256": sha256(CONTACT_REVIEW),
        "seed": {"frame": START, "player_id": "20", "analyst_contact_px": list(seed)},
        "profile": {"l_min": PROFILE.l_min, "a_min": PROFILE.a_min,
                    "a_max": PROFILE.a_max, "b_min": PROFILE.b_min,
                    "b_max": PROFILE.b_max},
        "frames": rows, "sheets": sheets,
        "summary": {
            "candidate_frames": sum(row["shoe_colour_candidate"]["centre_px"] is not None
                                    for row in rows),
            "missing_candidate_frames": [row["frame"] for row in rows
                                         if row["shoe_colour_candidate"]["centre_px"] is None],
            "outside_raw_box_frames": [row["frame"] for row in rows
                                       if row["candidate_inside_raw_player_box"] is False],
            "suspect_step_frames": [row["frame"] for row in rows
                                    if row["shoe_colour_candidate"]["continuity_suspect"]],
            "unlike_contact_target_frames": [row["frame"] for row in rows
                                             if row["contact_comparison_kind"] in
                                             ("other_planted_shoe", "floor_midpoint_between_shoes")],
        },
        "limitation": "A white colour component may be a sock, another shoe, or a floor reflection. At 21420 and 21463 the analyst floor target is a different shoe or midpoint, so centre-to-contact differences there are not tracking errors. A component centre is not a sole-floor contact.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
