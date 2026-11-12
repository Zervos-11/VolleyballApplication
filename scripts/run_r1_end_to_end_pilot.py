"""Run the production tracking/metrics path on the bounded r1 point in isolation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from services.api.processing import compute_tracking_metrics


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4"
SOURCE_RECORD = ROOT / "data/matches/yt_FqE5pTJqx8g/source_record.json"
CANDIDATE = ROOT / "data/processed/fqe_r1_boundary_recheck/R1_CASE_STUDY_CANDIDATE.json"
OUTPUT = ROOT / "data/processed/fqe_r1_end_to_end_pilot"
VIDEO = OUTPUT / SOURCE.name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    record = json.loads(SOURCE_RECORD.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    start = candidate["candidate_interval"]["start_frame"]
    end = candidate["candidate_interval"]["end_frame_exclusive"]
    fps = float(record["camera"]["fps"])
    assert [start, end] == [21050, 21464]
    assert sha256(SOURCE) == record["sha256"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not VIDEO.exists():
        os.link(SOURCE, VIDEO)
    if not VIDEO.samefile(SOURCE):
        raise RuntimeError("Isolated input must be a hard link to the verified source")
    (OUTPUT / "source_record.json").write_text(
        json.dumps({"video_file": VIDEO.name, "sha256": record["sha256"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "camera": {"fps": fps},
        "rally_start_pad_s": 0,
        "rally_end_pad_s": 0,
        "jersey_ocr": False,
        "use_pose_ankles": False,
        "rallies": [{"rally_id": "r1_candidate", "t_start": start / fps, "t_end": end / fps}],
    }
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    result = compute_tracking_metrics(
        OUTPUT, metadata["rallies"], metadata, fps=fps, max_frames=end - start,
    )
    if len(result) != 1 or result[0]["quality"]["start_frame"] != start or result[0]["quality"]["end_frame_exclusive"] != end:
        raise AssertionError("Processing returned the wrong frame interval")
    payload = {
        "schema_version": "v1", "match_id": "yt_FqE5pTJqx8g",
        "status": "exploratory_api_output_not_player_metrics",
        "source_sha256": record["sha256"],
        "candidate_sha256": sha256(CANDIDATE),
        "calibration_activated": False,
        "annotation_or_official_match_files_changed": False,
        "per_rally": result,
    }
    (OUTPUT / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    quality = result[0]["quality"]
    print(f"r1 {start}:{end}: {quality['frames_with_track_observations']}/{end-start} frames with detections; "
          f"{quality['raw_track_observations']} raw observations; status={quality['status']}", flush=True)


if __name__ == "__main__":
    main()
