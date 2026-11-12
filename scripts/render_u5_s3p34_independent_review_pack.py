"""Render unboxed native-resolution frames for an independent S3 P34 review.

The templates contain no tracker predictions or existing review verdicts.
They are local research materials; this script never fills reviewer answers.
"""

import csv
import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14"
SCREEN = BASE / "screening"
OUT = SCREEN / "s3p34_independent_review_pack"
VIDEO = BASE / "source_720p.mp4"
SAMPLED = SCREEN / "s3p34_reviewed_sample_ledger.json"
JERSEYS = ("28", "12", "15", "7", "19", "21")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sampled = json.loads(SAMPLED.read_text(encoding="utf-8"))
    sample_numbers = [row["source_frame"] for row in sampled["frames"]]
    assert sample_numbers == list(range(36000, 36139, 6))
    start_numbers = list(range(35986, 36001))
    end_numbers = list(range(36138, 36151))
    calibration_number = 36072
    requested = sorted(set(sample_numbers + start_numbers + end_numbers + [calibration_number]))
    assert len(requested) == 50
    OUT.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError("Could not open source video")
    image_hashes = {}
    for number in requested:
        capture.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, image = capture.read()
        if not ok or image.shape[:2] != (720, 1280):
            raise RuntimeError(f"Could not decode native source frame {number}")
        path = OUT / f"unboxed_{number}.png"
        if not cv2.imwrite(str(path), image):
            raise RuntimeError(f"Could not write {path}")
        image_hashes[path.name] = sha(path)
    capture.release()

    with (OUT / "player_review_blank.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("source_frame", "jersey", "image", "identity_status",
                         "ground_status", "shoe_midpoint_x_px", "shoe_midpoint_y_px",
                         "reading_uncertainty_px", "notes"))
        for number in sample_numbers:
            for jersey in JERSEYS:
                writer.writerow((number, jersey, f"unboxed_{number}.png", "", "", "", "", "", ""))
    with (OUT / "event_review_blank.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("source_frame", "event", "image", "ball_contact_or_dead_status", "notes"))
        for number in start_numbers:
            writer.writerow((number, "serve_contact", f"unboxed_{number}.png", "", ""))
        for number in end_numbers:
            writer.writerow((number, "point_end", f"unboxed_{number}.png", "", ""))
    with (OUT / "court_review_blank.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("source_frame", "image", "landmark", "x_px", "y_px", "notes"))
        for landmark in ("near_left_baseline_corner", "near_right_baseline_corner",
                         "near_right_centreline_corner", "near_left_centreline_corner",
                         "left_attack_line_sideline", "right_attack_line_sideline"):
            writer.writerow((calibration_number, f"unboxed_{calibration_number}.png",
                             landmark, "", "", ""))

    manifest = {
        "status": "blank_independent_review_pack_not_completed_validation",
        "point": "S3 P34",
        "source_sha256_claim_from_existing_ledger": sampled["source_sha256"],
        "source_video": str(VIDEO.relative_to(ROOT)).replace("\\", "/"),
        "source_frame_size_px": [1280, 720],
        "reviewer_predictions_hidden": True,
        "sampled_ground_frames": sample_numbers,
        "serve_contact_review_frames": start_numbers,
        "point_end_review_frames": end_numbers,
        "calibration_frame": calibration_number,
        "image_sha256": image_hashes,
        "blank_templates": ["player_review_blank.csv", "event_review_blank.csv",
                             "court_review_blank.csv"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text("\n".join([
        "# S3 P34 independent review packet", "",
        "No second reviewer is available for the current thesis audit. The active "
        "[single-reviewer protocol](../../../../../DELIVERABLES/HONOURS_U5_S3P34_SINGLE_REVIEWER_PROTOCOL.md) "
        "uses the frozen existing marks and keeps this packet as an optional unboxed "
        "source-image aid. The blank forms below contain no observations. If the "
        "original reviewer uses them, label the resulting marks as same-reviewer and "
        "previously exposed to tracker results; do not score them as independent adjudication.", "",
        "All 50 images are native 1280 x 720 source frames with no tracker boxes or earlier annotations. "
        "The blank templates must be filled by a reviewer who has not seen the existing proxy marks where possible. "
        "Keep the completed files separate from these blank templates.", "",
        "1. Copy `event_review_blank.csv` to `event_review_completed.csv`. For the "
        "serve frames 35986–36000, use `before_contact`, `contact`, `after_contact`, "
        "or `uncertain` in `ball_contact_or_dead_status`. For point-ending frames "
        "36138–36150, use `live`, `dead`, or `uncertain`. Record only directly visible "
        "evidence and use `uncertain` when the event cannot be resolved to a frame.",
        "2. Copy `court_review_blank.csv` to `court_review_completed.csv`. On frame 36072, mark four court corners and "
        "both attack-line/sideline intersections independently. Pixel coordinates use "
        "the original 1280 x 720 image.",
        "3. Copy `player_review_blank.csv` to `player_review_completed.csv`. For each of six UCLA jerseys at the 24 five-Hz "
        "source frames. Record identity as `confirmed`, `sequence_only`, or `uncertain`; "
        "ground status as `grounded`, `airborne`, `occluded`, or `uncertain`. "
        "Use `confirmed` only when the jersey digit is readable in the frame; "
        "use `sequence_only` for an assignment followed through neighbouring frames. "
        "If both shoes or their floor contact cannot be read, use `uncertain` for ground status. "
        "Enter an approximate shoe midpoint and a nonnegative `reading_uncertainty_px` "
        "only for readable grounded contact; leave other coordinates blank and "
        "explain in notes. Keep all 144 rows in their original order.", "",
        "This packet can support independent adjudication of the sampled analysis. "
        "It cannot create a continuous six-grounded-player rally where a player is airborne, "
        "and it does not make a post hoc selected window prespecified. "
        "The source footage and extracted images remain local research materials.", "",
        "Score the completed forms with `.\\.venv\\Scripts\\python.exe "
        "scripts/score_u5_s3p34_independent_review.py`. The scorer checks image "
        "hashes and form completeness and reports observed discrepancies; it never "
        "automatically grants strict approval.", "",
        "The manifest binds every unboxed image by SHA-256. Reproduce the pack with "
        "`.\\.venv\\Scripts\\python.exe scripts/render_u5_s3p34_independent_review_pack.py`.",
    ]) + "\n", encoding="utf-8")
    print(f"Wrote {len(requested)} unboxed native source images and blank review templates to {OUT}")


if __name__ == "__main__":
    main()
