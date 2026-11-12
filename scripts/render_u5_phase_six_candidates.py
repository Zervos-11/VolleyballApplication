"""Render one model-suggested play/six-candidate source frame per frozen point."""
import hashlib
import json
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
TRACKS = BASE / 'screening/dense_live_track_screen.json'
PHASE = BASE / 'screening/six_candidate_phase_screen.json'
OUT = BASE / 'screening/phase_six_candidate_review'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    phase = json.loads(PHASE.read_text(encoding='utf-8'))
    if phase['dense_track_screen_sha256'] != digest(TRACKS):
        raise ValueError('Phase and track screens differ')
    point_tracks = {(p['set'], p['point_number']): p for p in tracks['points']}
    OUT.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    chosen_rows = []
    try:
        for set_number in (1, 2, 3):
            sheet = np.full((3 * 395, 2 * 640, 3), 240, np.uint8)
            points = [p for p in phase['results'] if p['set'] == set_number]
            for i, point in enumerate(points):
                candidates = [r for r in point['rows'] if r['predicted_class'] == 'play']
                if not candidates:
                    candidates = point['rows']
                mid = statistics.median(r['source_frame'] for r in candidates)
                chosen = min(candidates, key=lambda r: (
                    abs(r['six_geometric_candidate_count'] - 6),
                    abs(r['source_frame'] - mid), r['source_frame']))
                key = (set_number, point['point_number'])
                source = next(r for r in point_tracks[key]['rows']
                              if r['source_frame'] == chosen['source_frame'])
                cap.set(cv2.CAP_PROP_POS_FRAMES, chosen['source_frame'])
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {chosen['source_frame']}")
                cv2.line(image, (297, 313), (1046, 313), (0, 255, 255), 2)
                for proposal in source['proposals']:
                    x1, y1, x2, y2 = map(round, proposal['bbox_px'])
                    color = ((0, 190, 0) if proposal['net_side_status'] ==
                             'near_floor_side_candidate' else (0, 0, 255))
                    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(image, str(proposal['raw_track_id']), (x1, max(24, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2)
                x, y = (i % 2) * 640, (i // 2) * 395
                sheet[y:y + 360, x:x + 640] = cv2.resize(image, (640, 360),
                                                           interpolation=cv2.INTER_AREA)
                cv2.putText(sheet, f"S{set_number} P{point['point_number']} "
                            f"frame {chosen['source_frame']} {chosen['predicted_class']} "
                            f"n={source['near_floor_side_candidate_count']}",
                            (x + 6, y + 382), cv2.FONT_HERSHEY_SIMPLEX,
                            .56, (20, 20, 20), 1)
                chosen_rows.append({'set': set_number, 'point_number': point['point_number'],
                                    'source_frame': chosen['source_frame'],
                                    'source_second': chosen['source_frame'] / 30,
                                    'predicted_class': chosen['predicted_class'],
                                    'geometric_candidate_count': source['near_floor_side_candidate_count'],
                                    'net_boundary_review_count': source['net_boundary_review_count'],
                                    'raw_track_ids': [p['raw_track_id'] for p in source['proposals']
                                                      if p['net_side_status'] == 'near_floor_side_candidate']})
            if not cv2.imwrite(str(OUT / f'set_{set_number}.jpg'), sheet,
                               [cv2.IMWRITE_JPEG_QUALITY, 94]):
                raise RuntimeError('Could not save sheet')
    finally:
        cap.release()
    (OUT / 'selected.json').write_text(json.dumps({
        'status': 'phase_model_navigation_frames_pending_source_review',
        'tracks_sha256': digest(TRACKS), 'phase_sha256': digest(PHASE),
        'selection_rule': 'model play class, exactly six geometric candidates preferred, '
                          'then nearest median play candidate frame',
        'selected': chosen_rows
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(chosen_rows)} candidate frames')


if __name__ == '__main__':
    main()
