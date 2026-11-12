"""Show each S3 P34 30-fps frame with a missing near-side candidate."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening/two_long_runs_30fps_screen.json'
VIDEO = BASE / 'source_720p.mp4'
OUT = BASE / 'screening/full_clip_run_spotcheck'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    point = next(p for p in screen['points'] if (p['set'], p['point_number']) == (3, 34))
    frames = [r for r in point['rows'] if r['near_candidate_count'] == 5]
    assert len(frames) == 10
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    panels = []
    try:
        for row in frames:
            frame = row['source_frame']
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame + 1
            for p in row['proposals']:
                if p['net_side_status'] != 'near_floor_side_candidate':
                    continue
                x1, y1, x2, y2 = map(round, p['bbox_px'])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 220, 0), 2)
                cv2.putText(image, f"ID{p['raw_track_id']}", (x1, max(17, y1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 3)
                cv2.putText(image, f"ID{p['raw_track_id']}", (x1, max(17, y1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 220, 0), 1)
            cv2.putText(image, f'S3 P34 frame {frame}', (18, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 4)
            cv2.putText(image, f'S3 P34 frame {frame}', (18, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
            panels.append(cv2.resize(image, (800, 450)))
    finally:
        cap.release()
    manifest = {'source_sha256': screen['source_sha256'],
                'dense_screen_sha256': sha(SCREEN), 'sheets': []}
    for page in range(2):
        sheet = cv2.vconcat(panels[page * 5:(page + 1) * 5])
        path = OUT / f's3_p34_30fps_missing_{page + 1}.png'
        assert cv2.imwrite(str(path), sheet)
        manifest['sheets'].append({'page': page + 1,
                                   'frames': [r['source_frame'] for r in frames[page * 5:(page + 1) * 5]],
                                   'image': path.relative_to(BASE).as_posix(),
                                   'image_sha256': sha(path)})
    (OUT / 's3_p34_30fps_missing_manifest.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(manifest['sheets'])


if __name__ == '__main__':
    main()
