"""Create unboxed S3 P34 event contact sheets from the existing hash-bound packet."""

from pathlib import Path
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_independent_review_pack"
OUT = ROOT / "data/matches/yt_u5HnY2aNW14/screening/s3p34_event_boundary_diagnostic"


def render(name: str, frames: range) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    width, height, cols = 640, 380, 3
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width, rows * height), "#101820")
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(frames):
        path = PACK / f"unboxed_{frame}.png"
        if not path.exists():
            raise FileNotFoundError(path)
        with Image.open(path) as original:
            image = original.convert("RGB").resize((width, 360))
        x, y = i % cols * width, i // cols * height
        sheet.paste(image, (x, y + 20))
        draw.text((x + 6, y + 3), f"Source frame {frame}", fill="white")
    target = OUT / name
    sheet.save(target, quality=90)
    print(target)


def render_serve_detail() -> None:
    frames = range(35990, 36001)
    width, height, cols = 520, 500, 4
    sheet = Image.new("RGB", (cols * width, 3 * height), "#101820")
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(frames):
        with Image.open(PACK / f"unboxed_{frame}.png") as original:
            # Native-resolution serve zone around UCLA #12 and the tossed ball.
            image = original.convert("RGB").crop((650, 240, 1170, 720))
        x, y = i % cols * width, i // cols * height
        sheet.paste(image, (x, y + 20))
        draw.text((x + 6, y + 3), f"Source frame {frame}", fill="white")
    target = OUT / "serve_contact_detail.jpg"
    sheet.save(target, quality=92)
    print(target)


if __name__ == "__main__":
    render("serve_contact.jpg", range(35986, 36001))
    render("point_end.jpg", range(36138, 36151))
    render_serve_detail()
