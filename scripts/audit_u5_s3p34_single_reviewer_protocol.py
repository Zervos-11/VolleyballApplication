"""Summarise the frozen S3 P34 manual reference by review timing.

This script reads existing annotations. It never edits manual QC or grants a
strict team-metric approval.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/matches/yt_u5HnY2aNW14/screening/full_rally_live_reference_audit.json"
OUTPUT = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_single_reviewer_protocol_audit.json"
GROUPS = {
    "pre_comparison_unboxed": (36066, 36078),
    "post_comparison_unblinded": (36036, 36096, 36138),
}


def summary(frames: list[dict]) -> dict:
    errors = [float(row["court_position_difference_m"]) for frame in frames for row in frame["rows"]]
    return {
        "source_frames": [frame["source_frame"] for frame in frames],
        "team_frames": len(frames),
        "player_pairs": len(errors),
        "median_player_discrepancy_m": round(statistics.median(errors), 4),
        "maximum_observed_player_discrepancy_m": round(max(errors), 3),
        "frame_metric_differences": [
            {"source_frame": frame["source_frame"], **frame["proxy_minus_manual_team_metric"]}
            for frame in frames
        ],
    }


def main() -> None:
    raw = SOURCE.read_bytes()
    data = json.loads(raw)
    by_frame = {frame["source_frame"]: frame for frame in data["frames"]}
    assert len(by_frame) == 5 and all(len(frame["rows"]) == 6 for frame in by_frame.values())
    assert set(by_frame) == set().union(*map(set, GROUPS.values()))
    result = {
        "source_sha256": data["source_sha256"],
        "reference_audit_sha256": hashlib.sha256(raw).hexdigest(),
        "protocol": "single_reviewer_retrospective_timing_stratification",
        "strict_full_rally_validation": False,
        "groups": {
            name: summary([by_frame[number] for number in numbers])
            for name, numbers in GROUPS.items()
        },
        "all_selected_frames": summary(list(data["frames"])),
        "interpretation": (
            "Pre-comparison unboxed marks are the primary internal positional check. "
            "Later unblinded marks are supplementary. Neither group is an independent "
            "observer reference, a population error bound, or full-rally ground truth."
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    for name, group in result["groups"].items():
        print(name, group["player_pairs"], group["median_player_discrepancy_m"], group["maximum_observed_player_discrepancy_m"])


if __name__ == "__main__":
    main()
