"""Inspect every bracketed six-box proposal at the corrected S1 P37 failure."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
OUT = SCREEN / 's1p37_replacement_review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    core_path = SCREEN / 'cut_bounded_provisional_rally_metrics.json'
    tracks_path = SCREEN / 'dense_live_track_screen.json'
    bracket_path = SCREEN / 'coarse_phase_brackets.json'
    core = json.loads(core_path.read_text(encoding='utf-8'))
    tracks = json.loads(tracks_path.read_text(encoding='utf-8'))
    bracket = json.loads(bracket_path.read_text(encoding='utf-8'))
    point = next(x for x in core['points'] if (x['set'], x['point_number']) == (1, 37))
    bound = next(x for x in bracket['points'] if (x['set'], x['point_number']) == (1, 37))
    candidates = [x['source_frame'] for x in point['frames']
                  if bound['first_obvious_active_frame'] <= x['source_frame'] <=
                  bound['last_obvious_active_frame']]
    rows = {x['source_frame']: x for x in next(x for x in tracks['points']
                                               if (x['set'], x['point_number']) == (1, 37))['rows']}
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(BASE / 'source_720p.mp4'))
    pages = []
    try:
        for offset in range(0, len(candidates), 12):
            batch = candidates[offset:offset + 12]
            sheet = np.full((3 * 300, 4 * 640, 3), 245, np.uint8)
            for i, frame in enumerate(batch):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f'Could not read {frame}')
                for box in rows[frame]['proposals']:
                    if box['net_side_status'] != 'near_floor_side_candidate':
                        continue
                    x1, y1, x2, y2 = map(round, box['bbox_px'])
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 190, 0), 2)
                    cv2.putText(image, str(box['raw_track_id']), (x1, max(20, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 190, 0), 2)
                x, y = (i % 4) * 640, (i // 4) * 300
                sheet[y:y + 275, x:x + 640] = cv2.resize(image[:550], (640, 275))
                cv2.putText(sheet, f'f{frame} {frame / 30:.1f}s', (x + 5, y + 295),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (20, 20, 20), 1)
            name = f'page_{offset // 12 + 1}.jpg'
            path = OUT / name
            cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95])
            pages.append({'path': name, 'sha256': sha(path), 'frames': batch})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({'source_sha256': tracks['source_sha256'],
                                                'core_sha256': sha(core_path),
                                                'brackets_sha256': sha(bracket_path),
                                                'pages': pages}, indent=2) + '\n')
    print(f'Rendered {len(candidates)} candidate frames on {len(pages)} pages')


if __name__ == '__main__':
    main()
