"""Prepare a source-linked S3 P34 full-span review queue without certifying it.

The output identifies candidate gaps and creates paired source/box contact sheets.
All detector identity and floor positions remain provisional until visual review.
"""

import hashlib
import csv
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
VIDEO = ROOT / "data/matches/yt_u5HnY2aNW14/source_720p.mp4"
PATHS = SCREEN / "full_rally_candidate_paths.json"
TRACKS = SCREEN / "source_bracketed_30fps_screen.json"
LEDGER = SCREEN / "s3p34_reviewed_sample_ledger.json"
OUT = SCREEN / "s3p34_full_span_review"
JERSEYS = ("28", "12", "15", "7", "19", "21")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(numbers):
    if not numbers:
        return []
    result = []
    start = previous = numbers[0]
    for number in numbers[1:]:
        if number != previous + 1:
            result.append([start, previous])
            start = number
        previous = number
    result.append([start, previous])
    return result


def tile(image, number, caption):
    image = cv2.resize(image, (640, 360))
    cv2.rectangle(image, (0, 0), (640, 34), (0, 0, 0), -1)
    cv2.putText(image, f"{number}  {caption}", (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, .62, (255, 255, 255), 2)
    return image


def main():
    paths = json.loads(PATHS.read_text(encoding="utf-8"))
    tracks = json.loads(TRACKS.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    point = next(p for p in paths["points"]
                 if (p["set"], p["point_number"]) == (3, 34))
    track_point = next(p for p in tracks["points"]
                       if (p["set"], p["point_number"]) == (3, 34))
    first, last = point["interval_inclusive"]
    path_rows = {r["source_frame"]: r for r in point["frames"]}
    track_rows = {r["source_frame"]: r for r in track_point["rows"]}
    sample_rows = {r["source_frame"]: r for r in ledger["frames"]}
    assert set(path_rows) == set(range(first, last + 1))
    assert set(path_rows).issubset(track_rows)
    assert tuple(sample_rows) == tuple(range(36000, 36139, 6))
    missing_by_jersey = {
        jersey: [number for number in range(first, last + 1)
                 if path_rows[number]["court_box_bottom_by_jersey_m"].get(jersey)
                 is None]
        for jersey in JERSEYS
    }
    missing_runs = {jersey: runs(numbers)
                    for jersey, numbers in missing_by_jersey.items()}
    incomplete = [number for number in range(first, last + 1)
                  if any(number in missing_by_jersey[j] for j in JERSEYS)]
    # Include both sides of each gap, every existing reviewed sample, and the
    # known serve/end and ID-transition brackets. This is a review queue only.
    selected = set(sample_rows) | set(range(first, min(first + 13, last + 1)))
    selected |= set(range(max(first, last - 14), last + 1))
    selected |= set(range(36114, 36127))
    for intervals in missing_runs.values():
        for start, end in intervals:
            selected.update(range(max(first, start - 1), min(last, end + 1) + 1))
    selected = sorted(selected)
    render_frames = sorted(set(range(first, last + 1)) | set(selected))

    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened(), VIDEO
    pages = []
    tiles = []
    for number in render_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, source = cap.read()
        assert ok, number
        overlay = source.copy()
        for proposal in track_rows[number]["proposals"]:
            x1, y1, x2, y2 = map(int, proposal["bbox_px"])
            near = proposal["net_side_status"] == "near_floor_side_candidate"
            color = (0, 220, 0) if near else (0, 170, 255)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            cv2.putText(overlay, str(proposal["raw_track_id"]),
                        (x1, max(20, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX,
                        .7, color, 2)
        absent = ",".join(j for j in JERSEYS
                          if number in missing_by_jersey[j]) or "none"
        tiles.append(cv2.hconcat([
            tile(source, number, "source"),
            tile(overlay, number, f"raw IDs; absent jerseys {absent}")]))
        if len(tiles) == 3 or number == render_frames[-1]:
            blank = tiles[0] * 0
            tiles += [blank] * (3 - len(tiles))
            page_path = OUT / f"review_page_{len(pages) + 1:02d}.jpg"
            assert cv2.imwrite(str(page_path), cv2.vconcat(tiles))
            pages.append(page_path.relative_to(ROOT).as_posix())
            tiles = []
    cap.release()

    with (OUT / "frame_player_review_template.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "source_frame", "jersey", "candidate_present", "candidate_x_m",
            "candidate_y_m", "existing_5hz_status", "new_source_review_status",
            "new_source_review_note"])
        writer.writeheader()
        for number in range(first, last + 1):
            for jersey in JERSEYS:
                candidate = path_rows[number]["court_box_bottom_by_jersey_m"].get(jersey)
                old = sample_rows.get(number, {}).get("players", {}).get(jersey, {})
                writer.writerow({
                    "source_frame": number, "jersey": jersey,
                    "candidate_present": candidate is not None,
                    "candidate_x_m": candidate[0] if candidate else "",
                    "candidate_y_m": candidate[1] if candidate else "",
                    "existing_5hz_status": old.get("status", ""),
                    "new_source_review_status": "",
                    "new_source_review_note": "",
                })

    result = {
        "status": "review_queue_not_source_validation",
        "set": 3, "point_number": 34,
        "interval_inclusive": [first, last],
        "input_sha256": {"candidate_paths": sha(PATHS), "dense_screen": sha(TRACKS),
                         "sampled_review": sha(LEDGER)},
        "frames_in_interval": last - first + 1,
        "frames_with_six_candidate_boxes": last - first + 1 - len(incomplete),
        "frames_with_any_missing_candidate": len(incomplete),
        "missing_candidate_frames_by_jersey": {
            jersey: len(numbers) for jersey, numbers in missing_by_jersey.items()},
        "missing_candidate_runs_by_jersey": missing_runs,
        "existing_5hz_reviewed_frames": sorted(sample_rows),
        "existing_5hz_reviewed_frames_outside_candidate_interval": [
            number for number in sample_rows if number < first or number > last],
        "queue_source_frames": selected,
        "queue_frames_outside_candidate_interval": [
            number for number in selected if number < first or number > last],
        "queue_count": len(selected),
        "rendered_source_frames": render_frames,
        "contact_sheets": pages,
        "frame_player_review_template": (
            (OUT / "frame_player_review_template.csv").relative_to(ROOT).as_posix()),
        "required_visual_verdicts": [
            "Confirm jersey identity on source frames, including every candidate gap and ID transition.",
            "For each player and frame, distinguish grounded usable box, airborne, occluded, visible unboxed, and off screen.",
            "Keep unavailable court positions null; any inferred gap path needs a separate validation result.",
            "Resolve or retain serve and point-end brackets without claiming an unseen exact contact."
        ]
    }
    output = OUT / "review_queue.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "frames_in_interval", "frames_with_six_candidate_boxes",
        "frames_with_any_missing_candidate", "missing_candidate_frames_by_jersey",
        "queue_count")}, indent=2))


if __name__ == "__main__":
    main()
