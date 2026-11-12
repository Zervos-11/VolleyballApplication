"""Local click review for an out-of-point holdout of S3 P34's court transform."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_holdout"
LOCK = threading.Lock()
app = FastAPI(title="S3 P34 court holdout")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol() -> dict:
    return json.loads((PACK / "protocol.json").read_text(encoding="utf-8"))


def draft() -> dict:
    path = PACK / "draft.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"revision": 0, "reviewer_code": "MZ", "frames": {}}


def write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin write refused")


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    status: str
    x_px: float | None = None
    y_px: float | None = None
    note: str = ""


class Save(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int
    reviewer_code: str
    rows: list[Row]


@app.get("/")
def page():
    html = (ROOT / "web/s3p34_calibration_review.html").read_text(encoding="utf-8")
    html = html.replace("<body>", '<body data-api="/api/review">')
    html = html.replace("S3 P34 court-line check", "S3 P34 out-of-point court holdout")
    html = html.replace('href="/s3p34-ground-review"', 'href="/"')
    return HTMLResponse(html)


@app.get("/s3p34_calibration_review.js")
def js():
    return FileResponse(ROOT / "web/s3p34_calibration_review.js", media_type="text/javascript")


@app.get("/api/review")
def state():
    p = protocol()
    for item in p["frames"]:
        if sha(PACK / item["image"]) != item["sha256"]:
            raise HTTPException(409, "Source image hash changed")
    return {"frames": [{"frame": item["frame"], "image_url": f"/api/image/{item['frame']}",
                        "image_sha256": item["sha256"]} for item in p["frames"]],
            "landmarks": p["landmarks"], "protocol_sha256": sha(PACK / "protocol.json"),
            "draft": draft(), "completed_csv_exists": (PACK / "completed.csv").exists()}


@app.get("/api/image/{frame}")
def image(frame: int):
    item = next((x for x in protocol()["frames"] if x["frame"] == frame), None)
    if item is None:
        raise HTTPException(404, "Outside frozen holdout")
    path = PACK / item["image"]
    if sha(path) != item["sha256"]:
        raise HTTPException(409, "Source image hash changed")
    return FileResponse(path)


@app.put("/api/review/{frame}")
def save(frame: int, payload: Save, request: Request):
    check_origin(request)
    p = protocol()
    if frame not in {x["frame"] for x in p["frames"]}:
        raise HTTPException(404, "Outside frozen holdout")
    if not payload.reviewer_code.strip() or [x.code for x in payload.rows] != [x["code"] for x in p["landmarks"]]:
        raise HTTPException(422, "Reviewer and six ordered landmarks required")
    for x in payload.rows:
        if x.status not in ("marked", "uncertain", "occluded"):
            raise HTTPException(422, "Invalid visibility state")
        if x.status == "marked":
            if x.x_px is None or x.y_px is None or not all(math.isfinite(v) for v in (x.x_px, x.y_px)) or not 0 <= x.x_px < 1280 or not 0 <= x.y_px < 720:
                raise HTTPException(422, "Marked landmarks need valid source pixels")
        elif x.x_px is not None or x.y_px is not None:
            raise HTTPException(422, "Uncertain landmarks must have null points")
    with LOCK:
        if (PACK / "completed.csv").exists():
            raise HTTPException(409, "Completed form is frozen")
        d = draft()
        if d["revision"] != payload.expected_revision:
            raise HTTPException(409, "Newer browser revision exists; reload")
        d["reviewer_code"] = payload.reviewer_code.strip()
        d["frames"][str(frame)] = {"rows": [x.model_dump() for x in payload.rows]}
        d["revision"] += 1
        write_json(PACK / "draft.json", d)
    return {"draft": d}


@app.post("/api/review/export")
def export(request: Request):
    check_origin(request)
    with LOCK:
        p, d = protocol(), draft()
        if (PACK / "completed.csv").exists():
            raise HTTPException(409, "Completed form exists")
        if set(d["frames"]) != {str(x["frame"]) for x in p["frames"]}:
            raise HTTPException(409, "Save both frames first")
        rows = []
        for item in p["frames"]:
            for mark in d["frames"][str(item["frame"])]["rows"]:
                target = next(x["court_m"] for x in p["landmarks"] if x["code"] == mark["code"])
                rows.append({"source_frame": item["frame"], "image_sha256": item["sha256"],
                             "landmark_code": mark["code"], "court_x_m": target[0], "court_y_m": target[1],
                             "status": mark["status"], "x_px": mark["x_px"], "y_px": mark["y_px"],
                             "note": mark["note"]})
        temp = PACK / "completed.csv.tmp"
        with temp.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        temp.replace(PACK / "completed.csv")
    return {"rows": len(rows), "completed_csv": str(PACK / "completed.csv"),
            "calibration_approved": False}
