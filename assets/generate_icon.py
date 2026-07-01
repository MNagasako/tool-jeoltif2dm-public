"""
Generate J2DM.ico for use as the PyInstaller executable icon.
Run once at build time: python assets/generate_icon.py
Requires Pillow (pip install Pillow).
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "J2DM.ico")

BG       = (26, 42, 74)    # dark navy
ACCENT   = (0, 180, 220)   # cyan
WHITE    = (255, 255, 255)
GRAY     = (160, 180, 200)


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded-rect background
    r = max(2, size // 8)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)

    # Try to load a system font; fall back to default
    font_big = font_small = None
    for name in ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            font_big   = ImageFont.truetype(name, max(6, size * 45 // 100))
            font_small = ImageFont.truetype(name, max(4, size * 22 // 100))
            break
        except OSError:
            continue
    if font_big is None:
        font_big = font_small = ImageFont.load_default()

    # Top label "J2DM"
    top_text = "J2DM"
    bbox = d.textbbox((0, 0), top_text, font=font_big)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = int(size * 0.12) - bbox[1]
    d.text((tx, ty), top_text, font=font_big, fill=WHITE)

    # Bottom label "TIFF" in accent colour
    bot_text = "TIFF"
    bbox2 = d.textbbox((0, 0), bot_text, font=font_small)
    bw, bh = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
    bx = (size - bw) // 2 - bbox2[0]
    by = size - int(size * 0.16) - bh - bbox2[1]
    d.text((bx, by), bot_text, font=font_small, fill=ACCENT)

    # Thin separator line
    lw = max(1, size // 64)
    ly = int(size * 0.76)
    d.rectangle([size // 8, ly, size * 7 // 8, ly + lw], fill=ACCENT)

    return img


def main():
    sizes = [16, 32, 48, 64, 128, 256]
    frames = [make_frame(s) for s in sizes]
    frames[0].save(
        OUTPUT,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Icon saved to {OUTPUT}")


if __name__ == "__main__":
    main()
