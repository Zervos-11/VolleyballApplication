#!/usr/bin/env python3
"""Visualize sample annotations from pilot CSVs.

Saves annotated frames to an output directory for manual review.

Usage:
  python scripts/visualize_samples.py --matches M1 provolley uts_demo --n 3 --out data/processed/visualizations
"""
import argparse
import csv
import os
import glob
import random
import cv2
import json


def find_video(match_dir):
    vids = glob.glob(os.path.join(match_dir, '*.mp4'))
    return vids[0] if vids else None


def load_metadata(match_dir):
    p = os.path.join(match_dir, 'metadata.json')
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def draw_bbox(frame, row):
    try:
        x1 = int(float(row['x1']))
        y1 = int(float(row['y1']))
        x2 = int(float(row['x2']))
        y2 = int(float(row['y2']))
    except Exception:
        return frame
    idval = row.get('id') or row.get('track_id') or ''
    conf = row.get('confidence', '')
    color = (0, 255, 0)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label = f'{idval} {conf}'
    cv2.putText(frame, label, (x1, max(0, y1-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return frame


def process_match(match_id, match_dir, n, out_dir):
    csv_path = os.path.join(match_dir, 'annotations_pilot.csv')
    if not os.path.exists(csv_path):
        print(f'No annotations_pilot.csv for {match_id}; skipping')
        return 0

    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print(f'No rows in {csv_path}')
        return 0

    samples = rows if len(rows) <= n else random.sample(rows, n)

    video = find_video(match_dir)
    meta = load_metadata(match_dir)
    width, height = (meta.get('resolution') or [1280, 720])

    if not video:
        print(f'No source video for {match_id}; skipping visualizations')
        return 0
    vc = cv2.VideoCapture(video)
    if not vc.isOpened():
        print(f'Cannot open source video for {match_id}; skipping visualizations')
        return 0

    saved = 0
    out_match_dir = os.path.join(out_dir, match_id)
    os.makedirs(out_match_dir, exist_ok=True)

    for row in samples:
        frame_idx = int(float(row.get('frame_index', 0)))
        vc.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = vc.read()
        if not ok or frame is None:
            print(f'Cannot decode frame {frame_idx} for {match_id}; skipping')
            continue

        frame = draw_bbox(frame, row)
        rally = row.get('rally_id', 'r_unknown')
        out_path = os.path.join(out_match_dir, f'{match_id}_{rally}_f{frame_idx}.png')
        cv2.imwrite(out_path, frame)
        saved += 1

    vc.release()
    print(f'Wrote {saved} visualizations for {match_id} -> {out_match_dir}')
    return saved


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--matches', nargs='+', required=True)
    p.add_argument('--n', type=int, default=5)
    p.add_argument('--out', required=True)
    args = p.parse_args()

    total = 0
    for m in args.matches:
        match_dir = os.path.join('data', 'matches', m)
        if not os.path.isdir(match_dir):
            print(f'Match dir not found: {match_dir}')
            continue
        total += process_match(m, match_dir, args.n, args.out)

    print(f'Done. Total images: {total}')


if __name__ == '__main__':
    main()
