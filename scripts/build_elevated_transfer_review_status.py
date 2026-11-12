"""Summarise source-selected transfer screens without promoting pending reviews."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/source_view_screen"
PACK = BASE / "elevated_transfer_review"
OUTPUT = ROOT / "DELIVERABLES/HONOURS_ELEVATED_TRANSFER_REVIEW_STATUS_2026-11-06.md"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    selection = read(BASE / "transfer_source_only_selection_2026-11-06_v2.json")
    review = {row["match_id"]: row for row in read(PACK / "review_progress_result.json")["cases"]}
    reference = {row["match_id"]: row for row in read(PACK / "position_reference_progress_result.json")["cases"]}
    cuts = {row["match_id"]: row for row in read(BASE / "transfer_selected_source_cut_screen_2026-11-06.json")["cases"]}
    lines = [
        "# Elevated-view transfer review status",
        "",
        "**Protocol frozen:** 6 November 2026. Each point was selected from source time before its detector screen. Updated 7 November 2026. This document is regenerated from saved review files; provisional suggestions are never counted as human checks.",
        "",
        "| Source-selected point | 5-Hz source frames reviewed | Same-player box frames among reviewed | Six plausible grounded proxy frames among reviewed | Court transform | Selected shoe comparison |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for case in selection["cases"]:
        match_id = case["match_id"]
        r = review[match_id]
        p = reference[match_id]
        calibration_path = PACK / f"{match_id}_calibration_draft.json"
        if calibration_path.exists():
            c = read(calibration_path)["check"]
            calibration = c["status"].replace("_", " ")
            errors = c.get("held_out_attack_errors_m", {})
            if errors:
                calibration += (f" (attack checks {errors['attack_left']:.3f}, "
                                f"{errors['attack_right']:.3f} m)")
        else:
            calibration = "pending human landmarks"
        if p["status"] == "pending_inputs":
            comparison = f"pending ({p['reviewed_reference_frames']}/3 frames)"
        elif p["status"] == "court_transform_unavailable":
            comparison = "blocked by unusable court transform"
        else:
            median = p["median_discrepancy_m"]
            comparison = (f"{p['matched_grounded_pairs']}/18 pairs; median {median:.3f} m; "
                          f"maximum {p['largest_observed_discrepancy_m']:.3f} m"
                          if median is not None else "0/18 readable matched pairs")
        label = {"yt_-siJXMXKcbo": "Princeton–Long Beach",
                 "yt__BOwnLLVaPs": "Pepperdine–USC",
                 "yt_b1bJ5WN05Qw": "USC–BYU"}.get(match_id, match_id)
        reviewed = r["reviewed_grid_frames"]
        box_rate = (f"{r['all_six_same_player_box_frames']}/{reviewed}"
                    if reviewed else "pending")
        floor_rate = (f"{r['all_six_plausible_grounded_proxy_frames']}/{reviewed}"
                      if reviewed else "pending")
        lines.append(
            f"| {label} | {r['reviewed_grid_frames']}/{r['expected_grid_frames']} | "
            f"{box_rate} | {floor_rate} | "
            f"{calibration} | {comparison} |"
        )
    byu = review["yt_b1bJ5WN05Qw"]
    byu_counts = byu["slot_counts"]
    byu_reasons = byu["gap_reasons"]
    lines += [
        "",
        "The grid is one frame every 0.2 seconds across a source-bracketed point interval. A reviewed box may remain useful while its player is airborne; its box bottom is then not an accepted floor coordinate. Missing boxes stay null. The selected shoe reference uses one reviewer who had already seen detector previews, so its positional discrepancies are supplementary descriptive checks. A readable grounded manual shoe mark is compared with a same-player box bottom even if that box's floor verdict remains uncertain; this diagnostic comparison does not approve the proxy for strict team metrics. The observed maximum is not a guaranteed error bound.",
        "",
        "## Source and analysis checks",
        "",
    ]
    for case in selection["cases"]:
        match_id = case["match_id"]
        cut = cuts[match_id]
        lines.append(
            f"- `{match_id}`: excerpt SHA-256 `{case['local_excerpt_sha256']}`; "
            f"{cut['adjacent_frame_pairs']} adjacent pairs screened; "
            f"{len(cut['pairs_above_35_gray_levels'])} exceeded the fixed 35/255 mean grayscale-difference flag "
            f"(maximum {cut['maximum_mean_gray_difference']:.3f})."
        )
    lines += [
        "",
        "A zero hard-cut flag is a diagnostic result, not proof of a perfectly fixed camera. The serve and point-end instants are still bracketed; the excerpt frame numbers have not been aligned to a full-video download. Reviewed 5-Hz coverage will not establish continuous 30/60-fps floor trajectories or a point-outcome effect.",
        "",
        "## Interpretation and remaining scope",
        "",
        ("The Pepperdine selected-point transfer review is complete at the stated 5-Hz, single-reviewer scope; Princeton remains partial. "
         f"USC-BYU has {byu['reviewed_grid_frames']} of {byu['expected_grid_frames']} grid frames saved. "
         f"Of its {byu['reviewed_player_slots']} saved player slots, {byu_counts.get('same_player_box', 0)} have accepted same-player boxes, "
         f"{byu_reasons.get('box:uncertain', 0)} retain uncertain box alignment and {byu_reasons.get('box:no_box', 0)} have no box. "
         f"Its reviewed frames include {byu['all_six_same_player_box_frames']} six-box frames. "
         "On 7 November 2026, MZ first confirmed 157 previously uncertain selected BYU boxes as same-player. After completing the grid, MZ confirmed the remaining 52 selected boxes and 205 previously uncertain identity assignments as same-player and sequence-consistent, respectively. These are single-reviewer confirmations of selected candidate assignments; no-box slots and floor verdicts were left unchanged, and revision history preserves the originals. "
         "An AI-assisted source-frame QA correction swapped the P1 and P4 box assignments at frame 918; the prior MZ entry remains in revision history. "
         f"The BYU staged court transform has held-out attack-line discrepancies of {read(PACK / 'yt_b1bJ5WN05Qw_calibration_draft.json')['check']['held_out_attack_errors_m']['attack_left']:.3f} and {read(PACK / 'yt_b1bJ5WN05Qw_calibration_draft.json')['check']['held_out_attack_errors_m']['attack_right']:.3f} m. "
         f"Its selected shoe reference compares {reference['yt_b1bJ5WN05Qw']['matched_grounded_pairs']} grounded marks with same-player box bottoms; {reference['yt_b1bJ5WN05Qw'].get('matched_source_floor_verdicts', {}).get('uncertain', 0)} of those boxes still have an uncertain floor verdict. "
         f"The remaining reference slots include {reference['yt_b1bJ5WN05Qw'].get('exclusions', {}).get('manual_uncertain', 0)} uncertain manual mark and {reference['yt_b1bJ5WN05Qw'].get('exclusions', {}).get('identity_uncertain', 0)} slots without a confirmed candidate identity. "
         "Neither the selected shoe check nor the court-landmark check establishes full-rally floor accuracy. None of these cases supplies a complete continuous six-player rally or an outcome association. Retain all nulls and all reviewed frames."),
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
