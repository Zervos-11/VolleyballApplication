"""Render every source second in each frozen score-to-score navigation interval."""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
SAMPLE = BASE / 'screening/rally_sample_score_only.json'
CONTEXT = BASE / 'screening/selected_point_review/record.json'
OUT = BASE / 'screening/selected_point_second_strips'
W, H, FOOT = 320, 180, 24


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    context = json.loads(CONTEXT.read_text(encoding='utf-8'))
    if digest(VIDEO) != manifest['video']['sha256'] or context['sample_sha256'] != digest(SAMPLE):
        raise ValueError('Source or sample hash mismatch')
    cap = cv2.VideoCapture(str(VIDEO))
    OUT.mkdir(exist_ok=True)
    records = []
    try:
        for item in context['source_seconds']:
            seconds = list(range(item['previous_score_change_s'] + 1,
                                 item['score_change_s'] + 1))
            sheet = np.full((math.ceil(len(seconds) / 4) * (H + FOOT), 4 * W, 3), 245, np.uint8)
            for index, second in enumerate(seconds):
                cap.set(cv2.CAP_PROP_POS_FRAMES, second * 30)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != second * 30 + 1:
                    raise RuntimeError(f'Cannot decode second {second}')
                x, y = (index % 4) * W, (index // 4) * (H + FOOT)
                sheet[y:y + H, x:x + W] = cv2.resize(image, (W, H), interpolation=cv2.INTER_AREA)
                cv2.putText(sheet, f'{second}s', (x + 5, y + H + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, (20, 20, 20), 1)
            path = OUT / f"set_{item['set']}_point_{item['point_number']:02d}.jpg"
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 91]):
                raise RuntimeError(f'Could not write {path}')
            records.append({'set': item['set'], 'point_number': item['point_number'],
                            'source_seconds_inclusive': [seconds[0], seconds[-1]],
                            'sheet': str(path.relative_to(ROOT)).replace('\\', '/')})
    finally:
        cap.release()
    (OUT / 'record.json').write_text(json.dumps({'source_sha256': manifest['video']['sha256'],
                                                 'sample_sha256': digest(SAMPLE),
                                                 'rows': records}, indent=2) + '\n',
                                     encoding='utf-8')
    print(f'Rendered {len(records)} second-by-second source strips')


if __name__ == '__main__':
    main()
