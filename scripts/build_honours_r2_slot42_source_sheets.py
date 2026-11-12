"""Make exact-frame source sheets for adjudicating R2 saved slot 42."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
LABELS = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json'
TRACKS = ROOT / 'data/processed/pilot_tracker_evaluation/dense_identity_validation_r2/tracker_predictions.json'
OUT = ROOT / 'data/processed/honours_r2_slot42_source_sheets'


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))['predictions']
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 78100)
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    tiles = []
    try:
        for frame_number in range(78100, 78151):
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
                raise RuntimeError(f'Could not decode exact frame {frame_number}')
            for proposal in tracks[str(frame_number)]:
                if proposal['track_id'] != 10:
                    continue
                x1, y1, x2, y2 = map(round, proposal['bbox'])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 0), 3)
            saved = labels['frames'].get(str(frame_number))
            if saved:
                slot = next(p for p in saved['players'] if p['player_id'] == '42')
                x1, y1, x2, y2 = map(round, slot['bbox'])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                if slot['footpoint']:
                    x, y = map(round, slot['footpoint'])
                    cv2.circle(frame, (x, y), 9, (0, 0, 255), -1)
            tile = frame[530:950, 650:1270].copy()
            cv2.putText(tile, f'{frame_number} red=saved green=track10', (8, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 3)
            cv2.putText(tile, f'{frame_number} red=saved green=track10', (8, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 0, 0), 1)
            tiles.append(tile)
    finally:
        cap.release()
    OUT.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(tiles), 13):
        group = tiles[start:start + 13]
        sheet = np.full((4 * 420, 4 * 620, 3), 240, dtype=np.uint8)
        for index, tile in enumerate(group):
            row, col = divmod(index, 4)
            sheet[row * 420:(row + 1) * 420, col * 620:(col + 1) * 620] = tile
        path = OUT / f'frames_{78100 + start}_{78100 + start + len(group) - 1}.jpg'
        if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 93]):
            raise RuntimeError(f'Failed to write {path}')
        print(path.relative_to(ROOT))

    anchors = np.full((4 * 470, 3 * 850, 3), 240, dtype=np.uint8)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    try:
        for index, (frame_text, record) in enumerate(sorted(labels['frames'].items(),
                                                               key=lambda item: int(item[0]))):
            frame_number = int(frame_text)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
                raise RuntimeError(f'Could not decode exact frame {frame_number}')
            slot = next(p for p in record['players'] if p['player_id'] == '42')
            x1, y1, x2, y2 = map(round, slot['bbox'])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            if slot['footpoint']:
                x, y = map(round, slot['footpoint'])
                cv2.circle(frame, (x, y), 9, (0, 0, 255), -1)
            crop = frame[480:950, 600:1450]
            cv2.putText(crop, f'{frame_number} saved slot 42', (8, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, .95, (255, 255, 255), 4)
            cv2.putText(crop, f'{frame_number} saved slot 42', (8, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, .95, (0, 0, 0), 2)
            row, col = divmod(index, 3)
            anchors[row * 470:(row + 1) * 470, col * 850:(col + 1) * 850] = crop
    finally:
        cap.release()
    path = OUT / 'saved_slot42_12_sparse_frames.jpg'
    if not cv2.imwrite(str(path), anchors, [cv2.IMWRITE_JPEG_QUALITY, 93]):
        raise RuntimeError(f'Failed to write {path}')
    print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
