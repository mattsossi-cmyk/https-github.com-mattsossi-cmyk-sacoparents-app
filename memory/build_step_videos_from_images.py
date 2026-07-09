"""Compose 7 reflection videos, each using its unique watercolor image
as the full-bleed backdrop with a subtle domain footer for polish.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


AUDIO_ROOT = Path("/app/frontend/public/audio/listen-first")
IMG_ROOT = Path("/app/frontend/public/images/steps")
VIDEO_ROOT = Path("/app/frontend/public/videos")
VIDEO_ROOT.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

PURPLE_BG = (61, 26, 120)    # #3D1A78 — brand primary
# All 7 module step videos land on the brand-purple matte.
# For the 5 images whose PNGs already have the purple frame baked in
# (child-goals, issues, priority, comm-style, readiness), image_scale=1.0
# fills the canvas — the existing PNG frame provides the visible purple
# border. The other 2 (safety-assessment, foundation) still get the ffmpeg
# purple pad at 0.88 scale to produce the same look.
STEPS = [
    ("step-safety-assessment.png", "step-ipv-assessment.mp3",         VIDEO_ROOT / "safety-assessment-reflection.mp4", PURPLE_BG, 0.88),
    ("step-comm-style.png",        "step-2-coparenting-relationship.mp3", VIDEO_ROOT / "comm-style-reflection.mp4",   PURPLE_BG, 1.00),
    ("step-child-goals.png",       "step-3-child-needs.mp3",          VIDEO_ROOT / "child-goals-reflection.mp4",     PURPLE_BG, 1.00),
    ("step-issues.png",            "step-issues.mp3",                 VIDEO_ROOT / "issues-reflection.mp4",          PURPLE_BG, 1.00),
    ("step-priority.png",          "step-priority.mp3",               VIDEO_ROOT / "priority-reflection.mp4",        PURPLE_BG, 1.00),
    ("step-foundation.png",        "step-4-foundation-statement.mp3", VIDEO_ROOT / "reflection-foundation.mp4",      PURPLE_BG, 0.88),
    ("step-readiness.png",         "step-5-prepare-mediation.mp3",    VIDEO_ROOT / "readiness-reflection.mp4",       PURPLE_BG, 1.00),
]


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
    )
    return float(out.strip())


def prepare_card(img_path: Path, out_png: Path, bg_color: tuple = (248, 246, 238), image_scale: float = 1.0) -> None:
    """Fit the illustration into a 1080x1350 canvas.

    * ``bg_color``   — canvas fill (defaults to warm cream ``#F8F6EE``).
    * ``image_scale`` — 1.0 means fit-cover (no visible background around
      the illustration). Values <1.0 letterbox the image inside a bg_color
      matte (used to render a brand-purple frame around specific steps).
    Always renders a subtle domain footer with a bottom scrim for legibility.
    """
    W, H = 1080, 1350
    canvas = Image.new("RGB", (W, H), bg_color)
    img = Image.open(img_path).convert("RGB")

    if image_scale >= 1.0:
        # Fit-cover to 1080 wide, then crop / letterbox to 1350 tall.
        scale = W / img.width
        new_h = int(img.height * scale)
        img = img.resize((W, new_h), Image.LANCZOS)
        if new_h >= H:
            top = (new_h - H) // 3  # bias upward so faces aren't clipped
            img = img.crop((0, top, W, top + H))
            canvas = img
        else:
            y = (H - new_h) // 2 - 40
            y = max(0, y)
            canvas.paste(img, (0, y))
    else:
        # Fit-inside a scaled inner box → visible bg_color matte around it.
        inner_w = int(W * image_scale)
        inner_h = int(H * image_scale)
        img_ratio = img.width / img.height
        box_ratio = inner_w / inner_h
        if img_ratio > box_ratio:
            fit_w = inner_w
            fit_h = int(inner_w / img_ratio)
        else:
            fit_h = inner_h
            fit_w = int(inner_h * img_ratio)
        img = img.resize((fit_w, fit_h), Image.LANCZOS)
        # Slight upward bias so the domain footer has breathing room
        y_offset = ((H - fit_h) // 2) - 20
        y_offset = max((H - inner_h) // 2, y_offset)
        canvas.paste(img, ((W - fit_w) // 2, y_offset))

    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Bottom scrim for domain legibility
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    scrim_draw = ImageDraw.Draw(scrim)
    scrim_start = int(H * 0.87)
    for y in range(scrim_start, H):
        t = (y - scrim_start) / max(1, H - scrim_start)
        alpha = int(90 * t)
        scrim_draw.line([(0, y), (W, y)], fill=(20, 12, 40, alpha))
    canvas = Image.alpha_composite(canvas, scrim)

    # Domain footer
    draw = ImageDraw.Draw(canvas)
    dom_font = ImageFont.truetype(FONT_REG, int(H * 0.026))
    dom = "sacoparentsapp.online"
    bbox = draw.textbbox((0, 0), dom, font=dom_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((W - tw) // 2 - bbox[0], int(H * 0.94)),
        dom,
        font=dom_font,
        fill=(255, 255, 255, 220),
    )

    canvas.convert("RGB").save(out_png, "PNG")


def compose(card_png: Path, narration: Path, out_mp4: Path) -> None:
    duration = probe_duration(narration) + 0.6
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-t", f"{duration:.2f}", "-i", str(card_png),
            "-i", str(narration),
            "-vf", (
                f"scale=1080:1350:flags=lanczos,setsar=1,fps=30,format=yuv420p,"
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


def main() -> None:
    for img_name, narration_name, out_mp4, bg_color, image_scale in STEPS:
        img_path = IMG_ROOT / img_name
        narration = AUDIO_ROOT / narration_name
        card_png = Path("/tmp") / f"card-{out_mp4.stem}.png"
        prepare_card(img_path, card_png, bg_color=bg_color, image_scale=image_scale)
        compose(card_png, narration, out_mp4)
        size_kb = out_mp4.stat().st_size // 1024
        print(f"wrote {out_mp4.name} ({size_kb} KB)")


if __name__ == "__main__":
    main()
