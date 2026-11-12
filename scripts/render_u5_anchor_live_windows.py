"""Render source evidence for live-anchor six-ID runs of at least five samples."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
TRACKS = BASE / 'screening/dense_live_track_screen.json'
AUDIT = BASE / 'screening/anchor_live_window_availability.json'
OUT = BASE / 'screening/anchor_live_window_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    if audit['dense_tracks_sha256'] != digest(TRACKS):
        raise ValueError('Anchor window audit does not match dense tracks')
    lookup = {(p['set'], p['point_number']): {r['source_frame']: r for r in p['rows']}
              for p in tracks['points']}
    runs = [r for r in audit['rows'] if r['anchor_phase'] == 'visible_live_play'
            and r['sampled_frames_in_run'] >= 5]
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    index = []
    try:
        for offset in range(0, len(runs), 2):
            sheet = np.full((2 * 395, 3 * 640, 3), 240, np.uint8)
            for row_index, item in enumerate(runs[offset:offset + 2]):
                first, last = item['first_sampled_frame'], item['last_sampled_frame']
                mid = first + ((last - first) // 12) * 6
                for col, frame_number in enumerate((first, mid, last)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    ok, image = cap.read()
                    if not ok:
                        raise RuntimeError(f'Could not decode {frame_number}')
                    cv2.line(image, (297, 313), (1046, 313), (0, 255, 255), 2)
                    row = lookup[item['set'], item['point_number']][frame_number]
                    for proposal in row['proposals']:
                        x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                        is_anchor_id = proposal['raw_track_id'] in item['raw_track_ids']
                        color = (0, 190, 0) if is_anchor_id else (0, 0, 255)
                        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(image, str(proposal['raw_track_id']),
                                    (x1, max(25, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                                    .6, color, 2)
                    x, y = col * 640, row_index * 395
                    sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                               interpolation=cv2.INTER_AREA)
                    cv2.putText(sheet, f"S{item['set']} P{item['point_number']} "
                                f"{frame_number / 30:.1f}s run={item['sampled_frames_in_run']}",
                                (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX,
                                .6, (20, 20, 20), 1)
            name = f'sheet_{offset // 2 + 1}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Could not save {path}')
            index.append({'path': name, 'sha256': digest(path),
                          'points': [{'set': r['set'], 'point_number': r['point_number']}
                                     for r in runs[offset:offset + 2]]})
    finally:
        cap.release()
    current = {entry['path'] for entry in index}
    for old_sheet in OUT.glob('sheet_*.jpg'):
        if old_sheet.name not in current:
            old_sheet.unlink()
    (OUT / 'index.json').write_text(json.dumps({'source_sha256': digest(VIDEO),
                                                'tracks_sha256': digest(TRACKS),
                                                'anchor_window_audit_sha256': digest(AUDIT),
                                                'sheets': index}, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(index)} anchor-window review sheets')


if __name__ == '__main__':
    main()
