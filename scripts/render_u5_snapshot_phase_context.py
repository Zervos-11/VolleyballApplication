"""Render source-video context for exact image-plane snapshot frames."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
INDEX = BASE / 'screening/image_plane_snapshot_screen.json'
VIDEO = BASE / 'source_720p.mp4'
OUT = BASE / 'screening/snapshot_phase_context'


def read_frame(cap, frame_number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f'Cannot read source frame {frame_number}')
    return frame


def main():
    screen = json.loads(INDEX.read_text(encoding='utf-8'))
    rows = screen['rows']
    with VIDEO.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert source_hash == screen['source_sha256'], 'Context video differs from reviewed source'
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open {VIDEO}')
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    cells = []
    for row in rows:
        f = row['source_frame']
        label = f"S{row['set']} P{row['point_number']} {'WIN' if row['near_team_won'] else 'LOSS'} f{f}"
        images = []
        for delta in (-12, 0, 12):
            source = read_frame(cap, f + delta)
            source = cv2.resize(source, (480, 270), interpolation=cv2.INTER_AREA)
            cell = np.full((300, 480, 3), 255, dtype=np.uint8)
            cell[30:300] = source
            cv2.putText(cell, f'{label} {delta:+d}', (7, 21),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
            images.append(cell)
        cells.append(np.hstack(images))
        manifest.append({'set': row['set'], 'point_number': row['point_number'],
                         'near_team_won': row['near_team_won'], 'source_frame': f,
                         'context_frames': [f-12, f, f+12],
                         'sheet': f'sheet_{(len(cells)-1)//4+1}.jpg'})
    for i in range(0, len(cells), 4):
        canvas = np.vstack(cells[i:i+4])
        path = OUT / f'sheet_{i//4+1}.jpg'
        if not cv2.imwrite(str(path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92]):
            raise RuntimeError(f'Cannot write {path}')
    (OUT/'index.json').write_text(json.dumps({'source_sha256': source_hash,
                                               'rows': manifest}, indent=2)+'\n', encoding='utf-8')
    cap.release()
    print(f'Rendered {len(rows)} exact snapshots with +/-12-frame source context')


if __name__ == '__main__':
    main()
