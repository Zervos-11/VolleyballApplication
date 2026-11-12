"""Freeze a verifiable local manifest for the AoEP 50-frame development case study."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_AoEP-YiWRvc"
DIR = ROOT / "data/processed/aoep_new_source"
OUTPUT = DIR / "CASE_STUDY_MANIFEST.json"
SOURCE = MATCH / "source_AoEP-YiWRvc.mp4"
CAL = MATCH / "homography.json"
ANNOTATIONS = MATCH / "pilot/player_annotations/point_21m.json"
SELECTION = MATCH / "pilot/selection.json"
RAW = DIR / "raw_74880_75540.json"
PATHS = DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.json"
DISTANCE = DIR / "reviewed_distance_estimate_75180_75229.json"
ZONE = DIR / "two_player_zone_readout.json"
SIDELINE = DIR / "player5_sideline_band.json"
BOUNDARY = DIR / "boundary_recheck.json"
RECHECK = DIR / "boundary_ground_recheck.json"
EVIDENCE = [
    ROOT / "scripts/render_aoep_heldout_source_sheets.py",
    ROOT / "scripts/evaluate_aoep_source_slice.py",
    ROOT / "DELIVERABLES/AOEP_SOURCE_SLICE_AUDIT.md",
    DIR / "heldout_source_review/visibility_reference_75180_75229.json",
    DIR / "heldout_source_review/development_audit_75180_75229.json",
    ROOT / "scripts/build_aoep_candidate_court_paths.py",
    ROOT / "scripts/build_aoep_sideline_band.py",
    ROOT / "scripts/build_aoep_distance_estimate.py",
    ROOT / "scripts/build_aoep_case_study_manifest.py",
    ROOT / "scripts/recheck_aoep_boundary_ground.py",
    CAL, ANNOTATIONS, SELECTION, RAW, PATHS, DISTANCE, ZONE, SIDELINE, BOUNDARY,
    DIR / "candidate_court_paths_75180_75229_7e8d7ea5cd.jpg",
    DIR / "two_player_zone_readout.jpg",
    DIR / "player5_sideline_band.jpg",
    DIR / "player4_source_qc_75180_75204.jpg",
    DIR / "player4_source_qc_75205_75229.jpg",
    DIR / "libero_source_qc_75180_75204.jpg",
    DIR / "libero_source_qc_75205_75229.jpg",
    DIR / "player5_source_qc_75180_75204.jpg",
    DIR / "player5_source_qc_75205_75229.jpg",
    DIR / "setter_grounded_qc_75211_75229.jpg",
    DIR / "floor_proxy_visual_qc_75205_75229.json",
    DIR / "pose_ankle_floor_proxy_75205_75229.json",
    DIR / "pose_guided_contact_trial_75205_75229.json",
    DIR / "floor_proxy_source_75205_75229.jpg",
    DIR / "end_net_75294_75305.jpg",
    DIR / "end_net_75306_75317.jpg",
    DIR / "end_net_75318_75329.jpg",
    DIR / "boundary_ground_recheck.json",
] + [DIR / f"heldout_source_review/source_{index:02d}.jpg" for index in range(1, 11)]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    source_hash = sha256(SOURCE)
    selection, calibration, annotations = load(SELECTION), load(CAL), load(ANNOTATIONS)
    raw, paths, distance = load(RAW), load(PATHS), load(DISTANCE)
    zone, sideline, boundary, recheck = load(ZONE), load(SIDELINE), load(BOUNDARY), load(RECHECK)
    if not all(record["source_sha256"] == source_hash for record in
               (selection, calibration, raw, paths, distance, zone, sideline, boundary, recheck)):
        raise ValueError("source hash mismatch")
    if selection["raw_prediction_sha256"] != sha256(RAW) or paths["raw_sha256"] != sha256(RAW):
        raise ValueError("raw prediction hash mismatch")
    if any(record["calibration_sha256"] != sha256(CAL) for record in
           (paths, distance, zone, sideline)):
        raise ValueError("calibration hash mismatch")
    if paths["saved_annotations_sha256"] != sha256(ANNOTATIONS) or distance["saved_annotations_sha256"] != sha256(ANNOTATIONS):
        raise ValueError("annotation hash mismatch")
    if any(record["candidate_path_sha256"] != sha256(PATHS) for record in
           (distance, zone, sideline)):
        raise ValueError("candidate path hash mismatch")
    if (boundary["end_frame_exclusive_selected"] is not None
            or recheck["end_frame_exclusive_selected"] is not None
            or recheck["calibration_sha256"] != sha256(CAL)
            or calibration["use_for_metrics"]):
        raise ValueError("case-study release gates unexpectedly changed")
    first, last = distance["frame_range_inclusive"]
    if [first, last] != [75180, 75229] or paths["frame_range_inclusive"] != [first, last]:
        raise ValueError("frame range mismatch")
    saved = annotations.get("frames", {})
    saved_in_slice = {frame: row for frame, row in saved.items() if first <= int(frame) <= last}
    complete = sum(bool(row.get("all_players_accounted_for")) for row in saved_in_slice.values())
    cap = cv2.VideoCapture(str(SOURCE))
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()
    if width != 1280 or height != 720 or fps <= 0:
        raise ValueError("unexpected video properties")
    files = []
    for path in EVIDENCE:
        if not path.is_file():
            raise FileNotFoundError(path)
        files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                      "size_bytes": path.stat().st_size})
    result = {
        "schema_version": "aoep_case_study_manifest_v1",
        "status": "frozen_local_development_case_study_not_validated_release",
        "match_id": "yt_AoEP-YiWRvc",
        "rally_id": "point_21m",
        "scope": {"first_frame": first, "last_frame_inclusive": last, "frame_count": last - first + 1,
                  "complete_rally": False, "source_frame_rate_fps": round(fps, 5),
                  "image_size_px": [width, height]},
        "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": source_hash,
                   "size_bytes": SOURCE.stat().st_size},
        "annotation_snapshot": {"saved_near_frames_in_slice": len(saved_in_slice),
                                "complete_near_frames_in_slice": complete,
                                "assisted_or_partial": True,
                                "independent_ground_truth": False},
        "release_gates": {"first_dead_ball_frame_verified": False,
                          "calibration_enabled_for_metrics": False,
                          "independent_dense_labels_complete": False,
                          "physical_travel_validated": False},
        "available_result": "Single-reviewer visual trace, coarse-zone case study, four rough smoothed box-bottom path estimates, and a 50-frame source-visibility development audit. No formal accuracy, speed, complete-rally distance or validated team-coverage score.",
        "rebuild_commands": [
            ".\\.venv\\Scripts\\python.exe scripts/evaluate_aoep_source_slice.py",
            ".\\.venv\\Scripts\\python.exe scripts/build_aoep_sideline_band.py",
            ".\\.venv\\Scripts\\python.exe scripts/build_aoep_distance_estimate.py",
            ".\\.venv\\Scripts\\python.exe scripts/build_aoep_case_study_manifest.py",
        ],
        "files": files,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    print(f"{len(saved_in_slice)} saved near frames; {complete} complete; {len(files)} evidence files")


if __name__ == "__main__":
    main()
