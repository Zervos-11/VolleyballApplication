"""Render all five sample frames of eight screened optical-flow windows."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from pilot_u5_box_centre_flow import review_image, source_frames


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
BASE = MATCH / 'screening'
FLOW = BASE / 'box_centre_flow_pilot.json'
WINDOW = BASE / 'flow_window_image_geometry.json'
VIDEO = MATCH / 'source_720p.mp4'
OUT = BASE / 'flow_window_five_sample_review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pilot = json.loads(FLOW.read_text(encoding='utf-8'))
    windows = json.loads(WINDOW.read_text(encoding='utf-8'))
    assert windows['input_sha256']['pilot'] == sha(FLOW)
    assert len(windows['rows']) == 8
    index = {(r['set'], r['point_number']): r for r in pilot['rows']}
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for window in windows['rows']:
        key = window['set'], window['point_number']
        row = index[key]
        anchor = row['anchor_frame']
        images = source_frames(cap, anchor)
        label = f"S{key[0]} P{key[1]} {'WIN' if row['near_team_won'] else 'LOSS'}"
        cells = [review_image(images[frame], row['players'], frame, label)
                 for frame in window['source_window_frames']]
        blank = np.full_like(cells[0], 255)
        sheet = np.vstack((np.hstack(cells[:3]), np.hstack(cells[3:] + [blank])))
        name = f's{key[0]}_p{key[1]:02d}.jpg'
        path = OUT / name
        assert cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 93])
        manifest.append({'set': key[0], 'point_number': key[1],
                         'near_team_won': row['near_team_won'],
                         'source_frames': window['source_window_frames'],
                         'sheet': name, 'sha256': sha(path)})
    cap.release()
    (OUT/'index.json').write_text(json.dumps({'source_sha256': pilot['source_sha256'],
                                               'pilot_sha256': sha(FLOW),
                                               'window_sha256': sha(WINDOW),
                                               'rows': manifest}, indent=2)+'\n', encoding='utf-8')
    print(f'Rendered {len(manifest)} five-sample review sheets')


if __name__ == '__main__':
    main()
