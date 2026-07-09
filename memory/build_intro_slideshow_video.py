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

# 9 slides in requested order: app first → branded posters 1-7 → graduation last.
# Total = 55s (~6.1s per slide).
SLIDES = [
    ("02-app.png",           6.0),  # SA CoParents App phone mockup — opening
    ("06-assess.png",        6.0),  # #1 Assess Your Family Situation
    ("11-understand.png",    6.0),  # #2 Understand Your Co-Parenting Relationship
    ("03-identify.png",      6.0),  # #3 Identify Your Child's Goals & Needs
    ("12-foundation.png",    6.0),  # #4 Create Your Foundation Statement
    ("05-prepare.png",       6.0),  # #5 Prepare for Mediation
    ("04-communicate.png",   6.0),  # #6 Strengthen Communication & Problem Solving
    ("08-better.png",        6.0),  # #7 Better Co-Parenting, Better Outcomes
    ("07-welcome-6step.png", 7.0),  # Graduation — Welcome to SA CoParents · Class of 2026
]
TOTAL_SECONDS = int(sum(d for _, d in SLIDES))  # 55
FADE = 0.4

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
        text=SCRIPT, model="tts-1-hd", voice="shimmer", speed=1.00,
    )
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_OUT.write_bytes(audio_bytes)
    print(f"wrote {AUDIO_OUT} ({len(audio_bytes)//1024} KB)")


def synth_warm_string_pad() -> None:
    """Now: gentle raindrops instead of a warm strings pad.

    The bed is audible only in the FIRST 5 seconds and the LAST 5 seconds
    of the video; the middle 45 s is silent so the narration carries alone.
    Rain is synthesized from filtered pink noise + fast tremolo (many small
    amplitude flickers like patter) + a peak filter to give drops sparkle.
    """
    filter_chain = (
        # Base rain layer — pink noise band-passed into the drop range and
        # flickered at ~8 Hz to imitate many small drops hitting a surface.
        f"anoisesrc=color=pink:sample_rate=44100:amplitude=0.9:duration={TOTAL_SECONDS},"
        "highpass=f=220,"
        "lowpass=f=5500,"
        "tremolo=f=8:d=0.45,"
        # Presence peak around 2 kHz gives water-sparkle without hiss.
        "equalizer=f=2000:width_type=q:width=1:g=3,"
        # Subtle stereo widening reverb — helps rain feel spatial, not mono.
        "aecho=0.6:0.5:40|75:0.30|0.22,"
        # Two-window envelope: on 0-5s, silent 5-50s, on 50-55s.
        "afade=t=in:st=0:d=1.0,"
        f"afade=t=out:st=3:d=2.0,"
        f"afade=t=in:st={TOTAL_SECONDS-5}:d=2.0,"
        f"afade=t=out:st={TOTAL_SECONDS-1}:d=1.0,"
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
    parts.append(f"[{p_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.35[apad]")
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
