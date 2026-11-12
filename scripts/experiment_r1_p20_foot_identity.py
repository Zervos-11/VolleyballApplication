"""Assign #20's two shoe-region candidates to seed foot tracks conservatively.

This diagnostic preserves image-region continuity only. Neither identity nor
sole-floor contact is verified, and a hidden foot has no current position.
"""

from __future__ import annotations

import itertools
import json

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, VISUAL, sha256


SHOES = BASE / "r1_p20_body_shoe_contact_trial.json"
OUT = BASE / "r1_p20_foot_identity_trial.json"
TRACKS = ("seed_planted_foot", "seed_raised_foot")
MAX_STEP_PX_PER_FRAME = 35.0
PAIR_AMBIGUITY_MARGIN = 3.0
SINGLE_AMBIGUITY_MARGIN = 4.0
CROP = (580, 735, 900, 850)


def score(last: dict, point: list[float], frame: int) -> float:
    gap = max(1, frame - last["frame"])
    return float(np.linalg.norm(np.subtract(point, last["point_px"]))) / gap


def assign_candidates(candidates: list[list[float]], last: dict, frame: int,
                      tracks: tuple[str, str] = TRACKS) -> tuple[dict, str]:
    """Return explicit per-foot positions or unknowns for this source frame."""
    assigned = {name: None for name in tracks}
    if not candidates:
        return assigned, "no_shoe_regions"
    if len(candidates) == 1:
        ranks = sorted((score(last[name], candidates[0], frame), name) for name in tracks)
        if ranks[0][0] > MAX_STEP_PX_PER_FRAME:
            return assigned, "single_candidate_too_far"
        if ranks[1][0] - ranks[0][0] < SINGLE_AMBIGUITY_MARGIN:
            return assigned, "single_candidate_foot_ambiguous"
        assigned[ranks[0][1]] = candidates[0]
        return assigned, "single_candidate_assigned"
    possibilities = []
    for permutation in itertools.permutations(candidates, 2):
        costs = [score(last[name], point, frame)
                 for name, point in zip(tracks, permutation)]
        if max(costs) <= MAX_STEP_PX_PER_FRAME:
            possibilities.append((sum(costs), permutation))
    if not possibilities:
        return assigned, "pair_too_far"
    possibilities.sort(key=lambda row: row[0])
    if len(possibilities) == 2 and possibilities[1][0] - possibilities[0][0] < PAIR_AMBIGUITY_MARGIN:
        return assigned, "pair_foot_identity_ambiguous"
    assigned.update(zip(tracks, possibilities[0][1]))
    return assigned, "pair_assigned"


def main() -> None:
    shoes = json.loads(SHOES.read_text(encoding="utf-8"))
    assert shoes["source_sha256"] == sha256(SOURCE)
    assert shoes["visual_candidate_sha256"] == sha256(VISUAL)
    first = shoes["frames"][0]
    if first["frame"] != 21300 or len(first["selected_regions"]) != 2:
        raise ValueError("Two visible seed shoes are required")
    last = {name: {"frame": first["frame"], "point_px": region["sole_cue_px"]}
            for name, region in zip(TRACKS, first["selected_regions"])}
    rows = []
    identity_lost_at = None
    for source in shoes["frames"]:
        frame = source["frame"]
        if frame == first["frame"]:
            assigned = {name: last[name]["point_px"] for name in TRACKS}
            state = "source_seed"
        else:
            candidates = [region["sole_cue_px"] for region in source["selected_regions"]]
            if identity_lost_at is not None:
                assigned = {name: None for name in TRACKS}
                state = "identity_unknown_after_overlap"
            else:
                assigned, state = assign_candidates(candidates, last, frame)
                if "ambiguous" in state:
                    identity_lost_at = frame
                for name, point in assigned.items():
                    if point is not None:
                        last[name] = {"frame": frame, "point_px": point}
        rows.append({"frame": frame, "assignment_state": state,
                     "shoe_region_count": len(source["selected_regions"]),
                     "feet": assigned,
                     "body_midpoint_px": None,
                     "ground_contact_px": None,
                     "court_position_m": None})
    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    try:
        for row in rows:
            cap.set(cv2.CAP_PROP_POS_FRAMES, row["frame"])
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {row['frame']}")
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (640, 230))
            for name, colour in ((TRACKS[0], (0, 255, 255)),
                                 (TRACKS[1], (255, 0, 255))):
                point = row["feet"][name]
                if point:
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
        name = f"r1_p20_foot_identity_sheet_{start // 12 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 3]) for i in (0, 3, 6, 9)]))
        sheets.append(name)
    summary = {
        "frames_with_both_assigned": sum(all(point is not None for point in row["feet"].values())
                                         for row in rows),
        "frames_with_one_assigned": sum(sum(point is not None for point in row["feet"].values()) == 1
                                        for row in rows),
        "frames_with_neither_assigned": sum(all(point is None for point in row["feet"].values())
                                            for row in rows),
        "ambiguous_frames": [row["frame"] for row in rows if "ambiguous" in row["assignment_state"]],
        "identity_lost_at_frame": identity_lost_at,
        "assignment_state_counts": {state: sum(row["assignment_state"] == state for row in rows)
                                    for state in sorted({row["assignment_state"] for row in rows})},
    }
    result = {
        "status": "development_two_foot_appearance_identity_trial",
        "source_sha256": sha256(SOURCE),
        "shoe_trial_sha256": sha256(SHOES),
        "seed_frame": first["frame"],
        "seed_meanings": {TRACKS[0]: "planted white shoe at seed",
                          TRACKS[1]: "raised white shoe at seed"},
        "thresholds": {"max_step_px_per_frame": MAX_STEP_PX_PER_FRAME,
                       "pair_ambiguity_margin": PAIR_AMBIGUITY_MARGIN,
                       "single_ambiguity_margin": SINGLE_AMBIGUITY_MARGIN},
        "frames": rows, "sheets": sheets, "summary": summary,
        "limitation": "Assignments are nearest-neighbour appearance hypotheses. Equal white shoes, crossing, and occlusion can switch their identities. An ambiguous overlap permanently ends the seed tracks until a separately verified new seed is available. Missing feet stay null. There is no grounded-state or body-centre path certification.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
