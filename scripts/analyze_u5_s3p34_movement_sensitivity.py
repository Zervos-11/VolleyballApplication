"""Describe S3 P34 sampled proxy displacement and conditional point-error bounds.

This does not estimate actual foot travel, impute invisible motion, or provide a
confidence interval. The error radius is a scenario, not a validated bound.
"""

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "data/matches/yt_u5HnY2aNW14/screening/"
          "s3p34_reviewed_sample_ledger.json")
OUT_JSON = (ROOT / "data/matches/yt_u5HnY2aNW14/screening/"
            "s3p34_sampled_movement_sensitivity.json")
OUT_MD = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_MOVEMENT_SENSITIVITY.md"
JERSEYS = ("28", "12", "15", "7", "19", "21")
EPSILON_M = 0.595  # Largest selected S3 P34 manual proxy discrepancy.


def rounded(value):
    return round(value, 3)


def main():
    source_bytes = SOURCE.read_bytes()
    data = json.loads(source_bytes)
    assert data["set"] == 3 and data["point_number"] == 34
    assert data["sample_stride_source_frames"] == 6
    assert len(data["frames"]) == 24
    players = []
    all_links = []
    endpoint_chords = []
    for jersey in JERSEYS:
        accepted = [(row["source_frame"],
                     row["players"][jersey]["accepted_ground_coordinate_m"])
                    for row in data["frames"]
                    if row["players"][jersey]["accepted_ground_coordinate_m"]
                    is not None]
        assert accepted
        links = []
        for (start, xy0), (end, xy1) in zip(accepted, accepted[1:]):
            link = {
                "start_frame": start, "end_frame": end,
                "source_frame_gap": end - start,
                "sampled_chord_m": math.dist(xy0, xy1),
                "crosses_missing_sample": end - start > 6,
            }
            links.append(link)
            all_links.append(link)
        endpoint_chord = math.dist(accepted[0][1], accepted[-1][1])
        endpoint_chords.append(endpoint_chord)
        players.append({
            "jersey": jersey,
            "accepted_samples": len(accepted),
            "first_accepted_frame": accepted[0][0],
            "last_accepted_frame": accepted[-1][0],
            "observed_adjacent_sample_chords_m": rounded(sum(
                link["sampled_chord_m"] for link in links
                if not link["crosses_missing_sample"])),
            "gap_bridge_chords_m": rounded(sum(
                link["sampled_chord_m"] for link in links
                if link["crosses_missing_sample"])),
            "gap_bridge_links": sum(link["crosses_missing_sample"]
                                    for link in links),
            "all_sampled_chords_m": rounded(sum(
                link["sampled_chord_m"] for link in links)),
            "first_to_last_accepted_chord_m": rounded(endpoint_chord),
        })
    observed = sum(link["sampled_chord_m"] for link in all_links)
    adjacent = sum(link["sampled_chord_m"] for link in all_links
                   if not link["crosses_missing_sample"])
    bridges = observed - adjacent
    # Triangle inequality: if each mapped endpoint differs from its true floor
    # point by at most epsilon, each endpoint-to-endpoint chord differs by at
    # most 2*epsilon. This does not bound travel between those endpoints.
    lower = sum(max(0.0, link["sampled_chord_m"] - 2 * EPSILON_M)
                for link in all_links)
    upper = sum(link["sampled_chord_m"] + 2 * EPSILON_M
                for link in all_links)
    endpoint_lower = sum(max(0.0, value - 2 * EPSILON_M)
                         for value in endpoint_chords)
    endpoint_upper = sum(value + 2 * EPSILON_M for value in endpoint_chords)
    result = {
        "status": "exploratory_5hz_proxy_displacement_not_actual_travel",
        "source_sha256": data["source_sha256"],
        "ledger_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "set": 3, "point_number": 34,
        "sample_frames_inclusive": data["sample_interval_inclusive"],
        "sample_stride_source_frames": 6,
        "scenario_per_position_error_radius_m": EPSILON_M,
        "scenario_basis": ("largest observed selected S3 P34 manual-position "
                           "discrepancy; not a guaranteed error bound"),
        "players": players,
        "summary": {
            "accepted_player_samples": sum(p["accepted_samples"] for p in players),
            "sampled_chord_links": len(all_links),
            "adjacent_sample_links": sum(
                not link["crosses_missing_sample"] for link in all_links),
            "gap_bridge_links": sum(
                link["crosses_missing_sample"] for link in all_links),
            "adjacent_sample_proxy_chords_m": rounded(adjacent),
            "gap_bridge_chords_m": rounded(bridges),
            "all_sampled_proxy_chords_m": rounded(observed),
            "sum_first_to_last_accepted_chords_m": rounded(sum(endpoint_chords)),
            "conditional_discrete_chord_sum_range_m": [rounded(lower),
                                                        rounded(upper)],
            "conditional_endpoint_chord_sum_range_m": [
                rounded(endpoint_lower), rounded(endpoint_upper)],
            "largest_single_sampled_chord_m": rounded(max(
                link["sampled_chord_m"] for link in all_links)),
        },
        "interpretation": ("The displayed chord sums describe the sampled "
                           "court-position proxies. A bridge chord connects "
                           "the nearest accepted positions on opposite sides "
                           "of missing samples, without observing the path "
                           "inside the gap. The conditional ranges apply "
                           "only to sums of discrete chords if every position "
                           "error is no greater than the chosen radius. "
                           "They do not bound physical distance travelled "
                           "between samples or over uncovered rally endpoints."),
    }
    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# S3 P34 sampled movement and uncertainty check", "",
        "This calculation uses only the 24 source-reviewed 5 Hz frames in the "
        "[grounded-position ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reviewed_sample_ledger.json). "
        "A point is used only when its jersey has an accepted grounded box-bottom "
        "proxy. It is an exploratory court-coordinate **proxy displacement**, not "
        "total physical player travel or a validated full-rally movement result.",
        "", "| UCLA jersey | Accepted samples | Adjacent chords (m) | "
        "Bridges across missing samples (m) | First-to-last accepted chord (m) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for p in players:
        lines.append(f"| #{p['jersey']} | {p['accepted_samples']} | "
                     f"{p['observed_adjacent_sample_chords_m']:.3f} | "
                     f"{p['gap_bridge_chords_m']:.3f} | "
                     f"{p['first_to_last_accepted_chord_m']:.3f} |")
    lines += [
        f"| **Six-player sum** | **{result['summary']['accepted_player_samples']}** "
        f"| **{result['summary']['adjacent_sample_proxy_chords_m']:.3f}** "
        f"| **{result['summary']['gap_bridge_chords_m']:.3f}** "
        f"| **{result['summary']['sum_first_to_last_accepted_chords_m']:.3f}** |",
        "",
        "Team sums are calculated before rounding individual rows.",
        "",
        f"The adjacent and bridge columns sum to **{observed:.3f} m** across "
        f"{len(all_links)} accepted-position links. Six links bridge one or more "
        "unobserved 5 Hz samples. UCLA #12's first accepted position is frame "
        "36030, after the initial serve/landing uncertainty; its earlier movement "
        "is absent from this calculation. Movement between any two samples can "
        "exceed their straight-line chord.",
        "", "## What a ± allowance would mean", "",
        "For two measured court points with assumed errors of at most "
        "\(\\epsilon\) metres each, the error in their straight-line chord "
        "is at most \(2\\epsilon\). Taking "
        f"\(\\epsilon={EPSILON_M:.3f}\) m—the largest "
        "*observed* selected S3 P34 shoe-to-box discrepancy—as an illustrative "
        f"per-point radius gives a conditional **{lower:.3f}–{upper:.3f} m** range for the "
        f"sum of the {len(all_links)} discrete sampled chords. The largest measured single "
        f"chord is only {max(link['sampled_chord_m'] for link in all_links):.3f} m, "
        f"smaller than the conditional {2 * EPSILON_M:.3f} m error "
        "allowance for one chord. This bound is broad because errors can occur "
        f"at every sampled point; {EPSILON_M:.3f} m is not a proven maximum error.",
        "",
        f"The six first-to-last accepted chords sum to **{sum(endpoint_chords):.3f} m**; under the "
        "same stipulated per-point radius, their conditional sum range is "
        f"**{endpoint_lower:.3f}–{endpoint_upper:.3f} m**. This describes net displacement between each "
        "player's first and last accepted sample, with different coverage "
        "for #12. It is not the distance travelled during the rally.",
        "",
        "Neither range includes extra travel between samples, movement before "
        "or after accepted endpoints, an incorrect identity, or calibration "
        "error beyond the assumed point radius. Without a separately justified "
        "motion limit, the video does not provide a finite upper bound on actual "
        "travel through unseen intervals. A neat claim such as '29 m ± 1 m' "
        "would therefore overstate the evidence. The defensible presentation "
        "is the measured sampled proxy sum, the explicit missingness and "
        "conditional sensitivity, with actual total movement left unestimated.",
        "",
        "[Machine-readable calculation](../data/matches/yt_u5HnY2aNW14/screening/s3p34_sampled_movement_sensitivity.json). "
        "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s3p34_movement_sensitivity.py`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
