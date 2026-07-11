"""Facebook intro video — 1080x1080 square format walking through the
"Welcome to SA CoParents" script with the app logo/hero plus the 9 badges,
ending on the certificate reveal.

Output:
  /app/frontend/public/audio/facebook-intro.mp3
  /app/frontend/public/videos/facebook-intro.mp4
"""
import asyncio
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

VIDEO_OUT = Path("/app/frontend/public/videos/facebook-intro.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/facebook-intro.mp3")
MUSIC_OUT = Path("/app/memory/_facebook_intro_music.wav")

STEPS_DIR = Path("/app/frontend/public/images/steps")
APP_HERO = Path("/app/frontend/public/images/dashboard-welcome-poster.jpg")
CERT = Path("/app/frontend/public/images/certificate-template.png")

W, H = 1080, 1080  # square — best Facebook feed performance
MATTE = "0x3D1A78"
IMAGE_SCALE = 0.84

SCRIPT = (
    "Welcome to SA CoParents. "
    "No matter where you are in your co-parenting journey, you've taken an "
    "important first step by being here. Successful co-parenting isn't about "
    "having a perfect relationship with your child's other parent — it's "
    "about making decisions that help your child feel safe, supported, and loved. "
    "Throughout this experience, we'll guide you step by step. "
    "You'll reflect on your family's current situation, better understand your "
    "co-parenting relationship, identify your child's needs, create a "
    "child-focused Foundation Statement, and prepare for productive "
    "conversations or mediation. "
    "There are no right or wrong answers. Simply answer honestly and keep "
    "your child's well-being at the center of each decision. "
    "Every step you take today is an investment in a healthier future for "
    "your child. "
    "Let's begin the journey toward stronger co-parenting — together."
)

# Slide plan — durations sum to the narration length. First slide holds the
# hero as the introduction speaks; badges roll as the "step by step" section
# is narrated; closing slides hold on the certificate + hero for the CTA.
SLIDES = [
    # image, caption, duration_seconds
    (APP_HERO,                                          "Welcome to SA CoParents",       9.5),
    (STEPS_DIR / "step-child-goals.png",                "1 · Child Goals",               5.5),
    (STEPS_DIR / "step-issues.png",                     "2 · Issues & Concerns",         5.5),
    (STEPS_DIR / "step-priority.png",                   "3 · Priority Agenda",           5.5),
    (STEPS_DIR / "step-comm-style.png",                 "4 · Communication",             5.5),
    (STEPS_DIR / "step-foundation.png",                 "5 · Foundation Statement",      5.5),
    (Path("/app/memory/summary_journey_frames/source.png"), "6 · Your Summaries",         5.5),
    (Path("/app/memory/ipv_frames/01-title.png"),       "7 · Family Violence Screen",    5.5),
    (STEPS_DIR / "step-safety-assessment.png",          "8 · Assess Your Family",        5.5),
    (STEPS_DIR / "step-readiness.png",                  "9 · Mediation Readiness",       5.5),
    (CERT,                                              "Your Certificate awaits",       5.5),
    (APP_HERO,                                          "Let's begin — together",        4.0),
]
FADE = 0.4
TOTAL_SECONDS = round(sum(d for _, _, d in SLIDES) + FADE * (len(SLIDES) - 1))


async def generate_voiceover() -> None:
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


def synth_music() -> None:
    """Warm Cmaj7 bed — same family as the other intro videos."""
    notes = [130.81, 164.81, 196.00, 246.94, 329.63]
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.12*t+{i}))"
        for i, f in enumerate(notes)
    )
    chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.5,lowpass=f=2600,"
        "chorus=0.5:0.9:50|60:0.35|0.45:0.25|0.30:2|2.5,"
        "aecho=0.8:0.7:60|120|240:0.25|0.18|0.10,"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st={TOTAL_SECONDS-2.5}:d=2.5,"
        "aformat=channel_layouts=stereo"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-filter_complex", chain,
         "-t", str(TOTAL_SECONDS), "-c:a", "pcm_s16le", str(MUSIC_OUT)],
        check=True, capture_output=True,
    )


def build_video() -> None:
    inputs = []
    for path, _t, dur in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}", "-i", str(path)]
    inputs += ["-i", str(AUDIO_OUT), "-i", str(MUSIC_OUT)]

    inner_w = int(W * IMAGE_SCALE)
    inner_h = int(H * IMAGE_SCALE)
    parts = []
    for i, (_p, title, _d) in enumerate(SLIDES):
        # Use a curly apostrophe to sidestep ffmpeg drawtext single-quote escaping
        safe = title.replace(":", "\\:").replace("'", "\u2019")
        parts.append(
            f"[{i}:v]scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={MATTE},"
            "setsar=1,fps=30,format=yuv420p,"
            f"drawbox=x=60:y={H-115}:w={W-120}:h=70:color=0x1A1330@0.85:t=fill,"
            f"drawtext=text='{safe}':fontcolor=white:fontsize=36:"
            f"x=(w-text_w)/2:y={H-100}:font=Sans:box=0:borderw=0"
            f"[v{i}]"
        )

    prev = "v0"
    off = 0.0
    for i in range(1, len(SLIDES)):
        off += SLIDES[i - 1][2]
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={off:.3f}[vx{i}]")
        prev = f"vx{i}"
    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    v_idx = len(SLIDES)
    m_idx = len(SLIDES) + 1
    parts.append(
        f"[{v_idx}:a]apad=whole_dur={TOTAL_SECONDS},"
        f"atrim=duration={TOTAL_SECONDS},volume=1.0[avoice]"
    )
    parts.append(f"[{m_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.16[amus]")
    parts.append(
        f"[avoice][amus]amix=inputs=2:duration=first:dropout_transition=3:normalize=0,"
        f"afade=t=out:st={TOTAL_SECONDS-1.2}:d=1.2[aout]"
    )

    VIDEO_OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", *inputs,
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
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB) ≈{TOTAL_SECONDS}s")


async def main():
    await generate_voiceover()
    synth_music()
    build_video()


if __name__ == "__main__":
    asyncio.run(main())
