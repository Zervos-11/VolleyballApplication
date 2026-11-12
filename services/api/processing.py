from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np

# ----------------- Homography helpers -----------------

def _video_size(video_path: Path) -> tuple[int, int]:
    """Return (width, height) of the video."""
    cap = cv2.VideoCapture(str(video_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    return (w, h)


def _to_np32(pts):
    return np.array(pts, dtype=np.float32)


def _load_homography(
    match_dir: Path,
    meta: Dict,
    video_size: Optional[tuple[int, int]] = None,
) -> Optional[np.ndarray]:
    """
    Build a 3x3 homography mapping pixels -> meters.
    If the JSON homography was created from a scaled screenshot,
    rescale the clicked points to the video's native resolution.
    """

    def _make_H(h: Dict) -> Optional[np.ndarray]:
        if h.get("use_for_metrics") is False:
            return None
        pts_px = np.array(h["points_px"], dtype=np.float32)
        tgt = np.array(h["points_court_m"], dtype=np.float32)

        # If homography JSON includes image_size and we know the video size,
        # scale the points to match the video resolution.
        if video_size and "image_size" in h:
            w_img, h_img = h["image_size"]
            w_vid, h_vid = video_size
            if w_img and h_img and (w_img != w_vid or h_img != h_vid):
                sx = float(w_vid) / float(w_img)
                sy = float(h_vid) / float(h_img)
                pts_px = pts_px * np.array([sx, sy], dtype=np.float32)

        return cv2.getPerspectiveTransform(pts_px, tgt)

    # Priority 1: meta["homography"]
    if isinstance(meta, dict):
        h = meta.get("homography")
        if isinstance(h, dict) and "points_px" in h and "points_court_m" in h:
            try:
                return _make_H(h)
            except Exception:
                pass

    # Priority 2: file data/matches/<match_id>/homography.json
    jpath = match_dir / "homography.json"
    if jpath.exists():
        try:
            h = json.loads(jpath.read_text(encoding="utf-8-sig"))
            return _make_H(h)
        except Exception:
            return None

    return None


def _project_points(H: np.ndarray, pts_xy: np.ndarray) -> np.ndarray:
    """Apply H to N x 2 pixel points -> meters."""
    if pts_xy.size == 0:
        return pts_xy
    pts = pts_xy.reshape(-1, 1, 2).astype(np.float32)
    proj = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
    return proj


# Court bounds helpers (for filtering outliers after projection)
def _court_bounds(meta: Dict, match_dir: Path) -> Optional[Tuple[float, float, float, float]]:
    """Return (xmin, xmax, ymin, ymax) for an active court calibration."""
    calibration = None
    if isinstance(meta, dict):
        h = meta.get("homography")
        if isinstance(h, dict) and "points_court_m" in h:
            calibration = h
    if calibration is None:
        jpath = match_dir / "homography.json"
        if jpath.exists():
            try:
                calibration = json.loads(jpath.read_text(encoding="utf-8-sig"))
            except Exception:
                calibration = None
    if not isinstance(calibration, dict) or calibration.get("use_for_metrics") is False:
        return None
    bounds = calibration.get("court_bounds_m")
    if bounds is not None:
        try:
            xmin, xmax, ymin, ymax = [float(value) for value in bounds]
        except (TypeError, ValueError):
            return None
        if not (np.isfinite([xmin, xmax, ymin, ymax]).all() and xmin < xmax and ymin < ymax):
            return None
        return xmin, xmax, ymin, ymax
    pts = calibration.get("points_court_m")
    if pts is None:
        return None
    a = np.array(pts, dtype=float)
    xmin, ymin = a.min(axis=0)
    xmax, ymax = a.max(axis=0)
    return float(xmin), float(xmax), float(ymin), float(ymax)


def _feature_float(meta: Dict, name: str, default: float) -> float:
    try:
        if isinstance(meta, dict):
            if isinstance(meta.get("features"), dict) and name in meta["features"]:
                return float(meta["features"][name])
            if name in meta:
                return float(meta[name])
    except Exception:
        pass
    return float(default)


def _feature_int(meta: Dict, name: str, default: int) -> int:
    try:
        if isinstance(meta, dict):
            if isinstance(meta.get("features"), dict) and name in meta["features"]:
                return int(meta["features"][name])
            if name in meta:
                return int(meta[name])
    except Exception:
        pass
    return int(default)


def _feature_str(meta: Dict, name: str, default: str) -> str:
    try:
        if isinstance(meta, dict):
            if isinstance(meta.get("features"), dict) and name in meta["features"]:
                return str(meta["features"][name])
            if name in meta:
                return str(meta[name])
    except Exception:
        pass
    return str(default)


def _feature_bool(meta: Dict, name: str, default: bool) -> bool:
    try:
        if isinstance(meta, dict):
            v = None
            if isinstance(meta.get("features"), dict) and name in meta["features"]:
                v = meta["features"][name]
            elif name in meta:
                v = meta[name]
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(int(v))
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "y", "on")
    except Exception:
        pass
    return bool(default)


def _render_topdown_overlay(points_m: np.ndarray, bounds: Tuple[float, float, float, float], out_path: Path) -> Path:
    """Render a top-down 2D scatter of projected points within court bounds.
    Saves PNG to out_path and returns the path.
    """
    xmin, xmax, ymin, ymax = bounds
    if xmax <= xmin or ymax <= ymin:
        return out_path

    # Scale: pixels per meter
    scale = 80  # 80 px/m => 9m ~ 720 px
    margin = 30
    W = int(round((xmax - xmin) * scale)) + margin * 2
    Himg = int(round((ymax - ymin) * scale)) + margin * 2

    # Background
    img = np.zeros((Himg, W, 3), dtype=np.uint8)
    img[:] = (18, 22, 28)

    # Draw court rectangle
    def to_px(x, y):
        u = margin + int(round((x - xmin) * scale))
        v = margin + int(round((ymax - y) * scale))  # invert y
        return u, v

    p0 = to_px(xmin, ymin)
    p1 = to_px(xmax, ymax)
    cv2.rectangle(img, p0, p1, (60, 120, 240), thickness=2)

    # If full court (xmax ~ 18), draw net at x=9
    try:
        if abs((xmax - xmin) - 18.0) < 0.5:
            u0, v0 = to_px(xmin + 9.0, ymin)
            u1, v1 = to_px(xmin + 9.0, ymax)
            cv2.line(img, (u0, v0), (u1, v1), (90, 180, 255), thickness=1)
    except Exception:
        pass

    # Draw meter grid (light)
    for gx in range(int(np.floor(xmin)), int(np.ceil(xmax)) + 1):
        u0, v0 = to_px(gx, ymin)
        u1, v1 = to_px(gx, ymax)
        cv2.line(img, (u0, v0), (u1, v1), (40, 50, 60), 1)
    for gy in range(int(np.floor(ymin)), int(np.ceil(ymax)) + 1):
        u0, v0 = to_px(xmin, gy)
        u1, v1 = to_px(xmax, gy)
        cv2.line(img, (u0, v0), (u1, v1), (40, 50, 60), 1)

    # Plot points
    if points_m is not None and points_m.size > 0:
        pts = np.asarray(points_m, dtype=float)
        for x, y in pts:
            u, v = to_px(x, y)
            if 0 <= u < W and 0 <= v < Himg:
                cv2.circle(img, (u, v), 2, (220, 220, 220), thickness=-1)

    # Save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)
    return out_path


def _render_topdown_tracks(points_m: np.ndarray, ids: np.ndarray, frames: np.ndarray, bounds: Tuple[float, float, float, float], out_path: Path, track_to_jersey: Optional[Dict[int, int]] = None) -> Path:
    """Render colored polylines per track id over time."""
    xmin, xmax, ymin, ymax = bounds
    if xmax <= xmin or ymax <= ymin or points_m.size == 0 or ids.size == 0:
        return out_path

    scale = 80
    margin = 30
    W = int(round((xmax - xmin) * scale)) + margin * 2
    Himg = int(round((ymax - ymin) * scale)) + margin * 2
    img = np.zeros((Himg, W, 3), dtype=np.uint8)
    img[:] = (18, 22, 28)

    def to_px(x, y):
        u = margin + int(round((x - xmin) * scale))
        v = margin + int(round((ymax - y) * scale))
        return u, v

    # Court rectangle
    cv2.rectangle(img, to_px(xmin, ymin), to_px(xmax, ymax), (60, 120, 240), 2)

    pts = np.asarray(points_m, dtype=float)
    tids = np.asarray(ids).astype(int)
    frs = np.asarray(frames).astype(int)

    # Draw per track in frame order
    uniq = np.unique(tids)
    rng = np.random.default_rng(12345)
    colors = {tid: tuple(int(c) for c in rng.integers(80, 255, size=3)) for tid in uniq}

    for tid in uniq:
        sel = (tids == tid)
        if not np.any(sel):
            continue
        pts_tid = pts[sel]
        frs_tid = frs[sel]
        order = np.argsort(frs_tid)
        pts_tid = pts_tid[order]
        # draw polyline
        prev = None
        for x, y in pts_tid:
            u, v = to_px(x, y)
            if 0 <= u < W and 0 <= v < Himg:
                if prev is not None:
                    cv2.line(img, prev, (u, v), colors[tid], 2, cv2.LINE_AA)
                prev = (u, v)
        # Draw jersey label at the last point if mapping provided
        if track_to_jersey and int(tid) in track_to_jersey and pts_tid.shape[0] > 0:
            x_last, y_last = pts_tid[-1]
            u, v = to_px(x_last, y_last)
            if 0 <= u < W and 0 <= v < Himg:
                txt = f"#{track_to_jersey[int(tid)]}"
                cv2.putText(img, txt, (u + 6, v - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 230, 120), 2, cv2.LINE_AA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)
    return out_path


# ----------------- Players lineup helpers -----------------


def _load_players_lineup(match_dir: Path) -> Optional[Dict]:
    p = match_dir / "players_lineup.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _map_tracks_from_lineup(
    lineup: Dict,
    frames_all: np.ndarray,
    track_ids_all: np.ndarray,
    cxy_all_px: np.ndarray,
    video_size: Tuple[int, int],
    max_init_frames: int = 45,
    max_px: Optional[float] = None,
    dy_weight: float = 1.0,
    below_only: bool = False,
    below_min_px: float = 0.0,
    below_max_px: Optional[float] = None,
) -> Tuple[Dict[int, int], Dict]:
    """
    Greedily assign lineup player clicks to nearest tracks in the first window of frames.
    Returns dict track_id -> jersey.
    """
    try:
        players = lineup.get("players", [])
        if not isinstance(players, list) or len(players) == 0:
            return {}
    except Exception:
        return {}

    w, h = video_size
    if max_px is None:
        max_px = max(60.0, 0.05 * max(w, h))

    # Compute per-track initial centroid using earliest frames
    fmin = int(frames_all.min()) if frames_all.size else 0
    fcut = fmin + max(1, int(max_init_frames))
    init_xy: Dict[int, Tuple[float, float]] = {}
    for tid in np.unique(track_ids_all):
        sel = (track_ids_all == tid) & (frames_all <= fcut)
        if not np.any(sel):
            continue
        xy = cxy_all_px[sel]
        if xy.shape[0] == 0:
            continue
        med = np.median(xy, axis=0)
        init_xy[int(tid)] = (float(med[0]), float(med[1]))

    # Build distance matrix (players x tracks)
    track_ids = list(init_xy.keys())
    if len(track_ids) == 0:
        return {}

    import math
    pairs = []  # (dist, player_index, track_id)
    for pi, p in enumerate(players):
        try:
            px, py = float(p["position_px"][0]), float(p["position_px"][1])
            jersey = int(p.get("jersey", 0))
        except Exception:
            continue
        for tid in track_ids:
            tx, ty = init_xy[tid]
            # If jersey click is at torso, only consider feet/ankle points below the click (pixel y grows downward)
            if below_only:
                if ty < (py + float(below_min_px)):
                    continue
                if below_max_px is not None and (ty - py) > float(below_max_px):
                    continue
            dx = px - tx
            dy = (py - ty) * float(max(0.05, dy_weight))
            d = math.hypot(dx, dy)
            pairs.append((d, pi, tid, jersey))
    # Greedy assignment by nearest distance with gating
    pairs.sort(key=lambda x: x[0])
    used_players = set()
    used_tracks = set()
    mapping: Dict[int, int] = {}
    debug: Dict[str, object] = {"players": [], "gate_px": float(max_px)}
    cand_by_player: Dict[int, List[Tuple[int, float]]] = {}
    for d, pi, tid, jersey in pairs:
        cand_by_player.setdefault(pi, []).append((int(tid), float(d)))
    for d, pi, tid, jersey in pairs:
        if d > max_px:
            continue
        if pi in used_players or tid in used_tracks:
            continue
        if jersey <= 0:
            continue
        mapping[int(tid)] = int(jersey)
        used_players.add(pi)
        used_tracks.add(tid)
        if len(used_players) >= 6:
            break
    for pi, p in enumerate(players):
        try:
            px, py = float(p["position_px"][0]), float(p["position_px"][1])
            jersey = int(p.get("jersey", 0))
        except Exception:
            continue
        chosen = None
        for tid, j in mapping.items():
            if j == jersey:
                chosen = tid
                break
        debug["players"].append({
            "slot": int(p.get("slot", pi + 1)),
            "jersey": jersey,
            "position_px": [px, py],
            "candidates": [{"track_id": t, "dist_px": d} for t, d in sorted(cand_by_player.get(pi, []), key=lambda x: x[1])],
            "chosen_track_id": int(chosen) if chosen is not None else None,
        })
    return mapping, debug


def _homography_target_points(meta: Dict, match_dir: Path) -> Optional[np.ndarray]:
    """Return 4x2 array of court target points in meters (LB,RB,RF,LF) if available."""
    pts = None
    if isinstance(meta, dict):
        h = meta.get("homography")
        if isinstance(h, dict) and "points_court_m" in h:
            pts = h.get("points_court_m")
    if pts is None:
        jpath = match_dir / "homography.json"
        if jpath.exists():
            try:
                j = json.loads(jpath.read_text(encoding="utf-8"))
                pts = j.get("points_court_m")
            except Exception:
                pts = None
    return np.array(pts, dtype=np.float32) if pts is not None else None


def _render_camera_overlay(
    video_path: Path,
    H: np.ndarray,
    court_pts_m: np.ndarray,
    frame_idx: int,
    points_px_frame: np.ndarray,
    ids_frame: Optional[np.ndarray],
    out_path: Path,
    track_to_jersey: Optional[Dict[int, int]] = None,
    hist_points_px: Optional[np.ndarray] = None,
    hist_ids: Optional[np.ndarray] = None,
    hist_frames: Optional[np.ndarray] = None,
    trail_len: int = 30,
) -> Optional[Path]:
    """Draw court polygon (meters projected back to pixels) and centroids for a frame."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(frame_idx)))
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return None

        # Court polygon in pixel coords: use inverse H to map meters -> pixels
        H_inv = None
        try:
            H_inv = np.linalg.inv(H)
        except Exception:
            H_inv = None

        if H_inv is not None and court_pts_m is not None and court_pts_m.shape == (4, 2):
            poly_px = cv2.perspectiveTransform(court_pts_m.reshape(-1, 1, 2).astype(np.float32), H_inv).reshape(-1, 2)
            pts_int = np.round(poly_px).astype(int)
            color = (60, 200, 255)
            thickness = 2
            for i in range(4):
                p1 = tuple(pts_int[i % 4])
                p2 = tuple(pts_int[(i + 1) % 4])
                cv2.line(frame, p1, p2, color, thickness, lineType=cv2.LINE_AA)

            # Net line if full court (x span ~ 18m)
            try:
                xs = court_pts_m[:, 0]
                if abs(xs.max() - xs.min() - 18.0) < 0.5:
                    net_m = np.array([[xs.min() + 9.0, court_pts_m[:, 1].min()], [xs.min() + 9.0, court_pts_m[:, 1].max()]], dtype=np.float32)
                    net_px = cv2.perspectiveTransform(net_m.reshape(-1, 1, 2), H_inv).reshape(-1, 2)
                    cv2.line(frame, tuple(np.round(net_px[0]).astype(int)), tuple(np.round(net_px[1]).astype(int)), (90, 180, 255), 1, cv2.LINE_AA)
            except Exception:
                pass

        # Helper color for stable per-track coloring
        def color_for_id(tid: int) -> tuple[int, int, int]:
            try:
                rng = np.random.default_rng(int(tid) * 9973 + 123)
                c = rng.integers(80, 255, size=3)
                return int(c[0]), int(c[1]), int(c[2])
            except Exception:
                return (50, 255, 120)

        # Draw short trails from historical points
        if (
            hist_points_px is not None
            and hist_ids is not None
            and hist_frames is not None
            and hist_points_px.size > 0
        ):
            pts_h = np.asarray(hist_points_px, dtype=float)
            ids_h = np.asarray(hist_ids).astype(int)
            frs_h = np.asarray(hist_frames).astype(int)
            # keep within [frame_idx - trail_len, frame_idx]
            mask_h = (frs_h <= frame_idx) & (frs_h >= frame_idx - int(max(1, trail_len)))
            pts_h = pts_h[mask_h]
            ids_h = ids_h[mask_h]
            frs_h = frs_h[mask_h]
            for tid in np.unique(ids_h):
                sel = (ids_h == tid)
                if not np.any(sel):
                    continue
                pts_tid = pts_h[sel]
                frs_tid = frs_h[sel]
                order = np.argsort(frs_tid)
                pts_tid = pts_tid[order]
                prev = None
                col = color_for_id(int(tid))
                for x, y in pts_tid:
                    u, v = int(round(x)), int(round(y))
                    if prev is not None:
                        cv2.line(frame, prev, (u, v), col, 2, cv2.LINE_AA)
                    prev = (u, v)

        # Draw points for this frame (pixel coords)
        if points_px_frame is not None and points_px_frame.size > 0:
            pts = np.asarray(points_px_frame, dtype=float)
            ids = None
            if ids_frame is not None:
                ids = np.asarray(ids_frame).astype(int)
            for idx, (x, y) in enumerate(pts):
                cx, cy = int(round(x)), int(round(y))
                col = (50, 255, 120)
                tid = None
                if ids is not None and idx < len(ids):
                    tid = int(ids[idx])
                    col = color_for_id(tid)
                cv2.circle(frame, (cx, cy), 4, col, thickness=-1)
                if tid is not None:
                    label_val = None
                    if isinstance(track_to_jersey, dict):
                        try:
                            label_val = track_to_jersey.get(tid, None)
                        except Exception:
                            label_val = None
                    label = f"id:{tid}  #{label_val}" if label_val is not None else f"id:{tid}"
                    cv2.putText(frame, label, (cx + 6, cy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
                    cv2.putText(frame, label, (cx + 6, cy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), frame)
        return out_path
    except Exception:
        return None


def _load_track_to_jersey(meta: Dict, match_dir: Path) -> Dict[int, int]:
    """Load optional mapping of tracker id -> jersey number from metadata or file.
    Accepts keys as strings or ints; returns dict[int,int]."""
    mapping: Dict[int, int] = {}
    # From metadata
    if isinstance(meta, dict) and isinstance(meta.get("track_to_jersey"), dict):
        for k, v in meta["track_to_jersey"].items():
            try:
                mapping[int(k)] = int(v)
            except Exception:
                continue
    # From file if present
    jpath = match_dir / "track_to_jersey.json"
    if jpath.exists():
        try:
            j = json.loads(jpath.read_text(encoding="utf-8"))
            if isinstance(j, dict):
                for k, v in j.items():
                    try:
                        mapping[int(k)] = int(v)
                    except Exception:
                        continue
        except Exception:
            pass
    return mapping

def _ocr_enabled(meta: Dict) -> bool:
    try:
        if isinstance(meta, dict):
            if isinstance(meta.get("features"), dict):
                val = meta["features"].get("jersey_ocr", None)
                if isinstance(val, bool):
                    return val
            if isinstance(meta.get("jersey_ocr"), bool):
                return bool(meta.get("jersey_ocr"))
    except Exception:
        pass
    return False


def _infer_track_to_jersey(
    video_path: Path,
    tracks_arr: np.ndarray,  # [N,4]: frame,id,cx,cy (pixels)
    model_name: str = "yolov8n.pt",
    max_tracks: int = 12,
    samples_per_track: int = 4,
    conf: float = 0.25,
    imgsz: int = 960,
    min_votes: int = 2,
    H: Optional[np.ndarray] = None,
    court_bounds: Optional[Tuple[float, float, float, float]] = None,
    pad_m: float = 0.5,
) -> Dict[int, int]:
    """
    Attempt to infer track_id -> jersey number mapping by sampling frames,
    detecting person boxes, cropping jersey region, and OCR'ing digits.
    """
    try:
        from ultralytics import YOLO
        import easyocr
    except Exception:
        return {}

    # Build per-track list of (frame,cx,cy)
    frames = tracks_arr[:, 0].astype(int)
    tids = tracks_arr[:, 1].astype(int)
    cxy = tracks_arr[:, 2:4].astype(float)

    # Optional: restrict to points inside court (in meters) when homography is available
    in_court = None
    if H is not None and court_bounds is not None:
        try:
            proj = cv2.perspectiveTransform(cxy.reshape(-1, 1, 2).astype(np.float32), H).reshape(-1, 2)
            xmin, xmax, ymin, ymax = court_bounds
            xmin -= pad_m; xmax += pad_m; ymin -= pad_m; ymax += pad_m
            in_court = (
                (proj[:, 0] >= xmin)
                & (proj[:, 0] <= xmax)
                & (proj[:, 1] >= ymin)
                & (proj[:, 1] <= ymax)
            )
        except Exception:
            in_court = None

    # Choose top tracks by frequency
    unique, counts = np.unique(tids, return_counts=True)
    order = np.argsort(-counts)
    top_ids = [int(unique[i]) for i in order[:max_tracks] if unique[i] >= 0]

    # For each track choose sample frames
    samples: Dict[int, List[int]] = {}
    for tid in top_ids:
        idxs = np.where(tids == tid)[0]
        if idxs.size == 0:
            continue
        frs = frames[idxs]
        # If court gating available, keep only in-court frames for this track (fallback to all)
        if in_court is not None:
            mask_track = in_court[idxs]
            frs_in = frs[mask_track]
            # require that some fraction of this track is in court to consider OCR for it
            if frs_in.size == 0 or (frs_in.size / max(1, frs.size)) < 0.25:
                continue
            frs = frs_in
        frs = np.unique(frs)
        if frs.size == 0:
            continue
        if frs.size <= samples_per_track:
            chosen = frs.tolist()
        else:
            # Evenly spaced samples
            chosen = [int(frs[int(round(i * (frs.size - 1) / (samples_per_track - 1)))]) for i in range(samples_per_track)]
        samples[tid] = chosen

    # Unique set of frames to detect
    frame_set = sorted({f for frs in samples.values() for f in frs})

    # Run detection once per sampled frame
    model = YOLO(model_name)
    det_by_frame: Dict[int, Dict[str, np.ndarray]] = {}
    cap = cv2.VideoCapture(str(video_path))
    for f in frame_set:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(f)))
        ok, img = cap.read()
        if not ok or img is None:
            continue
        try:
            res = model.predict(source=img, imgsz=imgsz, conf=conf, verbose=False)[0]
        except Exception:
            continue
        boxes = res.boxes
        if boxes is None or len(boxes) == 0:
            continue
        xyxy = boxes.xyxy.cpu().numpy()
        cls = boxes.cls.cpu().numpy() if boxes.cls is not None else np.full((xyxy.shape[0],), 0)
        keep = (cls == 0)  # person class
        xyxy = xyxy[keep]
        if xyxy.size == 0:
            continue
        det_by_frame[f] = {
            "xyxy": xyxy,
            "cx": (xyxy[:, 0] + xyxy[:, 2]) * 0.5,
            "cy": (xyxy[:, 1] + xyxy[:, 3]) * 0.5,
        }
    cap.release()

    # Prepare OCR reader
    try:
        reader = easyocr.Reader(["en"], gpu=True)
    except Exception:
        try:
            reader = easyocr.Reader(["en"], gpu=False)
        except Exception:
            return {}

    # Helper to crop a jersey ROI from a person box
    def crop_roi(img: np.ndarray, box: np.ndarray) -> Optional[np.ndarray]:
        x1, y1, x2, y2 = box.astype(int)
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = max(x1 + 1, x2)
        y2 = max(y1 + 1, y2)
        w, h = x2 - x1, y2 - y1
        if w <= 10 or h <= 10:
            return None
        # Try a few plausible regions (front/back), pick the largest successful OCR later
        regions = [
            (0.20, 0.80, 0.30, 0.85),  # central torso
            (0.15, 0.85, 0.20, 0.70),  # upper chest/back
            (0.25, 0.75, 0.45, 0.95),  # lower back
        ]
        # return the first region crop; caller may try multiple crops
        rx1 = x1 + int(regions[0][0] * w)
        rx2 = x1 + int(regions[0][1] * w)
        ry1 = y1 + int(regions[0][2] * h)
        ry2 = y1 + int(regions[0][3] * h)
        roi = img[ry1:ry2, rx1:rx2].copy()
        if roi.size == 0:
            return None
        # Optional preproc: upscale for OCR
        scale = 2.0
        roi = cv2.resize(roi, (int(roi.shape[1] * scale), int(roi.shape[0] * scale)), interpolation=cv2.INTER_CUBIC)
        return roi

    # Perform OCR per track
    mapping: Dict[int, int] = {}
    cap = cv2.VideoCapture(str(video_path))
    for tid, frs in samples.items():
        votes: List[int] = []
        for f in frs:
            if f not in det_by_frame:
                continue
            # Get track centroid at frame f
            idxs = np.where((tids == tid) & (frames == f))[0]
            if idxs.size == 0:
                continue
            cx, cy = cxy[idxs[0]]

            # Read frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(f)))
            ok, img = cap.read()
            if not ok or img is None:
                continue

            det = det_by_frame[f]
            # Find nearest person box by centroid distance
            dists = (det["cx"] - cx) ** 2 + (det["cy"] - cy) ** 2
            k = int(np.argmin(dists))
            box = det["xyxy"][k]
            roi = crop_roi(img, box)
            if roi is None:
                continue
            # Try OCR; if low confidence/no digits, try simple thresholding fallback
            def run_ocr(img_in):
                try:
                    return reader.readtext(img_in, detail=1, allowlist="0123456789")
                except Exception:
                    return []
            res = run_ocr(roi)
            if not res:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (3,3), 0)
                thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                thr = cv2.cvtColor(thr, cv2.COLOR_GRAY2BGR)
                res = run_ocr(thr)
            # pick top confidence purely-digit string 1-3 chars
            best_num = None
            best_conf = -1.0
            for _, txt, confscore in res:
                if not txt:
                    continue
                txt = ''.join(ch for ch in txt if ch.isdigit())
                if len(txt) == 0 or len(txt) > 3:
                    continue
                try:
                    val = int(txt)
                except Exception:
                    continue
                if confscore is None:
                    confscore = 0.0
                if confscore > best_conf:
                    best_conf = confscore
                    best_num = val
            if best_num is not None:
                votes.append(best_num)
        if votes:
            vals, cnts = np.unique(np.array(votes), return_counts=True)
            k = int(np.argmax(cnts))
            if int(cnts[k]) >= int(min_votes):
                mapping[int(tid)] = int(vals[k])
    cap.release()

    return mapping


# ----------------- Geometry / metrics -----------------


def _monotone_chain_hull(points: np.ndarray) -> np.ndarray:
    if points.shape[0] < 3:
        return points.copy()
    pts = points[np.lexsort((points[:, 1], points[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(tuple(p))

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(tuple(p))

    hull = np.array(lower[:-1] + upper[:-1], dtype=float)
    return hull


def _polygon_area(poly: np.ndarray) -> float:
    if poly.shape[0] < 3:
        return 0.0
    x = poly[:, 0]
    y = poly[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) * 0.5)


def _simultaneous_pairwise_distance(points: np.ndarray, frames: np.ndarray) -> tuple[Optional[float], int, int]:
    """Average distances only between detections observed in the same frame."""
    if points.shape[0] != frames.shape[0]:
        raise ValueError("Points and frame indices must have the same length")
    total_distance = 0.0
    pair_count = 0
    frame_count = 0
    for frame in np.unique(frames):
        same_frame = points[frames == frame]
        n = same_frame.shape[0]
        if n < 2:
            continue
        distances = np.linalg.norm(same_frame[:, None, :] - same_frame[None, :, :], axis=-1)
        upper = distances[np.triu_indices(n, 1)]
        total_distance += float(upper.sum())
        pair_count += int(upper.size)
        frame_count += 1
    return (total_distance / pair_count if pair_count else None, frame_count, pair_count)


def _coverage_entropy(points: np.ndarray, bins: Tuple[int, int] = (12, 8)) -> float:
    if points.shape[0] == 0:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    H, _, _ = np.histogram2d(x, y, bins=bins)
    s = H.sum()
    if s <= 0:
        return 0.0
    p = (H / s).ravel()
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


# ----------------- Video helpers -----------------


def _pick_video(match_dir: Path) -> Optional[Path]:
    record_path = match_dir / "source_record.json"
    if record_path.exists():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        named = record.get("video_file")
        if named:
            video = Path(named)
            if not video.is_absolute():
                video = (Path.cwd() / video) if (Path.cwd() / video).is_file() else (match_dir / video)
            video = video.resolve()
            if not video.is_file() or video.parent != match_dir.resolve():
                raise ValueError(f"Recorded source video is missing or outside match folder: {named}")
            return video
    hits = sorted(path for ext in ("*.mp4", "*.mov", "*.mkv", "*.avi") for path in match_dir.glob(ext))
    if len(hits) > 1:
        raise ValueError(f"Multiple videos in {match_dir}; set source_record.json video_file")
    return hits[0] if hits else None


def _video_fps(video_path: Path) -> float:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return float(fps)


# ----------------- Main processing -----------------


def compute_tracking_metrics(
    match_dir: Path,
    rallies: List[Dict],
    meta: Dict,
    fps: float,  # kept for signature compatibility; we'll override with actual fps
    max_frames: Optional[int] = None,
) -> List[Dict]:
    """
    Track each selected rally using t_start/t_end and the video's actual FPS.
    If homography exists, detector points are projected to meters; else pixels.
    Spatial summaries remain exploratory until identities and floor contacts are verified.
    No dummy/random fallbacks.
    """
    # Lazy import so API can load without GPU deps:
    from ..inference.yolo_tracker import track_players

    video = _pick_video(match_dir)
    if video is None:
        raise ValueError(f"No source MP4 found in {match_dir}")

    fps_used = _video_fps(video)
    if not np.isfinite(fps_used) or fps_used <= 0:
        raise ValueError("Video frame rate is unavailable")
    import cv2
    cap = cv2.VideoCapture(str(video))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if frame_count <= 0:
        raise ValueError("Video frame count is unavailable")
    pad_start_s = _feature_float(meta, "rally_start_pad_s", 0.0)
    pad_end_s = _feature_float(meta, "rally_end_pad_s", 0.5)
    windows = []
    for r in rallies or []:
        t0, t1 = float(r["t_start"]), float(r["t_end"])
        if not np.isfinite([t0, t1]).all() or t0 < 0 or t1 <= t0:
            raise ValueError(f"Invalid rally time interval: {r.get('rally_id', 'unknown')}")
        f0 = max(0, int(np.floor((t0 + pad_start_s) * fps_used)))
        f1 = int(np.ceil((t1 + pad_end_s) * fps_used))
        if f0 >= frame_count or f1 > frame_count or f1 <= f0:
            raise ValueError(f"Rally outside video frames: {r.get('rally_id', 'unknown')}")
        if max_frames is not None and f1 - f0 > max_frames:
            raise ValueError(f"Rally {r.get('rally_id', 'unknown')} exceeds max_frames={max_frames}")
        windows.append((r, f0, f1))
    tracks = []
    next_track_id = 0
    for r, f0, f1 in windows:
        rally_tracks = track_players(
            str(video), model_name="yolov8n.pt", conf=0.20, imgsz=960,
            max_frames=max_frames, start_frame=f0, end_frame_exclusive=f1,
            use_pose_ankles=_feature_bool(meta, "use_pose_ankles", False),
            pose_model_name=str(meta.get("pose_model", "yolov8n-pose.pt")) if isinstance(meta, dict) else "yolov8n-pose.pt",
            pose_conf=_feature_float(meta, "pose_conf_min", 0.30),
        )
        # ByteTrack starts fresh for every rally; keep numeric IDs distinct in exports.
        valid_ids = [int(row[1]) for row in rally_tracks if int(row[1]) >= 0]
        tracks.extend((fi, tid + next_track_id if tid >= 0 else tid, x, y)
                      for fi, tid, x, y in rally_tracks)
        if valid_ids:
            next_track_id += max(valid_ids) + 1
    # Save raw tracks for inspection
    (match_dir / "tracks_centroids.csv").write_text(
        "frame,track_id,cx,cy\n"
        + "\n".join(f"{int(fi)},{int(tid)},{cx:.2f},{cy:.2f}" for fi, tid, cx, cy in tracks),
        encoding="utf-8",
    )

    # Prepare arrays
    arr = np.array(tracks, dtype=float).reshape(-1, 4)  # [N,4]: frame, id, cx, cy (pixels)
    raw_frames_all = arr[:, 0].astype(int)
    raw_track_ids_all = arr[:, 1].astype(int)
    frames_all = arr[:, 0].astype(int)
    track_ids_all = arr[:, 1].astype(int)
    cxy_all_px = arr[:, 2:4]

    # Homography -> meters if available
    wvid, hvid = _video_size(video)
    H = _load_homography(match_dir, meta, video_size=(wvid, hvid))
    bounds = _court_bounds(meta, match_dir) if H is not None else None
    court_pts_m = _homography_target_points(meta, match_dir) if H is not None else None
    # Try lineup-based mapping first
    track_to_jersey = {}
    try:
        lineup = _load_players_lineup(match_dir)
        if lineup is not None and len(tracks) > 0:
            max_init = _feature_int(meta, "lineup_max_init_frames", 45)
            max_px = _feature_float(meta, "lineup_max_px", -1.0)
            click_mode = _feature_str(meta, "lineup_click_mode", "feet").strip().lower()
            dy_w = 0.25 if click_mode in ("torso", "jersey") else 1.0
            below_only = _feature_bool(meta, "lineup_below_only", False)
            below_min_px = _feature_float(meta, "lineup_below_min_px", 0.0)
            below_max_px = _feature_float(meta, "lineup_below_max_px", -1.0)
            track_to_jersey, mapping_debug = _map_tracks_from_lineup(
                lineup,
                frames_all,
                track_ids_all,
                cxy_all_px,
                (wvid, hvid),
                max_init_frames=max_init,
                max_px=(None if max_px <= 0 else float(max_px)),
                dy_weight=dy_w,
                below_only=below_only,
                below_min_px=float(below_min_px),
                below_max_px=(None if below_max_px <= 0 else float(below_max_px)),
            )
            if track_to_jersey:
                (match_dir / "track_to_jersey.json").write_text(json.dumps(track_to_jersey, indent=2), encoding="utf-8")
            # always write debug file
            try:
                (match_dir / "players_mapping_debug.json").write_text(json.dumps(mapping_debug, indent=2), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        track_to_jersey = {}

    # If still empty, fallback to an existing saved mapping or OCR-based inference
    if len(track_to_jersey) == 0:
        track_to_jersey = _load_track_to_jersey(meta, match_dir)
    if len(track_to_jersey) == 0 and len(tracks) > 0 and _ocr_enabled(meta):
        try:
            track_to_jersey = _infer_track_to_jersey(
                video,
                arr,
                model_name="yolov8n.pt",
                max_tracks=8,
                samples_per_track=4,
                min_votes=2,
                H=H,
                court_bounds=bounds,
                pad_m=0.5,
            )
            if track_to_jersey:
                (match_dir / "track_to_jersey.json").write_text(json.dumps(track_to_jersey, indent=2), encoding="utf-8")
        except Exception:
            track_to_jersey = {}

    # If we have a lineup-based map, optionally restrict to those track_ids (players on this side)
    if track_to_jersey and _feature_bool(meta, "lineup_filter_only", True):
        keep_ids = np.array([int(t) for t in track_to_jersey.keys()], dtype=int)
        mask_keep = np.isin(track_ids_all, keep_ids)
        if np.any(mask_keep):
            frames_all = frames_all[mask_keep]
            track_ids_all = track_ids_all[mask_keep]
            cxy_all_px = cxy_all_px[mask_keep]

    if H is not None:
        cxy_all = _project_points(H, cxy_all_px)
        units = "meters"
    else:
        cxy_all = cxy_all_px
        units = "pixels"

    out: List[Dict] = []
    # Optional per-match time padding (to include whistle tail, etc.)

    for r, f0, f1 in windows:
        raw_mask_time = (raw_frames_all >= f0) & (raw_frames_all < f1)
        mask_time = (frames_all >= f0) & (frames_all < f1)

        if H is not None and bounds is not None:
            xmin, xmax, ymin, ymax = bounds
            pad = _feature_float(meta, "court_pad_m", 0.5)  # meters margin (tunable via metadata)
            inside = (
                (cxy_all[:, 0] >= (xmin - pad))
                & (cxy_all[:, 0] <= (xmax + pad))
                & (cxy_all[:, 1] >= (ymin - pad))
                & (cxy_all[:, 1] <= (ymax + pad))
            )
            mask = mask_time & inside
        else:
            mask = mask_time

        pts = cxy_all[mask]
        mpd, pair_frames, pair_count = _simultaneous_pairwise_distance(pts, frames_all[mask])
        observed_frames = int(np.unique(raw_frames_all[raw_mask_time]).size)
        quality = {
            "status": "exploratory" if pts.shape[0] >= 2 else "insufficient_observations",
            "metric_revision": "same_frame_mpd_v2",
            "start_frame": f0,
            "end_frame_exclusive": f1,
            "expected_frames": f1 - f0,
            "frames_with_track_observations": observed_frames,
            "frames_without_track_observations": f1 - f0 - observed_frames,
            "raw_track_observations": int(raw_mask_time.sum()),
            "retained_track_observations": int(mask.sum()),
            "unique_tracker_ids": int(np.unique(raw_track_ids_all[raw_mask_time]).size),
            "team_identity_verified": False,
            "ground_positions_verified": False,
            "position_source": "projected_box_bottom_center" if H is not None else "box_bottom_center_px",
            "simultaneous_pair_frames": pair_frames,
            "simultaneous_pairs": pair_count,
        }

        overlay_path = None
        overlay_path_all = None
        overlay_tracks_path = None
        overlay_camera_path = None
        if units == "meters" and H is not None and cxy_all.size > 0:
            # Create a top-down overlay for this rally
            # Use time-window points (without in-court filtering) for visualization to show full movement,
            # and expand bounds slightly so near-court points are visible.
            if bounds is None:
                bounds_use = (
                    float(cxy_all[:, 0].min()),
                    float(cxy_all[:, 0].max()),
                    float(cxy_all[:, 1].min()),
                    float(cxy_all[:, 1].max()),
                )
            else:
                bounds_use = bounds
            bxmin, bxmax, bymin, bymax = bounds_use
            expand = _feature_float(meta, "overlay_pad_m", 1.0)
            bounds_overlay = (bxmin - expand, bxmax + expand, bymin - expand, bymax + expand)
            # All points in time window
            pts_overlay_all = cxy_all[mask_time]
            overlay_file_all = match_dir / f"overlay_topdown_{r.get('rally_id','unknown')}_all.png"
            try:
                _render_topdown_overlay(pts_overlay_all, bounds_overlay, overlay_file_all)
                overlay_path_all = str(overlay_file_all)
            except Exception:
                overlay_path_all = None

            # In-court points only
            # Use a more forgiving pad for overlay (separate from metrics pad) to capture near-court motion
            if bounds is not None:
                xmin, xmax, ymin, ymax = bounds
                pad_overlay = _feature_float(meta, "overlay_court_pad_m", max(0.5, expand))
                inside_overlay = (
                    (cxy_all[:, 0] >= (xmin - pad_overlay))
                    & (cxy_all[:, 0] <= (xmax + pad_overlay))
                    & (cxy_all[:, 1] >= (ymin - pad_overlay))
                    & (cxy_all[:, 1] <= (ymax + pad_overlay))
                )
                mask_overlay = mask_time & inside_overlay
            else:
                mask_overlay = mask_time
            pts_overlay_court = cxy_all[mask_overlay]
            overlay_file_court = match_dir / f"overlay_topdown_{r.get('rally_id','unknown')}_court.png"
            try:
                _render_topdown_overlay(pts_overlay_court, bounds_overlay, overlay_file_court)
                overlay_path = str(overlay_file_court)
            except Exception:
                overlay_path = None

            # Tracks polyline overlay (all time-window points, colored by track id)
            overlay_file_tracks = match_dir / f"overlay_topdown_{r.get('rally_id','unknown')}_tracks.png"
            try:
                _render_topdown_tracks(pts_overlay_all, track_ids_all[mask_time], frames_all[mask_time], bounds_overlay, overlay_file_tracks, track_to_jersey)
                overlay_tracks_path = str(overlay_file_tracks)
            except Exception:
                overlay_tracks_path = None

            # Create a camera-view overlay on a representative frame
            frames_in_window = frames_all[mask_time]
            if frames_in_window.size > 0:
                frame_pick = int(np.median(frames_in_window))
            else:
                frame_pick = f0
            idxs_frame = (frames_all == frame_pick)
            pts_frame_px = cxy_all_px[idxs_frame]
            ids_frame = track_ids_all[idxs_frame]
            cam_file = match_dir / f"overlay_camera_{r.get('rally_id','unknown')}.png"
            try:
                trail_len = int(_feature_float(meta, "camera_trail_len_frames", 30))
                # history points around the chosen frame within time window
                hist_mask = mask_time & (frames_all <= frame_pick) & (frames_all >= frame_pick - trail_len)
                _render_camera_overlay(
                    video,
                    H,
                    court_pts_m,
                    frame_pick,
                    pts_frame_px,
                    ids_frame,
                    cam_file,
                    track_to_jersey,
                    hist_points_px=cxy_all_px[hist_mask],
                    hist_ids=track_ids_all[hist_mask],
                    hist_frames=frames_all[hist_mask],
                    trail_len=trail_len,
                )
                overlay_camera_path = str(cam_file)
            except Exception:
                overlay_camera_path = None

        if pts.shape[0] >= 2:
            hull = _monotone_chain_hull(pts)
            cha = _polygon_area(hull)  # m^2 if meters, else px^2
            ent = _coverage_entropy(pts, bins=(12, 8))

            out.append(
                {
                    "rally_id": r.get("rally_id", "unknown"),
                    "rotation_home": None,
                    "quality": quality,
                    "coverage": {
                        "cha": float(max(0.0, cha)),
                        "entropy": float(max(0.0, ent)),
                        "mpd": float(max(0.0, mpd)) if mpd is not None else None,
                        "units": units,
                    },
                    "transition": {"latency_s": None},
                    "outcome_pred": {"p_win": None},
                    "overlay_topdown": overlay_path,
                    "overlay_topdown_all": overlay_path_all,
                    "overlay_topdown_tracks": overlay_tracks_path,
                    "overlay_camera": overlay_camera_path,
                }
            )
        else:
            out.append(
                {
                    "rally_id": r.get("rally_id", "unknown"),
                    "rotation_home": None,
                    "quality": quality,
                    "coverage": {"cha": None, "entropy": None, "mpd": None, "units": units},
                    "transition": {"latency_s": None},
                    "outcome_pred": {"p_win": None},
                    "overlay_topdown": overlay_path,
                    "overlay_topdown_all": overlay_path_all,
                    "overlay_topdown_tracks": overlay_tracks_path,
                    "overlay_camera": overlay_camera_path,
                }
            )

    # Write small diagnostics to help debugging
    if H is not None and bounds is not None:
        xmin, xmax, ymin, ymax = bounds
        pad = _feature_float(meta, "court_pad_m", 0.5)
        inside_all = (
            (cxy_all[:, 0] >= (xmin - pad))
            & (cxy_all[:, 0] <= (xmax + pad))
            & (cxy_all[:, 1] >= (ymin - pad))
            & (cxy_all[:, 1] <= (ymax + pad))
        )
    else:
        inside_all = np.ones(frames_all.shape, dtype=bool)

    diag = {
        "video_file": str(video),
        "fps_used": fps_used,
        "max_frames": max_frames,
        "processed_frame_windows": [
            {"rally_id": r.get("rally_id", "unknown"), "start_frame": f0, "end_frame_exclusive": f1}
            for r, f0, f1 in windows
        ],
        "total_tracks": int(len(tracks)),
        "min_frame": int(frames_all.min()) if frames_all.size else None,
        "max_frame": int(frames_all.max()) if frames_all.size else None,
        "units": units,
        "homography_loaded": bool(H is not None),
        "court_bounds": bounds,
        "jersey_map_size": int(len(track_to_jersey)),
        "ocr_court_only": bool(H is not None and bounds is not None and _ocr_enabled(meta)),
        "rallies": [
            {
                "rally_id": r.get("rally_id", "unknown"),
                "start_frame": f0,
                "end_frame_exclusive": f1,
                "points_in_window": int(((raw_frames_all >= f0) & (raw_frames_all < f1)).sum()),
                "points_after_filter": int((((frames_all >= f0) & (frames_all < f1)) & inside_all).sum()),
            }
            for r, f0, f1 in windows
        ],
    }
    (match_dir / "processing_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")

    return out

