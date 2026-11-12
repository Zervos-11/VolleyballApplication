"""Render post-annotation checks of manual shoe and fixed-box proxy points."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'dynamic_shoe_reference_sheets/index.json'
MANUAL = BASE / 'dynamic_shoe_reference_manual_qc.json'
OUT = BASE / 'dynamic_shoe_reference_overlay_index.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    manual = json.loads(MANUAL.read_text(encoding='utf-8'))
    assert manual['review_index_sha256'] == sha(INDEX)
    by_key = {(r['set'], r['point_number'], r['source_frame'], str(r['player_key'])): r
              for r in manual['rows']}
    rows = []
    for item in index['rows']:
        image = cv2.imread(str(BASE / 'dynamic_shoe_reference_sheets' / item['sheet']))
        assert image is not None
        for j, selected in enumerate(item['selected']):
            key = item['set'], item['point_number'], item['source_frame'], str(selected['player_key'])
            mark = by_key[key]
            crop = selected['crop']
            def to_canvas(point):
                return (round(2*(point[0]-crop['left'])+j*2*crop['width']),
                        round(2*(point[1]-crop['top'])+70))
            proxy = to_canvas(selected['proxy_bottom_px'])
            cv2.drawMarker(image, proxy, (0, 180, 0), cv2.MARKER_CROSS, 15, 2)
            if mark['status'] == 'approximate_clear_pair':
                manual_xy = to_canvas(mark['shoe_midpoint_px'])
                cv2.drawMarker(image, manual_xy, (0, 0, 255), cv2.MARKER_TILTED_CROSS, 15, 2)
            else:
                cv2.putText(image, 'missing shoe reference', (j*500+8, 438),
                            cv2.FONT_HERSHEY_SIMPLEX, .52, (0, 0, 220), 1, cv2.LINE_AA)
        name = item['sheet'].replace('.jpg', '_checked.jpg')
        path = BASE / 'dynamic_shoe_reference_sheets' / name
        assert cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        rows.append({'set': item['set'], 'point_number': item['point_number'],
                     'sheet': name, 'sha256': sha(path)})
    OUT.write_text(json.dumps({'source_sha256': index['source_sha256'],
                               'index_sha256': sha(INDEX), 'manual_sha256': sha(MANUAL),
                               'legend': 'green plus = fixed-box proxy; red x = manual shoe midpoint',
                               'rows': rows}, indent=2)+'\n', encoding='utf-8')
    print(f'Rendered {len(rows)} post-annotation checks')


if __name__ == '__main__':
    main()
