"""Separate reviewed D79 missing boxes from gaps with no dense visibility review."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/d79_new_source"
NAMED = BASE / "named_near_boxes_80_336.json"
QUEUE = BASE / "named_gap_review/gap_queue.json"
ANNOTATIONS = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/in_play_20m24.json"
ATTESTATION = ROOT / "data/matches/yt_D79JrsJsFgs/pilot/player_annotations/reviews/in_play_20m24_near.json"
SOURCE_REVIEW = BASE / "named_gap_review/source_visibility_review.json"
SOURCE_VIDEO = ROOT / "data/matches/yt_D79JrsJsFgs/screening/screen_20m20.mp4"
DENSE_MANIFEST = BASE / "named_gap_review/dense_visibility/manifest.json"
OUT = BASE / "named_gap_visibility_audit.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    named = json.loads(NAMED.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    labels = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
    source_review = json.loads(SOURCE_REVIEW.read_text(encoding="utf-8"))
    dense_manifest = json.loads(DENSE_MANIFEST.read_text(encoding="utf-8"))
    if queue["named_output_sha256"] != sha256(NAMED):
        raise ValueError("Gap queue is stale relative to named boxes")
    if attestation["status"] != "reviewed" or attestation["annotation_sha256"] != sha256(ANNOTATIONS):
        raise ValueError("Human review attestation is stale or missing")
    if (attestation["first_frame"], attestation["last_frame"]) != (240, 289):
        raise ValueError("Unexpected reviewed frame range")
    if named["frames_inclusive"] != [80, 336]:
        raise ValueError("Unexpected named output range")
    if (source_review["source_sha256"] != sha256(SOURCE_VIDEO)
            or source_review["named_output_sha256"] != sha256(NAMED)
            or source_review["dense_manifest_sha256"] != sha256(DENSE_MANIFEST)):
        raise ValueError("Dense source review is stale")
    source_states = {}
    for item in source_review["reviewed_ranges"]:
        if (item["visibility"] not in {"visible", "not_distinct"}
                or item["box_assessability"] != "no_accepted_box"):
            raise ValueError("Unexpected dense review state")
        evidence_frames = {frame for sheet in dense_manifest["sheets"]
                           if f"dense_visibility/{sheet['sheet']}" in item["evidence_sheets"]
                           for frame in sheet["frames"]}
        for frame in range(item["first_frame"], item["last_frame"] + 1):
            if frame not in evidence_frames:
                raise ValueError(f"No dense source sheet for frame {frame}")
            key = (frame, item["player_id"])
            if key in source_states:
                raise ValueError(f"Duplicate dense review: {key}")
            source_states[key] = ("source_visible_no_accepted_box" if item["visibility"] == "visible"
                                  else "source_not_distinct_no_accepted_box")

    missing = []
    counts = Counter()
    reviewed_visible = 0
    for frame in range(80, 337):
        review = labels["frames"].get(str(frame))
        players = {str(p["player_id"]): p for p in review["players"]} if review else {}
        if review and (not review["all_players_accounted_for"] or set(players) != set(named["target_players"])):
            raise ValueError(f"Incomplete near-side review at frame {frame}")
        for pid in named["target_players"]:
            box = named["frames"][str(frame)][pid]["bbox"]
            if review:
                label = players[pid]
                if label["bbox"] is not None:
                    reviewed_visible += 1
                    if box is None:
                        raise ValueError(f"Missing named box on reviewed visible player {pid} frame {frame}")
                elif box is not None:
                    raise ValueError(f"Named box on reviewed no-box player {pid} frame {frame}")
            if box is not None:
                continue
            if review:
                label = players[pid]
                if label["position_status"] != "occluded" or label["occlusion"] not in {"full", "partial"}:
                    raise ValueError(f"Unexpected reviewed missing-box state: {pid} frame {frame}")
                status = f"reviewed_{label['occlusion']}_occlusion"
            elif (frame, pid) in source_states:
                status = source_states[(frame, pid)]
            else:
                status = "unreviewed_visibility_unknown"
            counts[status] += 1
            missing.append({"frame": frame, "player_id": pid, "status": status})

    run_summaries = []
    for run in queue["runs"]:
        relevant = [slot for slot in missing if slot["player_id"] == run["player_id"]
                    and run["first_frame"] <= slot["frame"] <= run["last_frame"]]
        if len(relevant) != run["missing_slots"]:
            raise ValueError(f"Gap queue run changed: {run}")
        run_summaries.append({"player_id": run["player_id"], "frames_inclusive": [run["first_frame"], run["last_frame"]],
                              "missing_slots": len(relevant), "status_counts": dict(sorted(Counter(s["status"] for s in relevant).items())),
                              "source_sample_frames": run["sample_frames"], "source_sheet": run["source_sheet"],
                              "sample_limit": "Source sheet is sparse; its observations do not label unsampled frames."})

    if (len(missing) != queue["total_missing_slots"] or reviewed_visible != 232
            or sum(slot["status"] in {"source_visible_no_accepted_box", "source_not_distinct_no_accepted_box"}
                   for slot in missing) != len(source_states)):
        raise ValueError("Coverage totals changed; inspect source data")
    result = {"status": "review_bound_missing_box_visibility_audit",
              "named_output_sha256": sha256(NAMED), "annotation_sha256": sha256(ANNOTATIONS),
              "attestation_sha256": sha256(ATTESTATION), "gap_queue_sha256": sha256(QUEUE),
              "source_visibility_review_sha256": sha256(SOURCE_REVIEW),
              "frame_range_inclusive": [80, 336], "reviewed_range_inclusive": [240, 289],
              "target_players": named["target_players"],
              "accepted_named_boxes": 257 * len(named["target_players"]) - len(missing),
              "missing_box_status_counts": dict(sorted(counts.items())),
              "reviewed_visible_named_box_count": reviewed_visible,
              "reviewed_visible_box_coverage": "232/232",
              "full_point_visible_box_coverage": None,
              "full_point_coverage_limit": "Visibility of the remaining unreviewed missing slots is unknown; only listed dense source review ranges have been classified.",
              "missing_slots": missing, "runs": run_summaries}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"accepted_named_boxes": result["accepted_named_boxes"],
                      "missing_box_status_counts": result["missing_box_status_counts"],
                      "reviewed_visible_box_coverage": result["reviewed_visible_box_coverage"],
                      "full_point_visible_box_coverage": result["full_point_visible_box_coverage"]}, indent=2))


if __name__ == "__main__":
    main()
