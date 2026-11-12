"""Score frozen court geometry on source-reviewed runs in a separate match."""

import hashlib
import json
from pathlib import Path

from evaluate_pilot_tracker import image_to_court, project


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
SHEETS = BASE / 'track_review_sheets.json'
REVIEWS = BASE / 'reviewed_track_runs.json'
CALIBRATION = Path('data/matches/yt_ref_audio1/homography.json')
OUT = BASE / 'reviewed_run_geometry_score.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    sheets = json.loads(SHEETS.read_text(encoding='utf-8'))
    reviews = json.loads(REVIEWS.read_text(encoding='utf-8'))
    if (reviews['raw_sha256'] != sha256(RAW) or
            reviews['track_review_sheets_sha256'] != sha256(SHEETS) or
            raw['calibration_sha256'] != sha256(CALIBRATION)):
        raise ValueError('Reviewed run provenance mismatch')
    frames_by_track = {int(row['track_id']): set(row['frames']) for row in sheets['tracks']}
    matrix = image_to_court(json.loads(CALIBRATION.read_text(encoding='utf-8')))
    counts = {'near': {'accepted': 0, 'total': 0},
              'far': {'accepted': 0, 'total': 0}}
    run_scores = []
    rows = []
    seen = set()
    for review in reviews['runs']:
        track_id, side = int(review['track_id']), review['side']
        if side not in counts:
            raise ValueError(f'Invalid side {side}')
        scored = []
        for frame in range(review['first_frame'], review['last_frame'] + 1):
            key = (frame, track_id)
            if key in seen:
                raise ValueError(f'Duplicate reviewed box {key}')
            seen.add(key)
            if frame not in frames_by_track[track_id]:
                raise ValueError(f'Frame absent from visual review sheet: {key}')
            raw_row = next((row for row in raw['predictions'][str(frame)]
                            if int(row['track_id']) == track_id), None)
            if raw_row is None:
                raise ValueError(f'Frozen box absent: {key}')
            box = raw_row['bbox']
            x, y = map(float, project(((box[0] + box[2]) / 2, box[3]), matrix))
            accepted = 0 <= x <= 9 and 0 <= y <= 9.5
            counts[side]['total'] += 1
            counts[side]['accepted'] += int(accepted)
            scored.append(int(accepted))
            rows.append({'frame': frame, 'track_id': track_id, 'reviewed_side': side,
                         'projected_box_bottom_m': [round(x, 3), round(y, 3)],
                         'strict_court_accepted': accepted})
        run_scores.append({**review, 'accepted': sum(scored),
                           'total': len(scored)})
    OUT.write_text(json.dumps({
        'status': 'selected_reviewed_run_diagnostic',
        'raw_sha256': sha256(RAW), 'reviews_sha256': sha256(REVIEWS),
        'calibration_sha256': sha256(CALIBRATION),
        'rule': 'bbox bottom centre projects to 0<=court_x<=9m and 0<=court_y<=9.5m; no jersey filter',
        'warning': 'Adjacent frames are correlated, and these runs were visually selected for clarity. Counts are descriptive, not independent accuracy estimates.',
        'counts': counts, 'run_scores': run_scores, 'rows': rows,
    }, indent=2) + '\n', encoding='utf-8')
    print(counts)
    print([(r['track_id'], r['side'], r['accepted'], r['total']) for r in run_scores])


if __name__ == '__main__':
    main()
