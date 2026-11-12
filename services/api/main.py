"""Minimal API (reverted): init/upload/metadata/process/metrics/healthz only."""

import json
import uuid
import traceback
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .models import InitMatchRequest, ProcessResponse, MetricsResponse
from .storage import save_video_chunk, save_json, artifact_path, match_dir
from .processing import compute_tracking_metrics

API_VERSION = "v1"

app = FastAPI(title="Volley Analytics API", version=API_VERSION)
app.mount("/web", StaticFiles(directory="web", html=True), name="web")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return RedirectResponse(url="/web/")


@app.post("/v1/matches/init")
def init_match(req: InitMatchRequest):
    d = match_dir(req.match_id)
    return {"match_id": req.match_id, "set_number": req.set_number, "path": str(d)}


@app.post("/v1/matches/{match_id}/upload")
async def upload_video(match_id: str, file: UploadFile = File(...)):
    import cv2, os

    chunk = await file.read()
    path = save_video_chunk(match_id, file.filename, chunk)

    # Extract first frame PNG alongside video (best effort)
    frame_path = None
    try:
        cap = cv2.VideoCapture(str(path))
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            frame_path = os.path.splitext(str(path))[0] + "_frame0.png"
            cv2.imwrite(frame_path, frame)
    except Exception:
        frame_path = None

    return {"ok": True, "video_path": str(path), "frame0_path": frame_path, "bytes": len(chunk)}


@app.post("/v1/matches/{match_id}/metadata")
async def post_metadata(
    match_id: str,
    request: Request,
    payload: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Accept metadata via form field 'payload', uploaded JSON file, or raw JSON body."""
    text: Optional[str] = None

    if payload is not None:
        text = payload
    elif file is not None:
        raw = await file.read()
        try:
            text = raw.decode("utf-8")
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Could not decode uploaded file as UTF-8."})
    else:
        raw = await request.body()
        if not raw:
            return JSONResponse(status_code=422, content={"error": "Provide 'payload' form field, upload a JSON file, or send raw JSON body."})
        try:
            data = json.loads(raw.decode("utf-8"))
            text = json.dumps(data)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Invalid JSON body: {e}"})

    try:
        json.loads(text)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid JSON: {e}"})

    save_json(match_id, "metadata.json", text)
    return {"ok": True, "bytes": len(text)}


@app.post("/v1/matches/{match_id}/process", response_model=ProcessResponse)
def process(match_id: str):
    job_id = str(uuid.uuid4())
    meta_path = artifact_path(match_id, "metadata.json")
    if not meta_path.exists():
        raise HTTPException(status_code=400, detail="metadata.json missing. Did you POST /metadata?")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                pass
        if isinstance(meta, dict) and isinstance(meta.get("rallies"), list):
            norm = []
            for r in meta["rallies"]:
                if isinstance(r, str):
                    try:
                        r = json.loads(r)
                    except Exception:
                        pass
                norm.append(r)
            meta["rallies"] = norm
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"metadata.json is not valid JSON: {e}")

    rallies = meta.get("rallies", [])
    if not isinstance(rallies, list) or not rallies:
        raise HTTPException(status_code=400, detail="At least one rally is required")
    mdir = match_dir(match_id)

    fps = 30.0
    try:
        cam = meta.get("camera", {})
        if isinstance(cam, dict) and "fps" in cam:
            fps = float(cam["fps"])
    except Exception:
        pass

    try:
        per_rally = compute_tracking_metrics(mdir, rallies, meta, fps=fps)
        metrics = {"schema_version": "v1", "match_id": match_id, "per_rally": per_rally, "artifacts": {}}
        out_path = artifact_path(match_id, "metrics.json")
        out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return ProcessResponse(job_id=job_id, status="done")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


@app.get("/v1/matches/{match_id}/metrics", response_model=MetricsResponse)
def get_metrics(match_id: str):
    mpath = artifact_path(match_id, "metrics.json")
    if not mpath.exists():
        return JSONResponse(status_code=404, content={"error": "metrics not found"})
    return JSONResponse(content=json.loads(mpath.read_text()))


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": API_VERSION}


@app.post("/v1/matches/{match_id}/youtube")
async def youtube_download(match_id: str, request: Request):
    """Download a YouTube video into the match directory.

    Body JSON fields (all optional except url):
      - url: required YouTube URL
      - format: yt-dlp format string. If omitted, picks a progressive format when ffmpeg is absent,
                or bestvideo+bestaudio when ffmpeg is available.
      - max_height: cap selection by height when auto-picking progressive
      - extract_wav: bool (default True) — if ffmpeg is available, write 16 kHz mono WAV alongside MP4

    Returns: { ok, match_id, video_path, frame0_path, wav_path? }
    """
    from pathlib import Path
    import os
    import shutil
    import subprocess
    import json as _json

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    url = (body or {}).get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    d = match_dir(match_id)
    d.mkdir(parents=True, exist_ok=True)
    d_abs = d.resolve()

    # Resolve ffmpeg path (prefer PATH, else probe common Windows locations)
    def _find_ffmpeg() -> Optional[str]:
        p = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if p:
            return p
        try:
            from pathlib import Path as _P
            roots = []
            la = os.getenv("LOCALAPPDATA")
            if la:
                roots.append(_P(la) / "Microsoft" / "WinGet" / "Packages")
            roots.extend([
                _P("C:/Program Files/ffmpeg/bin"),
                _P("C:/Program Files/ffmpeg"),
                _P("C:/Program Files (x86)/ffmpeg/bin"),
                _P("C:/Program Files (x86)/ffmpeg"),
            ])
            for r in roots:
                try:
                    for hit in r.rglob("ffmpeg.exe"):
                        return str(hit)
                except Exception:
                    continue
        except Exception:
            pass
        return None

    # Allow explicit ffmpeg path from request; else try to find one
    ffmpeg_path = None
    override_ff = (body or {}).get("ffmpeg_path")
    if isinstance(override_ff, str) and override_ff:
        try:
            from pathlib import Path as _P
            if _P(override_ff).exists():
                ffmpeg_path = str(_P(override_ff))
        except Exception:
            ffmpeg_path = None
    if ffmpeg_path is None:
        ffmpeg_path = _find_ffmpeg()
    has_ffmpeg = ffmpeg_path is not None
    fmt = (body or {}).get("format")
    if not fmt:
        if has_ffmpeg:
            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
        else:
            # Progressive with both audio+video to avoid merging
            max_h = (body or {}).get("max_height")
            base = "best[acodec!=none][vcodec!=none]"
            if isinstance(max_h, (int, float)) and max_h > 0:
                fmt = f"bv*[height<={int(max_h)}][acodec!=none][vcodec!=none]/{base}"
            else:
                fmt = base
    else:
        # If user requested a merge format but ffmpeg isn't available, downgrade to progressive automatically
        if ('+' in str(fmt)) and not has_ffmpeg:
            max_h = (body or {}).get("max_height")
            base = "best[acodec!=none][vcodec!=none]"
            fmt = (
                f"bv*[height<={int(max_h)}][acodec!=none][vcodec!=none]/{base}"
                if isinstance(max_h, (int, float)) and max_h > 0 else base
            )

    # Use python module if available, else fallback to yt-dlp CLI
    outtmpl = str(d_abs / "youtube_%(id)s.%(ext)s")
    info = None
    video_path: Optional[Path] = None

    try:
        import yt_dlp  # type: ignore
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": fmt,
            "noplaylist": True,
            "merge_output_format": "mp4" if has_ffmpeg else None,
            "quiet": True,
            "no_warnings": True,
        }
        if has_ffmpeg:
            # yt-dlp accepts directory or binary path
            ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg_path) if os.path.isdir(os.path.dirname(ffmpeg_path)) else ffmpeg_path
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Try to resolve final output path(s) from the info dict
            candidates_paths = []
            try:
                for rd in (info.get("requested_downloads") or []):
                    fp = rd.get("filepath") or rd.get("_filename")
                    if fp:
                        candidates_paths.append(fp)
            except Exception:
                pass
            for key in ("filepath", "_filename"):
                try:
                    fp = info.get(key)
                    if fp:
                        candidates_paths.append(fp)
                except Exception:
                    pass
            try:
                candidates_paths.append(ydl.prepare_filename(info))
            except Exception:
                pass
        # Validate any resolved paths; else fallback to newest youtube_* file in match dir
        for fp in candidates_paths:
            p = Path(fp)
            if not p.is_absolute():
                p = d_abs / p.name
            if p.exists():
                video_path = p
                break
        if video_path is None:
            vids = sorted(d_abs.glob("youtube_*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if vids:
                video_path = vids[0]
    except Exception as e:
        # Fallback to CLI
        cli = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
        if not cli:
            raise HTTPException(status_code=500, detail=f"yt-dlp not available: {e}")
        cmd = [cli, "-f", fmt, "-o", outtmpl]
        if has_ffmpeg:
            cmd += ["--ffmpeg-location", os.path.dirname(ffmpeg_path)]
        cmd += [url]
        try:
            subprocess.run(cmd, check=True, cwd=str(d_abs))
        except subprocess.CalledProcessError as cpe:
            raise HTTPException(status_code=500, detail=f"yt-dlp error: {cpe}")
        # Pick newest file in match dir starting with youtube_
        candidates = sorted(d_abs.glob("youtube_*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            video_path = candidates[0]

    if not video_path:
        raise HTTPException(status_code=500, detail="Download completed but output file not found")

    video_path = Path(video_path)
    if not video_path.is_absolute():
        video_path = (d_abs / video_path.name)
    if not video_path.exists():
        raise HTTPException(status_code=500, detail="Download completed but output file not found")

    # If yt-dlp nested another data\matches tree, move file up to match dir
    if video_path.parent.resolve() != d_abs:
        target = d_abs / video_path.name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            import shutil as _sh
            _sh.move(str(video_path), str(target))
            video_path = target
        except Exception:
            pass

    if not video_path.exists():
        raise HTTPException(status_code=500, detail="Download completed but output file not found")

    # Create a frame0 PNG
    frame0_path = None
    try:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            frame0_path = str(video_path.with_name(video_path.stem + "_frame0.png"))
            cv2.imwrite(frame0_path, frame)
    except Exception:
        frame0_path = None

    # Extract 16k mono WAV if requested and we have ffmpeg
    wav_path = None
    extract_wav = bool((body or {}).get("extract_wav", True))
    if extract_wav and has_ffmpeg:
        try:
            wav_path = str(video_path.with_suffix(".wav"))
            subprocess.run([
                ffmpeg_path,
                "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000", "-vn", wav_path
            ], check=True)
        except Exception:
            wav_path = None

    return {
        "ok": True,
        "match_id": match_id,
        "video_path": str(video_path),
        "frame0_path": frame0_path,
        "wav_path": wav_path,
        "used_format": fmt,
        "ffmpeg": has_ffmpeg,
        "ffmpeg_path_used": ffmpeg_path,
    }


# --- Homography endpoints (save / diagnose / fix) ---

@app.post("/v1/matches/{match_id}/homography")
async def post_homography(
    match_id: str,
    request: Request,
    payload: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Save homography JSON to data/matches/<id>/homography.json.
    Accepts payload form field, uploaded file, or raw JSON body."""
    text: Optional[str] = None

    if payload is not None:
        text = payload
    elif file is not None:
        raw = await file.read()
        try:
            text = raw.decode("utf-8")
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Could not decode uploaded file as UTF-8."})
    else:
        raw = await request.body()
        if not raw:
            return JSONResponse(status_code=422, content={"error": "Provide 'payload' field, upload file, or send raw JSON body."})
        try:
            data = json.loads(raw.decode("utf-8"))
            text = json.dumps(data)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Invalid JSON body: {e}"})

    # Basic validation + normalize orientation to LB,RB,RF,LF with back (LB/RB) at image bottom
    try:
        j = json.loads(text)
        if not isinstance(j, dict) or "points_px" not in j or "points_court_m" not in j:
            pass
        else:
            pts = j.get("points_px")
            if isinstance(pts, list) and len(pts) == 4:
                # Identify bottom row by larger y; order left->right for LB,RB.
                with_idx = list(enumerate(pts))
                # sort by y ascending (top to bottom)
                by_y = sorted(with_idx, key=lambda t: float(t[1][1]))
                front = by_y[:2]   # smaller y -> front
                back  = by_y[-2:]  # larger y  -> back
                # sort each pair by x ascending
                back_sorted  = sorted(back,  key=lambda t: float(t[1][0]))  # -> [LB, RB]
                front_sorted = sorted(front, key=lambda t: float(t[1][0]))  # -> [LF, RF]
                # Canonical order LB, RB, RF, LF
                ordered_pts = [
                    [float(back_sorted[0][1][0]),  float(back_sorted[0][1][1])],
                    [float(back_sorted[1][1][0]),  float(back_sorted[1][1][1])],
                    [float(front_sorted[1][1][0]), float(front_sorted[1][1][1])],
                    [float(front_sorted[0][1][0]), float(front_sorted[0][1][1])],
                ]
                j["points_px"] = ordered_pts
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid JSON: {e}"})

    final_text = json.dumps(j)
    save_json(match_id, "homography.json", final_text)
    return {"ok": True, "bytes": len(final_text)}


@app.post("/v1/matches/{match_id}/homography/diagnose")
async def diagnose_homography(match_id: str, request: Request):
    """Diagnose ordering/shape by testing all permutations vs half (9x9) and full (18x9)."""
    import numpy as np  # type: ignore
    import cv2  # type: ignore

    try:
        body = await request.json()
    except Exception:
        body = {}

    if isinstance(body, dict) and "points_px" in body and "points_court_m" in body:
        j = body
    else:
        jpath = artifact_path(match_id, "homography.json")
        if not jpath.exists():
            return JSONResponse(status_code=404, content={"error": "homography.json not found and no body provided"})
        try:
            j = json.loads(jpath.read_text(encoding="utf-8-sig"))
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Invalid homography.json: {e}"})

    pts_px = np.array(j["points_px"], dtype=np.float32)
    half = np.array([[0, 0], [9, 0], [9, 9], [0, 9]], dtype=np.float32)
    full = np.array([[0, 0], [18, 0], [18, 9], [0, 9]], dtype=np.float32)

    def side_metrics(coords):
        a = float(np.linalg.norm(coords[1] - coords[0]))
        b = float(np.linalg.norm(coords[2] - coords[1]))
        c = float(np.linalg.norm(coords[3] - coords[2]))
        d = float(np.linalg.norm(coords[0] - coords[3]))
        diag = float(np.linalg.norm(coords[2] - coords[0]))
        return a, b, c, d, diag

    def score_rect(target):
        import math as _m
        w = float(target[1][0] - target[0][0])
        h = float(target[2][1] - target[1][1])
        diag_t = _m.hypot(w, h)
        best = None
        which = None
        import itertools as _it
        for perm in _it.permutations(range(4)):
            ordered_px = pts_px[list(perm)]
            try:
                H = cv2.getPerspectiveTransform(ordered_px, target)
                proj = cv2.perspectiveTransform(ordered_px.reshape(-1, 1, 2), H).reshape(-1, 2)
            except Exception:
                continue
            a, b, c, d, diag = side_metrics(proj)
            score = abs(a - w) + abs(b - h) + abs(c - w) + abs(d - h) + abs(diag - diag_t)
            rec = (score, list(perm), (a, b, c, d, diag))
            if best is None or score < best[0]:
                best = rec
        return best

    best_half = score_rect(half)
    best_full = score_rect(full)
    pick = ("half", best_half) if (best_full is None or (best_half and best_half[0] <= best_full[0])) else ("full", best_full)

    return {
        "ok": True,
        "match_id": match_id,
        "current_scores": {
            "to_half": float(best_half[0]) if best_half else None,
            "to_full": float(best_full[0]) if best_full else None,
        },
        "suggestion": {
            "court": pick[0],
            "perm": pick[1][1] if pick[1] else None,
            "score": float(pick[1][0]) if pick[1] else None,
            "sides": {
                "a": pick[1][2][0] if pick[1] else None,
                "b": pick[1][2][1] if pick[1] else None,
                "c": pick[1][2][2] if pick[1] else None,
                "d": pick[1][2][3] if pick[1] else None,
                "diag": pick[1][2][4] if pick[1] else None,
            },
        },
        "image_size": j.get("image_size") if isinstance(j, dict) else None,
        "explanation": "Lower score is better; suggested perm/court yields sides closest to target rectangle.",
    }


@app.post("/v1/matches/{match_id}/homography/fix")
async def fix_homography(match_id: str, request: Request):
    """Auto-fix homography by choosing best permutation and half/full court, then rewrite file."""
    import numpy as np  # type: ignore
    import cv2  # type: ignore
    try:
        body = await request.json()
    except Exception:
        body = {}
    do_process = bool((body or {}).get("do_process", False))

    jpath = artifact_path(match_id, "homography.json")
    if not jpath.exists():
        return JSONResponse(status_code=404, content={"error": "homography.json not found"})
    try:
        j = json.loads(jpath.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid homography.json: {e}"})

    pts_px = np.array(j["points_px"], dtype=np.float32)
    image_size = j.get("image_size")
    half = np.array([[0, 0], [9, 0], [9, 9], [0, 9]], dtype=np.float32)
    full = np.array([[0, 0], [18, 0], [18, 9], [0, 9]], dtype=np.float32)

    def side_metrics(coords):
        a = float(np.linalg.norm(coords[1] - coords[0]))
        b = float(np.linalg.norm(coords[2] - coords[1]))
        c = float(np.linalg.norm(coords[3] - coords[2]))
        d = float(np.linalg.norm(coords[0] - coords[3]))
        diag = float(np.linalg.norm(coords[2] - coords[0]))
        return a, b, c, d, diag

    best = None
    import itertools as _it, math as _m
    for target_name, target in (("half", half), ("full", full)):
        w = float(target[1][0] - target[0][0])
        h = float(target[2][1] - target[1][1])
        diag_t = _m.hypot(w, h)
        for perm in _it.permutations(range(4)):
            ordered_px = pts_px[list(perm)]
            try:
                H = cv2.getPerspectiveTransform(ordered_px, target)
                proj = cv2.perspectiveTransform(ordered_px.reshape(-1, 1, 2), H).reshape(-1, 2)
            except Exception:
                continue
            a, b, c, d, diag = side_metrics(proj)
            score = abs(a - w) + abs(b - h) + abs(c - w) + abs(d - h) + abs(diag - diag_t)
            rec = (score, target_name, list(perm), (a, b, c, d, diag))
            if best is None or score < best[0]:
                best = rec

    if best is None:
        return JSONResponse(status_code=500, content={"error": "Could not compute a valid homography"})

    score, which, perm, sides = best
    target = half if which == "half" else full
    ordered_px = pts_px[perm]
    fixed = {
        "schema_version": "v1",
        "points_px": [[float(x), float(y)] for x, y in ordered_px.tolist()],
        "points_court_m": target.tolist(),
    }
    if isinstance(image_size, (list, tuple)) and len(image_size) == 2:
        fixed["image_size"] = [int(image_size[0]), int(image_size[1])]
    jpath.write_text(json.dumps(fixed, indent=2), encoding="utf-8")

    if do_process:
        try:
            _ = process(match_id)
        except Exception:
            pass

    return {"ok": True, "perm": perm, "court": which, "score": float(score)}


# --- Referee analysis (selection + analyze with whistles) ---

def _find_video_in_dir(d: "Path"):
    for ext in ("*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi"):
        hits = list(d.glob(ext))
        if hits:
            return hits[0]
    return None


def _video_fps(path: str) -> float:
    import cv2
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return float(fps)


def _find_ffmpeg_bin() -> Optional[str]:
    import shutil, os
    p = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if p:
        return p
    try:
        from pathlib import Path as _P
        roots = []
        la = os.getenv("LOCALAPPDATA")
        if la:
            roots.append(_P(la) / "Microsoft" / "WinGet" / "Packages")
        roots.extend([
            _P("C:/Program Files/ffmpeg/bin"),
            _P("C:/Program Files/ffmpeg"),
            _P("C:/Program Files (x86)/ffmpeg/bin"),
            _P("C:/Program Files (x86)/ffmpeg"),
        ])
        for r in roots:
            try:
                for hit in r.rglob("ffmpeg.exe"):
                    return str(hit)
            except Exception:
                continue
    except Exception:
        pass
    return None


def _ensure_wav_for_video(video_path: "Path") -> Optional["Path"]:
    import subprocess
    vp = video_path
    wav = vp.with_suffix(".wav")
    if wav.exists():
        return wav
    ff = _find_ffmpeg_bin()
    if not ff:
        return None
    try:
        subprocess.run([ff, "-y", "-i", str(vp), "-ac", "1", "-ar", "16000", "-vn", str(wav)], check=True)
        return wav if wav.exists() else None
    except Exception:
        return None


def _load_wav_mono16(wav_path: "Path"):
    import wave, numpy as np
    with wave.open(str(wav_path), 'rb') as wf:
        nchan = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        fr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)
    if sampwidth != 2:
        # simple conversion: interpret as signed 16 where possible
        import numpy as np
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    else:
        import numpy as np
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if nchan > 1:
        y = y.reshape(-1, nchan).mean(axis=1)
    y = y / 32768.0
    return y, int(fr)


def _detect_whistles(
    y,
    sr,
    frame_ms=30.0,
    hop_ms=10.0,
    z_thresh=3.0,
    merge_ms=250.0,
    bp_low_khz=3.0,
    bp_high_khz=5.0,
    ratio_min=0.5,
    hp_cut_khz: Optional[float] = None,
):
    import numpy as np
    win = int(round(sr * frame_ms / 1000.0))
    hop = int(round(sr * hop_ms / 1000.0))
    if win < 16:
        win = 16
    if hop < 1:
        hop = 1
    n = len(y)
    if n < win:
        return []
    # preemphasis/light HPF can help
    y2 = y - 0.97 * np.concatenate([[0.0], y[:-1]])

    if hp_cut_khz and hp_cut_khz > 0:
        fc = float(hp_cut_khz) * 1000.0
        dt = 1.0 / sr
        rc = 1.0 / (2.0 * np.pi * fc)
        alpha = rc / (rc + dt)
        hp = np.empty_like(y2)
        prev_y = 0.0
        prev_x = y2[0]
        for i in range(len(y2)):
            x = y2[i]
            prev_y = alpha * (prev_y + x - prev_x)
            hp[i] = prev_y
            prev_x = x
        y2 = hp
    # framing
    frames = []
    for s in range(0, n - win + 1, hop):
        frames.append(y2[s:s+win])
    F = np.stack(frames, axis=0)
    # Hann window
    w = np.hanning(win).astype(np.float32)
    F = F * w[None, :]
    # rFFT
    X = np.fft.rfft(F, axis=1)
    mag = (X.real**2 + X.imag**2)
    # bin ranges
    freqs = np.fft.rfftfreq(win, d=1.0/sr)
    lo = float(bp_low_khz) * 1000.0
    hi = float(bp_high_khz) * 1000.0
    band = (freqs >= lo) & (freqs <= hi)
    band_energy = mag[:, band].sum(axis=1)
    total_energy = np.maximum(1e-12, mag.sum(axis=1))
    ratio = band_energy / total_energy
    # z-score
    mu = float(np.mean(ratio))
    sd = float(np.std(ratio) + 1e-6)
    z = (ratio - mu) / sd
    # threshold and ratio gate
    idx = np.where((z >= float(z_thresh)) & (ratio >= float(ratio_min)))[0]
    if idx.size == 0:
        return []
    # merge close hits
    times = idx * (hop / sr)
    merged = []
    cur_start = times[0]
    last = times[0]
    max_gap = float(merge_ms) / 1000.0
    for t in times[1:]:
        if t - last <= max_gap:
            last = t
        else:
            merged.append((cur_start + last) * 0.5)
            cur_start = last = t
    merged.append((cur_start + last) * 0.5)
    return [float(t) for t in merged]


@app.post("/v1/matches/{match_id}/referee/select")
async def referee_select(match_id: str, request: Request):
    """Save anchor/ROI for the referee selection to guide analysis/overlay."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    sel = {}
    if isinstance(body, dict):
        if all(k in body for k in ("anchor_x", "anchor_y")):
            sel["anchor"] = [int(body["anchor_x"]), int(body["anchor_y"])]
        if all(k in body for k in ("roi_x1", "roi_y1", "roi_x2", "roi_y2")):
            x1 = int(min(body["roi_x1"], body["roi_x2"]))
            x2 = int(max(body["roi_x1"], body["roi_x2"]))
            y1 = int(min(body["roi_y1"], body["roi_y2"]))
            y2 = int(max(body["roi_y1"], body["roi_y2"]))
            sel["roi"] = [x1, y1, x2, y2]
    path = artifact_path(match_id, "referee_select.json")
    path.write_text(json.dumps(sel, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path)}


@app.post("/v1/matches/{match_id}/referee/analyze")
def referee_analyze(match_id: str, body: Optional[dict] = None):
    d = match_dir(match_id)
    vid = _find_video_in_dir(d)
    if vid is None:
        raise HTTPException(status_code=400, detail="No video found in match directory")

    max_frames = int((body or {}).get("max_frames", 1200))
    step = int((body or {}).get("step", 1))
    fuse = bool((body or {}).get("fuse_whistles", True))
    use_pose_gestures = bool((body or {}).get("use_pose_gestures", True))
    roi_upscale = float((body or {}).get("roi_upscale", 1.35))
    min_kp_conf = float((body or {}).get("min_kp_conf", 0.35))
    savgol_window = int((body or {}).get("savgol_window", 7))  # odd
    pose_model_name = (body or {}).get("pose_model", "yolov8n-pose.pt")
    enable_cross_chest = bool((body or {}).get("enable_cross_chest", False))

    # Load selection if present
    sel_path = artifact_path(match_id, "referee_select.json")
    referee = None
    if sel_path.exists():
        try:
            referee = json.loads(sel_path.read_text(encoding="utf-8-sig"))
        except Exception:
            referee = None

    res = {
        "events": [],
        "referee": referee,
        "fps": _video_fps(str(vid)),
        "whistles": [],
        "whistle_gesture_pairs": [],
    }

    # --- Pose-based gesture analysis (upper-body only)
    if use_pose_gestures:
        try:
            import cv2, numpy as np
            from ultralytics import YOLO  # type: ignore

            fps = res["fps"] or 30.0
            cap = cv2.VideoCapture(str(vid))
            W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            pose = YOLO(pose_model_name)

            # Build ROI from selection
            def clamp(x, lo, hi):
                return max(lo, min(hi, x))

            roi = None
            if isinstance(referee, dict) and "roi" in referee:
                x1,y1,x2,y2 = referee["roi"]
                cx = (x1+x2)*0.5; cy=(y1+y2)*0.5; w=(x2-x1); h=(y2-y1)
                w *= roi_upscale; h *= roi_upscale
                x1 = int(clamp(cx - w/2, 0, W-1)); x2=int(clamp(cx + w/2, 0, W-1))
                y1 = int(clamp(cy - h/2, 0, H-1)); y2=int(clamp(cy + h/2, 0, H-1))
                roi = (x1,y1,x2,y2)
            elif isinstance(referee, dict) and "anchor" in referee:
                ax,ay = referee["anchor"]
                w = int(W*0.35*roi_upscale); h=int(H*0.6*roi_upscale)
                x1 = int(clamp(ax - w/2, 0, W-1)); x2=int(clamp(ax + w/2, 0, W-1))
                y1 = int(clamp(ay - h/2, 0, H-1)); y2=int(clamp(ay + h/2, 0, H-1))
                roi = (x1,y1,x2,y2)
            else:
                roi = (0,0,W,H)

            # helpers
            def elbow_angle(a,b,c):
                # angle ABC with B at elbow
                ax,ay=a; bx,by=b; cx,cy=c
                v1=(ax-bx, ay-by); v2=(cx-bx, cy-by)
                n1=(v1[0]**2+v1[1]**2)**0.5; n2=(v2[0]**2+v2[1]**2)**0.5
                if n1<1e-6 or n2<1e-6: return 180.0
                dot=(v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2)
                dot=max(-1.0,min(1.0,dot))
                import math
                return abs(math.degrees(math.acos(dot)))

            def classify(kp_xy, kp_conf, crop_w, crop_h):
                # indices: 5 L-shoulder,6 R-shoulder,7 L-elbow,8 R-elbow,9 L-wrist,10 R-wrist
                def ok(i):
                    return kp_conf is None or (i < kp_conf.shape[0] and kp_conf[i] >= min_kp_conf)
                def p(i):
                    return (float(kp_xy[i,0]), float(kp_xy[i,1]))
                used_conf=[]
                def y_less(a,b):
                    return a[1] < b[1] - 0.04*crop_h
                def near_y(a,b):
                    return abs(a[1]-b[1]) <= 0.05*crop_h
                def far_x(a,b):
                    return abs(a[0]-b[0]) >= 0.15*crop_w
                def near(a,b):
                    return ((a[0]-b[0])**2 + (a[1]-b[1])**2)**0.5 <= 0.18*((crop_w+crop_h)/2)

                if kp_xy is None or kp_xy.shape[0] < 11:
                    return "NEUTRAL", 0.0
                Ls, Rs, Le, Re, Lw, Rw = 5,6,7,8,9,10
                if ok(Ls) and ok(Le) and ok(Lw): used_conf += [kp_conf[Ls] if kp_conf is not None else 1.0, kp_conf[Le] if kp_conf is not None else 1.0, kp_conf[Lw] if kp_conf is not None else 1.0]
                if ok(Rs) and ok(Re) and ok(Rw): used_conf += [kp_conf[Rs] if kp_conf is not None else 1.0, kp_conf[Re] if kp_conf is not None else 1.0, kp_conf[Rw] if kp_conf is not None else 1.0]

                sL=p(Ls) if ok(Ls) else None; sR=p(Rs) if ok(Rs) else None
                eL=p(Le) if ok(Le) else None; eR=p(Re) if ok(Re) else None
                wL=p(Lw) if ok(Lw) else None; wR=p(Rw) if ok(Rw) else None

                # derived
                angL = elbow_angle(sL,eL,wL) if sL and eL and wL else 180.0
                angR = elbow_angle(sR,eR,wR) if sR and eR and wR else 180.0
                left_up = (wL and sL and y_less(wL,sL)) and angL>140
                right_up = (wR and sR and y_less(wR,sR)) and angR>140
                left_h = (wL and sL and near_y(wL,sL) and eL and angL>140 and far_x(wL,sL))
                right_h = (wR and sR and near_y(wR,sR) and eR and angR>140 and far_x(wR,sR))
                crossR = (wR and sL and eR and angR<150 and near(wR,sL)) if enable_cross_chest else False
                crossL = (wL and sR and eL and angL<150 and near(wL,sR)) if enable_cross_chest else False

                # priority
                if left_up and right_up:
                    lbl="BOTH_UP"
                elif right_up:
                    lbl="RAISE_RIGHT"
                elif left_up:
                    lbl="RAISE_LEFT"
                elif right_h:
                    lbl="POINT_RIGHT"
                elif left_h:
                    lbl="POINT_LEFT"
                elif crossR or crossL:
                    lbl="CROSS_CHEST"
                else:
                    lbl="NEUTRAL"
                conf = float(np.mean(used_conf)) if used_conf else 0.0
                return lbl, conf

            # iterate frames
            frames_labels=[]
            frame_idx=0
            kept=0
            while kept < max_frames:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                if frame_idx % step != 0:
                    frame_idx+=1
                    continue
                x1,y1,x2,y2 = roi
                crop = frame[y1:y2, x1:x2]
                if crop is None or crop.size==0:
                    frame_idx+=1; kept+=1
                    frames_labels.append((frame_idx-1, "NEUTRAL", 0.0))
                    continue
                pres = pose.predict(crop, imgsz=512, conf=min_kp_conf, verbose=False)[0]
                # pick best person
                kp_xy=None; kp_conf=None
                if hasattr(pres, 'keypoints') and pres.keypoints is not None and pres.keypoints.xy is not None:
                    kxy = pres.keypoints.xy.cpu().numpy()  # (P,K,2)
                    kcf = pres.keypoints.conf.cpu().numpy() if hasattr(pres.keypoints,'conf') and pres.keypoints.conf is not None else None
                    if kxy.shape[0] > 0:
                        # score by mean conf of key upper-body points
                        scores=[]
                        for j in range(kxy.shape[0]):
                            if kcf is not None:
                                sc = float(np.mean(kcf[j,5:11]))
                            else:
                                sc = 1.0
                            scores.append(sc)
                        jbest = int(np.argmax(np.array(scores)))
                        kp_xy = kxy[jbest]
                        kp_conf = kcf[jbest] if kcf is not None else None
                lbl, c = classify(kp_xy, kp_conf, crop.shape[1], crop.shape[0])
                frames_labels.append((frame_idx, lbl, c))
                frame_idx+=1
                kept+=1
            cap.release()

            # segment into events
            def segments(frames_labels, min_len=10):
                out=[]; start=None; cur=None; acc_conf=0.0; n=0
                for f,l,c in frames_labels+[(None,None,None)]:
                    if cur is None:
                        cur=l; start=f; acc_conf=c or 0.0; n=1
                    elif l==cur and f is not None:
                        acc_conf+=c or 0.0; n+=1
                    else:
                        if cur and cur!="NEUTRAL" and n>=min_len:
                            mid = start + (n//2)*step
                            out.append({"t": mid/float(fps), "frame": mid, "gesture": cur, "conf": float(acc_conf/max(1,n))})
                        cur=l; start=f; acc_conf=c or 0.0; n=1
                return out

            res["events"] = segments(frames_labels, min_len=8)  # ~8 frames at 60 fps ≈ 0.13s
        except Exception as e:
            # leave events empty on failure
            res["events"] = []

    if fuse:
        # ensure WAV
        wav = vid.with_suffix(".wav")
        if not wav.exists():
            wav = _ensure_wav_for_video(vid) or wav
        try:
            y, sr = _load_wav_mono16(wav)
            zt = float((body or {}).get("z_thresh", 2.8))
            mg = float((body or {}).get("merge_ms", 350.0))
            bl = float((body or {}).get("bp_low_khz", 2.7))
            bh = float((body or {}).get("bp_high_khz", 5.5))
            rmin = float((body or {}).get("ratio_min", 0.25))
            frame_ms = float((body or {}).get("frame_ms", 30.0))
            hop_ms = float((body or {}).get("hop_ms", 10.0))
            hp_cut = float((body or {}).get("hp_cut_khz", 0.0))
            times = _detect_whistles(
                y,
                sr,
                frame_ms=frame_ms,
                hop_ms=hop_ms,
                z_thresh=zt,
                merge_ms=mg,
                bp_low_khz=bl,
                bp_high_khz=bh,
                ratio_min=rmin,
                hp_cut_khz=hp_cut if hp_cut > 0 else None,
            )
            res["whistles"] = [float(t) for t in times]
            # pair to nearest gesture within 2s
            pairs=[]
            evts = res.get("events", [])
            for tw in times:
                best=None; best_dt=999.0
                for e in evts:
                    dt = abs(float(e.get("t", 0.0)) - tw)
                    if dt < best_dt and dt <= 2.0:
                        best_dt = dt; best = e
                pairs.append({"t_whistle": float(tw), "nearest_gesture": best, "dt": float(best_dt)})
            res["whistle_gesture_pairs"] = pairs
        except Exception:
            res["whistles"] = []
            res["whistle_gesture_pairs"] = []

    out = artifact_path(match_id, "referee_events.json")
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return JSONResponse(content=res)


@app.post("/v1/matches/{match_id}/players/lineup")
async def players_lineup(match_id: str, request: Request):
    """Save manual player lineup clicks + jersey numbers.

    Body example:
      {
        "image_size": [1920, 1080],
        "team": "home",
        "players": [
          { "slot": 1, "jersey": 5, "position_px": [820, 700] },
          ... up to 6 ...
        ]
      }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    players = body.get("players")
    if not isinstance(players, list) or len(players) == 0:
        raise HTTPException(status_code=400, detail="Provide a non-empty 'players' list")

    cleaned = []
    for idx, p in enumerate(players, start=1):
        if not isinstance(p, dict):
            continue
        jersey = p.get("jersey")
        pos = p.get("position_px")
        slot = p.get("slot", idx)
        try:
            jersey = int(jersey)
            if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                continue
            px = [float(pos[0]), float(pos[1])]
        except Exception:
            continue
        cleaned.append({"slot": int(slot), "jersey": jersey, "position_px": px})

    if len(cleaned) == 0:
        raise HTTPException(status_code=400, detail="No valid player entries found")

    payload = {
        "schema_version": "v1",
        "team": body.get("team", "home"),
        "image_size": body.get("image_size"),
        "players": cleaned,
    }
    path = artifact_path(match_id, "players_lineup.json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "count": len(cleaned)}


@app.post("/v1/matches/{match_id}/referee/overlay")
def referee_overlay(match_id: str, body: Optional[dict] = None):
    """Render an MP4 overlay of the referee crop with pose skeleton and gesture label.

    Body (optional): {
      max_frames:int=600, step:int=1, fps_out:float=None,
      use_pose_gestures:bool=True, pose_model:str="yolov8n-pose.pt",
      min_kp_conf:float=0.35, roi_upscale:float=1.35, enable_cross_chest:bool=False,
      draw_whistles:bool=True
    }
    Saves referee_overlay.mp4 under the match folder and returns the path.
    """
    import cv2, numpy as np
    from ultralytics import YOLO  # type: ignore

    d = match_dir(match_id)
    vid = _find_video_in_dir(d)
    if vid is None:
        raise HTTPException(status_code=400, detail="No video found in match directory")

    max_frames = int((body or {}).get("max_frames", 600))
    step = int((body or {}).get("step", 1))
    use_pose_gestures = bool((body or {}).get("use_pose_gestures", True))
    pose_model_name = (body or {}).get("pose_model", "yolov8n-pose.pt")
    min_kp_conf = float((body or {}).get("min_kp_conf", 0.35))
    roi_upscale = float((body or {}).get("roi_upscale", 1.35))
    enable_cross_chest = bool((body or {}).get("enable_cross_chest", False))
    draw_whistles = bool((body or {}).get("draw_whistles", True))

    fps_src = _video_fps(str(vid))
    fps_out = float((body or {}).get("fps_out", fps_src or 30.0))

    # Load selection
    sel_path = artifact_path(match_id, "referee_select.json")
    referee = None
    if sel_path.exists():
        try:
            referee = json.loads(sel_path.read_text(encoding="utf-8-sig"))
        except Exception:
            referee = None

    # ROI calc
    cap = cv2.VideoCapture(str(vid))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    def clamp(x, lo, hi):
        return max(lo, min(hi, x))
    if isinstance(referee, dict) and "roi" in referee:
        x1,y1,x2,y2 = referee["roi"]
        cx=(x1+x2)*0.5; cy=(y1+y2)*0.5; w=(x2-x1); h=(y2-y1)
        w*=roi_upscale; h*=roi_upscale
        x1=int(clamp(cx-w/2,0,W-1)); x2=int(clamp(cx+w/2,0,W-1))
        y1=int(clamp(cy-h/2,0,H-1)); y2=int(clamp(cy+h/2,0,H-1))
        roi=(x1,y1,x2,y2)
    elif isinstance(referee, dict) and "anchor" in referee:
        ax,ay=referee["anchor"]
        w=int(W*0.35*roi_upscale); h=int(H*0.6*roi_upscale)
        x1=int(clamp(ax-w/2,0,W-1)); x2=int(clamp(ax+w/2,0,W-1))
        y1=int(clamp(ay-h/2,0,H-1)); y2=int(clamp(ay+h/2,0,H-1))
        roi=(x1,y1,x2,y2)
    else:
        roi=(0,0,W,H)

    out_path = artifact_path(match_id, "referee_overlay.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    rw, rh = max(1, roi[2]-roi[0]), max(1, roi[3]-roi[1])
    writer = cv2.VideoWriter(str(out_path), fourcc, fps_out, (rw, rh))
    if not writer.isOpened():
        # Fallback codec
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(out_path), fourcc, fps_out, (rw, rh))
        if not writer.isOpened():
            cap.release()
            raise HTTPException(status_code=500, detail="Could not open VideoWriter for overlay")

    pose = YOLO(pose_model_name) if use_pose_gestures else None

    # Load whistles (optional)
    whistles = []
    if draw_whistles:
        evp = artifact_path(match_id, "referee_events.json")
        if evp.exists():
            try:
                ev = json.loads(evp.read_text(encoding="utf-8-sig"))
                whistles = [float(t) for t in (ev.get("whistles") or [])]
            except Exception:
                whistles = []

    # helper functions
    def elbow_angle(a,b,c):
        ax,ay=a; bx,by=b; cx,cy=c
        v1=(ax-bx, ay-by); v2=(cx-bx, cy-by)
        n1=(v1[0]**2+v1[1]**2)**0.5; n2=(v2[0]**2+v2[1]**2)**0.5
        if n1<1e-6 or n2<1e-6: return 180.0
        dot=(v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2)
        dot=max(-1.0,min(1.0,dot))
        import math
        return abs(math.degrees(math.acos(dot)))

    def classify(kp_xy, kp_conf, cw, ch):
        def ok(i):
            return kp_conf is None or (i < kp_conf.shape[0] and kp_conf[i] >= min_kp_conf)
        def p(i):
            return (float(kp_xy[i,0]), float(kp_xy[i,1]))
        def y_less(a,b): return a[1] < b[1] - 0.04*ch
        def near_y(a,b): return abs(a[1]-b[1]) <= 0.05*ch
        def far_x(a,b): return abs(a[0]-b[0]) >= 0.15*cw
        def near(a,b): return ((a[0]-b[0])**2+(a[1]-b[1])**2)**0.5 <= 0.18*((cw+ch)/2)
        if kp_xy is None or kp_xy.shape[0] < 11:
            return "NEUTRAL", 0.0
        Ls, Rs, Le, Re, Lw, Rw = 5,6,7,8,9,10
        sL=p(Ls) if ok(Ls) else None; sR=p(Rs) if ok(Rs) else None
        eL=p(Le) if ok(Le) else None; eR=p(Re) if ok(Re) else None
        wL=p(Lw) if ok(Lw) else None; wR=p(Rw) if ok(Rw) else None
        angL = elbow_angle(sL,eL,wL) if sL and eL and wL else 180.0
        angR = elbow_angle(sR,eR,wR) if sR and eR and wR else 180.0
        left_up = (wL and sL and y_less(wL,sL)) and angL>140
        right_up = (wR and sR and y_less(wR,sR)) and angR>140
        left_h = (wL and sL and near_y(wL,sL) and eL and angL>140 and far_x(wL,sL))
        right_h = (wR and sR and near_y(wR,sR) and eR and angR>140 and far_x(wR,sR))
        crossR = (wR and sL and eR and angR<150 and near(wR,sL)) if enable_cross_chest else False
        crossL = (wL and sR and eL and angL<150 and near(wL,sR)) if enable_cross_chest else False
        if left_up and right_up: lbl="BOTH_UP"
        elif right_up: lbl="RAISE_RIGHT"
        elif left_up: lbl="RAISE_LEFT"
        elif right_h: lbl="POINT_RIGHT"
        elif left_h: lbl="POINT_LEFT"
        elif crossR or crossL: lbl="CROSS_CHEST"
        else: lbl="NEUTRAL"
        return lbl, 1.0

    # COCO skeleton pairs for arms/shoulders
    sk_pairs = [(5,7),(7,9),(6,8),(8,10),(5,6)]

    frame_idx = 0
    kept = 0
    while kept < max_frames:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        if frame_idx % step != 0:
            frame_idx += 1
            continue
        x1,y1,x2,y2 = roi
        crop = frame[y1:y2, x1:x2]
        vis = crop.copy() if crop is not None else np.zeros((rh, rw, 3), dtype=np.uint8)
        lbl = "NEUTRAL"
        if use_pose_gestures and pose is not None and crop is not None and crop.size>0:
            pres = pose.predict(crop, imgsz=512, conf=min_kp_conf, verbose=False)[0]
            kp_xy=None; kp_conf=None
            if hasattr(pres,'keypoints') and pres.keypoints is not None and pres.keypoints.xy is not None:
                kxy = pres.keypoints.xy.cpu().numpy()  # (P,K,2)
                kcf = pres.keypoints.conf.cpu().numpy() if hasattr(pres.keypoints,'conf') and pres.keypoints.conf is not None else None
                if kxy.shape[0] > 0:
                    # pick best by upper-body conf
                    scores=[]
                    for j in range(kxy.shape[0]):
                        scores.append(float(np.mean(kcf[j,5:11])) if kcf is not None else 1.0)
                    jbest = int(np.argmax(np.array(scores)))
                    kp = kxy[jbest]; kpc = kcf[jbest] if kcf is not None else None
                    # draw skeleton
                    for a,b in sk_pairs:
                        if a < kp.shape[0] and b < kp.shape[0]:
                            pa = tuple(np.round(kp[a]).astype(int)); pb = tuple(np.round(kp[b]).astype(int))
                            cv2.line(vis, pa, pb, (60,220,255), 2, cv2.LINE_AA)
                    for j in range(min(kp.shape[0], 11)):
                        pxy = tuple(np.round(kp[j]).astype(int))
                        cv2.circle(vis, pxy, 3, (240,160,70), -1, cv2.LINE_AA)
                    lbl,_ = classify(kp, kpc, vis.shape[1], vis.shape[0])

        # draw label and whistle marker
        ts = frame_idx / float(fps_src or 30.0)
        text = f"{lbl}  t={ts:0.2f}s"
        cv2.rectangle(vis, (6,6), (6+320, 36), (0,0,0), -1)
        cv2.putText(vis, text, (12,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
        if draw_whistles and whistles:
            # draw small red dot if within 0.1s of a whistle
            if any(abs(ts - tw) <= 0.1 for tw in whistles):
                cv2.circle(vis, (vis.shape[1]-20, 20), 8, (0,0,255), -1, cv2.LINE_AA)

        writer.write(vis)
        frame_idx += 1
        kept += 1

    cap.release()
    writer.release()
    return {"ok": True, "path": str(out_path)}


@app.post("/v1/matches/{match_id}/homography/orient")
async def orient_homography(match_id: str, request: Request):
    """Rewrite homography.json with an explicit order mapping.

    Body JSON accepts either:
      - { "perm": [lb_idx, rb_idx, rf_idx, lf_idx], "court": "half"|"full"|null, "do_process": bool }
      - { "lb_idx": int, "rb_idx": int, "rf_idx": int, "lf_idx": int, "court": ..., "do_process": bool }

    The indices refer to the current points_px order stored in homography.json.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    jpath = artifact_path(match_id, "homography.json")
    if not jpath.exists():
        return JSONResponse(status_code=404, content={"error": "homography.json not found"})
    try:
        j = json.loads(jpath.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid homography.json: {e}"})

    pts_px = j.get("points_px")
    if not isinstance(pts_px, list) or len(pts_px) != 4:
        return JSONResponse(status_code=400, content={"error": "homography.points_px must be a 4-element list"})

    perm = body.get("perm")
    if not perm:
        keys = ["lb_idx", "rb_idx", "rf_idx", "lf_idx"]
        if all(k in body for k in keys):
            perm = [int(body[k]) for k in keys]
    if not perm or not (isinstance(perm, list) and len(perm) == 4) or len(set(perm)) != 4 or not all(0 <= int(x) < 4 for x in perm):
        return JSONResponse(status_code=400, content={"error": "Provide perm=[lb,rb,rf,lf] or all of lb_idx,rb_idx,rf_idx,lf_idx with distinct values 0..3"})

    court = body.get("court")
    if court not in (None, "half", "full"):
        return JSONResponse(status_code=400, content={"error": "court must be null, 'half', or 'full'"})

    # Build new homography JSON
    ordered_px = [pts_px[i] for i in perm]
    if court is None:
        # keep existing target if present, else default to half
        target = j.get("points_court_m") or [[0,0],[9,0],[9,9],[0,9]]
    else:
        target = [[0,0],[9,0],[9,9],[0,9]] if court == "half" else [[0,0],[18,0],[18,9],[0,9]]

    fixed = {
        "schema_version": "v1",
        "points_px": [[float(x), float(y)] for x, y in ordered_px],
        "points_court_m": target,
    }
    if isinstance(j.get("image_size"), list) and len(j["image_size"]) == 2:
        fixed["image_size"] = [int(j["image_size"][0]), int(j["image_size"][1])]

    jpath.write_text(json.dumps(fixed, indent=2), encoding="utf-8")

    if bool(body.get("do_process", False)):
        try:
            _ = process(match_id)
        except Exception:
            pass

    return {"ok": True, "perm": perm, "court": court or "preserved"}
