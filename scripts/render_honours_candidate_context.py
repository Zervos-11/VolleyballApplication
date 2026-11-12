"""Render temporal source context around nominal six-player candidate frames."""
import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_annotation_workspace/qc_context'
OFFSETS = (-75, -25, 0, 25, 75)


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    video = ROOT / source['video_file']
    digest = hashlib.sha256()
    with video.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != source['sha256']:
        raise ValueError('Source video hash differs from source record')
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError('Cannot open source video')
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    try:
        for point in audit['points']:
            for row in point['frame_rows']:
                if not row['projection_in_court']:
                    continue
                center = row['frame']
                tiles = []
                for offset in OFFSETS:
                    index = center + offset
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != index + 1:
                        raise RuntimeError(f'Could not decode exact frame {index}')
                    tile = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                    text = f"S{point['set']} P{point['point_number']} frame {index} ({offset:+d})"
                    cv2.putText(tile, text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX,
                                .8, (0, 0, 0), 5, cv2.LINE_AA)
                    cv2.putText(tile, text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX,
                                .8, (255, 255, 255), 2, cv2.LINE_AA)
                    tiles.append(tile)
                import numpy as np
                blank = np.zeros_like(tiles[0])
                sheet = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:] + [blank])])
                filename = f"s{point['set']}_p{point['point_number']}_f{center}_context.jpg"
                cv2.imwrite(str(OUT / filename), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
                manifest.append({'set': point['set'], 'point_number': point['point_number'],
                                 'winner': point['winner'], 'candidate_frame': center,
                                 'context_frames': [center + n for n in OFFSETS],
                                 'sheet': str((OUT / filename).relative_to(ROOT)).replace('\\', '/')})
    finally:
        cap.release()
    (OUT / 'manifest.json').write_text(json.dumps({
        'source_sha256': source['sha256'], 'audit_sha256': hashlib.sha256(AUDIT.read_bytes()).hexdigest(),
        'offsets_frames': OFFSETS, 'rows': manifest}, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(manifest)} context sheets to {OUT}')


if __name__ == '__main__':
    main()
