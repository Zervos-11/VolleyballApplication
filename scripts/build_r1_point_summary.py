"""Package the bounded r1 point as a player-by-player case-study summary."""

from __future__ import annotations

import json

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


ANCHOR_PATH = BASE / "r1_anchor_path_estimate.json"
FOOT_CENTRE = BASE / "r1_p20_foot_level_center_distance_trial.json"
P12_HYBRID = BASE / "r1_p12_box_center_hybrid_trial.json"
TRANSFER = BASE / "r1_d79_hold_policy_transfer.json"
P10_GAP = BASE / "r1_p10_gap_source_review.json"
OUT = BASE / "r1_point_summary.json"
PLAYERS = ("9", "10", "11", "12", "13", "20")
NAMES = {"9": "Blue #9", "10": "Blue #10", "11": "Blue #11",
         "12": "Blue #12", "13": "Blue #13", "20": "Yellow #20"}
UNAVAILABLE_REASONS = {
    "11": "103 missing candidate boxes and a raw-ID handoff involving another player",
    "13": "272 missing candidate boxes during overlap with #20",
}


def missing_runs(frames: list[int]) -> list[dict]:
    runs = []
    for frame in frames:
        if runs and frame == runs[-1]["end_frame"] + 1:
            runs[-1]["end_frame"] = frame
            runs[-1]["frames"] += 1
        else:
            runs.append({"start_frame": frame, "end_frame": frame, "frames": 1})
    return runs


def main() -> None:
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))
    anchor = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
    foot = json.loads(FOOT_CENTRE.read_text(encoding="utf-8"))
    p12 = json.loads(P12_HYBRID.read_text(encoding="utf-8"))
    transfer = json.loads(TRANSFER.read_text(encoding="utf-8"))
    p10_gap = json.loads(P10_GAP.read_text(encoding="utf-8"))
    assert foot["source_sha256"] == sha256(SOURCE)
    assert foot["visual_candidate_sha256"] == sha256(VISUAL)
    assert foot["physical_distance_released"] is False
    assert p12["record_sha256"] == sha256(VISUAL)
    assert p12["distance_status"] == "reportable_approximate_endpoint_chord_estimate"
    assert p12["validation_status"] == "not_validated_physical_distance"
    assert p12["distance_scope_frames_inclusive"] == [21070, 21463]
    assert transfer["record_sha256"] == sha256(VISUAL)
    assert transfer["players"]["10"]["metric_status"] == "geometry_passes_candidate_only"
    assert transfer["players"]["10"]["visible_segment_path_m"] == 9.66
    assert transfer["players"]["10"]["closed_gap_count"] == 1
    assert p10_gap["visual_candidate_sha256"] == sha256(VISUAL)
    assert p10_gap["source_sha256"] == sha256(SOURCE)
    assert p10_gap["source_endpoint_frames"] == [21098, 21133]
    records = visual["frame_records"]
    assert [row["frame"] for row in records] == list(range(21050, 21464))
    players = []
    for player_id in PLAYERS:
        statuses = [(row["frame"], row["players"][player_id]["box_status"])
                    for row in records]
        counts = {status: sum(value == status for _, value in statuses)
                  for status in ("raw_box_candidate", "invalid_truncated", "missing")}
        missing = [frame for frame, status in statuses if status != "raw_box_candidate"]
        row = {
            "player_id": player_id,
            "display_name": NAMES[player_id],
            "valid_box_frames": counts["raw_box_candidate"],
            "invalid_truncated_box_frames": counts["invalid_truncated"],
            "missing_box_frames": counts["missing"],
            "box_coverage_percent": round(100 * counts["raw_box_candidate"] / len(records), 1),
            "unusable_box_runs": missing_runs(missing),
            "approximate_distance_m": None,
            "distance_frames_inclusive": None,
            "distance_method": None,
            "smoothing_sensitivity_m": None,
            "distance_note": UNAVAILABLE_REASONS.get(player_id),
        }
        if player_id == "9":
            estimate = anchor["player_9"]
            row.update({
                "approximate_distance_m": round(estimate["rough_smoothed_box_bottom_path_m"], 1),
                "distance_frames_inclusive": estimate["source_frames_inclusive"],
                "distance_method": "15-frame median of court-projected box-bottom centre",
                "smoothing_sensitivity_m": [
                    round(estimate["method_sensitivity_median_width_frames_to_path_m"]["31"], 1),
                    round(estimate["method_sensitivity_median_width_frames_to_path_m"]["5"], 1)],
                "distance_note": "Starts at the source-checked serve landing; excludes the first 20 candidate frames.",
            })
        elif player_id == "10":
            visible = transfer["players"]["10"]["visible_segment_path_m"]
            chord = p10_gap["source_endpoint_displacement_m_approx"]
            row.update({
                "approximate_distance_m": round(visible + chord, 2),
                "distance_frames_inclusive": [21050, 21463],
                "distance_method": "15-frame median of court-projected box-bottom centre on visible segments, plus source-shoe endpoint chord across one closed gap",
                "distance_note": "Agreed-policy estimate: 9.66 m visible proxy plus about 0.06 m across frames 21098–21133. The ending shoe is partly occluded; hidden detours are omitted. Not validated physical travel.",
            })
        elif player_id == "12":
            row.update({
                "approximate_distance_m": p12["reported_approximate_distance_m"],
                "distance_frames_inclusive": p12["distance_scope_frames_inclusive"],
                "distance_method": "15-frame median of source-anchored box-centre translation, with straight endpoint chords across closed holds",
                "distance_note": "Agreed-policy estimate; first 20 frames excluded. The 32-frame overlap uses a 1.62 m endpoint chord and omits hidden detours. Not validated physical travel.",
            })
        elif player_id == "20":
            distances = foot["distance_proxy_m_by_interval_and_window"]["full_candidate_point"]
            row.update({
                "approximate_distance_m": round(distances["15"], 1),
                "distance_frames_inclusive": foot["frames_inclusive"],
                "distance_method": "15-frame median of foot-level centre proxy",
                "smoothing_sensitivity_m": [round(distances["31"], 1), round(distances["5"], 1)],
                "distance_note": "130 two-shoe frames, 280 box-centre fallback frames, four invalid-box frames bridged for diagnostic smoothing.",
            })
        players.append(row)
    result = {
        "status": "bounded_single_reviewer_development_point_summary",
        "match_id": "yt_FqE5pTJqx8g", "rally_id": "r1",
        "frames_inclusive": [21050, 21463], "fps_nominal": 50,
        "duration_s": 8.28, "player_count": len(players),
        "source_sha256": sha256(SOURCE),
        "visual_candidate_sha256": sha256(VISUAL),
        "anchor_path_sha256": sha256(ANCHOR_PATH),
        "foot_centre_sha256": sha256(FOOT_CENTRE),
        "p12_hybrid_sha256": sha256(P12_HYBRID),
        "transfer_sha256": sha256(TRANSFER),
        "p10_gap_review_sha256": sha256(P10_GAP),
        "players": players,
        "summary": {
            "players_with_approximate_distance": [row["player_id"] for row in players
                                                  if row["approximate_distance_m"] is not None],
            "all_six_usable_box_frames": sum(all(
                frame["players"][player_id]["box_status"] == "raw_box_candidate"
                for player_id in PLAYERS) for frame in records),
            "total_player_box_slots": len(records) * len(PLAYERS),
            "valid_player_box_slots": sum(row["valid_box_frames"] for row in players),
        },
        "scope": "Approximate, source-specific player path proxies; box coverage is not verified ground-position coverage.",
        "formal_tracking_accuracy_claim": False,
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    assert result["summary"]["all_six_usable_box_frames"] == 108
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["summary"])
    print([(row["player_id"], row["valid_box_frames"], row["approximate_distance_m"])
           for row in players])


if __name__ == "__main__":
    main()
