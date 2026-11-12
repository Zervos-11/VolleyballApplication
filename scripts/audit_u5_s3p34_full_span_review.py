"""Audit completeness and internal consistency of S3 P34 frame/jersey review.

This checks annotations; it cannot establish that a human visual verdict is right.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = (ROOT / "data/matches/yt_u5HnY2aNW14/screening/"
           "s3p34_full_span_review/frame_player_review_template.csv")
JERSEYS = ("28", "12", "15", "7", "19", "21")
STATUSES = {
    "grounded_usable_box", "visible_unboxed", "airborne",
    "occluded", "off_screen", "uncertain",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, default=DEFAULT)
    args = parser.parse_args()
    with args.review.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(frame, jersey) for frame in range(36001, 36139)
                for jersey in JERSEYS}
    keys = [(int(row["source_frame"]), row["jersey"]) for row in rows]
    assert len(rows) == len(expected) == 828, "Expected 828 frame/jersey rows"
    assert len(keys) == len(set(keys)) and set(keys) == expected, (
        "Duplicate or missing frame/jersey row")
    errors = []
    counts = Counter()
    for row in rows:
        frame, jersey = int(row["source_frame"]), row["jersey"]
        status = row["new_source_review_status"].strip()
        present = row["candidate_present"].strip().lower() == "true"
        counts[status or "unreviewed"] += 1
        if status and status not in STATUSES:
            errors.append(f"{frame} #{jersey}: invalid status {status!r}")
        if status == "grounded_usable_box" and not present:
            errors.append(f"{frame} #{jersey}: usable box status but no candidate")
        if status == "visible_unboxed" and present:
            errors.append(f"{frame} #{jersey}: visible_unboxed but candidate present")
        if status == "grounded_usable_box" and (
                not row["candidate_x_m"] or not row["candidate_y_m"]):
            errors.append(f"{frame} #{jersey}: usable box lacks court coordinates")
    per_frame = {frame: [row for row in rows
                         if int(row["source_frame"]) == frame]
                 for frame in range(36001, 36139)}
    all_six_reviewed = sum(all(r["new_source_review_status"].strip()
                               for r in frame_rows)
                           for frame_rows in per_frame.values())
    all_six_grounded = sum(all(r["new_source_review_status"].strip()
                               == "grounded_usable_box"
                               for r in frame_rows)
                           for frame_rows in per_frame.values())
    result = {
        "status": "annotation_consistency_only_not_scientific_validation",
        "review_file": str(args.review),
        "frame_player_slots": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "frames_with_six_new_verdicts": all_six_reviewed,
        "frames_with_six_reviewed_grounded_boxes": all_six_grounded,
        "internal_errors": errors[:30],
        "error_count": len(errors),
        "ready_for_separate_calibration_boundary_and_reference_review": (
            counts["unreviewed"] == 0 and not errors),
    }
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
