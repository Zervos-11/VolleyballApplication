"""Build an explicit six-player proxy scenario from the agreed gap rule."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
SUMMARY = BASE / "r1_point_summary.json"
OUT = BASE / "r1_six_player_proxy_scenario.json"
FIRST, LAST = 21050, 21463
MODEL_PLAYERS = ("11", "13")
OTHER_PLAYERS = ("9", "10", "12", "20")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(items):
    groups = []
    for frame, point in items:
        if not groups or frame > groups[-1][-1][0] + 1:
            groups.append([])
        groups[-1].append((frame, point))
    return groups


def median_path(points, window):
    radius = window // 2
    return np.asarray([np.median(points[max(0, i-radius):min(len(points), i+radius+1)],
                                 axis=0) for i in range(len(points))])


def model_player(pid, frames, transform, window):
    observed = []
    clipped = []
    for frame in range(FIRST, LAST + 1):
        slot = frames[frame][pid]
        box = slot["bbox_px"]
        if slot["box_status"] != "raw_box_candidate" or box is None:
            continue
        pixel = np.float32([[[(box[0] + box[2]) / 2, box[3]]]])
        projected = cv2.perspectiveTransform(pixel, transform)[0, 0].astype(float)
        point = np.clip(projected, 0, 9)
        if not np.allclose(point, projected):
            clipped.append(frame)
        observed.append((frame, point))
    segments = runs(observed)
    smooth = [median_path(np.asarray([point for _, point in segment]), window)
              for segment in segments]
    visible = sum(float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
                  for points in smooth if len(points) > 1)
    gap_details = []
    for left, right, left_points, right_points in zip(
            segments, segments[1:], smooth, smooth[1:]):
        gap_details.append({
            "last_seen_frame": left[-1][0],
            "return_frame": right[0][0],
            "missing_frames": right[0][0] - left[-1][0] - 1,
            "endpoint_chord_m": round(float(np.linalg.norm(right_points[0] - left_points[-1])), 3),
        })
    chords = sum(row["endpoint_chord_m"] for row in gap_details)
    return {
        "accepted_raw_box_frames": len(observed),
        "clipped_projected_box_bottom_frames": len(clipped),
        "clipped_frame_range_inclusive": [min(clipped), max(clipped)] if clipped else None,
        "first_observed_frame": observed[0][0],
        "last_observed_frame": observed[-1][0],
        "terminal_stationary_hold_frames": LAST - observed[-1][0],
        "visible_segment_path_m": round(visible, 3),
        "closed_gap_endpoint_chords": gap_details,
        "stationary_terminal_contribution_m": 0.0,
        "proxy_scenario_m": round(visible + chords, 2),
    }


def main():
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    frames = {row["frame"]: row["players"] for row in visual["frame_records"]}
    assert list(frames) == list(range(FIRST, LAST + 1))
    assert summary["visual_candidate_sha256"] == sha256(VISUAL)
    transform = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                            np.float32(calibration["points_court_m"]))
    existing = {row["player_id"]: row for row in summary["players"]
                if row["player_id"] in OTHER_PLAYERS}
    assert all(existing[pid]["approximate_distance_m"] is not None
               for pid in OTHER_PLAYERS)
    methods = {str(window): {pid: model_player(pid, frames, transform, window)
                             for pid in MODEL_PLAYERS} for window in (5, 15, 31)}
    displayed = {pid: existing[pid]["approximate_distance_m"] for pid in OTHER_PLAYERS}
    displayed.update({pid: methods["15"][pid]["proxy_scenario_m"] for pid in MODEL_PLAYERS})
    result = {
        "status": "assumption_based_six_player_proxy_scenario_not_validated_distance",
        "match_id": "yt_FqE5pTJqx8g",
        "candidate_frames_inclusive": [FIRST, LAST],
        "visual_candidate_sha256": sha256(VISUAL),
        "calibration_sha256": sha256(CALIBRATION),
        "point_summary_sha256": sha256(SUMMARY),
        "policy": "For #11 and #13, project curated box-bottom centres, clip court coordinates to 0-9 m, apply a 15-frame median per visible segment, add straight endpoint chords across closed gaps, and hold the last position through unclosed terminal gaps. Other players retain the displayed approximate estimates in the point summary.",
        "modelled_players": MODEL_PLAYERS,
        "modelled_player_smoothing_window_sensitivity": methods,
        "displayed_player_scenario_m": displayed,
        "displayed_six_player_sum_m": round(sum(displayed.values()), 2),
        "six_player_sum_if_modelled_players_use_5_frame_median_m": round(
            sum(existing[pid]["approximate_distance_m"] for pid in OTHER_PLAYERS) +
            sum(methods["5"][pid]["proxy_scenario_m"] for pid in MODEL_PLAYERS), 2),
        "six_player_sum_if_modelled_players_use_31_frame_median_m": round(
            sum(existing[pid]["approximate_distance_m"] for pid in OTHER_PLAYERS) +
            sum(methods["31"][pid]["proxy_scenario_m"] for pid in MODEL_PLAYERS), 2),
        "scenario_only_reasons": [
            "#11 and #13 box bottoms often do not represent visible shoe-floor contact; clipping is an explicit geometry assumption.",
            "#11 has a source-known cross-player raw-ID conflict; the curated visual slot is used as a scenario identity assumption.",
            "#13 has 272 missing candidate boxes and a 40-frame terminal stationary hold; unseen motion is assigned zero there.",
            "Endpoint chords give net displacement across hidden spans and omit detours.",
            "The other four player estimates use different approximate proxy methods and frame scopes.",
        ],
        "physical_team_distance_released": False,
        "official_annotations_changed": False,
        "production_metric_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print({"players": displayed, "sum_m": result["displayed_six_player_sum_m"],
           "5_to_31_frame_window_sums_m": [
               result["six_player_sum_if_modelled_players_use_31_frame_median_m"],
               result["six_player_sum_if_modelled_players_use_5_frame_median_m"]]})


if __name__ == "__main__":
    main()
