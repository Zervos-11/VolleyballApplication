"""Cross-check the disputed set-one frame alignment with independent methods."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_image_alignment_diagnostic'
REFERENCE = 21270
TARGETS = (36366, 65656, 65910, 66165)


def frame_at(cap, index):
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != index + 1:
        raise RuntimeError(index)
    return frame


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Video unavailable')
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        ref = frame_at(cap, REFERENCE)
        rows = []
        for index in TARGETS:
            target = frame_at(cap, index)
            # Large, stationary wall patch away from overlays, net and floor.
            a = cv2.cvtColor(ref[190:590, 230:1690], cv2.COLOR_BGR2GRAY).astype(np.float32)
            b = cv2.cvtColor(target[190:590, 230:1690], cv2.COLOR_BGR2GRAY).astype(np.float32)
            window = cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F)
            shift, response = cv2.phaseCorrelate(a, b, window)
            # ECC uses a different intensity-based objective. Translation only.
            warp = np.eye(2, 3, dtype=np.float32)
            try:
                score, warp = cv2.findTransformECC(
                    cv2.GaussianBlur(a, (5, 5), 0), cv2.GaussianBlur(b, (5, 5), 0),
                    warp, cv2.MOTION_TRANSLATION,
                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 250, 1e-7))
                ecc = {'status': 'converged', 'score': round(float(score), 5),
                       'reference_to_target_dx_px': round(float(warp[0, 2]), 3),
                       'reference_to_target_dy_px': round(float(warp[1, 2]), 3)}
            except cv2.error as exc:
                ecc = {'status': 'failed', 'reason': str(exc).splitlines()[0]}
            rows.append({'reference_frame': REFERENCE, 'target_frame': index,
                         'phase_correlation_shift_px': [round(float(v), 3) for v in shift],
                         'phase_correlation_response': round(float(response), 4),
                         'ecc': ecc})
            # Interleaved wall strips expose any genuine feature offset directly.
            checker = np.empty_like(ref[190:590, 230:1690])
            for left in range(0, checker.shape[1], 80):
                width = min(80, checker.shape[1] - left)
                checker[:, left:left + 80] = (ref if left // 80 % 2 == 0 else target)[
                    190:590, 230 + left:230 + left + width]
            cv2.imwrite(str(OUT / f'wall_checker_{index}.jpg'), checker,
                        [cv2.IMWRITE_JPEG_QUALITY, 93])
    finally:
        cap.release()
    (OUT / 'diagnostic.json').write_text(json.dumps({
        'source_sha256': source['sha256'], 'method':
        'Independent wall intensity registration by phase correlation and ECC translation; checkerboard reveals direct source-pixel differences.',
        'rows': rows}, indent=2) + '\n', encoding='utf-8')
    for row in rows:
        print(row)


if __name__ == '__main__':
    main()
