"""Make a sparse visual check around audio tone candidates in the source match."""
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4'
OUT = ROOT / 'data/processed/fqe_serve_audio_visual_check.jpg'
TIMES = [164.5, 165.5, 166.5, 167.5, 168.5, 169.5,
         188.5, 189.5, 190.5, 191.5, 192.5, 193.5,
         208.5, 209.5, 210.5, 211.5, 212.5, 213.5]
capture = cv2.VideoCapture(str(VIDEO))
canvas = Image.new('RGB', (1440, 6 * 290), '#13202a')
draw = ImageDraw.Draw(canvas)
for i, seconds in enumerate(TIMES):
    frame = round(seconds * 50)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, bgr = capture.read()
    if not ok:
        raise RuntimeError(f'Could not decode frame {frame}')
    image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    image.thumbnail((480, 270))
    x, y = (i % 3) * 480, (i // 3) * 290
    canvas.paste(image, (x, y))
    draw.text((x + 8, y + 272), f'{seconds:.1f}s / frame {frame}', fill='white')
capture.release()
canvas.save(OUT, quality=88)
print(OUT)
