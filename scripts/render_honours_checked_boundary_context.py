"""Render exact source-frame context around the two saved point boundaries."""
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
LEDGER = ROOT / 'data/processed/honours_interval_identity_ledger.json'
OUT = ROOT / 'data/processed/honours_checked_boundary_context'
OFFSETS = [-40, -15, 0, 15, 40]
W, H = 640, 360


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    if source['sha256'] != ledger['source_sha256']:
        raise ValueError('Video differs from ledger source')
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        for point in ledger['points']:
            if not point['annotator_checked_interval_saved']:
                continue
            for event, center in [('serve', point['annotator_checked_serve_contact_frame']),
                                  ('end', point['annotator_checked_end_frame_exclusive'])]:
                canvas = np.full((H + 34, len(OFFSETS) * W, 3), 245, np.uint8)
                for i, offset in enumerate(OFFSETS):
                    number = center + offset
                    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                    ok, image = cap.read()
                    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                        raise RuntimeError(f'Could not decode exact frame {number}')
                    x = i * W
                    canvas[:H, x:x + W] = cv2.resize(image, (W, H), interpolation=cv2.INTER_AREA)
                    cv2.putText(canvas, f'{event} {offset:+d}: f{number}', (x + 6, H + 24),
                                cv2.FONT_HERSHEY_SIMPLEX, .62, (20, 20, 20), 2)
                path = OUT / f's{point["set"]}_p{point["point_number"]}_{event}.jpg'
                if not cv2.imwrite(str(path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                    raise RuntimeError(f'Could not write {path}')
    finally:
        cap.release()
    print(f'Rendered {len(list(OUT.glob("*.jpg")))} boundary sheets')


if __name__ == '__main__':
    main()
