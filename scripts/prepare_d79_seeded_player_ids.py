"""Offer unreviewed player-ID prefill from the user's first saved frame.

Only the blank review schedule is changed. IDs follow continuous raw tracks;
unresolved players are left for source-frame review. No floor points are made.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_D79JrsJsFgs"
DRAFT = MATCH / "pilot/player_drafts/in_play_20m24.json"
LABELS = MATCH / "pilot/player_annotations/in_play_20m24.json"
RAW = ROOT / "data/processed/d79_new_source/raw_240_289.json"
SELECTION = MATCH / "pilot/selection.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if set(labels["frames"]) != {"240"}:
        raise ValueError("Expected exactly the user's saved seed frame 240")
    if draft["source_sha256"] != raw["source_sha256"] or selection["raw_prediction_sha256"] != sha256(RAW):
        raise ValueError("Source or frozen tracker changed")
    if any("suggested_players" in row for row in draft["frames"]):
        raise ValueError("Review schedule already has ID prefill")
    seed = labels["frames"]["240"]["players"]
    seed_ids = {person["player_id"] for person in seed}
    if len(seed) != 6 or len(seed_ids) != 6:
        raise ValueError("Need six distinct seed player slots")
    assigned = {}
    unresolved_seed = []
    for person in seed:
        origin = person.get("origin_proposal_id")
        if person["bbox"] is None or not origin:
            unresolved_seed.append(person["player_id"])
            continue
        index = int(origin.rsplit("_", 1)[1])
        if origin != f"raw_240_{index}":
            raise ValueError("Unexpected seed proposal ID")
        raw_id = raw["predictions"]["240"][index]["track_id"]
        if raw_id in assigned.values():
            raise ValueError("Two saved players point to one raw ID")
        assigned[person["player_id"]] = raw_id
    if len(assigned) != 5:
        raise ValueError("Expected five boxed seed players and one unresolved player")

    active = dict(assigned)
    counts = {player_id: 0 for player_id in assigned}
    for row in draft["frames"]:
        frame = row["frame_index"]
        if frame <= 240 or frame > 289:
            continue
        predictions = raw["predictions"][str(frame)]
        suggestions = []
        for player_id, raw_id in list(active.items()):
            matches = [(index, box) for index, box in enumerate(predictions)
                       if box["track_id"] == raw_id]
            if len(matches) != 1:
                del active[player_id]
                continue
            index, box = matches[0]
            suggestions.append({
                "player_id": player_id,
                "team_id": "home",
                "bbox": box["bbox"],
                "occlusion": "none",
                "position_status": "uncertain",
                "footpoint": None,
                "origin_proposal_id": f"raw_{frame}_{index}",
                "notes": "ID carried from saved frame 240 by continuous raw track; check this box and player identity.",
            })
            counts[player_id] += 1
        row["suggested_players"] = suggestions
        row["unresolved_player_ids"] = sorted(seed_ids - {person["player_id"] for person in suggestions})
    draft["seeded_id_prefill"] = {
        "status": "unreviewed_assisted_suggestions_not_saved_labels",
        "seed_frame": 240,
        "seed_annotation_sha256": sha256(LABELS),
        "raw_prediction_sha256": sha256(RAW),
        "method": "Carry five boxed seed IDs only through uninterrupted same raw track IDs. Original no-box #15 is never assigned to a raw ID; #9 stops after its track gap. No floor points are inferred.",
        "boxes_by_player": counts,
        "unresolved_seed_ids": unresolved_seed,
    }
    temporary = DRAFT.with_suffix(".tmp")
    temporary.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    temporary.replace(DRAFT)
    print(json.dumps(draft["seeded_id_prefill"], indent=2))


if __name__ == "__main__":
    main()
