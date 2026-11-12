"""Carry pre-rally player identities through ambiguous overlaps with explicit holds."""

import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from build_d79_provisional_court_paths import calibration, median_path, path_length, project


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/processed/d79_new_source/raw_point_candidate_80_336.json"
SEEDS = ROOT / "data/processed/d79_new_source/prerally_identity_seed.json"
OUT = ROOT / "data/processed/d79_new_source"
FIRST, LAST = 80, 336


def proxy(raw, frame, track_id):
    matches = [p for p in raw["predictions"][str(frame)] if p["track_id"] == track_id]
    if len(matches) != 1:
        raise ValueError(f"frame {frame} raw ID {track_id}: expected one box, got {len(matches)}")
    x1, _, x2, y2 = matches[0]["bbox"]
    return [(x1 + x2) / 2, y2]


def smooth_segment(points):
    width = min(15, len(points) if len(points) % 2 else len(points) - 1)
    return median_path(points, max(1, width))


def timeline(summary):
    image = np.full((430, 1250, 3), 255, np.uint8)
    x0, scale = 110, 4
    color = {"observed_proxy": (30, 165, 60), "held_assumption": (10, 170, 245),
             "airborne_excluded": (185, 185, 185), "unknown_before_first": (225, 225, 225)}
    for index, (pid, player) in enumerate(summary["players"].items()):
        y = 80 + index * 48
        cv2.putText(image, f"#{pid}", (25, y + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
        for frame, status in player["frame_status"]:
            x = x0 + (frame - FIRST) * scale
            cv2.rectangle(image, (x, y), (x + scale - 1, y + 28), color[status], -1)
    for frame in (80, 148, 212, 240, 268, 287, 336):
        x = x0 + (frame - FIRST) * scale
        cv2.line(image, (x, 72), (x, 365), (120, 120, 120), 1)
        cv2.putText(image, str(frame), (x - 14, 393), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 30, 30), 1)
    cv2.putText(image, "Source-seeded identity holds: green observed, orange held, grey excluded", (22, 43),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)
    if not cv2.imwrite(str(OUT / "seeded_hold_timeline.jpg"), image):
        raise RuntimeError("could not write timeline")


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    seeds = json.loads(SEEDS.read_text(encoding="utf-8"))
    h, _ = calibration()
    result = {
        "status": "source_seeded_identity_with_explicit_stationary_hold_assumption",
        "raw_candidate_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "identity_seed_sha256": hashlib.sha256(SEEDS.read_bytes()).hexdigest(),
        "frames_inclusive": [FIRST, LAST],
        "hold_policy": "When source identity becomes ambiguous, carry the last image/court position unchanged. A return counts only the endpoint chord across the gap; no speed or hidden trajectory is inferred. Held positions are assumptions, not observations.",
        "players": {},
    }
    rows = []
    viewer_frames = {str(frame): {} for frame in range(FIRST, LAST + 1)}
    for pid, config in seeds["players"].items():
        frame_to_track = {}
        segments = config["accepted_raw_segments"]
        for start, end, track_id in segments:
            for frame in range(start, end + 1):
                if frame in frame_to_track:
                    raise ValueError(f"overlapping identity segments for #{pid} frame {frame}")
                frame_to_track[frame] = track_id
        first_known = segments[0][0]
        last_point = None
        statuses = []
        observed_segments = []
        for start, end, track_id in segments:
            points = np.asarray([proxy(raw, frame, track_id) for frame in range(start, end + 1)], dtype=float)
            observed_segments.append((start, end, track_id, points))
        observed_court = [project(item[3], h) for item in observed_segments]
        outside = sum(int(((p[:, 0] < 0) | (p[:, 0] > 9) | (p[:, 1] < 0) | (p[:, 1] > 9)).sum())
                      for p in observed_court)
        smoothed = [smooth_segment(p) for p in observed_court]
        segment_path = sum(path_length(p) for p in smoothed)
        chords = [float(np.linalg.norm(right[0] - left[-1])) for left, right in zip(smoothed, smoothed[1:])]
        endpoint_estimate = round(segment_path + sum(chords), 2) if outside == 0 else None
        clipped = [smooth_segment(np.clip(p, 0, 9)) for p in observed_court]
        clipped_path = sum(path_length(p) for p in clipped)
        clipped_chords = sum(float(np.linalg.norm(right[0] - left[-1]))
                             for left, right in zip(clipped, clipped[1:]))
        hold_scenario = round(clipped_path + clipped_chords, 2)
        for frame in range(FIRST, LAST + 1):
            track_id = frame_to_track.get(frame)
            if track_id is not None:
                last_point = proxy(raw, frame, track_id)
                status = "observed_proxy"
            elif frame < first_known:
                status = "airborne_excluded" if pid == "98" else "unknown_before_first"
            else:
                status = "held_assumption"
            court = project([last_point], h)[0] if last_point is not None else None
            statuses.append([frame, status])
            rows.append({"frame": frame, "saved_player_id": pid, "status": status,
                         "accepted_raw_track_id": track_id if track_id is not None else "",
                         "proxy_or_hold_x_px": "" if last_point is None else round(last_point[0], 3),
                         "proxy_or_hold_y_px": "" if last_point is None else round(last_point[1], 3),
                         "candidate_x_m": "" if court is None else round(float(court[0]), 4),
                         "candidate_y_m": "" if court is None else round(float(court[1]), 4)})
            box = None
            if track_id is not None:
                box = next(p["bbox"] for p in raw["predictions"][str(frame)]
                           if p["track_id"] == track_id)
            viewer_frames[str(frame)][pid] = {
                "status": status,
                "raw_track_id": track_id,
                "bbox": box,
                "position_px": [round(v, 3) for v in last_point] if last_point is not None else None,
            }
        observed = sum(status == "observed_proxy" for _, status in statuses)
        held = sum(status == "held_assumption" for _, status in statuses)
        hold_runs = []
        run_start = None
        for frame, status in statuses + [[LAST + 1, "end"]]:
            if status == "held_assumption" and run_start is None:
                run_start = frame
            elif status != "held_assumption" and run_start is not None:
                hold_runs.append([run_start, frame - 1])
                run_start = None
        result["players"][pid] = {
            "accepted_raw_segments": segments,
            "observed_proxy_frames": observed,
            "stationary_hold_frames": held,
            "hold_runs_inclusive": hold_runs,
            "longest_hold_frames": max((end - start + 1 for start, end in hold_runs), default=0),
            "excluded_or_unseeded_frames": LAST - FIRST + 1 - observed - held,
            "observed_proxy_points_outside_candidate_near_court": outside,
            "reentry_gap_chord_m": [round(v, 2) for v in chords],
            "observed_segment_15_frame_proxy_path_m": round(segment_path, 2),
            "hold_policy_counterfactual_path_m": endpoint_estimate,
            "endpoint_chord_estimate_m": endpoint_estimate,
            "endpoint_chord_scope_frames_inclusive": [first_known, segments[-1][1]],
            "unclosed_hold_at_point_end_frames": LAST - segments[-1][1],
            "endpoint_chord_method": "Smoothed accepted segment paths plus straight chords between accepted endpoints; movement within gaps is unobserved. Candidate court geometry and box-bottom proxies are unvalidated.",
            "stationary_hold_full_point_scenario_m": hold_scenario,
            "scenario_clamped_proxy_points": outside,
            "scenario_assumption": "No additional movement in unclosed holds. Closed gaps use straight endpoint chords. Candidate projected proxy points beyond the 9 m near court are clipped to its boundary before smoothing.",
            "metric_status": ("withheld_due_to_off_court_or_airborne_proxy" if outside
                              else "counterfactual_only_due_to_unobserved_hold" if held
                              else "development_proxy_without_hold"),
            "frame_status": statuses,
        }
    OUT.mkdir(parents=True, exist_ok=True)
    result["team_stationary_hold_scenario_m"] = round(sum(
        player["stationary_hold_full_point_scenario_m"] for player in result["players"].values()), 2)
    result["team_scenario_status"] = "development_model_only_not_validated_physical_travel"
    timeline(result)
    (OUT / "seeded_occlusion_holds.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    viewer = {
        "status": "source_seeded_visual_candidates_with_marked_holds",
        "frames_inclusive": [FIRST, LAST],
        "source_width": 1280,
        "source_height": 720,
        "fps": 60,
        "player_order": list(seeds["players"]),
        "team_stationary_hold_scenario_m": result["team_stationary_hold_scenario_m"],
        "endpoint_estimates": {
            pid: {
                "metres": player["endpoint_chord_estimate_m"],
                "scope_frames_inclusive": player["endpoint_chord_scope_frames_inclusive"],
                "unclosed_hold_at_point_end_frames": player["unclosed_hold_at_point_end_frames"],
                "status": player["metric_status"],
                "full_point_hold_scenario_m": player["stationary_hold_full_point_scenario_m"],
                "clamped_proxy_points": player["scenario_clamped_proxy_points"],
            }
            for pid, player in result["players"].items()
        },
        "note": "Box-bottom centres are proxies. Held positions are last-seen display markers, not current observations or movement samples.",
        "frames": viewer_frames,
    }
    (OUT / "seeded_hold_viewer_record.json").write_text(json.dumps(viewer, separators=(",", ":")) + "\n", encoding="utf-8")
    with (OUT / "seeded_occlusion_hold_positions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({pid: {key: value for key, value in item.items() if key != "frame_status"}
                      for pid, item in result["players"].items()}, indent=2))


if __name__ == "__main__":
    main()
