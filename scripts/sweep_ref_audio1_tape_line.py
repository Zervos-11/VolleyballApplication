"""Measure sensitivity of transferred tape cues to small line-height errors."""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_ref_audio1_exact_tape import longest_streak
from net_tape_full_box import full_box_tape_span
from net_tape_line_continuity import line_continuity


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
REVIEWS = BASE / 'reviewed_track_runs.json'
SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
OUT = BASE / 'tape_line_height_sensitivity.json'
OFFSETS = (-4, -2, 0, 2, 4)
BASE_LINE = ((620, 516), (1390, 520))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    reviews = json.loads(REVIEWS.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(SOURCE) or reviews['raw_sha256'] != sha256(RAW):
        raise ValueError('Frozen source mismatch')
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    by_offset = {offset: {idx: [] for idx in range(len(reviews['runs']))}
                 for offset in OFFSETS}
    try:
        for frame in range(raw['first_frame'], raw['last_frame'] + 1):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            predictions = {int(row['track_id']): row for row in raw['predictions'][str(frame)]}
            for idx, run in enumerate(reviews['runs']):
                if not run['first_frame'] <= frame <= run['last_frame']:
                    continue
                box = predictions[run['track_id']]['bbox']
                for offset in OFFSETS:
                    line = ((620, 516 + offset), (1390, 520 + offset))
                    if box[0] < 620 or box[2] > 1390:
                        exact = full = {'status': 'not_applicable'}
                    else:
                        exact = line_continuity(image, box, line, hsv)
                        full = full_box_tape_span(image, box, line, hsv)
                    exact_candidate = (exact['status'] == 'measured' and
                                       exact['exact_line_fraction'] >= .8 and
                                       exact['longest_run_fraction'] >= .4 and
                                       exact['left_flank_fraction'] is not None and
                                       exact['right_flank_fraction'] is not None and
                                       exact['left_flank_fraction'] >= .5 and
                                       exact['right_flank_fraction'] >= .5)
                    full_candidate = (full['status'] == 'measured' and
                                      full['full_width_fraction'] >= .9 and
                                      full['left_edge_fraction'] >= .8 and
                                      full['right_edge_fraction'] >= .8 and
                                      full['largest_missing_gap_px'] <= 6)
                    by_offset[offset][idx].append({
                        'frame': frame,
                        'exact_eligible': exact['status'] == 'measured',
                        'full_eligible': full['status'] == 'measured',
                        'exact_candidate': exact_candidate,
                        'full_candidate': full_candidate,
                    })
    finally:
        video.release()
    results = []
    for offset in OFFSETS:
        runs = []
        for idx, review in enumerate(reviews['runs']):
            rows = by_offset[offset][idx]
            runs.append({'track_id': review['track_id'], 'side': review['side'],
                         'first_frame': review['first_frame'],
                         'exact_eligible': sum(r['exact_eligible'] for r in rows),
                         'full_eligible': sum(r['full_eligible'] for r in rows),
                         'exact_streak': longest_streak(rows, 'exact_candidate'),
                         'full_streak': longest_streak(rows, 'full_candidate')})
        results.append({'offset_px': offset,
                        'near_exact_flagged': sum(r['exact_streak'] >= 5 for r in runs
                                                  if r['side'] == 'near'),
                        'far_exact_flagged': sum(r['exact_streak'] >= 5 for r in runs
                                                 if r['side'] == 'far'),
                        'near_full_flagged': sum(r['full_streak'] >= 5 for r in runs
                                                 if r['side'] == 'near'),
                        'far_full_flagged': sum(r['full_streak'] >= 5 for r in runs
                                                if r['side'] == 'far'),
                        'runs': runs})
    OUT.write_text(json.dumps({
        'status': 'post_review_sensitivity_diagnostic',
        'raw_sha256': sha256(RAW), 'reviews_sha256': sha256(REVIEWS),
        'base_tape_line_px': BASE_LINE,
        'offsets_px': OFFSETS,
        'results': results,
    }, indent=2) + '\n', encoding='utf-8')
    print([(r['offset_px'], r['near_exact_flagged'], r['far_exact_flagged'],
            r['near_full_flagged'], r['far_full_flagged']) for r in results])


if __name__ == '__main__':
    main()
