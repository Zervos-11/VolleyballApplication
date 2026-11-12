"""Build short, explicitly unverified display holds for crossing player boxes.

A held marker is a viewer aid only. It never creates a bounding box, court
position, identity observation, or movement sample.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/fqe_r1_boundary_recheck"
VISUAL = BASE / "r1_six_slot_visual_candidate.json"
OUT = BASE / "r1_occlusion_display_holds.json"
MAX_HOLD_FRAMES = 8
MIN_OVERLAP_OF_SMALLER = 0.15
MAX_OCCLUDER_BOTTOM_ABOVE_FRACTION = 0.10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def overlap_of_smaller(a: list[float], b: list[float]) -> float:
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    smaller = min((a[2] - a[0]) * (a[3] - a[1]),
                  (b[2] - b[0]) * (b[3] - b[1]))
    return width * height / smaller if smaller > 0 else 0.0


def build_holds(frame_records: list[dict], max_hold_frames: int = MAX_HOLD_FRAMES) -> dict[str, dict]:
    if max_hold_frames < 1:
        raise ValueError("max_hold_frames must be positive")
    last_seen: dict[str, tuple[int, list[float]]] = {}
    holds: dict[str, dict] = {}
    for row in frame_records:
        frame = int(row["frame"])
        slots = row["players"]
        present = {player: slot["bbox_px"] for player, slot in slots.items()
                   if slot["box_status"] == "raw_box_candidate" and slot["bbox_px"] is not None}
        frame_holds = {}
        for player, slot in slots.items():
            if slot["box_status"] != "missing":
                continue
            previous = last_seen.get(player)
            if previous is None:
                continue
            seen_frame, anchor_box = previous
            age = frame - seen_frame
            if age < 1 or age > max_hold_frames:
                continue
            height = anchor_box[3] - anchor_box[1]
            if height <= 0:
                continue
            occluders = sorted(other for other, current_box in present.items()
                               if other != player
                               and overlap_of_smaller(anchor_box, current_box) >= MIN_OVERLAP_OF_SMALLER
                               and current_box[3] >= anchor_box[3] -
                               MAX_OCCLUDER_BOTTOM_ABOVE_FRACTION * height)
            if not occluders:
                continue
            frame_holds[player] = {
                "state": "possible_crossing_occlusion_display_hold",
                "last_observed_frame": seen_frame,
                "hold_age_frames": age,
                "display_anchor_px": [round((anchor_box[0] + anchor_box[2]) / 2, 1),
                                      round((anchor_box[1] + anchor_box[3]) / 2, 1)],
                "candidate_occluder_players": occluders,
                "bbox_px": None,
                "court_position_m": None,
                "motion_observed": False,
                "current_position_inferred": False,
            }
        if frame_holds:
            holds[str(frame)] = frame_holds
        for player, box in present.items():
            last_seen[player] = (frame, box)
    return holds


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    holds = build_holds(visual["frame_records"])
    counts = Counter(player for frame in holds.values() for player in frame)
    result = {
        "status": "visual_occlusion_display_aid_not_tracking",
        "match_id": visual["match_id"], "rally_id": visual["rally_id"],
        "visual_candidate_sha256": sha256(VISUAL),
        "thresholds": {"max_hold_frames": MAX_HOLD_FRAMES,
                       "minimum_overlap_of_smaller_box": MIN_OVERLAP_OF_SMALLER,
                       "maximum_occluder_bottom_above_fraction": MAX_OCCLUDER_BOTTOM_ABOVE_FRACTION},
        "hold_frame_count": len(holds),
        "hold_player_frame_count": sum(len(frame) for frame in holds.values()),
        "holds_by_player": dict(sorted(counts.items())),
        "holds": holds,
        "interpretation": "A dashed marker shows only the last observed image location for at most eight frames when another named box overlaps it. Source review shows the target can already be elsewhere, so the marker is not a current-position estimate or evidence that the player stopped. Missing raw boxes and court positions remain null; held frames contribute no distance or speed. The marker disappears on return or expiry.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['hold_player_frame_count']} temporary display holds on {len(holds)} frames: {dict(counts)}")


if __name__ == "__main__":
    main()
