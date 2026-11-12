"""Freeze dense raw tracker boxes around the two partly visible rally starts."""

import hashlib
import json
import os
from pathlib import Path

from evaluate_pilot_tracker import track_rally


MATCH = Path('data/matches/yt_FqE5pTJqx8g')
OUT = Path('data/processed/pilot_tracker_evaluation/start_boundary_audit')
INTERVALS = {'r3': (96550, 96670), 'r5': (176240, 176340)}


def main():
    os.environ['YOLO_CONFIG_DIR'] = str(Path('data/processed/ultralytics_config').resolve())
    model = Path('yolov8n.pt')
    model_hash = hashlib.sha256(model.read_bytes()).hexdigest()
    source = MATCH / 'source_FqE5pTJqx8g.mp4'
    for rally, (first, last) in INTERVALS.items():
        out = OUT / f'{rally}_first_visibility_dense_raw.json'
        if out.exists():
            raise FileExistsError(out)
        saved = {'start_frame': first, 'end_frame_exclusive': last + 1,
                 'frames': {str(frame): None for frame in range(first, last + 1)}}
        result = track_rally(model, model_hash, source, rally, saved, out)
        print(rally, len(result['predictions']),
              sum(map(len, result['predictions'].values())), flush=True)


if __name__ == '__main__':
    main()
