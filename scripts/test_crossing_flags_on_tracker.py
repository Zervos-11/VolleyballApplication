"""Test online crossing flags from raw ByteTrack boxes against reviewed paths."""

import csv
import json
from collections import defaultdict
from pathlib import Path

from evaluate_crossing_flags import (
    MAX_HOLD_FRAMES, MIN_OVERLAP_OF_SMALLER, WINDOWS,
    forecast_overlap, overlap_of_smaller,
)


PREDICTIONS = {
    "r4": WINDOWS["r4"].parent / "tracker_predictions.json",
    "r2": WINDOWS["r2"] / "tracker_predictions.json",
}


def raw_flags(predictions, first, last):
    """Use only boxes and track IDs available through the current frame."""
    last_seen = {}
    per_frame = {}
    for frame in range(first, last + 1):
        boxes = {int(row["track_id"]): row["bbox"]
                 for row in predictions[str(frame)] if int(row["track_id"]) >= 0}
        previous = last_seen.copy()
        statuses = {}
        for track_id, box in boxes.items():
            others = [(other, candidate) for other, candidate in boxes.items()
                      if other != track_id]
            overlaps = [(other, overlap_of_smaller(box, candidate))
                        for other, candidate in others
                        if overlap_of_smaller(box, candidate) >= MIN_OVERLAP_OF_SMALLER]
            approaching = [(other, forecast_overlap(
                frame, track_id, box, other, candidate, previous))
                for other, candidate in others
                if overlap_of_smaller(box, candidate) < MIN_OVERLAP_OF_SMALLER
                and forecast_overlap(frame, track_id, box, other, candidate, previous)
                >= MIN_OVERLAP_OF_SMALLER]
            partners = overlaps if overlaps else approaching
            statuses[track_id] = {"status": ("overlap_risk" if overlaps else
                                               "approaching_overlap" if approaching else
                                               "visible_clear"),
                                  "partners": [other for other, _ in partners],
                                  "largest_overlap": max((value for _, value in partners), default=0),
                                  "age": 0}
        for track_id, (seen_frame, old_box) in previous.items():
            age = frame - seen_frame
            if track_id in boxes or age > MAX_HOLD_FRAMES:
                continue
            partners = [(other, overlap_of_smaller(old_box, candidate))
                        for other, candidate in boxes.items()
                        if overlap_of_smaller(old_box, candidate) >= MIN_OVERLAP_OF_SMALLER]
            statuses[track_id] = {"status": ("possible_occlusion" if partners else
                                               "missing_unknown"),
                                  "partners": [other for other, _ in partners],
                                  "largest_overlap": max((value for _, value in partners), default=0),
                                  "age": age}
        last_seen.update({key: (frame, box) for key, box in boxes.items()})
        per_frame[frame] = statuses
    return per_frame


def evaluate(name):
    window = WINDOWS[name]
    dense = json.loads(PREDICTIONS[name].read_text())
    with (window / "assisted_paths.csv").open(newline="", encoding="utf-8") as stream:
        reviewed = list(csv.DictReader(stream))
    first = min(int(row["frame_index"]) for row in reviewed)
    last = max(int(row["frame_index"]) for row in reviewed)
    flags = raw_flags(dense["predictions"], first, last)
    last_player_track = {}
    comparison = []
    for row in sorted(reviewed, key=lambda item: (int(item["frame_index"]), item["player_id"])):
        frame, player = int(row["frame_index"]), row["player_id"]
        current = int(row["candidate_track_id"]) if row["candidate_track_id"] else None
        previous = last_player_track.get(player)
        prior_id = previous[1] if previous and frame - previous[0] <= MAX_HOLD_FRAMES else None
        status = flags[frame].get(prior_id, {}) if prior_id is not None else {}
        comparison.append({"frame_index": frame, "player_id": player,
                           "reviewed_box_present": current is not None,
                           "reviewed_track_id": current,
                           "previous_reviewed_track_id": prior_id,
                           "raw_previous_track_status": status.get("status", "no_recent_track"),
                           "raw_occluder_track_ids": status.get("partners", []),
                           "raw_hold_age": status.get("age")})
        if current is not None:
            last_player_track[player] = (frame, current)
    missing = [row for row in comparison if not row["reviewed_box_present"]]
    held_missing = [row for row in missing if row["raw_previous_track_status"] == "possible_occlusion"]
    visible = [row for row in comparison if row["reviewed_box_present"]]
    false_holds = [row for row in visible if row["raw_previous_track_status"] == "possible_occlusion"]
    warning_frames = []
    visible_risk = []
    lookup = {(row["frame_index"], row["player_id"]): row for row in comparison}
    for row in visible:
        next_row = lookup.get((row["frame_index"] + 1, row["player_id"]))
        if next_row is None:
            continue
        raw_status = flags[row["frame_index"]].get(row["reviewed_track_id"], {}).get("status")
        visible_risk.append({"frame_index": row["frame_index"], "player_id": row["player_id"],
                             "risk": raw_status in ("approaching_overlap", "overlap_risk"),
                             "next_reviewed_box_missing": not next_row["reviewed_box_present"]})
    for row in comparison:
        if row["reviewed_box_present"]:
            continue
        frame, player = row["frame_index"], row["player_id"]
        if any(prior["player_id"] == player and prior["frame_index"] == frame - 1
               and not prior["reviewed_box_present"] for prior in comparison):
            continue
        previous = next((prior for prior in comparison
                         if prior["player_id"] == player and prior["frame_index"] == frame - 1), None)
        if previous is None or previous["reviewed_track_id"] is None:
            continue
        raw_status = flags[frame - 1].get(previous["reviewed_track_id"], {}).get("status")
        warning_frames.append({"frame_index": frame, "player_id": player,
                               "previous_frame_risk": raw_status in
                               ("approaching_overlap", "overlap_risk"),
                               "previous_frame_status": raw_status})
    result = {"window": name,
              "raw_rule": "All ByteTrack person boxes; no reviewed labels used to generate flags. A vanished track is held as possible occlusion for up to eight frames if its last box overlaps another current box by at least 15% of the smaller area. No identity or position is assigned.",
              "reviewed_missing_slots": len(missing),
              "missing_slots_with_raw_possible_occlusion": len(held_missing),
              "reviewed_visible_slots": len(visible),
              "visible_slots_with_false_raw_hold_of_previous_id": len(false_holds),
              "gap_onsets_with_prior_box": len(warning_frames),
              "gap_onsets_with_prior_frame_risk": sum(item["previous_frame_risk"] for item in warning_frames),
              "visible_player_frames_with_next_frame": len(visible_risk),
              "visible_player_frames_with_risk": sum(item["risk"] for item in visible_risk),
              "risk_frames_followed_by_missing_box": sum(
                  item["risk"] and item["next_reviewed_box_missing"] for item in visible_risk),
              "risk_frames_followed_by_visible_box": sum(
                  item["risk"] and not item["next_reviewed_box_missing"] for item in visible_risk),
              "gap_onsets": warning_frames,
              "raw_flagged_missing_slots": held_missing,
              "raw_false_hold_visible_slots": false_holds,
              "limitation": "Reviewed unassigned boxes are not verified visual occlusions or detector misses. A held old ByteTrack ID may describe the same visible player after an ID switch. This is an exploratory same-match check, not precision/recall against occlusion ground truth."}
    (window / "automatic_crossing_test.json").write_text(json.dumps(result, indent=2) + "\n")
    with (window / "automatic_crossing_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = list(comparison[0])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(comparison)
    return result


def main():
    for name in WINDOWS:
        result = evaluate(name)
        print(name, {key: value for key, value in result.items()
                     if isinstance(value, int)})


if __name__ == "__main__":
    main()
