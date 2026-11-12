"""Compare a source-reviewed six-player shoe frame with dense court proxies."""

import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14"
SCREEN = BASE / "screening"
MANUALS = [SCREEN / f"full_rally_validation_frames/s3_p34_f{frame}_manual_qc.json"
           for frame in (36036, 36066, 36078, 36096, 36138)]
DENSE = SCREEN / "source_bracketed_30fps_screen.json"
PRIOR = SCREEN / "two_long_runs_30fps_screen.json"
IDENTITY = SCREEN / "two_long_runs_30fps_audit.json"
CALIBRATION = SCREEN / "near_court_candidate.json"
OUT = SCREEN / "full_rally_live_reference_audit.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(point, matrix):
    return tuple(cv2.perspectiveTransform(
        np.asarray([[point]], np.float32), matrix)[0, 0].tolist())


def main():
    manuals = [json.loads(path.read_text(encoding="utf-8")) for path in MANUALS]
    dense = json.loads(DENSE.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert dense["source_sha256"] == prior["source_sha256"] == identity["source_sha256"]
    point = next(p for p in dense["points"] if (p["set"], p["point_number"]) == (3, 34))
    previous = next(p for p in prior["points"] if (p["set"], p["point_number"]) == (3, 34))
    assert point["rows"][:len(previous["rows"])] == previous["rows"]
    known = next(r for r in identity["rows"] if (r["set"], r["point_number"]) == (3, 34))
    raw_by_jersey = {p["reviewed_jersey_number"]: p["dense_raw_track_id"]
                     for p in known["players"]}
    assert len(raw_by_jersey) == 6
    h = np.asarray(calibration["homography_image_to_court"], np.float64)
    reviewed_frames = []
    for manual_path, manual in zip(MANUALS, manuals):
        assert (manual["set"], manual["point_number"]) == (3, 34)
        assert {r["jersey"] for r in manual["rows"]} == set(raw_by_jersey)
        frame = next(r for r in point["rows"] if r["source_frame"] == manual["source_frame"])
        proposals = {p["raw_track_id"]: p for p in frame["proposals"]
                     if p["net_side_status"] == "near_floor_side_candidate"}
        corrected_raw = dict(raw_by_jersey)
        if manual["source_frame"] >= 36122:
            corrected_raw["7"] = 78
        assert set(corrected_raw.values()) <= set(proposals)
        image_path = BASE / manual["source_image"]
        image = cv2.imread(str(image_path))
        assert image is not None and image.shape[:2] == (720, 1280)
        rows = []
        manual_positions, proxy_positions = [], []
        for mark in manual["rows"]:
            a, b = mark["shoe_centres_px"]
            midpoint = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
            assert math.dist(midpoint, mark["midpoint_px"]) <= .71
            raw_id = corrected_raw[mark["jersey"]]
            proposal = proposals[raw_id]
            x1, _, x2, y2 = proposal["bbox_px"]
            bottom = [(x1 + x2) / 2, y2]
            manual_court = project(mark["midpoint_px"], h)
            proxy_court = tuple(proposal["box_bottom_court_m"])
            manual_positions.append(manual_court)
            proxy_positions.append(proxy_court)
            rows.append({
                "jersey": mark["jersey"], "dense_raw_track_id": raw_id,
                "manual_shoe_midpoint_px": mark["midpoint_px"],
                "manual_court_m": [round(v, 4) for v in manual_court],
                "box_bottom_px": [round(v, 1) for v in bottom],
                "box_bottom_court_m": proxy_court,
                "image_position_difference_px": round(math.dist(bottom, mark["midpoint_px"]), 2),
                "court_position_difference_m": round(math.dist(manual_court, proxy_court), 3),
            })
            cv2.circle(image, tuple(mark["midpoint_px"]), 7, (0, 0, 255), 2)
            cv2.circle(image, tuple(map(round, bottom)), 5, (0, 255, 0), 2)
            cv2.line(image, tuple(mark["midpoint_px"]), tuple(map(round, bottom)),
                     (0, 255, 255), 1)
            cv2.putText(image, f"#{mark['jersey']}",
                        (mark["midpoint_px"][0] + 8, mark["midpoint_px"][1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 2)
        overlay = SCREEN / f"full_rally_validation_frames/s3_p34_f{manual['source_frame']}_reference_overlay.png"
        assert cv2.imwrite(str(overlay), image)
        manual_metric = metrics(manual_positions)
        proxy_metric = metrics(proxy_positions)
        reviewed_frames.append({
            "source_frame": manual["source_frame"],
            "input_sha256": {"manual": sha(manual_path), "source_image": sha(image_path)},
            "manual_rule": manual["rule"],
            "rows": rows,
            "median_player_position_difference_m": round(statistics.median(
                r["court_position_difference_m"] for r in rows), 3),
            "maximum_player_position_difference_m": max(
                r["court_position_difference_m"] for r in rows),
            "manual_team_metric": {k: round(v, 3) for k, v in manual_metric.items()},
            "proxy_team_metric": {k: round(v, 3) for k, v in proxy_metric.items()},
            "proxy_minus_manual_team_metric": {
                k: round(proxy_metric[k] - manual_metric[k], 3) for k in manual_metric},
            "overlay": overlay.relative_to(BASE).as_posix(),
        })
    all_rows = [row for frame in reviewed_frames for row in frame["rows"]]
    result = {
        "status": "five_single_reviewer_six_player_frames_not_full_rally_validation",
        "source_sha256": dense["source_sha256"],
        "input_sha256": {**{f"manual_{path.stem.split('_f')[1].split('_')[0]}": sha(path)
                            for path in MANUALS},
                         "dense": sha(DENSE), "identity": sha(IDENTITY),
                         "calibration": sha(CALIBRATION)},
        "set": 3, "point_number": 34,
        "summary": {
            "reviewed_players": len(all_rows),
            "six_player_reference_frames": len(reviewed_frames),
            "median_player_position_difference_m": round(statistics.median(
                r["court_position_difference_m"] for r in all_rows), 3),
            "maximum_player_position_difference_m": max(
                r["court_position_difference_m"] for r in all_rows),
        },
        "frames": reviewed_frames,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Five in-rally six-player position references",
        "",
        "At S3 P34 source frames 36036, 36066, 36078, 36096 and 36138, six UCLA "
        "player shoe positions were marked by one reviewer. The original 36066 and "
        "36078 marks were made on unboxed source images before the detector comparison. "
        "The three added marks are supplementary unblinded checks made after seeing "
        "tracker boxes. Estimated shoe reading uncertainty is 12-15 source pixels "
        "per axis. These five frames span early, middle and late play.",
        "",
        "| Frame | Median player difference (m) | Maximum (m) | Spacing difference (m) | Hull difference (m^2) | Dispersion difference (m) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for frame in reviewed_frames:
        diff = frame["proxy_minus_manual_team_metric"]
        lines.append(f"| {frame['source_frame']} | "
                     f"{frame['median_player_position_difference_m']:.3f} | "
                     f"{frame['maximum_player_position_difference_m']:.3f} | "
                     f"{diff['mean_pairwise_spacing_m']:+.3f} | "
                     f"{diff['convex_hull_area_m2']:+.3f} | "
                     f"{diff['centroid_dispersion_m']:+.3f} |")
    s = result["summary"]
    lines += [
        "",
        f"Across the {len(all_rows)} selected player positions, median difference is "
        f"**{s['median_player_position_difference_m']:.3f} m** and maximum is "
        f"**{s['maximum_player_position_difference_m']:.3f} m**.",
        "",
    ]
    for frame in reviewed_frames:
        number = frame["source_frame"]
        lines += [
            f"### Frame {number}",
            "",
            f"[Manual marks](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f{number}_manual_qc.json) "
            f"and [source image](../data/matches/yt_u5HnY2aNW14/{next(m['source_image'] for m in manuals if m['source_frame'] == number)}).",
            "",
            f"![Red manual shoe midpoint, green box bottom](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f{number}_reference_overlay.png)",
            "",
            "| Jersey | Box-to-shoe difference (m) |",
            "| --- | ---: |",
        ]
        for row in frame["rows"]:
            lines.append(f"| #{row['jersey']} | {row['court_position_difference_m']:.3f} |")
        lines.append("")
    lines += [
        "The [audit JSON](../data/matches/yt_u5HnY2aNW14/screening/full_rally_live_reference_audit.json) "
        "contains all image and court coordinates and source hashes. These are five "
        "selected single-reviewer source-frame comparisons; three are unblinded. "
        "They do not validate the full "
        "rally, every-frame jersey assignment, airborne positions, or outcome effects.",
        "",
        "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/audit_u5_live_reference_frame.py`.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
