"""Render source/raw side-by-side crops for two dense-slice review gaps."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
VIDEO = ROOT / 'data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4'
RAW = DIR / 'raw_74880_75540.json'
SETS = {
    'centre_left_gap': (75205, 75206, 75210, 75215, 75220, 75225, 75229),
    'right_entrant_gap': (75215, 75216, 75220, 75224, 75226, 75227),
}
CROPS = {
    'centre_left_gap': (430, 250, 760, 490),
    'right_entrant_gap': (1040, 250, 1280, 510),
}


def main():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    if raw['source_sha256'] != hashlib.sha256(VIDEO.read_bytes()).hexdigest():
        raise ValueError('Source/prediction mismatch')
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    try:
        for name, frames in SETS.items():
            x1, y1, x2, y2 = CROPS[name]
            strips = []
            for frame in frames:
                video.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = video.read()
                if not ok:
                    raise RuntimeError(frame)
                source = image[y1:y2, x1:x2].copy()
                marked = source.copy()
                for row in raw['predictions'][str(frame)]:
                    bx1, by1, bx2, by2 = row['bbox']
                    if (bx1 + bx2) / 2 < x1 or (bx1 + bx2) / 2 > x2:
                        continue
                    px1, py1 = round(bx1 - x1), round(by1 - y1)
                    px2, py2 = round(bx2 - x1), round(by2 - y1)
                    cv2.rectangle(marked, (px1, py1), (px2, py2), (0, 255, 255), 2)
                    cv2.putText(marked, str(row['track_id']), (px1, max(16, py1 - 3)),
                                cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 0, 0), 3)
                    cv2.putText(marked, str(row['track_id']), (px1, max(16, py1 - 3)),
                                cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 255, 255), 1)
                for panel in (source, marked):
                    cv2.putText(panel, str(frame), (6, 24), cv2.FONT_HERSHEY_SIMPLEX,
                                .72, (0, 0, 0), 3)
                    cv2.putText(panel, str(frame), (6, 24), cv2.FONT_HERSHEY_SIMPLEX,
                                .72, (255, 255, 255), 1)
                strips.append(cv2.hconcat([source, marked]))
            out = DIR / f'{name}_source_raw_review.jpg'
            if out.exists() or not cv2.imwrite(str(out), cv2.vconcat(strips)):
                raise OSError(out)
            print(out)
    finally:
        video.release()


if __name__ == '__main__':
    main()
