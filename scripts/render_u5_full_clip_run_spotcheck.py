"""Render source frames for a bounded visual check of the longest raw-ID runs."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening/full_clip_track_screen.json'
AUDIT = BASE / 'screening/full_clip_tracklet_audit.json'
VIDEO = BASE / 'source_720p.mp4'
OUT_DIR = BASE / 'screening/full_clip_run_spotcheck'
SELECTED = ((1, 5), (3, 34))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    assert audit['input_sha256']['full_clip_screen'] == sha(SCREEN)
    by_screen = {(p['set'], p['point_number']): p for p in screen['points']}
    by_audit = {(p['set'], p['point_number']): p for p in audit['points']}
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {'source_sha256': screen['source_sha256'],
                'screen_sha256': sha(SCREEN), 'audit_sha256': sha(AUDIT), 'rows': []}
    try:
        for key in SELECTED:
            run = by_audit[key]['longest_same_six_raw_id_run_full_clip']
            frames = [run['first_frame'],
                      run['first_frame'] + 6 * (run['sampled_frames'] // 2),
                      run['last_frame']]
            rows = {r['source_frame']: r for r in by_screen[key]['rows']}
            panels = []
            for frame in frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame + 1
                for p in rows[frame]['proposals']:
                    if p['raw_track_id'] not in run['raw_track_ids']:
                        continue
                    x1, y1, x2, y2 = map(round, p['bbox_px'])
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 225, 255), 2)
                    cv2.putText(image, f"ID {p['raw_track_id']}", (x1, max(18, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 3)
                    cv2.putText(image, f"ID {p['raw_track_id']}", (x1, max(18, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 225, 255), 1)
                cv2.putText(image, f'S{key[0]} P{key[1]} source f{frame}',
                            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 4)
                cv2.putText(image, f'S{key[0]} P{key[1]} source f{frame}',
                            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
                panels.append(cv2.resize(image, (960, 540)))
            sheet = cv2.hconcat(panels)
            path = OUT_DIR / f's{key[0]}_p{key[1]:02d}_first_middle_last.png'
            assert cv2.imwrite(str(path), sheet)
            manifest['rows'].append({'set': key[0], 'point_number': key[1],
                                     'frames': frames, 'image': path.relative_to(BASE).as_posix(),
                                     'image_sha256': sha(path)})
    finally:
        cap.release()
    (OUT_DIR / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(manifest['rows'])


if __name__ == '__main__':
    main()
