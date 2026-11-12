"""Score all 138 S3 P34 candidate-interval frames after 85-frame human review."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PACK = SCREEN / "s3p34_remaining_rally_review"
ROSTER = ("28", "12", "15", "7", "19", "21")
OUTPUT = SCREEN / "s3p34_whole_rally_review_score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_WHOLE_RALLY_REVIEW_RESULT.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    complete = PACK / "completed.csv"
    if not complete.is_file():
        raise SystemExit("85-frame review is not exported yet; no final score was written")
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads((SCREEN / "s3p34_six_player_observation_ledger.json").read_text(encoding="utf-8"))
    old = rows(SCREEN / "s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv")
    new = rows(complete)
    by_frame = {f["source_frame"]: f for f in ledger["frames"]}
    manifest_by_frame = {f["source_frame"]: f for f in manifest["frames"]}
    assert len(new) == 510 and len(old) == 180 and len(by_frame) == 138
    new_by_key = {}
    for row in new:
        key = (int(row["source_frame"]), row["jersey"])
        assert key not in new_by_key and key[1] in ROSTER
        item = manifest_by_frame[key[0]]
        assert row["image_sha256"] == item["image_sha256"]
        box = item["numbered_boxes"][key[1]]
        assert (box is None) == (row["candidate_alignment"] == "no_box")
        assert row["ground_status"] in ("grounded", "airborne", "feet_occluded", "not_visible", "uncertain")
        assert row["identity_status"] in ("digit_confirmed", "sequence_consistent", "uncertain", "not_visible")
        assert row["floor_alignment"] in ("plausible", "implausible", "not_applicable", "uncertain")
        if row["ground_status"] != "grounded":
            assert row["floor_alignment"] != "plausible"
        new_by_key[key] = row
    old_by_key = {(int(r["source_frame"]), r["jersey"]): r for r in old}
    assert len(new_by_key) == 510 and len(old_by_key) == 180
    count: Counter[str] = Counter()
    frame_rows = []
    for number, frame in sorted(by_frame.items()):
        per = Counter()
        for jersey in ROSTER:
            key = number, jersey
            item = frame["players"][jersey]
            candidate = item["jersey_keyed_candidate_court_m"] is not None
            if candidate:
                count["candidate_box"] += 1
                per["candidate_box"] += 1
            if key in new_by_key:
                r = new_by_key[key]
                count["new_review_slot"] += 1
                ground = r["ground_status"]
                identity = r["identity_status"]
                aligned = r["candidate_alignment"] == "same_player"
                accepted = (ground == "grounded" and identity not in ("uncertain", "not_visible")
                            and aligned and r["floor_alignment"] == "plausible")
                if aligned:
                    count["source_reviewed_same_player_box"] += 1
                if identity == "not_visible" or ground == "not_visible":
                    count["not_visible"] += 1
                if ground == "airborne":
                    count["airborne"] += 1
                if ground == "grounded":
                    count["grounded_source_state"] += 1
                if ground in ("feet_occluded", "uncertain"):
                    count["floor_state_unresolved"] += 1
            elif key in old_by_key:
                r = old_by_key[key]
                count["prior_30fps_review_slot"] += 1
                ground = r["ground_status"]
                aligned = r["candidate_alignment"] == "same_player"
                accepted = (ground == "grounded" and r["identity_status"] != "uncertain"
                            and aligned and r["proxy_floor_alignment"] == "plausible")
                if aligned:
                    count["source_reviewed_same_player_box"] += 1
                if ground == "grounded":
                    count["grounded_source_state"] += 1
                if ground == "airborne":
                    count["airborne"] += 1
                if ground in ("occluded", "uncertain"):
                    count["floor_state_unresolved"] += 1
            else:
                assert item["evidence_tier"] == "sampled_5hz_source_review"
                count["prior_5hz_review_slot"] += 1
                ground = item["floor_status"]
                accepted = item["source_reviewed_ground_court_m"] is not None
                if accepted:
                    count["grounded_source_state"] += 1
                    count["source_reviewed_same_player_box"] += 1
                if ground == "airborne":
                    count["airborne"] += 1
                if not accepted and ground not in ("airborne",):
                    count["floor_state_unresolved"] += 1
            if accepted:
                assert candidate
                count["accepted_grounded_proxy"] += 1
                per["accepted_grounded_proxy"] += 1
        if per["candidate_box"] == 6:
            count["six_candidate_frames"] += 1
        if per["accepted_grounded_proxy"] == 6:
            count["six_accepted_grounded_frames"] += 1
        frame_rows.append({"source_frame": number, **dict(per)})
    assert sum(count[k] for k in ("new_review_slot", "prior_30fps_review_slot", "prior_5hz_review_slot")) == 828
    assert count["candidate_box"] == 780 and count["six_candidate_frames"] == 104
    result = {"status": "complete_source_state_review_of_bracketed_candidate_interval_single_reviewer",
              "interval_inclusive": [36001, 36138],
              "exact_serve_to_dead_ball": False,
              "denominators": {"frames": 138, "player_slots": 828,
                               "source_grounded_slots": count["grounded_source_state"]},
              "counts": dict(count),
              "rates": {"candidate_box_slots": round(count["candidate_box"]/828, 4),
                        "source_reviewed_matched_box_slots": round(count["source_reviewed_same_player_box"]/828, 4),
                        "accepted_grounded_proxy_among_explicit_grounded": round(
                            count["accepted_grounded_proxy"]/count["grounded_source_state"], 4),
                        "six_accepted_grounded_frames": round(count["six_accepted_grounded_frames"]/138, 4)},
              "inputs_sha256": {"completed_review": sha(complete),
                                "manifest": sha(PACK / "manifest.json"),
                                "observation_ledger": sha(SCREEN / "s3p34_six_player_observation_ledger.json")},
              "limitations": ["The interval is source-bracketed, not exact serve-to-dead-ball.",
                              "New review is by one previously exposed reviewer; labels are not independent ground truth.",
                              "Court calibration is a separate approval decision.",
                              "Airborne states preserve identity and box evidence with unavailable floor position."],
              "frames": frame_rows}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = f"""# S3 P34 whole candidate-interval source review result

The reviewed interval is frames 36001–36138 (138 frames, 828 player slots). Its exact serve-to-dead-ball bounds remain unresolved. This result joins 23 prior sampled frames, 30 prior full-rate reviewed frames and 85 newly reviewed frames. The new review is single-reviewer and not independent ground truth. [Machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s3p34_whole_rally_review_score.json).

| Measure | Count | Denominator |
| --- | ---: | ---: |
| Candidate boxes present | {count['candidate_box']} | 828 slots |
| Source-reviewed same-player candidate boxes | {count['source_reviewed_same_player_box']} | 828 slots |
| Source-grounded states | {count['grounded_source_state']} | 828 slots |
| Accepted grounded box-bottom proxies | {count['accepted_grounded_proxy']} | {count['grounded_source_state']} source-grounded slots |
| Airborne states recorded | {count['airborne']} | 828 slots |
| Unresolved floor state or contact | {count['floor_state_unresolved']} | 828 slots |
| Frames with all six candidate boxes | {count['six_candidate_frames']} | 138 frames |
| Frames with six accepted grounded proxies | {count['six_accepted_grounded_frames']} | 138 frames |

An airborne player can retain a matched identity and box while the floor point is null. The six-grounded-frame rate is not an identity-tracking success rate. The accepted-grounded fraction is {100*result['rates']['accepted_grounded_proxy_among_explicit_grounded']:.1f}% **conditional on an explicit grounded verdict**; unresolved contact is outside this denominator and reported separately. Court metric approval, exact rally boundaries and external validation must be assessed separately.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"{count['accepted_grounded_proxy']}/{count['grounded_source_state']} accepted among source-grounded slots")


if __name__ == "__main__":
    main()
