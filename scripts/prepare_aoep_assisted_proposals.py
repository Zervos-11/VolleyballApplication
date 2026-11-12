"""Expose frozen AoEP tracker boxes as optional, unverified review suggestions."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
RAW = ROOT / 'data/processed/aoep_new_source/raw_74880_75540.json'
OUT = MATCH / 'pilot/assisted_proposals/point_21m.json'


def main():
    selection = json.loads((MATCH / 'pilot/selection.json').read_text(encoding='utf-8'))
    raw_bytes = RAW.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != selection['raw_prediction_sha256']:
        raise ValueError('Frozen tracker file changed')
    raw = json.loads(raw_bytes)
    if raw['source_sha256'] != selection['source_sha256']:
        raise ValueError('Tracker source does not match selected video')
    rally = selection['rallies'][0]
    frames = {}
    for frame in range(rally['start_frame'], rally['end_frame_exclusive']):
        rows = raw['predictions'][str(frame)]
        frames[str(frame)] = [
            {'proposal_id': f'raw_{frame}_{index}', 'bbox': row['bbox'],
             'raw_track_id': row['track_id'], 'confidence': row['confidence']}
            for index, row in enumerate(rows)
        ]
    payload = {
        'status': 'unverified_frozen_tracker_suggestions',
        'match_id': selection['match_id'], 'rally_id': rally['rally_id'],
        'source_sha256': selection['source_sha256'],
        'raw_prediction_sha256': selection['raw_prediction_sha256'],
        'frame_range_inclusive': [rally['start_frame'], rally['end_frame_exclusive'] - 1],
        'interpretation': 'Boxes include both teams and other people. A raw track ID is not a player ID. Selecting or viewing these suggestions makes the resulting frame assisted review material, not independent ground truth.',
        'frames': frames,
    }
    if OUT.exists():
        if json.loads(OUT.read_text(encoding='utf-8')) != payload:
            raise ValueError(f'Refusing to overwrite existing proposals: {OUT}')
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {len(frames)} frames, {sum(map(len, frames.values()))} unverified boxes')


if __name__ == '__main__':
    main()
