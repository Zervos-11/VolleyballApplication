"""Render first, median and last box candidates per provisional clip-core point."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
TRACKS = BASE / 'screening/dense_live_track_screen.json'
METRICS = BASE / 'screening/cut_bounded_provisional_rally_metrics.json'
OUT = BASE / 'screening/provisional_core_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    result = json.loads(METRICS.read_text(encoding='utf-8'))
    if result['dense_tracks_sha256'] != digest(TRACKS):
        raise ValueError('Provisional result does not match dense tracks')
    track_lookup = {(p['set'], p['point_number']): {r['source_frame']: r for r in p['rows']}
                    for p in tracks['points']}
    points = [r for r in result['points'] if r['provisional_candidate_frames']]
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    pages = []
    try:
        for offset in range(0, len(points), 2):
            sheet = np.full((2 * 395, 3 * 640, 3), 240, np.uint8)
            for row_no, point in enumerate(points[offset:offset + 2]):
                candidates = point['frames']
                chosen = [candidates[0], candidates[len(candidates) // 2], candidates[-1]]
                for col_no, entry in enumerate(chosen):
                    frame_no = entry['source_frame']
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                    ok, image = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode frame {frame_no}')
                    row = track_lookup[point['set'], point['point_number']][frame_no]
                    cv2.line(image, (297, 313), (1046, 313), (0, 255, 255), 2)
                    for proposal in row['proposals']:
                        x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                        color = ((0, 190, 0) if proposal['net_side_status'] ==
                                 'near_floor_side_candidate' else (0, 0, 255))
                        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(image, str(proposal['raw_track_id']),
                                    (x1, max(25, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                                    .6, color, 2)
                    x, y = col_no * 640, row_no * 395
                    sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                               interpolation=cv2.INTER_AREA)
                    cv2.putText(sheet, f"S{point['set']} P{point['point_number']} "
                                f"{frame_no / 30:.1f}s n={len(candidates)}",
                                (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX,
                                .6, (20, 20, 20), 1)
            name = f'sheet_{offset // 2 + 1}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Could not save {path}')
            pages.append({'path': name, 'sha256': digest(path),
                          'points': [{'set': r['set'], 'point_number': r['point_number']}
                                     for r in points[offset:offset + 2]]})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({'source_sha256': tracks['source_sha256'],
                                                'metrics_sha256': digest(METRICS),
                                                'pages': pages}, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(pages)} provisional core review sheets')


if __name__ == '__main__':
    main()
