"""Record a source-visual floor-level midpoint proposal, separate from saved clicks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
MANIFEST = CALIBRATION.parent / "calibration_manifest.json"
REVIEW = BASE / "r1_floor_contact_review.json"
FRAME = 21064

# Manual source-image readings from r1_sole_detail_21064.jpg. The ranges are
# visual brackets for this one frame, not measured annotation uncertainty.
PROPOSALS = {
    "11": {"midpoint_px": [1066, 767], "pixel_bracket_xyxy": [1061, 764, 1071, 770],
           "observation": "Both white sole-floor edges are visible. Saved click is between shoes but above their floor-level midpoint."},
    "12": {"midpoint_px": [1305, 762], "pixel_bracket_xyxy": [1300, 759, 1310, 765],
           "observation": "Two blue-white shoe soles appear planted behind #10. Saved click is between them but above the apparent floor-level midpoint."},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project(points: list[list[float]], matrix: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(np.asarray(points, dtype=np.float32).reshape(-1, 1, 2),
                                    matrix).reshape(-1, 2)


def main() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if review["match_id"] != manifest["match_id"] or review["rally_id"] != "r1":
        raise ValueError("Source mismatch")
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))
    capture = cv2.VideoCapture(str(SOURCE))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, FRAME)
        okay, image = capture.read()
        if not okay:
            raise RuntimeError("Could not decode source frame")
    finally:
        capture.release()

    left_detail = cv2.resize(image[650:820, 980:1140], (640, 680),
                             interpolation=cv2.INTER_LINEAR)
    right_detail = cv2.resize(image[650:820, 1240:1400], (640, 680),
                              interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(str(BASE / "r1_sole_detail_21064.jpg"),
                cv2.hconcat([left_detail, right_detail]))

    x1, y1, x2, y2 = manifest["camera_segments"]["camera_r1"]["heldout_net_line_px"]
    overlay = image.copy()
    cv2.line(overlay, (x1, y1), (x2, y2), (0, 0, 255), 2, cv2.LINE_AA)
    observations = []
    for player, proposal in PROPOSALS.items():
        saved = review["records"][str(FRAME)][player]
        if saved["state"] != "grounded_contact_visible":
            raise ValueError(f"No grounded saved point for #{player}")
        saved_px = saved["footpoint_px"]
        candidate_px = proposal["midpoint_px"]
        xa, ya, xb, yb = proposal["pixel_bracket_xyxy"]
        if not (xa <= candidate_px[0] <= xb and ya <= candidate_px[1] <= yb):
            raise ValueError("Candidate outside its visual pixel bracket")
        projected = project([candidate_px, [xa, ya], [xa, yb], [xb, ya], [xb, yb]], matrix)
        line_y = y1 + (candidate_px[0] - x1) * (y2 - y1) / (x2 - x1)
        observations.append({
            "player_id": player,
            "saved_draft_point_px": saved_px,
            "analyst_floor_midpoint_candidate_px": candidate_px,
            "hand_selected_pixel_bracket_xyxy": [xa, ya, xb, yb],
            "candidate_court_m_diagnostic": [round(float(v), 3) for v in projected[0]],
            "bracket_court_depth_range_m_diagnostic": [round(float(projected[1:, 1].min()), 3),
                                                        round(float(projected[1:, 1].max()), 3)],
            "candidate_minus_recorded_net_line_y_px": round(candidate_px[1] - line_y, 3),
            "source_observation": proposal["observation"],
            "status": "analyst_visual_proposal_not_saved_annotation",
        })
        cv2.circle(overlay, tuple(round(v) for v in saved_px), 9, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.circle(overlay, tuple(candidate_px), 9, (0, 220, 0), 2, cv2.LINE_AA)
        cv2.rectangle(overlay, (xa, ya), (xb, yb), (0, 220, 0), 1, cv2.LINE_AA)
        cv2.putText(overlay, f"#{player}", (candidate_px[0] + 12, candidate_px[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(overlay, f"#{player}", (candidate_px[0] + 12, candidate_px[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2, cv2.LINE_AA)

    crop = overlay[650:820, 980:1400]
    cv2.imwrite(str(BASE / "r1_near_net_midpoint_proposals_21064.jpg"), cv2.resize(
        crop, (1260, 510), interpolation=cv2.INTER_LINEAR))
    result = {
        "status": "single_frame_source_visual_midpoint_proposals_not_metric_release",
        "match_id": review["match_id"], "rally_id": "r1", "frame_index": FRAME,
        "source_video_sha256_from_record": json.loads((SOURCE.parent / "source_record.json").read_text(
            encoding="utf-8"))["sha256"],
        "saved_review_sha256": sha256(REVIEW),
        "calibration_sha256": sha256(CALIBRATION),
        "heldout_net_line_px": [x1, y1, x2, y2],
        "source_detail": "r1_sole_detail_21064.jpg",
        "proposal_overlay": "r1_near_net_midpoint_proposals_21064.jpg",
        "convention": "When both shoes appear grounded, use an image point at floor level midway between their sole-floor contacts; do not use an ankle-height midpoint. One planted shoe may be used if the other is airborne or hidden. Both airborne means no ground point.",
        "observations": observations,
        "limitation": "Manually estimated pixels and hand-selected brackets on one source frame. The floor line comes from calibration median frames. Proposed points have not been independently checked and do not establish player distance or production court positions.",
        "saved_review_modified": False, "official_annotations_changed": False,
        "production_metric_changed": False,
    }
    (BASE / "r1_near_net_midpoint_proposals_21064.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print([(row["player_id"], row["candidate_court_m_diagnostic"],
            row["bracket_court_depth_range_m_diagnostic"]) for row in observations])


if __name__ == "__main__":
    main()
