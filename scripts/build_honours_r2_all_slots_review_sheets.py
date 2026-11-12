"""Render the saved R2 slots on exact source frames for source review."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
LABELS = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json'
OUT = ROOT / 'data/processed/honours_r2_all_slots_source_sheets'


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    tiles = []
    candidate_frames = {78050, 78100, 78400}
    try:
        for frame_text, record in sorted(labels['frames'].items(), key=lambda item: int(item[0])):
            frame_number = int(frame_text)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
                raise RuntimeError(f'Could not decode exact frame {frame_number}')
            raw = frame.copy()
            for slot in record['players']:
                x1, y1, x2, y2 = map(round, slot['bbox'])
                color = (0, 0, 255) if slot['player_id'] == '42' else (0, 175, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, slot['player_id'], (x1, max(510, y1 - 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, .9, color, 3)
                if slot['footpoint'] is not None:
                    x, y = map(round, slot['footpoint'])
                    cv2.circle(frame, (x, y), 9, color, -1)
            cv2.putText(frame, str(frame_number), (40, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 255), 4)
            tiles.append(cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA))
            if frame_number in candidate_frames:
                overlay = OUT / f'candidate_{frame_number}_full.jpg'
                if not cv2.imwrite(str(overlay), frame, [cv2.IMWRITE_JPEG_QUALITY, 96]):
                    raise RuntimeError(f'Failed to write {overlay}')
                crops = np.full((640, 1440, 3), 245, dtype=np.uint8)
                for index, slot in enumerate(record['players']):
                    foot = slot['footpoint'] or [(slot['bbox'][0] + slot['bbox'][2]) / 2, slot['bbox'][3]]
                    x, y = map(round, foot)
                    left = max(0, min(raw.shape[1] - 480, x - 240))
                    top = max(0, min(raw.shape[0] - 320, y - 220))
                    crop = raw[top:top + 320, left:left + 480].copy()
                    cv2.drawMarker(crop, (x - left, y - top), (0, 0, 255),
                                   cv2.MARKER_CROSS, 22, 2)
                    cv2.putText(crop, f"slot {slot['player_id']} | {slot['position_status']}",
                                (8, 30), cv2.FONT_HERSHEY_SIMPLEX, .72, (255, 255, 255), 3)
                    cv2.putText(crop, f"slot {slot['player_id']} | {slot['position_status']}",
                                (8, 30), cv2.FONT_HERSHEY_SIMPLEX, .72, (0, 0, 0), 1)
                    row, col = divmod(index, 3)
                    crops[row * 320:(row + 1) * 320, col * 480:(col + 1) * 480] = crop
                crop_path = OUT / f'candidate_{frame_number}_foot_crops.jpg'
                if not cv2.imwrite(str(crop_path), crops, [cv2.IMWRITE_JPEG_QUALITY, 96]):
                    raise RuntimeError(f'Failed to write {crop_path}')
    finally:
        cap.release()
    for start in range(0, len(tiles), 4):
        sheet = np.full((1080, 1920, 3), 240, dtype=np.uint8)
        for index, tile in enumerate(tiles[start:start + 4]):
            row, col = divmod(index, 2)
            sheet[row * 540:(row + 1) * 540, col * 960:(col + 1) * 960] = tile
        path = OUT / f'saved_frames_{start + 1:02d}_{min(start + 4, len(tiles)):02d}.jpg'
        if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
            raise RuntimeError(f'Failed to write {path}')
        print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
