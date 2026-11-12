"""Diagnose S3 P34 UCLA #7 candidate gaps without changing reviewer verdicts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
VIDEO = ROOT / "data/matches/yt_u5HnY2aNW14/source_720p.mp4"
SOURCE_SHA = "da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b"
MODEL = ROOT / "yolov8n.pt"
RAW = SCREEN / "source_bracketed_30fps_screen.json"
PACK = SCREEN / "s3p34_remaining_rally_review"
OUT_DIR = SCREEN / "s3p34_player7_gap_diagnostic"
OUT = OUT_DIR / "candidate_recovery.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_U5_S3P34_PLAYER7_GAP_DIAGNOSTIC.md"
EARLY = (36015, 36026, 36030, 36031)
LATE = (36124, 36126, 36127, 36128, 36129, 36130, 36131)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo_config"))
from ultralytics import YOLO  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if digest(VIDEO) != SOURCE_SHA:
        raise ValueError("Source video hash changed")
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    point = next(p for p in raw["points"] if p["set"] == 3 and p["point_number"] == 34)
    raw_frames = {r["source_frame"]: r for r in point["rows"]}
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    manifest_frames = {r["source_frame"]: r for r in manifest["frames"]}
    draft = json.loads((PACK / "draft.json").read_text(encoding="utf-8"))["frames"]
    early = []
    for frame in EARLY:
        proposal = next((p for p in raw_frames[frame]["proposals"] if p["raw_track_id"] == 9), None)
        if proposal is None or proposal["net_side_status"] != "net_boundary_review":
            raise ValueError(f"Expected original ID 9 at boundary on {frame}")
        if frame in manifest_frames:
            if manifest_frames[frame]["numbered_boxes"]["7"] is not None:
                raise ValueError(f"Packet already has a #7 candidate at {frame}")
            verdict = next(r for r in draft[str(frame)]["paired"] if r["jersey"] == "7")
            if verdict["candidate_alignment"] != "no_box":
                raise ValueError(f"Saved review changed at {frame}")
        else:
            sampled = json.loads((SCREEN / "s3p34_six_player_observation_ledger.json").read_text(encoding="utf-8"))
            prior = next(r for r in sampled["frames"] if r["source_frame"] == frame)
            if prior["players"]["7"]["jersey_keyed_candidate_court_m"] is not None:
                raise ValueError(f"Sampled ledger already has #7 at {frame}")
        early.append({"source_frame": frame, "raw_track_id": 9,
                      "bbox_px": proposal["bbox_px"],
                      "box_bottom_court_m_staged": proposal["box_bottom_court_m"],
                      "raw_detector_confidence": proposal["confidence"],
                      "reason_not_in_original_jersey_candidate": "net_boundary_review_gate",
                      "review_status": "person_box_exists_but_jersey_and_floor_not_re_adjudicated"})

    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Could not open source video")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    late = []
    tiles = []
    crops = []
    try:
        for frame in LATE:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1:
                raise RuntimeError(f"Could not decode frame {frame}")
            result = model.predict(image, classes=[0], conf=0.05, imgsz=1600, verbose=False)[0]
            proposals = []
            for box, confidence in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist()):
                x1, y1, x2, y2 = map(float, box)
                cx = (x1 + x2) / 2
                # Local search window near the last and next #7 track boxes. This is a
                # proposal filter, not an automatic jersey assignment.
                if not (790 <= cx <= 900 and 185 <= y1 <= 270 and 315 <= y2 <= 420):
                    continue
                proposals.append({"bbox_px": [round(v, 1) for v in (x1, y1, x2, y2)],
                                  "confidence": round(float(confidence), 4)})
            tile = cv2.resize(image, (640, 360))
            for number, proposal in enumerate(proposals, 1):
                x1, y1, x2, y2 = (round(v / 2) for v in proposal["bbox_px"])
                cv2.rectangle(tile, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(tile, f"proposal {number}: {proposal['confidence']:.2f}",
                            (x1, max(17, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.48, (0, 0, 0), 3)
                cv2.putText(tile, f"proposal {number}: {proposal['confidence']:.2f}",
                            (x1, max(17, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.48, (0, 255, 255), 1)
            cv2.putText(tile, str(frame), (12, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.85, (0, 0, 0), 4)
            cv2.putText(tile, str(frame), (12, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.85, (255, 255, 255), 2)
            tiles.append(tile)
            crop = cv2.resize(image[165:435, 760:950], (380, 540))
            for number, proposal in enumerate(proposals, 1):
                x1, y1, x2, y2 = proposal["bbox_px"]
                cv2.rectangle(crop, (round((x1 - 760) * 2), round((y1 - 165) * 2)),
                              (round((x2 - 760) * 2), round((y2 - 165) * 2)), (0, 255, 255), 3)
                cv2.putText(crop, f"P{number} {proposal['confidence']:.2f}",
                            (max(0, round((x1 - 760) * 2)), max(22, round((y1 - 165) * 2) - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                cv2.putText(crop, f"P{number} {proposal['confidence']:.2f}",
                            (max(0, round((x1 - 760) * 2)), max(22, round((y1 - 165) * 2) - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.putText(crop, str(frame), (12, 36), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 0, 0), 4)
            cv2.putText(crop, str(frame), (12, 36), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 255, 255), 2)
            crops.append(crop)
            late.append({"source_frame": frame, "search_region_rule_px":
                         "centre x 790..900, box top y 185..270, bottom y 315..420",
                         "person_proposals": proposals,
                         "review_status": "candidate_only_not_jersey_or_floor_approved"})
    finally:
        cap.release()

    sheet = cv2.vconcat([cv2.hconcat(tiles[:4]),
                         cv2.hconcat(tiles[4:] + [255 * (tiles[0] * 0 + 1)])])
    sheet_path = OUT_DIR / "sideways_7_proposals.jpg"
    if not cv2.imwrite(str(sheet_path), sheet):
        raise RuntimeError("Could not write candidate contact sheet")
    crop_sheet = cv2.vconcat([cv2.hconcat(crops[:4]),
                             cv2.hconcat(crops[4:] + [255 * (crops[0] * 0 + 1)])])
    crop_path = OUT_DIR / "sideways_7_crops.jpg"
    if not cv2.imwrite(str(crop_path), crop_sheet):
        raise RuntimeError("Could not write cropped candidate sheet")
    data = {"status": "diagnostic_recovery_candidates_not_validated_positions",
            "source_sha256": SOURCE_SHA, "raw_screen_sha256": digest(RAW),
            "review_manifest_sha256": digest(PACK / "manifest.json"),
            "model_sha256": digest(MODEL), "method": "original net-boundary audit plus YOLOv8n person prediction conf 0.05 imgsz 1600 on seven late frames",
            "early_original_boxes_excluded_by_gate": early,
            "late_higher_resolution_proposals": late,
            "contact_sheet": str(sheet_path.relative_to(ROOT)).replace("\\", "/"),
            "crop_sheet": str(crop_path.relative_to(ROOT)).replace("\\", "/"),
            "limitation": "Do not substitute proposals for saved human box verdicts or grounded coordinates without new source adjudication."}
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# S3 P34 UCLA #7 candidate-gap diagnosis\n\n"
        "The saved full-packet review currently records UCLA #7 / player 4 as having no selected box "
        "at nine packet frames, and the prior 5-Hz ledger misses two more. This diagnostic preserves those verdicts.\n\n"
        "At **36015, 36026, 36030 and 36031**, the original 960-pixel detector produced raw ID 9 "
        "person boxes, but the near-side box-bottom gate labelled them `net_boundary_review` "
        "and omitted them from the jersey-keyed candidate packet. This is a gate omission, "
        "not a person-detector omission. The staged court depths were 9.002, 9.029, 9.016 "
        "and 9.003 m. These box bottoms cannot be accepted as floor positions merely by changing the gate.\n\n"
        "For the later sideways sequence, a 1600-pixel YOLOv8n pass produced local person "
        "proposals on all **7/7** checked frames 36124 and 36126–36131. These have not "
        "been adjudicated as UCLA #7 or accepted floor positions. "
        f"[Proposal sheet](../{sheet_path.relative_to(ROOT).as_posix()}), "
        f"[larger crops](../{crop_path.relative_to(ROOT).as_posix()}) and "
        f"[machine-readable boxes](../{OUT.relative_to(ROOT).as_posix()}).\n\n"
        "The original 138-frame candidate and source-review records remain unchanged. "
        "A reviewer must compare these suggestions with unboxed frames and adjacent identity "
        "context before any correction is scored.\n",
        encoding="utf-8")
    print(f"Original boundary omissions: {len(early)}; late frames with proposals: {sum(bool(x['person_proposals']) for x in late)}/{len(late)}")


if __name__ == "__main__":
    main()
