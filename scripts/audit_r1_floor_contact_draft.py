"""Audit separately saved r1 shoe-contact clicks without releasing court metrics."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
REVIEW = BASE / "r1_floor_contact_review.json"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
OUTPUT = BASE / "r1_saved_floor_contact_audit.json"
ROSTER = {"9", "10", "11", "12", "13", "20"}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if review["match_id"] != "yt_FqE5pTJqx8g" or review["rally_id"] != "r1":
        raise ValueError("Floor review does not match the frozen case study")
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], dtype=np.float32),
        np.asarray(calibration["points_court_m"], dtype=np.float32),
    )
    frame_records = {row["frame"]: row["players"] for row in visual["frame_records"]}
    width, height = calibration["image_size"]
    observations = []
    state_counts = Counter()
    player_frames = defaultdict(set)
    preview_frames = []
    capture = cv2.VideoCapture(str(SOURCE))
    if not capture.isOpened():
        raise RuntimeError("Cannot open r1 source video")
    try:
        for frame_key, players in sorted(review["records"].items(), key=lambda item: int(item[0])):
            frame = int(frame_key)
            if not 21050 <= frame < 21464 or frame not in frame_records:
                raise ValueError(f"Reviewed frame {frame} outside the candidate")
            if len(preview_frames) < 12:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
                okay, image = capture.read()
                if not okay:
                    raise RuntimeError(f"Cannot decode source frame {frame}")
                preview_frames.append(frame)
            else:
                image = None
            for player, record in sorted(players.items(), key=lambda item: int(item[0])):
                if player not in ROSTER or record["frame_index"] != frame or record["player_id"] != player:
                    raise ValueError(f"Invalid player/frame reference at {frame}/{player}")
                state = record["state"]
                point = record["footpoint_px"]
                if state == "grounded_contact_visible":
                    if point is None or len(point) != 2 or not np.isfinite(point).all():
                        raise ValueError(f"Visible contact at {frame}/{player} lacks a finite point")
                    if not (0 <= point[0] < width and 0 <= point[1] < height):
                        raise ValueError(f"Point outside source image at {frame}/{player}")
                    court = cv2.perspectiveTransform(
                        np.asarray(point, dtype=np.float32).reshape(1, 1, 2), matrix,
                    ).reshape(2)
                    court_xy = [round(float(v), 3) for v in court]
                    # A fixed pixel perturbation is a sensitivity scenario, not an
                    # estimate of the reviewer's actual click error.
                    perturbations = np.asarray(
                        [[point[0] + dx, point[1] + dy]
                         for dx, dy in ((-5, 0), (5, 0), (0, -5), (0, 5))],
                        dtype=np.float32,
                    ).reshape(-1, 1, 2)
                    shifted = cv2.perspectiveTransform(perturbations, matrix).reshape(-1, 2)
                    sensitivity_5px = {
                        "pixel_offsets_xy": [[-5, 0], [5, 0], [0, -5], [0, 5]],
                        "court_depth_range_m": [round(float(shifted[:, 1].min()), 3),
                                                 round(float(shifted[:, 1].max()), 3)],
                        "max_court_displacement_m": round(float(np.linalg.norm(shifted - court, axis=1).max()), 3),
                        "interpretation": "Fixed 5 px axis perturbation of the saved click; not a measured error bound.",
                    }
                    # The four calibration fit points span baseline to the 3 m line
                    # (depth 0..6). The held-out net line is at depth 9 m.
                    nominal_near_court = bool(0 <= court[0] <= 9 and 0 <= court[1] <= 9)
                    near_court_boundary_review = bool(
                        -0.25 <= court[0] <= 9.25
                        and -0.25 <= court[1] <= 9.25
                        and min(abs(court[0]), abs(court[0] - 9),
                                abs(court[1]), abs(court[1] - 9)) <= 0.25
                    )
                else:
                    if point is not None:
                        raise ValueError(f"Non-grounded state has a floor point at {frame}/{player}")
                    court_xy = None
                    sensitivity_5px = None
                    nominal_near_court = None
                    near_court_boundary_review = None
                candidate = frame_records[frame][player]
                bbox = candidate["bbox_px"]
                box_bottom_offset = round(float(point[1] - bbox[3]), 1) if point and bbox else None
                box_horizontal_match = bool(bbox[0] - 10 <= point[0] <= bbox[2] + 10) if point and bbox else None
                if point is not None and bbox is not None:
                    box_bottom_px = [(bbox[0] + bbox[2]) / 2, bbox[3]]
                    box_bottom_court = cv2.perspectiveTransform(
                        np.asarray(box_bottom_px, dtype=np.float32).reshape(1, 1, 2), matrix,
                    ).reshape(2)
                    box_bottom_court_xy = [round(float(v), 3) for v in box_bottom_court]
                    floor_vs_box_bottom_m = round(float(np.linalg.norm(court - box_bottom_court)), 3)
                else:
                    box_bottom_court_xy = None
                    floor_vs_box_bottom_m = None
                row = {
                    "frame_index": frame,
                    "player_id": player,
                    "state": state,
                    "footpoint_px": point,
                    "court_position_m_diagnostic": court_xy,
                    "projection_sensitivity_5px_diagnostic": sensitivity_5px,
                    "inside_nominal_near_court": nominal_near_court,
                    "within_0_25m_of_near_court_boundary": near_court_boundary_review,
                    "candidate_box_status": candidate["box_status"],
                    "point_minus_box_bottom_y_px": box_bottom_offset,
                    "point_within_candidate_box_x_plus_10px": box_horizontal_match,
                    "candidate_box_bottom_court_m_diagnostic": box_bottom_court_xy,
                    "floor_vs_box_bottom_court_m_diagnostic": floor_vs_box_bottom_m,
                    "source_visual_check": "pending",
                }
                observations.append(row)
                state_counts[state] += 1
                player_frames[player].add(frame)
                if image is not None and point is not None:
                    x, y = (int(round(v)) for v in point)
                    cv2.circle(image, (x, y), 13, (0, 0, 0), 5, cv2.LINE_AA)
                    cv2.circle(image, (x, y), 10, (0, 255, 255), 3, cv2.LINE_AA)
                    cv2.putText(image, f"#{player}", (x + 14, y - 12), cv2.FONT_HERSHEY_SIMPLEX,
                                0.8, (0, 0, 0), 4, cv2.LINE_AA)
                    cv2.putText(image, f"#{player}", (x + 14, y - 12), cv2.FONT_HERSHEY_SIMPLEX,
                                0.8, (0, 255, 255), 2, cv2.LINE_AA)
            if image is not None:
                cv2.imwrite(str(BASE / f"r1_saved_floor_contacts_{frame}.jpg"), image)
    finally:
        capture.release()

    proxy_differences = [row["floor_vs_box_bottom_court_m_diagnostic"] for row in observations
                         if row["floor_vs_box_bottom_court_m_diagnostic"] is not None]
    result = {
        "status": "single_reviewer_draft_structural_and_projection_audit_not_metric_release",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1",
        "review_sha256": file_hash(REVIEW),
        "calibration_sha256": file_hash(CALIBRATION),
        "calibration_status": "staged_not_activated_for_metrics",
        "near_court_bounds_m": [0, 9, 0, 9],
        "calibration_fit_region_depth_m": [0, 6],
        "saved_frame_count": len(review["records"]),
        "saved_player_frame_count": len(observations),
        "state_counts": dict(state_counts),
        "players_with_two_or_more_reviewed_frames": sorted(
            player for player, frames in player_frames.items() if len(frames) >= 2),
        "source_previews": [f"r1_saved_floor_contacts_{frame}.jpg" for frame in preview_frames],
        "observations": observations,
        "clicked_floor_vs_box_bottom_m_this_snapshot": {
            "count": len(proxy_differences),
            "min": round(min(proxy_differences), 3) if proxy_differences else None,
            "median": round(float(np.median(proxy_differences)), 3) if proxy_differences else None,
            "max": round(max(proxy_differences), 3) if proxy_differences else None,
        },
        "physical_distance_available": False,
        "limitation": "The projections are staged-geometry diagnostics. The four fit points end at the 3 m line (depth 6); front court through the net at depth 9 is extrapolated and checked only by held-out line evidence. Fixed 5 px perturbations illustrate sensitivity but do not bound click or calibration error. A near-boundary point needs source review. Structural QC and one clicked frame do not establish a movement path.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved_frames": result["saved_frame_count"],
                      "saved_player_frames": len(observations),
                      "players_with_two_or_more_reviewed_frames": result["players_with_two_or_more_reviewed_frames"]}))


if __name__ == "__main__":
    main()
