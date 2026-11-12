"""Score a visually reviewed player path over 101 consecutive source frames."""

import csv
import json
from pathlib import Path

import cv2

from evaluate_identity_cues import assign_ids, colour_distance, extract_observations
from evaluate_pilot_tracker import image_to_court, in_target_region, iou, project


MATCH = Path("data/matches/yt_FqE5pTJqx8g")
OUT = Path("data/processed/pilot_tracker_evaluation/dense_identity_window_r4")


def segments(rows):
    output = []
    for row in rows:
        key = row["assigned_id"]
        if output and output[-1]["assigned_id"] == key and row["frame_index"] == output[-1]["end_frame"] + 1:
            output[-1]["end_frame"] = row["frame_index"]
        else:
            output.append({"start_frame": row["frame_index"],
                           "end_frame": row["frame_index"], "assigned_id": key})
    return output


def duplicate_track_aliases(observations):
    """Merge IDs with repeated near-identical simultaneous boxes, conservatively."""
    evidence = {}
    for frame, people in observations.items():
        for index, first in enumerate(people):
            for second in people[index + 1:]:
                id_a = first["prediction"]["track_id"]
                id_b = second["prediction"]["track_id"]
                if id_a < 0 or id_b < 0 or id_a == id_b:
                    continue
                pair = tuple(sorted((id_a, id_b)))
                overlap = iou(first["prediction"]["bbox"], second["prediction"]["bbox"])
                colour = colour_distance(first["jersey"], second["jersey"])
                evidence.setdefault(pair, []).append((frame, overlap, colour))
    accepted = []
    for pair, samples in evidence.items():
        strong = [(frame, overlap, colour) for frame, overlap, colour in samples
                  if overlap >= .60 and (colour is None or colour <= .55)]
        consecutive = any(b[0] == a[0] + 1 for a, b in zip(strong, strong[1:]))
        apart = any(overlap < .30 for _, overlap, _ in samples)
        if len(strong) >= 2 and consecutive and not apart:
            accepted.append({"ids": list(pair), "support_frames": [frame for frame, _, _ in strong],
                             "max_jersey_distance": max((colour for _, _, colour in strong
                                                          if colour is not None), default=None)})
    parent = {}
    def root(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            key = parent[key]
        return key
    for merge in accepted:
        a, b = merge["ids"]
        parent[root(b)] = root(a)
    return {key: root(key) for key in parent}, accepted


def main():
    dense = json.loads((OUT / "tracker_predictions.json").read_text())
    calibration = json.loads((MATCH / "pilot/calibration/camera_r2_r5.json").read_text())
    matrix = image_to_court(calibration)
    with (OUT / "player13_assisted_path.csv").open(newline="", encoding="utf-8") as stream:
        reference = list(csv.DictReader(stream))
    predictions = {}
    for frame, people in dense["predictions"].items():
        kept = []
        for pred in people:
            box = pred["bbox"]
            position = project([(box[0] + box[2]) / 2, box[3]], matrix)
            if in_target_region(position, False):
                kept.append(pred)
        predictions[frame] = kept
    video = cv2.VideoCapture(str(MATCH / "source_FqE5pTJqx8g.mp4"))
    try:
        observations = extract_observations(
            video, "r4", {"frames": {frame: {} for frame in predictions}},
            {"predictions": predictions}, matrix)
    finally:
        video.release()
    aliases, merge_evidence = duplicate_track_aliases(observations)
    methods = {"byte_track": None,
               "byte_track_duplicate_merge": "duplicate",
               "motion_strict": (False, False, 0.0),
               "motion_jersey_strict": (True, False, 0.0),
               "motion_jersey_shoe_strict": (True, True, 0.0),
               "motion_jersey_noise_0_5m": (True, False, 0.5),
               "motion_jersey_shoe_noise_0_5m": (True, True, 0.5)}
    output = {"rally_id": "r4", "player_id": "13", "first_frame": 150190,
              "last_frame": 150290, "source_fps": 50,
              "reference_note": "Visual review of all 101 source-frame crops confirmed the same jersey #13. One frame has no detector box. Reference detection selection used three saved label boxes and interpolation; not a six-player MOT benchmark.",
              "measurement_note": "Strict gate is 5m/s (0.1m per adjacent source frame); noise variants add 0.5m allowance for bottom-centre footpoint jitter.",
              "duplicate_merge_note": "Merge different ByteTrack IDs only when their boxes overlap >=0.60 on at least two consecutive frames, torso colours agree, and no simultaneous separated boxes contradict the merge. Exploratory window-specific rule.",
              "duplicate_merge_evidence": merge_evidence,
              "methods": {}}
    assignment_rows = []
    for method, parameters in methods.items():
        if parameters is None or parameters == "duplicate":
            assigned = {frame: [item["prediction"]["track_id"] for item in people]
                        for frame, people in observations.items()}
            if parameters == "duplicate":
                assigned = {frame: [aliases.get(key, key) for key in ids]
                            for frame, ids in assigned.items()}
        else:
            assigned = assign_ids(observations, *parameters)
        track_rows = []
        for row in reference:
            if not row["candidate_box"]:
                continue
            frame = int(row["frame_index"])
            box = json.loads(row["candidate_box"])
            index = next((i for i, item in enumerate(observations[frame])
                          if item["prediction"]["bbox"] == box), None)
            if index is None:
                raise RuntimeError(f"Selected player detection missing from target region at {frame}")
            track_rows.append({"method": method, "frame_index": frame,
                               "assigned_id": assigned[frame][index],
                               "byte_track_id": observations[frame][index]["prediction"]["track_id"]})
        changes = sum(a["assigned_id"] != b["assigned_id"]
                      for a, b in zip(track_rows, track_rows[1:]))
        result = {"observed_frames": len(track_rows),
                  "observed_pairs": max(0, len(track_rows) - 1),
                  "identity_changes": changes,
                  "distinct_assigned_ids": len({row["assigned_id"] for row in track_rows}),
                  "segments": segments(track_rows)}
        output["methods"][method] = result
        assignment_rows.extend(track_rows)
    (OUT / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    with (OUT / "player13_identity_assignments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(assignment_rows[0]))
        writer.writeheader()
        writer.writerows(assignment_rows)
    print(json.dumps({method: {key: result[key] for key in
                       ("observed_frames", "identity_changes", "distinct_assigned_ids")}
                      for method, result in output["methods"].items()}, indent=2))


if __name__ == "__main__":
    main()
