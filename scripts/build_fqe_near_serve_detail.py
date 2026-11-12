"""Source crops for checking near-side ball-carrier exit versus serve contact."""
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4'
capture = cv2.VideoCapture(str(VIDEO))
for label, times in {
    'p2': [168 + i * .5 for i in range(17)],
    'p4': [212 + i * .25 for i in range(17)],
}.items():
    canvas = Image.new('RGB', (1600, 5 * 410), '#13202a')
    draw = ImageDraw.Draw(canvas)
    for index, seconds in enumerate(times):
        frame = round(seconds * 50)
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, bgr = capture.read()
        if not ok:
            raise RuntimeError(f'Could not decode frame {frame}')
        image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).crop((940, 370, 1920, 1080))
        image.thumbnail((400, 390))
        x, y = (index % 4) * 400, (index // 4) * 410
        canvas.paste(image, (x, y))
        draw.text((x + 8, y + 391), f'{seconds:.2f}s / frame {frame}', fill='white')
    output = ROOT / f'data/processed/fqe_near_serve_detail_{label}.jpg'
    canvas.save(output, quality=90)
    print(output)
capture.release()
