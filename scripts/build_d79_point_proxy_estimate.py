"""Build bounded D79 point movement diagnostics from grounded box-bottom proxies."""

import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from build_d79_provisional_court_paths import calibration, median_path, path_length, project


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/processed/d79_new_source/raw_point_candidate_80_336.json"
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
OUT = ROOT / "data/processed/d79_new_source"
WINDOWS = (5, 9, 15, 21, 31)
TRACKS = {"8": {"raw_id": 1, "first": 80, "color": (0, 150, 0)},
          "98": {"raw_id": 5, "first": 98, "color": (200, 30, 170)}}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def track_points(raw, track_id, first):
    points = []
    for frame in range(first, 337):
        boxes = [row["bbox"] for row in raw["predictions"][str(frame)] if row["track_id"] == track_id]
        if len(boxes) != 1:
            raise ValueError(f"raw ID {track_id} has {len(boxes)} boxes at frame {frame}")
        box = boxes[0]
        points.append(((box[0] + box[2]) / 2, box[3]))
    return np.asarray(points, dtype=float)


def anchor_check(labels, raw, pid, track_id, h):
    deviations = []
    clicked = []
    proxy = []
    for frame in range(240, 290):
        person = next(p for p in labels["frames"][str(frame)]["players"] if p["player_id"] == pid)
        if person["position_status"] != "visible" or person["footpoint"] is None:
            raise ValueError(f"missing checked anchor for #{pid} frame {frame}")
        box = next(p["bbox"] for p in raw["predictions"][str(frame)] if p["track_id"] == track_id)
        point = [(box[0] + box[2]) / 2, box[3]]
        deviations.append(np.linalg.norm(np.asarray(person["footpoint"]) - point))
        clicked.append(person["footpoint"])
        proxy.append(point)
    return {
        "checked_frames": 50,
        "proxy_to_checked_point_median_px": round(float(np.median(deviations)), 2),
        "proxy_to_checked_point_p90_px": round(float(np.percentile(deviations, 90)), 2),
        "same_50_frame_15_median_checked_path_m": round(path_length(median_path(project(clicked, h), 15)), 2),
        "same_50_frame_15_median_proxy_path_m": round(path_length(median_path(project(proxy, h), 15)), 2),
    }


def draw_map(paths):
    scale = 65
    margin = 105
    image = np.full((790, 790, 3), 255, dtype=np.uint8)
    to_pixel = lambda p: (round(margin + p[0] * scale), round(margin + (9 - p[1]) * scale))
    cv2.rectangle(image, to_pixel((0, 9)), to_pixel((9, 0)), (30, 30, 30), 3)
    cv2.line(image, to_pixel((0, 6)), to_pixel((9, 6)), (80, 80, 80), 2)
    cv2.putText(image, "NET", (margin + 265, margin - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (20, 20, 20), 2)
    cv2.putText(image, "3 m attack line", (margin + 10, margin + 3 * scale - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1)
    for pid, points in paths.items():
        color = TRACKS[pid]["color"]
        pix = np.asarray([to_pixel(p) for p in points], dtype=np.int32)
        cv2.polylines(image, [pix], False, color, 3, cv2.LINE_AA)
        cv2.circle(image, tuple(pix[0]), 7, color, -1, cv2.LINE_AA)
        cv2.circle(image, tuple(pix[-1]), 7, color, 2, cv2.LINE_AA)
        cv2.putText(image, f"#{pid} start", tuple(pix[0] + [8, -6]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
        cv2.putText(image, f"#{pid} end", tuple(pix[-1] + [8, -6]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    cv2.putText(image, "PROVISIONAL FEET-LEVEL BOX PROXIES", (115, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (10, 10, 10), 2)
    cv2.putText(image, "Not validated physical travel", (245, 760),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (10, 10, 10), 2)
    if not cv2.imwrite(str(OUT / "point_candidate_proxy_court_paths.jpg"), image):
        raise RuntimeError("could not write court map")


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    main_h, _ = calibration()
    variants = [calibration(n, a)[0] for n in (-8, 0, 8) for a in (-3, 0, 3)]
    result = {
        "status": "source_sampled_development_estimate_not_validated_physical_travel",
        "raw_candidate_sha256": sha256(RAW), "checked_labels_sha256": sha256(LABELS),
        "point_interval_inclusive": [80, 336],
        "geometry": "Provisional 9 m width, 3 m net-to-attack span, net-floor line partly hidden; nine line-placement scenarios.",
        "method": "Use centre x and bottom y of the raw person box as a feet-level proxy. Project through candidate homography, apply coordinate-wise median over 15 frames, sum consecutive court-plane steps. Compare 5, 9, 15, 21, 31-frame smoothing and nine geometry variants.",
        "unobserved_policy": "#98's airborne serve and landing transition through frame 97 are excluded. A visible box is not proof of planted feet; other unobserved contacts remain an uncertainty, not imputed ground truth.",
        "players": {},
    }
    rows = []
    paths = {}
    for pid, config in TRACKS.items():
        points_px = track_points(raw, config["raw_id"], config["first"])
        points_m = project(points_px, main_h)
        if ((points_m[:, 0] < 0) | (points_m[:, 0] > 9) | (points_m[:, 1] < 0) | (points_m[:, 1] > 9)).any():
            raise ValueError(f"#{pid} candidate path projects outside near court")
        window_values = {str(w): round(path_length(median_path(points_m, w)), 2) for w in WINDOWS}
        geometry_15 = [path_length(median_path(project(points_px, h), 15)) for h in variants]
        joint = [path_length(median_path(project(points_px, h), w)) for h in variants for w in WINDOWS]
        result["players"][pid] = {
            "raw_track_id": config["raw_id"], "measured_frames_inclusive": [config["first"], 336],
            "observed_box_count": len(points_px),
            "main_15_frame_proxy_m": window_values["15"],
            "smoothing_window_path_m": window_values,
            "geometry_15_frame_scenario_range_m": [round(min(geometry_15), 2), round(max(geometry_15), 2)],
            "joint_smoothing_geometry_scenario_range_m": [round(min(joint), 2), round(max(joint), 2)],
            "endpoint_displacement_m": round(float(np.linalg.norm(points_m[-1] - points_m[0])), 2),
            "raw_unsmoothed_proxy_path_m": round(path_length(points_m), 2),
            "checked_anchor_comparison": anchor_check(labels, raw, pid, config["raw_id"], main_h),
        }
        paths[pid] = median_path(points_m, 15)
        for frame, px, m in zip(range(config["first"], 337), points_px, points_m):
            rows.append({"frame": frame, "player_id": pid, "proxy_x_px": round(float(px[0]), 3),
                         "proxy_y_px": round(float(px[1]), 3),
                         "candidate_court_x_m": round(float(m[0]), 4),
                         "candidate_court_y_m": round(float(m[1]), 4)})
    OUT.mkdir(parents=True, exist_ok=True)
    draw_map(paths)
    (OUT / "point_candidate_proxy_distance.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (OUT / "point_candidate_proxy_positions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result["players"], indent=2))


if __name__ == "__main__":
    main()
