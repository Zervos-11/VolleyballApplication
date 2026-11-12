"""Stage the AoEP near-court grid and audit saved floor contacts.

The independent line observations below are approximate pixels read from the
source overlays. This script checks geometry; it does not activate metrics.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
CANDIDATE = MATCH / "pilot/calibration/near_court_candidate.json"
ANNOTATIONS = MATCH / "pilot/player_annotations/point_21m.json"
SOURCE = MATCH / "source_AoEP-YiWRvc.mp4"
CANONICAL = MATCH / "homography.json"
REVIEW = MATCH / "pilot/calibration/geometry_review.json"
EXPECTED_SOURCE_SHA256 = "2b762dfadcc1d725e9f08f3c376a22be276254499493a7af7674086b91910b44"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def projected_line(inverse: np.ndarray, y_m: float) -> list[list[float]]:
    metres = np.array([[[0.0, y_m]], [[9.0, y_m]]], dtype=np.float32)
    projected = cv2.perspectiveTransform(metres, inverse).reshape(2, 2)
    return [[round(float(value), 1) for value in point] for point in projected]


def main() -> None:
    source_hash = sha256(SOURCE)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError("AoEP source video has changed")
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    source = np.asarray(candidate["points_px"], dtype=np.float32)
    target = np.asarray(candidate["points_court_m"], dtype=np.float32)
    if source.shape != (4, 2) or target.shape != (4, 2):
        raise ValueError("four 2D correspondences are required")
    if not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError("non-finite correspondences")
    for polygon in (source, target):
        if not cv2.isContourConvex(polygon) or cv2.contourArea(polygon) < 1:
            raise ValueError("invalid court polygon")
    if candidate.get("image_size") != [1280, 720]:
        raise ValueError("unexpected reference image size")
    if not np.allclose(target, [[1, 0], [7, 0], [7, 6], [1, 6]]):
        raise ValueError("unexpected line-family assignment")
    matrix = cv2.getPerspectiveTransform(source, target)
    if not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) < 1e-12:
        raise ValueError("degenerate homography")
    reprojection = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(4, 2)
    error_m = float(np.max(np.linalg.norm(reprojection - target, axis=1)))
    if error_m > 0.001:
        raise ValueError("calibration anchors failed reprojection")
    inverse = np.linalg.inv(matrix)
    baseline = projected_line(inverse, 0)
    attack = projected_line(inverse, 6)
    net = projected_line(inverse, 9)
    # Net-floor line endpoints were read independently from the source overlays.
    net_observed = np.array([[265, 464], [1167, 463]], dtype=float)
    net_error_px = np.linalg.norm(np.asarray(net) - net_observed, axis=1).tolist()
    if max(net_error_px) > 8:
        raise ValueError("projected net floor line disagrees with the source overlay")

    saved = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    frames = saved.get("frames", {})
    rows = [player for frame in frames.values() for player in frame.get("players", [])]
    usable = [player for player in rows if player.get("position_status") == "visible"
              and isinstance(player.get("footpoint"), list)
              and len(player["footpoint"]) == 2
              and all(isinstance(v, (int, float)) and np.isfinite(v) for v in player["footpoint"])]
    calibration = {
        "schema_version": "v1",
        "image_size": candidate["image_size"],
        "points_px": candidate["points_px"],
        "points_court_m": candidate["points_court_m"],
        "court_bounds_m": [0, 9, 0, 9],
        "court_coordinates": candidate["court_coordinates"],
        "status": "geometry_checked_projection_staged",
        "use_for_metrics": False,
        "source_sha256": source_hash,
        "candidate_sha256": sha256(CANDIDATE),
        "review": "Source-overlay grid checked on frames 74970, 75180 and 75280; net-floor line agrees with independent visual endpoints. Multiple sports markings and ground contacts still need source-frame review before activation.",
    }
    if CANONICAL.exists():
        if json.loads(CANONICAL.read_text(encoding="utf-8")) != calibration:
            raise FileExistsError("canonical calibration differs; refusing to overwrite")
    else:
        CANONICAL.write_text(json.dumps(calibration, indent=2) + "\n", encoding="utf-8")
    review = {
        "source_sha256": source_hash,
        "candidate_sha256": sha256(CANDIDATE),
        "homography_sha256": sha256(CANONICAL),
        "source_overlay_frames": [74970, 75180, 75280],
        "projected_full_court_lines_px": {"baseline": baseline, "attack": attack, "net": net},
        "independent_net_floor_endpoints_px_approx": net_observed.astype(int).tolist(),
        "net_endpoint_error_px": [round(value, 2) for value in net_error_px],
        "max_anchor_reprojection_error_m": error_m,
        "annotation_snapshot_sha256": sha256(ANNOTATIONS),
        "saved_frames": len(frames),
        "saved_player_rows": len(rows),
        "saved_visible_floor_contacts": len(usable),
        "saved_floor_contact_samples_available": bool(usable),
        "court_path_ready": False,
        "limitation": "No metre paths can be made from saved annotations without visible floor contact points. Calibration remains disabled for processing metrics and court filtering.",
    }
    REVIEW.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"calibration": str(CANONICAL), "review": str(REVIEW),
                      "saved_visible_floor_contacts": len(usable),
                      "net_endpoint_error_px": review["net_endpoint_error_px"]}))


if __name__ == "__main__":
    main()
