"""Render a source-only frame contact sheet without detector annotations."""

import argparse
from pathlib import Path

import cv2
import numpy as np


def make_sheet(source, first, last, step, columns, out):
    if out.exists():
        raise FileExistsError(out)
    if first < 0 or last < first or step < 1 or columns < 1:
        raise ValueError('Invalid frame range or grid size')
    frames = list(range(first, last + 1, step))
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise FileNotFoundError(source)
    width, height, label_height = 640, 360, 30
    canvas = np.zeros(((height + label_height) * ((len(frames) + columns - 1) // columns),
                       width * columns, 3), dtype=np.uint8)
    try:
        for i, frame in enumerate(frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            x, y = (i % columns) * width, (i // columns) * (height + label_height)
            canvas[y:y + height, x:x + width] = cv2.resize(image, (width, height))
            cv2.putText(canvas, f'frame {frame}', (x + 8, y + height + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 1, cv2.LINE_AA)
    finally:
        cap.release()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), canvas):
        raise OSError(out)
    print(f'{len(frames)} source frames: {out}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--first', type=int, required=True)
    parser.add_argument('--last', type=int, required=True)
    parser.add_argument('--step', type=int, default=5)
    parser.add_argument('--columns', type=int, default=4)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    make_sheet(args.source, args.first, args.last, args.step, args.columns, args.out)
