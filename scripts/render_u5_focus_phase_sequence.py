"""Render source frame sequences around ambiguous U5 point phases."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
SELECTION = BASE / 'screening/phase_six_candidate_review/selected.json'
SAMPLE = BASE / 'screening/rally_sample_score_only.json'
OUT = BASE / 'screening/focus_phase_sequence'
WINDOWS = {
    (1, 5): (45.0, 51.0),
    (1, 34): (320.0, 328.0),
    (3, 11): (974.0, 980.0),
    (3, 23): (1090.0, 1094.0),
    (2, 14): (533.0, 538.0),
    (2, 28): (648.0, 653.0),
    (3, 34): (1200.0, 1205.0),
}


def main():
    selection = json.loads(SELECTION.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    video_hash = hashlib.sha256()
    with VIDEO.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            video_hash.update(chunk)
    if video_hash.hexdigest() != sample['source_sha256']:
        raise ValueError('Local source video does not match the frozen sample')
    rows = {(r['set'], r['point_number']): r for r in selection['selected']}
    if not set(WINDOWS) <= set(rows):
        raise ValueError('Missing phase-QC point')
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    index = []
    try:
        for (set_no, point_no), (start_s, stop_s) in WINDOWS.items():
            frames = list(range(round(start_s * 30), round(stop_s * 30) + 1, 6))
            for page_no, offset in enumerate(range(0, len(frames), 20), 1):
                page = frames[offset:offset + 20]
                sheet = np.full((4 * 295, 5 * 480, 3), 245, np.uint8)
                for i, frame_no in enumerate(page):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode source frame {frame_no}')
                    y, x = divmod(i, 5)
                    x *= 480
                    y *= 295
                    sheet[y:y + 270, x:x + 480] = cv2.resize(frame, (480, 270))
                    selected = frame_no == rows[set_no, point_no]['source_frame']
                    color = (0, 0, 200) if selected else (30, 30, 30)
                    cv2.putText(sheet, f'{frame_no / 30:.1f}s f{frame_no}' + (' SELECTED' if selected else ''),
                                (x + 5, y + 289), cv2.FONT_HERSHEY_SIMPLEX, .55, color, 1)
                name = f's{set_no}_p{point_no:02d}_{page_no}.jpg'
                path = OUT / name
                if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 91]):
                    raise RuntimeError(f'Could not save {path}')
                index.append({'set': set_no, 'point_number': point_no, 'page': page_no,
                              'path': name, 'first_frame': page[0], 'last_frame': page[-1],
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({'source_sha256': sample['source_sha256'],
                                                'selection_sha256': hashlib.sha256(SELECTION.read_bytes()).hexdigest(),
                                                'windows_seconds': {f's{s}_p{p}': v for (s, p), v in WINDOWS.items()},
                                                'sheets': index}, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(index)} sequence sheets')


if __name__ == '__main__':
    main()
