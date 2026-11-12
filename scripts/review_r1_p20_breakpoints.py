"""Build exact-frame source sheets for #20's unresolved shoe continuity breaks."""

from __future__ import annotations

import json

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, sha256


SHOES = BASE / "r1_p20_body_shoe_contact_trial.json"
ANCHORS = BASE / "r1_p20_late_contact_anchor_review.json"
OUT = BASE / "r1_p20_breakpoint_source_review.json"
INTERVALS = ((21331, 21343), (21390, 21403), (21454, 21463))
CROP = (560, 550, 850, 850)

# Source-visible statements only. Shoe visibility does not certify a planted
# sole or give an exact floor pixel. Existing contact anchors are kept separate.
OBSERVATIONS = {}
for frame_no in range(21331, 21344):
    merged = 21333 <= frame_no <= 21342
    OBSERVATIONS[frame_no] = {
        "visual_state": "shoes_source_visible_region_merge" if merged else "two_shoes_separated_in_source",
        "source_note": ("#20's lower legs remain visible while white regions merge; exact anatomical foot correspondence through the overlap is unverified."
                        if merged else "Two #20 shoes can be distinguished at source resolution."),
        "anatomical_foot_link": "unverified_across_21333_21342",
    }
for frame_no in range(21390, 21404):
    turning = 21393 <= frame_no <= 21399
    OBSERVATIONS[frame_no] = {
        "visual_state": ("turning_shoes_overlap_in_source" if turning else
                         "one_shoe_floor_level_other_moving" if frame_no <= 21392 else
                         "two_shoes_separated_in_source"),
        "source_note": ("One shoe swings around the other; source pixels do not establish a repeatable cross-gap anatomical label."
                        if turning else "At least one shoe appears floor-level; sole selection still needs a frame-specific point review."),
        "anatomical_foot_link": "unverified_across_21393_21399",
    }
for frame_no in range(21454, 21464):
    OBSERVATIONS[frame_no] = {
        "visual_state": "two_shoes_visible_in_source",
        "source_note": "Both #20 shoes and their lower legs are visible; region detection is checked separately below.",
        "anatomical_foot_link": "same_two_legs_visually_plausible_not_dense_label",
    }


def main() -> None:
    shoe_trial = json.loads(SHOES.read_text(encoding="utf-8"))
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    assert shoe_trial["source_sha256"] == anchors["source_sha256"] == sha256(SOURCE)
    shoes = {row["frame"]: row for row in shoe_trial["frames"]}
    contacts = {row["frame"]: row for row in anchors["frames"]}
    cap = cv2.VideoCapture(str(SOURCE))
    sheets = []
    try:
        for interval_index, (start, end) in enumerate(INTERVALS, 1):
            tiles = []
            for frame_no in range(start, end + 1):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                okay, frame = cap.read()
                if not okay:
                    raise RuntimeError(f"Could not decode frame {frame_no}")
                x0, y0, x1, y1 = CROP
                tile = cv2.resize(frame[y0:y1, x0:x1], (580, 600))
                for region in shoes[frame_no]["selected_regions"]:
                    x, y = region["sole_cue_px"]
                    cv2.circle(tile, (round((x - x0) * 2), round((y - y0) * 2)),
                               13, (0, 255, 0), 2)
                if frame_no in contacts and contacts[frame_no]["floor_point_proposal_px"]:
                    x, y = contacts[frame_no]["floor_point_proposal_px"]
                    cv2.drawMarker(tile, (round((x - x0) * 2), round((y - y0) * 2)),
                                   (255, 255, 0), cv2.MARKER_CROSS, 16, 2)
                cv2.putText(tile, str(frame_no), (8, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            .85, (255, 255, 255), 2, cv2.LINE_AA)
                tiles.append(tile)
            blank = np.full_like(tiles[0], 30)
            for first in range(0, len(tiles), 6):
                part = tiles[first:first + 6]
                part += [blank] * (6 - len(part))
                name = f"r1_p20_breakpoint_{interval_index}_sheet_{first // 6 + 1}.jpg"
                cv2.imwrite(str(BASE / name), cv2.vconcat([
                    cv2.hconcat(part[i:i + 2]) for i in (0, 2, 4)]))
                sheets.append(name)
    finally:
        cap.release()
    rows = []
    for start, end in INTERVALS:
        for frame_no in range(start, end + 1):
            observation = OBSERVATIONS[frame_no]
            candidate_count = len(shoes[frame_no]["selected_regions"])
            late_gap = 21454 <= frame_no <= 21463 and candidate_count < 2
            rows.append({"frame": frame_no,
                         "candidate_region_count": candidate_count,
                         "visual_state": ("two_shoes_visible_in_source_despite_candidate_gap" if late_gap
                                          else observation.get("visual_state", "pending_source_review")),
                         "source_note": ("Both #20 shoes are source-visible, but fewer than two colour regions were selected."
                                         if late_gap else observation.get("source_note")),
                         "ground_contact_px": observation.get("ground_contact_px"),
                         "anatomical_foot_link": observation.get("anatomical_foot_link", "unknown"),
                         "court_position_m": None})
    result = {"status": "development_breakpoint_source_review",
              "source_sha256": sha256(SOURCE),
              "shoe_trial_sha256": sha256(SHOES),
              "contact_anchor_sha256": sha256(ANCHORS),
              "intervals_inclusive": [list(value) for value in INTERVALS],
              "sheets": sheets,
              "legend": "Green circles are unverified white-shoe regions; cyan crosses are prior single-reviewer floor proposals.",
              "frames": rows,
              "summary": {"frames": len(rows),
                          "reviewed_states": sum(row["visual_state"] != "pending_source_review" for row in rows),
                          "late_source_visible_two_shoe_frames": sum(21454 <= row["frame"] <= 21463 for row in rows),
                          "late_visible_frames_with_fewer_than_two_colour_regions": sum(
                              21454 <= row["frame"] <= 21463 and row["candidate_region_count"] < 2
                              for row in rows),
                          "with_ground_contact": sum(row["ground_contact_px"] is not None for row in rows)},
              "limitation": "This single-reviewer source inspection records shoe visibility and detector misses, not exact planted-sole pixels or independently verified anatomical foot identities. Candidate circles are not grounded contacts. This artifact cannot release physical distance.",
              "production_metric_changed": False, "official_annotations_changed": False}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
