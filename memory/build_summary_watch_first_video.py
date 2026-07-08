"""Build the 'Watch First' summary video shown at the top of the Summary
page. Ken-Burns pans across the Summation poster with a warmer, more
personal coaching voice-over (distinct from the Three Reports trailer)
and the same warm-strings pad.

Outputs:
  /app/frontend/public/audio/summary-watch-first.mp3   (voice-over)
  /app/frontend/public/videos/summary-watch-first.mp4  (1080x1350, 55s)
"""
import asyncio
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

FRAME_DIR = Path("/app/memory/summation_frames")
VIDEO_OUT = Path("/app/frontend/public/videos/summary-watch-first.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/summary-watch-first.mp3")
PAD_OUT = Path("/app/memory/_summary_watch_first_pad.wav")

# Slide durations in seconds — sum to TOTAL_SECONDS (fades are additive).
SLIDES = [
    ("01-full.png",       8.0),   # 0-8s    intro / "you made it here"
    ("02-conflict.png",  12.0),   # 8-20s   Conflict Assessment - what to look for
    ("03-foundation.png", 12.0),  # 20-32s  Foundation Statement - what to look for
    ("04-mediation.png", 13.0),   # 32-45s  Mediation Declaration - what to look for
    ("05-tagline.png",   10.0),   # 45-55s  outro / how to use
]
TOTAL_SECONDS = int(sum(d for _, d in SLIDES))
FADE = 0.6

# ~168 words → ~55s at Nova speed 1.05. Distinct, coaching-tone voice-over
# tuned for the moment the parent lands on the Summary page.
SCRIPT = (
    "Take a breath. You just did the hardest part — reflecting honestly, "
    "one step at a time. This is your prepared summary. "
    "The first section is your Conflict Assessment. Read it slowly. "
    "You'll see the patterns that keep pulling you apart, and the small "
    "moves that bring you back to child-first thinking. "
    "The second section is your Foundation Statement. This is the ground "
    "everything else stands on — what your child needs, what matters most "
    "to you, and where you are willing to flex. "
    "The third section is your Mediation Declaration. This is what you "
    "bring to the table — your priorities, agreements you're already "
    "moving toward, and solutions you're ready to propose. "
    "You can download it as a PDF, share it with your mediator, or send "
    "it by email. However you use it, remember — this isn't about winning. "
    "It's about walking in prepared, calm, and centered on your child."
)


async def generate_voiceover() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT,
        model="tts-1-hd",
        voice="nova",
        speed=1.05,
    )
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_OUT.write_bytes(audio_bytes)
    print(f"wrote {AUDIO_OUT} ({len(audio_bytes)//1024} KB)")


def synth_warm_string_pad() -> None:
    """Same Cmaj7 warm pad as the Three Reports trailer, sized for 55s."""
    notes = [130.81, 164.81, 196.00, 246.94, 261.63]  # C3 E3 G3 B3 C4
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.15*t+{i}))"
        for i, f in enumerate(notes)
    )
    filter_chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.6,"
        "lowpass=f=2600,"
        "chorus=0.5:0.9:50|60:0.35|0.45:0.25|0.30:2|2.5,"
        "aecho=0.8:0.7:60|120|240:0.25|0.18|0.10,"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st={TOTAL_SECONDS-2.0}:d=2.0,"
        "aformat=channel_layouts=stereo"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-filter_complex", filter_chain,
         "-t", str(TOTAL_SECONDS), "-c:a", "pcm_s16le", str(PAD_OUT)],
        check=True, capture_output=True,
    )
    print(f"wrote {PAD_OUT} ({PAD_OUT.stat().st_size//1024} KB)")


def build_slideshow() -> None:
    W, H = 1080, 1350
    inputs = []
    for name, dur in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}",
                   "-i", str(FRAME_DIR / name)]
    inputs += ["-i", str(AUDIO_OUT), "-i", str(PAD_OUT)]

    parts = []
    for i in range(len(SLIDES)):
        parts.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1A1330,"
            f"setsar=1,fps=30,format=yuv420p[v{i}]"
        )

    prev = "v0"
    offset = 0.0
    for i in range(1, len(SLIDES)):
        offset += SLIDES[i - 1][1]
        out = f"vx{i}"
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:"
            f"offset={offset:.3f}[{out}]"
        )
        prev = out

    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    voice_idx = len(SLIDES)
    pad_idx = len(SLIDES) + 1
    parts.append(
        f"[{voice_idx}:a]apad=whole_dur={TOTAL_SECONDS},"
        f"atrim=duration={TOTAL_SECONDS},volume=1.0[avoice]"
    )
    parts.append(f"[{pad_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.20[apad]")
    parts.append(
        f"[avoice][apad]amix=inputs=2:duration=first:dropout_transition=3:normalize=0,"
        f"afade=t=out:st={TOTAL_SECONDS-0.8}:d=0.8[aout]"
    )

    VIDEO_OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(parts),
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "160k",
            "-movflags", "+faststart",
            "-shortest",
            str(VIDEO_OUT),
        ],
        check=True,
    )
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB)")


async def main():
    await generate_voiceover()
    synth_warm_string_pad()
    build_slideshow()


if __name__ == "__main__":
    asyncio.run(main())
