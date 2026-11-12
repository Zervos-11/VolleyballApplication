"""Check whether the separate-source dense labels are complete enough to score."""

import json
from pathlib import Path


MATCH = Path("data/matches/yt_em6zFUxfYpc")


def check():
    manifest = json.loads((MATCH / "pilot/heldout_tracking_manifest.json").read_text())
    summary = {"match_id": MATCH.name, "status": "ready", "windows": {}, "issues": []}
    for window in manifest["windows"]:
        expected_ids = None
        name = window["name"]
        annotation_file = MATCH / "pilot/player_annotations" / f"{name}.json"
        saved = json.loads(annotation_file.read_text()) if annotation_file.exists() else {"frames": {}}
        frames = saved.get("frames", {})
        ready = 0
        for frame in range(window["first_frame"], window["last_frame"] + 1):
            label = frames.get(str(frame))
            if label is None:
                summary["issues"].append(f"{name} frame {frame}: not saved")
                continue
            if not label.get("all_players_accounted_for"):
                summary["issues"].append(f"{name} frame {frame}: completeness unchecked")
                continue
            players = label.get("players", [])
            ids = [player["player_id"] for player in players]
            if len(ids) != 6 or len(set(ids)) != 6:
                summary["issues"].append(f"{name} frame {frame}: expected six unique player IDs")
                continue
            if expected_ids is None:
                expected_ids = set(ids)
            if set(ids) != expected_ids:
                summary["issues"].append(f"{name} frame {frame}: player IDs differ from first complete frame")
                continue
            bad = [player["player_id"] for player in players
                   if (player.get("origin_proposal_id") is not None
                       or (player["occlusion"] == "full" or player["position_status"] == "out_of_frame") != (player["bbox"] is None))]
            if bad:
                summary["issues"].append(f"{name} frame {frame}: invalid manual box/occlusion for {bad}")
                continue
            ready += 1
        summary["windows"][name] = {"saved_frames": len(frames),
                                    "complete_valid_frames": ready,
                                    "expected_frames": window["frame_count"]}
    if summary["issues"]:
        summary["status"] = "awaiting_independent_labels"
    return summary


def main():
    result = check()
    print(json.dumps({"status": result["status"], "windows": result["windows"],
                      "issue_count": len(result["issues"]),
                      "first_issues": result["issues"][:8]}, indent=2))
    if result["status"] == "ready":
        print("Independent labels are complete; the frozen tracker output can be scored.")


if __name__ == "__main__":
    main()
