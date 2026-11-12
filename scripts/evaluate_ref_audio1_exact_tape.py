"""Transfer existing exact-line and full-box tape checks to reviewed runs."""

import hashlib
import json
from pathlib import Path

import cv2

from net_tape_full_box import full_box_tape_span
from net_tape_line_continuity import line_continuity


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
REVIEWS = BASE / 'reviewed_track_runs.json'
SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
OUT = BASE / 'exact_tape_transfer_audit.json'
TAPE_LINE = ((620, 516), (1390, 520))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def longest_streak(rows, field):
    longest = streak = 0
    previous = None
    for row in rows:
        if row[field]:
            streak = streak + 1 if previous is not None and row['frame'] == previous + 1 else 1
            longest = max(longest, streak)
        else:
            streak = 0
        previous = row['frame']
    return longest


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
    measured = {}
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
                if box[0] < TAPE_LINE[0][0] or box[2] > TAPE_LINE[1][0]:
                    exact = full = {'status': 'not_applicable',
                                    'reason': 'outside_calibrated_tape_span'}
                else:
                    exact = line_continuity(image, box, TAPE_LINE, hsv)
                    full = full_box_tape_span(image, box, TAPE_LINE, hsv)
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
                measured.setdefault(idx, []).append({
                    'frame': frame, 'track_id': run['track_id'],
                    'side': run['side'], 'exact': exact, 'full': full,
                    'exact_candidate': exact_candidate,
                    'full_candidate': full_candidate,
                })
    finally:
        video.release()
    runs = []
    for idx, run in enumerate(reviews['runs']):
        rows = measured[idx]
        runs.append({**run,
                     'exact_eligible': sum(r['exact']['status'] == 'measured' for r in rows),
                     'exact_candidate_frames': sum(r['exact_candidate'] for r in rows),
                     'exact_longest_streak': longest_streak(rows, 'exact_candidate'),
                     'full_eligible': sum(r['full']['status'] == 'measured' for r in rows),
                     'full_candidate_frames': sum(r['full_candidate'] for r in rows),
                     'full_longest_streak': longest_streak(rows, 'full_candidate'),
                     'rows': rows})
    summary = {}
    for side in ('near', 'far'):
        subset = [r for r in runs if r['side'] == side]
        summary[side] = {
            'runs': len(subset),
            'exact_eligible': sum(r['exact_eligible'] for r in subset),
            'exact_candidate_frames': sum(r['exact_candidate_frames'] for r in subset),
            'exact_runs_flagged': sum(r['exact_longest_streak'] >= 5 for r in subset),
            'full_eligible': sum(r['full_eligible'] for r in subset),
            'full_candidate_frames': sum(r['full_candidate_frames'] for r in subset),
            'full_runs_flagged': sum(r['full_longest_streak'] >= 5 for r in subset),
        }
    OUT.write_text(json.dumps({
        'status': 'transfer_diagnostic', 'source_sha256': raw['source_sha256'],
        'raw_sha256': sha256(RAW), 'reviews_sha256': sha256(REVIEWS),
        'exact_rule_sha256': sha256(Path('scripts/net_tape_line_continuity.py')),
        'full_rule_sha256': sha256(Path('scripts/net_tape_full_box.py')),
        'tape_line_px': TAPE_LINE,
        'criterion': 'unchanged em6z exact/full thresholds and five-frame streak',
        'summary': summary, 'runs': runs,
    }, indent=2) + '\n', encoding='utf-8')
    print(summary)
    print([(r['track_id'], r['side'], r['exact_longest_streak'],
            r['full_longest_streak']) for r in runs])


if __name__ == '__main__':
    main()
