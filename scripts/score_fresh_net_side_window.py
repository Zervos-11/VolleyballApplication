"""Score the frozen temporal net cue on source-reviewed player tracks."""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_net_tape_temporal_cue import (LINE, MIN_FRAMES,
                                            MIN_TOP_MOTION_PX, THRESHOLD, runs)
from net_tape_visibility import tape_visibility


LABELS = Path('data/processed/pilot_tracker_evaluation/net_cue_trial/fresh_side_labels_1030_1079.json')
PRED = Path('data/processed/heldout_crossing_eval_em6z/fresh_airborne_segment.json')
OUT = Path('data/processed/pilot_tracker_evaluation/net_cue_trial/fresh_side_score_1030_1079.json')
SOURCE = Path('data/matches/yt_em6zFUxfYpc/heldout_source_cfr.mp4')


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    pred = json.loads(PRED.read_text(encoding='utf-8'))
    if labels['segment'] != pred['segment'] or pred['source_sha256'] != hashlib.sha256(SOURCE.read_bytes()).hexdigest():
        raise ValueError('Segment or source hash mismatch')
    target_ids = {x['track_id'] for x in labels['tracks']}
    rows = {track_id: [] for track_id in target_ids}
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    try:
        for frame in range(labels['segment'][0], labels['segment'][1] + 1):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            for box in pred['raw_predictions'][str(frame)]:
                track_id = box['track_id']
                if track_id not in target_ids:
                    continue
                score = tape_visibility(image, box['bbox'], LINE)
                rows[track_id].append({
                    'frame': frame, 'box_top': round(float(box['bbox'][1]), 1),
                    'status': score['status'],
                    'fraction': score.get('white_ridge_fraction'),
                })
    finally:
        video.release()

    scored = []
    for item in labels['tracks']:
        observations = rows[item['track_id']]
        bright_runs = runs(observations)
        flagged = any(run['criterion_met'] for run in bright_runs)
        scored.append({**item, 'observed_frames': len(observations),
                       'eligible_frames': sum(r['fraction'] is not None for r in observations),
                       'flagged_as_possible_far': flagged,
                       'bright_runs': bright_runs, 'rows': observations})
    summary = {
        side: {'tracks': sum(x['side'] == side for x in scored),
               'flagged': sum(x['side'] == side and x['flagged_as_possible_far'] for x in scored),
               'observed_frames': sum(x['observed_frames'] for x in scored if x['side'] == side),
               'eligible_frames': sum(x['eligible_frames'] for x in scored if x['side'] == side)}
        for side in ('near', 'far')
    }
    OUT.write_text(json.dumps({
        'status': 'fresh_window_single_reviewer',
        'source_sha256': pred['source_sha256'],
        'labels_sha256': hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        'predictions_sha256': hashlib.sha256(PRED.read_bytes()).hexdigest(),
        'temporal_rule_sha256': hashlib.sha256(Path('scripts/evaluate_net_tape_temporal_cue.py').read_bytes()).hexdigest(),
        'photometric_rule_sha256': hashlib.sha256(Path('scripts/net_tape_visibility.py').read_bytes()).hexdigest(),
        'criterion': {'bright_fraction_at_least': THRESHOLD,
                      'consecutive_frames_at_least': MIN_FRAMES,
                      'box_top_motion_px_at_least': MIN_TOP_MOTION_PX},
        'summary': summary, 'tracks': scored,
    }, indent=2) + '\n', encoding='utf-8')
    print(summary)
    for item in scored:
        print(item['track_id'], item['side'], item['description'],
              item['observed_frames'], item['eligible_frames'], item['flagged_as_possible_far'])


if __name__ == '__main__':
    main()
