"""Build a local-only index of the two bounded volleyball case studies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "data/processed/fqe_r1_boundary_recheck"
AOEP = ROOT / "data/processed/aoep_new_source"
OUT = ROOT / "data/processed/case_studies_catalog.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    r1_summary_path = R1 / "r1_point_summary.json"
    r1_manifest_path = R1 / "R1_CASE_STUDY_MANIFEST.json"
    r1_scenario_path = R1 / "r1_six_player_proxy_scenario.json"
    aoep_distance_path = AOEP / "reviewed_distance_estimate_75180_75229.json"
    aoep_manifest_path = AOEP / "CASE_STUDY_MANIFEST.json"
    r1 = read(r1_summary_path)
    r1_manifest = read(r1_manifest_path)
    r1_scenario = read(r1_scenario_path)
    aoep = read(aoep_distance_path)
    aoep_manifest = read(aoep_manifest_path)
    r1_source_record = read(ROOT / "data/matches/yt_FqE5pTJqx8g/source_record.json")
    aoep_source_record = read(ROOT / "data/matches/yt_AoEP-YiWRvc/source_record.json")
    assert r1["source_sha256"] == r1_manifest["source_video_sha256_verified"]
    assert aoep["source_sha256"] == aoep_manifest["source"]["sha256"]
    assert aoep["frame_range_inclusive"] == [75180, 75229]
    assert aoep_manifest["scope"]["complete_rally"] is False
    assert r1_source_record["sha256"] == r1["source_sha256"]
    assert aoep_source_record["sha256"] == aoep["source_sha256"]
    assert r1["summary"]["players_with_approximate_distance"] == ["9", "10", "12", "20"]
    assert r1_scenario["point_summary_sha256"] == sha256(r1_summary_path)
    assert r1_scenario["visual_candidate_sha256"] == r1["visual_candidate_sha256"]
    assert r1_scenario["physical_team_distance_released"] is False

    aoep_names = {"yellow_centre_4": "Yellow #4", "navy_libero_10": "Navy libero #10",
                  "yellow_left_5": "Yellow #5", "yellow_setter_18": "Yellow setter #18"}
    aoep_distances = []
    for source, rows in (("full_slice", aoep["players"]),
                         ("post_landing_segment", aoep["partial_players"])):
        for key, row in rows.items():
            aoep_distances.append({
                "player": aoep_names[key],
                "approximate_distance_m": row["distance_estimate_m"],
                "frames_inclusive": row.get("frame_range_inclusive", [75180, 75229]),
                "scope": source,
                "method_range_m": row["three_to_seven_frame_method_range_m"],
            })

    result = {
        "schema_version": "local_case_studies_catalog_v1",
        "status": "two_bounded_development_case_studies",
        "release_scope": "Local approximate case studies; no validated full-match or public dataset release.",
        "case_studies": [
            {
                "id": "r1_candidate_point", "title": "R1 candidate point",
                "match_id": r1["match_id"], "source_sha256": r1["source_sha256"],
                "frames_inclusive": r1["frames_inclusive"], "fps_nominal": r1["fps_nominal"],
                "scope": "Provisional 414-frame point; six near-side player slots",
                "complete_rally_confirmed": False,
                "source_use_status": r1_source_record["rights_status"],
                "privacy_review_status": r1_source_record["privacy_review_status"],
                "candidate_box_player_frames": r1["summary"]["valid_player_box_slots"],
                "candidate_box_total_player_frames": r1["summary"]["total_player_box_slots"],
                "all_six_box_frames": r1["summary"]["all_six_usable_box_frames"],
                "distances": [{"player": row["display_name"],
                               "approximate_distance_m": row["approximate_distance_m"],
                               "frames_inclusive": row["distance_frames_inclusive"],
                               "scope": "endpoint_chord_scoped_estimate" if row["player_id"] in {"10", "12"}
                                        else "bounded_player_path",
                               "method_range_m": row["smoothing_sensitivity_m"]}
                              for row in r1["players"] if row["approximate_distance_m"] is not None],
                "players_without_distance": [row["display_name"] for row in r1["players"]
                                             if row["approximate_distance_m"] is None],
                "six_player_proxy_scenario": {
                    "assumption_based_sum_m": r1_scenario["displayed_six_player_sum_m"],
                    "smoothing_scenario_range_m": [
                        r1_scenario["six_player_sum_if_modelled_players_use_31_frame_median_m"],
                        r1_scenario["six_player_sum_if_modelled_players_use_5_frame_median_m"]],
                    "source_file": "r1_six_player_proxy_scenario.json",
                    "source_file_sha256": sha256(r1_scenario_path),
                    "physical_distance": False,
                },
                "viewer_path": "/r1-case-study", "source_file": "r1_point_summary.json",
                "source_file_sha256": sha256(r1_summary_path),
                "manifest_sha256": sha256(r1_manifest_path),
            },
            {
                "id": "aoep_50_frame_slice", "title": "AoEP in-play slice",
                "match_id": aoep_manifest["match_id"],
                "source_sha256": aoep["source_sha256"],
                "frames_inclusive": aoep["frame_range_inclusive"],
                "fps_nominal": aoep_manifest["scope"]["source_frame_rate_fps"],
                "scope": "50-frame in-play slice of a highlights recording; surrounding point end unresolved",
                "complete_rally_confirmed": False,
                "source_use_status": aoep_source_record["rights_status"],
                "privacy_review_status": aoep_source_record["privacy_review_status"],
                "independently_labelled_frames": 0,
                "distances": aoep_distances,
                "players_without_distance": ["Yellow #19", "Sam"],
                "court_map_path": "/api/case-studies/aoep/court-map",
                "source_file": "reviewed_distance_estimate_75180_75229.json",
                "source_file_sha256": sha256(aoep_distance_path),
                "manifest_sha256": sha256(aoep_manifest_path),
            },
        ],
        "formal_tracking_accuracy_claim": False,
        "production_metrics_changed": False,
        "official_annotations_changed": False,
    }
    assert sum(len(row["distances"]) for row in result["case_studies"]) == 8
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print([(row["id"], len(row["distances"])) for row in result["case_studies"]])


if __name__ == "__main__":
    main()
