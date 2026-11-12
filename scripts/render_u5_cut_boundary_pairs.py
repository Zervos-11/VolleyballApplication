"""Render before/after frames for the selected edited rally clip cuts."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
REGISTER = BASE / 'screening/rally_cut_clip_register.json'
OUT = BASE / 'screening/rally_cut_boundary_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(REGISTER.read_text(encoding='utf-8'))
    if len(data['selected_clips']) != 18:
        raise ValueError('Expected 18 selected clips')
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    pages = []
    try:
        for offset in range(0, 18, 3):
            sheet = np.full((3 * 240, 4 * 400, 3), 245, np.uint8)
            group = data['selected_clips'][offset:offset + 3]
            for row_no, item in enumerate(group):
                start = item['clip_start_frame_inclusive']
                end = item['clip_end_frame_exclusive']
                frames = (max(0, start - 1), start, end - 1, end)
                for col_no, frame_no in enumerate(frames):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode frame {frame_no}')
                    x, y = col_no * 400, row_no * 240
                    sheet[y:y + 225, x:x + 400] = cv2.resize(frame, (400, 225))
                    label = ('start-' if col_no == 0 else 'start+' if col_no == 1 else
                             'end-' if col_no == 2 else 'end+')
                    cv2.putText(sheet, f"S{item['set']} P{item['point_number']} {label} f{frame_no}",
                                (x + 4, y + 237), cv2.FONT_HERSHEY_SIMPLEX,
                                .48, (20, 20, 20), 1)
            name = f'sheet_{offset // 3 + 1}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Could not save {path}')
            pages.append({'path': name, 'sha256': digest(path),
                          'points': [{'set': r['set'], 'point_number': r['point_number']}
                                     for r in group]})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({'source_sha256': data['source_sha256'],
                                                'clip_register_sha256': digest(REGISTER),
                                                'pages': pages,
                                                'review_rule': 'Four source frames per selected clip: before and after each hard-cut boundary'},
                                               indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(pages)} cut-boundary sheets')


if __name__ == '__main__':
    main()
