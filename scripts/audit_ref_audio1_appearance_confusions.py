"""Explain reviewed near misses and far selections from the unchanged rule."""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_team_appearance import THRESHOLD, torso_histogram


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
APPLIED = BASE / 'unchanged_court_jersey_candidates.json'
REVIEWS = BASE / 'reviewed_track_runs.json'
SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
OUT = BASE / 'appearance_confusion_audit.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    applied = json.loads(APPLIED.read_text(encoding='utf-8'))
    reviews = json.loads(REVIEWS.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(SOURCE) or applied['raw_sha256'] != sha256(RAW):
        raise ValueError('Source provenance mismatch')
    seeds = applied['diagnostics']['seed_track_ids']
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    examples = []
    try:
        video.set(cv2.CAP_PROP_POS_FRAMES, raw['first_frame'])
        ok, image = video.read()
        if not ok:
            raise RuntimeError('Cannot read first frame')
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        first_rows = {int(row['track_id']): row for row in raw['predictions'][str(raw['first_frame'])]}
        seed_hist = {track_id: torso_histogram(hsv, first_rows[track_id]['bbox'])[0]
                     for track_id in seeds}
        for frame in range(raw['first_frame'], raw['last_frame'] + 1):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot read frame {frame}')
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            reviewed = [(run['track_id'], run['side']) for run in reviews['runs']
                        if run['first_frame'] <= frame <= run['last_frame']]
            kept_ids = {int(row['track_id']) for row in applied['predictions'][str(frame)]}
            raw_rows = {int(row['track_id']): row for row in raw['predictions'][str(frame)]}
            for track_id, side in reviewed:
                kept = track_id in kept_ids
                if (side == 'far' and not kept) or (side == 'near' and kept):
                    continue
                appearance = torso_histogram(hsv, raw_rows[track_id]['bbox'])
                distances = ({str(seed_id): round(float(cv2.compareHist(
                    appearance[0], seed, cv2.HISTCMP_BHATTACHARYYA)), 3)
                              for seed_id, seed in seed_hist.items()}
                             if appearance is not None else None)
                examples.append({'frame': frame, 'track_id': track_id,
                                 'reviewed_side': side, 'selected': kept,
                                 'at_window_first_frame': frame == raw['first_frame'],
                                 'distances_to_seed_ids': distances})
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'diagnostic_after_review', 'raw_sha256': sha256(RAW),
        'applied_sha256': sha256(APPLIED), 'reviews_sha256': sha256(REVIEWS),
        'seed_track_ids': seeds, 'appearance_threshold': THRESHOLD,
        'examples': examples,
    }, indent=2) + '\n', encoding='utf-8')
    print(examples)


if __name__ == '__main__':
    main()
