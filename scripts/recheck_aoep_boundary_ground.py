"""Record the source-only AoEP endpoint and ground-position recheck."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
VIDEO = MATCH / "source_AoEP-YiWRvc.mp4"
CAL = MATCH / "homography.json"
BOUNDARY = MATCH / "pilot/boundary_candidate.json"
POSE_TRIAL = DIR / "pose_guided_contact_trial_75205_75229.json"
OUTPUT = DIR / "boundary_ground_recheck.json"
CROPS = ["end_net_75294_75305.jpg", "end_net_75306_75317.jpg",
         "end_net_75318_75329.jpg", "floor_proxy_source_75205_75229.jpg"]
FRAMES = [75180, 75205, 75229, 75320, 75340]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    source_hash = sha256(VIDEO)
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    pose_trial = json.loads(POSE_TRIAL.read_text(encoding="utf-8"))
    if not all(item["source_sha256"] == source_hash for item in (cal, boundary, pose_trial)):
        raise ValueError("source mismatch")
    cap = cv2.VideoCapture(str(VIDEO))
    still = {}
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(frame)
            still[frame] = cv2.cvtColor(image[20:175, 325:1050], cv2.COLOR_BGR2GRAY).astype(np.float32)
    finally:
        cap.release()
    window = cv2.createHanningWindow((still[75180].shape[1], still[75180].shape[0]), cv2.CV_32F)
    camera_checks = []
    for frame in FRAMES[1:]:
        (dx, dy), response = cv2.phaseCorrelate(still[75180], still[frame], window)
        camera_checks.append({"frame_index": frame, "shift_from_75180_px": [round(dx, 3), round(dy, 3)],
                              "response": round(response, 3)})
    if max(abs(v) for check in camera_checks for v in check["shift_from_75180_px"]) >= 1:
        raise ValueError("sampled static background shifted at least one pixel")
    crop_hashes = {name: sha256(DIR / name) for name in CROPS}
    record = {
        "status": "source_only_boundary_unresolved_ground_positions_not_validated",
        "match_id": "yt_AoEP-YiWRvc",
        "rally_id": "point_21m",
        "source_sha256": source_hash,
        "calibration_sha256": sha256(CAL),
        "boundary_candidate_sha256": sha256(BOUNDARY),
        "pose_guided_contact_trial_sha256": sha256(POSE_TRIAL),
        "source_crop_sha256": crop_hashes,
        "endpoint_review_frames_inclusive": [75294, 75329],
        "endpoint_observation": "The final net exchange is crowded and the decisive ball-floor or dead-ball event is hidden. An orange ball-like object appears above the far-side players later in the crop, but its relationship to the preceding live point cannot be established from these frames.",
        "serve_contact_candidate_frame_unchanged": boundary["serve_contact_candidate_frame"],
        "first_dead_ball_candidate_interval_unchanged": boundary["end_first_dead_ball_candidate_interval"],
        "end_frame_exclusive_selected": None,
        "ground_review_frames": [75205, 75229],
        "ground_observation": "Visible shoes and stance changes show that box-bottom centres are not always shoe-floor contacts. The pose-guided cue often moves a marker toward a shoe but does not establish weight bearing or an exact sole contact. No independent contact labels exist on these sampled frames.",
        "camera_static_roi_px": [325, 20, 1050, 175],
        "camera_registration_from_75180": camera_checks,
        "camera_interpretation": "The sampled upper-wall patch shifts less than one pixel, supporting a stable camera over these frames. Static-camera alignment does not validate the court-line assignment or ground-contact points.",
        "calibration_use_for_metrics": cal["use_for_metrics"],
        "official_selection_changed": False,
        "annotation_changes": False,
    }
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    print("max sampled camera shift px", max(abs(v) for check in camera_checks for v in check["shift_from_75180_px"]))


if __name__ == "__main__":
    main()
