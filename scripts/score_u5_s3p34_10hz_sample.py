"""Score the frozen, systematically spaced S3 P34 source review sample."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = SCREEN / "s3p34_remaining_rally_review"
PRIOR = SCREEN / "s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv"
LEDGER = SCREEN / "s3p34_six_player_observation_ledger.json"
OUTPUT = SCREEN / "s3p34_10hz_sample_score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_10HZ_SAMPLE_RESULT.md"
ROSTER = ("28", "12", "15", "7", "19", "21")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def keyed(rows: list[dict]) -> dict[tuple[int, str], dict]:
    result = {}
    for row in rows:
        key = int(row["source_frame"]), row["jersey"]
        if key in result:
            raise ValueError(f"Duplicate review slot {key}")
        result[key] = row
    return result


def main() -> None:
    complete = PACK / "focused_completed.csv"
    if not complete.is_file():
        raise SystemExit("Focused review has not been exported; no score written")
    protocol_path = PACK / "focused_10hz_protocol.json"
    manifest_path = PACK / "manifest.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    new = keyed(csv_rows(complete))
    old = keyed(csv_rows(PRIOR))
    manifest_frames = {f["source_frame"]: f for f in manifest["frames"]}
    ledger_frames = {f["source_frame"]: f for f in ledger["frames"]}
    new_frames = set(protocol["new_frames_to_review"])
    old_frames = set(protocol["already_human_reviewed_on_interleaved_grid"])
    sample_frames = sorted(f for f in ledger_frames if f % 3 == 0)
    if (len(sample_frames), len(new_frames), len(old_frames)) != (46, 17, 6):
        raise ValueError("Frozen 10-Hz frame counts changed")
    if {f for f in sample_frames if f % 6 == 3} != new_frames | old_frames:
        raise ValueError("Interleaved grid does not match frozen protocol")
    if set(new) != {(f, j) for f in new_frames for j in ROSTER}:
        raise ValueError("Focused export must contain exactly 17 x 6 slots")
    for (frame, jersey), row in new.items():
        item = manifest_frames[frame]
        if row["image_sha256"] != item["image_sha256"]:
            raise ValueError(f"Image hash mismatch in {frame}/{jersey}")
        box = item["numbered_boxes"][jersey]
        if (box is None) != (row["candidate_alignment"] == "no_box"):
            raise ValueError(f"Candidate availability mismatch in {frame}/{jersey}")
        if row["ground_status"] != "grounded" and row["floor_alignment"] == "plausible":
            raise ValueError(f"Airborne or uncertain floor accepted in {frame}/{jersey}")
    if not {(f, j) for f in old_frames for j in ROSTER} <= set(old):
        raise ValueError("Prior interleaved review is incomplete")

    counts = Counter()
    frame_results = []
    for frame in sample_frames:
        tier = "prior_5hz" if frame % 6 == 0 else "prior_dense" if frame in old_frames else "new_focused"
        candidate_count = accepted_count = 0
        for jersey in ROSTER:
            item = ledger_frames[frame]["players"][jersey]
            candidate = item["jersey_keyed_candidate_court_m"] is not None
            candidate_count += candidate
            counts["candidate_boxes"] += candidate
            counts[f"{tier}_slots"] += 1
            if tier == "prior_5hz":
                if item["evidence_tier"] != "sampled_5hz_source_review":
                    raise ValueError(f"Unexpected prior evidence in {frame}/{jersey}")
                accepted = item["source_reviewed_ground_court_m"] is not None
                if item["floor_status"] == "airborne":
                    counts["airborne"] += 1
                if item["floor_status"] not in ("airborne", "reviewed_grounded_box_bottom_proxy"):
                    counts["unresolved_or_unboxed_floor"] += 1
            elif tier == "prior_dense":
                row = old[(frame, jersey)]
                accepted = (row["ground_status"] == "grounded"
                            and row["identity_status"] != "uncertain"
                            and row["candidate_alignment"] == "same_player"
                            and row["proxy_floor_alignment"] == "plausible")
                if row["candidate_alignment"] == "same_player":
                    counts["paired_same_player_boxes"] += 1
                if row["ground_status"] == "airborne":
                    counts["airborne"] += 1
            else:
                row = new[(frame, jersey)]
                accepted = (row["ground_status"] == "grounded"
                            and row["identity_status"] not in ("uncertain", "not_visible")
                            and row["candidate_alignment"] == "same_player"
                            and row["floor_alignment"] == "plausible")
                if row["candidate_alignment"] == "same_player":
                    counts["paired_same_player_boxes"] += 1
                if row["candidate_alignment"] == "wrong_player":
                    counts["paired_wrong_player_boxes"] += 1
                if row["candidate_alignment"] == "no_box":
                    counts["new_missing_boxes"] += 1
                if row["ground_status"] == "airborne":
                    counts["airborne"] += 1
                if row["identity_status"] == "uncertain":
                    counts["new_uncertain_identities"] += 1
                if row["identity_status"] == "sequence_consistent":
                    counts["new_sequence_consistent_identities"] += 1
                if row["identity_status"] == "digit_confirmed":
                    counts["new_digit_confirmed_identities"] += 1
                if row["candidate_boxes_shown_before_source"] == "True":
                    counts["new_boxes_seen_before_source"] += 1
            if accepted and not candidate:
                raise ValueError(f"Accepted floor proxy lacks candidate box in {frame}/{jersey}")
            accepted_count += accepted
            counts["accepted_grounded_proxies"] += accepted
        counts["six_candidate_frames"] += candidate_count == 6
        counts["six_accepted_grounded_frames"] += accepted_count == 6
        frame_results.append({"source_frame": frame, "evidence_tier": tier,
                              "candidate_boxes": candidate_count,
                              "accepted_grounded_proxies": accepted_count})
    if counts["prior_5hz_slots"] != 138 or counts["prior_dense_slots"] != 36 or counts["new_focused_slots"] != 102:
        raise ValueError("Review tier denominator changed")
    result = {
        "status": "systematic_10hz_source_sample_single_reviewer_candidate_assisted",
        "interval_inclusive": [36001, 36138],
        "exact_serve_to_dead_ball": False,
        "denominators": {"sampled_frames": 46, "sampled_player_slots": 276,
                         "paired_review_slots": 138, "new_review_frames": 17},
        "counts": dict(counts),
        "rates": {"candidate_box_slots": round(counts["candidate_boxes"] / 276, 4),
                  "accepted_grounded_proxy_slots": round(counts["accepted_grounded_proxies"] / 276, 4),
                  "six_candidate_frames": round(counts["six_candidate_frames"] / 46, 4),
                  "six_accepted_grounded_frames": round(counts["six_accepted_grounded_frames"] / 46, 4)},
        "inputs_sha256": {"focused_review": sha(complete), "prior_dense_review": sha(PRIOR),
                          "prior_5hz_ledger": sha(LEDGER), "manifest": sha(manifest_path),
                          "protocol": sha(protocol_path)},
        "limitations": ["Systematic sample across a source-bracketed interval, not continuous 30-fps validation.",
                        "Candidate-assisted, single-reviewer identity and floor judgments are not independent ground truth.",
                        "Accepted box bottoms are visual floor proxies, not measured shoe-position accuracy.",
                        "Court calibration and exact serve/end events remain separate validation questions."],
        "frames": frame_results,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = f"""# S3 P34 systematic 10-Hz whole-interval sample

The frozen time grid covers **46 frames and 276 player slots** across source-bracketed frames 36001–36138: 23 prior 5-Hz frames, six prior dense-reviewed interleaved frames and 17 newly reviewed interleaved frames. The new reviews used provisional numbered boxes as an identity guide; they are single-reviewer, candidate-assisted verdicts. [Machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s3p34_10hz_sample_score.json).

| Measure | Count | Denominator |
| --- | ---: | ---: |
| Jersey-keyed candidate boxes | {counts['candidate_boxes']} | 276 sampled slots |
| Visually accepted grounded box-bottom proxies | {counts['accepted_grounded_proxies']} | 276 sampled slots |
| Frames with six candidate boxes | {counts['six_candidate_frames']} | 46 sampled frames |
| Frames with six accepted grounded proxies | {counts['six_accepted_grounded_frames']} | 46 sampled frames |
| Same-player box verdicts in paired reviews | {counts['paired_same_player_boxes']} | 138 paired-review slots |
| New focused review missing boxes | {counts['new_missing_boxes']} | 102 new slots |
| New focused review wrong-player boxes | {counts['paired_wrong_player_boxes']} | 102 new slots |

Frame 36129 player 4 / UCLA #7 is recorded as **no box**, matching the reviewer's reported turned-player missed detection. The whole 17-frame focused export records {counts['new_missing_boxes']} missing boxes, so this one explained instance does not erase other omissions. Airborne players may retain a correct box and identity with a null floor point.

The 46-frame rates describe **sampled availability and visual proxy eligibility**, not a complete 30-fps six-player rally trajectory. Identity labels for the new frames use prior sequence context and visible candidate boxes: {counts['new_sequence_consistent_identities']}/102 new source labels are sequence-consistent and {counts['new_digit_confirmed_identities']}/102 have readable digits recorded. Candidate boxes were shown before source-state save for {counts['new_boxes_seen_before_source']}/102 new slots. The unreviewed 92 frames remain unknown at this level. Exact serve/end frames, physical court calibration approval and measured foot-position error remain separate. This result does not change the strict count of zero validated complete six-player rally trajectories.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"{counts['candidate_boxes']}/276 candidate boxes; {counts['accepted_grounded_proxies']}/276 accepted grounded proxies; {counts['six_accepted_grounded_frames']}/46 six-grounded frames")


if __name__ == "__main__":
    main()
