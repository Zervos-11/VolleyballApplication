"""Render indexed detector proposals for source-image inspection."""
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/processed/honours_missing_outcome_box_screen.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_missing_outcome_box_candidates'


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    if screen['source_sha256'] != source['sha256']:
        raise ValueError('Screen belongs to a different source video')
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    try:
        for point in screen['points']:
            for row in point['rows']:
                if row['near_court_candidate_count'] < 6:
                    continue
                cap.set(cv2.CAP_PROP_POS_FRAMES, row['frame'])
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != row['frame'] + 1:
                    raise RuntimeError(f'Could not decode frame {row["frame"]}')
                for index, candidate in enumerate(row['candidates']):
                    x1, y1, x2, y2 = map(round, candidate['bbox_px'])
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 190, 0), 3)
                    cv2.putText(image, str(index), (x1, max(35, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
                name = f's{point["set"]}_p{point["point_number"]}_f{row["frame"]}.jpg'
                if not cv2.imwrite(str(OUT / name), image, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                    raise RuntimeError(f'Could not write {name}')
    finally:
        cap.release()
    print(f'Wrote {len(list(OUT.glob("*.jpg")))} indexed frames to {OUT}')


if __name__ == '__main__':
    main()
