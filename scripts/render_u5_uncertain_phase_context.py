"""Render a five-second source strip around each unresolved selected U5 phase."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
QC = BASE / 'screening/selected_phase_source_qc.json'
OUT = BASE / 'screening/phase_six_candidate_review/uncertain_context'
REVIEWED_KEYS = {(1, 5), (1, 18), (1, 27), (1, 34), (3, 11), (3, 27)}


def main():
    qc = json.loads(QC.read_text(encoding='utf-8'))
    points = [r for r in qc['rows'] if (r['set'], r['point_number']) in REVIEWED_KEYS]
    if len(points) != len(REVIEWED_KEYS):
        raise ValueError('Missing a scheduled extended-context review point')
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    try:
        for point in points:
            sheet = np.full((2 * 395, 3 * 640, 3), 240, np.uint8)
            for i, delta in enumerate((-60, -30, 0, 30, 60)):
                frame = point['source_frame'] + delta
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f'Could not decode frame {frame}')
                x, y = (i % 3) * 640, (i // 3) * 395
                sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                           interpolation=cv2.INTER_AREA)
                cv2.putText(sheet, f"S{point['set']} P{point['point_number']} "
                            f"frame {frame} {frame / 30:.2f}s", (x + 6, y + 382),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (20, 20, 20), 1)
            name = f"s{point['set']}_p{point['point_number']}.jpg"
            if not cv2.imwrite(str(OUT / name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Could not save {name}')
    finally:
        cap.release()
    print(f'Rendered {len(points)} uncertain phase strips')


if __name__ == '__main__':
    main()
