"""Prepare provisional six-slot assignments for source review of elevated points.

Assignments are candidate suggestions only. A reviewer must confirm each frame.
"""

from __future__ import annotations

import hashlib
import json
import math
import argparse
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/source_view_screen"
SELECTION = BASE / "transfer_source_only_selection_2026-11-06_v2.json"
REVIEW = BASE / "elevated_transfer_review"

# Initial boxes were source-checked in the first selected grid frame, after the
# source-time rally rule was frozen. Slot names are stable arbitrary labels.
SEEDS = {
    "yt_-siJXMXKcbo": [3, 5, 11, 14, 1, 9],
    "yt__BOwnLLVaPs": [9, 5, 2, 4, 3, 6],
    "yt_b1bJ5WN05Qw": [28, 2, 3, 9, 43, 4],
}
SEED_FRAME = {"yt_b1bJ5WN05Qw": 720}
BYU_EARLY_RAW_IDS = [28, 2, 3, 9, 8, 4]
# Source-inspected one-frame detail suggestions where the 960-pixel pass lost
# a visible BYU player. These IDs carry no tracking continuity or floor claim.
BYU_EARLY_DETAIL_IDS = {
    678: {5: 267827},
    684: {1: 268407, 5: 268424},
    690: {1: 269004},
    708: {1: 270805, 4: 270841, 5: 270827},
}
ROI = {
    "yt_-siJXMXKcbo": {"x1_min": 100, "x2_max": 900, "y2_min": 290,
                          "missing_cost": 130, "same_id_bonus": 65},
    "yt__BOwnLLVaPs": {"x1_min": 200, "x2_max": 1450, "y2_min": 480,
                        "missing_cost": 190, "same_id_bonus": 90},
    "yt_b1bJ5WN05Qw": {"x1_min": 250, "x2_max": 1500, "y2_min": 480,
                          "missing_cost": 190, "same_id_bonus": 90},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def foot(box: list[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2, box[3])


def prepare(case: dict) -> dict:
    match_id = case["match_id"]
    source = BASE / f"{match_id}_raw_5hz_candidates.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = data["rows"]
    seed_ids = SEEDS[match_id]
    settings = ROI[match_id]
    seed_frame = SEED_FRAME.get(match_id, rows[0]["excerpt_frame"])
    seed_index = next(i for i, row in enumerate(rows)
                      if row["excerpt_frame"] == seed_frame)
    first = {p["raw_track_id"]: p for p in rows[seed_index]["proposals"]}
    if any(seed not in first for seed in seed_ids):
        raise ValueError(f"Missing initial candidate in {match_id}")
    last_box = [first[seed]["bbox_px"] for seed in seed_ids]
    last_id = seed_ids[:]
    out_rows = []
    for index, row in enumerate(rows):
        if index < seed_index:
            early_ids = BYU_EARLY_RAW_IDS if match_id == "yt_b1bJ5WN05Qw" else [None] * 6
            present_ids = {proposal["raw_track_id"] for proposal in row["proposals"]}
            out_rows.append({"excerpt_frame": row["excerpt_frame"],
                             "proposals": row["proposals"],
                             "slots": [{"slot": i + 1,
                                        "suggested_raw_track_id": (early_ids[i] if early_ids[i] in present_ids else None),
                                        "assignment_kind": ("backward_raw_id_candidate" if early_ids[i] in present_ids
                                                            else "pre_seed_unassigned")}
                                       for i in range(6)]})
            continue
        candidates = [p for p in row["proposals"]
                      if p["bbox_px"][0] >= settings["x1_min"]
                      and p["bbox_px"][2] <= settings["x2_max"]
                      and p["bbox_px"][3] >= settings["y2_min"]]
        if index == seed_index:
            chosen = [first[seed] for seed in seed_ids]
            kinds = ["seed"] * 6
        else:
            # One dummy column per slot permits explicit provisional gaps.
            cost = np.full((6, len(candidates) + 6), 1e6, dtype=float)
            for i in range(6):
                x, y = foot(last_box[i])
                for j, p in enumerate(candidates):
                    px, py = foot(p["bbox_px"])
                    distance = math.hypot(px - x, py - y)
                    if p["raw_track_id"] == last_id[i]:
                        distance -= settings["same_id_bonus"]
                    cost[i, j] = distance
                cost[i, len(candidates) + i] = settings["missing_cost"]
            r_idx, c_idx = linear_sum_assignment(cost)
            assigned = dict(zip(r_idx.tolist(), c_idx.tolist()))
            chosen = []
            kinds = []
            for i in range(6):
                col = assigned[i]
                if col >= len(candidates):
                    chosen.append(None)
                    kinds.append("unassigned")
                else:
                    p = candidates[col]
                    chosen.append(p)
                    kinds.append("same_raw_id" if p["raw_track_id"] == last_id[i]
                                 else "nearest_candidate")
                    last_box[i] = p["bbox_px"]
                    last_id[i] = p["raw_track_id"]
        out_rows.append({
            "excerpt_frame": row["excerpt_frame"],
            "proposals": row["proposals"],
            "slots": [
                {"slot": i + 1, "suggested_raw_track_id": p["raw_track_id"] if p else None,
                 "assignment_kind": kinds[i]}
                for i, p in enumerate(chosen)
            ],
        })
    supplement_sha = None
    if match_id == "yt_b1bJ5WN05Qw":
        supplement_path = REVIEW / f"{match_id}_hires_supplement.json"
        if supplement_path.exists():
            supplement = json.loads(supplement_path.read_text(encoding="utf-8"))
            if (supplement["excerpt_sha256"] != case["local_excerpt_sha256"]
                    or supplement["original_raw_candidate_sha256"] != sha256(source)):
                raise ValueError("High-resolution BYU supplement does not match source")
            supplemental_rows = {item["excerpt_frame"]: item["proposals"]
                                 for item in supplement["rows"]}
            for item in out_rows:
                frame = item["excerpt_frame"]
                item["proposals"].extend(supplemental_rows.get(frame, []))
                for slot, detail_id in BYU_EARLY_DETAIL_IDS.get(frame, {}).items():
                    if not any(p["raw_track_id"] == detail_id for p in item["proposals"]):
                        raise ValueError(f"Missing BYU early detail box {detail_id} at frame {frame}")
                    if item["slots"][slot - 1]["suggested_raw_track_id"] is None:
                        item["slots"][slot - 1] = {
                            "slot": slot,
                            "suggested_raw_track_id": detail_id,
                            "assignment_kind": "backward_detail_candidate",
                        }
            supplement_sha = sha256(supplement_path)
        # The raw association follows USC after #1 changes direction. Leave
        # P4 unresolved so the reviewer can select #1 from source imagery.
        for item in out_rows:
            if item["excerpt_frame"] >= 780:
                item["slots"][3] = {"slot": 4,
                                    "suggested_raw_track_id": None,
                                    "assignment_kind": "manual_jersey_1_required"}
    return {
        "status": "unreviewed_candidate_suggestions",
        "match_id": match_id,
        "near_side_team_source_read": case["near_side_team_source_read"],
        "source_url": case["source_url"],
        "excerpt": case["local_excerpt"],
        "excerpt_sha256": case["local_excerpt_sha256"],
        "source_selection_sha256": sha256(SELECTION),
        "raw_candidate_sha256": sha256(source),
        "high_resolution_supplement_sha256": supplement_sha,
        "seed_raw_ids_by_slot": seed_ids,
        "seed_excerpt_frame": seed_frame,
        "method": ("Initial source-screened six near-side boxes; later one-to-one nearest-box assignment with raw-ID bonus and explicit gaps. "
                   + ("BYU pre-seed raw IDs are source-inspected backward candidates with explicit gaps; P4 after frame 774 needs manual #1 assignment; optional high-resolution boxes are one-frame proposals only. "
                      if match_id == "yt_b1bJ5WN05Qw" else "")
                   + "Every assignment requires source review."),
        "rows": out_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", help="Prepare only one case without rewriting earlier suggestions")
    args = parser.parse_args()
    REVIEW.mkdir(parents=True, exist_ok=True)
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    for case in selection["cases"]:
        if args.match_id and case["match_id"] != args.match_id:
            continue
        data = prepare(case)
        out = REVIEW / f"{case['match_id']}_suggestions.json"
        out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        kinds = [slot["assignment_kind"] for row in data["rows"] for slot in row["slots"]]
        print(f"{case['match_id']}: {len(data['rows'])} frames, "
              f"{kinds.count('unassigned')} provisional gaps, "
              f"{kinds.count('nearest_candidate')} nearest-box suggestions")


if __name__ == "__main__":
    main()
