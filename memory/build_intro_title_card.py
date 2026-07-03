"""Prepend a branded title card to /app/frontend/public/intro-tour.mp4.

Title card:
  - Solid #3D1A78 → #2DB5B5 gradient (SA Coparents brand).
  - "SMARTER COMMUNICATION" (tracked-out eyebrow) above
    "Healthier Co-Parenting" (large serif-ish sans headline).
  - 1080 × 2340 (same canvas as the tour video).
  - Held for 3.0 seconds with a gentle 0.4s fade-in.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 2340
OUT_PNG = Path("/tmp/intro_title_card.png")
OUT_MP4 = Path("/tmp/intro_title_card.mp4")
CURRENT = Path("/app/frontend/public/intro-tour.mp4")
BACKUP = Path("/app/frontend/public/intro-tour.notitle.mp4")
CONCAT_LIST = Path("/tmp/intro_concat.txt")

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def make_vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    base = Image.new("RGB", size, top)
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return base


def add_dot_pattern(img: Image.Image, opacity: int = 22) -> None:
    """Cheap grain/pattern to break up the flat gradient."""
    draw = ImageDraw.Draw(img, "RGBA")
    step = 42
    for y in range(0, img.height, step):
        for x in range(0, img.width, step):
            draw.ellipse((x, y, x + 3, y + 3), fill=(255, 255, 255, opacity))


def draw_centered(draw: ImageDraw.ImageDraw, text: str, font, y: int, color=(255, 255, 255)) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (W - tw) // 2 - bbox[0]
    draw.text((x, y), text, font=font, fill=color)
    return th


def build_card() -> None:
    # Brand gradient (deep royal purple → soft teal, same as the app CTA gradient).
    img = make_vertical_gradient((W, H), top=(61, 26, 120), bottom=(45, 181, 181))
    add_dot_pattern(img, opacity=18)
    draw = ImageDraw.Draw(img)

    # Small eyebrow (all-caps, tracked)
    eyebrow_font = ImageFont.truetype(FONT_BOLD, 46)
    eyebrow_text = "S A   C O P A R E N T S"
    eyebrow_y = int(H * 0.30)
    _ = draw_centered(draw, eyebrow_text, eyebrow_font, eyebrow_y, color=(255, 255, 255))

    # Thin white rule under eyebrow
    line_y = eyebrow_y + 90
    line_w = 260
    draw.line(
        [((W - line_w) // 2, line_y), ((W + line_w) // 2, line_y)],
        fill=(255, 255, 255),
        width=3,
    )

    # Big headline — two lines
    h_font_big = ImageFont.truetype(FONT_BOLD, 138)
    h_font_med = ImageFont.truetype(FONT_BOLD, 138)
    top_line = "Smarter"
    mid_line = "Communication."
    bottom_line1 = "Healthier"
    bottom_line2 = "Co-Parenting."
    # Layout the four lines centered vertically-ish
    start_y = int(H * 0.40)
    y = start_y
    y += draw_centered(draw, top_line, h_font_big, y) + 30
    y += draw_centered(draw, mid_line, h_font_med, y) + 90
    y += draw_centered(draw, bottom_line1, h_font_big, y, color=(232, 226, 255)) + 30
    y += draw_centered(draw, bottom_line2, h_font_med, y, color=(232, 226, 255)) + 60

    # Small footer signature
    sig_font = ImageFont.truetype(FONT_REG, 44)
    draw_centered(draw, "sacoparentsapp.online", sig_font, int(H * 0.85), color=(255, 255, 255, 200))

    img.save(OUT_PNG, "PNG")
    print(f"wrote {OUT_PNG}")


def build_card_video(duration: float = 3.0) -> None:
    """3-second silent MP4 from the still image, with a 0.4s fade-in."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration),
            "-i", str(OUT_PNG),
            "-f", "lavfi", "-t", str(duration),
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-vf", "fade=t=in:st=0:d=0.4,fps=30,scale=1080:2340:flags=lanczos,setsar=1,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(OUT_MP4),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {OUT_MP4}")


def normalize_current() -> Path:
    """Re-encode the current intro-tour.mp4 to match audio params (44.1 kHz stereo)
    so the concat demuxer doesn't complain."""
    norm = Path("/tmp/intro_tour_norm.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(CURRENT),
            "-vf", "scale=1080:2340:flags=lanczos,setsar=1,fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            "-movflags", "+faststart",
            str(norm),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {norm}")
    return norm


def concat(norm_current: Path) -> None:
    CONCAT_LIST.write_text(f"file '{OUT_MP4}'\nfile '{norm_current}'\n")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(CONCAT_LIST),
            "-c", "copy",
            "-movflags", "+faststart",
            str(CURRENT),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {CURRENT}")


def main() -> None:
    # Safety copy of the current narrated-only intro (only if not already saved).
    if not BACKUP.exists():
        BACKUP.write_bytes(CURRENT.read_bytes())
        print(f"backed up current intro to {BACKUP}")

    build_card()
    build_card_video(duration=3.0)
    norm = normalize_current()
    concat(norm)


if __name__ == "__main__":
    main()
