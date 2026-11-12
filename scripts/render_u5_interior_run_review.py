"""Render three source instants per >=5-sample live-interior ID run."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
TRACKS = SCREEN / 'dense_live_track_screen.json'
RUNS = SCREEN / 'interior_identity_run_availability.json'
OUT = SCREEN / 'interior_run_review'


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
    pages = []
    try:
        for offset in range(0, len(selected), 2):
            batch = selected[offset:offset + 2]
            sheet = np.full((2 * 395, 3 * 640, 3), 245, np.uint8)
            items = []
            for j, p in enumerate(batch):
                run = p['run_source_frames']
                chosen = [run[0], run[len(run)//2], run[-1]]
                for k, frame in enumerate(chosen):
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
                    x, y = k * 640, j * 395
                    sheet[y:y+360, x:x+640] = cv2.resize(image, (640, 360))
                    cv2.putText(sheet, f'S{p["set"]} P{p["point_number"]} f{frame} run={len(run)}',
                                (x+8, y+384), cv2.FONT_HERSHEY_SIMPLEX, .58, (20, 20, 20), 1)
                items.append({'set': p['set'], 'point_number': p['point_number'],
                              'run_frames': run, 'displayed_frames': chosen})
            name = f'sheet_{offset // 2 + 1}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f'Could not write {path}')
            pages.append({'path': name, 'sha256': sha(path), 'items': items})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'status': 'three_instants_per_candidate_run_pending_source_review',
        'source_sha256': tracks['source_sha256'], 'tracks_sha256': sha(TRACKS),
        'run_audit_sha256': sha(RUNS), 'pages': pages}, indent=2) + '\n')
    print(f'Rendered {len(selected)} runs on {len(pages)} pages')


if __name__ == '__main__':
    main()
