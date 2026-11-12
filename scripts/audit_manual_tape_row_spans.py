"""Measure tape appearance on manually reviewed body-width spans."""

import hashlib
import json
from pathlib import Path

import cv2

from net_tape_full_box import full_box_tape_span


BASE = Path('data/processed/pilot_tracker_evaluation/net_cue_trial')
LABELS = BASE / 'manual_tape_row_spans.json'
OUT = BASE / 'manual_tape_row_audit.json'
SOURCE = Path('data/matches/yt_em6zFUxfYpc/heldout_source_cfr.mp4')
LINE = ((70, 624), (1515, 624))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    labels = json.loads(LABELS.read_text())
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    results = []
    try:
        for item in labels['examples']:
            video.set(cv2.CAP_PROP_POS_FRAMES, item['frame'])
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {item['frame']}")
            left, right = item['body_x_px']
            # Only horizontal limits matter for this row-level measure. The
            # vertical bounds simply allow the context samples around y=624.
            result = full_box_tape_span(image, [left, 580, right, 710], LINE)
            results.append({**item, 'body_row_measure': result})
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'single_reviewer_development_examples',
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'labels_sha256': hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        'rule_sha256': hashlib.sha256(Path('scripts/net_tape_full_box.py').read_bytes()).hexdigest(),
        'line_px': LINE,
        'scope': 'Five single-frame horizontal body-width annotations; no sequence-level segmentation or team classification.',
        'results': results,
    }, indent=2) + '\n', encoding='utf-8')
    for item in results:
        print(item['key'], item['side'], item['body_row_measure'])


if __name__ == '__main__':
    main()
