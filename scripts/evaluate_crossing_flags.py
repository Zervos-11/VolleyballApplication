"""Flag possible player occlusions in the visually reviewed dense windows.

This is a diagnostic on reviewed paths, not a tracker identity correction.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path("data/processed/pilot_tracker_evaluation")
WINDOWS = {
    "r4": ROOT / "dense_identity_window_r4/full_team_150240_150290",
    "r2": ROOT / "dense_identity_validation_r2",
}
MAX_HOLD_FRAMES = 8
MIN_OVERLAP_OF_SMALLER = 0.15


def overlap_of_smaller(a, b):
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    smaller = min((a[2] - a[0]) * (a[3] - a[1]),
                  (b[2] - b[0]) * (b[3] - b[1]))
    return width * height / smaller if smaller > 0 else 0.0


def forecast_overlap(frame, player, box, other, other_box, last_seen):
    first = last_seen.get(player)
    second = last_seen.get(other)
    if first is None or second is None or first[0] != frame - 1 or second[0] != frame - 1:
        return 0.0
    velocity_a = [box[index] - first[1][index] for index in range(4)]
    velocity_b = [other_box[index] - second[1][index] for index in range(4)]
    return max(overlap_of_smaller(
        [box[index] + step * velocity_a[index] for index in range(4)],
        [other_box[index] + step * velocity_b[index] for index in range(4)])
        for step in range(1, 4))


def evaluate(window):
    with (window / "assisted_paths.csv").open(newline="", encoding="utf-8") as stream:
        source = list(csv.DictReader(stream))
    review = json.loads((window / "visual_review.json").read_text())
    selected = sum(bool(row["candidate_box"]) for row in source)
    if selected != review["selected_detection_identities_confirmed"]:
        raise ValueError(f"Visual review no longer matches {window}")
    by_frame = defaultdict(dict)
    for row in source:
        by_frame[int(row["frame_index"])][row["player_id"]] = (
            json.loads(row["candidate_box"]) if row["candidate_box"] else None)
    players = sorted(next(iter(by_frame.values())))
    last_seen = {}
    output = []
    for frame, boxes in sorted(by_frame.items()):
        previous_seen = last_seen.copy()
        for player in players:
            box = boxes[player]
            other_boxes = [(other, candidate) for other, candidate in boxes.items()
                           if other != player and candidate is not None]
            if box is not None:
                partners = [(other, round(overlap_of_smaller(box, candidate), 4))
                            for other, candidate in other_boxes
                            if overlap_of_smaller(box, candidate) >= MIN_OVERLAP_OF_SMALLER]
                approaching = [(other, round(forecast_overlap(
                    frame, player, box, other, candidate, previous_seen), 4))
                    for other, candidate in other_boxes
                    if overlap_of_smaller(box, candidate) < MIN_OVERLAP_OF_SMALLER
                    and forecast_overlap(frame, player, box, other, candidate, previous_seen)
                    >= MIN_OVERLAP_OF_SMALLER]
                status = ("overlap_risk" if partners else
                          "approaching_overlap" if approaching else "visible_clear")
                if not partners:
                    partners = approaching
                last_seen[player] = (frame, box)
            else:
                previous = last_seen.get(player)
                age = frame - previous[0] if previous else None
                partners = ([(other, round(overlap_of_smaller(previous[1], candidate), 4))
                             for other, candidate in other_boxes
                             if overlap_of_smaller(previous[1], candidate) >= MIN_OVERLAP_OF_SMALLER]
                            if age is not None and age <= MAX_HOLD_FRAMES else [])
                status = "possible_occlusion" if partners else "unassigned_unknown"
            output.append({"frame_index": frame, "player_id": player,
                           "status": status,
                           "other_player_ids": ";".join(other for other, _ in partners),
                           "largest_overlap_fraction": max((value for _, value in partners), default=0),
                           "frames_since_seen": (age if box is None else 0) or 0})
    with (window / "crossing_flags.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    counts = {status: sum(row["status"] == status for row in output)
              for status in ("visible_clear", "approaching_overlap", "overlap_risk",
                             "possible_occlusion", "unassigned_unknown")}
    result = {"window": str(window), "player_frames": len(output),
              "rule": {"overlap_fraction_of_smaller_box": MIN_OVERLAP_OF_SMALLER,
                       "maximum_missing_frames": MAX_HOLD_FRAMES},
              "counts": counts,
              "possible_occlusion_events": [row for row in output
                                            if row["status"] == "possible_occlusion"],
              "interpretation": "Approaching overlap extrapolates two visible boxes by three frames using their last frame of motion. Possible occlusion is an uncertain flag, not proof that the player is hidden. No box or track ID is assigned. Flags use visually reviewed player paths and are not a deployable tracker score."}
    (window / "crossing_flag_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    for name, window in WINDOWS.items():
        result = evaluate(window)
        print(name, result["counts"])


if __name__ == "__main__":
    main()
