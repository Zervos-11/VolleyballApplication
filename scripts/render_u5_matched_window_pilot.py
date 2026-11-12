"""Render equal-duration set-three win/loss candidate windows for source review."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
VIDEO = SCREEN.parent / 'source_720p.mp4'
OLD_TRACKS = SCREEN / 'dense_live_track_screen.json'
OLD_RUNS = SCREEN / 'interior_identity_run_availability.json'
NEW_TRACKS = SCREEN / 'highres_winning_run_screen.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, image):
    if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 97]):
        raise RuntimeError(f'Could not write {path}')
    return sha(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase-aligned', action='store_true',
                        help='Render a revised, source-phase-aligned diagnostic candidate')
    args = parser.parse_args()
    out = SCREEN / ('matched_window_pilot_phase' if args.phase_aligned else 'matched_window_pilot')
    old = json.loads(OLD_TRACKS.read_text(encoding='utf-8'))
    runs = json.loads(OLD_RUNS.read_text(encoding='utf-8'))
    new = json.loads(NEW_TRACKS.read_text(encoding='utf-8'))
    assert old['source_sha256'] == runs['source_sha256'] == new['source_sha256'] == sha(VIDEO)
    assert runs['tracks_sha256'] == sha(OLD_TRACKS)
    win = next(p for p in new['points'] if (p['set'], p['point_number']) == (3, 13))
    loss = next(p for p in old['points'] if (p['set'], p['point_number']) == (3, 34))
    loss_run = next(p for p in runs['points'] if (p['set'], p['point_number']) == (3, 34))
    win_frames = win['longest_exact_six_same_raw_id_run'][6:11] if args.phase_aligned else win['longest_exact_six_same_raw_id_run'][:5]
    choices = [
        ('win', 13, win_frames,
         {r['source_frame']: r['near_floor_side_proposals'] for r in win['rows']}),
        ('loss', 34, loss_run['run_source_frames'][:5],
         {r['source_frame']: [p for p in r['proposals']
                              if p['net_side_status'] == 'near_floor_side_candidate']
          for r in loss['rows']}),
    ]
    out.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    records = []
    try:
        for outcome, point, frames, lookup in choices:
            assert len(frames) == 5 and all(b - a == 6 for a, b in zip(frames, frames[1:]))
            for frame in frames:
                boxes = lookup[frame]
                assert len(boxes) == 6 and len({b['raw_track_id'] for b in boxes}) == 6
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, source = cap.read()
                if not ok:
                    raise RuntimeError(f'Could not decode frame {frame}')
                overlay = source.copy()
                sheet = np.full((2 * 180, 3 * 240, 3), 245, np.uint8)
                for i, box in enumerate(sorted(boxes, key=lambda p: p['raw_track_id'])):
                    x1, y1, x2, y2 = map(round, box['bbox_px'])
                    pid = box['raw_track_id']
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 210, 0), 2)
                    cv2.putText(overlay, str(pid), (x1, max(20, y1 - 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 180, 0), 2)
                    cx = round((x1 + x2) / 2)
                    left, right = max(0, cx - 75), min(source.shape[1], cx + 75)
                    top, bottom = max(0, y2 - 85), min(source.shape[0], y2 + 40)
                    crop = source[top:bottom, left:right]
                    if crop.size == 0:
                        raise RuntimeError('Empty foot-level crop')
                    x, y = (i % 3) * 240, (i // 3) * 180
                    sheet[y:y + 150, x:x + 240] = cv2.resize(crop, (240, 150))
                    cv2.putText(sheet, f'raw {pid} frame {frame}', (x + 4, y + 174),
                                cv2.FONT_HERSHEY_SIMPLEX, .45, (20, 20, 20), 1)
                prefix = f's3_p{point:02d}_f{frame}'
                paths = {'source': out / f'{prefix}_source.jpg',
                         'overlay': out / f'{prefix}_overlay.jpg',
                         'feet': out / f'{prefix}_feet.jpg'}
                hashes = {name: save(path, image) for name, path, image in
                          [('source', paths['source'], source),
                           ('overlay', paths['overlay'], overlay),
                           ('feet', paths['feet'], sheet)]}
                records.append({'set': 3, 'point_number': point, 'near_team_won': outcome == 'win',
                                'source_frame': frame, 'raw_ids': sorted(b['raw_track_id'] for b in boxes),
                                'files': {name: path.name for name, path in paths.items()},
                                'sha256': hashes})
    finally:
        cap.release()
    rule = ('Revised exploratory phase candidate: five consecutive 5 Hz frames ending near '
            'observed opponent front-court action in each point; this revision follows the '
            'first-window failure, and cannot support a prespecified outcome test.'
            if args.phase_aligned else
            'First five consecutive 5 Hz samples of the longest exact-six-ID run, '
            'for set-three point 13 (win) and point 34 (loss), selected before '
            'frame-level ground adjudication; equal 0.8 s spans.')
    index = {'status': 'matched_window_pilot_source_review_pack',
             'selection_rule': rule,
             'source_sha256': old['source_sha256'],
             'input_sha256': {str(p.relative_to(ROOT)): sha(p)
                              for p in (OLD_TRACKS, OLD_RUNS, NEW_TRACKS)},
             'rows': records}
    (out / 'index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(records)} full-resolution source frames and foot sheets')


if __name__ == '__main__':
    main()
