"""Render first/middle/last source frames of each longest stable raw-ID run."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
TRACKS = BASE / 'screening/dense_live_track_screen.json'
AUDIT = BASE / 'screening/dense_live_continuity_audit.json'
OUT = BASE / 'screening/dense_continuity_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    if audit['dense_track_screen_sha256'] != digest(TRACKS):
        raise ValueError('Audit and tracks differ')
    lookup = {(p['set'], p['point_number']): p for p in tracks['points']}
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    sheets = []
    try:
        points = audit['points']
        for offset in range(0, len(points), 2):
            sheet = np.full((2 * 395, 3 * 640, 3), 240, np.uint8)
            for row_index, item in enumerate(points[offset:offset + 2]):
                run = item['longest_consecutive_exact_six_same_raw_ids']
                first, last = run['first_frame'], run['last_frame']
                frames = [first, first + ((last - first) // 12) * 6, last]
                source_rows = {r['source_frame']: r for r in
                               lookup[item['set'], item['point_number']]['rows']}
                for col, frame_number in enumerate(frames):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    ok, image = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode {frame_number}')
                    cv2.line(image, (297, 313), (1046, 313), (0, 255, 255), 2)
                    for proposal in source_rows[frame_number]['proposals']:
                        x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                        color = ((0, 190, 0) if proposal['net_side_status'] ==
                                 'near_floor_side_candidate' else (0, 0, 255))
                        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(image, str(proposal['raw_track_id']),
                                    (x1, max(25, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                                    .55, color, 2)
                    x, y = col * 640, row_index * 395
                    sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                               interpolation=cv2.INTER_AREA)
                    cv2.putText(sheet, f"S{item['set']} P{item['point_number']} "
                                f"frame {frame_number} run={run['frames']}",
                                (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX,
                                .6, (20, 20, 20), 1)
            name = f'sheet_{offset // 2 + 1}.jpg'
            if not cv2.imwrite(str(OUT / name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                raise RuntimeError(f'Could not save {name}')
            sheets.append(name)
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'tracks_sha256': digest(TRACKS), 'audit_sha256': digest(AUDIT),
        'video_sha256': digest(VIDEO), 'sheets': sheets,
        'review_basis': 'Three frames from the longest exact-six same-raw-ID run per selected point'
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(sheets)} sheets')


if __name__ == '__main__':
    main()
