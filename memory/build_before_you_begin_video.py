"""Build the 70-second "Before You Begin" coaching video that plays
right before a parent starts their assessment journey. Ken-Burns pans
across the "Journey Starts Here" poster with a warm, unhurried Nova
voice-over + strings pad — tone is coaching, not software training.

Outputs:
  /app/frontend/public/audio/before-you-begin.mp3
  /app/frontend/public/videos/before-you-begin.mp4
"""
import asyncio
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

FRAME_DIR = Path("/app/memory/before_you_begin_frames")
VIDEO_OUT = Path("/app/frontend/public/videos/before-you-begin.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/before-you-begin.mp3")
PAD_OUT = Path("/app/memory/_before_you_begin_pad.wav")

# 5 slides — sum to TOTAL_SECONDS (70s).
SLIDES = [
    ("01-full.png",       14.0),  # welcome / not just an assessment
    ("02-laptop.png",     14.0),  # take your time / honest / thoughtful
    ("03-journal.png",    14.0),  # discover strengths / challenges
    ("04-full-out.png",   14.0),  # each section builds / reflection & growth
    ("05-summaries.png",  14.0),  # thank you / when you're ready — closing
]
TOTAL_SECONDS = int(sum(d for _, d in SLIDES))  # 70
FADE = 0.7

# ~245 words → ~70s at Nova speed 1.08.
SCRIPT = (
    "Before you begin, remember that SA CoParents is not simply an "
    "assessment or a collection of forms. It's a guided journey designed "
    "to help you better understand your co-parenting relationship and focus "
    "on what matters most — your child's well-being. "
    "As you move through each step, take your time. Answer each question "
    "honestly and from your own perspective. There are no right or wrong "
    "answers. The more thoughtful and accurate your responses, the more "
    "valuable your personalized reports and recommendations will be. "
    "You may discover strengths you can build on, challenges that need "
    "attention, or new ways of approaching conversations with your child's "
    "other parent. That's all part of the process. "
    "Each section builds on the one before it — from understanding your "
    "family's situation, to learning child-focused strategies, creating "
    "your Parenting Foundation Statement, and preparing for productive "
    "mediation or future parenting discussions. "
    "This experience is about reflection, growth, and preparing to make "
    "decisions that support your child's long-term success. If you need a "
    "break, you can always return and continue where you left off. "
    "Thank you for investing in yourself and your child. When you're ready, "
    "let's begin the journey together."
)


async def generate_voiceover() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT, model="tts-1-hd", voice="nova", speed=1.05,
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
        f"afade=t=in:st=0:d=2.0,afade=t=out:st={TOTAL_SECONDS-2.5}:d=2.5,"
        "aformat=channel_layouts=stereo"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-filter_complex", filter_chain,
         "-t", str(TOTAL_SECONDS), "-c:a", "pcm_s16le", str(PAD_OUT)],
        check=True, capture_output=True,
    )


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
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xF6F0E7,"
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
        f"afade=t=out:st={TOTAL_SECONDS-1.2}:d=1.2[aout]"
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
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB)")


async def main():
    await generate_voiceover()
    synth_warm_string_pad()
    build_slideshow()


if __name__ == "__main__":
    asyncio.run(main())
