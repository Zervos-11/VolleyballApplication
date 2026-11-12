"""Three-frame source and provisional-box review before the S3 P34 tracker interval."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict


ROOT = Path(__file__).resolve().parents[2]
SCREEN = ROOT / "data/matches/yt_u5HnY2aNW14/screening"
SOURCE = SCREEN / "s3p34_independent_review_pack"
DETECTOR = SCREEN / "s3p34_opening_frame_screen.json"
OUTPUT = SCREEN / "s3p34_opening_frame_review"
FRAMES = (35998, 35999, 36000)
SLOTS = ("28", "12", "15", "7", "19", "21")
LOCK = threading.Lock()
app = FastAPI(title="S3 P34 opening player review")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def manifest() -> dict:
    path = OUTPUT / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    detector = json.loads(DETECTOR.read_text(encoding="utf-8"))
    rows = []
    for row in detector["rows"]:
        n = row["source_frame"]
        assert n in FRAMES
        image = SOURCE / f"unboxed_{n}.png"
        boxes = {p["suggested_slot"]: p["bbox_px"] for p in row["proposals"] if p["suggested_slot"]}
        rows.append({"frame": n, "image_sha256": sha(image), "suggested_boxes": boxes})
    assert tuple(r["frame"] for r in rows) == FRAMES
    result = {"source_sha256": detector["source_sha256"], "detector_sha256": sha(DETECTOR),
              "slots": list(SLOTS), "rows": rows,
              "provenance": "candidate-assisted, single-reviewer, post hoc opening-frame completion"}
    write_json(path, result)
    return result


def draft() -> dict:
    path = OUTPUT / "draft.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"revision": 0, "reviewer": "MZ", "frames": {}}


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin write refused")


class Player(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identity: str
    ground: str
    box: str
    floor: str


class FrameReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int
    checked_all_six: bool
    players: dict[str, Player]


@app.get("/")
def page():
    return FileResponse(ROOT / "web/s3p34_opening_frame_review.html")


@app.get("/api/review")
def get_review():
    return {"manifest": manifest(), "draft": draft(), "completed": (OUTPUT / "completed.json").exists()}


@app.get("/api/image/{frame}")
def image(frame: int):
    if frame not in FRAMES:
        raise HTTPException(404, "Outside packet")
    path = SOURCE / f"unboxed_{frame}.png"
    if sha(path) != next(r["image_sha256"] for r in manifest()["rows"] if r["frame"] == frame):
        raise HTTPException(409, "Source image hash changed")
    return FileResponse(path)


@app.put("/api/review/{frame}")
def save(frame: int, verdict: FrameReview, request: Request):
    check_origin(request)
    if frame not in FRAMES or not verdict.checked_all_six or set(verdict.players) != set(SLOTS):
        raise HTTPException(422, "Check all six roster slots in this frame")
    if (OUTPUT / "completed.json").exists():
        raise HTTPException(409, "Export already frozen")
    boxes = next(r["suggested_boxes"] for r in manifest()["rows"] if r["frame"] == frame)
    for slot, player in verdict.players.items():
        if player.identity not in {"same_by_sequence", "digit_confirmed", "uncertain", "wrong"}:
            raise HTTPException(422, f"Invalid identity for {slot}")
        if player.ground not in {"grounded", "airborne", "uncertain"}:
            raise HTTPException(422, f"Invalid ground state for {slot}")
        if player.box not in {"same", "missing", "wrong"}:
            raise HTTPException(422, f"Invalid box state for {slot}")
        if player.floor not in {"plausible", "not_applicable", "uncertain"}:
            raise HTTPException(422, f"Invalid floor state for {slot}")
        if slot not in boxes and player.box == "same":
            raise HTTPException(422, f"No suggested box for {slot}")
        if player.ground != "grounded" and player.floor == "plausible":
            raise HTTPException(422, f"Floor cannot be plausible when {slot} is not grounded")
    with LOCK:
        data = draft()
        if verdict.expected_revision != data["revision"]:
            raise HTTPException(409, "Review changed; reload")
        data["frames"][str(frame)] = {slot: p.model_dump() for slot, p in verdict.players.items()}
        data["revision"] += 1
        write_json(OUTPUT / "draft.json", data)
    return {"draft": data}


@app.post("/api/export")
def export(request: Request):
    check_origin(request)
    with LOCK:
        if (OUTPUT / "completed.json").exists():
            raise HTTPException(409, "Already exported")
        data = draft()
        if set(data["frames"]) != {str(n) for n in FRAMES}:
            raise HTTPException(409, "Review all three frames before export")
        result = {"status": "single_reviewer_candidate_assisted_source_and_box_review",
                  "manifest_sha256": sha(OUTPUT / "manifest.json"),
                  "reviewer": data["reviewer"], "frames": data["frames"],
                  "limitations": ["Nearest-box slot suggestions were visible to the reviewer.",
                                  "No manual shoe coordinate was marked in this opening review.",
                                  "Provisional detector boxes are not independent jersey identification."]}
        write_json(OUTPUT / "completed.json", result)
    return result
