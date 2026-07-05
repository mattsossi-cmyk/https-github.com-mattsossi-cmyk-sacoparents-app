"""Batch-produce four 'Watch First' reflection videos for the guided journey.

Reuses the existing Listen First narrations as the audio track and composes
each with a warm branded title card + a looped intro-loop.mp4 background.

Outputs:
  /app/frontend/public/videos/safety-assessment-reflection.mp4
  /app/frontend/public/videos/comm-style-reflection.mp4
  /app/frontend/public/videos/reflection-foundation.mp4
  /app/frontend/public/videos/readiness-reflection.mp4
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1350
BACKGROUND = Path("/app/frontend/public/intro-loop.mp4")
OUT_DIR = Path("/app/frontend/public/videos")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# (narration_mp3, output_mp4, eyebrow_text, headline_lines, subtitle)
STEPS = [
    (
        Path("/app/frontend/public/audio/listen-first/step-ipv-assessment.mp3"),
        OUT_DIR / "safety-assessment-reflection.mp4",
        "S A F E T Y   F I R S T",
        ("Understand", "your safety."),
        "Take a moment before you begin the assessment.",
    ),
    (
        Path("/app/frontend/public/audio/listen-first/step-2-coparenting-relationship.mp3"),
        OUT_DIR / "comm-style-reflection.mp4",
        "S T E P   T W O",
        ("Understand", "your relationship."),
        "Reflect on how you and the other parent communicate.",
    ),
    (
        Path("/app/frontend/public/audio/listen-first/step-4-foundation-statement.mp3"),
        OUT_DIR / "reflection-foundation.mp4",
        "S T E P   F O U R",
        ("Create your", "Foundation Statement."),
        "Describe the future you want for your child.",
    ),
    (
        Path("/app/frontend/public/audio/listen-first/step-5-prepare-mediation.mp3"),
        OUT_DIR / "readiness-reflection.mp4",
        "S T E P   F I V E",
        ("Prepare for", "mediation."),
        "Walk in with a child-focused foundation.",
    ),
]


def build_title_card(eyebrow: str, headline_lines: tuple, subtitle: str, out_png: Path) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    scrim_draw = ImageDraw.Draw(scrim)
    for y in range(int(H * 0.35), H):
        t = (y - int(H * 0.35)) / (H - int(H * 0.35))
        alpha = int(140 * t)
        scrim_draw.line([(0, y), (W, y)], fill=(20, 12, 40, alpha))
    img = Image.alpha_composite(img, scrim)
    draw = ImageDraw.Draw(img)

    eyebrow_font = ImageFont.truetype(FONT_BOLD, 34)
    bbox = draw.textbbox((0, 0), eyebrow, font=eyebrow_font)
    tw = bbox[2] - bbox[0]
    ex = (W - tw) // 2 - bbox[0]
    ey = int(H * 0.58)
    draw.text((ex, ey), eyebrow, font=eyebrow_font, fill=(232, 226, 255, 235))

    divider_y = ey + 68
    draw.line(
        [((W - 220) // 2, divider_y), ((W + 220) // 2, divider_y)],
        fill=(255, 255, 255, 200),
        width=3,
    )

    head_font = ImageFont.truetype(FONT_BOLD, 92)
    y = divider_y + 46
    for line in headline_lines:
        bbox = draw.textbbox((0, 0), line, font=head_font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2 - bbox[0]
        draw.text((x, y), line, font=head_font, fill=(255, 255, 255, 245))
        y += 112

    sub_font = ImageFont.truetype(FONT_REG, 32)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2 - bbox[0]
    draw.text((x, y + 20), subtitle, font=sub_font, fill=(220, 214, 240, 220))

    img.save(out_png, "PNG")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
    )
    return float(out.strip())


def compose(narration: Path, card_png: Path, out_mp4: Path, duration_s: float) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(BACKGROUND),
            "-i", str(card_png),
            "-i", str(narration),
            "-filter_complex",
            "[0:v]scale=1080:1350:flags=lanczos,setsar=1,fps=30,format=yuv420p[bg];"
            "[bg][1:v]overlay=(W-w)/2:(H-h)/2,fade=t=in:st=0:d=0.6,fade=t=out:st="
            + f"{duration_s - 0.6:.2f}"
            + ":d=0.6[v]",
            "-map", "[v]", "-map", "2:a",
            "-t", f"{duration_s:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    for narration, out_mp4, eyebrow, headline, subtitle in STEPS:
        card_png = Path("/tmp") / f"card-{out_mp4.stem}.png"
        build_title_card(eyebrow, headline, subtitle, card_png)
        audio_len = probe_duration(narration)
        compose(narration, card_png, out_mp4, audio_len + 0.6)
        size_kb = out_mp4.stat().st_size // 1024
        print(f"wrote {out_mp4.name} ({audio_len + 0.6:.1f}s, {size_kb} KB)")


if __name__ == "__main__":
    main()
