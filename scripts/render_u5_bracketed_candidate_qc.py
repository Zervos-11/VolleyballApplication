"""Render source and boxed views of one bracketed six-box frame per point.

This is a review aid; it does not adjudicate identities or floor positions.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
TRACKS = BASE / 'screening/dense_live_track_screen.json'
CORE = BASE / 'screening/cut_bounded_provisional_rally_metrics.json'
BRACKETS = BASE / 'screening/coarse_phase_brackets.json'
OUT = BASE / 'screening/bracketed_candidate_qc'
SOURCE_REVIEWED_REPLACEMENTS = {(1, 37): 10488}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    core = json.loads(CORE.read_text(encoding='utf-8'))
    brackets = json.loads(BRACKETS.read_text(encoding='utf-8'))
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    if not (core['source_sha256'] == brackets['source_sha256'] == tracks['source_sha256'] == digest(VIDEO)):
        raise ValueError('Different source videos')
    if core['dense_tracks_sha256'] != digest(TRACKS):
        raise ValueError('Candidate screen differs from tracker')
    by_key = {(r['set'], r['point_number']): r for r in brackets['points']}
    track_by_key = {(r['set'], r['point_number']): {f['source_frame']: f for f in r['rows']}
                    for r in tracks['points']}
    chosen = []
    for point in core['points']:
        key = point['set'], point['point_number']
        first = by_key[key]['first_obvious_active_frame']
        last = by_key[key]['last_obvious_active_frame']
        eligible = [f for f in point['frames'] if first - 1 <= f['source_frame'] <= last + 1]
        if eligible:
            replacement = SOURCE_REVIEWED_REPLACEMENTS.get(key)
            if replacement is not None and replacement not in {f['source_frame'] for f in eligible}:
                raise ValueError(f'Replacement is not an eligible candidate: {key} {replacement}')
            selected = (next(f for f in eligible if f['source_frame'] == replacement)
                        if replacement is not None else eligible[len(eligible) // 2])
            chosen.append({'set': key[0], 'point_number': key[1],
                           'source_frame': selected['source_frame'],
                           'source_second': selected['source_second'],
                           'bracketed_candidate_count': len(eligible)})
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    pages = []
    try:
        for offset in range(0, len(chosen), 2):
            sheet = np.full((2 * 395, 2 * 640, 3), 240, np.uint8)
            items = chosen[offset:offset + 2]
            for row_no, item in enumerate(items):
                frame_no = item['source_frame']
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                ok, source = cap.read()
                if not ok:
                    raise RuntimeError(f'Could not decode source frame {frame_no}')
                annotated = source.copy()
                row = track_by_key[item['set'], item['point_number']][frame_no]
                cv2.line(annotated, (297, 313), (1046, 313), (0, 255, 255), 2)
                for proposal in row['proposals']:
                    x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                    color = ((0, 195, 0) if proposal['net_side_status'] == 'near_floor_side_candidate'
                             else (0, 0, 220))
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated, str(proposal['raw_track_id']),
                                (x1, max(24, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 2)
                y = row_no * 395
                sheet[y:y + 360, :640] = cv2.resize(source, (640, 360), interpolation=cv2.INTER_AREA)
                sheet[y:y + 360, 640:] = cv2.resize(annotated, (640, 360), interpolation=cv2.INTER_AREA)
                label = f"S{item['set']} P{item['point_number']} {item['source_second']:.1f}s f{frame_no}  n={item['bracketed_candidate_count']}"
                cv2.putText(sheet, label, (8, y + 384), cv2.FONT_HERSHEY_SIMPLEX,
                            .58, (20, 20, 20), 1)
            name = f'sheet_{offset // 2 + 1}.jpg'
            path = OUT / name
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError(f'Could not save {path}')
            pages.append({'path': name, 'sha256': digest(path), 'items': items})
    finally:
        cap.release()
    index = {'status': 'source_and_detector_views_pending_individual_review',
             'source_sha256': core['source_sha256'],
             'candidate_screen_sha256': digest(CORE), 'coarse_brackets_sha256': digest(BRACKETS),
             'point_count': len(chosen), 'pages': pages}
    (OUT / 'index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    print(f"Rendered {len(chosen)} bracketed candidate frames on {len(pages)} sheets")


if __name__ == '__main__':
    main()
