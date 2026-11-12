"""Build bounded, source-reviewed distance estimates for the AoEP slice."""

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
SOURCE = DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.json"
OUTPUT = DIR / "reviewed_distance_estimate_75180_75229.json"
PLAYERS = {
    "yellow_centre_4": ["player4_source_qc_75180_75204.jpg", "player4_source_qc_75205_75229.jpg"],
    "navy_libero_10": ["libero_source_qc_75180_75204.jpg", "libero_source_qc_75205_75229.jpg"],
    "yellow_left_5": ["player5_source_qc_75180_75204.jpg", "player5_source_qc_75205_75229.jpg"],
}
SETTER_SHEET = "setter_grounded_qc_75211_75229.jpg"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_length(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def median_path(points, window):
    half = window // 2
    return np.asarray([
        np.median(points[max(0, i - half):min(len(points), i + half + 1)], axis=0)
        for i in range(len(points))
    ])


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    frames = list(range(75180, 75230))
    result = {
        "status": "single_reviewer_provisional_distance_estimate_not_release_metric",
        "source_sha256": source["source_sha256"],
        "candidate_path_sha256": sha256(SOURCE),
        "calibration_sha256": source["calibration_sha256"],
        "saved_annotations_sha256": source["saved_annotations_sha256"],
        "frame_range_inclusive": [frames[0], frames[-1]],
        "frame_count": len(frames),
        "method": "Project box-bottom centres through the staged homography; apply a centred five-frame coordinate-wise median, then sum consecutive Euclidean steps. Endpoint displacement is a strict lower bound on travel. Three- and seven-frame median results are method-sensitivity checks, not confidence intervals.",
        "missing_gap_policy": "Include only visual players whose identity and box foot region were checked across the reported interval. Do not bridge an unobserved court position or airborne interval. The median smooths noisy observed box bottoms; it does not create missing positions.",
        "players": {},
        "partial_players": {},
        "excluded_players": {
            "yellow_centre_left": "No distinct raw box after 75205; missing segment has no checked returning endpoint and earlier foot proxy is obscured.",
            "yellow_right_entrant": "Entry and approach boxes are clipped or outside the calibrated court; no reliable bracket of grounded positions.",
        },
        "limits": "These are approximate distances for this 50-frame slice only. The homography remains disabled for production metrics; box-bottom movement, court-line fit, and single-reviewer assisted identity checks limit accuracy. Do not extrapolate to a rally or report speed."
    }
    for name, sheets in PLAYERS.items():
        for sheet in sheets:
            if not (DIR / sheet).is_file():
                raise FileNotFoundError(sheet)
        path = source["players"][name]
        points = np.asarray([path[str(frame)]["court_position_m_diagnostic"] for frame in frames], dtype=float)
        if points.shape != (50, 2) or not np.isfinite(points).all():
            raise ValueError(f"missing or invalid source-reviewed positions for {name}")
        raw = path_length(points)
        sensitivities = {str(window): path_length(median_path(points, window)) for window in (3, 5, 7)}
        estimate = sensitivities["5"]
        displacement = float(np.linalg.norm(points[-1] - points[0]))
        if not (0 <= displacement <= raw + 1e-9):
            raise ValueError(f"invalid endpoint displacement for {name}")
        result["players"][name] = {
            "source_review_sheets_sha256": {sheet: sha256(DIR / sheet) for sheet in sheets},
            "source_reviewed_frames": 50,
            "distance_estimate_m": round(estimate, 2),
            "three_to_seven_frame_method_range_m": [round(min(sensitivities.values()), 2), round(max(sensitivities.values()), 2)],
            "raw_box_bottom_path_m": round(raw, 2),
            "endpoint_displacement_lower_bound_m": round(displacement, 2),
            "outside_nominal_court_frames": int(np.any((points < 0) | (points > 9), axis=1).sum()),
        }
    if not (DIR / SETTER_SHEET).is_file():
        raise FileNotFoundError(SETTER_SHEET)
    setter_frames = list(range(75211, 75230))
    setter_path = source["players"]["yellow_setter_18"]
    setter_points = np.asarray([setter_path[str(frame)]["court_position_m_diagnostic"] for frame in setter_frames], dtype=float)
    if setter_points.shape != (19, 2) or not np.isfinite(setter_points).all():
        raise ValueError("invalid setter post-landing positions")
    setter_sensitivities = {str(window): path_length(median_path(setter_points, window)) for window in (3, 5, 7)}
    result["partial_players"]["yellow_setter_18"] = {
        "frame_range_inclusive": [setter_frames[0], setter_frames[-1]],
        "source_review_sheet_sha256": {SETTER_SHEET: sha256(DIR / SETTER_SHEET)},
        "source_reviewed_frames": 19,
        "distance_estimate_m": round(setter_sensitivities["5"], 2),
        "three_to_seven_frame_method_range_m": [round(min(setter_sensitivities.values()), 2), round(max(setter_sensitivities.values()), 2)],
        "raw_box_bottom_path_m": round(path_length(setter_points), 2),
        "endpoint_displacement_lower_bound_m": round(float(np.linalg.norm(setter_points[-1] - setter_points[0])), 2),
        "excluded_start_frames": [75180, 75210],
        "scope_note": "Only the visually checked post-landing segment is estimated; the airborne and uncertain landing interval is omitted. The source sheet confirms the same visible setter across the raw-ID handoff at 75225.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    for name, item in result["players"].items():
        print(name, item["distance_estimate_m"], item["three_to_seven_frame_method_range_m"])
    print("yellow_setter_18 partial", result["partial_players"]["yellow_setter_18"]["distance_estimate_m"])


if __name__ == "__main__":
    main()
