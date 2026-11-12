"""Draw staged court lines on exact R2 frames for a source calibration check."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json'
MANIFEST = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/calibration_manifest.json'
OUT = ROOT / 'data/processed/honours_r2_calibration_spotcheck'
FRAMES = (78050, 78100, 78400)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, calibration, manifest = read(SOURCE), read(CALIBRATION), read(MANIFEST)
    pixels = np.asarray(calibration['points_px'], np.float32)
    court = np.asarray(calibration['points_court_m'], np.float32)
    inverse = cv2.getPerspectiveTransform(court, pixels)
    forward = cv2.getPerspectiveTransform(pixels, court)

    def image_point(x_m, y_m):
        return tuple(map(round, cv2.perspectiveTransform(
            np.asarray([[[x_m, y_m]]], np.float32), inverse)[0, 0]))

    def draw_court(frame):
        lines = [((0, 0), (9, 0), (20, 190, 20), 'baseline'),
                 ((0, 6), (9, 6), (0, 230, 230), 'attack'),
                 ((0, 9), (9, 9), (20, 20, 230), 'net floor'),
                 ((0, 0), (0, 9), (20, 190, 20), 'left side'),
                 ((9, 0), (9, 9), (20, 190, 20), 'right side')]
        for start, end, color, _ in lines:
            cv2.line(frame, image_point(*start), image_point(*end), color, 3)
        return frame

    heldout = manifest['camera_segments']['camera_r2_r5']['heldout_net_line_px']
    x1, y1, x2, y2 = heldout
    projected = cv2.perspectiveTransform(np.asarray(
        [[[x1, y1]], [[x2, y2]]], np.float32), forward)[:, 0, :]
    (court_x1, court_y1), (court_x2, court_y2) = projected
    sample = []
    for x_m in (0, 2.25, 4.5, 6.75, 9):
        y_m = court_y1 + (x_m - court_x1) * (court_y2 - court_y1) / (court_x2 - court_x1)
        sample.append({'court_x_m': x_m, 'court_y_m': round(float(y_m), 3),
                       'net_depth_residual_m': round(float(y_m - 9), 3)})

    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    images = {}
    try:
        for frame_number in FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
                raise RuntimeError(f'Could not decode exact frame {frame_number}')
            frame = draw_court(frame)
            cv2.putText(frame, str(frame_number), (40, 70), cv2.FONT_HERSHEY_SIMPLEX,
                        1.8, (0, 0, 255), 4)
            path = OUT / f'court_{frame_number}.jpg'
            if not cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 96]):
                raise RuntimeError(f'Could not write {path}')
            images[str(frame_number)] = {'file': str(path.relative_to(ROOT)),
                                         'sha256': sha(path)}
    finally:
        cap.release()
    result = {'status': 'exact_source_frame_calibration_spotcheck_not_metric_validation',
              'source_sha256': source['sha256'],
              'calibration_sha256': sha(CALIBRATION),
              'calibration_manifest_sha256': sha(MANIFEST),
              'frames': images, 'heldout_net_line_samples': sample,
              'limitations': ['The held-out net line is one landmark, not independent player-floor error.',
                              'Visual agreement on three frames does not validate all rally frames.',
                              'The source points were fitted to the baseline and attack line.']}
    path = OUT / 'spotcheck.json'
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
