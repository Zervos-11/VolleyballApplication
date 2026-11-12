"""Build a conservative, source-reviewed 5 Hz S3 P34 diagnostic ledger.

This is not final metric input: play boundaries and the court transform remain
uncertified. Unchecked frames and airborne players are never filled or held.
"""

import hashlib
import json
import math
import statistics
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
SOURCE = SCREEN / "source_bracketed_30fps_screen.json"
OUT = SCREEN / "s3p34_reviewed_sample_ledger.json"
JERSEY_TO_RAW = {"28": 1, "12": 3, "15": 6, "7": 9, "19": 10, "21": 13}

# The source sheets were reviewed at this 5 Hz grid. Only the listed instants
# were judged to have six grounded, readable UCLA boxes. The remainder retain
# candidate boxes but have no accepted six-player metric.
ALL_SIX_GROUNDED = {36036, 36042, 36054, 36066, 36072,
                    36078, 36084, 36090, 36096, 36102, 36138}
FRAME_REASONS = {
    36000: "server_12_airborne_after_contact",
    36006: "server_12_landing_not_certified",
    36012: "server_12_ground_contact_not_certified",
    36018: "server_12_ground_contact_not_certified",
    36024: "server_12_ground_contact_not_certified",
    36030: "jersey_7_visible_but_unboxed",
    36048: "jersey_21_visible_but_unboxed",
    36060: "jersey_21_visible_but_unboxed",
    36108: "front_players_enter_airborne_or_occluded_interval",
    36114: "jerseys_21_and_15_airborne",
    36120: "jerseys_21_and_15_airborne",
    36126: "front_player_landing_contact_not_certified",
    36132: "jersey_7_one_foot_raised_box_bottom_unreliable",
}
PLAYER_EXCLUSIONS = {
    36000: {"12": "airborne"},
    36006: {"12": "landing_contact_uncertain"},
    36012: {"12": "ground_contact_uncertain"},
    36018: {"12": "ground_contact_uncertain"},
    36024: {"12": "ground_contact_uncertain"},
    36030: {"7": "visible_but_unboxed"},
    36048: {"21": "visible_but_unboxed"},
    36060: {"21": "visible_but_unboxed"},
    36108: {"21": "airborne_or_occluded", "15": "airborne_or_occluded"},
    36114: {"21": "airborne", "15": "airborne"},
    36120: {"21": "airborne", "15": "airborne"},
    36126: {"21": "landing_contact_uncertain", "15": "landing_contact_uncertain",
            "7": "visible_but_unboxed"},
    36132: {"7": "one_foot_raised_proxy_unreliable"},
}


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    point = next(p for p in data["points"] if (p["set"], p["point_number"]) == (3, 34))
    by_frame = {r["source_frame"]: r for r in point["rows"]}
    sampled = list(range(36000, 36139, 6))
    assert set(sampled) == ALL_SIX_GROUNDED | set(FRAME_REASONS)
    assert set(PLAYER_EXCLUSIONS) == set(FRAME_REASONS)
    # Numeric continuity is a screen for jumps, not a visual identity verdict.
    last_centres = {}
    adjacent_motion = []
    for number in range(sampled[0], sampled[-1] + 1):
        near = {p["raw_track_id"]: p for p in by_frame[number]["proposals"]
                if p["net_side_status"] == "near_floor_side_candidate"}
        for jersey, original_raw in JERSEY_TO_RAW.items():
            raw = (original_raw if jersey != "7" or number < 36117 or
                   original_raw in near else 78)
            box = near.get(raw)
            if box is None:
                continue
            x1, y1, x2, y2 = box["bbox_px"]
            centre = ((x1 + x2) / 2, (y1 + y2) / 2)
            if jersey in last_centres and number - last_centres[jersey][0] == 1:
                adjacent_motion.append({"frame": number, "jersey": jersey,
                                        "centre_displacement_px": round(math.dist(
                                            centre, last_centres[jersey][1]), 2)})
            last_centres[jersey] = number, centre
    rows = []
    for number in sampled:
        source_image = SCREEN / f"s3p34_validation_review/source_{number}.png"
        assert source_image.exists(), source_image
        source_row = by_frame[number]
        proposals = {p["raw_track_id"]: p for p in source_row["proposals"]
                     if p["net_side_status"] == "near_floor_side_candidate"}
        observed = {}
        for jersey, original_raw in JERSEY_TO_RAW.items():
            raw = 78 if jersey == "7" and number >= 36122 else original_raw
            candidate = proposals.get(raw)
            exclusion = PLAYER_EXCLUSIONS.get(number, {}).get(jersey)
            if candidate is None:
                assert exclusion is not None, (number, jersey)
            accepted = candidate is not None and exclusion is None
            observed[jersey] = {
                "reviewed_raw_id": raw,
                "candidate_box_bottom_court_m": (candidate["box_bottom_court_m"]
                                                  if candidate else None),
                "candidate_bbox_px": candidate["bbox_px"] if candidate else None,
                "accepted_ground_coordinate_m": (candidate["box_bottom_court_m"]
                                                 if accepted else None),
                "status": ("reviewed_grounded_box_bottom_proxy" if accepted
                           else exclusion),
            }
        if number in ALL_SIX_GROUNDED:
            assert all(x["accepted_ground_coordinate_m"] is not None
                       for x in observed.values()), number
            assert 39 not in JERSEY_TO_RAW.values()
            values = metrics([tuple(observed[j]["accepted_ground_coordinate_m"])
                              for j in JERSEY_TO_RAW])
            values = {k: round(v, 4) for k, v in values.items()}
        else:
            assert any(x["accepted_ground_coordinate_m"] is None
                       for x in observed.values()), number
            values = None
        rows.append({
            "source_frame": number,
            "source_image": source_image.relative_to(ROOT).as_posix(),
            "source_image_sha256": hashlib.sha256(source_image.read_bytes()).hexdigest(),
            "identity_review": "single_reviewer_visual_5hz_source_sheet",
            "all_six_grounded_proxy_status": ("accepted_for_exploratory_comparison"
                                               if values else "excluded"),
            "exclusion_reason": FRAME_REASONS.get(number),
            "players": observed,
            "exploratory_team_metrics": values,
        })
    accepted = [x["exploratory_team_metrics"] for x in rows
                if x["exploratory_team_metrics"]]
    result = {
        "status": "source_reviewed_sampled_proxy_diagnostic_not_validated_full_rally",
        "source_sha256": data["source_sha256"],
        "screen_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "set": 3, "point_number": 34,
        "sample_interval_inclusive": [sampled[0], sampled[-1]],
        "sample_stride_source_frames": 6,
        "sample_rate_hz": 5,
        "event_boundary_status": "exact_serve_contact_and_dead_ball_not_certified",
        "calibration_status": "staged_not_validated_for_final_metric_use",
        "raw_id_correction": "UCLA jersey 7: prefer ID 9 while present, use ID 78 when ID 9 is absent from frame 36117 onward; far-side ID 39 excluded",
        "interframe_box_motion_screen": {
            "adjacent_identity_corrected_box_pairs": len(adjacent_motion),
            "maximum_centre_displacement_px": max(
                x["centre_displacement_px"] for x in adjacent_motion),
            "pairs_over_30px": [x for x in adjacent_motion
                                if x["centre_displacement_px"] > 30],
            "interpretation": "No large one-frame centre jump is a numeric continuity diagnostic, not proof of continuous visual jersey identity or grounded floor position."
        },
        "accepted_frame_rule": "six source-reviewed near-side jerseys with grounded, readable box-bottom proxies; no airborne or missing positions held or interpolated",
        "summary": {
            "sampled_frames": len(rows),
            "sampled_player_slots": len(rows) * len(JERSEY_TO_RAW),
            "accepted_individual_grounded_proxies": sum(
                p["accepted_ground_coordinate_m"] is not None
                for row in rows for p in row["players"].values()),
            "accepted_exploratory_frames": len(accepted),
            "excluded_frames": len(rows) - len(accepted),
            "accepted_fraction_of_samples": round(len(accepted) / len(rows), 4),
            "accepted_fraction_of_source_interval": round(len(accepted) /
                                                          (sampled[-1] - sampled[0] + 1), 4),
            "exploratory_median_team_metrics": {
                k: round(statistics.median(x[k] for x in accepted), 4)
                for k in accepted[0]
            },
        },
        "frames": rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["summary"])


if __name__ == "__main__":
    main()
