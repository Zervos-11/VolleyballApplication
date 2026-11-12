"""Check a completed single-reviewer ground-status form without granting approval."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = BASE / "s3p34_30fps_ground_review"
BLANK = PACK / "single_reviewer_unsampled_blank.csv"
COMPLETED = PACK / "single_reviewer_unsampled_completed.csv"
OUTPUT = PACK / "single_reviewer_score.json"
JERSEYS = ("28", "12", "15", "7", "19", "21")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    reference = rows(BLANK)
    assert len(reference) == 180
    result: dict = {
        "status": "awaiting_single_reviewer_completed_form",
        "blank_sha256": sha256(BLANK),
        "required_slots": 180,
        "strict_metric_approval": False,
    }
    if COMPLETED.exists():
        completed = rows(COMPLETED)
        assert len(completed) == len(reference)
        accepted = []
        exceptions = []
        by_frame = {}
        for expected, actual in zip(reference, completed, strict=True):
            for key in ("source_frame", "jersey", "unboxed_image", "image_sha256", "paired_sheet_after_unboxed_review"):
                assert actual[key] == expected[key], f"Frozen field mismatch at {key}"
            assert actual["jersey"] in JERSEYS
            assert sha256(PACK / actual["unboxed_image"]) == actual["image_sha256"]
            assert actual["identity_status"] in ("confirmed", "sequence_only", "uncertain")
            assert actual["ground_status"] in ("grounded", "airborne", "occluded", "uncertain")
            assert actual["candidate_alignment"] in ("same_player", "wrong_player", "uncertain")
            assert actual["proxy_floor_alignment"] in ("plausible", "implausible", "uncertain")
            x, y = actual["shoe_midpoint_x_px"], actual["shoe_midpoint_y_px"]
            if x or y:
                assert x and y and actual["ground_status"] == "grounded"
                assert 0 <= float(x) < 1280 and 0 <= float(y) < 720
                assert actual["reading_uncertainty_px"] and float(actual["reading_uncertainty_px"]) >= 0
            else:
                assert not actual["reading_uncertainty_px"]
            good = (actual["identity_status"] != "uncertain"
                    and actual["ground_status"] == "grounded"
                    and actual["candidate_alignment"] == "same_player"
                    and actual["proxy_floor_alignment"] == "plausible")
            key = [int(actual["source_frame"]), actual["jersey"]]
            by_frame.setdefault(key[0], []).append(good)
            if good:
                accepted.append(key)
            else:
                exceptions.append({"frame": key[0], "jersey": key[1],
                                   "identity_status": actual["identity_status"],
                                   "ground_status": actual["ground_status"],
                                   "candidate_alignment": actual["candidate_alignment"],
                                   "proxy_floor_alignment": actual["proxy_floor_alignment"]})
        result.update({
            "status": "single_reviewer_form_scored_not_strict_approval",
            "completed_sha256": sha256(COMPLETED),
            "accepted_intervening_slots": len(accepted),
            "intervening_frames_with_six_accepted_slots": sum(all(flags) for flags in by_frame.values()),
            "exceptions": exceptions,
            "interpretation": "Single-reviewer verdicts require documented provenance; the selected segment remains diagnostic, and calibration/window gates are separate.",
        })
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
