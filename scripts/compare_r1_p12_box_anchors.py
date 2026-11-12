"""Compare box-centre motion from a seeded foot anchor with reviewed #12 contacts."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_six_slot_visual_candidate.json"
CONTACTS = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_p12_contact_checks.json"
CALIBRATION = ROOT / "data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json"
OUTPUT = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_p12_box_anchor_comparison.json"
SEED_FRAME = 21070


def centre(box):
    return np.asarray([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2], dtype=float)


def project(point, transform):
    return cv2.perspectiveTransform(np.float32([[point]]), transform)[0, 0].astype(float)


def main():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    contacts = json.loads(CONTACTS.read_text(encoding="utf-8"))
    cal = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    transform = cv2.getPerspectiveTransform(np.asarray(cal["points_px"], np.float32),
                                             np.asarray(cal["points_court_m"], np.float32))
    frames = {item["frame"]: item["players"]["12"] for item in record["frame_records"]}
    seed_contact = next(item["contact_px"] for item in contacts["rows"]
                        if item["frame_index"] == SEED_FRAME)
    seed_centre = centre(frames[SEED_FRAME]["bbox_px"])
    rows = []
    for checked in contacts["rows"]:
        if checked["contact_px"] is None:
            continue
        frame = checked["frame_index"]
        box = frames[frame]["bbox_px"]
        if box is None:
            continue
        actual = project(checked["contact_px"], transform)
        body_centre = centre(box)
        bottom_centre = np.asarray([(box[0] + box[2]) / 2, box[3]], dtype=float)
        translated_foot = np.asarray(seed_contact, dtype=float) + body_centre - seed_centre
        candidates = {
            "body_centre": body_centre,
            "bottom_centre": bottom_centre,
            "seeded_centre_translation": translated_foot,
        }
        row = {"frame": frame, "reviewed_contact_px": checked["contact_px"]}
        for name, pixel in candidates.items():
            projected = project(pixel, transform)
            row[name + "_court_m"] = [round(float(v), 3) for v in projected]
            row[name + "_error_to_reviewed_m"] = round(float(np.linalg.norm(projected - actual)), 3)
        rows.append(row)
    summary = {}
    for name in ("body_centre", "bottom_centre", "seeded_centre_translation"):
        errors = [row[name + "_error_to_reviewed_m"] for row in rows]
        outside = sum(any(v < 0 or v > 9 for v in row[name + "_court_m"]) for row in rows)
        summary[name] = {"median_error_m": round(float(np.median(errors)), 3),
                         "max_error_m": max(errors), "outside_near_court_samples": outside}
    result = {
        "status": "single_seed_box_centre_vs_checked_contact_diagnostic",
        "record_sha256": hashlib.sha256(RECORD.read_bytes()).hexdigest(),
        "contacts_sha256": hashlib.sha256(CONTACTS.read_bytes()).hexdigest(),
        "calibration_sha256": hashlib.sha256(CALIBRATION.read_bytes()).hexdigest(),
        "seed_frame": SEED_FRAME,
        "seed_contact_px": seed_contact,
        "method": "Translate the reviewed seed foot point by the change in body-box centre, then project the translated point onto the staged court. Compare with direct body-centre and box-bottom projection on other reviewed frames.",
        "rows": rows,
        "summary": summary,
        "limit": "Eight single-reviewer source contact samples are diagnostic, not dense ground truth. No new distance is published from this comparison.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
