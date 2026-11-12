"""Compare short chord motion from matched manual and box-bottom positions.

The frames are a selected, single-reviewer diagnostic segment. Discrete chords
are not observed foot travel and this script does not grant strict approval.
"""

import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review"
INPUT = PACK / "single_reviewer_position_comparison.json"
OUT = PACK / "single_reviewer_path_consistency.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_30FPS_PATH_CONSISTENCY.md"
SLOTS = ("28", "12", "15", "7", "19", "21")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    assert data["status"] == "single_reviewer_diagnostic_position_comparison"
    assert data["summary"]["reviewed_frames"] == 30
    frames = data["frames"]
    numbers = [row["source_frame"] for row in frames]
    assert numbers == sorted(numbers) and len(set(numbers)) == 30
    assert numbers[0] == 36067 and numbers[-1] == 36101
    by_slot = {slot: [] for slot in SLOTS}
    for frame in frames:
        assert [p["stored_slot"] for p in frame["players"]] == list(SLOTS)
        for player in frame["players"]:
            by_slot[player["stored_slot"]].append({
                "frame": frame["source_frame"],
                "manual": tuple(player["manual_court_m"]),
                "proxy": tuple(player["proxy_court_m"]),
            })
    chords = []
    player_sums = []
    manual_grand_total = proxy_grand_total = 0.0
    for slot in SLOTS:
        path = by_slot[slot]
        manual_total = proxy_total = 0.0
        for first, second in zip(path, path[1:]):
            span = second["frame"] - first["frame"]
            assert span in (1, 2)
            manual = math.dist(first["manual"], second["manual"])
            proxy = math.dist(first["proxy"], second["proxy"])
            manual_total += manual
            proxy_total += proxy
            chords.append({
                "stored_slot": slot, "first_frame": first["frame"],
                "second_frame": second["frame"], "source_frame_gap": span,
                "manual_chord_m": round(manual, 4), "proxy_chord_m": round(proxy, 4),
                "proxy_minus_manual_m": round(proxy - manual, 4),
                "absolute_chord_difference_m": round(abs(proxy - manual), 4),
            })
        player_sums.append({"stored_slot": slot,
                            "manual_chord_sum_m": round(manual_total, 3),
                            "proxy_chord_sum_m": round(proxy_total, 3),
                            "proxy_minus_manual_m": round(proxy_total - manual_total, 3)})
        manual_grand_total += manual_total
        proxy_grand_total += proxy_total
    assert len(chords) == 174
    absolute = [x["absolute_chord_difference_m"] for x in chords]
    signed = [x["proxy_minus_manual_m"] for x in chords]
    gap_summary = {str(gap): {
        "chords": sum(x["source_frame_gap"] == gap for x in chords),
        "median_manual_chord_m": round(statistics.median(
            x["manual_chord_m"] for x in chords if x["source_frame_gap"] == gap), 3),
        "median_proxy_chord_m": round(statistics.median(
            x["proxy_chord_m"] for x in chords if x["source_frame_gap"] == gap), 3),
    } for gap in (1, 2)}
    result = {
        "status": "single_reviewer_diagnostic_chord_comparison",
        "input_sha256": sha(INPUT),
        "source_frame_span": [numbers[0], numbers[-1]],
        "marked_frames": len(numbers),
        "player_interval_chords": len(chords),
        "source_frame_gap_counts": {str(gap): sum(x["source_frame_gap"] == gap for x in chords)
                                    for gap in (1, 2)},
        "source_frame_gap_summary": gap_summary,
        "manual_chord_sum_m": round(manual_grand_total, 3),
        "proxy_chord_sum_m": round(proxy_grand_total, 3),
        "signed_sum_difference_m": round(proxy_grand_total - manual_grand_total, 3),
        "median_manual_chord_m": round(statistics.median(x["manual_chord_m"] for x in chords), 3),
        "median_proxy_chord_m": round(statistics.median(x["proxy_chord_m"] for x in chords), 3),
        "median_absolute_chord_difference_m": round(statistics.median(absolute), 3),
        "maximum_absolute_chord_difference_m": round(max(absolute), 3),
        "median_signed_chord_difference_m": round(statistics.median(signed), 3),
        "per_player": player_sums,
        "chords": chords,
        "strict_metric_approval": False,
        "interpretation": "The two paths use the same 30 manually marked instants and the same staged court transform. Their 174 chords are correlated within six players and one selected interval; sums are not measured foot travel, and signed differences can cancel.",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    largest = max(chords, key=lambda row: row["absolute_chord_difference_m"])
    lines = [
        "# S3 P34 30-fps diagnostic path consistency", "",
        "The [completed position comparison](HONOURS_U5_S3P34_30FPS_POSITION_COMPARISON.md) "
        "provides 30 clicked shoe midpoints per player slot in the selected 36066–36102 segment. "
        "For each of six slots, this audit compares the manual and box-bottom straight-line chords "
        "between the same successive marked frames. The seven earlier sampled frames are not "
        "inserted into either path, so no position is imputed.", "",
        f"There are **{result['player_interval_chords']} matched player-interval chords**: "
        f"{result['source_frame_gap_counts']['1']} span one source frame and "
        f"{result['source_frame_gap_counts']['2']} span two. "
        f"The manual chord sum is **{result['manual_chord_sum_m']:.3f} m** and the proxy sum "
        f"is **{result['proxy_chord_sum_m']:.3f} m**, a signed difference of "
        f"**{result['signed_sum_difference_m']:+.3f} m**. The median absolute paired "
        f"chord difference is **{result['median_absolute_chord_difference_m']:.3f} m** "
        f"and the largest is **{result['maximum_absolute_chord_difference_m']:.3f} m**. "
        f"Median individual chords are {result['median_manual_chord_m']:.3f} m for manual marks "
        f"and {result['median_proxy_chord_m']:.3f} m for box bottoms.", "",
        f"For one-frame gaps, the median manual and proxy chords are "
        f"{gap_summary['1']['median_manual_chord_m']:.3f} and "
        f"{gap_summary['1']['median_proxy_chord_m']:.3f} m; for two-frame gaps they are "
        f"{gap_summary['2']['median_manual_chord_m']:.3f} and "
        f"{gap_summary['2']['median_proxy_chord_m']:.3f} m. The manual median changes little "
        "with the longer gap, which is compatible with shoe stance or clicking variation "
        "contributing to the manual sum. This comparison cannot determine how much of the "
        "sum difference is true missed movement.", "",
        f"The largest disagreement is stored slot {largest['stored_slot']} between frames "
        f"{largest['first_frame']} and {largest['second_frame']}: its clicked midpoint chord is "
        f"{largest['manual_chord_m']:.3f} m while its box-bottom chord is "
        f"{largest['proxy_chord_m']:.3f} m. The two source frames show the player near the net "
        "with little change in shoe-midpoint location; this pattern is consistent with a changing "
        "detector box bottom, although annotation uncertainty also matters.", "",
        "| Stored slot | Manual chord sum (m) | Proxy chord sum (m) | Proxy − manual (m) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in player_sums:
        lines.append(f"| {row['stored_slot']} | {row['manual_chord_sum_m']:.3f} | "
                     f"{row['proxy_chord_sum_m']:.3f} | {row['proxy_minus_manual_m']:+.3f} |")
    lines += ["",
              "These sums describe displacement of two point proxies at the sampled instants. "
              "They are not foot travel, step counts, or speed. A shoe midpoint can move with stance "
              "even when the player's court position changes little. The existing 12–15-pixel "
              "per-axis reading uncertainty is substantial relative to these one-frame chords, "
              "so summing them may amplify manual-click jitter. Signed differences may cancel, "
              "and all chords come from one previously tracker-exposed reviewer and one availability-selected "
              "segment under a staged court transform. The "
              "[machine-readable audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_path_consistency.json) "
              "retains every paired chord; strict metric approval remains false.", "",
              "Reproduce with `.\\.venv\\Scripts\\python.exe scripts/analyze_u5_s3p34_30fps_path_consistency.py`."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "player_interval_chords", "manual_chord_sum_m", "proxy_chord_sum_m",
        "signed_sum_difference_m", "median_absolute_chord_difference_m",
        "maximum_absolute_chord_difference_m")}, indent=2))


if __name__ == "__main__":
    main()
