"""Build local source-frame navigation sheets for the frozen honours sample."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
QUEUE = ROOT / 'data/processed/fqe_rally_review_queue.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUTPUT_DIR = ROOT / 'data/processed/honours_sample_sheets'
MANIFEST = OUTPUT_DIR / 'manifest.json'
PANEL_W, PANEL_H = 600, 338
HEADER_H, GAP, ROW_H = 50, 16, PANEL_H + 42


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_at(cap, number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(number))
    ok, frame = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
        raise RuntimeError(f'Could not decode exact source frame {number}')
    return cv2.resize(frame, (PANEL_W, PANEL_H), interpolation=cv2.INTER_AREA)


def main():
    sample, queue, source = read(SAMPLE), read(QUEUE), read(SOURCE)
    assert sample['match_id'] == queue['match_id'] == source['match_id']
    assert sample['source_sha256'] == queue['source_sha256'] == source['sha256']
    assert sample['input_sha256'][str(QUEUE.relative_to(ROOT))] == digest(QUEUE)
    assert sample['input_sha256'][str(SOURCE.relative_to(ROOT))] == digest(SOURCE)
    rows = {(r['set'], r['point_number']): r for r in queue['rows']}
    video = ROOT / source['video_file']
    if not video.is_file():
        raise FileNotFoundError(video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError('Could not open source video')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sheets = []
    try:
        for set_number in (1, 2, 3):
            subset = [r for r in sample['selected_points'] if r['set'] == set_number]
            canvas = np.full((HEADER_H + len(subset) * ROW_H, 3 * PANEL_W + 2 * GAP, 3), 245, np.uint8)
            cv2.putText(canvas, f'Set {set_number} | source-frame navigation | check timing labels',
                        (16, 32), cv2.FONT_HERSHEY_SIMPLEX, .72, (35, 35, 35), 2)
            sheet_rows = []
            for index, selected in enumerate(subset):
                record = rows[(set_number, selected['point_number'])]
                saved = record['serve_contact_frame'] is not None and record['end_frame_exclusive'] is not None
                start = record['serve_contact_frame'] if saved else record['estimated_start_frame']
                end = record['end_frame_exclusive'] if saved else record['estimated_end_frame_exclusive']
                assert start is not None and end is not None and 0 <= start < end <= source['frame_count']
                picks = [start, (start + end - 1) // 2, end - 1]
                y = HEADER_H + index * ROW_H
                labels = ('saved start', 'saved middle', 'saved end') if saved else ('start est.', 'middle est.', 'end est.')
                for col, (number, label) in enumerate(zip(picks, labels)):
                    x = col * (PANEL_W + GAP)
                    canvas[y:y + PANEL_H, x:x + PANEL_W] = frame_at(cap, number)
                    cv2.putText(canvas, f'S{set_number} P{selected["point_number"]} {selected["winner"]} | {label} f{number}',
                                (x + 4, y + PANEL_H + 26), cv2.FONT_HERSHEY_SIMPLEX, .49, (20, 20, 20), 1)
                sheet_rows.append({'point_number': selected['point_number'], 'winner': selected['winner'],
                                   'shown_frames': picks, 'timing_basis': 'saved_pilot_boundary' if saved else 'heuristic_estimate',
                                   'seek_frames': [selected['seek_from_frame'], selected['seek_to_frame_exclusive']]})
            filename = f'set_{set_number}_sample_navigation.jpg'
            path = OUTPUT_DIR / filename
            if not cv2.imwrite(str(path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                raise RuntimeError(f'Could not write {path}')
            sheets.append({'set': set_number, 'file': str(path.relative_to(ROOT)),
                           'sha256': digest(path), 'rows': sheet_rows})
    finally:
        cap.release()
    manifest = {'status': 'local_source_frame_navigation_not_accepted_rally_boundaries',
                'source_sha256': source['sha256'], 'sample_sha256': digest(SAMPLE),
                'queue_sha256': digest(QUEUE), 'sheets': sheets}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(sheets)} sheets and {MANIFEST}')


if __name__ == '__main__':
    main()
