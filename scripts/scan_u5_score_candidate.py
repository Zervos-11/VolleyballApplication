"""Make a provisional second-by-second score scan for the elevated source.

The minute labels are manually read calibration examples. This is a candidate
reader, not an independent score or point-winner validation.
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
OUT = BASE / 'screening/score_second_candidate.json'
CELLS = [(590, 612), (611, 633), (650, 672), (671, 693)]
REFERENCE = {
    0: (0, 0), 60: (3, 2), 120: (7, 4), 180: (12, 5),
    240: (18, 7), 300: (22, 9), 360: (24, 12), 420: (2, 0),
    480: (5, 2), 540: (7, 7), 600: (12, 9), 660: (15, 13),
    720: (19, 15), 780: (22, 17), 840: (24, 20), 900: (2, 2),
    960: (5, 3), 1020: (8, 6), 1080: (13, 8), 1140: (17, 9),
    1200: (20, 13), 1260: (22, 15),
}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def digits(score):
    return [score[0] // 10, score[0] % 10, score[1] // 10, score[1] % 10]


def masks(frame):
    return np.stack([(np.min(frame[5:36, x0:x1], axis=2) > 145)
                     for x0, x1 in CELLS])


def read_at(cap, frame_number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, frame = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
        raise RuntimeError(f'Cannot decode frame {frame_number}')
    return frame


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if digest(VIDEO) != manifest['video']['sha256']:
        raise ValueError('Source hash mismatch')
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError('Unexpected video')
    examples = defaultdict(list)
    try:
        for second, score in REFERENCE.items():
            for digit, patch in zip(digits(score), masks(read_at(cap, second * 30))):
                examples[digit].append(patch.astype(np.float32))
        if set(examples) != set(range(10)):
            raise ValueError(f'Missing calibration digit classes: {set(range(10)) - set(examples)}')
        prototypes = {digit: np.mean(patches, axis=0) for digit, patches in examples.items()}
        rows = []
        for second in range(1300):
            frame = read_at(cap, second * 30)
            predicted, margins = [], []
            for patch in masks(frame):
                distances = sorted((float(np.mean(np.abs(patch.astype(np.float32) - prototype))), digit)
                                   for digit, prototype in prototypes.items())
                predicted.append(distances[0][1])
                margins.append(round(distances[1][0] - distances[0][0], 4))
            score = [predicted[0] * 10 + predicted[1], predicted[2] * 10 + predicted[3]]
            rows.append({'second': second, 'source_frame': second * 30,
                         'candidate_score': score, 'digit_margin': margins})
    finally:
        cap.release()
    calibration_errors = [{'second': second, 'expected': score,
                           'read': rows[second]['candidate_score']}
                          for second, score in REFERENCE.items()
                          if tuple(rows[second]['candidate_score']) != score]
    output = {
        'status': 'provisional_template_score_scan_not_independently_audited',
        'video_id': 'u5HnY2aNW14', 'source_sha256': manifest['video']['sha256'],
        'sampling': 'one decoded frame at each integer source second',
        'cell_x_ranges_px': CELLS, 'cell_y_range_px': [5, 36],
        'calibration_scores_by_second': {str(k): v for k, v in REFERENCE.items()},
        'calibration_error_count': len(calibration_errors),
        'calibration_errors': calibration_errors,
        'rows': rows,
        'limitations': ['Calibration scores were manually read from this source.',
                        'One-second sampling can miss very short score states.',
                        'An independent audit and transition filtering are required before point winners or a frozen sample.'],
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print({'rows': len(rows), 'calibration_errors': len(calibration_errors),
           'minimum_digit_margin': min(min(row['digit_margin']) for row in rows)})


if __name__ == '__main__':
    main()
