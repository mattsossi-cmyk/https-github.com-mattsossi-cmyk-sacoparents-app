"""Batch-rebuild ALL guided-journey videos as 'logo screen' videos.

Each output video is:
  - Purple → teal SA Coparents brand gradient background (1080x1350)
  - SA Coparents logo centered
  - Small tagline underneath ("Smarter Communication · Healthier Co-Parenting")
  - The step's narration audio
  - 0.5s fade-in at the start and 0.5s fade-out at the end

Also rebuilds /intro-tour.mp4 as the logo screen + intro narration.

Outputs:
  /app/frontend/public/videos/safety-assessment-reflection.mp4
  /app/frontend/public/videos/comm-style-reflection.mp4
  /app/frontend/public/videos/child-goals-reflection.mp4
  /app/frontend/public/videos/reflection-foundation.mp4
  /app/frontend/public/videos/readiness-reflection.mp4
  /app/frontend/public/videos/issues-reflection.mp4       (NEW)
  /app/frontend/public/videos/priority-reflection.mp4     (NEW)
  /app/frontend/public/intro-tour.mp4                     (rebuilt)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


AUDIO_ROOT = Path("/app/frontend/public/audio/listen-first")
VIDEO_ROOT = Path("/app/frontend/public/videos")
VIDEO_ROOT.mkdir(parents=True, exist_ok=True)

LOGO_PATH = Path("/app/frontend/public/sa-coparents-logo.png")
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

CARD_PORTRAIT_SM = Path("/tmp/logo_card_1080x1350.png")   # for reflection videos
CARD_PORTRAIT_TALL = Path("/tmp/logo_card_1080x2340.png")  # for intro (matches existing intro dims)


def make_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, top)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def dot_pattern(img: Image.Image, opacity: int = 22) -> None:
    draw = ImageDraw.Draw(img, "RGBA")
    step = 42
    for y in range(0, img.height, step):
        for x in range(0, img.width, step):
            draw.ellipse((x, y, x + 3, y + 3), fill=(255, 255, 255, opacity))


def build_logo_card(size: tuple[int, int], out_png: Path) -> None:
    W, H = size
    bg = make_gradient((W, H), (61, 26, 120), (45, 181, 181))  # #3D1A78 -> #2DB5B5
    dot_pattern(bg, opacity=18)

    # Load and scale the logo — keep aspect, fit to 70% of width.
    logo = Image.open(LOGO_PATH).convert("RGBA")
    target_w = int(W * 0.72)
    scale = target_w / logo.width
    logo = logo.resize((target_w, int(logo.height * scale)), Image.LANCZOS)

    canvas = bg.convert("RGBA")
    lx = (W - logo.width) // 2
    ly = int(H * 0.36) - logo.height // 2
    canvas.alpha_composite(logo, dest=(lx, ly))

    # Divider
    draw = ImageDraw.Draw(canvas)
    div_y = ly + logo.height + int(H * 0.03)
    draw.line(
        [((W - 240) // 2, div_y), ((W + 240) // 2, div_y)],
        fill=(255, 255, 255, 220),
        width=3,
    )

    # Tagline
    tag_font = ImageFont.truetype(FONT_BOLD, int(H * 0.030))
    tag = "S M A R T E R   C O M M U N I C A T I O N"
    bbox = draw.textbbox((0, 0), tag, font=tag_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((W - tw) // 2 - bbox[0], div_y + int(H * 0.03)),
        tag,
        font=tag_font,
        fill=(255, 255, 255, 240),
    )
    tag2 = "H E A L T H I E R   C O - P A R E N T I N G"
    bbox = draw.textbbox((0, 0), tag2, font=tag_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((W - tw) // 2 - bbox[0], div_y + int(H * 0.07)),
        tag2,
        font=tag_font,
        fill=(232, 226, 255, 235),
    )

    # Domain footer
    dom_font = ImageFont.truetype(FONT_REG, int(H * 0.026))
    dom = "sacoparentsapp.online"
    bbox = draw.textbbox((0, 0), dom, font=dom_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((W - tw) // 2 - bbox[0], int(H * 0.90)),
        dom,
        font=dom_font,
        fill=(255, 255, 255, 200),
    )

    canvas.convert("RGB").save(out_png, "PNG")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
    )
    return float(out.strip())


def compose(card_png: Path, narration: Path, out_mp4: Path, size: tuple[int, int]) -> None:
    duration = probe_duration(narration) + 0.6
    W, H = size
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-t", f"{duration:.2f}", "-i", str(card_png),
            "-i", str(narration),
            "-vf", (
                f"scale={W}:{H}:flags=lanczos,setsar=1,fps=30,format=yuv420p,"
                f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration - 0.5:.2f}:d=0.5"
            ),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )


# (narration filename, output mp4 path)
STEP_MAP = [
    ("step-ipv-assessment.mp3", VIDEO_ROOT / "safety-assessment-reflection.mp4"),
    ("step-2-coparenting-relationship.mp3", VIDEO_ROOT / "comm-style-reflection.mp4"),
    ("step-3-child-needs.mp3", VIDEO_ROOT / "child-goals-reflection.mp4"),
    ("step-4-foundation-statement.mp3", VIDEO_ROOT / "reflection-foundation.mp4"),
    ("step-5-prepare-mediation.mp3", VIDEO_ROOT / "readiness-reflection.mp4"),
    ("step-issues.mp3", VIDEO_ROOT / "issues-reflection.mp4"),
    ("step-priority.mp3", VIDEO_ROOT / "priority-reflection.mp4"),
]


def main() -> None:
    build_logo_card((1080, 1350), CARD_PORTRAIT_SM)
    print(f"wrote {CARD_PORTRAIT_SM}")
    build_logo_card((1080, 2340), CARD_PORTRAIT_TALL)
    print(f"wrote {CARD_PORTRAIT_TALL}")

    for narration_name, out_mp4 in STEP_MAP:
        narration = AUDIO_ROOT / narration_name
        compose(CARD_PORTRAIT_SM, narration, out_mp4, (1080, 1350))
        size_kb = out_mp4.stat().st_size // 1024
        print(f"wrote {out_mp4.name} ({size_kb} KB)")

    # Intro video: 1080x2340 tall
    intro_narration = Path("/app/frontend/public/intro-narration.mp3")
    intro_out = Path("/app/frontend/public/intro-tour.mp4")
    compose(CARD_PORTRAIT_TALL, intro_narration, intro_out, (1080, 2340))
    print(f"wrote {intro_out.name} ({intro_out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
