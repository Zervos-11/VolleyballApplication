"""Compare reviewed box bottoms with selected manual shoe points per camera."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path

import numpy as np

from elevated_transfer_identity_exceptions import unresolved_swap


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/source_view_screen"
PACK = BASE / "elevated_transfer_review"
SELECTION = BASE / "transfer_source_only_selection_2026-11-06_v2.json"
REFERENCE_PLAN = PACK / "position_reference_plan_2026-11-06_v2.json"


def project(h: np.ndarray, x: float, y: float) -> tuple[float, float]:
    v = h @ np.array([x, y, 1.0])
    if abs(v[2]) < 1e-12:
        raise ValueError("Point maps to infinity")
    return float(v[0] / v[2]), float(v[1] / v[2])


def analyze(case: dict) -> dict:
    match_id = case["match_id"]
    plan = json.loads(REFERENCE_PLAN.read_text(encoding="utf-8"))
    planned_frames = next(row["reference_excerpt_frames"] for row in plan["cases"]
                          if row["match_id"] == match_id)
    progress_path = PACK / f"{match_id}_review_draft.json"
    calibration_path = PACK / f"{match_id}_calibration_draft.json"
    reference_path = PACK / f"{match_id}_position_reference_draft.json"
    status = {
        "player_grid_review": progress_path.exists(),
        "court_calibration": calibration_path.exists(),
        "manual_reference": reference_path.exists(),
    }
    result = {"match_id": match_id, "status": "pending_inputs", "inputs_present": status,
              "matched_grounded_pairs": 0, "planned_reference_frames": planned_frames,
              "reviewed_reference_frames": 0,
              "planned_reference_slots": 6 * len(planned_frames),
              "discrepancies_m": [], "median_discrepancy_m": None,
              "largest_observed_discrepancy_m": None}
    if not all(status.values()):
        return result
    grid = json.loads(progress_path.read_text(encoding="utf-8"))
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    unexpected_frames = set(reference["frames"]) - {str(frame) for frame in planned_frames}
    if unexpected_frames:
        raise ValueError(f"Unexpected reference frames for {match_id}: {sorted(unexpected_frames)}")
    result["reviewed_reference_frames"] = len(reference["frames"])
    h_values = calibration["check"].get("homography_image_to_court")
    if h_values is None:
        result["status"] = "court_transform_unavailable"
        return result
    h = np.asarray(h_values, dtype=float)
    candidates = json.loads((BASE / f"{match_id}_raw_5hz_candidates.json")
                            .read_text(encoding="utf-8"))
    candidate_by_frame = {row["excerpt_frame"]: row for row in candidates["rows"]}
    distances = []
    exclusions = {}
    floor_verdicts = Counter()
    for frame_str, entry in reference["frames"].items():
        frame = int(frame_str)
        grid_entry = grid["frames"].get(frame_str)
        proposals = {p["raw_track_id"]: p for p in candidate_by_frame[frame]["proposals"]}
        for manual in entry["rows"]:
            slot = manual["slot"]
            if manual["state"] != "grounded":
                exclusions[f"manual_{manual['state']}"] = exclusions.get(f"manual_{manual['state']}", 0) + 1
                continue
            if grid_entry is None:
                exclusions["grid_not_reviewed"] = exclusions.get("grid_not_reviewed", 0) + 1
                continue
            reviewed = next(row for row in grid_entry["rows"] if row["slot"] == slot)
            if reviewed["physical_state"] != "grounded":
                exclusions["source_state_not_grounded"] = exclusions.get("source_state_not_grounded", 0) + 1
                continue
            if unresolved_swap(match_id, frame, reviewed):
                exclusions["identity_swap_unresolved"] = exclusions.get("identity_swap_unresolved", 0) + 1
                continue
            if reviewed["identity_status"] not in ("digit_confirmed", "sequence_consistent"):
                exclusions["identity_uncertain"] = exclusions.get("identity_uncertain", 0) + 1
                continue
            if reviewed["box_alignment"] != "same_player":
                exclusions["no_same_player_box"] = exclusions.get("no_same_player_box", 0) + 1
                continue
            proposal = proposals.get(reviewed["candidate_raw_track_id"])
            if proposal is None:
                raise ValueError(f"Saved candidate missing in {match_id} frame {frame}")
            x1, _, x2, y2 = proposal["bbox_px"]
            proxy_court = project(h, (x1 + x2) / 2, y2)
            manual_court = project(h, manual["shoe_x_px"], manual["shoe_y_px"])
            distance = math.dist(proxy_court, manual_court)
            distances.append(distance)
            floor_verdicts[reviewed["floor_alignment"]] += 1
            result["discrepancies_m"].append({"excerpt_frame": frame, "slot": slot,
                                               "distance_m": round(distance, 4),
                                               "source_floor_verdict": reviewed["floor_alignment"]})
    expected_grid = json.loads((PACK / f"{match_id}_suggestions.json").read_text(encoding="utf-8"))
    grid_complete = len(grid["frames"]) == len(expected_grid["rows"])
    result["status"] = ("complete_selected_single_reviewer_comparison"
                        if len(reference["frames"]) == len(planned_frames) and grid_complete
                        else "partial_selected_single_reviewer_comparison")
    result["matched_grounded_pairs"] = len(distances)
    result["exclusions"] = exclusions
    result["matched_source_floor_verdicts"] = dict(floor_verdicts)
    if distances:
        result["median_discrepancy_m"] = round(statistics.median(distances), 4)
        result["largest_observed_discrepancy_m"] = round(max(distances), 4)
    result["limitations"] = [
        "Time-stratified selected frames, not a random player-position sample.",
        "Single-reviewer unblinded shoe marks and source box decisions.",
        "Four-corner staged court transform with separately reported held-out line error.",
        "A manual grounded shoe mark permits a diagnostic proxy error comparison even when the source box-floor verdict was uncertain; it does not approve that proxy for strict team metrics.",
        "The observed largest discrepancy is not a guaranteed error bound.",
    ]
    return result


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    results = [analyze(case) for case in selection["cases"]]
    out = PACK / "position_reference_progress_result.json"
    out.write_text(json.dumps({"cases": results}, indent=2) + "\n", encoding="utf-8")
    for row in results:
        print(f"{row['match_id']}: {row['status']}, {row['matched_grounded_pairs']}/18 matched grounded pairs")


if __name__ == "__main__":
    main()
