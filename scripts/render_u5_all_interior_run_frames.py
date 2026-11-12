"""Render every 5 Hz frame in each seven-point interior six-ID candidate run."""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
TRACKS = SCREEN / 'dense_live_track_screen.json'
RUNS = SCREEN / 'interior_identity_run_availability.json'
OUT = SCREEN / 'all_interior_run_frames'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    runs = json.loads(RUNS.read_text(encoding='utf-8'))
    assert runs['tracks_sha256'] == sha(TRACKS)
    rows = {(p['set'], p['point_number']): {r['source_frame']: r for r in p['rows']}
            for p in tracks['points']}
    selected = [p for p in runs['points'] if p['longest_same_six_raw_id_run_frames'] >= 5]
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(BASE / 'source_720p.mp4'))
    entries = []
    try:
        for p in selected:
            frames = p['run_source_frames']
            sheet = np.full((math.ceil(len(frames) / 3) * 290, 3 * 640, 3), 245, np.uint8)
            for i, frame in enumerate(frames):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode {frame}')
                for box in rows[p['set'], p['point_number']][frame]['proposals']:
                    if box['net_side_status'] != 'near_floor_side_candidate':
                        continue
                    x1, y1, x2, y2 = map(round, box['bbox_px'])
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 190, 0), 2)
                    cv2.putText(image, str(box['raw_track_id']), (x1, max(25, y1-5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 190, 0), 2)
                x, y = (i % 3) * 640, (i // 3) * 290
                sheet[y:y+270, x:x+640] = cv2.resize(image[:540], (640, 270))
                cv2.putText(sheet, f'S{p["set"]} P{p["point_number"]} f{frame}',
                            (x+8, y+285), cv2.FONT_HERSHEY_SIMPLEX, .58, (20, 20, 20), 1)
            name = f's{p["set"]}_p{p["point_number"]:02d}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f'Could not write {path}')
            entries.append({'set': p['set'], 'point_number': p['point_number'],
                            'path': name, 'sha256': sha(path), 'source_frames': frames})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'status': 'all_sampled_run_frames_source_review_pack',
        'source_sha256': tracks['source_sha256'], 'tracks_sha256': sha(TRACKS),
        'run_audit_sha256': sha(RUNS), 'entries': entries}, indent=2) + '\n')
    print(f'Rendered {sum(len(x["source_frames"]) for x in entries)} frames in {len(entries)} sheets')


if __name__ == '__main__':
    main()
