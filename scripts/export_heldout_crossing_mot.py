"""Export complete independent labels and frozen predictions for TrackEval."""

import json
from pathlib import Path

from check_heldout_crossing_labels import MATCH, check


OUT = Path("data/processed/heldout_crossing_eval_em6z/mot_challenge")
BENCHMARK = "VolleyHoldout"


def line(frame, track_id, box, confidence, ground_truth=False):
    x1, y1, x2, y2 = box
    if ground_truth:
        fields = [frame, track_id, x1, y1, x2-x1, y2-y1, 1, 1, 1, -1]
    else:
        fields = [frame, track_id, x1, y1, x2-x1, y2-y1, confidence, -1, -1, -1]
    return ",".join(str(round(value, 4)) if isinstance(value, float) else str(value)
                    for value in fields)


def main():
    validation = check()
    if validation["status"] != "ready":
        raise SystemExit(f"Independent labels are incomplete: {len(validation['issues'])} issues. "
                         "Run scripts/check_heldout_crossing_labels.py for progress.")
    manifest = json.loads((MATCH / "pilot/heldout_tracking_manifest.json").read_text())
    frozen = json.loads((MATCH / "pilot/heldout_tracker_predictions.json").read_text())
    if frozen["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Frozen tracker output belongs to a different source video")
    filtered_path = MATCH / "pilot/heldout_team_filtered_predictions.json"
    filtered = json.loads(filtered_path.read_text()) if filtered_path.exists() else None
    if filtered and filtered["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Filtered tracker output belongs to a different source video")
    court_path = MATCH / "pilot/heldout_court_filtered_predictions.json"
    court = json.loads(court_path.read_text()) if court_path.exists() else None
    if court and court["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Court-filtered output belongs to a different source video")
    grace_path = MATCH / "pilot/heldout_airborne_grace_predictions.json"
    grace = json.loads(grace_path.read_text()) if grace_path.exists() else None
    if grace and grace["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Airborne-grace output belongs to a different source video")
    labels_by_window = {window["name"]: json.loads(
        (MATCH / "pilot/player_annotations" / f"{window['name']}.json").read_text())
        for window in manifest["windows"]}
    stable_ids = sorted({player["player_id"] for saved in labels_by_window.values()
                         for frame in saved["frames"].values()
                         for player in frame["players"]})
    id_numbers = {player_id: index + 1 for index, player_id in enumerate(stable_ids)}
    split = f"{BENCHMARK}-train"
    gt_root = OUT / "gt/mot_challenge" / split
    tracker_root = OUT / "trackers/mot_challenge" / split / "bytetrack/data"
    filtered_root = OUT / "trackers/mot_challenge" / split / "bytetrack_team_filter/data"
    court_root = OUT / "trackers/mot_challenge" / split / "bytetrack_court_filter/data"
    grace_root = OUT / "trackers/mot_challenge" / split / "bytetrack_airborne_grace/data"
    seqmap = OUT / "gt/mot_challenge/seqmaps" / f"{split}.txt"
    seqmap.parent.mkdir(parents=True, exist_ok=True)
    seqmap.write_text("name\n" + "\n".join(window["name"] for window in manifest["windows"]) + "\n")
    tracker_root.mkdir(parents=True, exist_ok=True)
    if filtered:
        filtered_root.mkdir(parents=True, exist_ok=True)
    if court:
        court_root.mkdir(parents=True, exist_ok=True)
    if grace:
        grace_root.mkdir(parents=True, exist_ok=True)
    for window in manifest["windows"]:
        name, first = window["name"], window["first_frame"]
        gt_rows, tracker_rows, filtered_rows, court_rows, grace_rows = [], [], [], [], []
        for source_frame in range(first, window["last_frame"] + 1):
            relative_frame = source_frame - first + 1
            for player in labels_by_window[name]["frames"][str(source_frame)]["players"]:
                if player["bbox"] is not None:
                    gt_rows.append(line(relative_frame, id_numbers[player["player_id"]],
                                        player["bbox"], 1, ground_truth=True))
            for prediction in frozen["windows"][name]["predictions"][str(source_frame)]:
                if prediction["track_id"] >= 1:
                    tracker_rows.append(line(relative_frame, prediction["track_id"],
                                             prediction["bbox"], prediction["confidence"]))
            if filtered:
                for prediction in filtered["windows"][name]["predictions"][str(source_frame)]:
                    if prediction["track_id"] >= 1:
                        filtered_rows.append(line(relative_frame, prediction["track_id"],
                                                  prediction["bbox"], prediction["confidence"]))
            if court:
                for prediction in court["windows"][name]["predictions"][str(source_frame)]:
                    if prediction["track_id"] >= 1:
                        court_rows.append(line(relative_frame, prediction["track_id"],
                                               prediction["bbox"], prediction["confidence"]))
            if grace:
                for prediction in grace["windows"][name]["predictions"][str(source_frame)]:
                    if prediction["track_id"] >= 1:
                        grace_rows.append(line(relative_frame, prediction["track_id"],
                                               prediction["bbox"], prediction["confidence"]))
        sequence = gt_root / name
        (sequence / "gt").mkdir(parents=True, exist_ok=True)
        (sequence / "gt/gt.txt").write_text("\n".join(gt_rows) + "\n")
        (tracker_root / f"{name}.txt").write_text("\n".join(tracker_rows) + "\n")
        if filtered:
            (filtered_root / f"{name}.txt").write_text("\n".join(filtered_rows) + "\n")
        if court:
            (court_root / f"{name}.txt").write_text("\n".join(court_rows) + "\n")
        if grace:
            (grace_root / f"{name}.txt").write_text("\n".join(grace_rows) + "\n")
        (sequence / "seqinfo.ini").write_text(
            f"[Sequence]\nname={name}\nimDir=img1\nframeRate={manifest['fps']:.0f}\n"
            f"seqLength={window['frame_count']}\nimWidth={manifest['frame_size'][0]}\n"
            f"imHeight={manifest['frame_size'][1]}\nimExt=.jpg\n")
        print(f"{name}: {len(gt_rows)} visible GT boxes, {len(tracker_rows)} raw tracker boxes"
              + (f", {len(filtered_rows)} team-filtered boxes" if filtered else ""))
        if court:
            print(f"  {len(court_rows)} court-only boxes")
        if grace:
            print(f"  {len(grace_rows)} airborne-grace boxes")
    (OUT / "player_id_map.json").write_text(json.dumps(id_numbers, indent=2) + "\n")
    print(f"Exported TrackEval input under {OUT}")


if __name__ == "__main__":
    main()
