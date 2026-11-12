"""Render saved boxes on the two set-three ProVolley-win navigation frames."""
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_missing_outcome_box_candidates'
FRAMES = {5: 155799, 27: 187701}


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    if audit['source_sha256'] != source['sha256']:
        raise ValueError('Audit and video differ')
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    try:
        for point in audit['points']:
            if point['set'] != 3 or point['point_number'] not in FRAMES:
                continue
            number = FRAMES[point['point_number']]
            labels = json.loads((ROOT / point['label_file']).read_text(encoding='utf-8'))
            cap.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                raise RuntimeError(f'Cannot decode {number}')
            for player in labels['frames'][str(number)]['players']:
                if player['bbox'] is None:
                    continue
                x1, y1, x2, y2 = map(round, player['bbox'])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 190, 0), 3)
                cv2.putText(image, player['player_id'], (x1, max(35, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
            target = OUT / f's3_p{point["point_number"]}_f{number}_saved.jpg'
            if not cv2.imwrite(str(target), image, [cv2.IMWRITE_JPEG_QUALITY, 93]):
                raise RuntimeError(f'Could not write {target}')
            print(target)
    finally:
        cap.release()


if __name__ == '__main__':
    main()
