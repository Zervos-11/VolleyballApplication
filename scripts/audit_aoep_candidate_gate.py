"""Diagnose a provisional court gate on frozen AoEP boxes without assigning teams."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
VIDEO = MATCH / 'source_AoEP-YiWRvc.mp4'
CALIBRATION = MATCH / 'pilot/calibration/near_court_candidate.json'
RAW = ROOT / 'data/processed/aoep_new_source/raw_74880_75540.json'
OUT = ROOT / 'data/processed/aoep_new_source/court_gate_diagnostic.json'
SAMPLE_FRAMES = (74970, 75180, 75280)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def category(x, y):
    if 0 <= x <= 9 and 0 <= y <= 9:
        return 'strict_near_region'
    if -.5 <= x <= 9.5 and -.5 <= y <= 9.5:
        return 'boundary_band_unresolved'
    if 0 <= x <= 9 and 9 < y <= 16:
        return 'beyond_projected_net_unresolved'
    return 'other_unresolved'


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(VIDEO):
        raise ValueError('Frozen predictions do not match source video')
    if calibration['use_for_metrics'] is not False:
        raise ValueError('Expected an exploratory calibration candidate')
    matrix = cv2.getPerspectiveTransform(np.asarray(calibration['points_px'], np.float32),
                                         np.asarray(calibration['points_court_m'], np.float32))
    totals = Counter()
    frames = {}
    samples = {}
    for frame, boxes in raw['predictions'].items():
        if boxes:
            feet = np.asarray([[[(box['bbox'][0] + box['bbox'][2]) / 2,
                                 box['bbox'][3]] for box in boxes]], np.float32)
            projected = cv2.perspectiveTransform(feet, matrix)[0]
        else:
            projected = []
        counts = Counter()
        rows = []
        for box, (x, y) in zip(boxes, projected):
            status = category(float(x), float(y))
            counts[status] += 1
            if int(frame) in SAMPLE_FRAMES:
                rows.append({'track_id': box['track_id'], 'bbox': box['bbox'],
                             'court_xy_m_from_box_bottom': [round(float(x), 3), round(float(y), 3)],
                             'region_diagnostic': status})
        totals.update(counts)
        frames[frame] = dict(counts)
        if int(frame) in SAMPLE_FRAMES:
            samples[frame] = rows
    payload = {
        'status': 'geometry_diagnostic_not_team_predictions',
        'source_sha256': raw['source_sha256'], 'raw_sha256': sha256(RAW),
        'calibration_candidate_sha256': sha256(CALIBRATION),
        'method': 'Project frozen detector-box bottom centers through the unverified court candidate. Geometry categories are not team labels; airborne and partially visible people can project beyond the net or sidelines.',
        'thresholds_m': {'strict_near': [0, 9, 0, 9],
                         'boundary_band': [-.5, 9.5, -.5, 9.5],
                         'net_side_unresolved_y': [9, 16]},
        'totals': dict(totals), 'per_frame_counts': frames, 'sample_rows': samples,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    colors = {'strict_near_region': (0, 220, 0),
              'boundary_band_unresolved': (0, 210, 255),
              'beyond_projected_net_unresolved': (255, 160, 0),
              'other_unresolved': (125, 125, 125)}
    try:
        for frame in SAMPLE_FRAMES:
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(frame)
            for row in samples[str(frame)]:
                x1, y1, x2, y2 = map(lambda n: int(round(n)), row['bbox'])
                color = colors[row['region_diagnostic']]
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                cv2.putText(image, str(row['track_id']), (x1, max(20, y1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, color, 2, cv2.LINE_AA)
            path = OUT.parent / f'court_gate_diagnostic_{frame}.jpg'
            if path.exists():
                raise FileExistsError(path)
            if not cv2.imwrite(str(path), image):
                raise OSError(path)
    finally:
        video.release()
    print('Frozen boxes:', sum(totals.values()), dict(totals))
    for frame in SAMPLE_FRAMES:
        print(frame, frames[str(frame)])


if __name__ == '__main__':
    main()
