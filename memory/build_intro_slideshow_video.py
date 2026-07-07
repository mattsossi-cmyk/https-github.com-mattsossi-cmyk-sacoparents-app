"""Build the 55-second SA CoParents intro slideshow using the branded
poster slides (Journey Starts Here → App overview → Assess → Identify →
Communicate → Prepare) with the same Nova voice-over + warm strings pad.

Outputs:
  /app/frontend/public/videos/intro-slideshow.mp4
  /app/frontend/public/intro-tour.mp4              (legacy path used by
                                                    IntroTourModal player)
"""
import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

SLIDE_DIR = Path("/app/memory/intro_slides")
VIDEO_OUT = Path("/app/frontend/public/videos/intro-slideshow.mp4")
LEGACY_OUT = Path("/app/frontend/public/intro-tour.mp4")
AUDIO_OUT = Path("/app/frontend/public/intro-narration.mp3")
PAD_OUT = Path("/app/memory/_intro_slideshow_pad.wav")

# 4 slides aligned to the voice-over rhythm; sum = 55s.
# 01-journey        A Better Co-Parenting Journey Starts Here (landscape)
# 02-app            SA CoParents App phone mockup             (portrait)
# 06-assess         Assess — Understand your situation        (landscape)
# 05-prepare        Prepare for Mediation. Feel Confident.    (landscape)
SLIDES = [
    ("01-journey.png",  14.0),  # welcome + child deserves to feel safe
    ("02-app.png",      13.0),  # designed to help you take the next step
    ("06-assess.png",   14.0),  # assess + identify + foundation
    ("05-prepare.png",  14.0),  # prepare + practical tools + get started
]
TOTAL_SECONDS = int(sum(d for _, d in SLIDES))  # 55
FADE = 0.7

SCRIPT = (
    "Welcome to the SA CoParents App. "
    "No matter where you are in your co-parenting journey, one thing remains "
    "the same — your child deserves to feel safe, loved, and supported. "
    "This app is designed to help you take the next step toward healthier "
    "co-parenting by guiding you through a simple, child-focused process. "
    "You'll assess your current parenting relationship, identify your child's "
    "goals and needs, create a personalized Foundation Statement, and prepare "
    "for productive mediation or constructive conversations with your child's "
    "other parent. "
    "Along the way, you'll receive practical tools, personalized reports, and "
    "thoughtful guidance to help reduce conflict, improve communication, and "
    "keep your focus where it matters most — on your child's future. "
    "Let's get started together."
)


async def generate_voiceover() -> None:
    if AUDIO_OUT.exists():
        print(f"reusing existing {AUDIO_OUT} ({AUDIO_OUT.stat().st_size//1024} KB)")
        return
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT, model="tts-1-hd", voice="nova", speed=1.02,
    )
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_OUT.write_bytes(audio_bytes)
    print(f"wrote {AUDIO_OUT} ({len(audio_bytes)//1024} KB)")


def synth_warm_string_pad() -> None:
    notes = [130.81, 164.81, 196.00, 246.94, 261.63]
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.15*t+{i}))"
        for i, f in enumerate(notes)
    )
    filter_chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.6,lowpass=f=2600,"
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


def build_slideshow() -> None:
    """Assemble a 1080x1350 (4:5) slideshow with brand-cream padding so
    landscape and portrait posters both sit in the same canvas without
    letterbox seams (posters already have cream backgrounds)."""
    W, H = 1080, 1350
    BG = "0xF6F0E7"  # match the poster cream

    inputs = []
    for name, dur in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}",
                   "-i", str(SLIDE_DIR / name)]
    inputs += ["-i", str(AUDIO_OUT), "-i", str(PAD_OUT)]

    parts = []
    for i in range(len(SLIDES)):
        parts.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG},"
            f"setsar=1,fps=30,format=yuv420p[v{i}]"
        )

    prev = "v0"
    offset = 0.0
    for i in range(1, len(SLIDES)):
        offset += SLIDES[i - 1][1]
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:"
            f"offset={offset:.3f}[vx{i}]"
        )
        prev = f"vx{i}"

    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    v_idx = len(SLIDES)
    p_idx = len(SLIDES) + 1
    parts.append(
        f"[{v_idx}:a]apad=whole_dur={TOTAL_SECONDS},"
        f"atrim=duration={TOTAL_SECONDS},volume=1.0[avoice]"
    )
    parts.append(f"[{p_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.15[apad]")
    parts.append(
        f"[avoice][apad]amix=inputs=2:duration=first:dropout_transition=3:normalize=0,"
        f"afade=t=out:st={TOTAL_SECONDS-1.0}:d=1.0[aout]"
    )

    VIDEO_OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(parts),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", "-shortest",
            str(VIDEO_OUT),
        ],
        check=True,
    )
    shutil.copyfile(VIDEO_OUT, LEGACY_OUT)
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB)")
    print(f"wrote {LEGACY_OUT} (copy for the IntroTourModal player)")


async def main():
    await generate_voiceover()
    synth_warm_string_pad()
    build_slideshow()


if __name__ == "__main__":
    asyncio.run(main())
