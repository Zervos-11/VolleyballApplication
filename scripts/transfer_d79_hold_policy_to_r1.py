"""Test the D79 endpoint-and-hold policy on the independent R1 source."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_six_slot_visual_candidate.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
OUTPUT = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_d79_hold_policy_transfer.json"
FIRST, LAST = 21050, 21463
PLAYERS = ("9", "10", "11", "12", "13", "20")
MAX_COURT_OVERSHOOT_M = 0.25


def runs(frames):
    result = []
    for frame in frames:
        if not result or frame > result[-1][-1] + 1:
            result.append([frame])
        else:
            result[-1].append(frame)
    return result


def median_path(points):
    radius = 7
    return np.asarray([np.median(points[max(0, i - radius):min(len(points), i + radius + 1)], axis=0)
                       for i in range(len(points))])


def path_length(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()) if len(points) > 1 else 0.0


def main():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    cal = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    transform = cv2.getPerspectiveTransform(np.asarray(cal["points_px"], np.float32),
                                             np.asarray(cal["points_court_m"], np.float32))
    frames = {item["frame"]: item["players"] for item in record["frame_records"]}
    result = {
        "status": "independent_source_transfer_diagnostic_not_physical_distance",
        "source_match_id": "yt_FqE5pTJqx8g",
        "record_sha256": hashlib.sha256(RECORD.read_bytes()).hexdigest(),
        "calibration_sha256": hashlib.sha256(CALIBRATION.read_bytes()).hexdigest(),
        "frames_inclusive": [FIRST, LAST],
        "policy": "Use 15-frame median within each contiguous accepted box segment, then a straight chord across every closed gap. Unclosed end gaps contribute zero in the stationary-hold scenario. Reject material court overshoot and known identity conflicts instead of using an unrestricted court clip.",
        "court_overshoot_limit_m": MAX_COURT_OVERSHOOT_M,
        "players": {},
    }
    for pid in PLAYERS:
        start = 21070 if pid == "9" else FIRST
        usable = {}
        rejected = {}
        raw_ids = set()
        for frame in range(start, LAST + 1):
            item = frames[frame][pid]
            if item["box_status"] != "raw_box_candidate" or not item["bbox_px"]:
                rejected[frame] = item["box_status"]
                continue
            x1, _, x2, y2 = item["bbox_px"]
            point = np.float32([[[0.5 * (x1 + x2), y2]]])
            court = cv2.perspectiveTransform(point, transform)[0, 0]
            overshoot = float(max(0, -court[0], court[0] - 9, -court[1], court[1] - 9))
            raw_ids.add(item["raw_track_id"])
            if overshoot > MAX_COURT_OVERSHOOT_M:
                rejected[frame] = "material_off_court_projection"
                continue
            usable[frame] = court.astype(float)
        segments = runs(sorted(usable))
        smooth = [median_path(np.asarray([usable[f] for f in segment])) for segment in segments]
        visible_distance = sum(path_length(points) for points in smooth)
        gap_chords = [float(np.linalg.norm(right[0] - left[-1]))
                      for left, right in zip(smooth, smooth[1:])]
        accepted_end = max(usable) if usable else None
        status = "geometry_passes_candidate_only"
        if pid == "11":
            status = "withheld_known_raw_identity_conflict_and_off_court_projection"
        elif pid == "13":
            status = "withheld_sparse_overlap_and_airborne_proxy"
        elif any(reason == "material_off_court_projection" for reason in rejected.values()):
            status = "withheld_material_off_court_projection"
        elif not usable:
            status = "withheld_no_usable_position"
        result["players"][pid] = {
            "raw_candidate_frames": sum(frames[f][pid]["box_status"] == "raw_box_candidate"
                                        for f in range(start, LAST + 1)),
            "accepted_proxy_frames": len(usable),
            "rejected_by_reason": {reason: sum(value == reason for value in rejected.values())
                                   for reason in sorted(set(rejected.values()))},
            "raw_id_count": len(raw_ids),
            "contiguous_segment_count": len(segments),
            "closed_gap_count": max(0, len(segments) - 1),
            "longest_missing_run_frames": max((len(run) for run in runs(sorted(rejected))), default=0),
            "visible_segment_path_m": round(visible_distance, 2),
            "closed_gap_endpoint_chords_m": [round(value, 2) for value in gap_chords],
            "last_accepted_frame": accepted_end,
            "terminal_hold_frames": LAST - accepted_end if accepted_end is not None else LAST - start + 1,
            "stationary_hold_scenario_m": round(visible_distance + sum(gap_chords), 2)
                                          if status == "geometry_passes_candidate_only" else None,
            "metric_status": status,
        }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["players"], indent=2))


if __name__ == "__main__":
    main()
