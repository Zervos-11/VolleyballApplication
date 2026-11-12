"""Render every frame of a newly found long winning six-ID candidate run."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = MATCH / 'screening'
VIDEO = MATCH / 'source_720p.mp4'
AUDIT = SCREEN / 'highres_winning_run_screen.json'
OUT = SCREEN / 'highres_winning_run_review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    assert audit['source_sha256'] == sha(VIDEO)
    selected = [p for p in audit['points'] if p['longest_run_length'] >= 5]
    assert len(selected) == 1 and (selected[0]['set'], selected[0]['point_number']) == (3, 13)
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    entries = []
    try:
        for point in selected:
            by_frame = {row['source_frame']: row for row in point['rows']}
            frames = point['longest_exact_six_same_raw_id_run']
            for first in range(0, len(frames), 4):
                chunk = frames[first:first+4]
                sheet = np.full((len(chunk)*390, 640, 3), 245, np.uint8)
                for i, frame in enumerate(chunk):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                    ok, image = cap.read()
                    if not ok:
                        raise RuntimeError(f'Cannot decode frame {frame}')
                    for box in by_frame[frame]['near_floor_side_proposals']:
                        x1, y1, x2, y2 = map(round, box['bbox_px'])
                        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 210, 0), 2)
                        cv2.putText(image, str(box['raw_track_id']), (x1, max(20, y1-5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 180, 0), 2)
                    sheet[i*390:i*390+360] = cv2.resize(image, (640, 360))
                    cv2.putText(sheet, f'S3 P13 f{frame}', (8, i*390+383),
                                cv2.FONT_HERSHEY_SIMPLEX, .55, (20, 20, 20), 1)
                name = f's3_p13_{first:02d}.jpg'
                path = OUT / name
                if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise RuntimeError(f'Cannot save {path}')
                entries.append({'set': 3, 'point_number': 13, 'source_frames': chunk,
                                'sheet': name, 'sha256': sha(path)})
    finally:
        cap.release()
    (OUT / 'index.json').write_text(json.dumps({
        'status': 'all_frames_long_highres_winning_run_review_pack',
        'source_sha256': audit['source_sha256'], 'run_audit_sha256': sha(AUDIT),
        'entries': entries,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {sum(len(e["source_frames"]) for e in entries)} source frames')


if __name__ == '__main__':
    main()
