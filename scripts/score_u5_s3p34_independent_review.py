"""Score completed S3 P34 independent review forms without self-approval.

The independent reviewer must write three *_completed.csv files alongside the
blank templates. This script never fills answers or grants strict validation.
"""

import argparse
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
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
DEFAULT_PACK = BASE / "s3p34_independent_review_pack"
SAMPLED = BASE / "s3p34_reviewed_sample_ledger.json"
OUT = BASE / "s3p34_independent_review_score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_INDEPENDENT_REVIEW_STATUS.md"
ROSTER = ("28", "12", "15", "7", "19", "21")
COURT_LANDMARKS = ("near_left_baseline_corner", "near_right_baseline_corner",
                   "near_right_centreline_corner", "near_left_centreline_corner",
                   "left_attack_line_sideline", "right_attack_line_sideline")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def number(value, label, lower, upper):
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError(f"{label} must lie in [{lower}, {upper}]")
    return result


def project(homography, point):
    raw = np.array([[[point[0], point[1]]]], dtype=np.float64)
    return tuple(float(v) for v in cv2.perspectiveTransform(raw, homography)[0, 0])


def score_event(rows, manifest):
    expected = ([(n, "serve_contact") for n in manifest["serve_contact_review_frames"]] +
                [(n, "point_end") for n in manifest["point_end_review_frames"]])
    keys = [(int(row["source_frame"]), row["event"]) for row in rows]
    if keys != expected:
        raise ValueError("Completed event form does not match the blank frame order")
    valid = {"serve_contact": {"before_contact", "contact", "after_contact", "uncertain"},
             "point_end": {"live", "dead", "uncertain"}}
    for row in rows:
        if row["ball_contact_or_dead_status"] not in valid[row["event"]]:
            raise ValueError(f"Invalid event status at {row['source_frame']}")
    serve = [row for row in rows if row["event"] == "serve_contact"]
    end = [row for row in rows if row["event"] == "point_end"]
    contacts = [int(row["source_frame"]) for row in serve
                if row["ball_contact_or_dead_status"] == "contact"]
    first_dead = next((int(row["source_frame"]) for row in end
                       if row["ball_contact_or_dead_status"] == "dead"), None)
    exact_serve = len(contacts) == 1 and all(
        row["ball_contact_or_dead_status"] ==
        ("before_contact" if int(row["source_frame"]) < contacts[0] else
         "contact" if int(row["source_frame"]) == contacts[0] else "after_contact")
        for row in serve)
    exact_end = first_dead is not None and first_dead > min(manifest["point_end_review_frames"]) and all(
        row["ball_contact_or_dead_status"] ==
        ("live" if int(row["source_frame"]) < first_dead else "dead")
        for row in end)
    return {"exact_serve_contact_in_review_range": bool(exact_serve),
            "serve_contact_frame": contacts[0] if exact_serve else None,
            "first_dead_frame_in_review_range": first_dead if exact_end else None,
            "point_end_resolved_in_review_range": bool(exact_end),
            "uncertain_event_rows": sum(row["ball_contact_or_dead_status"] == "uncertain"
                                        for row in rows)}


def score_court(rows, manifest):
    keys = [(int(row["source_frame"]), row["landmark"]) for row in rows]
    expected = [(manifest["calibration_frame"], landmark) for landmark in COURT_LANDMARKS]
    if keys != expected:
        raise ValueError("Completed court form does not match the blank landmark order")
    points = [(number(row["x_px"], f"{row['landmark']} x", 0, 1280),
               number(row["y_px"], f"{row['landmark']} y", 0, 720)) for row in rows]
    target = np.array([[0, 0], [9, 0], [9, 9], [0, 9]], dtype=np.float32)
    homography = cv2.getPerspectiveTransform(np.array(points[:4], dtype=np.float32), target)
    if not np.isfinite(homography).all():
        raise ValueError("Court homography is not finite")
    attack = [project(homography, point) for point in points[4:]]
    return homography, {"independent_landmarks_px": points,
                        "attack_line_projected_m": attack,
                        "attack_line_depth_abs_residual_m": [abs(point[1] - 6) for point in attack],
                        "max_attack_line_depth_abs_residual_m": max(abs(point[1] - 6)
                                                                  for point in attack),
                        "calibration_approved_for_metric_use": False,
                        "approval_note": "Numerical residual is diagnostic; no post hoc threshold automatically approves calibration."}


def score_players(rows, manifest, sampled, homography):
    expected = [(n, jersey) for n in manifest["sampled_ground_frames"] for jersey in ROSTER]
    keys = [(int(row["source_frame"]), row["jersey"]) for row in rows]
    if keys != expected:
        raise ValueError("Completed player form does not match the blank frame and jersey order")
    frames = {row["source_frame"]: row for row in sampled["frames"]}
    errors = []
    complete_frames = []
    uncertain_identity = 0
    non_grounded = 0
    by_frame = {}
    for row in rows:
        frame, jersey = int(row["source_frame"]), row["jersey"]
        if row["identity_status"] not in {"confirmed", "sequence_only", "uncertain"}:
            raise ValueError(f"Invalid identity status at {frame} #{jersey}")
        if row["ground_status"] not in {"grounded", "airborne", "occluded", "uncertain"}:
            raise ValueError(f"Invalid ground status at {frame} #{jersey}")
        uncertain_identity += row["identity_status"] == "uncertain"
        non_grounded += row["ground_status"] != "grounded"
        if row["ground_status"] != "grounded":
            if row["shoe_midpoint_x_px"] or row["shoe_midpoint_y_px"]:
                raise ValueError(f"Non-grounded slot has shoe coordinates at {frame} #{jersey}")
            continue
        x = number(row["shoe_midpoint_x_px"], f"{frame} #{jersey} shoe x", 0, 1280)
        y = number(row["shoe_midpoint_y_px"], f"{frame} #{jersey} shoe y", 0, 720)
        number(row["reading_uncertainty_px"], f"{frame} #{jersey} reading uncertainty", 0, 100)
        if row["identity_status"] == "uncertain":
            continue
        source_player = frames[frame]["players"][jersey]
        box = source_player["candidate_bbox_px"]
        if box is None:
            continue
        shoe_court = project(homography, (x, y))
        box_court = project(homography, ((box[0] + box[2]) / 2, box[3]))
        error = math.dist(shoe_court, box_court)
        errors.append({"source_frame": frame, "jersey": jersey,
                       "shoe_vs_box_bottom_m": round(error, 4)})
        by_frame.setdefault(frame, {})[jersey] = {"shoe": shoe_court, "box": box_court}
    metric_differences = []
    for frame, players in sorted(by_frame.items()):
        if set(players) != set(ROSTER):
            continue
        complete_frames.append(frame)
        manual = metrics([players[j]["shoe"] for j in ROSTER])
        proxy = metrics([players[j]["box"] for j in ROSTER])
        metric_differences.append({"source_frame": frame,
                                   "proxy_minus_shoe": {key: round(proxy[key] - manual[key], 4)
                                                        for key in manual}})
    return {"reviewed_player_slots": len(rows),
            "uncertain_identity_slots": uncertain_identity,
            "non_grounded_or_uncertain_ground_slots": non_grounded,
            "paired_position_count": len(errors),
            "paired_position_median_m": (round(statistics.median(r["shoe_vs_box_bottom_m"]
                                                                  for r in errors), 4) if errors else None),
            "paired_position_maximum_m": (max(r["shoe_vs_box_bottom_m"] for r in errors)
                                          if errors else None),
            "independently_complete_six_player_frames": complete_frames,
            "position_comparisons": errors,
            "team_metric_comparisons": metric_differences}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_PACK)
    args = parser.parse_args()
    pack = args.review_dir.resolve()
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    for filename, digest in manifest["image_sha256"].items():
        if sha(pack / filename) != digest:
            raise ValueError(f"Source review image hash mismatch: {filename}")
    completed = {kind: pack / f"{kind}_review_completed.csv"
                 for kind in ("player", "event", "court")}
    missing = [kind for kind, path in completed.items() if not path.is_file()]
    result = {"status": "awaiting_independent_review" if missing else
              "independent_review_scored_not_automatically_approved",
              "point": "S3 P34", "pack_manifest_sha256": sha(pack / "manifest.json"),
              "missing_completed_forms": missing, "strict_approved": False}
    if not missing:
        sampled = json.loads(SAMPLED.read_text(encoding="utf-8"))
        court_h, court = score_court(read_csv(completed["court"]), manifest)
        result.update({"input_sha256": {kind: sha(path) for kind, path in completed.items()},
                       "event_review": score_event(read_csv(completed["event"]), manifest),
                       "court_review": court,
                       "player_review": score_players(read_csv(completed["player"]),
                                                       manifest, sampled, court_h)})
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if missing:
        detail = ("No completed independent verdicts were supplied. Missing forms: " +
                  ", ".join(path.name for kind, path in completed.items() if kind in missing) + ".")
    else:
        positions = result["player_review"]
        detail = (f"Scored {positions['paired_position_count']} paired grounded positions "
                  f"and {len(positions['independently_complete_six_player_frames'])} complete "
                  "six-player frames. Court and event decisions still require documented "
                  "protocol acceptance; this script does not grant strict approval.")
    REPORT.write_text("\n".join([
        "# S3 P34 independent review status", "",
        "No second reviewer is available for the current thesis audit. This packet is optional; "
        "the active same-reviewer process is documented in "
        "[the single-reviewer protocol](HONOURS_U5_S3P34_SINGLE_REVIEWER_PROTOCOL.md).", "",
        detail, "",
        "The [score record](../data/matches/yt_u5HnY2aNW14/screening/s3p34_independent_review_score.json) "
        "checks the native source-image hashes, reviewer form structure, event verdicts, "
        "independent court marks and player shoe-to-box differences when completed forms exist. "
        "It does not replace source review or convert an airborne frame into a floor position.", "",
        "Forms and instructions: [local unboxed review packet]"
        "(../data/matches/yt_u5HnY2aNW14/screening/s3p34_independent_review_pack/README.md). "
        "Place completed copies beside the blank forms, named "
        "`event_review_completed.csv`, `court_review_completed.csv` and "
        "`player_review_completed.csv`. Reproduce with `.\\.venv\\Scripts\\python.exe "
        "scripts/score_u5_s3p34_independent_review.py`.",
    ]) + "\n", encoding="utf-8")
    print(result["status"] + ": " + detail)


if __name__ == "__main__":
    main()
