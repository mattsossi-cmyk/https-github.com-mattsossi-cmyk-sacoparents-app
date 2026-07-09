"""Build the 55-second IPV Safety Assessment intro video that Ken-Burns
across the infographic with a Nova voice-over and warm-strings pad.

Outputs:
  /app/frontend/public/audio/ipv-assessment-intro.mp3
  /app/frontend/public/videos/ipv-assessment-intro.mp4
"""
import asyncio
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

FRAME_DIR = Path("/app/memory/ipv_frames")
VIDEO_OUT = Path("/app/frontend/public/videos/ipv-assessment-intro.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/ipv-assessment-intro.mp3")
PAD_OUT = Path("/app/memory/_ipv_pad.wav")

# Slide (image, seconds) — sum to TOTAL_SECONDS.
SLIDES = [
    ("01-title.png",         11.0),  # Opening — IPV assessment framing
    ("02-why.png",           14.0),  # "confidential assessment helps you identify patterns…"
    ("03-assess.png",        12.0),  # "direct, supported, or alternative approaches"
    ("04-confidential.png",   9.0),  # "no right or wrong answers…"
    ("05-footer.png",         9.0),  # closing — child-focused decisions
]
TOTAL_SECONDS = int(sum(d for _, d in SLIDES))  # 55
FADE = 0.7

# ~140 words → ~48-52s at Nova 1.02x. 3 seconds of soft tail before fade-out.
SCRIPT = (
    "When intimate partner violence, coercive control, or ongoing fear has "
    "been part of a relationship, the first step is not better communication "
    "— it is understanding safety. "
    "This confidential assessment helps you identify patterns of intimidation, "
    "control, threats, or other behaviors that may affect how parenting "
    "decisions should be made. It also helps determine whether direct "
    "communication, supported communication, or alternative approaches may be "
    "the safest path forward. "
    "There are no right or wrong answers. Simply answer honestly based on "
    "your own experiences. "
    "Our goal is to help you make child-focused decisions while protecting "
    "your well-being and creating the safest possible future for your family."
)


async def generate_voiceover() -> None:
    # Idempotent: skip if the narration MP3 already exists so we don't
    # re-spend TTS credits when we're only re-scoring or re-framing.
    if AUDIO_OUT.exists() and AUDIO_OUT.stat().st_size > 20_000:
        print(f"voice-over already present at {AUDIO_OUT} — skipping regen")
        return
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    # Slightly slower speed so the safety-critical script lands calmly.
    audio_bytes = await tts.generate_speech(
        text=SCRIPT,
        model="tts-1-hd",
        voice="shimmer",
        speed=1.00,
    )
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_OUT.write_bytes(audio_bytes)
    print(f"wrote {AUDIO_OUT} ({len(audio_bytes)//1024} KB)")


def synth_warm_string_pad() -> None:
    """Same Cmaj7 pad as the trailers — even lower level to keep this
    subject serious."""
    notes = [130.81, 164.81, 196.00, 246.94, 261.63]
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.15*t+{i}))"
        for i, f in enumerate(notes)
    )
    filter_chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.5,"
        "lowpass=f=2400,"
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
    print(f"wrote {PAD_OUT} ({PAD_OUT.stat().st_size//1024} KB)")


def build_slideshow() -> None:
    # Landscape 16:9 to match the new source graphic (1536x1024) and the
    # summary-journey/dashboard-welcome trailers. Purple brand-matte border
    # is applied by scaling the frame to IMAGE_SCALE and padding with
    # MATTE_COLOR so a visible band of colour sits behind the panel.
    W, H = 1920, 1080
    MATTE_COLOR = "0x3D1A78"   # brand primary
    IMAGE_SCALE = 0.88

    inputs = []
    for name, dur in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}",
                   "-i", str(FRAME_DIR / name)]
    inputs += ["-i", str(AUDIO_OUT), "-i", str(PAD_OUT)]

    inner_w = int(W * IMAGE_SCALE)
    inner_h = int(H * IMAGE_SCALE)
    parts = []
    for i in range(len(SLIDES)):
        parts.append(
            f"[{i}:v]scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={MATTE_COLOR},"
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
    # Lower pad volume to 0.15 — voice needs full clarity on safety content.
    parts.append(
        f"[{voice_idx}:a]apad=whole_dur={TOTAL_SECONDS},"
        f"atrim=duration={TOTAL_SECONDS},volume=1.0[avoice]"
    )
    parts.append(f"[{pad_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.15[apad]")
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
