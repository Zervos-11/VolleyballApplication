"""Render every 5 Hz person crop for the two longest six-ID candidate runs."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening/full_clip_track_screen.json'
AUDIT = BASE / 'screening/full_clip_tracklet_audit.json'
VIDEO = BASE / 'source_720p.mp4'
OUT = BASE / 'screening/full_clip_run_spotcheck'
SELECTED = ((1, 5), (3, 34))
CELL_W, CELL_H = 160, 210


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    assert audit['input_sha256']['full_clip_screen'] == sha(SCREEN)
    points = {(p['set'], p['point_number']): p for p in screen['points']}
    runs = {(p['set'], p['point_number']): p['longest_same_six_raw_id_run_full_clip']
            for p in audit['points']}
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    manifest = {'source_sha256': screen['source_sha256'], 'screen_sha256': sha(SCREEN),
                'tracklet_audit_sha256': sha(AUDIT), 'rows': []}
    try:
        for key in SELECTED:
            run = runs[key]
            assert run['sampled_frames'] == 18 and len(run['raw_track_ids']) == 6
            rows = [r for r in points[key]['rows']
                    if run['first_frame'] <= r['source_frame'] <= run['last_frame']]
            assert len(rows) == 18
            crops = {raw_id: [] for raw_id in run['raw_track_ids']}
            for row in rows:
                frame = row['source_frame']
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame + 1
                for raw_id in run['raw_track_ids']:
                    match = [p for p in row['proposals']
                             if p['raw_track_id'] == raw_id
                             and p['net_side_status'] == 'near_floor_side_candidate']
                    assert len(match) == 1
                    x1, y1, x2, y2 = map(round, match[0]['bbox_px'])
                    crop = image[max(0, y1 - 8):min(image.shape[0], y2 + 8),
                                 max(0, x1 - 8):min(image.shape[1], x2 + 8)]
                    assert crop.size
                    # Preserve proportions so jersey cues can be visually compared.
                    scale = min((CELL_W - 8) / crop.shape[1], (CELL_H - 30) / crop.shape[0])
                    resized = cv2.resize(crop, None, fx=scale, fy=scale)
                    cell = np.full((CELL_H, CELL_W, 3), 245, np.uint8)
                    x = (CELL_W - resized.shape[1]) // 2
                    y = 25 + (CELL_H - 30 - resized.shape[0]) // 2
                    cell[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
                    cv2.putText(cell, f'ID{raw_id} f{frame}', (4, 16),
                                cv2.FONT_HERSHEY_SIMPLEX, .38, (0, 0, 0), 1)
                    crops[raw_id].append(cell)
            # Three six-frame pages keep the source crops readable in the viewer.
            for page in range(3):
                sheet = cv2.vconcat([cv2.hconcat(crops[raw_id][page * 6:(page + 1) * 6])
                                     for raw_id in run['raw_track_ids']])
                path = OUT / f's{key[0]}_p{key[1]:02d}_all_samples_crops_{page + 1}.png'
                assert cv2.imwrite(str(path), sheet)
                manifest['rows'].append({'set': key[0], 'point_number': key[1],
                                         'page': page + 1,
                                         'frames': [r['source_frame'] for r in rows[page * 6:(page + 1) * 6]],
                                         'raw_track_ids': run['raw_track_ids'],
                                         'image': path.relative_to(BASE).as_posix(),
                                         'image_sha256': sha(path)})
    finally:
        cap.release()
    path = OUT / 'all_samples_crop_manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print({'pages': len(manifest['rows']), 'samples_per_run': 18})


if __name__ == '__main__':
    main()
