"""Render 5 Hz source evidence around serve and dead-ball transitions.

The windows are driven by source-still navigation brackets, not detector
output. They are for adjudicating event timing, not automatic labels.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
BRACKETS = BASE / 'screening/coarse_phase_brackets.json'
OUT = BASE / 'screening/event_transition_review'
FPS = 30
STEP = 6
COLS = 5
ROWS = 4
CELL_W = 480
CELL_H = 295


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    brackets = json.loads(BRACKETS.read_text(encoding='utf-8'))
    if digest(VIDEO) != brackets['source_sha256']:
        raise ValueError('Source video differs from phase brackets')
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    entries = []
    try:
        for point in brackets['points']:
            key = point['set'], point['point_number']
            for event, earlier, later in (
                ('serve', point['last_obvious_pre_play_frame'], point['first_obvious_active_frame']),
                ('dead', point['last_obvious_active_frame'], point['first_obvious_post_play_frame']),
            ):
                start = max(point['clip_start_frame_inclusive'], earlier - STEP)
                stop = min(point['clip_end_frame_exclusive'] - 1, later + STEP)
                frames = list(range(start, stop + 1, STEP))
                if frames[-1] != stop:
                    frames.append(stop)
                pages = []
                for page_no, offset in enumerate(range(0, len(frames), COLS * ROWS), 1):
                    page_frames = frames[offset:offset + COLS * ROWS]
                    sheet = np.full((ROWS * CELL_H, COLS * CELL_W, 3), 242, np.uint8)
                    for i, frame_no in enumerate(page_frames):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                        ok, frame = cap.read()
                        if not ok:
                            raise RuntimeError(f'Could not decode source frame {frame_no}')
                        row, col = divmod(i, COLS)
                        x, y = col * CELL_W, row * CELL_H
                        sheet[y:y + 270, x:x + CELL_W] = cv2.resize(frame, (CELL_W, 270),
                                                                      interpolation=cv2.INTER_AREA)
                        label = f'{frame_no / FPS:.3f}s f{frame_no}'
                        if frame_no == earlier:
                            label += ' EARLIER'
                        if frame_no == later:
                            label += ' LATER'
                        cv2.putText(sheet, label, (x + 5, y + 289),
                                    cv2.FONT_HERSHEY_SIMPLEX, .55, (20, 20, 20), 1)
                    name = f's{key[0]}_p{key[1]:02d}_{event}_{page_no}.jpg'
                    path = OUT / name
                    if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92]):
                        raise RuntimeError(f'Could not save {path}')
                    pages.append({'path': name, 'sha256': digest(path),
                                  'first_frame': page_frames[0], 'last_frame': page_frames[-1]})
                entries.append({'set': key[0], 'point_number': key[1], 'event': event,
                                'earlier_navigation_frame': earlier,
                                'later_navigation_frame': later,
                                'sampled_source_frames': frames, 'pages': pages})
    finally:
        cap.release()
    result = {'status': 'five_hz_event_transition_source_review_pack',
              'source_sha256': brackets['source_sha256'],
              'coarse_brackets_sha256': digest(BRACKETS),
              'event_windows': len(entries), 'entries': entries}
    (OUT / 'index.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Rendered {len(entries)} event windows on {sum(len(r['pages']) for r in entries)} sheets")


if __name__ == '__main__':
    main()
