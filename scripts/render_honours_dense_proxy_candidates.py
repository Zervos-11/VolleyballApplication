"""Render the dense-window six-box proposals for source-image review."""
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/processed/honours_dense_proxy_window_screen.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_dense_proxy_window_candidates'


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    if screen['source_sha256'] != source['sha256']:
        raise ValueError('Screen belongs to another source')
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    try:
        for point in screen['points']:
            for row in point['rows']:
                if row['overlap_filtered_count'] < 6:
                    continue
                number = row['frame']
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f'Could not decode frame {number}')
                for index, box in enumerate(row['overlap_filtered_boxes']):
                    x1, y1, x2, y2 = map(round, box['bbox_px'])
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 190, 0), 3)
                    cv2.putText(image, str(index), (x1, max(35, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
                path = OUT / f's3_p{point["point_number"]}_f{number}.jpg'
                if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                    raise RuntimeError(f'Could not write {path}')
    finally:
        cap.release()
    print(f'Rendered {len(list(OUT.glob("*.jpg")))} candidate frames')


if __name__ == '__main__':
    main()
