"""Render one deterministic six-box candidate frame for each frozen point."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
SCREEN = BASE / 'screening/live_core_box_screen.json'
OUT = BASE / 'screening/live_core_review_anchors'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    if digest(VIDEO) != manifest['video']['sha256'] or screen['source_sha256'] != manifest['video']['sha256']:
        raise ValueError('Source mismatch')
    cap = cv2.VideoCapture(str(VIDEO))
    OUT.mkdir(exist_ok=True)
    anchors = []
    try:
        for set_number in (1, 2, 3):
            sheet = np.full((3 * 395, 2 * 640, 3), 245, np.uint8)
            points = [item for item in screen['point_summary'] if item['set'] == set_number]
            for i, point in enumerate(points):
                candidates = [row for row in screen['rows'] if row['set'] == set_number
                              and row['point_number'] == point['point_number']
                              and row['gated_person_proposal_count'] >= 6]
                if candidates:
                    middle = sum(row['source_second'] for row in candidates) / len(candidates)
                    chosen = min(candidates, key=lambda row: (abs(row['gated_person_proposal_count'] - 6),
                                                              abs(row['source_second'] - middle),
                                                              row['source_second']))
                    selection_status = 'six_or_more_proposal_candidate'
                else:
                    available = [row for row in screen['rows'] if row['set'] == set_number
                                 and row['point_number'] == point['point_number']]
                    chosen = max(available, key=lambda row: row['gated_person_proposal_count'])
                    selection_status = 'no_six_proposal_live_second'
                cap.set(cv2.CAP_PROP_POS_FRAMES, chosen['source_frame'])
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != chosen['source_frame'] + 1:
                    raise RuntimeError(f"Cannot decode frame {chosen['source_frame']}")
                for proposal in chosen['proposals']:
                    x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 190, 0), 2)
                x, y = (i % 2) * 640, (i // 2) * 395
                sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                           interpolation=cv2.INTER_AREA)
                cv2.putText(sheet, f"S{set_number} P{point['point_number']} "
                            f"{chosen['source_second']}s n={chosen['gated_person_proposal_count']}",
                            (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX, .6,
                            (20, 20, 20), 1)
                anchors.append({'set': set_number, 'point_number': point['point_number'],
                                'second': chosen['source_second'],
                                'source_frame': chosen['source_frame'],
                                'proposal_count': chosen['gated_person_proposal_count'],
                                'selection_status': selection_status,
                                'selection_rule': 'exactly six preferred, then closest to candidate-time centre'})
            if not cv2.imwrite(str(OUT / f'set_{set_number}.jpg'), sheet,
                               [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError('Could not write anchor sheet')
    finally:
        cap.release()
    (OUT / 'anchors.json').write_text(json.dumps({'source_sha256': manifest['video']['sha256'],
                                                  'box_screen_sha256': digest(SCREEN),
                                                  'anchors': anchors}, indent=2) + '\n',
                                      encoding='utf-8')
    print(f'Rendered {len(anchors)} deterministic candidate anchors')


if __name__ == '__main__':
    main()
