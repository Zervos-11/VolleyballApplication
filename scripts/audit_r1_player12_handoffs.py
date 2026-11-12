"""Audit blue #12 raw-track handoffs without claiming a movement metric."""

import json
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import median_filter


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
RAW = BASE / "r1_dense_raw_tracks.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"


def contiguous_runs(frames):
    runs = []
    for frame in frames:
        if not runs or frame > runs[-1][1]+1:
            runs.append([frame, frame])
        else:
            runs[-1][1] = frame
    return runs


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32))

    def point(track_id, frame):
        rows = [row for row in raw["frames"][str(frame)]
                if row["track_id"] == track_id]
        if not rows:
            return None
        x1, _, x2, y2 = rows[0]["bbox"]
        return cv2.perspectiveTransform(
            np.asarray([[[(x1+x2)/2, y2]]], dtype=np.float32), matrix)[0, 0]

    segments = [(8, 21050, 21087), (72, 21099, 21212), (338, 21236, 21463)]
    segment_records = []
    for track_id, first, last in segments:
        observed = [(frame, point(track_id, frame))
                    for frame in range(first, last+1)]
        observed = [(frame, xy) for frame, xy in observed if xy is not None]
        out_of_court = [frame for frame, xy in observed
                        if not (0 <= xy[0] <= 9 and 0 <= xy[1] <= 9)]
        jumps = [{"to_frame": frame, "step_m": round(float(np.linalg.norm(xy-observed[i-1][1])), 3)}
                 for i, (frame, xy) in enumerate(observed) if i and frame == observed[i-1][0]+1
                 and np.linalg.norm(xy-observed[i-1][1]) > 0.5]
        segment_records.append({"raw_track_id": track_id, "frames_inclusive": [first, last],
                                "observed_frames": len(observed),
                                "out_of_court_box_bottom_frames": out_of_court,
                                "over_0_5_m_one_frame_jumps": jumps})

    handoffs = []
    for left_id, left_end, right_id, right_start in ((8,21087,72,21099),
                                                     (72,21212,338,21236)):
        a, b = point(left_id, left_end), point(right_id, right_start)
        displacement = float(np.linalg.norm(b-a))
        handoffs.append({"from_track": left_id, "last_frame": left_end,
                         "to_track": right_id, "first_frame": right_start,
                         "unobserved_frames": right_start-left_end-1,
                         "endpoint_displacement_m": round(displacement, 3),
                         "endpoint_average_m_per_s": round(displacement*50/(right_start-left_end), 3),
                         "identity_at_endpoints": "source_visually_consistent_blue_12",
                         "floor_path_in_gap": "unknown"})

    full_frames = range(21050, 21464)
    target_track = lambda frame: (8 if frame <= 21087 else
                                  72 if 21099 <= frame <= 21212 else
                                  338 if frame >= 21236 else None)
    missing = [frame for frame in full_frames
               if target_track(frame) is None or point(target_track(frame), frame) is None]
    full_coverage = {"frames_inclusive": [21050, 21463],
                     "source_frames": len(full_frames),
                     "raw_target_box_frames": len(full_frames)-len(missing),
                     "missing_target_box_frames": len(missing),
                     "missing_runs_inclusive": contiguous_runs(missing),
                     "source_gap_review": "r1_player12_gap_source_review.json",
                     "interpretation": "#12 remains visually present in the source-reviewed missing frames, but ground positions remain unknown."}

    # Quantify why full-span path length is withheld. All missing points are
    # interpolated only for this sensitivity test, not saved as player labels.
    first, end = 21100, 21464
    frames = np.arange(first, end)
    series = np.full((len(frames), 2), np.nan)
    for i, frame in enumerate(frames):
        xy = point(72 if frame <= 21212 else 338, int(frame))
        if xy is not None:
            series[i] = xy
    known = np.isfinite(series[:, 0])
    interpolated = series.copy()
    for dim in (0, 1):
        interpolated[:, dim] = np.interp(frames, frames[known], series[known, dim])
    sensitivity = {}
    for width in (5, 9, 15, 21, 31):
        smoothed = np.column_stack([
            median_filter(interpolated[:, dim], size=width, mode="nearest")
            for dim in (0, 1)])
        sensitivity[str(width)] = round(float(
            np.linalg.norm(np.diff(smoothed, axis=0), axis=1).sum()), 3)

    result = {
        "status": "source_sampled_identity_audit_floor_path_unresolved",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1", "player_id": "12",
        "track_segments": segment_records,
        "handoffs": handoffs,
        "full_candidate_coverage": full_coverage,
        "source_sheets": ["data/processed/fqe_r1_boundary_recheck/p12_first_gap_sheet.jpg",
                          "data/processed/fqe_r1_boundary_recheck/p12_second_gap_sheet.jpg",
                          "data/processed/fqe_r1_boundary_recheck/p12_motion_break_sheet.jpg"],
        "full_span_diagnostic": {
            "frames_inclusive": [first, end-1],
            "raw_positions_available": int(known.sum()),
            "interpolated_positions_for_sensitivity_only": int((~known).sum()),
            "median_filter_width_frames_to_proxy_path_m": sensitivity,
            "interpretation": "Smoothing sensitivity and near-net box-bottom jumps make this unsuitable as a player-distance estimate."
        },
        "decision": "Identity appears continuous through sampled source frames, but do not use raw ID 8 after frame 21087 and do not publish a full-span #12 distance from these box bottoms.",
        "official_labels_changed": False,
        "production_metric_changed": False
    }
    (BASE/"r1_player12_handoff_audit.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(f"#12: {int(known.sum())}/{len(frames)} raw positions; distance withheld")


if __name__ == "__main__":
    main()
