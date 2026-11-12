"""Exploratory temporal check for the lower net tape in the heldout match.

The side labels below were read from source-only frames around the block.
This is a development diagnostic, not an independent accuracy estimate.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2

from net_tape_visibility import tape_visibility


ROOT = Path('data/matches/yt_em6zFUxfYpc')
OUT = Path('data/processed/pilot_tracker_evaluation/net_cue_trial/temporal_tape_audit.json')
PRED = Path('data/processed/heldout_crossing_eval_em6z/frozen_block_segment_860_960.json')
LINE = ((70, 618), (1515, 618))
THRESHOLD = 0.8
MIN_FRAMES = 5
MIN_TOP_MOTION_PX = 30


def runs(rows):
    """Find sustained bright-line runs during visible vertical body motion."""
    result = []
    current = []
    for row in rows:
        if (row['fraction'] is not None and row['fraction'] >= THRESHOLD
                and (not current or row['frame'] == current[-1]['frame'] + 1)):
            current.append(row)
        else:
            if current:
                result.append(current)
            current = [row] if row['fraction'] is not None and row['fraction'] >= THRESHOLD else []
    if current:
        result.append(current)
    return [{'start': run[0]['frame'], 'end': run[-1]['frame'],
             'frames': len(run),
             'top_motion_px': round(max(r['box_top'] for r in run)
                                    - min(r['box_top'] for r in run), 1),
             'criterion_met': len(run) >= MIN_FRAMES and
                              max(r['box_top'] for r in run)
                              - min(r['box_top'] for r in run) >= MIN_TOP_MOTION_PX}
            for run in result]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    pred = json.loads(PRED.read_text())
    source = ROOT / 'heldout_source_cfr.mp4'
    if hashlib.sha256(source.read_bytes()).hexdigest() != pred['source_sha256']:
        raise ValueError('Source hash mismatch')

    # Source-only inspection: dark #10 jumps on the far side at 880-888;
    # blue #9 jumps on the near side at 880-960. Track IDs are the raw box links.
    labelled_tracks = [
        {'key': 'far_10', 'side': 'far', 'track_id': 128, 'start': 880, 'end': 888},
        {'key': 'near_9', 'side': 'near', 'track_id': 96, 'start': 880, 'end': 960},
    ]
    gt = {}
    for window in ('cross_a', 'cross_b'):
        labels = json.loads((ROOT / 'pilot/player_annotations' / f'{window}.json').read_text())
        for frame, record in labels['frames'].items():
            for player in record['players']:
                if player.get('bbox') is not None:
                    gt.setdefault((window, player['player_id']), []).append(
                        (int(frame), player['bbox']))

    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise FileNotFoundError(source)
    cache = {}
    def measure(frame, box):
        if frame not in cache:
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            cache[frame] = image
        score = tape_visibility(cache[frame], box, LINE)
        return {'frame': frame, 'box_top': round(float(box[1]), 1),
                'fraction': score.get('white_ridge_fraction'),
                'status': score['status']}

    groups = []
    try:
        for item in labelled_tracks:
            rows = []
            for frame in range(item['start'], item['end'] + 1):
                for box in pred['raw_predictions'][str(frame)]:
                    if box['track_id'] == item['track_id']:
                        rows.append(measure(frame, box['bbox']))
            groups.append({**item, 'label_basis': 'source-only crop review, near-side blue / far-side dark',
                           'rows': rows, 'bright_runs': runs(rows)})
        for (window, player_id), items in sorted(gt.items()):
            rows = [measure(frame, box) for frame, box in sorted(items)]
            groups.append({'key': f'{window}:{player_id}', 'side': 'near',
                           'label_basis': 'existing near-side player annotations',
                           'rows': rows, 'bright_runs': runs(rows)})
    finally:
        video.release()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        'status': 'exploratory_development_only',
        'source_sha256': pred['source_sha256'],
        'prediction_sha256': hashlib.sha256(PRED.read_bytes()).hexdigest(),
        'rule_sha256': hashlib.sha256(Path('scripts/net_tape_visibility.py').read_bytes()).hexdigest(),
        'line_px': LINE,
        'criterion': {'bright_fraction_at_least': THRESHOLD,
                      'consecutive_frames_at_least': MIN_FRAMES,
                      'box_top_motion_px_at_least': MIN_TOP_MOTION_PX},
        'source_review': ['net_cue_trial/crop_880.jpg', 'net_cue_trial/crop_886.jpg',
                          'net_cue_trial/crop_890.jpg', 'net_cue_trial/crop_900.jpg'],
        'groups': groups,
    }, indent=2) + '\n', encoding='utf-8')
    for group in groups:
        positives = [r for r in group['bright_runs'] if r['criterion_met']]
        print(group['key'], group['side'], len(group['rows']), positives)


if __name__ == '__main__':
    main()
