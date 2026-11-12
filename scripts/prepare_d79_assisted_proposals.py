"""Expose frozen D79 raw person boxes as assisted review suggestions."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_D79JrsJsFgs"
RAW = ROOT / "data/processed/d79_new_source/raw_240_289.json"
SELECTION = MATCH / "pilot/selection.json"
SOURCE = MATCH / "source_record.json"
OUT = MATCH / "pilot/assisted_proposals/in_play_20m24.json"
RALLY_ID = "in_play_20m24"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"Proposals already prepared: {OUT}")
    if any((MATCH / f"pilot/player_annotations/{RALLY_ID}{suffix}.json").exists()
           for suffix in ("", "_far")):
        raise RuntimeError("Refusing to attach new proposals after review labels were saved")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    raw_bytes = RAW.read_bytes()
    raw = json.loads(raw_bytes)
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    if raw["source_sha256"] != source["sha256"] or source["sha256"] != selection["source_sha256"]:
        raise ValueError("Source hash mismatch")
    if raw["first_frame"] != 240 or raw["last_frame"] != 289:
        raise ValueError("Unexpected frozen prediction window")
    if selection["raw_prediction_sha256"] is not None:
        raise ValueError("Selection already has a frozen prediction")
    frames = {
        str(frame): [
            {"proposal_id": f"raw_{frame}_{index}", "bbox": row["bbox"],
             "raw_track_id": row["track_id"], "confidence": row["confidence"]}
            for index, row in enumerate(raw["predictions"][str(frame)])
        ] for frame in range(240, 290)
    }
    proposal = {
        "status": "unverified_frozen_tracker_suggestions",
        "match_id": source["match_id"], "rally_id": RALLY_ID,
        "source_sha256": source["sha256"], "raw_prediction_sha256": raw_hash,
        "frame_range_inclusive": [240, 289],
        "interpretation": "Includes both teams and other people. The reviewer requested visible automatic boxes. Frames where suggestions are displayed are assisted labels, not independent detector ground truth.",
        "frames": frames,
    }
    selection["raw_prediction_sha256"] = raw_hash
    selection["dataset_stage"] = "new_video_assisted_review"
    selection["split"] = "new_video_assisted"
    selection["design"] = "50 source frames selected before inference; raw tracker frozen before saved labels. Automatic box suggestions were requested by the reviewer, so labels made with them are assisted, not independent ground truth."
    source["split"] = "new_video_assisted_review"
    source["annotation_status"] = "assisted_review_ready"
    write_json(OUT, proposal)
    write_json(SELECTION, selection)
    write_json(SOURCE, source)
    print(f"Prepared {len(frames)} frames and {sum(map(len, frames.values()))} raw box suggestions")


if __name__ == "__main__":
    main()
