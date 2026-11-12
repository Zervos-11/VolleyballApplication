"""Render source stills for winning points with no six-ID interior run."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
OUT = SCREEN / 'zero_run_source_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs_path = SCREEN / 'interior_identity_run_availability.json'
    intervals_path = SCREEN / 'event_transition_source_qc.json'
    runs = json.loads(runs_path.read_text(encoding='utf-8'))
    intervals = json.loads(intervals_path.read_text(encoding='utf-8'))
    by_point = {(p['set'], p['point_number']): p for p in intervals['points']}
    selected = [p for p in runs['points'] if p['near_team_won'] and not p['run_source_frames']]
    assert len(selected) == 3
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(BASE / 'source_720p.mp4'))
    entries = []
    try:
        for point in selected:
            key = point['set'], point['point_number']
            interval = by_point[key]
            start = interval['conservative_interior_start_frame_inclusive']
            end = interval['conservative_interior_end_frame_exclusive']
            frames = list(range(start, end, 5))
            if end - 1 not in frames:
                frames.append(end - 1)
            sheet = np.full((len(frames) * 376, 640, 3), 245, np.uint8)
            for i, frame in enumerate(frames):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode frame {frame}')
                sheet[i*376:i*376+360] = cv2.resize(image, (640, 360))
                cv2.putText(sheet, f'S{key[0]} P{key[1]} f{frame}', (8, i*376+372),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (20, 20, 20), 1)
            name = f's{key[0]}_p{key[1]:02d}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f'Cannot write {path}')
            entries.append({'set': key[0], 'point_number': key[1], 'source_frames': frames,
                            'sheet': name, 'sha256': digest(path)})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'status': 'source_only_full_image_stills_no_detector_boxes',
        'source_sha256': runs['source_sha256'], 'runs_sha256': digest(runs_path),
        'intervals_sha256': digest(intervals_path), 'entries': entries,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {sum(len(e["source_frames"]) for e in entries)} source stills')


if __name__ == '__main__':
    main()
