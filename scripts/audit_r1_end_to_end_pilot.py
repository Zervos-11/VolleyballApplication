"""Compare isolated API tracks with frozen r1 raw detections and source frames."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_end_to_end_pilot"
FROZEN = ROOT / "data/processed/fqe_r1_boundary_recheck/r1_dense_raw_tracks.json"
FRAMES = [21050, 21064, 21133, 21265, 21310, 21463]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    metrics = json.loads((BASE / "metrics.json").read_text(encoding="utf-8"))
    api = defaultdict(list)
    with (BASE / "tracks_centroids.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            api[int(row["frame"])].append((int(row["track_id"]), float(row["cx"]), float(row["cy"])))
    if sorted(api) != list(range(21050, 21464)):
        raise AssertionError("The API run did not observe the whole candidate interval")
    paired_deltas, mismatch_frames = [], []
    for frame in range(21050, 21464):
        expected = sorted((row["track_id"], (row["bbox"][0] + row["bbox"][2]) / 2,
                           row["bbox"][3]) for row in frozen["frames"][str(frame)])
        observed = sorted(api[frame])
        if len(expected) != len(observed) or [row[0] for row in expected] != [row[0] for row in observed]:
            mismatch_frames.append(frame)
            continue
        paired_deltas.extend(
            float(np.hypot(a[1] - b[1], a[2] - b[2])) for a, b in zip(expected, observed)
        )
    cap = cv2.VideoCapture(str(BASE / "source_FqE5pTJqx8g.mp4"))
    tiles = []
    try:
        for frame in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, source = cap.read()
            if not okay:
                raise RuntimeError(f"Cannot decode {frame}")
            for _, x, y in api[frame]:
                cv2.circle(source, (round(x), round(y)), 7, (0, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(source, (round(x), round(y)), 9, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(source, f"API frame {frame} | {len(api[frame])} detections",
                        (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 0, 0), 5, cv2.LINE_AA)
            cv2.putText(source, f"API frame {frame} | {len(api[frame])} detections",
                        (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 255, 255), 2, cv2.LINE_AA)
            tiles.append(cv2.resize(source, (640, 360), interpolation=cv2.INTER_AREA))
    finally:
        cap.release()
    cv2.imwrite(str(BASE / "source_overlay_sheet.jpg"),
                cv2.vconcat([cv2.hconcat(tiles[:3]), cv2.hconcat(tiles[3:])]))
    quality = metrics["per_rally"][0]["quality"]
    result = {
        "status": "api_run_vs_frozen_raw_tracks",
        "source_sha256": metrics["source_sha256"],
        "frozen_raw_sha256": sha256(FROZEN),
        "api_tracks_sha256": sha256(BASE / "tracks_centroids.csv"),
        "metrics_sha256": sha256(BASE / "metrics.json"),
        "candidate_frames": [21050, 21464],
        "api_observation_frames": len(api),
        "api_raw_observations": sum(map(len, api.values())),
        "frozen_raw_observations": sum(map(len, frozen["frames"].values())),
        "frames_with_different_track_ids_or_counts": mismatch_frames,
        "paired_observations": len(paired_deltas),
        "paired_position_delta_px_max": round(max(paired_deltas), 4) if paired_deltas else None,
        "paired_position_delta_px_median": round(float(np.median(paired_deltas)), 4) if paired_deltas else None,
        "source_overlay_sheet": "source_overlay_sheet.jpg",
        "sampled_overlay_frames": FRAMES,
        "quality_flags": {name: quality[name] for name in
                          ("team_identity_verified", "ground_positions_verified", "position_source")},
        "interpretation": "Tests repeatability and source-frame alignment of raw API observations. It does not validate target-team identity, shoe-floor positions or physical movement.",
    }
    (BASE / "AUDIT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{len(mismatch_frames)} frame ID/count mismatches; "
          f"{len(paired_deltas)} paired observations; max delta {result['paired_position_delta_px_max']} px")


if __name__ == "__main__":
    main()
