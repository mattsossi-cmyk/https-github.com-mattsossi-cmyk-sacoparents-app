"""Build a 21-second 'Meet the Program' trailer that fades through all
seven Watch-First posters, layered with a fresh Nova voice-over.

Output:
  /app/frontend/public/audio/meet-the-program.mp3   (TTS voice-over)
  /app/frontend/public/videos/meet-the-program.mp4  (final 1080x1350 mp4)
"""
import asyncio
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

STEPS_DIR = Path("/app/frontend/public/images/steps")
VIDEO_OUT = Path("/app/frontend/public/videos/meet-the-program.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/meet-the-program.mp3")
PAD_OUT = Path("/app/memory/_meet_pad.wav")

# Posters shown in narrative order (matches the numbered poster series).
POSTERS = [
    "step-safety-assessment.png",  # 1 Assess Your Family Situation
    "step-comm-style.png",         # 2 Understand Your Co-Parenting Relationship
    "step-child-goals.png",        # 3 Identify Your Child's Needs
    "step-foundation.png",         # 4 Foundation Statement
    "step-readiness.png",          # 5 Prepare for Mediation
    "step-issues.png",             # 6 Strengthen Communication & Problem Solving
    "step-priority.png",           # 7 Better Co-Parenting, Better Outcomes
]

# ~58 words → ~20 seconds at Nova speed 1.0. We generate a bit tighter
# than the video length so the last poster gets a beat of silence.
SCRIPT = (
    "Preparing for mediation shouldn't feel like a fight. "
    "SA Coparents walks you through seven simple, guided steps — "
    "assess your family, understand your co-parenting relationship, "
    "identify your child's needs, build your foundation statement, "
    "prepare for mediation, and strengthen how you communicate. "
    "Different parents. Same goal — our children. "
    "Because better co-parenting means brighter futures."
)

TOTAL_SECONDS = 21
POSTER_COUNT = len(POSTERS)
PER_POSTER = TOTAL_SECONDS / POSTER_COUNT  # ~3.0s each
FADE = 0.4  # crossfade duration between posters


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
    """
    Synthesize a warm, slowly-evolving string pad (Cmaj7 chord: C-E-G-B)
    with a subtle chorus/vibrato and low-pass filter so it sounds like a
    string section rather than raw sine waves. The pad runs the full
    TOTAL_SECONDS length with gentle fade-in and fade-out envelopes so it
    tucks in under the voice-over.
    """
    # Cmaj7 in a warm mid range so it doesn't clash with Nova's midrange
    # voice. Roots at C3, then E3, G3, B3, plus a soft C4 octave sparkle.
    notes = {
        "C3": 130.81,
        "E3": 164.81,
        "G3": 196.00,
        "B3": 246.94,
        "C4": 261.63,
    }
    # Mix five oscillators with slow amplitude modulation (LFO ~0.2 Hz)
    # for gentle "breathing" movement. The whole pad is band-limited with
    # a low-pass filter to remove the harshness of raw sines.
    aeval = "+".join(
        f"0.18*sin(2*PI*{freq}*t)*(0.7+0.3*sin(2*PI*0.15*t+{i}))"
        for i, freq in enumerate(notes.values())
    )
    filter_chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        # Bring level up to sensible listening range
        "volume=1.6,"
        # Soft low-pass to warm the timbre (kill anything above ~2.6 kHz)
        "lowpass=f=2600,"
        # Add movement + width via chorus
        "chorus=0.5:0.9:50|60:0.35|0.45:0.25|0.30:2|2.5,"
        # A short reverb via aecho for that hall-of-strings tail
        "aecho=0.8:0.7:60|120|240:0.25|0.18|0.10,"
        # Gentle fade in/out so the pad tucks in politely under the voice
        f"afade=t=in:st=0:d=1.2,afade=t=out:st={TOTAL_SECONDS-1.5}:d=1.5,"
        # Duplicate to stereo
        "aformat=channel_layouts=stereo"
    )
    cmd = [
        "ffmpeg", "-y",
        "-filter_complex", filter_chain,
        "-t", str(TOTAL_SECONDS),
        "-c:a", "pcm_s16le",
        str(PAD_OUT),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"wrote {PAD_OUT} ({PAD_OUT.stat().st_size//1024} KB)")


def build_slideshow() -> None:
    """
    Stitch the 7 posters into a 1080x1350 (4:5) crossfaded slideshow,
    layered with the Nova voice-over, and encode to H.264 mp4.
    """
    W, H = 1080, 1350

    # Build filter_complex:
    #   - Each poster: scale to fit inside W x H, pad to 1080x1350 on a
    #     brand-purple background so no letterbox looks stark.
    #   - Chain xfade transitions between adjacent clips.
    inputs = []
    for p in POSTERS:
        inputs += ["-loop", "1", "-t", f"{PER_POSTER + FADE:.3f}", "-i", str(STEPS_DIR / p)]

    # Voice-over + warm-strings pad as final audio inputs
    inputs += ["-i", str(AUDIO_OUT)]
    inputs += ["-i", str(PAD_OUT)]

    # v0..v6 = normalized frames
    parts = []
    for i in range(POSTER_COUNT):
        parts.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1A1330,"
            f"setsar=1,fps=30,format=yuv420p[v{i}]"
        )

    # Chain xfade transitions. Each subsequent clip crossfades in at
    # offset = i * PER_POSTER (so the first poster is fully visible for
    # ~3s before the second one begins to fade in).
    prev = "v0"
    for i in range(1, POSTER_COUNT):
        offset = i * PER_POSTER
        out = f"vx{i}"
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[{out}]"
        )
        prev = out

    # Trim the final composition to exactly TOTAL_SECONDS.
    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    # Audio: voice-over (input POSTER_COUNT) + warm strings pad (input POSTER_COUNT+1)
    # duck the pad ~14 dB under the voice, mix, then fade out and pad to 21s.
    voice_idx = POSTER_COUNT
    pad_idx = POSTER_COUNT + 1
    parts.append(
        f"[{voice_idx}:a]apad=whole_dur={TOTAL_SECONDS},atrim=duration={TOTAL_SECONDS},"
        f"volume=1.0[avoice]"
    )
    parts.append(
        f"[{pad_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.20[apad]"
    )
    parts.append(
        f"[avoice][apad]amix=inputs=2:duration=first:dropout_transition=3:normalize=0,"
        f"afade=t=out:st={TOTAL_SECONDS-0.6}:d=0.6[aout]"
    )

    filter_complex = ";".join(parts)

    VIDEO_OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
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
    ]
    subprocess.run(cmd, check=True)
    size_kb = VIDEO_OUT.stat().st_size // 1024
    print(f"wrote {VIDEO_OUT} ({size_kb} KB)")


async def main():
    await generate_voiceover()
    synth_warm_string_pad()
    build_slideshow()


if __name__ == "__main__":
    asyncio.run(main())
