"""Render short source-video motion strips around phase/six candidates."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
SELECTION = BASE / 'screening/phase_six_candidate_review/selected.json'
OUT = BASE / 'screening/phase_six_candidate_review/context'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(SELECTION.read_text(encoding='utf-8'))
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    sheets = []
    try:
        for offset in range(0, len(data['selected']), 2):
            sheet = np.full((2 * 395, 3 * 640, 3), 240, np.uint8)
            points = data['selected'][offset:offset + 2]
            for row_index, point in enumerate(points):
                for col, delta in enumerate((-12, 0, 12)):
                    frame_number = point['source_frame'] + delta
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    ok, image = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode frame {frame_number}')
                    x, y = col * 640, row_index * 395
                    sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                               interpolation=cv2.INTER_AREA)
                    cv2.putText(sheet, f"S{point['set']} P{point['point_number']} "
                                f"frame {frame_number} t={frame_number / 30:.2f}s",
                                (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX,
                                .58, (20, 20, 20), 1)
            name = f'context_{offset // 2 + 1}.jpg'
            if not cv2.imwrite(str(OUT / name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Could not save {name}')
            sheets.append(name)
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'selection_sha256': digest(SELECTION), 'source_sha256': digest(VIDEO),
        'offset_frames': [-12, 0, 12], 'sheets': sheets
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(sheets)} context sheets')


if __name__ == '__main__':
    main()
