"""Single-reviewer floor-contact proposals for #20's r1 late segment.

These are hand-selected from the source contact sheets and the existing sparse
analyst review. They are review anchors, not independent labels or a dense path.
"""

from __future__ import annotations

import json

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


CONTACTS = BASE / "r1_p20_contact_checks.json"
SHOES = BASE / "r1_p20_body_shoe_contact_trial.json"
OUT = BASE / "r1_p20_late_contact_anchor_review.json"

# One source-reviewed proposal every ten frames, plus the last point frame.
# None means the sole-floor contact cannot be chosen from this source crop.
PROPOSALS = {
    21300: ("existing_analyst_point", "one_visible_planted_shoe", None, "Planted image-left shoe; other shoe raised."),
    21310: ("existing_analyst_point", "one_visible_planted_shoe", None, "Planted white shoe despite truncated detector box."),
    21320: ("new_source_sheet_proposal", "two_planted_sole_midpoint", [714.5, 817.0], "Both white soles appear floor-level."),
    21330: ("new_source_sheet_proposal", "two_planted_sole_midpoint", [685.0, 820.0], "Both white soles appear floor-level."),
    21340: ("existing_analyst_point", "two_planted_sole_midpoint", None, "Keep existing analyst midpoint rather than one merged colour component."),
    21350: ("new_source_sheet_proposal", "two_planted_sole_midpoint", [639.5, 827.0], "Both white soles appear floor-level; right heel is less clear."),
    21360: ("new_source_sheet_proposal", "two_planted_sole_midpoint", [633.5, 827.0], "Both white soles appear floor-level."),
    21370: ("new_source_sheet_proposal", "two_planted_sole_midpoint", [638.0, 827.0], "Both white soles appear floor-level."),
    21380: ("existing_analyst_point", "one_visible_planted_shoe", None, "Keep existing planted-shoe analyst point."),
    21390: ("new_source_sheet_proposal", "one_visible_planted_shoe", [656.0, 814.0], "Image-right shoe appears planted; image-left heel is raised."),
    21400: ("new_source_sheet_proposal", "two_planted_sole_midpoint", [670.0, 812.0], "Both white shoes appear at floor level during step transition."),
    21410: ("new_source_sheet_proposal", "one_visible_planted_shoe", [706.0, 809.0], "Image-right shoe appears planted; image-left heel is raised."),
    21420: ("existing_analyst_point", "one_visible_planted_shoe", None, "Keep existing point on the planted shoe; other shoe is airborne."),
    21430: ("new_source_sheet_proposal", "one_visible_planted_shoe", [644.0, 805.0], "Image-left shoe appears planted; image-right shoe is raised."),
    21440: ("source_sheet_uncertain", "uncertain", None, "Both shoes move in a crowded transition; no repeatable sole-floor point selected."),
    21450: ("new_source_sheet_proposal", "one_visible_planted_shoe", [760.0, 790.0], "Image-right shoe appears planted; image-left shoe is obscured or raised."),
    21460: ("new_source_sheet_proposal", "one_visible_planted_shoe", [761.0, 792.0], "Image-right shoe appears planted; image-left shoe is raised."),
    21463: ("existing_analyst_point", "two_planted_sole_midpoint", None, "Keep existing analyst floor-level midpoint."),
}


def main() -> None:
    contacts = json.loads(CONTACTS.read_text(encoding="utf-8"))
    shoes = json.loads(SHOES.read_text(encoding="utf-8"))
    assert contacts["source_sha256"] == shoes["source_sha256"] == sha256(SOURCE)
    assert contacts["visual_candidate_sha256"] == shoes["visual_candidate_sha256"] == sha256(VISUAL)
    existing = {row["frame_index"]: row for row in contacts["rows"]}
    shoe_rows = {row["frame"]: row for row in shoes["frames"]}
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles, detail_tiles = [], [], []
    try:
        for frame_no, (origin, state, proposed, note) in PROPOSALS.items():
            if origin == "existing_analyst_point":
                proposed = existing[frame_no]["contact_px"]
            if state == "uncertain" and proposed is not None:
                raise ValueError("Uncertain state cannot carry a floor point")
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {frame_no}")
            if frame_no in (21340, 21463):
                detail = cv2.resize(frame[750:845, 590:800], (840, 380))
                cv2.putText(detail, str(frame_no), (12, 32), cv2.FONT_HERSHEY_SIMPLEX,
                            1, (0, 0, 0), 4)
                cv2.putText(detail, str(frame_no), (12, 32), cv2.FONT_HERSHEY_SIMPLEX,
                            1, (255, 255, 255), 2)
                detail_tiles.append(detail)
            x0, y0, x1, y1 = 575, 725, 835, 850
            tile = cv2.resize(frame[y0:y1, x0:x1], (520, 250))
            for region in shoe_rows[frame_no]["selected_regions"]:
                px, py = region["sole_cue_px"]
                cv2.drawMarker(tile, (round((px - x0) * 2), round((py - y0) * 2)),
                               (255, 200, 0), cv2.MARKER_CROSS, 12, 1)
            if proposed:
                px, py = proposed
                cv2.drawMarker(tile, (round((px - x0) * 2), round((py - y0) * 2)),
                               (0, 0, 255), cv2.MARKER_TILTED_CROSS, 18, 2)
            cv2.putText(tile, f"{frame_no} {state}", (5, 23),
                        cv2.FONT_HERSHEY_SIMPLEX, .48, (255, 255, 255), 2)
            tiles.append(tile)
            rows.append({"frame": frame_no, "origin": origin, "source_visual_state": state,
                         "floor_point_proposal_px": proposed,
                         "source_note": note,
                         "parent_box_status": shoe_rows[frame_no]["parent_box_status"],
                         "independent_label": False,
                         "official_annotation_changed": False})
    finally:
        cap.release()
    sheets = []
    for start in range(0, len(tiles), 6):
        name = f"r1_p20_late_contact_anchor_sheet_{start // 6 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(tiles[start:start + 3]),
            cv2.hconcat(tiles[start + 3:start + 6])]))
        sheets.append(name)
    detail_name = "r1_p20_contact_ambiguity_recheck.jpg"
    cv2.imwrite(str(BASE / detail_name), cv2.vconcat(detail_tiles))
    result = {
        "status": "single_reviewer_source_contact_anchor_proposals",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "shoe_trial_sha256": sha256(SHOES),
        "existing_contact_review_sha256": sha256(CONTACTS),
        "player_id": "20", "frames": rows, "sheets": sheets,
        "detail_sheet": detail_name,
        "summary": {"sampled_frames": len(rows),
                    "contact_proposals": sum(row["floor_point_proposal_px"] is not None for row in rows),
                    "uncertain_frames": [row["frame"] for row in rows
                                         if row["source_visual_state"] == "uncertain"],
                    "new_proposals": sum(row["origin"] == "new_source_sheet_proposal" for row in rows)},
        "dense_path_gate": {
            "status": "failed_contact_target_consistency",
            "foot_switch_review_intervals": [[21380, 21390], [21460, 21463]],
            "unknown_interval_anchor": 21440,
            "reason": "Intervals can join a planted single shoe to the other shoe or to a two-shoe midpoint. Straight chords then include stance changes, not only body translation.",
            "distance_released": False,
        },
        "limitation": "Every contact is a single-reviewer source-pixel proposal. Ten-frame intervals can hide turns and airborne events. The boxes and white components do not verify ground contact. No dense trajectory or physical distance is released.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
