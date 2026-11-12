"""Join existing S3 P34 source reviews without promoting candidates to truth."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
LEDGER = SCREEN / "s3p34_six_player_observation_ledger.json"
FORM = SCREEN / "s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv"
SCORE = SCREEN / "s3p34_30fps_ground_review/single_reviewer_score.json"
OUTPUT = SCREEN / "s3p34_whole_interval_coverage.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_WHOLE_INTERVAL_COVERAGE.md"
ROSTER = ("28", "12", "15", "7", "19", "21")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6)


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    score = json.loads(SCORE.read_text(encoding="utf-8"))
    with FORM.open(newline="", encoding="utf-8") as handle:
        manual_rows = list(csv.DictReader(handle))
    assert ledger["source_sha256"] == "da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b"
    assert score["completed_sha256"] == digest(FORM), "Ground review changed after scoring"
    assert ledger["roster"] == list(ROSTER)
    frames = ledger["frames"]
    assert len(frames) == 138 and [f["source_frame"] for f in frames] == list(range(36001, 36139))
    frame_lookup = {frame["source_frame"]: frame for frame in frames}
    reviews: dict[tuple[int, str], dict] = {}
    for row in manual_rows:
        frame = int(row["source_frame"])
        jersey = row["jersey"]
        key = (frame, jersey)
        assert frame in frame_lookup and jersey in ROSTER and key not in reviews
        assert frame_lookup[frame]["players"][jersey]["evidence_tier"] != "sampled_5hz_source_review"
        assert row["identity_status"] in ("confirmed", "sequence_only", "uncertain")
        assert row["ground_status"] in ("grounded", "airborne", "occluded", "uncertain")
        assert row["candidate_alignment"] in ("same_player", "wrong_player", "uncertain")
        assert row["proxy_floor_alignment"] in ("plausible", "implausible", "uncertain")
        reviews[key] = row
    assert len(reviews) == 180 and score["accepted_intervening_slots"] == 180

    slot_counts: Counter[str] = Counter()
    frame_counts: Counter[str] = Counter()
    frame_rows = []
    for frame in frames:
        number = frame["source_frame"]
        accepted = 0
        reviewed = 0
        candidates = 0
        source_state_counts: Counter[str] = Counter()
        for jersey in ROSTER:
            item = frame["players"][jersey]
            has_candidate = item["jersey_keyed_candidate_court_m"] is not None
            if has_candidate:
                candidates += 1
                slot_counts["candidate_box"] += 1
            else:
                slot_counts["candidate_missing"] += 1
            key = (number, jersey)
            if key in reviews:
                row = reviews[key]
                status = row["ground_status"]
                good = (status == "grounded" and row["identity_status"] != "uncertain"
                        and row["candidate_alignment"] == "same_player"
                        and row["proxy_floor_alignment"] == "plausible"
                        and bool(row["shoe_midpoint_x_px"] and row["shoe_midpoint_y_px"]))
                assert has_candidate, f"Accepted manual slot lacks candidate: {key}"
                reviewed += 1
                slot_counts["single_reviewer_30fps_slots"] += 1
                source_state_counts["single_reviewer_" + status] += 1
            elif item["evidence_tier"] == "sampled_5hz_source_review":
                status = item["floor_status"]
                good = item["source_reviewed_ground_court_m"] is not None
                reviewed += 1
                slot_counts["sampled_5hz_review_slots"] += 1
                source_state_counts["sampled_" + status] += 1
            else:
                status = "unreviewed_at_30fps"
                good = False
                slot_counts["unreviewed_source_slots"] += 1
            if good:
                accepted += 1
                slot_counts["accepted_grounded_proxy"] += 1
        if candidates == 6:
            frame_counts["all_six_candidate_boxes"] += 1
        if reviewed == 6:
            frame_counts["all_six_source_state_reviewed"] += 1
        if accepted == 6:
            frame_counts["all_six_grounded_proxy_accepted"] += 1
        frame_rows.append({"source_frame": number, "candidate_box_slots": candidates,
                           "source_state_reviewed_slots": reviewed,
                           "accepted_grounded_proxy_slots": accepted,
                           "source_state_counts": dict(source_state_counts)})

    assert sum(slot_counts[k] for k in ("candidate_box", "candidate_missing")) == 828
    assert slot_counts["candidate_box"] == 780 and slot_counts["candidate_missing"] == 48
    assert slot_counts["accepted_grounded_proxy"] == 301
    assert frame_counts["all_six_grounded_proxy_accepted"] == 41
    assert frame_counts["all_six_source_state_reviewed"] == 53
    result = {
        "status": "whole_candidate_interval_coverage_baseline_not_complete_rally_validation",
        "interval_inclusive": [36001, 36138],
        "interval_status": "source_bracketed_candidate_interval_not_exact_serve_to_dead_ball",
        "source_sha256": ledger["source_sha256"],
        "inputs_sha256": {"observation_ledger": digest(LEDGER),
                          "single_reviewer_completed_csv": digest(FORM),
                          "single_reviewer_score": digest(SCORE)},
        "source_frames": len(frames), "player_slots": len(frames) * 6,
        "slot_counts": dict(slot_counts), "frame_counts": dict(frame_counts),
        "fractions": {
            "candidate_box_slot_coverage": fraction(slot_counts["candidate_box"], 828),
            "all_six_candidate_frame_coverage": fraction(frame_counts["all_six_candidate_boxes"], 138),
            "source_reviewed_slot_coverage": fraction(318, 828),
            "all_six_source_reviewed_frame_coverage": fraction(53, 138),
            "accepted_grounded_slot_lower_bound": fraction(301, 828),
            "all_six_grounded_frame_lower_bound": fraction(41, 138),
        },
        "interpretation": "Unknown source states remain unknown. Lower bounds count only existing human-reviewed accepted positions; they are not estimated 30-fps success rates. Box availability is a separate candidate measure.",
        "frames": frame_rows,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = f"""# S3 P34 whole candidate-interval coverage baseline

This report joins the [138-frame observation ledger](HONOURS_U5_S3P34_SIX_PLAYER_OBSERVATION_LEDGER.md) to the [completed 30-fps single-reviewer segment](HONOURS_U5_S3P34_30FPS_GROUND_REVIEW_PROGRESS.md). The interval is source-bracketed frames 36001–36138, **not** exact serve contact to dead ball. [Machine-readable output](../data/matches/yt_u5HnY2aNW14/screening/s3p34_whole_interval_coverage.json) retains per-frame counts and input hashes.

| Evidence tier | Count | Denominator | Meaning |
| --- | ---: | ---: | --- |
| Jersey-keyed candidate boxes | {slot_counts['candidate_box']} | 828 player slots | {100*fraction(780,828):.1f}% candidate availability; not verified grounded positions |
| Frames with six candidate boxes | {frame_counts['all_six_candidate_boxes']} | 138 frames | {100*fraction(104,138):.1f}% candidate team availability |
| Source-reviewed player states | 318 | 828 player slots | 138 previously sampled slots plus 180 new single-reviewer slots |
| Frames with six source-reviewed states | {frame_counts['all_six_source_state_reviewed']} | 138 frames | 23 prior sampled frames plus 30 new frames |
| Accepted grounded proxies under those reviews | {slot_counts['accepted_grounded_proxy']} | 828 player slots | {100*fraction(301,828):.1f}% **known lower bound**; unreviewed slots are unknown |
| Frames with six accepted grounded proxies | {frame_counts['all_six_grounded_proxy_accepted']} | 138 frames | {100*fraction(41,138):.1f}% **known lower bound**, not full-interval success rate |

The accepted 301 slots comprise 121 accepted positions from 23 sampled five-Hz frames inside this interval and 180 from 30 new source-reviewed frames. The 41 complete frames comprise 11 sampled frames and 30 newly reviewed frames. The remaining 510 player slots have no individual 30-fps source-state verdict in these joined forms. They are **not counted as failed floor positions**; their status is unknown. The 48 missing box candidates stay missing even where sequence review saw a player in the source image. The 37-frame chosen diagnostic has six accepted positions throughout, but it was selected after box availability was known.

These counts answer how much of the **candidate interval is already supported by each evidence tier**. They do not yet estimate the proportion of the full serve-to-dead-ball rally that can be reliably tracked: exact events, source states outside the reviewed frames and the calibration decision remain unresolved. A player can remain identified and boxed while airborne, with a null floor coordinate. Do not treat structural airborne nulls as identity failures or fill them with a held position.

Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s3p34_whole_interval_coverage.py` from the repository root. This script reads completed human annotations and writes only derived files.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"{slot_counts['candidate_box']}/828 candidate boxes; {slot_counts['accepted_grounded_proxy']}/828 accepted reviewed grounded proxies")
    print(f"{frame_counts['all_six_candidate_boxes']}/138 six-candidate frames; {frame_counts['all_six_grounded_proxy_accepted']}/138 known complete reviewed frames")


if __name__ == "__main__":
    main()
