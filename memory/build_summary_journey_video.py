"""Build the 45-second 'Summary of Your Journey' Watch-First video that
sits above the tabs on the Summary page. Ken-Burns pans across the
"Your Summaries. Your Roadmap." poster with Nova narration and the
same warm-strings pad used across the trailers.

Outputs:
  /app/memory/summary_journey_frames/*.png            (Ken-Burns crops)
  /app/frontend/public/audio/summary-journey.mp3      (voice-over)
  /app/frontend/public/videos/summary-journey.mp4     (1920x1080, ~48s)
  /app/frontend/public/images/summary-journey-poster.jpg  (poster)
"""
import asyncio
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

SRC = Path("/app/memory/summary_journey_frames/source.png")
FRAME_DIR = Path("/app/memory/summary_journey_frames")
VIDEO_OUT = Path("/app/frontend/public/videos/summary-journey.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/summary-journey.mp3")
POSTER_OUT = Path("/app/frontend/public/images/summary-journey-poster.jpg")
PAD_OUT = Path("/app/memory/_summary_journey_pad.wav")

# 16:9 landscape target — plays well on the Summary page desktop layout
# and inside WatchFirstVideo (which is 16:9 on sm+ / 4:5 on mobile).
W, H = 1920, 1080
ASPECT = W / H  # 1.777

# Purple matte around each panel. Brand primary #3D1A78 (matches the app
# gradient) — the Ken-Burns crop sits centred on this background with a
# small breathing room border.
MATTE_COLOR = "0x3D1A78"
# Fraction of the frame each cropped image occupies (rest is purple matte).
IMAGE_SCALE = 0.88

# Ken-Burns slide plan. `cx`/`cy` are 0..1 normalised centres on the
# source image, `zoom` is 1.0=whole image. Times chosen so the whole
# video is ~48s at Nova speed 1.10 (fits the 155-word script comfortably).
SLIDES = [
    # name              cx    cy    zoom   duration
    ("01-full.png",     0.50, 0.50, 1.00, 5.0),
    ("02-title.png",    0.24, 0.14, 1.55, 6.5),
    ("03-summary1.png", 0.395, 0.55, 1.75, 10.0),
    ("04-summary2.png", 0.615, 0.55, 1.75, 9.0),
    ("05-summary3.png", 0.835, 0.55, 1.75, 10.0),
    ("06-tagline.png",  0.50, 0.91, 1.55, 7.5),
]
TOTAL_SECONDS = sum(d for *_, d in SLIDES)  # 48.0
FADE = 0.5

SCRIPT = (
    "Summary of Your Journey. "
    "You've reached the final step of your SA CoParents journey. "
    "Throughout this process, you've taken time to reflect on your family "
    "situation, better understand your co-parenting relationship, identify "
    "your child's needs, create a Foundation Statement, and prepare for "
    "future conversations or mediation. "
    "Your personalized summaries bring all of that work together in one place. "
    "These reports highlight your strengths, identify areas for growth, and "
    "provide a clear, child-focused roadmap you can use moving forward. "
    "Whether you're preparing for mediation, meeting with a professional, or "
    "simply working to improve communication, these summaries are designed to "
    "keep your child's well-being at the center of every decision. "
    "Remember — lasting change doesn't happen in a single conversation. "
    "It happens one thoughtful step at a time. "
    "Thank you for choosing to invest in a stronger co-parenting relationship "
    "and a brighter future for your child."
)


def crop_kenburns(img: Image.Image, cx: float, cy: float, zoom: float) -> Image.Image:
    """Crop a 16:9 rectangle centred on (cx,cy) at the given zoom factor,
    then resize to the output target. zoom=1.0 → largest 16:9 crop that
    fits inside the source. zoom>1 → tighter."""
    src_w, src_h = img.size
    if src_w / src_h > ASPECT:
        # source is wider than target ratio → height-bound
        base_h = src_h
        base_w = base_h * ASPECT
    else:
        base_w = src_w
        base_h = base_w / ASPECT
    crop_w = base_w / zoom
    crop_h = base_h / zoom
    cx_px = cx * src_w
    cy_px = cy * src_h
    left = max(0, min(src_w - crop_w, cx_px - crop_w / 2))
    top = max(0, min(src_h - crop_h, cy_px - crop_h / 2))
    right = left + crop_w
    bottom = top + crop_h
    return img.crop((left, top, right, bottom)).resize((W, H), Image.LANCZOS)


def build_frames() -> None:
    img = Image.open(SRC).convert("RGB")
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for name, cx, cy, zoom, _ in SLIDES:
        crop_kenburns(img, cx, cy, zoom).save(FRAME_DIR / name)
    # Poster: establishing shot on the same purple matte so the video's
    # first frame matches the still shown before playback starts.
    POSTER_OUT.parent.mkdir(parents=True, exist_ok=True)
    establishing = crop_kenburns(img, 0.50, 0.50, 1.00)
    inner_w = int(W * IMAGE_SCALE)
    inner_h = int(H * IMAGE_SCALE)
    establishing_scaled = establishing.resize((inner_w, inner_h), Image.LANCZOS)
    matte = Image.new("RGB", (W, H), (0x3D, 0x1A, 0x78))
    matte.paste(establishing_scaled, ((W - inner_w) // 2, (H - inner_h) // 2))
    matte.save(POSTER_OUT, quality=82)
    print(f"wrote {len(SLIDES)} frames + poster")


async def generate_voiceover() -> None:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
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
    """Same Cmaj7 warm pad as the other trailers, sized for TOTAL_SECONDS."""
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
    inputs = []
    for name, _cx, _cy, _z, dur in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}",
                   "-i", str(FRAME_DIR / name)]
    inputs += ["-i", str(AUDIO_OUT), "-i", str(PAD_OUT)]

    parts = []
    inner_w = int(W * IMAGE_SCALE)
    inner_h = int(H * IMAGE_SCALE)
    for i in range(len(SLIDES)):
        parts.append(
            f"[{i}:v]scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={MATTE_COLOR},"
            f"setsar=1,fps=30,format=yuv420p[v{i}]"
        )

    prev = "v0"
    offset = 0.0
    for i in range(1, len(SLIDES)):
        offset += SLIDES[i - 1][4]
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
    build_frames()
    await generate_voiceover()
    synth_warm_string_pad()
    build_slideshow()


if __name__ == "__main__":
    asyncio.run(main())
