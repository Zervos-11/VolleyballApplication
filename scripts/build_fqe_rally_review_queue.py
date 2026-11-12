"""Make source-video seek windows for reviewing main-match rally boundaries."""

import csv
import json
from statistics import median
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = "yt_FqE5pTJqx8g"
SCORES = ROOT / "data/processed/fqe_score_timeline.json"
FLIPS = ROOT / "data/processed/fqe_score_flip_frames.json"
BOUNDARIES = ROOT / f"data/matches/{MATCH}/pilot/boundary_review.json"
OUT_JSON = ROOT / "data/processed/fqe_rally_review_queue.json"
OUT_CSV = ROOT / "data/processed/fqe_rally_review_queue.csv"


def main():
    timeline = json.loads(SCORES.read_text(encoding="utf-8"))
    flips = json.loads(FLIPS.read_text(encoding="utf-8"))
    pilots = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    assert timeline["match_id"] == MATCH
    assert flips["match_id"] == MATCH
    assert flips["source_sha256"] == timeline["source_sha256"]
    flip_by_point = {(r["set"], r["point_number"]): r for r in flips["changes"]}
    assert len(flip_by_point) == 121
    pilot_points = [p for p in timeline["points"] if p["pilot_rally_id"]]
    estimated_duration = round(median(
        pilots[p["pilot_rally_id"]]["end_frame_exclusive"] -
        pilots[p["pilot_rally_id"]]["start_frame"] for p in pilot_points))
    graphic_lag_by_set = {
        set_number: round(median(
            flip_by_point[(p["set"], p["point_number"])]["first_new_digit_frame"] -
            pilots[p["pilot_rally_id"]]["end_frame_exclusive"]
            for p in pilot_points if p["set"] == set_number))
        for set_number in (1, 2, 3)
    }
    assert estimated_duration == 510 and graphic_lag_by_set == {1: 106, 2: 119, 3: 148}
    pilot_flip_lags = [
        flip_by_point[(p["set"], p["point_number"])]["first_new_digit_frame"] -
        pilots[p["pilot_rally_id"]]["end_frame_exclusive"] for p in pilot_points
    ]
    assert min(pilot_flip_lags) == 93 and max(pilot_flip_lags) == 171
    rows = []
    previous_update = {1: 0.0, 2: 1542.0, 3: 2964.0}
    for point in timeline["points"]:
        set_number = point["set"]
        start = previous_update[set_number]
        end = point["graphic_change_by_s"]
        if end is None:
            assert set_number == 1 and point["score_after"] == "25-15"
            end = 1344.0  # first keyframe with no set-one score graphic
        assert start < end
        seek_from_frame = int(round(start * 50))
        seek_to_frame = int(round(end * 50))
        flip = flip_by_point.get((set_number, point["point_number"]))
        if point["evidence"] == "broadcast_score_transition":
            assert flip and flip["score_after"] == point["score_after"]
            estimate_end = max(seek_from_frame + 1,
                               flip["first_new_digit_frame"] - graphic_lag_by_set[set_number])
        else:
            assert flip is None
            estimate_end = max(seek_from_frame + 1,
                               seek_to_frame - graphic_lag_by_set[set_number])
        estimate_start = max(seek_from_frame, estimate_end - estimated_duration)
        if point["evidence"] == "first_visible_score_only":
            # The graphic is absent before 1-0, so the usual lag estimate
            # cannot be anchored to a preceding visible score.
            estimate_end = max(0, seek_to_frame - 100)
            estimate_start = max(0, estimate_end - estimated_duration)
        elif point["evidence"] == "inferred_from_next_set_counter_not_visible_score":
            # The set-one graphic disappears after the point; there is no
            # visible 25-15 score-change time to subtract a normal lag from.
            estimate_end = max(seek_from_frame + 1, seek_to_frame - 100)
            estimate_start = max(seek_from_frame, estimate_end - estimated_duration)
        row = {
            "set": set_number, "point_number": point["point_number"],
            "score_before": point["score_before"],
            "score_after": point["score_after"], "winner": point["winner"],
            "seek_from_s": start, "seek_to_s": end,
            "seek_from_frame": seek_from_frame,
            "seek_to_frame_exclusive": seek_to_frame,
            "estimated_start_frame": estimate_start,
            "estimated_end_frame_exclusive": estimate_end,
            "estimate_status": "rough_score_timing_estimate_check_source",
            "estimate_graphic_lag_frames": graphic_lag_by_set[set_number],
            "score_flip_frame": flip["first_new_digit_frame"] if flip else None,
            "end_review_from_frame": max(0, flip["first_new_digit_frame"] - max(pilot_flip_lags) - 50) if flip else None,
            "end_review_to_frame": flip["first_new_digit_frame"] - min(pilot_flip_lags) + 50 if flip else None,
            "score_evidence": point["evidence"],
            "pilot_rally_id": point["pilot_rally_id"],
            "boundary_status": "needs_source_review",
            "serve_contact_frame": None, "end_frame_exclusive": None,
        }
        if point["pilot_rally_id"]:
            pilot = pilots[point["pilot_rally_id"]]
            assert pilot["boundary_status"] == "checked_by_annotator"
            row.update(boundary_status="pilot_annotator_checked",
                       serve_contact_frame=pilot["start_frame"],
                       end_frame_exclusive=pilot["end_frame_exclusive"],
                       estimated_start_frame=None,
                       estimated_end_frame_exclusive=None,
                       estimate_status="not_applicable_saved_pilot_boundary",
                       estimate_graphic_lag_frames=None)
            # Score updates can lag the first dead ball; pilot intervals must
            # nevertheless be near the associated score-review window.
            assert row["seek_from_frame"] - 250 <= pilot["start_frame"]
            assert pilot["end_frame_exclusive"] <= row["seek_to_frame_exclusive"] + 250
        rows.append(row)
        previous_update[set_number] = end

    assert len(rows) == 123
    assert sum(row["boundary_status"] == "pilot_annotator_checked" for row in rows) == 5
    output = {
        "match_id": MATCH, "source_sha256": timeline["source_sha256"],
        "window_meaning": "Heuristic video seek interval from previous visible score update to current score update. It is a review aid, not a proven enclosing rally interval or rally duration.",
        "estimate_method": "For ordinary points, locate the new score digit frame within the six-second sampled interval and subtract the median exact-flip lag from checked pilot boundaries in the same set (set 1: 106 frames from one pilot; set 2: 119 frames from two; set 3: 148 frames from two). Estimate start by subtracting the median pilot rally duration (510 frames), clamped to the seek window. Opening and inferred set-one final points use separate rough offsets. All estimates require source review.",
        "end_review_range_method": "For visible score changes, show a source-review range from the earliest to latest end implied by the five pilot score-flip lags (93-171 frames), padded by 50 frames on each side. This is a search aid, not an accepted point-end interval.",
        "boundary_rule": "Serve contact and first frame after point-ending action must be checked in source footage; the score graphic alone cannot label either boundary.",
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} seek windows: 5 pilot boundaries, 118 source reviews pending")


if __name__ == "__main__":
    main()
