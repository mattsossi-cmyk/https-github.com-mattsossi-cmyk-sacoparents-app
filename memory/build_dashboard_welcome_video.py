"""Build a 70-second Dashboard welcome video that Ken-Burns across the
"Better co-parenting starts with a plan" hero and reuses the existing
Before-You-Begin coaching voice-over. Plays when the user clicks Dashboard.

Outputs:
  /app/frontend/public/videos/dashboard-welcome.mp4
"""
import subprocess
from pathlib import Path
from PIL import Image

SRC = Path("/app/memory/dashboard_frames/source.png")
FRAME_DIR = Path("/app/memory/dashboard_frames")
AUDIO_IN = Path("/app/frontend/public/audio/before-you-begin.mp3")
PAD_OUT = Path("/app/memory/_dashboard_welcome_pad.wav")
VIDEO_OUT = Path("/app/frontend/public/videos/dashboard-welcome.mp4")

# Output is 1600x900 landscape (16:9) to match the hero's landscape aspect.
W, H = 1600, 900
ASPECT = W / H

# 6 Ken-Burns crops of the same landscape hero, aligned to the coaching script:
# 1. Full hero               (0-14s)  "Before you begin, remember that SA CoParents…"
# 2. Left copy title         (14-26s) "It's a guided journey designed to help you…"
# 3. Family + soccer         (26-38s) "As you move through each step, take your time…"
# 4. 7 icon strip zoom       (38-52s) "You may discover strengths… new ways of…"
# 5. Phone mockup            (52-62s) "Each section builds on the one before it…"
# 6. Zoom back to full hero  (62-70s) "Thank you… let's begin the journey together."
SLIDES = [
    ("01-full.png",    14.0, 0.50, 0.50, 1.00),
    ("02-copy.png",    12.0, 0.20, 0.34, 1.45),
    ("03-family.png",  12.0, 0.60, 0.34, 1.35),
    ("04-icons.png",   14.0, 0.35, 0.70, 1.55),
    ("05-phone.png",   10.0, 0.75, 0.70, 1.65),
    ("06-full-out.png", 8.0, 0.50, 0.50, 1.05),
]
TOTAL_SECONDS = int(sum(s[1] for s in SLIDES))  # 70
FADE = 0.6


def crop_to_aspect(img: Image.Image, cx: float, cy: float, zoom: float) -> Image.Image:
    src_w, src_h = img.size
    if src_w / src_h > ASPECT:
        base_h = src_h
        base_w = base_h * ASPECT
    else:
        base_w = src_w
        base_h = base_w / ASPECT
    crop_w = base_w / zoom
    crop_h = base_h / zoom
    cx_px, cy_px = cx * src_w, cy * src_h
    left = max(0, min(src_w - crop_w, cx_px - crop_w / 2))
    top = max(0, min(src_h - crop_h, cy_px - crop_h / 2))
    return img.crop((left, top, left + crop_w, top + crop_h)).resize(
        (W, H), Image.LANCZOS
    )


def make_frames() -> None:
    img = Image.open(SRC).convert("RGB")
    for name, _dur, cx, cy, zoom in SLIDES:
        crop_to_aspect(img, cx, cy, zoom).save(FRAME_DIR / name)
        print(f"wrote {name}")


def synth_pad() -> None:
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


def build_video() -> None:
    inputs = []
    for name, dur, *_ in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}",
                   "-i", str(FRAME_DIR / name)]
    inputs += ["-i", str(AUDIO_IN), "-i", str(PAD_OUT)]

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

    v_idx, p_idx = len(SLIDES), len(SLIDES) + 1
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


if __name__ == "__main__":
    make_frames()
    synth_pad()
    build_video()
