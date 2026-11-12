"""Add reviewable no-box slots for #9 and #15 on unsaved D79 frames.

The user's saved labels are never edited. #15 is partly visible behind #23
in the source frames, so its no-box state is partial occlusion rather than
full invisibility. All prefilled states remain unsaved suggestions.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "data/matches/yt_D79JrsJsFgs"
DRAFT = MATCH / "pilot/player_drafts/in_play_20m24.json"
LABELS = MATCH / "pilot/player_annotations/in_play_20m24.json"


def main() -> None:
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    saved = json.loads(LABELS.read_text(encoding="utf-8"))["frames"]
    if "seeded_id_prefill" not in draft or "occluded_slot_prefill" in draft:
        raise ValueError("Expected seeded ID suggestions without no-box prefill")
    changed = []
    for row in draft["frames"]:
        frame = row["frame_index"]
        if frame < 272 or frame > 289 or str(frame) in saved:
            continue
        suggestions = row.get("suggested_players")
        if suggestions is None or {p["player_id"] for p in suggestions} != {"98", "8", "23", "4"}:
            raise ValueError(f"Unexpected ID suggestions on frame {frame}")
        for player_id, occlusion, note in (
            ("9", "full", "No distinct source body box after the raw track gap; check for reappearance."),
            ("15", "partial", "Partly visible behind #23, without a distinct usable body box; draw one if clear."),
        ):
            suggestions.append({
                "player_id": player_id, "team_id": "home", "bbox": None,
                "occlusion": occlusion, "position_status": "occluded",
                "footpoint": None, "origin_proposal_id": None, "notes": note,
            })
        row["unresolved_player_ids"] = []
        row["no_box_player_ids"] = ["9", "15"]
        changed.append(frame)
    draft["occluded_slot_prefill"] = {
        "status": "unreviewed_suggestions_not_saved_labels",
        "frames": changed,
        "players": ["9", "15"],
        "interpretation": "#9 is provisionally fully hidden after its raw track gap; #15 is partly visible behind #23 without a distinct usable box. Reviewer must revise either slot if a clear box returns. No floor position is inferred.",
    }
    temporary = DRAFT.with_suffix(".tmp")
    temporary.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    temporary.replace(DRAFT)
    print(f"Added two home-team no-box suggestions on {len(changed)} unsaved frames: {changed}")


if __name__ == "__main__":
    main()
