"""Build a source-only single-reviewer intake for the S3 P34 diagnostic span.

The blank intake is for a human reviewer. This audit never promotes unsampled
candidate boxes to grounded positions or grants a strict metric result.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = BASE / "s3p34_30fps_ground_review"
LEDGER = BASE / "s3p34_six_player_observation_ledger.json"
MANIFEST = PACK / "manifest.json"
AUDIT = PACK / "audit.json"
BLANK = PACK / "single_reviewer_unsampled_blank.csv"
JERSEYS = ("28", "12", "15", "7", "19", "21")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert manifest["interval_inclusive"] == [36066, 36102]
    assert manifest["source_video_sha256"] == ledger["source_sha256"]
    assert len(manifest["frames"]) == 37 and len(manifest["sheets"]) == 10
    for row in manifest["frames"]:
        assert digest(PACK / row["image"]) == row["sha256"]
    by_frame = {row["source_frame"]: row for row in ledger["frames"]}
    sampled, unsampled = [], []
    for row in manifest["frames"]:
        frame = row["frame"]
        observation = by_frame[frame]
        assert observation["six_candidate_boxes"]
        assert set(observation["players"]) == set(JERSEYS)
        if observation["six_reviewed_ground_positions"]:
            assert all(observation["players"][j]["source_reviewed_ground_court_m"] is not None for j in JERSEYS)
            sampled.append(frame)
        else:
            assert all(observation["players"][j]["source_reviewed_ground_court_m"] is None for j in JERSEYS)
            unsampled.append(frame)
    assert sampled == [36066, 36072, 36078, 36084, 36090, 36096, 36102]
    assert len(unsampled) == 30
    with BLANK.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "source_frame", "jersey", "unboxed_image", "image_sha256", "identity_status",
            "ground_status", "shoe_midpoint_x_px", "shoe_midpoint_y_px",
            "reading_uncertainty_px", "paired_sheet_after_unboxed_review",
            "candidate_alignment", "proxy_floor_alignment", "notes",
        ])
        writer.writeheader()
        for frame in unsampled:
            image = next(row for row in manifest["frames"] if row["frame"] == frame)
            for jersey in JERSEYS:
                writer.writerow({
                    "source_frame": frame, "jersey": jersey,
                    "unboxed_image": image["image"], "image_sha256": image["sha256"],
                    "identity_status": "", "ground_status": "",
                    "shoe_midpoint_x_px": "", "shoe_midpoint_y_px": "",
                    "reading_uncertainty_px": "",
                    "paired_sheet_after_unboxed_review": "../s3p34_full_span_review/"
                    + observation["players"][jersey]["source_review_page"],
                    "candidate_alignment": "", "proxy_floor_alignment": "", "notes": "",
                })
    output = {
        "status": "human_single_reviewer_verdicts_pending",
        "interval_inclusive": [36066, 36102],
        "interval_source_frames": 37,
        "sampled_frames_with_six_existing_reviewed_ground_points": sampled,
        "sampled_reviewed_ground_slots": 42,
        "intervening_frames_without_ground_verdict": unsampled,
        "intervening_slots_without_ground_verdict": len(unsampled) * 6,
        "candidate_boxes_on_all_interval_frames": True,
        "unboxed_contact_sheets_visually_screened_by_ai": 10,
        "new_ground_points_accepted_by_this_audit": 0,
        "human_intake_csv": BLANK.name,
        "manifest_sha256": digest(MANIFEST),
        "observation_ledger_sha256": digest(LEDGER),
        "reason_not_strict": "Availability-selected diagnostic segment; 180 slots lack human ground review, calibration and fixed-window approval remain unresolved.",
    }
    AUDIT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {BLANK.relative_to(ROOT)} ({len(unsampled) * 6} rows)")
    print(f"Wrote {AUDIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
