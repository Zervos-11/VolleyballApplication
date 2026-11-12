"""Create seeded temporal pilot windows and real-frame contact sheets, not labels."""
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np


def contact_sheets(video, directory, name, frames, fps, columns=4, per_page=16):
    cap = cv2.VideoCapture(str(video))
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    try:
        for page_start in range(0, len(frames), per_page):
            batch = frames[page_start:page_start + per_page]
            sheet = np.zeros((300 * ((len(batch) + columns - 1) // columns), 480 * columns, 3), np.uint8)
            for i, index in enumerate(batch):
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f'Cannot decode frame {index}')
                thumb = cv2.resize(frame, (480, 270))
                y, x = (i // columns) * 300, (i % columns) * 480
                sheet[y:y + 270, x:x + 480] = thumb
                t = index / fps
                cv2.putText(sheet, f'{int(t // 60):02}:{t % 60:05.2f}  f{index}', (x + 8, y + 292),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            path = directory / f'{name}_{page_start // per_page + 1:02d}.jpg'
            if not cv2.imwrite(str(path), sheet):
                raise OSError(path)
            paths.append(path.as_posix())
    finally:
        cap.release()
    return paths


def prepare(match, seed=20261009):
    record = json.loads((match / 'source_record.json').read_text(encoding='utf-8'))
    fps = record['camera']['fps']
    count = record['frame_count']
    video = Path(record['video_file'])
    # Keep initial/final two minutes out of this pilot sampling frame, explicitly.
    lower, upper = round(120 * fps), count - round(120 * fps)
    length = round(60 * fps)
    if upper - lower < 5 * length:
        raise ValueError('Source too short for this five-window design')
    rng = random.Random(seed)
    windows = []
    out = match / 'pilot'
    if (out / 'review_windows.json').exists():
        raise ValueError('Review windows already exist; preserve the recorded selection')
    for i in range(5):
        left = lower + (upper - lower) * i // 5
        right = lower + (upper - lower) * (i + 1) // 5
        start = rng.randint(left, right - length)
        # Quantise before viewing for easy second-based review; preserve bounds.
        start = max(left, (start // round(fps)) * round(fps))
        frames = list(range(start, start + length, round(2 * fps)))
        windows.append(dict(window_id=f'w{i + 1}', stratum=f'time_quintile_{i + 1}',
                            stratum_start_frame=left, stratum_end_frame_exclusive=right,
                            start_frame=start, end_frame_exclusive=start + length,
                            t_start=start / fps, t_end=(start + length) / fps,
                            contact_sheets=contact_sheets(video, out / 'windows', f'w{i + 1}', frames, fps)))
    report = dict(match_id=match.name, seed=seed, design='five temporal strata; one seeded 60-second window each',
                  sampling_frame_start=lower, sampling_frame_end_exclusive=upper,
                  purpose='development pilot; not an unbiased full-match rally sample',
                  boundary_status='not_annotated', windows=windows)
    (out / 'review_windows.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--match-dir', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.match_dir)
