"""Join S3 P34 candidate paths, reviewed gaps, and sampled ground verdicts.

The join preserves evidence tiers. It does not make unsampled identities or
ground points source-verified and never fills a missing court coordinate.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
PATHS = BASE / "full_rally_candidate_paths.json"
SAMPLED = BASE / "s3p34_reviewed_sample_ledger.json"
GAPS = BASE / "s3p34_full_span_review/gap_source_verdicts.json"
IDENTITY = BASE / "s3p34_full_span_review/candidate_identity_source_review.json"
OUT = BASE / "s3p34_six_player_observation_ledger.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_SIX_PLAYER_OBSERVATION_LEDGER.md"
JERSEYS = ("28", "12", "15", "7", "19", "21")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths, sampled, gaps, identity = (read(p) for p in
                                      (PATHS, SAMPLED, GAPS, IDENTITY))
    point = next(p for p in paths["points"]
                 if (p["set"], p["point_number"]) == (3, 34))
    first, last = point["interval_inclusive"]
    assert (first, last) == (36001, 36138)
    assert paths["source_sha256"] == sampled["source_sha256"]
    assert identity["interval_inclusive"] == [first, last]
    assert identity["source_review_exceptions"] == []
    reviewed_pages = set(identity["reviewed_pages"])
    expected_pages = {f"review_page_{n:02d}.jpg" for n in range(1, 48)}
    assert reviewed_pages == expected_pages
    assert len(identity["reviewed_pages"]) == len(expected_pages)
    assert all((IDENTITY.parent / name).is_file() for name in reviewed_pages)
    sampled_frames = {f["source_frame"]: f for f in sampled["frames"]
                      if first <= f["source_frame"] <= last}
    gap_slots = {}
    for verdict in gaps["verdicts"]:
        assert verdict["source_visibility"] == "visible"
        for frame in range(verdict["interval_inclusive"][0],
                           verdict["interval_inclusive"][1] + 1):
            key = (frame, verdict["jersey"])
            assert key not in gap_slots
            gap_slots[key] = verdict
    frames = []
    counts = Counter()
    for frame in point["frames"]:
        number = frame["source_frame"]
        rows = {}
        for jersey in JERSEYS:
            candidate = frame["court_box_bottom_by_jersey_m"][jersey]
            sample = sampled_frames.get(number)
            reviewed = sample["players"][jersey] if sample else None
            gap = gap_slots.get((number, jersey))
            assert (candidate is None) == (gap is not None), (
                number, jersey, "gap review and candidate availability disagree")
            if reviewed:
                evidence = "sampled_5hz_source_review"
                floor_status = reviewed["status"]
                accepted = reviewed["accepted_ground_coordinate_m"]
                identity_status = "existing_sampled_source_review"
                if accepted is not None:
                    assert candidate is not None
            elif gap:
                evidence = "targeted_gap_sequence_review"
                floor_status = gap["floor_status"]
                accepted = None
                identity_status = "visible_in_targeted_gap_sequence"
            else:
                evidence = "source_sequence_reviewed_candidate_unsampled"
                floor_status = "not_reviewed_at_30fps"
                accepted = None
                identity_status = identity["candidate_verdict_for_reviewed_pages"]
            page = f"review_page_{(number - 36000) // 3 + 1:02d}.jpg"
            assert page in reviewed_pages
            rows[jersey] = {
                "jersey_keyed_candidate_court_m": candidate,
                "source_reviewed_ground_court_m": accepted,
                "evidence_tier": evidence,
                "floor_status": floor_status,
                "identity_source_review_status": identity_status,
                "source_review_page": page,
                "source_visibility_in_gap_review": (
                    gap["source_visibility"] if gap else None),
            }
            counts["candidate_present" if candidate is not None
                   else "candidate_missing"] += 1
            counts[evidence] += 1
            if accepted is not None:
                counts["reviewed_ground_slots"] += 1
        frames.append({"source_frame": number,
                       "six_candidate_boxes": all(
                           rows[j]["jersey_keyed_candidate_court_m"] is not None
                           for j in JERSEYS),
                       "six_reviewed_ground_positions": all(
                           rows[j]["source_reviewed_ground_court_m"] is not None
                           for j in JERSEYS),
                       "players": rows})
    assert len(frames) == 138
    assert counts["candidate_present"] == 780
    assert counts["candidate_missing"] == len(gap_slots) == 48
    assert sum(f["six_candidate_boxes"] for f in frames) == 104
    assert counts["sampled_5hz_source_review"] == 23 * 6
    assert counts["source_sequence_reviewed_candidate_unsampled"] == 651
    assert sum(f["six_reviewed_ground_positions"] for f in frames) == 11
    result = {
        "status": "six_player_full_span_observation_ledger_not_validated_full_rally_trajectory",
        "source_sha256": paths["source_sha256"],
        "input_sha256": {"candidate_paths": sha(PATHS),
                         "sampled_source_review": sha(SAMPLED),
                         "targeted_gap_review": sha(GAPS),
                         "candidate_identity_source_review": sha(IDENTITY),
                         "review_pages": {name: sha(IDENTITY.parent / name)
                                          for name in sorted(reviewed_pages)}},
        "interval_inclusive": [first, last],
        "roster": list(JERSEYS),
        "coordinate_rule": "Candidate court points remain provisional; only accepted 5 Hz sampled grounded proxies appear in source_reviewed_ground_court_m. No interpolation or airborne floor projection.",
        "summary": {
            "source_frames": len(frames),
            "player_slots": len(frames) * 6,
            "frames_with_six_candidates": 104,
            "frames_with_missing_candidate": 34,
            "candidate_present_slots": counts["candidate_present"],
            "candidate_missing_slots": counts["candidate_missing"],
            "sampled_5hz_reviewed_frames_inside_interval": len(sampled_frames),
            "sampled_5hz_reviewed_slots_inside_interval": counts["sampled_5hz_source_review"],
            "reviewed_ground_slots_inside_interval": counts["reviewed_ground_slots"],
            "sampled_frames_with_six_reviewed_ground_positions": 11,
            "unsampled_source_sequence_reviewed_candidate_slots": counts["source_sequence_reviewed_candidate_unsampled"],
            "gap_sequence_reviewed_slots": counts["targeted_gap_sequence_review"],
            "fully_validated_rally_trajectories": 0,
        },
        "frames": frames,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    s = result["summary"]
    lines = [
        "# S3 P34 six-player full-span observation ledger", "",
        "The [machine-readable ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_six_player_observation_ledger.json) "
        "joins the six named UCLA players across every source frame from "
        "36001 through 36138. Each slot preserves the tracker candidate, "
        "any existing 5 Hz source-reviewed grounded coordinate, and the "
        "targeted source visibility verdict for missing candidates. "
        "A candidate point does not become a validated floor point by appearing "
        "in this ledger. The [source-sequence verdict record]"
        "(../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/candidate_identity_source_review.json) "
        "lists the 47 inspected paired contact sheets and the limits of the "
        "visual identity assessment. This added pass was AI-assisted and has "
        "not received independent human adjudication.", "",
        "| Evidence tier in this interval | Player slots | Meaning |",
        "| --- | ---: | --- |",
        f"| Existing 5 Hz source review | {s['sampled_5hz_reviewed_slots_inside_interval']} | "
        "Grounded positions accepted or rejected per player at 23 sampled instants. |",
        f"| Targeted gap sequence review | {s['gap_sequence_reviewed_slots']} | "
        "Visible player with no jersey-keyed candidate; no new floor coordinate. |",
        f"| Unsampled source sequence-reviewed candidate | {s['unsampled_source_sequence_reviewed_candidate_slots']} | "
        "Candidate-to-player continuity checked in paired 30 fps contact sheets; ground position unreviewed. |",
        f"| **Total** | **{s['player_slots']}** | **138 frames x six players.** |",
        "", f"Candidate boxes exist in {s['candidate_present_slots']}/{s['player_slots']} "
        f"player slots and all six candidate boxes coexist in {s['frames_with_six_candidates']}/138 "
        "frames. The 48 missing candidate slots occupy 34 frames; the targeted "
        "gap audit reports all of those players visible in the source sequence. "
        f"Within the interval, the existing 5 Hz source review accepted {s['reviewed_ground_slots_inside_interval']} "
        "individual grounded proxies and eleven complete six-player frames. "
        "The sampled review also includes frame 36000 outside this interval, "
        "which explains its separate 126/144 denominator.", "",
        "The 138 frames begin at a conservative live-looking start and end at "
        "the last reviewed live frame. They are not exact serve-contact to "
        "dead-ball boundaries. All 47 contact sheets were inspected in frame "
        "order. The 651 previously candidate-only slots have sequence-consistent "
        "visual assignments, but jersey digits are not independently readable "
        "at every frame and ground contacts outside the sampled review remain "
        "unassessed. Frame 36112 includes "
        "an airborne #15 without a usable floor point. Thus the ledger supports "
        "a six-player *observation and missingness account*, not a validated "
        "continuous six-grounded-position rally or full-rally distance.", "",
        "Reproduce with `.\\.venv\\Scripts\\python.exe "
        "scripts/build_u5_s3p34_six_player_observation_ledger.py`. "
        "The script checks the join against the saved candidate and source-review files.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
