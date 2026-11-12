"""Render one source frame per second throughout each frozen edited point clip.

These images are a navigation pass for finding serve and dead-ball intervals;
they do not certify the intervening frames as live play.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
CUTS = BASE / 'screening/rally_cut_clip_register.json'
OUT = BASE / 'screening/frozen_clip_phase_review'
COLS = 6
ROWS = 4
CELL_W = 400
CELL_H = 250


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cuts = json.loads(CUTS.read_text(encoding='utf-8'))
    if digest(VIDEO) != cuts['source_sha256']:
        raise ValueError('Source video differs from cut register')
    clips = cuts['selected_clips']
    if len(clips) != 18:
        raise ValueError('Expected the frozen 18-point sample')
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    index = []
    try:
        for clip in clips:
            start = clip['clip_start_frame_inclusive']
            end = clip['clip_end_frame_exclusive']
            # Exact first edit frame, then one sample at each source second,
            # and the exact last frame before the next edit.
            frames = sorted({start, end - 1} | set(range(start + 30, end, 30)))
            pages = []
            for page_no, offset in enumerate(range(0, len(frames), COLS * ROWS), 1):
                page_frames = frames[offset:offset + COLS * ROWS]
                sheet = np.full((ROWS * CELL_H, COLS * CELL_W, 3), 240, np.uint8)
                for cell, frame_no in enumerate(page_frames):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode source frame {frame_no}')
                    row, col = divmod(cell, COLS)
                    x, y = col * CELL_W, row * CELL_H
                    sheet[y:y + 225, x:x + CELL_W] = cv2.resize(frame, (CELL_W, 225),
                                                                 interpolation=cv2.INTER_AREA)
                    label = f"{frame_no / 30:.3f}s  f{frame_no}  +{(frame_no - start) / 30:.2f}s"
                    cv2.putText(sheet, label, (x + 6, y + 244),
                                cv2.FONT_HERSHEY_SIMPLEX, .52, (25, 25, 25), 1)
                name = f"s{clip['set']}_p{clip['point_number']:02d}_{page_no}.jpg"
                path = OUT / name
                if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                    raise RuntimeError(f'Could not save {path}')
                pages.append({'path': name, 'sha256': digest(path),
                              'first_frame': page_frames[0], 'last_frame': page_frames[-1]})
            index.append({'set': clip['set'], 'point_number': clip['point_number'],
                          'clip_start_frame_inclusive': start, 'clip_end_frame_exclusive': end,
                          'sampled_source_frames': frames, 'pages': pages})
    finally:
        cap.release()
    result = {'status': 'one_hz_source_navigation_not_phase_adjudication',
              'source_sha256': cuts['source_sha256'], 'cut_register_sha256': digest(CUTS),
              'point_count': len(index), 'clips': index}
    (OUT / 'index.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Rendered {len(index)} clips, {sum(len(c['sampled_source_frames']) for c in index)} frames")


if __name__ == '__main__':
    main()
