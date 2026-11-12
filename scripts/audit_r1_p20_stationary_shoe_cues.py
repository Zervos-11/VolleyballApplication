"""Flag locally still shoe regions for source contact review, not floor positions."""

from __future__ import annotations

import json
import math

import cv2
import numpy as np

from experiment_r1_seeded_shoe import BASE, SOURCE, sha256


SEGMENT_FILES = (
    "r1_p20_foot_identity_trial.json",
    "r1_p20_local_reseed_trial.json",
    "r1_p20_local_reseed_21402_trial.json",
)
ANCHORS = BASE / "r1_p20_late_contact_anchor_review.json"
OUT = BASE / "r1_p20_stationary_shoe_cue_audit.json"
RADIUS_FRAMES = 2
MAX_RANGE_PX = 4.0
CROP = (580, 735, 900, 850)


def main() -> None:
    segments = [json.loads((BASE / name).read_text(encoding="utf-8"))
                for name in SEGMENT_FILES]
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    source_hash = sha256(SOURCE)
    assert all(segment["source_sha256"] == source_hash for segment in segments)
    assert anchors["source_sha256"] == source_hash
    frames = {}
    for segment in segments:
        for row in segment["frames"]:
            if any(point is not None for point in row["feet"].values()):
                if row["frame"] in frames:
                    raise ValueError("Local segment rows overlap")
                frames[row["frame"]] = row

    cues = {}
    for frame, row in sorted(frames.items()):
        proposals = []
        for label, point in row["feet"].items():
            if point is None:
                continue
            window = [frames.get(i, {}).get("feet", {}).get(label)
                      for i in range(frame - RADIUS_FRAMES, frame + RADIUS_FRAMES + 1)]
            if any(value is None for value in window):
                continue
            span = max(math.dist(a, b) for a in window for b in window)
            if span <= MAX_RANGE_PX:
                proposals.append({"local_foot_label": label,
                                  "shoe_region_px": point,
                                  "five_frame_max_pairwise_motion_px": round(span, 3)})
        cues[frame] = proposals

    audit_rows = []
    for anchor in anchors["frames"]:
        frame = anchor["frame"]
        selected = cues.get(frame, [])
        proposal = anchor["floor_point_proposal_px"]
        nearest = (min(math.dist(proposal, cue["shoe_region_px"]) for cue in selected)
                   if proposal is not None and selected else None)
        audit_rows.append({
            "frame": frame,
            "analyst_source_visual_state": anchor["source_visual_state"],
            "analyst_floor_point_proposal_px": proposal,
            "stationary_shoe_cues": selected,
            "nearest_stationary_cue_to_analyst_point_px": round(nearest, 3) if nearest is not None else None,
        })

    cap = cv2.VideoCapture(str(SOURCE))
    tiles = []
    try:
        for row in audit_rows:
            cap.set(cv2.CAP_PROP_POS_FRAMES, row["frame"])
            okay, frame = cap.read()
            if not okay:
                raise RuntimeError(f"Could not decode frame {row['frame']}")
            x0, y0, x1, y1 = CROP
            tile = cv2.resize(frame[y0:y1, x0:x1], (640, 230))
            for cue in row["stationary_shoe_cues"]:
                x, y = cue["shoe_region_px"]
                cv2.circle(tile, (round((x - x0) * 2), round((y - y0) * 2)),
                           13, (0, 220, 0), 2)
            if row["analyst_floor_point_proposal_px"] is not None:
                x, y = row["analyst_floor_point_proposal_px"]
                cv2.drawMarker(tile, (round((x - x0) * 2), round((y - y0) * 2)),
                               (255, 255, 0), cv2.MARKER_CROSS, 15, 2)
            cv2.putText(tile, str(row["frame"]), (5, 23), cv2.FONT_HERSHEY_SIMPLEX,
                        .65, (255, 255, 255), 2, cv2.LINE_AA)
            tiles.append(tile)
    finally:
        cap.release()
    sheets = []
    blank = np.full_like(tiles[0], 30)
    for start in range(0, len(tiles), 9):
        part = tiles[start:start + 9]
        part += [blank] * (9 - len(part))
        name = f"r1_p20_stationary_shoe_cue_sheet_{start // 9 + 1}.jpg"
        cv2.imwrite(str(BASE / name), cv2.vconcat([
            cv2.hconcat(part[i:i + 3]) for i in (0, 3, 6)]))
        sheets.append(name)
    summary = {
        "source_frames_with_local_shoe_assignment": len(frames),
        "frames_with_stationary_shoe_cue": sum(bool(value) for value in cues.values()),
        "analyst_anchor_frames": len(audit_rows),
        "anchor_frames_with_stationary_shoe_cue": sum(bool(row["stationary_shoe_cues"])
                                                       for row in audit_rows),
        "uncertain_21440_has_stationary_cue": bool(cues.get(21440)),
    }
    result = {
        "status": "development_stationary_shoe_review_cues",
        "source_sha256": source_hash,
        "segment_sha256": {name: sha256(BASE / name) for name in SEGMENT_FILES},
        "contact_anchor_sha256": sha256(ANCHORS),
        "rule": {"radius_frames": RADIUS_FRAMES,
                 "max_pairwise_motion_px": MAX_RANGE_PX,
                 "requires_five_consecutive_assigned_frames": True},
        "frame_cues": {str(frame): value for frame, value in cues.items()},
        "anchor_comparison": audit_rows,
        "sheets": sheets, "summary": summary,
        "limitation": "Low image motion is a review cue only. It can occur during partial occlusion or misassociation and can miss a planted shoe that shifts or rolls. No cue is a verified ground contact, court position, or distance sample.",
        "production_metric_changed": False,
        "official_annotations_changed": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
