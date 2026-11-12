"""Summarize source-reviewed AoEP players in coarse diagnostic court zones."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
PATH = DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.json"
CALIBRATION = MATCH / "homography.json"
OUT = DIR / "two_player_zone_readout.json"
PREVIEW = DIR / "two_player_zone_readout.jpg"
PLAYERS = {"yellow_centre_4": "Yellow #4", "navy_libero_10": "Navy #10"}
REVIEW_SHEETS = {
    "yellow_centre_4": ["player4_source_qc_75180_75204.jpg", "player4_source_qc_75205_75229.jpg"],
    "navy_libero_10": ["libero_source_qc_75180_75204.jpg", "libero_source_qc_75205_75229.jpg"],
}
ZONE_EDGES_M = (0, 3, 6, 9)
BOUNDARY_MARGIN_M = 0.3


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(path):
    counts = Counter()
    robust_counts = Counter()
    positions = []
    for key, row in path.items():
        if not row["candidate_ground_position"]:
            raise ValueError(f"missing candidate point at {key}")
        x, y = row["court_position_m_diagnostic"]
        if not (0 <= x < 9 and 0 <= y < 9):
            raise ValueError(f"position outside court at {key}")
        zone = (int(x // 3), int(y // 3))
        margin = min(abs(value - boundary)
                     for value in (x, y) for boundary in ZONE_EDGES_M)
        counts[zone] += 1
        if margin > BOUNDARY_MARGIN_M:
            robust_counts[zone] += 1
        positions.append((x, y))
    xs, ys = zip(*positions)
    return {
        "frame_count": len(path),
        "zone_counts": {f"x{ix}_y{iy}": count for (ix, iy), count in sorted(counts.items())},
        "zone_counts_clear_of_grid_lines": {
            f"x{ix}_y{iy}": count for (ix, iy), count in sorted(robust_counts.items())
        },
        "frames_clear_of_grid_lines": sum(robust_counts.values()),
        "projected_extent_m": {
            "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys)
        },
    }


def render(summary):
    image = np.full((520, 940, 3), 246, np.uint8)
    for index, player in enumerate(PLAYERS):
        x0 = 55 + index * 465
        cv2.putText(image, PLAYERS[player], (x0, 38), cv2.FONT_HERSHEY_SIMPLEX,
                    .8, (30, 30, 30), 2)
        data = summary[player]
        for iy in range(3):
            for ix in range(3):
                x1, y1 = x0 + ix * 120, 70 + (2 - iy) * 120
                key = f"x{ix}_y{iy}"
                count = data["zone_counts"].get(key, 0)
                robust = data["zone_counts_clear_of_grid_lines"].get(key, 0)
                shade = max(80, 238 - count * 3)
                cv2.rectangle(image, (x1, y1), (x1 + 120, y1 + 120),
                              (shade, 238, shade), -1)
                cv2.rectangle(image, (x1, y1), (x1 + 120, y1 + 120),
                              (80, 80, 80), 1)
                if count:
                    cv2.putText(image, str(count), (x1 + 42, y1 + 58),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (25, 25, 25), 2)
                    cv2.putText(image, f"{robust} clear", (x1 + 17, y1 + 87),
                                cv2.FONT_HERSHEY_SIMPLEX, .42, (50, 50, 50), 1)
        cv2.putText(image, "net", (x0 + 300, 62), cv2.FONT_HERSHEY_SIMPLEX,
                    .55, (50, 50, 50), 1)
        cv2.putText(image, "near baseline", (x0 + 220, 455),
                    cv2.FONT_HERSHEY_SIMPLEX, .45, (50, 50, 50), 1)
    cv2.putText(image, "50-frame source-reviewed development proxy; no speed/distance",
                (55, 495), cv2.FONT_HERSHEY_SIMPLEX, .55, (20, 20, 20), 1)
    if not cv2.imwrite(str(PREVIEW), image):
        raise OSError(PREVIEW)


def main():
    source = json.loads(PATH.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration["use_for_metrics"] is not False:
        raise ValueError("expected a staged diagnostic calibration")
    for names in REVIEW_SHEETS.values():
        for name in names:
            if not (DIR / name).is_file():
                raise FileNotFoundError(name)
    summary = {player: summarize(source["players"][player]) for player in PLAYERS}
    if any(item["frame_count"] != 50 for item in summary.values()):
        raise ValueError("expected 50 points per player")
    payload = {
        "status": "source_reviewed_single_reviewer_development_zone_summary",
        "source_sha256": source["source_sha256"],
        "candidate_path_sha256": sha256(PATH),
        "calibration_sha256": sha256(CALIBRATION),
        "frame_range_inclusive": [75180, 75229],
        "method": "3x3 zones on the staged 9m near court from bbox bottom-centre projected points",
        "zone_edges_m": list(ZONE_EDGES_M),
        "clear_of_grid_line_margin_m": BOUNDARY_MARGIN_M,
        "visual_review": "All 50 source frames visually checked for each listed player's box identity and foot region; single-reviewer development evidence, not independent ground truth or exact shoe contact.",
        "source_review_sheets": REVIEW_SHEETS,
        "players": summary,
        "distance_speed_coverage_published": False,
        "limitation": "Box-bottom and line-fit error may move points across zone boundaries, especially for navy #10. A clear-of-grid-line count is shown separately. These data do not validate exact movement, speed, tracking accuracy, or the full rally.",
        "preview": PREVIEW.name,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    render(summary)
    print(json.dumps({key: {"zones": value["zone_counts"],
                            "clear_frames": value["frames_clear_of_grid_lines"]}
                      for key, value in summary.items()}))


if __name__ == "__main__":
    main()
