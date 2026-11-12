"""Build the primary match point register from reviewed broadcast score states.

Input states are sampled keyframe scoreboard readings, with digit clusters labeled
from the contact sheets in data/processed. Times bound graphic changes, not play.
"""

import csv
import hashlib
import json
from itertools import groupby
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = "yt_FqE5pTJqx8g"
STATES = ROOT / "data/processed/fqe_score_keyframe_states.json"
CLUSTERS = ROOT / "data/processed/fqe_score_clusters.json"
KEYFRAME_TIMES = ROOT / "data/processed/fqe_keyframe_times.txt"
ANCHORS = ROOT / "data/processed/fqe_score_anchor_review.json"
SOURCE = ROOT / f"data/matches/{MATCH}/source_record.json"
OUT = ROOT / "data/processed/fqe_score_timeline.json"
CSV = ROOT / "data/processed/fqe_score_timeline.csv"

# Rank labels transcribed from fqe_score_top_clusters.jpg and
# fqe_score_bottom_clusters.jpg. Unlisted ranks show no score graphic.
TOP_LABELS = {0: 17, 1: 18, 2: 5, 3: 21, 5: 20, 6: 19, 8: 24,
              9: 13, 10: 4, 11: 9, 12: 23, 13: 8, 14: 16,
              15: 10, 16: 12, 17: 2, 18: 7, 19: 15, 21: 3,
              22: 1, 23: 14, 24: 6, 25: 22, 26: 11, 27: 0,
              29: 25}
BOTTOM_LABELS = {0: 9, 1: 6, 2: 0, 3: 12, 4: 10, 6: 13,
                 7: 3, 9: 4, 10: 17, 11: 7, 12: 2, 13: 8,
                 14: 15, 15: 5, 16: 11, 17: 14, 18: 1,
                 20: 16}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(value):
    return f"{value[0]}-{value[1]}"


def derive_score_states():
    times = [float(line) for line in KEYFRAME_TIMES.read_text().splitlines()]
    clusters = read(CLUSTERS)
    labels = []
    for side, mapping in (("top", TOP_LABELS), ("bottom", BOTTOM_LABELS)):
        values = [None] * len(times)
        for cluster in clusters[side]:
            value = mapping.get(cluster["rank"])
            for index in cluster["members"]:
                assert values[index] is None
                values[index] = value if value is not None else "blank"
        assert all(value is not None for value in values)
        labels.append(values)
    states = []
    for top, bottom in zip(*labels):
        assert (top == "blank") == (bottom == "blank")
        states.append(None if top == "blank" else [top, bottom])
    runs = []
    for index, state in enumerate(states):
        if runs and runs[-1]["state"] == state:
            runs[-1]["last"] = index
        else:
            runs.append({"state": state, "first": index, "last": index})
    return {"times": times, "states": states, "runs": runs}


def main():
    data, anchors, source = read(STATES), read(ANCHORS), read(SOURCE)
    derived = derive_score_states()
    assert data == derived, "Reviewed score states differ from labeled clusters"
    assert anchors["match_id"] == source["match_id"] == MATCH
    assert anchors["source_sha256"] == source["sha256"]
    times, runs = data["times"], data["runs"]
    assert len(times) == len(data["states"]) == 721
    assert runs[0]["first"] == 0 and runs[-1]["last"] == len(times) - 1
    assert all(a["last"] + 1 == b["first"] for a, b in zip(runs, runs[1:]))

    sets = []
    group = []
    for run in runs:
        if run["state"] is None:
            if group:
                sets.append(group)
                group = []
        else:
            group.append(run)
    if group:
        sets.append(group)
    assert len(sets) == 3

    points = []
    corrections = []
    set_summaries = []
    for set_number, group in enumerate(sets, 1):
        first = group[0]
        if set_number == 1:
            assert first["state"] == [1, 0]
            points.append({
                "set": 1, "point_number": 1, "score_before": "0-0",
                "score_after": "1-0", "winner": "ProVolley",
                "evidence": "first_visible_score_only", "graphic_change_after_s": None,
                "graphic_change_by_s": times[first["first"]],
                "rally_boundary_status": "unknown", "pilot_rally_id": None,
            })
        else:
            assert first["state"] == [0, 0]
        previous = first
        for index, run in enumerate(group[1:], 1):
            before, after = previous["state"], run["state"]
            if set_number == 1 and before == [19, 10] and after == [19, 11]:
                assert group[index + 1]["state"] == [19, 10]
                corrections.append({
                    "set": 1, "score_before": "19-10",
                    "temporary_score": "19-11", "restored_score": "19-10",
                    "temporary_visible_from_s": times[run["first"]],
                    "temporary_visible_through_s": times[run["last"]],
                    "restored_at_s": times[group[index + 1]["first"]],
                    "status": "broadcast_score_correction_no_point_counted",
                })
                previous = run
                continue
            if set_number == 1 and before == [19, 11] and after == [19, 10]:
                previous = run
                continue
            delta = [after[0] - before[0], after[1] - before[1]]
            assert delta in ([1, 0], [0, 1]), (set_number, before, after)
            points.append({
                "set": set_number, "point_number": sum(after),
                "score_before": score(before), "score_after": score(after),
                "winner": "ProVolley" if delta == [1, 0] else "UTS",
                "evidence": "broadcast_score_transition",
                "graphic_change_after_s": times[previous["last"]],
                "graphic_change_by_s": times[run["first"]],
                "rally_boundary_status": "unknown", "pilot_rally_id": None,
            })
            previous = run
        last = group[-1]
        if set_number == 1:
            assert last["state"] == [24, 15]
            # The graphic disappears at 24-15. The next set counter is 1-0.
            points.append({
                "set": 1, "point_number": 40, "score_before": "24-15",
                "score_after": "25-15", "winner": "ProVolley",
                "evidence": "inferred_from_next_set_counter_not_visible_score",
                "graphic_change_after_s": None, "graphic_change_by_s": None,
                "rally_boundary_status": "unknown", "pilot_rally_id": None,
            })
            final = [25, 15]
        else:
            final = last["state"]
        set_summaries.append({
            "set": set_number, "final_score": score(final),
            "score_status": "inferred_from_next_set_counter" if set_number == 1 else "visible_on_broadcast",
            "first_score_visible_s": times[first["first"]],
            "last_score_visible_s": times[last["last"]],
            "point_count": len([p for p in points if p["set"] == set_number]),
        })

    for anchor in anchors["rallies"]:
        pilot = anchor["rally_id"]
        # The five anchor frames were visually reviewed; resolve the repeated
        # score pairs by proximity to the after frame, not by score alone.
        target = anchor["after_frame"] / source["camera"]["fps"]
        matches = [p for p in points if p["score_before"] == anchor["before_score"]
                   and p["score_after"] == anchor["after_score"]
                   and p["evidence"] == "broadcast_score_transition"]
        match = min(matches, key=lambda p: abs(p["graphic_change_by_s"] - target))
        assert abs(match["graphic_change_by_s"] - target) <= 12, (pilot, match, target)
        assert match["winner"] == anchor["scoring_team"]
        assert match["pilot_rally_id"] is None
        match["pilot_rally_id"] = pilot
        match["rally_boundary_status"] = "pilot_boundary_review_separate"

    assert [s["point_count"] for s in set_summaries] == [40, 41, 42]
    assert len(points) == 123 and len(corrections) == 1
    assert len([p for p in points if p["pilot_rally_id"]]) == 5
    for summary in set_summaries:
        subset = [p for p in points if p["set"] == summary["set"]]
        assert [p["point_number"] for p in subset] == list(range(1, len(subset) + 1))
        assert subset[-1]["score_after"] == summary["final_score"]
        summary["provolley_points"] = sum(p["winner"] == "ProVolley" for p in subset)
        summary["uts_points"] = sum(p["winner"] == "UTS" for p in subset)
        runs = [(winner, len(list(group))) for winner, group in
                groupby(p["winner"] for p in subset)]
        summary["longest_provolley_point_run"] = max(
            length for winner, length in runs if winner == "ProVolley")
        summary["longest_uts_point_run"] = max(
            length for winner, length in runs if winner == "UTS")
        leads = [int(p["score_after"].split("-")[0]) -
                 int(p["score_after"].split("-")[1]) for p in subset]
        summary["largest_provolley_lead"] = max(leads)
        summary["largest_uts_lead"] = max(0, -min(leads))

    output = {
        "match_id": MATCH, "match_role": "primary_analysis",
        "score_order": "ProVolley-UTS", "source_sha256": source["sha256"],
        "input_score_states_sha256": sha(STATES),
        "input_pilot_anchor_review_sha256": sha(ANCHORS),
        "method": "Manual digit labels on 721 approximately six-second video keyframes; consecutive scoreboard states yield point-score changes. Five pilot transitions also have separately reviewed before/after frames.",
        "timing_note": "Graphic-change windows are sampled broadcast overlay updates. They are not serve, rally start, contact, or rally end times.",
        "set_summaries": set_summaries, "score_corrections": corrections,
        "points": points,
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    with CSV.open("w", newline="", encoding="utf-8") as file:
        fields = list(points[0])
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(points)
    print(f"Wrote {len(points)} points, {len(corrections)} correction, {len(set_summaries)} sets")


if __name__ == "__main__":
    main()
