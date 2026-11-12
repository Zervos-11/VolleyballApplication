#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def ensure_features(meta: dict) -> dict:
    if not isinstance(meta.get("features"), dict):
        meta["features"] = {}
    return meta["features"]


def set_if_not_none(d: dict, key: str, val):
    if val is not None:
        d[key] = val


def load_meta(match_id: str) -> tuple[Path, dict]:
    mdir = Path("data/matches") / match_id
    mdir.mkdir(parents=True, exist_ok=True)
    mpath = mdir / "metadata.json"
    if mpath.exists():
        try:
            meta = json.loads(mpath.read_text(encoding="utf-8-sig"))
        except Exception:
            meta = {}
    else:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    if "schema_version" not in meta:
        meta["schema_version"] = "v1"
    if "match_id" not in meta:
        meta["match_id"] = match_id
    return mpath, meta


def apply_preset(features: dict, meta: dict, name: str):
    name = (name or "").strip().lower()
    if name == "ref_clip":
        # Ankle tracking + jersey-click friendly lineup + stitching; don't drop tracks while tuning
        features.update({
            "use_pose_ankles": True,
            "pose_conf_min": 0.30,
            "lineup_click_mode": "torso",
            "lineup_below_only": True,
            "lineup_below_min_px": 8,
            "lineup_below_max_px": 220,
            "lineup_max_init_frames": 150,
            "lineup_max_px": 160,
            "lineup_filter_only": True,
            "stitch_adopt_unmapped": True,
            "stitch_gap_frames": 20,
            "stitch_max_px": 90,
        })
        # Prefer a lightweight pose model filename if not set at top-level
        meta.setdefault("pose_model", "yolov8n-pose.pt")


def main():
    ap = argparse.ArgumentParser(description="Set/tune match metadata features")
    ap.add_argument("--match", required=True, help="match_id under data/matches/<match>")
    ap.add_argument("--preset", choices=["ref_clip"], help="apply a preset of sensible defaults")
    # Ankle pose
    ap.add_argument("--use-pose-ankles", dest="use_pose_ankles", action="store_true")
    ap.add_argument("--no-use-pose-ankles", dest="use_pose_ankles", action="store_false")
    ap.set_defaults(use_pose_ankles=None)
    ap.add_argument("--pose-model", dest="pose_model")
    ap.add_argument("--pose-conf-min", dest="pose_conf_min", type=float)
    # Lineup mapping
    ap.add_argument("--lineup-click-mode", choices=["feet", "torso"])
    ap.add_argument("--lineup-below-only", dest="lineup_below_only", action="store_true")
    ap.add_argument("--no-lineup-below-only", dest="lineup_below_only", action="store_false")
    ap.set_defaults(lineup_below_only=None)
    ap.add_argument("--lineup-below-min-px", type=float)
    ap.add_argument("--lineup-below-max-px", type=float)
    ap.add_argument("--lineup-max-init-frames", type=int)
    ap.add_argument("--lineup-max-px", type=float)
    ap.add_argument("--lineup-filter-only", dest="lineup_filter_only", action="store_true")
    ap.add_argument("--no-lineup-filter-only", dest="lineup_filter_only", action="store_false")
    ap.set_defaults(lineup_filter_only=None)
    # Stitching
    ap.add_argument("--stitch-adopt-unmapped", dest="stitch_adopt_unmapped", action="store_true")
    ap.add_argument("--no-stitch-adopt-unmapped", dest="stitch_adopt_unmapped", action="store_false")
    ap.set_defaults(stitch_adopt_unmapped=None)
    ap.add_argument("--stitch-gap-frames", type=int)
    ap.add_argument("--stitch-max-px", type=float)
    # Tracker coverage
    ap.add_argument("--tracker-max-frames", type=int)

    args = ap.parse_args()
    mpath, meta = load_meta(args.match)
    features = ensure_features(meta)

    # preset first (provides sensible defaults)
    if args.preset:
        apply_preset(features, meta, args.preset)

    # set options if provided
    set_if_not_none(features, "use_pose_ankles", args.use_pose_ankles)
    if args.pose_model:
        meta["pose_model"] = args.pose_model
    set_if_not_none(features, "pose_conf_min", args.pose_conf_min)

    if args.lineup_click_mode:
        features["lineup_click_mode"] = args.lineup_click_mode
    set_if_not_none(features, "lineup_below_only", args.lineup_below_only)
    set_if_not_none(features, "lineup_below_min_px", args.lineup_below_min_px)
    set_if_not_none(features, "lineup_below_max_px", args.lineup_below_max_px)
    set_if_not_none(features, "lineup_max_init_frames", args.lineup_max_init_frames)
    set_if_not_none(features, "lineup_max_px", args.lineup_max_px)
    set_if_not_none(features, "lineup_filter_only", args.lineup_filter_only)

    set_if_not_none(features, "stitch_adopt_unmapped", args.stitch_adopt_unmapped)
    set_if_not_none(features, "stitch_gap_frames", args.stitch_gap_frames)
    set_if_not_none(features, "stitch_max_px", args.stitch_max_px)

    set_if_not_none(features, "tracker_max_frames", args.tracker_max_frames)

    mpath.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {mpath}")
    print(json.dumps({"match_id": args.match, "features": features, "pose_model": meta.get("pose_model")}, indent=2))


if __name__ == "__main__":
    main()

