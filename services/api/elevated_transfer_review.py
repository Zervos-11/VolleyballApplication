"""Local review UI for source-selected elevated volleyball points."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/processed/source_view_screen"
PACK = BASE / "elevated_transfer_review"
SELECTION = BASE / "transfer_source_only_selection_2026-11-06_v2.json"
LOCK = threading.Lock()
app = FastAPI(title="Elevated volleyball transfer review")
CALIBRATION_FRAME = {"yt_-siJXMXKcbo": 840, "yt__BOwnLLVaPs": 240,
                     "yt_b1bJ5WN05Qw": 600}
COURT_LANDMARKS = ("net_left", "net_right", "baseline_left", "baseline_right",
                   "attack_left", "attack_right")
REFERENCE_PLAN = PACK / "position_reference_plan_2026-11-06_v2.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=3)
def case_data(match_id: str) -> tuple[dict, dict]:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    case = next((c for c in selection["cases"] if c["match_id"] == match_id), None)
    if case is None:
        raise HTTPException(404, "Unknown match")
    suggestion_path = PACK / f"{match_id}_suggestions.json"
    suggestions = json.loads(suggestion_path.read_text(encoding="utf-8"))
    source = ROOT / case["local_excerpt"]
    if sha256(source) != case["local_excerpt_sha256"]:
        raise HTTPException(409, "Source excerpt hash changed")
    return case, suggestions


def draft_path(match_id: str) -> Path:
    case_data(match_id)
    return PACK / f"{match_id}_review_draft.json"


def read_draft(match_id: str) -> dict:
    path = draft_path(match_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"revision": 0, "scope": "single_reviewer_unblinded_5hz_transfer",
            "frames": {}, "status": "in_progress"}


class PlayerRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot: int = Field(ge=1, le=6)
    identity_status: Literal["digit_confirmed", "sequence_consistent", "uncertain", "not_visible"]
    physical_state: Literal["grounded", "airborne", "feet_occluded", "uncertain", "not_visible"]
    candidate_raw_track_id: int | None = None
    box_alignment: Literal["same_player", "no_box", "uncertain"]
    floor_alignment: Literal["plausible", "implausible", "not_applicable", "uncertain"]
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def consistent(self):
        if self.candidate_raw_track_id is None and self.box_alignment == "same_player":
            raise ValueError("A same-player decision needs a selected box")
        if self.candidate_raw_track_id is not None and self.box_alignment == "no_box":
            raise ValueError("A no-box decision cannot have a selected box")
        if self.physical_state != "grounded" and self.floor_alignment == "plausible":
            raise ValueError("Only a grounded player can have a plausible floor proxy")
        if self.box_alignment != "same_player" and self.floor_alignment == "plausible":
            raise ValueError("A plausible floor proxy needs a matched box")
        return self


class FrameSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    reviewer_code: str = Field(min_length=1, max_length=80)
    checked_all_six_in_source: Literal[True]
    rows: list[PlayerRow] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def six_slots(self):
        if sorted(row.slot for row in self.rows) != list(range(1, 7)):
            raise ValueError("Save must contain each of the six slots exactly once")
        selected = [row.candidate_raw_track_id for row in self.rows
                    if row.candidate_raw_track_id is not None and row.box_alignment == "same_player"]
        if len(selected) != len(set(selected)):
            raise ValueError("One detector box cannot match two slots")
        return self


@app.get("/")
def page():
    return FileResponse(ROOT / "web/elevated_transfer_review.html")


@app.get("/elevated_transfer_review.js")
def javascript():
    return FileResponse(ROOT / "web/elevated_transfer_review.js", media_type="text/javascript")


@app.get("/calibration")
def calibration_page():
    return FileResponse(ROOT / "web/elevated_transfer_calibration.html")


@app.get("/elevated_transfer_calibration.js")
def calibration_javascript():
    return FileResponse(ROOT / "web/elevated_transfer_calibration.js", media_type="text/javascript")


@app.get("/position-reference")
def position_reference_page():
    return FileResponse(ROOT / "web/elevated_transfer_position_reference.html")


@app.get("/elevated_transfer_position_reference.js")
def position_reference_javascript():
    return FileResponse(ROOT / "web/elevated_transfer_position_reference.js",
                        media_type="text/javascript")


@app.get("/api/cases")
def cases():
    selected = json.loads(SELECTION.read_text(encoding="utf-8"))
    return [{"match_id": case["match_id"], "name": case["near_side_team_source_read"],
             "source_url": case["source_url"]} for case in selected["cases"]]


@app.get("/api/cases/{match_id}")
def case(match_id: str):
    source_case, suggestions = case_data(match_id)
    draft = read_draft(match_id)
    return {"case": source_case, "suggestions": suggestions,
            "draft": draft, "source_sha256": source_case["local_excerpt_sha256"]}


@app.get("/api/cases/{match_id}/frame/{frame}/image")
def frame_image(match_id: str, frame: int):
    source_case, suggestions = case_data(match_id)
    allowed = {row["excerpt_frame"] for row in suggestions["rows"]}
    if frame not in allowed:
        raise HTTPException(404, "Frame outside selected grid")
    return source_image(source_case, frame)


def source_image(source_case: dict, frame: int):
    cap = cv2.VideoCapture(str(ROOT / source_case["local_excerpt"]))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = cap.read()
        if not ok:
            raise HTTPException(500, "Cannot decode source frame")
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise HTTPException(500, "Cannot encode source frame")
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    finally:
        cap.release()


@app.get("/api/cases/{match_id}/calibration/image")
def calibration_image(match_id: str):
    source_case, _ = case_data(match_id)
    return source_image(source_case, CALIBRATION_FRAME[match_id])


def calibration_path(match_id: str) -> Path:
    case_data(match_id)
    return PACK / f"{match_id}_calibration_draft.json"


def read_calibration(match_id: str) -> dict:
    path = calibration_path(match_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"revision": 0, "reviewer_code": None, "landmarks": {},
            "status": "not_reviewed"}


class Landmark(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Literal["net_left", "net_right", "baseline_left", "baseline_right",
                  "attack_left", "attack_right"]
    x_px: float | None = None
    y_px: float | None = None
    status: Literal["clicked", "unreadable"]
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def point_consistency(self):
        if self.status == "clicked" and (self.x_px is None or self.y_px is None):
            raise ValueError("Clicked landmark needs x and y")
        if self.status == "unreadable" and (self.x_px is not None or self.y_px is not None):
            raise ValueError("Unreadable landmark must have null coordinates")
        return self


class CalibrationSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    reviewer_code: str = Field(min_length=1, max_length=80)
    checked_unboxed_source: Literal[True]
    landmarks: list[Landmark] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def six_landmarks(self):
        if set(row.code for row in self.landmarks) != set(COURT_LANDMARKS):
            raise ValueError("All six court landmarks must be present")
        return self


def calibration_check(points: dict) -> dict:
    source_codes = ("net_left", "net_right", "baseline_left", "baseline_right")
    if any(points[code]["status"] != "clicked" for code in source_codes):
        return {"status": "four_corners_unavailable", "homography_image_to_court": None,
                "held_out_attack_errors_m": None}
    image = np.float32([[points[code]["x_px"], points[code]["y_px"]]
                        for code in source_codes])
    court = np.float32([[0, 0], [9, 0], [0, 9], [9, 9]])
    h = cv2.getPerspectiveTransform(image, court)
    if abs(float(np.linalg.det(h))) < 1e-12:
        return {"status": "singular_transform", "homography_image_to_court": None,
                "held_out_attack_errors_m": None}
    errors = {}
    for code, expected in (("attack_left", (0, 3)), ("attack_right", (9, 3))):
        if points[code]["status"] != "clicked":
            errors[code] = None
            continue
        xy = np.array([points[code]["x_px"], points[code]["y_px"], 1.0])
        mapped = h @ xy
        mapped = mapped[:2] / mapped[2]
        errors[code] = round(float(np.linalg.norm(mapped - np.array(expected))), 4)
    return {"status": "staged_four_corner_transform", "homography_image_to_court": h.tolist(),
            "held_out_attack_errors_m": errors,
            "note": "Held-out line error checks selected image landmarks; it is not player-position accuracy."}


@app.get("/api/cases/{match_id}/calibration")
def get_calibration(match_id: str):
    source_case, _ = case_data(match_id)
    return {"match_id": match_id, "source_sha256": source_case["local_excerpt_sha256"],
            "source_frame": CALIBRATION_FRAME[match_id],
            "landmark_codes": COURT_LANDMARKS, "draft": read_calibration(match_id)}


@app.put("/api/cases/{match_id}/calibration")
def save_calibration(match_id: str, payload: CalibrationSave):
    case_data(match_id)
    with LOCK:
        draft = read_calibration(match_id)
        if payload.expected_revision != draft["revision"]:
            raise HTTPException(409, "Calibration changed; reload before saving")
        points = {row.code: row.model_dump() for row in payload.landmarks}
        result = calibration_check(points)
        revision = draft["revision"] + 1
        new = {"revision": revision, "reviewer_code": payload.reviewer_code,
               "checked_unboxed_source": True, "source_frame": CALIBRATION_FRAME[match_id],
               "source_boxes_visible_during_review": False,
               "landmarks": points, "check": result,
               "status": "source_reviewed_staged_calibration"}
        history = PACK / "history" / match_id
        history.mkdir(parents=True, exist_ok=True)
        (history / f"calibration_{revision:05d}_{uuid.uuid4().hex}.json").write_text(
            json.dumps({"prior": draft, "new": new}, indent=2) + "\n", encoding="utf-8")
        path = calibration_path(match_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return {"draft": new}


def reference_frames(match_id: str) -> list[int]:
    case_data(match_id)
    plan = json.loads(REFERENCE_PLAN.read_text(encoding="utf-8"))
    case = next((c for c in plan["cases"] if c["match_id"] == match_id), None)
    if case is None:
        raise HTTPException(404, "No reference plan for match")
    return case["reference_excerpt_frames"]


def reference_path(match_id: str) -> Path:
    reference_frames(match_id)
    return PACK / f"{match_id}_position_reference_draft.json"


def read_reference(match_id: str) -> dict:
    path = reference_path(match_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"revision": 0, "status": "not_reviewed", "frames": {}}


class ShoeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot: int = Field(ge=1, le=6)
    state: Literal["grounded", "airborne", "feet_occluded", "uncertain", "not_visible"]
    shoe_x_px: float | None = Field(default=None, ge=0)
    shoe_y_px: float | None = Field(default=None, ge=0)
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def shoe_consistency(self):
        if self.state == "grounded" and (self.shoe_x_px is None or self.shoe_y_px is None):
            raise ValueError("Grounded reference needs a shoe midpoint click")
        if self.state != "grounded" and (self.shoe_x_px is not None or self.shoe_y_px is not None):
            raise ValueError("Non-grounded or unreadable reference must have null shoe point")
        return self


class ReferenceSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    reviewer_code: str = Field(min_length=1, max_length=80)
    checked_unboxed_source: Literal[True]
    identity_guide_seen: bool
    rows: list[ShoeRow] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def six_shoes(self):
        if sorted(row.slot for row in self.rows) != list(range(1, 7)):
            raise ValueError("Each of the six slots is required")
        return self


@app.get("/api/cases/{match_id}/position-reference")
def get_reference(match_id: str):
    source_case, suggestions = case_data(match_id)
    frames = reference_frames(match_id)
    by_frame = {row["excerpt_frame"]: row for row in suggestions["rows"]}
    main = read_draft(match_id)
    return {"match_id": match_id, "source_sha256": source_case["local_excerpt_sha256"],
            "reference_frames": frames,
            "suggestions": {str(frame): by_frame[frame]["slots"] for frame in frames},
            "reviewed_slots": {str(frame): main["frames"].get(str(frame), {}).get("rows")
                               for frame in frames},
            "proposals": {str(frame): by_frame[frame]["proposals"] for frame in frames},
            "draft": read_reference(match_id)}


@app.get("/api/cases/{match_id}/position-reference/{frame}/image")
def reference_image(match_id: str, frame: int):
    if frame not in reference_frames(match_id):
        raise HTTPException(404, "Frame outside reference plan")
    source_case, _ = case_data(match_id)
    return source_image(source_case, frame)


@app.put("/api/cases/{match_id}/position-reference/{frame}")
def save_reference(match_id: str, frame: int, payload: ReferenceSave):
    if frame not in reference_frames(match_id):
        raise HTTPException(404, "Frame outside reference plan")
    with LOCK:
        draft = read_reference(match_id)
        if payload.expected_revision != draft["revision"]:
            raise HTTPException(409, "Reference changed; reload before saving")
        revision = draft["revision"] + 1
        new_frame = {"excerpt_frame": frame, "reviewer_code": payload.reviewer_code,
                     "checked_unboxed_source": True,
                     "identity_guide_seen": payload.identity_guide_seen,
                     "rows": [row.model_dump() for row in payload.rows]}
        history = PACK / "history" / match_id
        history.mkdir(parents=True, exist_ok=True)
        (history / f"reference_{revision:05d}_{uuid.uuid4().hex}.json").write_text(
            json.dumps({"prior": draft["frames"].get(str(frame)), "new": new_frame}, indent=2)
            + "\n", encoding="utf-8")
        draft["revision"] = revision
        draft["frames"][str(frame)] = new_frame
        draft["status"] = ("complete_single_reviewer" if len(draft["frames"]) == 3
                           else "in_progress")
        path = reference_path(match_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return {"draft": draft}


@app.put("/api/cases/{match_id}/frame/{frame}")
def save_frame(match_id: str, frame: int, payload: FrameSave):
    _, suggestions = case_data(match_id)
    selected = next((row for row in suggestions["rows"] if row["excerpt_frame"] == frame), None)
    if selected is None:
        raise HTTPException(404, "Frame outside selected grid")
    valid_ids = {p["raw_track_id"] for p in selected["proposals"]}
    if any(row.candidate_raw_track_id is not None
           and row.candidate_raw_track_id not in valid_ids for row in payload.rows):
        raise HTTPException(422, "A chosen candidate does not occur in this frame")
    with LOCK:
        draft = read_draft(match_id)
        if payload.expected_revision != draft["revision"]:
            raise HTTPException(409, "Saved review changed; reload before saving")
        prior = draft["frames"].get(str(frame))
        revision = draft["revision"] + 1
        entry = {"excerpt_frame": frame, "reviewer_code": payload.reviewer_code,
                 "checked_all_six_in_source": True,
                 "source_boxes_visible_during_review": True,
                 "rows": [row.model_dump() for row in payload.rows]}
        event = {"revision": revision, "match_id": match_id, "frame": frame,
                 "prior": prior, "new": entry}
        history = PACK / "history" / match_id
        history.mkdir(parents=True, exist_ok=True)
        (history / f"{revision:05d}_{uuid.uuid4().hex}.json").write_text(
            json.dumps(event, indent=2) + "\n", encoding="utf-8")
        draft["frames"][str(frame)] = entry
        draft["revision"] = revision
        draft["status"] = ("complete_single_reviewer" if len(draft["frames"]) == len(suggestions["rows"])
                           else "in_progress")
        path = draft_path(match_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return {"draft": draft}
