"""Build the /prep/child-goals reflection video.

  1. Generate 45-second narration from the provided script (OpenAI TTS, nova).
  2. Compose a video: loop the branded /public/intro-loop.mp4 background
     while overlaying a warm 'Focus on Your Child' title card, all under
     the narration audio.
  3. Write the result to /app/frontend/public/videos/child-goals-reflection.mp4.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

from emergentintegrations.llm.openai import OpenAITextToSpeech


load_dotenv("/app/backend/.env")

W, H = 1080, 1350  # match /public/intro-loop.mp4 size

BACKGROUND = Path("/app/frontend/public/intro-loop.mp4")
OUT_MP4 = Path("/app/frontend/public/videos/child-goals-reflection.mp4")
OUT_MP4.parent.mkdir(parents=True, exist_ok=True)
NARRATION = Path("/tmp/child-goals-narration.mp3")
CARD_PNG = Path("/tmp/child-goals-card.png")

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

SCRIPT = (
    "Before you get started, we'd like to ask you to take a moment and think about "
    "your child. "
    "Every parent wants their child to grow up feeling happy, safe, loved, and "
    "supported. Even though your family may be changing, your child's need for "
    "caring, involved parents remains the same. "
    "As you answer these questions, try to picture your child's future. What are your "
    "hopes for them? What values would you like them to learn? What do they need from "
    "you to grow into a healthy, confident, and resilient person? "
    "Don't worry about finding the right answers. Simply share what matters most to "
    "you as a parent."
)


async def generate_narration() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT,
        model="tts-1-hd",
        voice="shimmer",
        speed=1.0,
    )
    NARRATION.write_bytes(audio_bytes)
    print(f"wrote {NARRATION} ({len(audio_bytes) // 1024} KB)")


def build_title_card_overlay() -> None:
    """Semi-transparent overlay with the reflection prompt title.

    The overlay is transparent so the intro-loop gradient still shows through.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Subtle dark scrim across the bottom third for legibility.
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    scrim_draw = ImageDraw.Draw(scrim)
    for y in range(int(H * 0.35), H):
        t = (y - int(H * 0.35)) / (H - int(H * 0.35))
        alpha = int(140 * t)
        scrim_draw.line([(0, y), (W, y)], fill=(20, 12, 40, alpha))
    img = Image.alpha_composite(img, scrim)
    draw = ImageDraw.Draw(img)

    # Eyebrow
    eyebrow_font = ImageFont.truetype(FONT_BOLD, 34)
    eyebrow = "A   M O M E N T   O F   R E F L E C T I O N"
    bbox = draw.textbbox((0, 0), eyebrow, font=eyebrow_font)
    tw = bbox[2] - bbox[0]
    ex = (W - tw) // 2 - bbox[0]
    ey = int(H * 0.60)
    draw.text((ex, ey), eyebrow, font=eyebrow_font, fill=(232, 226, 255, 235))

    # Divider
    divider_y = ey + 68
    draw.line(
        [((W - 220) // 2, divider_y), ((W + 220) // 2, divider_y)],
        fill=(255, 255, 255, 200),
        width=3,
    )

    # Headline
    head_font = ImageFont.truetype(FONT_BOLD, 96)
    head1 = "Focus on"
    head2 = "your child."
    y = divider_y + 46
    for line in (head1, head2):
        bbox = draw.textbbox((0, 0), line, font=head_font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2 - bbox[0]
        draw.text((x, y), line, font=head_font, fill=(255, 255, 255, 245))
        y += 118

    # Subtitle
    sub_font = ImageFont.truetype(FONT_REG, 36)
    sub = "45 seconds. Then answer with your heart."
    bbox = draw.textbbox((0, 0), sub, font=sub_font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2 - bbox[0]
    draw.text((x, y + 24), sub, font=sub_font, fill=(220, 214, 240, 220))

    img.save(CARD_PNG, "PNG")
    print(f"wrote {CARD_PNG}")


def compose(duration_s: float) -> None:
    """FFmpeg compose:
      background = intro-loop.mp4 looped for `duration_s`
      overlay    = static title-card PNG on top
      audio      = the new narration
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(BACKGROUND),
            "-i", str(CARD_PNG),
            "-i", str(NARRATION),
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
            str(OUT_MP4),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {OUT_MP4}")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
    )
    return float(out.strip())


async def main() -> None:
    await generate_narration()
    audio_len = probe_duration(NARRATION)
    print(f"narration duration = {audio_len:.2f}s")
    build_title_card_overlay()
    # Video length = narration + 0.6s tail so the fade-out doesn't clip audio.
    compose(duration_s=audio_len + 0.6)


if __name__ == "__main__":
    asyncio.run(main())
