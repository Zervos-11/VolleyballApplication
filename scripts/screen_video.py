#!/usr/bin/env python3
"""Measure a local source video and extract reproducible frames for manual screening."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


def screen(video, out):
    if not video.is_file():
        raise ValueError(f'Video missing: {video}')
    cap = cv2.VideoCapture(str(video))
    try:
        if not cap.isOpened():
            raise ValueError(f'Cannot decode {video}')
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if min(width, height, fps, count) <= 0:
            raise ValueError('Invalid video properties')
        duration = count / fps
        indices = sorted(set(int(i) for i in np.linspace(0, count - 1, 12)))
        out.mkdir(parents=True, exist_ok=True)
        tiles, samples = [], []
        for index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok or frame is None:
                samples.append({'frame_index': index, 'decoded': False})
                continue
            name = f'frame_{index:07d}.jpg'
            if not cv2.imwrite(str(out / name), frame):
                raise OSError(f'Could not save {name}')
            tile = np.zeros((400, 640, 3), dtype=np.uint8)
            scale = min(640 / width, 360 / height)
            thumb = cv2.resize(frame, (round(width * scale), round(height * scale)))
            tile[:thumb.shape[0], :thumb.shape[1]] = thumb
            seconds = index / fps
            label = f'{int(seconds // 60):02d}:{seconds % 60:05.2f}  frame {index}'
            cv2.putText(tile, label, (10, 386), cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (255, 255, 255), 1, cv2.LINE_AA)
            tiles.append(tile)
            samples.append({'frame_index': index, 'time_s': seconds, 'decoded': True, 'image': name})
        if tiles:
            sheet = np.zeros((400 * ((len(tiles) + 2) // 3), 640 * 3, 3), dtype=np.uint8)
            for i, tile in enumerate(tiles):
                y, x = (i // 3) * 400, (i % 3) * 640
                sheet[y:y + 400, x:x + 640] = tile
            if not cv2.imwrite(str(out / 'contact_sheet.jpg'), sheet):
                raise OSError('Could not save contact sheet')
    finally:
        cap.release()
    digest = hashlib.sha256()
    with video.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    report = {
        'video_file': video.as_posix(), 'bytes': video.stat().st_size,
        'sha256': digest.hexdigest(), 'width': width, 'height': height,
        'fps': fps, 'frame_count': count, 'duration_s': duration,
        'meets_basic_resolution_and_fps_rule': width >= 1280 and height >= 720 and fps >= 25,
        'frame_rate_verified': False, 'sample_frames': samples,
        'screened_at_utc': datetime.now(timezone.utc).isoformat(),
        'limitations': [
            'Nominal FPS and frame count are decoder properties, not a full timestamp continuity check.',
            'Sparse sample frames cannot establish visibility or camera stability for every rally.',
            'Permission, privacy, rally boundaries and label quality require separate review.',
        ],
    }
    (out / 'video_probe.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('sample_frames', 'limitations')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    screen(args.video, args.out)
