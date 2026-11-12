"""Render unboxed source crops for a bounded non-anchor shoe reference."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
VIDEO = BASE / 'source_720p.mp4'
PROXY = SCREEN / 'fixed_box_court_proxy_pilot.json'
PILOT = SCREEN / 'box_centre_flow_pilot.json'
OUT_DIR = SCREEN / 'dynamic_shoe_reference_sheets'
INDEX = OUT_DIR / 'index.json'
WIDTH, HEIGHT = 250, 190


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(frame, point, key, frame_number):
    x, y = point
    left = max(0, min(frame.shape[1]-WIDTH, int(round(x-WIDTH/2))))
    top = max(0, min(frame.shape[0]-HEIGHT, int(round(y-HEIGHT+90))))
    canvas = frame[top:top+HEIGHT, left:left+WIDTH].copy()
    # Fine grid for reading coordinates; no predicted box or proxy marker is drawn.
    for gx in range((left//25+1)*25, left+WIDTH, 25):
        color = (215, 215, 215) if gx % 50 else (130, 130, 130)
        cv2.line(canvas, (gx-left, 0), (gx-left, HEIGHT-1), color, 1)
        if gx % 50 == 0:
            cv2.putText(canvas, str(gx), (gx-left+2, 12), cv2.FONT_HERSHEY_SIMPLEX,
                        .32, (0, 0, 0), 1, cv2.LINE_AA)
    for gy in range((top//25+1)*25, top+HEIGHT, 25):
        color = (215, 215, 215) if gy % 50 else (130, 130, 130)
        cv2.line(canvas, (0, gy-top), (WIDTH-1, gy-top), color, 1)
        if gy % 50 == 0:
            cv2.putText(canvas, str(gy), (2, gy-top-3), cv2.FONT_HERSHEY_SIMPLEX,
                        .32, (0, 0, 0), 1, cv2.LINE_AA)
    header = np.full((35, WIDTH, 3), 255, np.uint8)
    cv2.putText(header, f'{key} f{frame_number}', (5, 14), cv2.FONT_HERSHEY_SIMPLEX,
                .44, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(header, f'x {left}-{left+WIDTH}, y {top}-{top+HEIGHT}', (5, 30),
                cv2.FONT_HERSHEY_SIMPLEX, .38, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([header, canvas]), {'left': left, 'top': top, 'width': WIDTH, 'height': HEIGHT}


def main():
    proxy = json.loads(PROXY.read_text(encoding='utf-8'))
    pilot = json.loads(PILOT.read_text(encoding='utf-8'))
    assert proxy['summary']['candidate_windows'] == 8
    pilot_rows = {(r['set'], r['point_number']): r for r in pilot['rows']}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    rows = []
    for row in proxy['rows']:
        frame = row['frames'][-1]
        frame_number = frame['source_frame']
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, source = cap.read()
        assert ok
        anchor = row['frames'][2]
        ordering = sorted(range(6), key=lambda i: anchor['fixed_box_bottom_px'][i][1])
        selected = [ordering[0], ordering[-1]]
        images = []
        identity_images = []
        selections = []
        for index in selected:
            key = row['player_keys'][index]
            image, crop = panel(source, frame['fixed_box_bottom_px'][index], key, frame_number)
            images.append(image)
            player = pilot_rows[(row['set'], row['point_number'])]['players'][index]
            dx, dy = player['frames'][str(frame_number)]['translation_px']
            x1, y1, x2, y2 = player['anchor_bbox_px']
            overlay = source.copy()
            cv2.rectangle(overlay, (round(x1+dx), round(y1+dy)),
                          (round(x2+dx), round(y2+dy)), (0, 220, 0), 2)
            identity_image, _ = panel(overlay, frame['fixed_box_bottom_px'][index],
                                      key, frame_number)
            identity_images.append(identity_image)
            selections.append({'player_index': index, 'player_key': key, 'crop': crop,
                               'proxy_bottom_px': frame['fixed_box_bottom_px'][index]})
        sheet = cv2.resize(np.hstack(images), None, fx=2, fy=2,
                           interpolation=cv2.INTER_CUBIC)
        name = f"s{row['set']}_p{row['point_number']:02d}_f{frame_number}.jpg"
        path = OUT_DIR / name
        assert cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 96])
        identity_name = name.replace('.jpg', '_identity.jpg')
        identity_path = OUT_DIR / identity_name
        identity_sheet = cv2.resize(np.hstack(identity_images), None, fx=2, fy=2,
                                    interpolation=cv2.INTER_CUBIC)
        assert cv2.imwrite(str(identity_path), identity_sheet,
                           [cv2.IMWRITE_JPEG_QUALITY, 96])
        rows.append({'set': row['set'], 'point_number': row['point_number'],
                     'source_frame': frame_number, 'sheet': name, 'sheet_sha256': sha(path),
                     'identity_sheet': identity_name,
                     'identity_sheet_sha256': sha(identity_path),
                     'selected': selections})
    cap.release()
    assert len(rows) == 8
    out = {'status': 'unboxed_source_crop_index_for_single_reviewer_non_anchor_reference',
           'source_sha256': proxy['source_sha256'], 'proxy_sha256': sha(PROXY),
           'pilot_sha256': sha(PILOT),
           'video_sha256': proxy['source_sha256'],
           'selection_rule': 'frontmost and rearmost anchor box by image bottom; evaluate at +12 frames',
           'annotation_rule': 'manual midpoint of two visible grounded shoes; uncertain contact is null',
           'rows': rows}
    INDEX.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    print(f'Rendered {len(rows)} source sheets')


if __name__ == '__main__':
    main()
