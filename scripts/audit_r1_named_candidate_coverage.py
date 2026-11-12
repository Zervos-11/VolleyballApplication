"""Measure six-slot candidate coverage against the isolated API track output."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_end_to_end_pilot"
VISUAL = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_six_slot_visual_candidate.json"
PLAYERS = ("9", "10", "11", "12", "13", "20")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runs(frames: list[int]) -> list[list[int]]:
    result = []
    for frame in frames:
        if result and frame == result[-1][1] + 1:
            result[-1][1] = frame
        else:
            result.append([frame, frame])
    return result


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    api = {}
    with (BASE / "tracks_centroids.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            api[int(row["frame"]), int(row["track_id"])] = (float(row["cx"]), float(row["cy"]))
    records = visual["frame_records"]
    if [row["frame"] for row in records] != list(range(21050, 21464)):
        raise AssertionError("Six-slot candidate does not cover the pilot interval")
    counts = {str(n): 0 for n in range(7)}
    player_results, deltas, unmatched = {}, [], []
    for player in PLAYERS:
        states = [(row["frame"], row["players"][player]) for row in records]
        valid = [(frame, state) for frame, state in states if state["box_status"] == "raw_box_candidate"]
        unknown = [frame for frame, state in states if state["box_status"] != "raw_box_candidate"]
        for frame, state in valid:
            box = state["bbox_px"]
            reference = api.get((frame, state["raw_track_id"]))
            if reference is None:
                unmatched.append([player, frame, "track_id_missing"])
            else:
                deltas.append(float(np.hypot(reference[0] - (box[0] + box[2]) / 2,
                                             reference[1] - box[3])))
        player_results[player] = {
            "candidate_box_frames": len(valid),
            "candidate_box_percent": round(100 * len(valid) / len(records), 1),
            "missing_or_invalid_box_frames": len(unknown),
            "missing_or_invalid_runs_inclusive": runs(unknown),
            "court_position_frames": sum(state["court_position_m"] is not None for _, state in states),
        }
    for row in records:
        count = sum(row["players"][player]["box_status"] == "raw_box_candidate" for player in PLAYERS)
        counts[str(count)] += 1
    result = {
        "status": "development_candidate_coverage_not_accuracy",
        "visual_candidate_sha256": sha256(VISUAL),
        "api_tracks_sha256": sha256(BASE / "tracks_centroids.csv"),
        "interval_frames": [21050, 21464],
        "source_frames": len(records),
        "players": player_results,
        "frames_by_valid_candidate_box_count": counts,
        "candidate_to_api_unmatched": unmatched,
        "paired_candidate_boxes": len(deltas),
        "candidate_vs_api_bottom_centre_delta_px_max": round(max(deltas), 4) if deltas else None,
        "interpretation": "Named slots are a conservatively mapped visual candidate from the same raw tracker output. Box coverage is not player visibility, identity accuracy, or validated ground-position coverage. All court positions remain null.",
    }
    (BASE / "NAMED_CANDIDATE_COVERAGE.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{counts['6']}/414 frames with six candidate boxes; {len(deltas)} API-linked boxes; "
          f"{len(unmatched)} unmatched")


if __name__ == "__main__":
    main()
