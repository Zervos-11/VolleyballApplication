"""Join three disjoint human-review tiers across S3 P34's candidate interval.

This scores observation coverage, not an independently validated full rally.
The 85-frame full packet must be exported before the final score is written.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = SCREEN / "s3p34_remaining_rally_review"
FULL = PACK / "completed.csv"
DENSE = SCREEN / "s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv"
LEDGER = SCREEN / "s3p34_six_player_observation_ledger.json"
PRIOR_GAP = SCREEN / "s3p34_full_span_review/gap_source_verdicts.json"
OUTPUT = SCREEN / "s3p34_full_30fps_review_score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_FULL_30FPS_REVIEW_SCORE.md"
ROSTER = ("28", "12", "15", "7", "19", "21")
FRAMES = set(range(36001, 36139))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> dict[tuple[int, str], dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        source = list(csv.DictReader(stream))
    keyed = {(int(row["source_frame"]), row["jersey"]): row for row in source}
    if len(keyed) != len(source):
        raise ValueError(f"Duplicate frame/jersey rows in {path}")
    return keyed


def main() -> None:
    manifest_path = PACK / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    draft = json.loads((PACK / "draft.json").read_text(encoding="utf-8"))
    packet_frames = {row["source_frame"]: row for row in manifest["frames"]}
    pending = sorted(f for f in packet_frames if not draft["frames"].get(str(f), {}).get("paired"))
    if not FULL.is_file():
        print(f"Full review pending: {len(pending)}/85 packet frames; next {pending[:8]}")
        return
    if pending:
        raise ValueError(f"Full export exists but {len(pending)} draft frames lack paired review")

    full = rows(FULL)
    dense = rows(DENSE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    prior_gap = json.loads(PRIOR_GAP.read_text(encoding="utf-8"))
    decisive = prior_gap["decisive_example"]
    if (decisive["source_frame"], decisive["jersey"]) != (36112, "15"):
        raise ValueError("Prior source-gap QC example changed")
    if full[(36112, "15")]["ground_status"] == "grounded":
        raise ValueError("Frame 36112 / #15 is marked grounded, but the prior source audit and unboxed image show an airborne blocker; resolve the contradictory annotation before scoring")
    ledger_frames = {row["source_frame"]: row for row in ledger["frames"]}
    sampled_frames = {f for f in FRAMES if f % 6 == 0}
    dense_frames = {f for f, _ in dense}
    if len(packet_frames) != 85 or len(sampled_frames) != 23 or len(dense_frames) != 30:
        raise ValueError("The frozen review-tier denominators changed")
    if set(packet_frames) | sampled_frames | dense_frames != FRAMES or (
        set(packet_frames) & sampled_frames or set(packet_frames) & dense_frames or sampled_frames & dense_frames
    ):
        raise ValueError("Review tiers no longer partition the 138 source frames")
    if set(full) != {(f, j) for f in packet_frames for j in ROSTER}:
        raise ValueError("Full packet must contain exactly 85 x 6 player rows")
    if set(dense) != {(f, j) for f in dense_frames for j in ROSTER}:
        raise ValueError("Dense review must contain exactly 30 x 6 player rows")

    counts = Counter()
    frame_scores = []
    for frame in sorted(FRAMES):
        tier = "sampled_5hz" if frame in sampled_frames else "dense_30fps" if frame in dense_frames else "full_packet"
        accepted_count = candidate_count = 0
        players = {}
        for jersey in ROSTER:
            candidate = ledger_frames[frame]["players"][jersey]["jersey_keyed_candidate_court_m"] is not None
            if tier == "sampled_5hz":
                prior = ledger_frames[frame]["players"][jersey]
                accepted = prior["source_reviewed_ground_court_m"] is not None
                state = prior["floor_status"]
            else:
                row = dense[(frame, jersey)] if tier == "dense_30fps" else full[(frame, jersey)]
                if tier == "full_packet":
                    item = packet_frames[frame]
                    if row["image_sha256"] != item["image_sha256"]:
                        raise ValueError(f"Source image hash mismatch at {frame}/{jersey}")
                    box = item["numbered_boxes"][jersey]
                    if (box is None) != (row["candidate_alignment"] == "no_box"):
                        raise ValueError(f"Box availability mismatch at {frame}/{jersey}")
                    floor = row["floor_alignment"]
                else:
                    floor = row["proxy_floor_alignment"]
                if row["ground_status"] != "grounded" and floor == "plausible":
                    raise ValueError(f"Non-grounded floor proxy accepted at {frame}/{jersey}")
                accepted = (row["ground_status"] == "grounded"
                            and row["identity_status"] not in ("uncertain", "not_visible")
                            and row["candidate_alignment"] == "same_player"
                            and floor == "plausible")
                state = row["ground_status"]
                if tier == "full_packet" and row["candidate_alignment"] == "same_player":
                    counts["full_packet_same_player_boxes"] += 1
            if accepted and not candidate:
                raise ValueError(f"Accepted proxy has no ledger candidate at {frame}/{jersey}")
            candidate_count += candidate
            accepted_count += accepted
            counts["candidate_box_slots"] += candidate
            counts["accepted_grounded_proxy_slots"] += accepted
            counts[f"state_{state}"] += 1
            players[jersey] = {"candidate_box": candidate, "accepted_grounded_proxy": accepted,
                               "source_state": state}
        counts["six_candidate_frames"] += candidate_count == 6
        counts["six_accepted_grounded_frames"] += accepted_count == 6
        frame_scores.append({"source_frame": frame, "review_tier": tier,
                             "candidate_boxes": candidate_count,
                             "accepted_grounded_proxies": accepted_count,
                             "players": players})

    result = {
        "status": "whole_candidate_interval_single_reviewer_state_and_proxy_review",
        "interval_inclusive": [36001, 36138],
        "exact_serve_to_dead_ball": False,
        "denominators": {"source_frames": 138, "player_slots": 828,
                         "sampled_5hz_frames": 23, "dense_30fps_frames": 30,
                         "full_packet_frames": 85},
        "counts": dict(counts),
        "inputs_sha256": {"full_review": sha(FULL), "dense_review": sha(DENSE),
                          "sampled_ledger": sha(LEDGER), "packet_manifest": sha(manifest_path),
                          "prior_gap_source_qc": sha(PRIOR_GAP)},
        "limitations": [
            "The interval starts after the unresolved serve-contact bracket and ends before the first reviewed post-point frame.",
            "Candidate-assisted single-reviewer source judgments are not independent identity ground truth.",
            "Accepted grounded box bottoms are visual proxies, not independently calibrated physical positions.",
            "Airborne, missing and uncertain positions remain null and cannot count as six-grounded team frames.",
        ],
        "frames": frame_scores,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# S3 P34 full 30-fps candidate-interval review\n\n"
        "The 138 source frames from 36001 to 36138 have six single-reviewer state records per frame: "
        "23 prior five-Hz source frames, 30 dense-reviewed frames and 85 full-packet frames. "
        "The full-packet review was candidate-assisted. "
        f"[Machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/{OUTPUT.name}).\n\n"
        f"- Jersey-keyed candidate boxes: **{counts['candidate_box_slots']}/828** player slots.\n"
        f"- Accepted grounded box-bottom proxies: **{counts['accepted_grounded_proxy_slots']}/828** player slots.\n"
        f"- Frames with six candidate boxes: **{counts['six_candidate_frames']}/138**.\n"
        f"- Frames with six accepted grounded proxies: **{counts['six_accepted_grounded_frames']}/138**.\n\n"
        "These are whole-*candidate-interval* observation rates. Airborne, unboxed and uncertain floor positions "
        "remain explicit nulls. The source-reviewed serve and end are still bracketed, the court transform is staged, "
        "and this was one candidate-assisted reviewer. This result does not by itself validate an exact full-rally "
        "six-player floor trajectory or an outcome effect.\n",
        encoding="utf-8",
    )
    print(f"Scored 138 frames: {counts['accepted_grounded_proxy_slots']}/828 accepted grounded slots")


if __name__ == "__main__":
    main()
