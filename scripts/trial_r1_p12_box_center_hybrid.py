"""Trial source-anchored box-centre motion with explicit holds for R1 #12."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_six_slot_visual_candidate.json"
CONTACTS = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_checks.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
OUT = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_p12_box_center_hybrid_trial.json"
FIRST, LAST = 21050, 21463
ANCHOR_FRAMES = (21070, 21200, 21250, 21343, 21350, 21374, 21463)
CHECK_FRAMES = (21150, 21236, 21400)
PREJUMP_CONTACT_PX = (1322.0, 819.0)
LANDING_CONTACT_PX = (1394.0, 840.0)
SOURCE_GAP_CONTACTS_PX = {
    21339: (1292.0, 800.0),
    21423: (1482.0, 822.0),
    21436: (1470.0, 820.0),
    21441: (1410.0, 805.0),
}
APPROACH_HOLD_FRAMES = range(21344, 21350)
AIRBORNE_HOLD_FRAMES = range(21351, 21374)
HEIGHT_TOLERANCE = 0.15
WIDTH_TOLERANCE = 0.35
COURT_OVERSHOOT_M = 0.25


def box_centre(box):
    return np.asarray([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2], dtype=float)


def box_size(box):
    return np.asarray([box[2] - box[0], box[3] - box[1]], dtype=float)


def project(point, transform):
    return cv2.perspectiveTransform(np.float32([[point]]), transform)[0, 0].astype(float)


def runs(frames):
    groups = []
    for frame in frames:
        if not groups or frame > groups[-1][-1] + 1:
            groups.append([frame])
        else:
            groups[-1].append(frame)
    return groups


def median_path(points):
    return np.asarray([np.median(points[max(0, i - 7):min(len(points), i + 8)], axis=0)
                       for i in range(len(points))])


def main():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    contacts = json.loads(CONTACTS.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    matrix = cv2.getPerspectiveTransform(np.asarray(calibration["points_px"], np.float32),
                                          np.asarray(calibration["points_court_m"], np.float32))
    slots = {entry["frame"]: entry["players"]["12"] for entry in record["frame_records"]}
    reviewed = {entry["frame_index"]: entry for entry in contacts["rows"]}
    anchors = {}
    for frame in ANCHOR_FRAMES:
        point = (PREJUMP_CONTACT_PX if frame == 21343 else
                 LANDING_CONTACT_PX if frame == 21374 else reviewed[frame]["contact_px"])
        box = slots[frame]["bbox_px"]
        if point is None or box is None:
            raise ValueError(f"Anchor {frame} needs a reviewed contact and box")
        anchors[frame] = {"floor_px": np.asarray(point, dtype=float), "centre_px": box_centre(box),
                          "size_px": box_size(box)}
    accepted = {}
    states = {}
    for frame in range(FIRST, LAST + 1):
        if frame in APPROACH_HOLD_FRAMES:
            states[frame] = "held_approach_posture_change"
            continue
        if frame in AIRBORNE_HOLD_FRAMES:
            states[frame] = "held_jump_transition"
            continue
        previous = [value for value in ANCHOR_FRAMES if value <= frame]
        if not previous:
            states[frame] = "unseeded"
            continue
        anchor_frame = previous[-1]
        anchor = anchors[anchor_frame]
        slot = slots[frame]
        box = slot["bbox_px"]
        if slot["box_status"] != "raw_box_candidate" or box is None:
            states[frame] = "held_missing_box"
            continue
        size = box_size(box)
        if abs(size[1] / anchor["size_px"][1] - 1) > HEIGHT_TOLERANCE or abs(
                size[0] / anchor["size_px"][0] - 1) > WIDTH_TOLERANCE:
            states[frame] = "held_posture_or_scale_change"
            continue
        translated = anchor["floor_px"] + box_centre(box) - anchor["centre_px"]
        court = project(translated, matrix)
        if max(0, -court[0], court[0] - 9, -court[1], court[1] - 9) > COURT_OVERSHOOT_M:
            states[frame] = "held_off_court_translation"
            continue
        accepted[frame] = court
        states[frame] = "box_centre_translation_proxy"
    segments = runs(sorted(accepted))
    smoothed = [median_path(np.asarray([accepted[frame] for frame in group])) for group in segments]
    visible_path = sum(float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
                       for points in smoothed if len(points) > 1)
    jump_contact_chord = float(np.linalg.norm(
        project(reviewed[21350]["contact_px"], matrix) - project(LANDING_CONTACT_PX, matrix)))
    prejump_contact_chord = float(np.linalg.norm(
        project(PREJUMP_CONTACT_PX, matrix) - project(reviewed[21350]["contact_px"], matrix)))
    prejump_perturbations = [float(np.linalg.norm(
        project([PREJUMP_CONTACT_PX[0] + dx, PREJUMP_CONTACT_PX[1] + dy], matrix) -
        project(reviewed[21350]["contact_px"], matrix)))
        for dx in (-5, 5) for dy in (-5, 5)]
    jump_perturbations = [float(np.linalg.norm(
        project(reviewed[21350]["contact_px"], matrix) -
        project([LANDING_CONTACT_PX[0] + dx, LANDING_CONTACT_PX[1] + dy], matrix)))
        for dx in (-5, 5) for dy in (-5, 5)]
    chords = []
    source_gap_chords = {
        (21339, 21343): float(np.linalg.norm(
            project(SOURCE_GAP_CONTACTS_PX[21339], matrix) - project(PREJUMP_CONTACT_PX, matrix))),
        (21423, 21436): float(np.linalg.norm(
            project(SOURCE_GAP_CONTACTS_PX[21423], matrix) -
            project(SOURCE_GAP_CONTACTS_PX[21436], matrix))),
        (21441, 21463): float(np.linalg.norm(
            project(SOURCE_GAP_CONTACTS_PX[21441], matrix) -
            project(reviewed[21463]["contact_px"], matrix))),
    }
    source_gap_sensitivity = {}
    for (before, after), chord in source_gap_chords.items():
        before_px = SOURCE_GAP_CONTACTS_PX[before]
        after_px = (SOURCE_GAP_CONTACTS_PX[after] if after in SOURCE_GAP_CONTACTS_PX else
                    PREJUMP_CONTACT_PX if after == 21343 else reviewed[after]["contact_px"])
        perturbations = [float(np.linalg.norm(
            project((before_px[0] + dx, before_px[1] + dy), matrix) -
            project(after_px, matrix))) for dx in (-5, 5) for dy in (-5, 5)]
        source_gap_sensitivity[f"{before}-{after}"] = [round(min(perturbations), 3),
                                                        round(max(perturbations), 3)]
    for left_frames, right_frames, left, right in zip(segments, segments[1:], smoothed, smoothed[1:]):
        gap = (left_frames[-1], right_frames[0])
        if gap in source_gap_chords:
            chords.append(source_gap_chords[gap])
        elif gap == (21343, 21350):
            chords.append(prejump_contact_chord)
        elif gap == (21350, 21374):
            chords.append(jump_contact_chord)
        else:
            chords.append(float(np.linalg.norm(right[0] - left[-1])))
    gap_details = [
        {"before_frame": left[-1], "after_frame": right[0],
         "held_frames": right[0] - left[-1] - 1, "endpoint_chord_m": round(chord, 2),
         "endpoint_method": "source_checked_ground_contacts" if (left[-1], right[0]) in
                            {(21339, 21343), (21343, 21350), (21350, 21374),
                             (21423, 21436), (21441, 21463)}
                            else "smoothed_box_centre_proxy"}
        for left, right, chord in zip(segments, segments[1:], chords)
    ]
    largest_short_gap = max((gap for gap in gap_details if gap["held_frames"] <= 10),
                            key=lambda gap: gap["endpoint_chord_m"], default=None)
    validation = []
    for frame in CHECK_FRAMES:
        actual = project(reviewed[frame]["contact_px"], matrix)
        prediction = accepted.get(frame)
        validation.append({"frame": frame, "status": states[frame],
                           "error_m": round(float(np.linalg.norm(prediction - actual)), 3)
                                      if prediction is not None else None})
    counts = {state: sum(value == state for value in states.values()) for state in sorted(set(states.values()))}
    result = {
        "status": "development_box_centre_hybrid_trial_not_validated_distance",
        "record_sha256": hashlib.sha256(RECORD.read_bytes()).hexdigest(),
        "contacts_sha256": hashlib.sha256(CONTACTS.read_bytes()).hexdigest(),
        "calibration_sha256": hashlib.sha256(CALIBRATION.read_bytes()).hexdigest(),
        "frames_inclusive": [FIRST, LAST],
        "distance_scope_frames_inclusive": [ANCHOR_FRAMES[0], LAST],
        "anchor_frames": ANCHOR_FRAMES,
        "prejump_contact_px": PREJUMP_CONTACT_PX,
        "additional_source_gap_contacts_px": SOURCE_GAP_CONTACTS_PX,
        "additional_source_gap_chords_m": {f"{before}-{after}": round(chord, 3)
                                           for (before, after), chord in source_gap_chords.items()},
        "additional_source_gap_5px_first_click_sensitivity_m": source_gap_sensitivity,
        "additional_source_gap_contact_status": "single_reviewer_visible_shoe_floor_contact_proposals_not_independent_ground_truth",
        "prejump_contact_status": "single_reviewer_visible_planted_shoe_floor_contact_proposal_at_frame_21343",
        "prejump_source_contact_chord_m": round(prejump_contact_chord, 3),
        "prejump_5px_corner_sensitivity_chord_m": [round(min(prejump_perturbations), 3),
                                                    round(max(prejump_perturbations), 3)],
        "source_reviewed_approach_hold_frames_inclusive": [21344, 21349],
        "landing_contact_px": LANDING_CONTACT_PX,
        "landing_contact_status": "single_reviewer_visible_left_shoe_floor_contact_proposal_at_frame_21374",
        "takeoff_anchor_frame": 21350,
        "takeoff_anchor_contact_px": reviewed[21350]["contact_px"],
        "jump_source_contact_chord_m": round(jump_contact_chord, 3),
        "landing_5px_corner_sensitivity_chord_m": [round(min(jump_perturbations), 3),
                                                    round(max(jump_perturbations), 3)],
        "jump_source_sheet": "r1_p12_jump_contact_sheet.jpg",
        "prejump_source_sheet": "r1_p12_prejump_gap_sheet.jpg",
        "prejump_source_zoom": "r1_p12_foot_21343_zoom.png",
        "source_reviewed_jump_hold_frames_inclusive": [21351, 21373],
        "heldout_check_frames": CHECK_FRAMES,
        "height_tolerance_fraction": HEIGHT_TOLERANCE,
        "width_tolerance_fraction": WIDTH_TOLERANCE,
        "court_overshoot_limit_m": COURT_OVERSHOOT_M,
        "state_counts": counts,
        "accepted_segment_count": len(segments),
        "longest_held_run_frames": max((len(group) for group in runs([f for f, state in states.items()
                                                                 if state.startswith("held_")])), default=0),
        "visible_segment_path_m": round(visible_path, 2),
        "closed_gap_endpoint_chords_m": [round(value, 2) for value in chords],
        "closed_gap_details": gap_details,
        "anchored_scope_hold_scenario_m": round(visible_path + sum(chords), 2),
        "reported_approximate_distance_m": round(visible_path + sum(chords), 2),
        "distance_status": "reportable_approximate_endpoint_chord_estimate",
        "validation_status": "not_validated_physical_distance",
        "reporting_scope": "player_12_frames_21070_to_21463_only_first_20_candidate_frames_excluded",
        "gap_policy": "accepted_segment_path_plus_straight_endpoint_chords_across_closed_holds",
        "largest_short_gap": largest_short_gap,
        "heldout_check_results": validation,
        "limitation": "Five earlier reviewed floor anchors and two new source anchors construct this candidate; three other reviewed frames are held out. Additional gap contacts are single-reviewer proposals. The position is a translated box-centre proxy. Endpoint chords omit within-gap detours, including the 21212-21245 overlap. This is an agreed-policy approximate estimate for the stated frame scope, not validated physical distance or a six-player total.",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
