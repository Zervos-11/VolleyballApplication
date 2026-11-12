"""Show existing and camera-registered court lines on exact source frames."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
STABILITY = ROOT / 'data/processed/honours_camera_stability_audit.json'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration'
OUT = ROOT / 'data/processed/honours_court_alignment_sheets'
FRAMES = (8643, 15505, 19345, 36366, 65656, 66165,
          78050, 90335, 102259, 155290, 187701, 205154)
COURT_LINES = ((0, 0, 9, 0), (0, 6, 9, 6), (0, 9, 9, 9),
               (0, 0, 0, 9), (9, 0, 9, 9))


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, stability = read(SOURCE), read(STABILITY)
    if source['sha256'] != stability['source_sha256']:
        raise ValueError('Registration belongs to a different source')
    rows = {r['frame']: r for r in stability['rows']}
    cameras = {}
    for s in (1, 2, 3):
        path = CALIBRATION / ('camera_r1.json' if s == 1 else 'camera_r2_r5.json')
        data = read(path)
        cameras[s] = (cv2.getPerspectiveTransform(
            np.float32(data['points_court_m']), np.float32(data['points_px'])), sha(path))
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Video unavailable')
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    try:
        for number in FRAMES:
            row = rows[number]
            if row['status'] != 'registered':
                raise ValueError(f'No stable registration for {number}')
            cap.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                raise RuntimeError(f'Could not decode exact frame {number}')
            inverse, cal_hash = cameras[row['set']]
            affine = np.float32(row['affine_ref_to_target'])
            for x1, y1, x2, y2 in COURT_LINES:
                image_points = cv2.perspectiveTransform(
                    np.float32([[[x1, y1]], [[x2, y2]]]), inverse)[:, 0, :]
                original = [tuple(map(round, p)) for p in image_points]
                shifted = [tuple(map(round, p)) for p in image_points @ affine[:, :2].T + affine[:, 2]]
                cv2.line(frame, *original, (0, 0, 255), 3)
                cv2.line(frame, *shifted, (0, 230, 0), 3)
            cv2.putText(frame, f'frame {number}: red existing, green wall-registered',
                        (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 5, cv2.LINE_AA)
            cv2.putText(frame, f'frame {number}: red existing, green wall-registered',
                        (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
            path = OUT / f'court_{number}.jpg'
            cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 94])
            manifest.append({'set': row['set'], 'point_number': row['point_number'],
                             'frame': number, 'file': str(path.relative_to(ROOT)).replace('\\', '/'),
                             'sha256': sha(path), 'calibration_sha256': cal_hash,
                             'camera_registration': row})
    finally:
        cap.release()
    (OUT / 'manifest.json').write_text(json.dumps({
        'status': 'visual_alignment_sheets_not_measured_landmark_error',
        'source_sha256': source['sha256'], 'stability_sha256': sha(STABILITY),
        'rows': manifest}, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(manifest)} court alignment sheets')


if __name__ == '__main__':
    main()
