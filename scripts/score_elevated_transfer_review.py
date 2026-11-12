"""Score the source-reviewed six-slot transfer grid, preserving incomplete cases."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from elevated_transfer_identity_exceptions import unresolved_swap


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/source_view_screen"
PACK = BASE / "elevated_transfer_review"
SELECTION = BASE / "transfer_source_only_selection_2026-11-06_v2.json"


def score(case: dict) -> dict:
    match_id = case["match_id"]
    suggestions = json.loads((PACK / f"{match_id}_suggestions.json").read_text(encoding="utf-8"))
    draft_path = PACK / f"{match_id}_review_draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8")) if draft_path.exists() else {"frames": {}}
    expected_frames = [row["excerpt_frame"] for row in suggestions["rows"]]
    observed = draft["frames"]
    unexpected = set(observed) - {str(frame) for frame in expected_frames}
    if unexpected:
        raise ValueError(f"Unexpected frames in {match_id}: {sorted(unexpected)}")
    counts = Counter()
    states = Counter()
    reasons = Counter()
    reviewed_frames = 0
    six_box_frames = 0
    six_grounded_proxy_frames = 0
    for frame in expected_frames:
        entry = observed.get(str(frame))
        if entry is None:
            continue
        rows = entry["rows"]
        if sorted(row["slot"] for row in rows) != list(range(1, 7)):
            raise ValueError(f"Invalid six-slot review in {match_id} frame {frame}")
        reviewed_frames += 1
        frame_matched = 0
        frame_grounded = 0
        for row in rows:
            conflict = unresolved_swap(match_id, frame, row)
            counts["reviewed_player_slots"] += 1
            states[row["physical_state"]] += 1
            counts["source_visible"] += row["physical_state"] != "not_visible"
            counts["identity_digit_confirmed"] += row["identity_status"] == "digit_confirmed" and not conflict
            counts["identity_sequence_consistent"] += row["identity_status"] == "sequence_consistent" and not conflict
            counts["candidate_selected"] += row["candidate_raw_track_id"] is not None
            counts["identity_exception_unresolved"] += conflict
            matched = row["box_alignment"] == "same_player" and not conflict
            counts["same_player_box"] += matched
            frame_matched += matched
            grounded = (matched and row["physical_state"] == "grounded"
                        and row["floor_alignment"] == "plausible"
                        and row["identity_status"] in ("digit_confirmed", "sequence_consistent"))
            counts["source_reviewed_plausible_grounded_proxy"] += grounded
            frame_grounded += grounded
            if conflict:
                reasons["identity:source_reviewed_swap_unresolved"] += 1
            elif not matched:
                reasons[f"box:{row['box_alignment']}"] += 1
            if row["physical_state"] != "grounded":
                reasons[f"state:{row['physical_state']}"] += 1
            elif row["floor_alignment"] != "plausible":
                reasons[f"floor:{row['floor_alignment']}"] += 1
        six_box_frames += frame_matched == 6
        six_grounded_proxy_frames += frame_grounded == 6
    return {
        "match_id": match_id,
        "status": "complete_single_reviewer" if reviewed_frames == len(expected_frames) else "partial_review",
        "expected_grid_frames": len(expected_frames),
        "reviewed_grid_frames": reviewed_frames,
        "expected_player_slots": 6 * len(expected_frames),
        "reviewed_player_slots": counts["reviewed_player_slots"],
        "slot_counts": dict(counts),
        "physical_states": dict(states),
        "gap_reasons": dict(reasons),
        "all_six_same_player_box_frames": six_box_frames,
        "all_six_plausible_grounded_proxy_frames": six_grounded_proxy_frames,
        "limitations": [
            "Single-reviewer unblinded source and box judgments.",
            "Grid samples are 5 Hz; intervening source frames have no source review.",
            "Plausible box bottoms are not independent shoe-position accuracy measurements.",
            "Court calibration and exact full-video frame alignment are separate gates.",
        ],
    }


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    results = [score(case) for case in selection["cases"]]
    out = PACK / "review_progress_result.json"
    out.write_text(json.dumps({"cases": results}, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result['match_id']}: {result['reviewed_grid_frames']}/"
              f"{result['expected_grid_frames']} source frames reviewed; "
              f"{result['all_six_same_player_box_frames']} six-box frames; "
              f"{result['all_six_plausible_grounded_proxy_frames']} six-grounded-proxy frames")


if __name__ == "__main__":
    main()
