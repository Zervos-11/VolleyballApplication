"""Compare late #20 contact chords with body-box proxy chords.

This audit is a method disagreement screen, not a physical-distance estimate.
The calibration remains staged and individual contact points are proposals.
"""

from __future__ import annotations

import json

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


ROOT = BASE.parents[2]
CONTACTS = BASE / "r1_p20_late_contact_anchor_review.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
OUT = BASE / "r1_p20_late_anchor_path_consistency.json"
TRIAGE_DISAGREEMENT_M = 0.4


def main() -> None:
    contacts = json.loads(CONTACTS.read_text(encoding="utf-8"))
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert contacts["source_sha256"] == sha256(SOURCE)
    assert contacts["visual_candidate_sha256"] == sha256(VISUAL)
    boxes = {row["frame"]: row["players"]["20"] for row in visual["frame_records"]}
    matrix = cv2.getPerspectiveTransform(np.float32(calibration["points_px"]),
                                         np.float32(calibration["points_court_m"]))

    def project(point: list[float]) -> np.ndarray:
        return cv2.perspectiveTransform(np.float32([[point]]), matrix)[0, 0]

    def chord(first: list[float], second: list[float]) -> float:
        return round(float(np.linalg.norm(project(first) - project(second))), 3)

    rows = []
    reviewed = [row for row in contacts["frames"] if row["floor_point_proposal_px"] is not None]
    for before, after in zip(reviewed, reviewed[1:]):
        first, last = before["frame"], after["frame"]
        foot_first, foot_last = before["floor_point_proposal_px"], after["floor_point_proposal_px"]
        box_first, box_last = boxes[first]["bbox_px"], boxes[last]["bbox_px"]
        contact_chord = chord(foot_first, foot_last)
        box_chord = None
        hybrid_chord = None
        if box_first and box_last:
            x_first = (box_first[0] + box_first[2]) / 2
            x_last = (box_last[0] + box_last[2]) / 2
            box_chord = chord([x_first, box_first[3]], [x_last, box_last[3]])
            hybrid_chord = chord([x_first, foot_first[1]], [x_last, foot_last[1]])
        disagreement = (round(abs(contact_chord - box_chord), 3)
                        if box_chord is not None else None)
        rows.append({
            "start_frame": first, "end_frame": last,
            "contact_target_start": before["source_visual_state"],
            "contact_target_end": after["source_visual_state"],
            "source_contact_chord_m_diagnostic": contact_chord,
            "box_bottom_chord_m_diagnostic": box_chord,
            "body_x_with_contact_y_chord_m_diagnostic": hybrid_chord,
            "absolute_method_disagreement_m": disagreement,
            "review_flag": ("large_method_disagreement" if disagreement is not None
                            and disagreement > TRIAGE_DISAGREEMENT_M else
                            "no_box_comparison" if disagreement is None else
                            "below_triage_threshold"),
        })
    result = {
        "status": "development_contact_target_path_consistency_failed",
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "contact_anchor_sha256": sha256(CONTACTS),
        "staged_calibration_sha256": sha256(CALIBRATION),
        "triage_disagreement_m": TRIAGE_DISAGREEMENT_M,
        "intervals": rows,
        "review_summary": {
            "proposed_anchor_count": len(reviewed),
            "adjacent_anchor_intervals": len(rows),
            "comparable_intervals": sum(row["box_bottom_chord_m_diagnostic"] is not None
                                        for row in rows),
            "large_disagreement_intervals": [[row["start_frame"], row["end_frame"]]
                                             for row in rows if row["review_flag"] ==
                                             "large_method_disagreement"],
            "body_x_correction_still_large_at_21380_21390": next(
                row["body_x_with_contact_y_chord_m_diagnostic"] for row in rows
                if row["start_frame"] == 21380),
        },
        "interpretation": "Different feet and midpoint conventions can change both image x and court depth. Replacing shoe x with box-centre x does not fix the depth change at 21380-21390. The 0.4 m threshold only queues review; it is not an error bound. Chord totals and dense distance are intentionally not reported.",
        "distance_released": False,
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["review_summary"])


if __name__ == "__main__":
    main()
