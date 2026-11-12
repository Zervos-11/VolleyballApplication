"""Render exact source context around set-three box-proxy case frames."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_missing_outcome_box_candidates'
FRAMES = {(3, 5): 155799, (3, 11): 162695, (3, 27): 187701, (3, 37): 204263}
OFFSETS = (-75, -25, 0, 25, 75)


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    try:
        for (set_number, point_number), center in FRAMES.items():
            tiles = []
            for offset in OFFSETS:
                number = center + offset
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, frame = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f'Cannot decode {number}')
                tile = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.putText(tile, f'S{set_number} P{point_number} frame {number}',
                            (15, 35), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
                tiles.append(tile)
            sheet = np.vstack([np.hstack(tiles[:3]),
                               np.hstack(tiles[3:] + [np.zeros_like(tiles[0])])])
            target = OUT / f's{set_number}_p{point_number}_f{center}_context.jpg'
            if not cv2.imwrite(str(target), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                raise RuntimeError(f'Could not write {target}')
            print(target)
    finally:
        cap.release()


if __name__ == '__main__':
    main()
