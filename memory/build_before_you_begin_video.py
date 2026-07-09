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
OCEAN_OUT = Path("/app/memory/_before_you_begin_ocean.wav")

# Music bed windows: ocean surf plays only during intro & outro (bracketing
# the voice-over); the warm strings pad carries the middle section.
INTRO_END = 14.0        # ocean fades out by this second
OUTRO_START = 56.0      # ocean fades back in from this second
CROSSFADE = 2.0         # length of fade transitions between beds

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
    # Idempotent: skip if the narration MP3 already exists so we don't
    # re-spend TTS credits when we're only re-scoring the music bed.
    if AUDIO_OUT.exists() and AUDIO_OUT.stat().st_size > 20_000:
        print(f"voice-over already present at {AUDIO_OUT} — skipping regen")
        return
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT, model="tts-1-hd", voice="shimmer", speed=1.00,
    )
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_OUT.write_bytes(audio_bytes)
    print(f"wrote {AUDIO_OUT} ({len(audio_bytes)//1024} KB)")


def synth_ocean_bed() -> None:
    """Light rain + cafe ambience bed. Two layered noise sources:
      • pink noise → gentle patter of light rain (upper frequencies)
      • brown noise → warm room hum of a café (lower frequencies)
    A slow LFO on the pink layer gives the rain its natural breathe/lull.
    Output is at full loudness — the volume envelope is applied in the
    main video mix so this file is reusable at any dynamic level.
    (Filename kept as _ocean.wav for backward compatibility with the
    video build step; the bed is now rain+cafe.)"""
    filter_chain = (
        # === RAIN layer (pink noise + lowpass to remove hiss + gentle LFO)
        f"anoisesrc=color=pink:sample_rate=44100:amplitude=0.55:duration={TOTAL_SECONDS}"
        "[rain_src];"
        "[rain_src]"
        "lowpass=f=1800,"
        "highpass=f=260,"
        # slow "breathing" of the rain — 0.11 Hz ≈ one swell every 9s
        "tremolo=f=0.11:d=0.55,"
        # tiny stereo widening so the rain isn't dead-centre
        "aecho=0.6:0.4:35|55:0.35|0.30,"
        "volume=0.75"
        "[rain];"
        # === CAFE layer (brown noise + reverb — warm background murmur)
        f"anoisesrc=color=brown:sample_rate=44100:amplitude=0.75:duration={TOTAL_SECONDS}"
        "[cafe_src];"
        "[cafe_src]"
        "lowpass=f=520,"
        "highpass=f=80,"
        # bigger reverb tail — feels like a room with distant conversation
        "aecho=0.85:0.75:280|520|900:0.45|0.32|0.22,"
        # very slow swell (~0.04 Hz) mimics natural crowd ebb & flow
        "volume=volume='0.55+0.15*sin(2*PI*0.04*t)':eval=frame"
        "[cafe];"
        # === MIX ==================================================
        "[rain][cafe]amix=inputs=2:duration=first:normalize=0,"
        "aformat=channel_layouts=stereo"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-filter_complex", filter_chain,
         "-t", str(TOTAL_SECONDS), "-c:a", "pcm_s16le", str(OCEAN_OUT)],
        check=True, capture_output=True,
    )
    print(f"wrote {OCEAN_OUT} ({OCEAN_OUT.stat().st_size//1024} KB) — rain+cafe bed")


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
    inputs += ["-i", str(AUDIO_OUT), "-i", str(PAD_OUT), "-i", str(OCEAN_OUT)]

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
    o_idx = len(SLIDES) + 2

    # Voice — unchanged
    parts.append(
        f"[{v_idx}:a]apad=whole_dur={TOTAL_SECONDS},"
        f"atrim=duration={TOTAL_SECONDS},volume=1.0[avoice]"
    )

    # Strings pad — audible only in the MIDDLE. Fade in a couple seconds
    # before ocean fades out; fade back out just as ocean returns.
    strings_in_start = INTRO_END - CROSSFADE          # 12s
    strings_out_start = OUTRO_START - CROSSFADE       # 54s
    parts.append(
        f"[{p_idx}:a]atrim=duration={TOTAL_SECONDS},"
        f"afade=t=in:st={strings_in_start:.2f}:d={CROSSFADE*2:.2f},"
        f"afade=t=out:st={strings_out_start:.2f}:d={CROSSFADE*2:.2f},"
        f"volume=0.16[apad]"
    )

    # Ocean bed — audible only in INTRO (0 → INTRO_END) and OUTRO
    # (OUTRO_START → END). Two fade-in/out pairs.
    intro_out_start = INTRO_END - CROSSFADE           # 12s
    outro_in_start = OUTRO_START                      # 56s
    outro_out_start = TOTAL_SECONDS - CROSSFADE       # 68s
    parts.append(
        f"[{o_idx}:a]atrim=duration={TOTAL_SECONDS},"
        f"afade=t=in:st=0:d=2.0,"
        f"afade=t=out:st={intro_out_start:.2f}:d={CROSSFADE:.2f},"
        f"afade=t=in:st={outro_in_start:.2f}:d={CROSSFADE:.2f},"
        f"afade=t=out:st={outro_out_start:.2f}:d={CROSSFADE:.2f},"
        f"volume=0.30[aocean]"
    )

    parts.append(
        f"[avoice][apad][aocean]amix=inputs=3:duration=first:"
        f"dropout_transition=3:normalize=0,"
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
    synth_ocean_bed()
    build_slideshow()


if __name__ == "__main__":
    asyncio.run(main())
