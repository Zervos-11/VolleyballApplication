"""Local, click-based single-reviewer event bracket annotation for S3 P34."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_independent_review_pack"
OUTPUT = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_event_boundary_review"
FRAMES = tuple(range(35986, 36001)) + tuple(range(36138, 36151))
SOURCE_HASH = "da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b"
LOCK = threading.Lock()
app = FastAPI(title="S3 P34 event boundary review")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def manifest() -> dict:
    path = OUTPUT / "manifest.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    value = {"source_video_sha256": SOURCE_HASH,
             "review_type": "single_reviewer_source_only_event_brackets",
             "frames": [{"frame": n, "event": "serve" if n < 36001 else "point_end",
                         "image_sha256": sha(SOURCE / f"unboxed_{n}.png")} for n in FRAMES]}
    write_json(path, value)
    return value


def draft() -> dict:
    path = OUTPUT / "draft.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"revision": 0, "reviewer": "MZ", "verdicts": {}}


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin write refused")


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int
    status: str
    note: str = ""


@app.get("/")
def page():
    return FileResponse(ROOT / "web/s3p34_event_boundary_review.html")


@app.get("/api/review")
def get_review():
    return {"manifest": manifest(), "draft": draft(),
            "completed": (OUTPUT / "completed.json").is_file()}


@app.get("/api/image/{frame}")
def image(frame: int):
    if frame not in FRAMES:
        raise HTTPException(404, "Frame outside frozen event packet")
    path = SOURCE / f"unboxed_{frame}.png"
    if sha(path) != next(x["image_sha256"] for x in manifest()["frames"] if x["frame"] == frame):
        raise HTTPException(409, "Source image hash changed")
    return FileResponse(path)


@app.put("/api/review/{frame}")
def save(frame: int, verdict: Verdict, request: Request):
    check_origin(request)
    if frame not in FRAMES:
        raise HTTPException(404, "Frame outside frozen event packet")
    allowed = {"before_contact", "contact_visible", "after_contact", "uncertain"} if frame < 36001 else {"live", "dead", "uncertain"}
    if verdict.status not in allowed:
        raise HTTPException(422, "Invalid status for this event")
    if (OUTPUT / "completed.json").exists():
        raise HTTPException(409, "Export is frozen")
    with LOCK:
        data = draft()
        if verdict.expected_revision != data["revision"]:
            raise HTTPException(409, "Review changed in another tab; reload")
        data["verdicts"][str(frame)] = {"status": verdict.status, "note": verdict.note.strip()}
        data["revision"] += 1
        write_json(OUTPUT / "draft.json", data)
    return {"draft": data}


@app.post("/api/export")
def export(request: Request):
    check_origin(request)
    with LOCK:
        if (OUTPUT / "completed.json").exists():
            raise HTTPException(409, "Export already exists")
        data = draft()
        if set(data["verdicts"]) != {str(n) for n in FRAMES}:
            raise HTTPException(409, "Review all 28 frames before export")
        ordered = [(n, data["verdicts"][str(n)]["status"]) for n in FRAMES]
        serve = [(n, s) for n, s in ordered if n < 36001]
        ending = [(n, s) for n, s in ordered if n > 36137]
        contact = [n for n, s in serve if s == "contact_visible"]
        before = [n for n, s in serve if s == "before_contact"]
        after = [n for n, s in serve if s == "after_contact"]
        live = [n for n, s in ending if s == "live"]
        dead = [n for n, s in ending if s == "dead"]
        summary = {"serve_contact_visible_frames": contact,
                   "last_reviewed_before_contact": max(before) if before else None,
                   "first_reviewed_after_contact": min(after) if after else None,
                   "last_reviewed_live": max(live) if live else None,
                   "first_reviewed_dead": min(dead) if dead else None,
                   "exact_serve_contact_certified": len(contact) == 1 and not any(s == "uncertain" for n, s in serve if abs(n-contact[0]) <= 1),
                   "exact_point_end_certified": False}
        result = {"status": "single_reviewer_event_review_not_independent_adjudication",
                  "manifest_sha256": sha(OUTPUT / "manifest.json"),
                  "source_video_sha256": SOURCE_HASH, "reviewer": data["reviewer"],
                  "verdicts": data["verdicts"], "summary": summary,
                  "limitations": ["No whistle or ball-ground event can be inferred solely from player disengagement.",
                                  "Uncertain frames remain uncertain; this export does not manufacture exact boundaries."]}
        write_json(OUTPUT / "completed.json", result)
    return result
