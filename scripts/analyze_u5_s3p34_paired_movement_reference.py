"""Compare coarse S3 P34 player-displacement chords with manual shoe marks.

Five selected frames provide four temporal chords per jersey. The result is a
selected reference comparison, not full-rally travel or a confidence interval.
"""

import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "data/matches/yt_u5HnY2aNW14/screening/"
          "full_rally_live_reference_audit.json")
OUT_JSON = (ROOT / "data/matches/yt_u5HnY2aNW14/screening/"
            "s3p34_paired_movement_reference.json")
OUT_MD = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_PAIRED_MOVEMENT_REFERENCE.md"
JERSEYS = ("28", "12", "15", "7", "19", "21")


def r3(number):
    return round(number, 3)


def main():
    raw = SOURCE.read_bytes()
    audit = json.loads(raw)
    assert (audit["set"], audit["point_number"]) == (3, 34)
    frames = {row["source_frame"]: {str(player["jersey"]): player
                                     for player in row["rows"]}
              for row in audit["frames"]}
    frame_numbers = sorted(frames)
    assert frame_numbers == [36036, 36066, 36078, 36096, 36138]
    segments = []
    for jersey in JERSEYS:
        for start, end in zip(frame_numbers, frame_numbers[1:]):
            before, after = frames[start][jersey], frames[end][jersey]
            manual = math.dist(before["manual_court_m"],
                               after["manual_court_m"])
            proxy = math.dist(before["box_bottom_court_m"],
                              after["box_bottom_court_m"])
            segments.append({
                "jersey": jersey, "start_frame": start, "end_frame": end,
                "manual_chord_m": manual, "proxy_chord_m": proxy,
                "proxy_minus_manual_m": proxy - manual,
            })
    by_jersey = []
    for jersey in JERSEYS:
        own = [s for s in segments if s["jersey"] == jersey]
        manual = sum(s["manual_chord_m"] for s in own)
        proxy = sum(s["proxy_chord_m"] for s in own)
        by_jersey.append({"jersey": jersey,
                          "manual_four_chord_sum_m": r3(manual),
                          "proxy_four_chord_sum_m": r3(proxy),
                          "proxy_minus_manual_m": r3(proxy - manual)})
    by_interval = []
    for start, end in zip(frame_numbers, frame_numbers[1:]):
        own = [s for s in segments if
               (s["start_frame"], s["end_frame"]) == (start, end)]
        manual = sum(s["manual_chord_m"] for s in own)
        proxy = sum(s["proxy_chord_m"] for s in own)
        by_interval.append({"start_frame": start, "end_frame": end,
                            "manual_six_player_chord_sum_m": r3(manual),
                            "proxy_six_player_chord_sum_m": r3(proxy),
                            "proxy_minus_manual_m": r3(proxy - manual)})
    manual_total = sum(s["manual_chord_m"] for s in segments)
    proxy_total = sum(s["proxy_chord_m"] for s in segments)
    absolute_errors = [abs(s["proxy_minus_manual_m"]) for s in segments]
    result = {
        "status": "selected_five_frame_single_reviewer_movement_reference_not_full_rally_validation",
        "source_sha256": audit["source_sha256"],
        "manual_audit_sha256": hashlib.sha256(raw).hexdigest(),
        "set": 3, "point_number": 34,
        "frames": frame_numbers,
        "note": "Frames 36066 and 36078 were marked on unboxed source images; 36036, 36096 and 36138 are unblinded supplements. All marks are from one reviewer.",
        "summary": {
            "player_interval_chords": len(segments),
            "manual_chord_sum_m": r3(manual_total),
            "proxy_chord_sum_m": r3(proxy_total),
            "proxy_minus_manual_sum_m": r3(proxy_total - manual_total),
            "median_absolute_player_interval_discrepancy_m": r3(
                statistics.median(absolute_errors)),
            "mean_absolute_player_interval_discrepancy_m": r3(
                statistics.mean(absolute_errors)),
            "maximum_absolute_player_interval_discrepancy_m": r3(
                max(absolute_errors)),
        },
        "by_jersey": by_jersey,
        "by_interval": by_interval,
        "segments": [{key: r3(value) if isinstance(value, float) else value
                      for key, value in segment.items()}
                     for segment in segments],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = result["summary"]
    lines = [
        "# S3 P34 paired coarse movement reference", "",
        "This check compares the same four frame-to-frame straight-line court "
        "chords for each of six UCLA players, using the [five selected manual "
        "shoe-reference frames](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md). "
        "It is a selected **coarse displacement** check, not actual foot travel "
        "or a validated full-rally trajectory. The first compared frame is "
        "36036 and the last is 36138; movement before, after and between these "
        "instants is not measured by the chords.", "",
        "| UCLA jersey | Manual four-chord sum (m) | Proxy four-chord sum (m) | Proxy − manual (m) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for p in by_jersey:
        lines.append(f"| #{p['jersey']} | {p['manual_four_chord_sum_m']:.3f} | "
                     f"{p['proxy_four_chord_sum_m']:.3f} | "
                     f"{p['proxy_minus_manual_m']:+.3f} |")
    lines += [
        f"| **Six-player total** | **{manual_total:.3f}** | "
        f"**{proxy_total:.3f}** | **{proxy_total - manual_total:+.3f}** |",
        "", "Totals are computed before individual-row rounding. Across the "
        f"{len(segments)} player-interval chords, the median absolute paired "
        f"discrepancy is **{statistics.median(absolute_errors):.3f} m**, "
        f"the mean absolute discrepancy is **{statistics.mean(absolute_errors):.3f} m** "
        f"and the maximum is **{max(absolute_errors):.3f} m**. "
        "The small six-player signed difference reflects cancellation; it must "
        "not be used as a ± error bar for an entire rally.",
        "", "| Source-frame interval | Manual six-player chord sum (m) | "
        "Proxy sum (m) | Proxy − manual (m) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in by_interval:
        lines.append(f"| {item['start_frame']}–{item['end_frame']} | "
                     f"{item['manual_six_player_chord_sum_m']:.3f} | "
                     f"{item['proxy_six_player_chord_sum_m']:.3f} | "
                     f"{item['proxy_minus_manual_m']:+.3f} |")
    lines += [
        "", "The reference is approximate and visibility-selected. One reviewer "
        "marked all positions; only frames 36066 and 36078 were marked on "
        "unboxed images before box comparison, while the other three were "
        "unblinded supplements. The analysis cannot estimate an error "
        "distribution for all rally moments, especially jumps and missing boxes. "
        "For the thesis, use these direct paired discrepancies to describe "
        "the *selected coarse movement proxy*, alongside its coverage. Retain "
        "the separate [5 Hz sensitivity check](HONOURS_U5_S3P34_MOVEMENT_SENSITIVITY.md) "
        "to show why a frame-by-frame total and compact ± allowance are not "
        "supported.", "",
        "[Machine-readable calculation](../data/matches/yt_u5HnY2aNW14/screening/s3p34_paired_movement_reference.json). "
        "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s3p34_paired_movement_reference.py`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
