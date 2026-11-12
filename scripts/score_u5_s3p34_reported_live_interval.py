"""Join the reviewed S3 P34 opening frames to its 30-fps player record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
OPENING = SCREEN / "s3p34_opening_frame_review/completed.json"
OPENING_MANIFEST = SCREEN / "s3p34_opening_frame_review/manifest.json"
INTERVAL = SCREEN / "s3p34_full_30fps_review_score.json"
EVENT = SCREEN / "s3p34_event_boundary_review/completed.json"
OUT = SCREEN / "s3p34_reported_live_interval_score.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_REPORTED_LIVE_INTERVAL_RESULT.md"
SLOTS = ("28", "12", "15", "7", "19", "21")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    opening = json.loads(OPENING.read_text(encoding="utf-8"))
    manifest = json.loads(OPENING_MANIFEST.read_text(encoding="utf-8"))
    interval = json.loads(INTERVAL.read_text(encoding="utf-8"))
    event = json.loads(EVENT.read_text(encoding="utf-8"))
    assert opening["manifest_sha256"] == sha(OPENING_MANIFEST)
    assert event["summary"]["serve_contact_visible_frames"] == [35998]
    assert event["summary"]["first_reviewed_dead"] == 36138
    assert event["summary"]["exact_point_end_certified"] is False
    assert set(opening["frames"]) == {"35998", "35999", "36000"}
    assert manifest["slots"] == list(SLOTS)
    opening_boxes = {r["frame"]: r["suggested_boxes"] for r in manifest["rows"]}
    rows = []
    for frame in (35998, 35999, 36000):
        players = {}
        for slot in SLOTS:
            verdict = opening["frames"][str(frame)][slot]
            candidate = slot in opening_boxes[frame] and verdict["box"] == "same"
            accepted = (candidate and verdict["identity"] in {"same_by_sequence", "digit_confirmed"}
                        and verdict["ground"] == "grounded" and verdict["floor"] == "plausible")
            players[slot] = {"candidate_box": candidate, "accepted_grounded_proxy": accepted,
                             "source_state": verdict["ground"]}
        rows.append({"source_frame": frame, "review_tier": "opening_packet",
                     "candidate_boxes": sum(p["candidate_box"] for p in players.values()),
                     "accepted_grounded_proxies": sum(p["accepted_grounded_proxy"] for p in players.values()),
                     "players": players})
    old = [r for r in interval["frames"] if 36001 <= r["source_frame"] <= 36137]
    assert len(old) == 137
    rows.extend(old)
    assert [r["source_frame"] for r in rows] == list(range(35998, 36138))
    frames = len(rows)
    counts = {"source_frames": frames, "player_slots": frames * 6,
              "candidate_box_slots": sum(r["candidate_boxes"] for r in rows),
              "accepted_grounded_proxy_slots": sum(r["accepted_grounded_proxies"] for r in rows),
              "six_candidate_box_frames": sum(r["candidate_boxes"] == 6 for r in rows),
              "six_accepted_grounded_frames": sum(r["accepted_grounded_proxies"] == 6 for r in rows),
              "opening_airborne_slots": sum(p["source_state"] == "airborne"
                                            for r in rows[:3] for p in r["players"].values())}
    result = {
        "status": "complete_single_reviewer_six_player_state_record_over_reported_live_interval",
        "interval_inclusive": [35998, 36137],
        "first_reviewed_dead_frame": 36138,
        "last_live_frame_from_reviewer_statement_not_individual_event_verdict": 36137,
        "exact_point_end_certified": False,
        "strict_all_six_grounded_floor_trajectory": False,
        "counts": counts,
        "rates": {"candidate_box_slot_fraction": counts["candidate_box_slots"] / counts["player_slots"],
                  "accepted_grounded_proxy_slot_fraction": counts["accepted_grounded_proxy_slots"] / counts["player_slots"],
                  "six_grounded_frame_fraction": counts["six_accepted_grounded_frames"] / frames},
        "inputs_sha256": {"opening_review": sha(OPENING), "opening_manifest": sha(OPENING_MANIFEST),
                          "candidate_interval_score": sha(INTERVAL), "event_review": sha(EVENT)},
        "limitations": ["Point ending was given as a reviewer statement, without an individually marked last-live event frame.",
                        "The opening three frames were chosen and reviewed after the serve-contact judgment.",
                        "The source and box review was candidate-assisted and completed by one reviewer.",
                        "Airborne, missing or uncertain floor positions remain null; all-six floor geometry exists only in eligible frames.",
                        "Court transform approval is a separate issue; this report scores state and proxy eligibility only."],
        "frames": rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# S3 P34 reported live-interval six-player result\n\n"
        "[Machine-readable joined score](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reported_live_interval_score.json). "
        "The single-reviewer event record marks serve contact at **35998** and the first reviewed dead frame at **36138**. "
        "The reviewer stated that play was live before 36138, but no individual last-live event verdict was saved, "
        "so the exact point-ending instant is uncertified. The working live interval is **35998–36137**, inclusive.\n\n"
        f"All **{frames} source frames** in that interval have six source/box state records (**{counts['player_slots']} player slots**). "
        f"There are **{counts['candidate_box_slots']}/{counts['player_slots']}** accepted same-player candidate-box slots "
        f"and **{counts['accepted_grounded_proxy_slots']}/{counts['player_slots']}** accepted grounded box-bottom proxies. "
        f"All six candidate boxes are present in **{counts['six_candidate_box_frames']}/{frames}** frames; "
        f"all six grounded proxies are accepted in **{counts['six_accepted_grounded_frames']}/{frames}** frames. "
        "The serving player #12 is airborne in all three newly reviewed opening frames; his box remains a valid identity observation "
        "while his floor coordinate is null.\n\n"
        "This is a **complete six-player state and candidate-box review over the reported live interval**, with explicit missing or airborne "
        "floor coordinates. It is not a continuous six-grounded-floor-point trajectory or independently adjudicated positional ground truth. "
        "The last-live boundary is based on a broad reviewer statement; source timing, the camera transform and box-floor accuracy "
        "remain separate qualifications. The opening-frame packet was added after contact timing was reviewed.\n",
        encoding="utf-8",
    )
    print(counts)


if __name__ == "__main__":
    main()
