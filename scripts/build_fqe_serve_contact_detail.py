"""Frame-level serve contact sheets for two visible near-side servers."""
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4'
capture = cv2.VideoCapture(str(VIDEO))
for label, frames in {'p2': range(8540, 8581, 2), 'p4': range(10680, 10711, 2)}.items():
    columns = 4
    rows = (len(frames) + columns - 1) // columns
    canvas = Image.new('RGB', (columns * 400, rows * 360), '#13202a')
    draw = ImageDraw.Draw(canvas)
    for i, frame in enumerate(frames):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, bgr = capture.read()
        if not ok:
            raise RuntimeError(f'Could not decode frame {frame}')
        image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).crop((900, 220, 1920, 1080))
        image.thumbnail((400, 340))
        x, y = (i % columns) * 400, (i // columns) * 360
        canvas.paste(image, (x, y))
        draw.text((x + 8, y + 342), f'{frame} / {frame / 50:.2f}s', fill='white')
    output = ROOT / f'data/processed/fqe_serve_contact_detail_{label}.jpg'
    canvas.save(output, quality=92)
    print(output)
capture.release()
