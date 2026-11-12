"""Build six named near-team box slots without inventing floor locations."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/d79_new_source"
RAW = BASE / "raw_point_candidate_80_336.json"
SEED = BASE / "prerally_identity_seed.json"
POLICY = BASE / "named_near_box_policy.json"
OUT = BASE / "named_near_boxes_80_336.json"


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    players = sorted(seed["players"], key=int)
    segments = {}
    for pid in players:
        base = [(first, last, track, "base_identity") for first, last, track in seed["players"][pid]["accepted_raw_segments"]]
        extensions = [(first, last, track, "box_only_extension") for first, last, track in policy["box_only_extensions"].get(pid, [])]
        segments[pid] = base + extensions
        covered = [f for first, last, _, _ in segments[pid] for f in range(first, last + 1)]
        if len(covered) != len(set(covered)):
            raise ValueError(f"Overlapping named-box policy for #{pid}")
    frames = {}
    for frame in range(80, 337):
        raw_boxes = raw["predictions"][str(frame)]
        slots = {}
        for pid in players:
            selected = next(((track, kind) for first, last, track, kind in segments[pid]
                             if first <= frame <= last), None)
            if selected is None:
                slots[pid] = {"box_status": "no_accepted_box", "bbox": None,
                              "raw_track_id": None, "floor_position_px": None}
                continue
            track, kind = selected
            candidates = [p for p in raw_boxes if p["track_id"] == track]
            if len(candidates) != 1:
                raise ValueError(f"Frame {frame} #{pid}: expected one raw ID {track} box, found {len(candidates)}")
            slots[pid] = {"box_status": kind, "bbox": candidates[0]["bbox"],
                          "raw_track_id": track, "floor_position_px": None}
        frames[str(frame)] = slots
    result = {
        "status": "source_seeded_named_near_boxes_no_floor_positions",
        "frames_inclusive": [80, 336],
        "target_players": players,
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "seed_sha256": hashlib.sha256(SEED.read_bytes()).hexdigest(),
        "box_policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "box_only_extension_rule": policy["rule"],
        "accepted_named_box_slots_by_player": {pid: sum(slots[pid]["bbox"] is not None for slots in frames.values())
                                               for pid in players},
        "all_six_box_frames": sum(all(slot["bbox"] is not None for slot in slots.values())
                                  for slots in frames.values()),
        "frames": frames,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frames": len(frames), "target_players": players,
                      "box_only_extension_slots": sum(slot["box_status"] == "box_only_extension"
                                                      for slots in frames.values() for slot in slots.values())}, indent=2))


if __name__ == "__main__":
    main()
