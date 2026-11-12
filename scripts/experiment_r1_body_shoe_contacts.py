"""Source-frame trial: find white shoe regions under #20's identified body box.

The output is for visual review. A white component touching the detector box
bottom is only a contact cue; neither the box bottom nor a colour region proves
that a sole is planted on the floor.
"""

from __future__ import annotations

import json

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


START, END = 21300, 21463
OUT = BASE / "r1_p20_body_shoe_contact_trial.json"
CONTACT_REVIEW = BASE / "r1_p20_contact_checks.json"
CROP = (580, 735, 900, 850)


def shoe_components(frame: np.ndarray, box: list[float],
                    horizontal_margin: int = 6, min_l: int = 220,
                    min_area: int = 60) -> list[dict]:
    """Return image-space white regions within the parent box's foot band."""
    x1, _, x2, y2 = box
    left = max(0, int(x1) - horizontal_margin)
    right = min(frame.shape[1], int(np.ceil(x2)) + horizontal_margin + 1)
    top = max(0, int(y2) - 70)
    bottom = min(frame.shape[0], int(np.ceil(y2)) + 9)
    lab = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    mask = ((l >= min_l) & (a >= 110) & (a <= 131) &
            (b >= 110) & (b <= 143)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    found = []
    for index in range(1, count):
        x, y, width, height, area = map(int, stats[index])
        if area < min_area or width < 8:
            continue
        # Use the bottom few coloured rows as a sole-location cue. Components
        # extending into socks are allowed but do not gain contact status.
        ys, xs = np.where((labels == index) &
                          (np.arange(labels.shape[0])[:, None] >= y + height - 5))
        if len(xs) == 0:
            continue
        px = float(np.median(xs) + left)
        py = float(y + height - 1 + top)
        if y2 - py > 35:
            continue
        found.append({"sole_cue_px": [round(px, 1), round(py, 1)],
                      "component_bbox_px": [x + left, y + top,
                                            x + width + left, y + height + top],
                      "area_px": area,
                      "box_bottom_gap_px": round(float(y2 - py), 1),
                      "box_bottom_alignment": "aligned" if abs(y2 - py) <= 12 else
                                              "not_aligned"})
    return found


def select_foot_regions(regions: list[dict]) -> list[dict]:
    """Pick at most two separated foot-like regions, without assigning feet."""
    # Favour low, broad components; keep alternatives in the record for audit.
    ranked = sorted(regions, key=lambda row: (
        abs(row["box_bottom_gap_px"]), -row["area_px"]))
    selected = []
    for region in ranked:
        point = region["sole_cue_px"]
        if all(abs(point[0] - other["sole_cue_px"][0]) >= 25
               for other in selected):
            selected.append(region)
        if len(selected) == 2:
            break
    return sorted(selected, key=lambda row: row["sole_cue_px"][0])


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    contact_review = json.loads(CONTACT_REVIEW.read_text(encoding="utf-8"))
    assert contact_review["source_sha256"] == sha256(SOURCE)
    assert contact_review["visual_candidate_sha256"] == sha256(VISUAL)
    reference = {row["frame_index"]: row for row in contact_review["rows"]}
    boxes = {row["frame"]: row["players"]["20"] for row in visual["frame_records"]}
    cap = cv2.VideoCapture(str(SOURCE))
    rows, tiles = [], []
    previous_selected = []
    try:
        for frame_no in range(START, END + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {frame_no}")
            parent = boxes[frame_no]
            valid = parent["box_status"] == "raw_box_candidate"
            # The late lunge puts #20's front shoe beyond her detector-box edge
            # while the shaded back shoe is dimmer. Source frames 21449–21463
            # support a wider, lower-lightness search in this local interval.
            late_lunge_search = frame_no >= 21449
            search = {"horizontal_margin_px": 35 if late_lunge_search else 6,
                      "minimum_lab_lightness": 205 if late_lunge_search else 220,
                      "minimum_component_area_px": 60}
            regions = shoe_components(frame, parent["bbox_px"],
                                      search["horizontal_margin_px"],
                                      search["minimum_lab_lightness"],
                                      search["minimum_component_area_px"]) if valid else []
            chosen = select_foot_regions(regions)
            pair_rejected = None
            if len(chosen) == 2 and valid:
                middle_x = sum(region["sole_cue_px"][0] for region in chosen) / 2
                box_middle_x = (parent["bbox_px"][0] + parent["bbox_px"][2]) / 2
                if abs(middle_x - box_middle_x) > 20:
                    # A spurious second white region can fall inside a wide
                    # person box during an overlap. Keep only the continuation
                    # of a previously selected shoe, never infer its partner.
                    if previous_selected:
                        keep = min(chosen, key=lambda region: min(
                            np.linalg.norm(np.subtract(region["sole_cue_px"], old))
                            for old in previous_selected))
                        pair_rejected = next(region for region in chosen if region is not keep)
                        chosen = [keep]
                    else:
                        pair_rejected = chosen
                        chosen = []
            if chosen:
                previous_selected = [region["sole_cue_px"] for region in chosen]
            reference_row = reference.get(frame_no)
            reference_point = reference_row["contact_px"] if reference_row else None
            reference_state = reference_row["contact_state"] if reference_row else None
            matched = None
            if reference_point and reference_state.startswith("one_visible_planted_shoe") and chosen:
                matched = min((region["sole_cue_px"] for region in chosen),
                              key=lambda point: np.linalg.norm(np.subtract(point, reference_point)))
            elif reference_point and reference_state == "two_sole_floor_midpoint" and len(chosen) == 2:
                matched = np.mean([region["sole_cue_px"] for region in chosen], axis=0).tolist()
            difference = (round(float(np.linalg.norm(np.subtract(matched, reference_point))), 1)
                          if matched is not None else None)
            rows.append({"frame": frame_no, "parent_box_status": parent["box_status"],
                         "component_search": search,
                         "all_white_regions": regions, "selected_regions": chosen,
                         "body_pair_rejected_region": pair_rejected,
                         "analyst_contact_px": reference_point,
                         "analyst_contact_state": reference_state,
                         "comparable_candidate_px": [round(float(v), 1) for v in matched]
                         if matched is not None else None,
                         "candidate_vs_analyst_px": difference,
                         "verified_floor_contact_px": None,
                         "court_position_m": None})
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (640, 230))
            for region in chosen:
                px, py = region["sole_cue_px"]
                colour = ((255, 200, 0) if region["box_bottom_alignment"] == "aligned"
                          else (0, 165, 255))
                cv2.drawMarker(tile, (round((px - x0) * 2), round((py - y0) * 2)),
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
        name = f"r1_p20_body_shoe_contact_sheet_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 3]) for i in (0, 3, 6, 9)]))
        sheets.append(name)
    result = {
        "status": "body_box_conditioned_white_shoe_contact_cue_trial",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "player_id": "20", "frames": rows, "sheets": sheets,
        "summary": {
            "valid_parent_box_frames": sum(row["parent_box_status"] == "raw_box_candidate"
                                           for row in rows),
            "frames_with_one_or_more_selected_regions": sum(bool(row["selected_regions"])
                                                           for row in rows),
            "frames_with_two_selected_regions": sum(len(row["selected_regions"]) == 2
                                                    for row in rows),
            "body_pair_rejection_frames": [row["frame"] for row in rows
                                           if row["body_pair_rejected_region"] is not None],
            "late_lunge_expanded_search_frames": [row["frame"] for row in rows
                                                  if row["component_search"]["horizontal_margin_px"] == 35],
            "frames_with_box_bottom_alignment_cue": sum(any(
                region["box_bottom_alignment"] == "aligned"
                for region in row["selected_regions"]) for row in rows),
            "analyst_sample_comparison_px": {
                str(row["frame"]): row["candidate_vs_analyst_px"] for row in rows
                if row["analyst_contact_px"] is not None},
        },
        "limitation": "White regions inside a player box can include socks, reflections, or an overlapping player. Near-box-bottom is not verified sole-floor contact. Feet are not assigned left/right across frames. No player path or physical distance is released.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
