"""Project checked D79 footpaths through a provisional 9 m court geometry."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
IMAGE = ROOT / "data/matches/yt_D79JrsJsFgs/screening/court_median_40s.jpg"
OUT = ROOT / "data/processed/d79_new_source"


def intersection(first, second):
    # y = intercept + slope * x
    x = (second[0] - first[0]) / (first[1] - second[1])
    return [x, first[0] + first[1] * x]


def calibration(net_shift=0, attack_shift=0):
    left = (571.0, -0.3453)
    right = (188.9, 0.3072)
    net = (504.5 + net_shift, -0.0185)
    attack = (553.5 + attack_shift, -0.0185)
    image_points = np.asarray([
        intersection(left, net), intersection(right, net),
        intersection(left, attack), intersection(right, attack),
    ], dtype=np.float32)
    court_points = np.asarray([[0, 9], [9, 9], [0, 6], [9, 6]], dtype=np.float32)
    return cv2.getPerspectiveTransform(image_points, court_points), image_points


def path_length(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()) if len(points) > 1 else 0.0


def median_path(points, width):
    half = width // 2
    return np.asarray([
        np.median(points[max(0, i - half):min(len(points), i + half + 1)], axis=0)
        for i in range(len(points))
    ])


def project(points, homography):
    return cv2.perspectiveTransform(np.asarray(points, dtype=np.float32).reshape(-1, 1, 2), homography).reshape(-1, 2)


def main():
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    by_id = {}
    for frame in range(240, 290):
        for row in labels["frames"][str(frame)]["players"]:
            by_id.setdefault(str(row["player_id"]), []).append((frame, row.get("footpoint")))
    main_h, corners = calibration()
    variants = [calibration(n, a)[0] for n in (-8, 0, 8) for a in (-3, 0, 3)]
    result = {
        "status": "provisional_user_checked_assisted_case_study_not_validated_metric",
        "labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "court_width_m": 9,
        "net_to_attack_line_m": 3,
        "image_corners_net_left_net_right_attack_left_attack_right_px": corners.tolist(),
        "geometry_basis": "Two visible black diagonal near-court sidelines; near attack line y=553.5-0.0185*x; provisional net-floor line y=504.5-0.0185*x guided by post bases. Net-floor line is partly hidden, so geometry remains a candidate.",
        "sensitivity": "Nine geometry variants shift the inferred net line by -8/0/+8 px and the attack line by -3/0/+3 px. The interval is scenario sensitivity, not a statistical confidence interval. Five-frame coordinate-wise median is applied to projected points before summing steps.",
        "occlusion_policy": "Only adjacent visible frames within each segment are joined. No missing player movement is estimated.",
        "players": {},
    }
    for pid, entries in sorted(by_id.items(), key=lambda item: int(item[0])):
        segments = []
        current = []
        for frame, foot in entries:
            if foot is None:
                if current:
                    segments.append(current)
                    current = []
            else:
                current.append((frame, foot))
        if current:
            segments.append(current)
        if not segments or max(map(len, segments)) < 5:
            result["players"][pid] = {"five_frame_median_path_m": None, "reason": "fewer than five consecutive visible floor points"}
            continue
        def measure(h, window=5):
            return sum(path_length(median_path(project([p for _, p in s], h), window))
                       for s in segments if len(s) >= window)
        estimates = [measure(h) for h in variants]
        raw = sum(path_length(project([p for _, p in s], main_h)) for s in segments)
        main_points = [project([p for _, p in s], main_h) for s in segments]
        outside = sum(int(((p[:, 0] < 0) | (p[:, 0] > 9) | (p[:, 1] < 0) | (p[:, 1] > 9)).sum()) for p in main_points)
        candidate = {
            "observed_segments_inclusive": [[s[0][0], s[-1][0]] for s in segments],
            "visible_footpoints": sum(len(s) for s in segments),
            "outside_candidate_court_points": outside,
            "outside_count_by_net_line_shift_px": {
                str(shift): sum(int((project([p for _, p in s], calibration(shift, 0)[0])[:, 1] > 9).sum())
                                for s in segments)
                for shift in (-16, -12, -8, -4, 0, 4, 8)
            },
        }
        if outside:
            candidate.update({"five_frame_median_path_m": None,
                              "reason": "one or more clicked shoe points project beyond the near court; airborne or net-line ambiguity needs source review"})
        else:
            points = [p for segment in segments for _, p in segment]
            variant_points = [project(points, h) for h in variants]
            def lane(value):
                return "left" if value < 3 else "middle" if value < 6 else "right"
            def depth(value):
                return "front" if value >= 6 else "back"
            variant_lanes = [[lane(p[0]) for p in path] for path in variant_points]
            variant_depths = [[depth(p[1]) for p in path] for path in variant_points]
            candidate.update({
                "five_frame_median_path_m": round(measure(main_h), 3),
                "geometry_sensitivity_range_m": [round(min(estimates), 3), round(max(estimates), 3)],
                "smoothing_window_path_m": {str(window): round(measure(main_h, window), 3)
                                            for window in (3, 5, 7, 9, 11, 15)},
                "endpoint_displacement_m": round(sum(float(np.linalg.norm(p[-1] - p[0]))
                                                     for p in main_points), 3),
                "raw_footpoint_path_m": round(raw, 3),
                "zone_diagnostic": {
                    "lateral_counts_main_geometry": dict(Counter(variant_lanes[4])),
                    "front_back_counts_main_geometry": dict(Counter(variant_depths[4])),
                    "lateral_frames_agreeing_all_nine_geometries": sum(len(set(values)) == 1 for values in zip(*variant_lanes)),
                    "front_back_frames_agreeing_all_nine_geometries": sum(len(set(values)) == 1 for values in zip(*variant_depths)),
                },
            })
        result["players"][pid] = candidate
    image = cv2.imread(str(IMAGE))
    if image is None:
        raise FileNotFoundError(IMAGE)
    p = np.rint(corners).astype(int)
    cv2.line(image, tuple(p[0]), tuple(p[1]), (20, 20, 220), 3)
    cv2.line(image, tuple(p[2]), tuple(p[3]), (20, 180, 20), 3)
    cv2.line(image, tuple(p[0]), tuple(p[2]), (220, 60, 20), 3)
    cv2.line(image, tuple(p[1]), tuple(p[3]), (220, 60, 20), 3)
    cv2.putText(image, "PROVISIONAL: red net / green attack / blue sidelines", (25, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.73, (0, 0, 0), 2, cv2.LINE_AA)
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "provisional_court_geometry.jpg"), image)
    (OUT / "provisional_court_paths_240_289.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["players"], indent=2))


if __name__ == "__main__":
    main()
