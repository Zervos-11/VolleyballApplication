"""Render five unboxed S1 P6 source frames from the frozen fixed-window rule."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = MATCH / 'screening'
PROTOCOL = SCREEN / 'source_only_fixed_window_protocol.json'
VIDEO = MATCH / 'source_720p.mp4'
PACK = SCREEN / 's1p6_fixed_window_source_review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = PACK / 'manifest.json'
    if manifest_path.exists():
        raise FileExistsError(f'Frozen source packet already exists: {manifest_path}')
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    row = next(item for item in protocol['rows'] if
               (item['set'], item['point_number']) == (1, 6))
    assert row['status'] == 'frozen_source_navigation_window_pending_frame_review'
    assert sha(VIDEO) == protocol['source_sha256']
    PACK.mkdir(exist_ok=True)
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise RuntimeError('Cannot open source video')
    images = []
    try:
        for frame in row['five_sample_frames']:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok or image.shape[:2] != (720, 1280):
                raise RuntimeError(f'Cannot decode source frame {frame}')
            target = PACK / f'unboxed_{frame}.png'
            if target.exists():
                raise FileExistsError(f'Existing source image: {target}')
            if not cv2.imwrite(str(target), image):
                raise RuntimeError(f'Cannot write {target}')
            images.append({'source_frame': frame, 'image': target.name,
                           'sha256': sha(target)})
    finally:
        capture.release()
    manifest = {'status': 'frozen_unboxed_source_only_review_packet',
                'source_sha256': protocol['source_sha256'],
                'window_protocol_sha256': sha(PROTOCOL),
                'set': 1, 'point_number': 6,
                'window_start_frame_inclusive': row['window_start_frame_inclusive'],
                'window_end_frame_exclusive': row['window_end_frame_exclusive'],
                'five_sample_frames': row['five_sample_frames'],
                'images': images,
                'source_phase_review_status': 'pending',
                'candidate_or_ground_review_status': 'pending'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Rendered {len(images)} unboxed S1 P6 frames')


if __name__ == '__main__':
    main()
