"""Render source-only contact frames for the user-requested reserve switch."""

from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "data/processed/source_view_screen/ucla_gcu_selection.mp4"
OUTPUT = ROOT / "data/processed/source_view_screen/ucla_gcu_selection_2s_sheet.jpg"
FINE_OUTPUT = ROOT / "data/processed/source_view_screen/ucla_gcu_selection_serve_fine.jpg"


def main() -> None:
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    seconds = range(0, min(60, int(frames / fps)), 2)
    width, height = 320, 180
    columns = 5
    rows = (len(seconds) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * width, rows * (height + 20)), "#111923")
    draw = ImageDraw.Draw(sheet)
    for index, sec in enumerate(seconds):
        frame_number = round(sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(cv2.resize(frame, (width, height)), cv2.COLOR_BGR2RGB)
        x = (index % columns) * width
        y = (index // columns) * (height + 20)
        sheet.paste(Image.fromarray(rgb), (x, y))
        draw.text((x + 4, y + height + 2), f"excerpt +{sec:02d}s, frame {frame_number}", fill="white")
    cap.release()
    sheet.save(OUTPUT, quality=88)
    print(OUTPUT)

    cap = cv2.VideoCapture(str(VIDEO))
    fine = Image.new("RGB", (4 * 480, 7 * 290), "#111923")
    fine_draw = ImageDraw.Draw(fine)
    for index in range(28):
        sec = 14 + index * 0.5
        frame_number = round(sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(cv2.resize(frame, (480, 270)), cv2.COLOR_BGR2RGB)
        x = (index % 4) * 480
        y = (index // 4) * 290
        fine.paste(Image.fromarray(rgb), (x, y))
        fine_draw.text((x + 4, y + 272), f"+{sec:.1f}s, frame {frame_number}", fill="white")
    cap.release()
    fine.save(FINE_OUTPUT, quality=92)
    print(FINE_OUTPUT)


if __name__ == "__main__":
    main()
