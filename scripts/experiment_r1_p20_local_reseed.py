"""Test a new, independent #20 two-shoe segment after the first overlap."""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

from experiment_r1_p20_foot_identity import SHOES, assign_candidates
from experiment_r1_seeded_shoe import BASE, SOURCE, sha256


CROP = (580, 735, 900, 850)


def main(seed_frame: int = 21343) -> None:
    tracks = (f"left_region_at_{seed_frame}", f"right_region_at_{seed_frame}")
    stem = "r1_p20_local_reseed" if seed_frame == 21343 else f"r1_p20_local_reseed_{seed_frame}"
    out = BASE / f"{stem}_trial.json"
    trial = json.loads(SHOES.read_text(encoding="utf-8"))
    assert trial["source_sha256"] == sha256(SOURCE)
    sources = [row for row in trial["frames"] if row["frame"] >= seed_frame]
    first = sources[0]
    if first["frame"] != seed_frame or len(first["selected_regions"]) != 2:
        raise ValueError("Expected two separate shoe regions at the source-reviewed local seed")
    points = [region["sole_cue_px"] for region in first["selected_regions"]]
    if not points[0][0] < points[1][0]:
        raise ValueError("Local seed regions are not left-to-right")
    last = {name: {"frame": seed_frame, "point_px": point}
            for name, point in zip(tracks, points)}
    rows = []
    identity_lost_at = None
    for source in sources:
        frame = source["frame"]
        if frame == seed_frame:
            feet = {name: last[name]["point_px"] for name in tracks}
            state = "local_source_seed"
        elif identity_lost_at is not None:
            feet = {name: None for name in tracks}
            state = "identity_unknown_after_local_loss"
        else:
            candidates = [region["sole_cue_px"] for region in source["selected_regions"]]
            feet, state = assign_candidates(candidates, last, frame, tracks)
            if "ambiguous" in state or "too_far" in state:
                identity_lost_at = frame
            for name, point in feet.items():
                if point is not None:
                    last[name] = {"frame": frame, "point_px": point}
        rows.append({"frame": frame, "assignment_state": state,
                     "shoe_region_count": len(source["selected_regions"]),
                     "feet": feet, "ground_contact_px": None,
                     "court_position_m": None})

    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    try:
        # Include the first unresolved frames to show why the local track ends.
        render_end = min(seed_frame + 64, (identity_lost_at or sources[-1]["frame"]) + 3)
        for row in rows:
            if row["frame"] > render_end:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, row["frame"])
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {row['frame']}")
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (640, 230))
            for name, colour in ((tracks[0], (0, 255, 255)),
                                 (tracks[1], (255, 0, 255))):
                point = row["feet"][name]
                if point is not None:
                    cv2.drawMarker(tile, (round((point[0] - x0) * 2),
                                          round((point[1] - y0) * 2)),
                                   colour, cv2.MARKER_CROSS, 14, 2)
            cv2.putText(tile, str(row["frame"]), (5, 23), cv2.FONT_HERSHEY_SIMPLEX,
                        .65, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    sheets = []
    blank = np.full_like(tiles[0], 30)
    for start in range(0, len(tiles), 12):
        part = tiles[start:start + 12]
        part += [blank] * (12 - len(part))
        name = f"{stem}_sheet_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 3]) for i in (0, 3, 6, 9)]))
        sheets.append(name)
    summary = {
        "frames_with_both_assigned": sum(all(point is not None for point in row["feet"].values())
                                         for row in rows),
        "frames_with_one_assigned": sum(sum(point is not None for point in row["feet"].values()) == 1
                                        for row in rows),
        "identity_lost_at_frame": identity_lost_at,
    }
    result = {
        "status": "development_independent_local_shoe_segment",
        "source_sha256": sha256(SOURCE),
        "shoe_trial_sha256": sha256(SHOES),
        "local_seed_frame": seed_frame,
        "local_seed_basis": "Source crop shows two distinct shoes under #20's separate shins",
        "relationship_to_frame_21300_seed_feet": "unknown",
        "frames": rows, "sheets": sheets, "summary": summary,
        "limitation": "The second seed starts new appearance labels. Their anatomical relationship to the early segment is unknown. A candidate region is not a verified planted sole; no distance is calculated.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-frame", type=int, default=21343)
    main(parser.parse_args().seed_frame)
