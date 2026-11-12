"""Project frozen AoEP box bottoms as explicitly provisional court traces."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
DIR = ROOT / "data/processed/aoep_new_source"
RAW = DIR / "raw_74880_75540.json"
NAV = DIR / "dense_review_gap_audit.json"
VISIBILITY = DIR / "dense_visibility_states.json"
SAVED = MATCH / "pilot/player_annotations/point_21m.json"
CALIBRATION = MATCH / "homography.json"
VIDEO = MATCH / "source_AoEP-YiWRvc.mp4"
PLAYER_IDS = {
    "yellow_left_5": "5",
    "yellow_centre_left": "19",
    "yellow_centre_4": "4",
    "yellow_setter_18": "18",
    "navy_libero_10": "10",
    "yellow_right_entrant": "Sam",
}
COLORS = [(50, 190, 255), (220, 80, 210), (40, 210, 80),
          (255, 130, 40), (220, 120, 40), (100, 100, 240)]
FIRST, LAST = 75180, 75229
MOTION_REVIEW_M_PER_FRAME = 0.30


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_rows():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    nav = json.loads(NAV.read_text(encoding="utf-8"))
    visibility = json.loads(VISIBILITY.read_text(encoding="utf-8"))
    saved = json.loads(SAVED.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if raw["source_sha256"] != nav["source_sha256"] or raw["source_sha256"] != sha256(VIDEO):
        raise ValueError("source provenance mismatch")
    if calibration["source_sha256"] != raw["source_sha256"]:
        raise ValueError("calibration source mismatch")
    matrix = cv2.getPerspectiveTransform(
        np.asarray(calibration["points_px"], np.float32),
        np.asarray(calibration["points_court_m"], np.float32),
    )
    width, height = calibration["image_size"]
    rows = {visual_id: {} for visual_id in PLAYER_IDS}
    for frame in range(FIRST, LAST + 1):
        key = str(frame)
        nav_by_id = {item["visual_player_id"]: item for item in nav["frames"][key]}
        visibility_by_id = {item["visual_player_id"]: item for item in visibility["frames"][key]}
        saved_by_id = {item["player_id"]: item for item in saved["frames"].get(key, {}).get("players", [])}
        for visual_id, player_id in PLAYER_IDS.items():
            navigation = nav_by_id[visual_id]
            state = visibility_by_id[visual_id]["court_position_status"]
            saved_player = saved_by_id.get(player_id)
            raw_id = navigation.get("candidate_raw_track_id")
            box = saved_player.get("bbox") if saved_player else None
            source = "saved_box" if saved_player else "frozen_raw_box_candidate"
            if saved_player is None and navigation["navigation_status"] == "single_box_candidate":
                matches = [item for item in raw["predictions"][key] if item["track_id"] == raw_id]
                if len(matches) != 1:
                    raise ValueError(f"unexpected raw candidate count at {frame}/{visual_id}")
                box = matches[0]["bbox"]
            reasons = []
            if box is None:
                reasons.append("no_distinct_box")
            if state in ("unknown_airborne", "unknown_landing_transition"):
                reasons.append(state)
            if saved_player and saved_player["position_status"] in ("airborne", "occluded", "out_of_frame"):
                reasons.append("saved_non_ground_state")
            if box is not None:
                x1, y1, x2, y2 = map(float, box)
                if x1 <= 1 or x2 >= width - 1 or y2 >= height - 1:
                    reasons.append("box_touches_image_edge")
                pixel = [(x1 + x2) / 2, y2]
                court = cv2.perspectiveTransform(
                    np.asarray(pixel, np.float32).reshape(1, 1, 2), matrix
                ).reshape(2)
                if not (0 <= court[0] <= 9 and 0 <= court[1] <= 9):
                    reasons.append("outside_nominal_near_court")
                pixel = [round(v, 2) for v in pixel]
                court = [round(float(v), 2) for v in court]
            else:
                pixel = court = None
            rows[visual_id][key] = {
                "player_id": player_id,
                "source": source if box is not None else "unresolved",
                "raw_track_id_candidate": raw_id,
                "bbox_bottom_centre_px": pixel,
                "court_position_m_diagnostic": court,
                "candidate_ground_position": bool(court is not None and not reasons),
                "withheld_reasons": reasons,
            }
    for path in rows.values():
        previous = None
        for key, item in path.items():
            if not item["candidate_ground_position"]:
                previous = None
                continue
            if previous is not None:
                distance = float(np.linalg.norm(
                    np.asarray(item["court_position_m_diagnostic"])
                    - np.asarray(previous["court_position_m_diagnostic"])
                ))
                if distance > MOTION_REVIEW_M_PER_FRAME:
                    item["motion_discontinuity_from_previous_m"] = round(distance, 2)
            previous = item
    return rows, raw, nav, visibility, saved, calibration


def segments(rows):
    result = {}
    for visual_id, path in rows.items():
        groups, group = [], []
        previous_raw_id = None
        for key, item in path.items():
            valid = item["candidate_ground_position"]
            raw_id = item["raw_track_id_candidate"]
            if valid and group and (item.get("motion_discontinuity_from_previous_m") is not None
                                    or (raw_id is not None and previous_raw_id is not None
                                        and raw_id != previous_raw_id)):
                groups.append(group)
                group = []
            if valid:
                group.append(int(key))
                previous_raw_id = raw_id
            else:
                if group:
                    groups.append(group)
                group = []
                previous_raw_id = None
        if group:
            groups.append(group)
        result[visual_id] = [{"first_frame": group[0], "last_frame": group[-1],
                              "observed_frames": len(group)} for group in groups if len(group) >= 2]
    return result


def render(rows, groups, destination):
    canvas = np.full((900, 900, 3), 250, dtype=np.uint8)
    cv2.rectangle(canvas, (85, 85), (815, 815), (50, 50, 50), 3)
    cv2.line(canvas, (85, 328), (815, 328), (120, 120, 120), 2)  # attack y=6
    cv2.putText(canvas, "Near baseline y=0", (85, 855), cv2.FONT_HERSHEY_SIMPLEX, .6, (30, 30, 30), 2)
    cv2.putText(canvas, "Net y=9", (85, 62), cv2.FONT_HERSHEY_SIMPLEX, .6, (30, 30, 30), 2)
    def point(xy):
        return (round(85 + xy[0] * 730 / 9), round(815 - xy[1] * 730 / 9))
    for index, visual_id in enumerate(PLAYER_IDS):
        color = COLORS[index]
        path = rows[visual_id]
        for group in groups[visual_id]:
            positions = [point(path[str(frame)]["court_position_m_diagnostic"])
                         for frame in range(group["first_frame"], group["last_frame"] + 1)]
            if len(positions) > 1:
                cv2.polylines(canvas, [np.asarray(positions, np.int32)], False, color, 2, cv2.LINE_AA)
            for p in positions:
                cv2.circle(canvas, p, 2, color, -1)
        cv2.putText(canvas, PLAYER_IDS[visual_id], (650, 550 + index * 30),
                    cv2.FONT_HERSHEY_SIMPLEX, .65, color, 2)
    cv2.putText(canvas, "AoEP provisional box-bottom traces", (85, 30),
                cv2.FONT_HERSHEY_SIMPLEX, .72, (25, 25, 25), 2)
    cv2.putText(canvas, "Gaps/airborne/boundary points withheld; not movement metrics", (85, 882),
                cv2.FONT_HERSHEY_SIMPLEX, .48, (25, 25, 25), 1)
    if not cv2.imwrite(str(destination), canvas):
        raise OSError(destination)


def main():
    rows, raw, nav, visibility, saved, calibration = candidate_rows()
    groups = segments(rows)
    stem = f"candidate_court_paths_{FIRST}_{LAST}_{sha256(SAVED)[:10]}"
    output, preview = DIR / f"{stem}.json", DIR / f"{stem}.jpg"
    if output.exists() or preview.exists():
        raise FileExistsError(stem)
    summary = {
        "source_sha256": raw["source_sha256"],
        "raw_sha256": sha256(RAW),
        "navigation_sha256": sha256(NAV),
        "visibility_sha256": sha256(VISIBILITY),
        "saved_annotations_sha256": sha256(SAVED),
        "calibration_sha256": sha256(CALIBRATION),
        "status": "provisional_box_bottom_court_traces_not_movement_metrics",
        "frame_range_inclusive": [FIRST, LAST],
        "position_method": "bbox bottom centre projected through staged homography",
        "motion_review_threshold_m_per_frame": MOTION_REVIEW_M_PER_FRAME,
        "ground_status": "Candidate only; raw IDs and visual-player associations are development navigation, not independently reviewed ground truth.",
        "counts_by_player": {key: dict(Counter(
            "candidate_ground_position" if row["candidate_ground_position"] else
            ",".join(row["withheld_reasons"]) for row in path.values()
        )) for key, path in rows.items()},
        "continuous_segments_at_least_two_frames": groups,
        "motion_discontinuities_by_player": {
            key: [{"frame_index": int(frame), "step_m": item["motion_discontinuity_from_previous_m"]}
                  for frame, item in path.items() if "motion_discontinuity_from_previous_m" in item]
            for key, path in rows.items()
        },
        "distance_speed_coverage_published": False,
        "preview": preview.name,
        "players": rows,
    }
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    render(rows, groups, preview)
    print(json.dumps({"output": output.name, "segments": groups,
                      "counts": {key: value.get("candidate_ground_position", 0)
                                 for key, value in summary["counts_by_player"].items()}}))


if __name__ == "__main__":
    main()
