"""Compare completed 30-fps single-reviewer shoe marks with box-bottom proxies.

This selected segment and its single-reviewer annotations are diagnostic. The
script does not approve a calibration, a fixed analysis window, or a rally.
"""

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = SCREEN / "s3p34_30fps_ground_review"
FORM = PACK / "single_reviewer_unsampled_completed.csv"
SCORE = PACK / "single_reviewer_score.json"
TRACKS = SCREEN / "source_bracketed_30fps_screen.json"
IDENTITY = SCREEN / "two_long_runs_30fps_audit.json"
CALIBRATION = SCREEN / "near_court_candidate.json"
OUT = PACK / "single_reviewer_position_comparison.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_30FPS_POSITION_COMPARISON.md"
SLOTS = ("28", "12", "15", "7", "19", "21")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(point, matrix):
    value = cv2.perspectiveTransform(np.asarray([[point]], np.float32), matrix)[0, 0]
    return tuple(float(x) for x in value)


def summary(values):
    return {"median": round(statistics.median(values), 3),
            "minimum": round(min(values), 3), "maximum": round(max(values), 3)}


def main():
    score = json.loads(SCORE.read_text(encoding="utf-8"))
    assert score["status"] == "single_reviewer_form_scored_not_strict_approval"
    assert score["completed_sha256"] == sha(FORM)
    assert score["accepted_intervening_slots"] == 180
    assert score["intervening_frames_with_six_accepted_slots"] == 30
    with FORM.open(newline="", encoding="utf-8") as stream:
        form = list(csv.DictReader(stream))
    assert len(form) == 180
    tracks = json.loads(TRACKS.read_text(encoding="utf-8"))
    point = next(p for p in tracks["points"] if (p["set"], p["point_number"]) == (3, 34))
    tracked = {row["source_frame"]: row for row in point["rows"]}
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    player_map = next(p for p in identity["rows"] if (p["set"], p["point_number"]) == (3, 34))
    raw_by_slot = {p["reviewed_jersey_number"]: p["dense_raw_track_id"]
                   for p in player_map["players"]}
    assert set(raw_by_slot) == set(SLOTS)
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert calibration["use_for_final_metrics"] is False
    matrix = np.asarray(calibration["homography_image_to_court"], np.float64)

    by_frame = {}
    for row in form:
        number, slot = int(row["source_frame"]), row["jersey"]
        assert slot in SLOTS
        assert row["identity_status"] != "uncertain"
        assert row["ground_status"] == "grounded"
        assert row["candidate_alignment"] == "same_player"
        assert row["proxy_floor_alignment"] == "plausible"
        assert row["shoe_midpoint_x_px"] and row["shoe_midpoint_y_px"]
        source_image = PACK / row["unboxed_image"]
        assert sha(source_image) == row["image_sha256"]
        mark = [float(row["shoe_midpoint_x_px"]), float(row["shoe_midpoint_y_px"])]
        proposals = {p["raw_track_id"]: p for p in tracked[number]["proposals"]
                     if p["net_side_status"] == "near_floor_side_candidate"}
        proposal = proposals[raw_by_slot[slot]]
        x1, _, x2, y2 = proposal["bbox_px"]
        bottom = [(x1 + x2) / 2, y2]
        manual_court = project(mark, matrix)
        proxy_court = tuple(proposal["box_bottom_court_m"])
        assert all(math.isfinite(x) for x in manual_court + proxy_court)
        by_frame.setdefault(number, []).append({
            "stored_slot": slot, "raw_track_id": raw_by_slot[slot],
            "shoe_midpoint_px": mark, "box_bottom_px": [round(x, 2) for x in bottom],
            "manual_court_m": [round(x, 4) for x in manual_court],
            "proxy_court_m": proxy_court,
            "image_difference_px": round(math.dist(mark, bottom), 3),
            "court_difference_m": round(math.dist(manual_court, proxy_court), 3),
        })
    assert len(by_frame) == 30
    frames = []
    for number, rows in sorted(by_frame.items()):
        assert [row["stored_slot"] for row in rows] == list(SLOTS)
        manual = metrics([tuple(row["manual_court_m"]) for row in rows])
        proxy = metrics([tuple(row["proxy_court_m"]) for row in rows])
        frames.append({
            "source_frame": number, "players": rows,
            "manual_team_metric": {key: round(value, 3) for key, value in manual.items()},
            "proxy_team_metric": {key: round(value, 3) for key, value in proxy.items()},
            "proxy_minus_manual": {key: round(proxy[key] - manual[key], 3) for key in manual},
        })
    differences = [row["court_difference_m"] for frame in frames for row in frame["players"]]
    image_differences = [row["image_difference_px"] for frame in frames for row in frame["players"]]
    metric_names = ("mean_pairwise_spacing_m", "convex_hull_area_m2", "centroid_dispersion_m")
    metric_summary = {key: summary([frame["proxy_minus_manual"][key] for frame in frames])
                      for key in metric_names}
    result = {
        "status": "single_reviewer_diagnostic_position_comparison",
        "source_video_sha256": tracks["source_sha256"],
        "input_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p)
                         for p in (FORM, SCORE, TRACKS, IDENTITY, CALIBRATION)},
        "calibration_status": "staged_not_approved_for_final_metrics",
        "review_provenance": "one reviewer, previously exposed to tracker; source-first within this pass",
        "frames": frames,
        "summary": {
            "reviewed_frames": len(frames), "reviewed_player_slots": len(differences),
            "image_position_difference_px": summary(image_differences),
            "court_position_difference_m": summary(differences),
            "proxy_minus_manual_team_metric": metric_summary,
        },
        "strict_metric_approval": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    s = result["summary"]
    rows = [
        "# S3 P34 single-reviewer 30-fps position comparison", "",
        "The [completed 180-row review](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv) "
        "covers the 30 intervening frames in the selected 36066–36102 diagnostic segment. "
        "All six stored slots were marked grounded with a shoe midpoint and judged to have a matching, "
        "plausible candidate box. The [scorer](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_score.json) "
        "accepted all 180 slots under that single-reviewer rule. The reviewer had previously seen tracker "
        "output, so the source-first step in this pass does not create an independent blinded reference.", "",
        f"The 180 shoe-to-box-bottom projected distances have median **{s['court_position_difference_m']['median']:.3f} m** "
        f"and largest observed value **{s['court_position_difference_m']['maximum']:.3f} m**. "
        f"In image pixels, the median is **{s['image_position_difference_px']['median']:.3f} px** "
        f"and the largest is **{s['image_position_difference_px']['maximum']:.3f} px**. "
        "These are within-frame differences from one reviewer, not independently established floor-position errors.", "",
        "| Proxy minus manual team metric across 30 frames | Median | Minimum | Maximum |", "| --- | ---: | ---: | ---: |",
    ]
    labels = {"mean_pairwise_spacing_m": "Mean pairwise spacing (m)",
              "convex_hull_area_m2": "Convex-hull area (m²)",
              "centroid_dispersion_m": "Centroid dispersion (m)"}
    for key in metric_names:
        value = metric_summary[key]
        rows.append(f"| {labels[key]} | {value['median']:+.3f} | {value['minimum']:+.3f} | {value['maximum']:+.3f} |")
    rows += ["",
             "The [machine-readable comparison](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_position_comparison.json) "
             "retains all 30 frame-level and 180 player-level values. The four-corner court transform is still staged, "
             "and this segment was selected after box availability was known. These comparisons do not certify a "
             "strict fixed window or complete rally; the source-bracketed S3 P34 rally still includes missing and "
             "airborne floor positions outside this segment.", "",
             "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s3p34_30fps_single_reviewer_reference.py`."]
    REPORT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
