"""Build a 45-second 9:16 social media reel that walks through the parent's
journey — badges 1-9 — and ends with the "Certificate of Completion" reveal.

Format: 1080×1920 vertical mp4, optimised for Instagram Reels / TikTok /
Shorts. No voice-over (social autoplays muted); each slide carries its
title as an on-screen overlay. Brand-purple matte behind every panel.

Output: /app/frontend/public/videos/social-journey.mp4
"""
import subprocess
from pathlib import Path

VIDEO_OUT = Path("/app/frontend/public/videos/social-journey.mp4")
MUSIC_OUT = Path("/app/memory/_social_journey_music.wav")

STEPS_DIR = Path("/app/frontend/public/images/steps")
CERT_PATH = Path("/app/frontend/public/images/certificate-template.png")

# Target format
W, H = 1080, 1920
TARGET_ASPECT = W / H  # 0.5625

# The journey — 9 badges in ceremony order, then the certificate reveal.
# Each entry: (image_path, on-screen title, duration_seconds)
SLIDES = [
    (STEPS_DIR / "step-child-goals.png",         "1 · Child Goals",           3.8),
    (STEPS_DIR / "step-issues.png",              "2 · Issues & Concerns",     3.8),
    (STEPS_DIR / "step-priority.png",            "3 · Priority Agenda",       3.8),
    (STEPS_DIR / "step-comm-style.png",          "4 · Communication",         3.8),
    (STEPS_DIR / "step-foundation.png",          "5 · Foundation Statement",  4.2),
    # Summary uses the summary-journey source (already has "6" badge baked in).
    (Path("/app/memory/summary_journey_frames/source.png"), "6 · Your Summaries",  4.2),
    # Family Violence — use one of the IPV Ken-Burns frames (title crop).
    (Path("/app/memory/ipv_frames/01-title.png"),           "7 · Family Violence",  4.2),
    (STEPS_DIR / "step-safety-assessment.png",    "8 · Assess Your Family",   4.2),
    (STEPS_DIR / "step-readiness.png",            "9 · Mediation Readiness",  4.2),
    (CERT_PATH,                                   "Certificate awarded",      4.8),
]
FADE = 0.4
TOTAL_SECONDS = sum(d for _, _, d in SLIDES) + FADE * (len(SLIDES) - 1)
# Round to a clean integer for the music bed.
TOTAL_SECONDS = round(TOTAL_SECONDS)

MATTE = "0x3D1A78"       # brand primary — behind every panel
IMAGE_SCALE = 0.86       # leaves a visible purple frame + room for title bar


def synth_music() -> None:
    """Warm, uplifting Cmaj7 pad (same family as the trailer beds) sized
    for the full reel duration."""
    notes = [130.81, 164.81, 196.00, 246.94, 329.63]  # C3 E3 G3 B3 E4
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.12*t+{i}))"
        for i, f in enumerate(notes)
    )
    filter_chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.7,"
        "lowpass=f=2800,"
        "chorus=0.5:0.9:50|60:0.35|0.45:0.25|0.30:2|2.5,"
        "aecho=0.8:0.7:60|120|240:0.25|0.18|0.10,"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st={TOTAL_SECONDS-2.5}:d=2.5,"
        "aformat=channel_layouts=stereo"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-filter_complex", filter_chain,
         "-t", str(TOTAL_SECONDS), "-c:a", "pcm_s16le", str(MUSIC_OUT)],
        check=True, capture_output=True,
    )


def build_video() -> None:
    # Build the -i inputs list. Each image loops for its own duration + fade.
    inputs = []
    for path, _title, dur in SLIDES:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}", "-i", str(path)]
    inputs += ["-i", str(MUSIC_OUT)]

    inner_w = int(W * IMAGE_SCALE)
    inner_h = int(H * IMAGE_SCALE)

    parts = []
    for i, (_p, title, _d) in enumerate(SLIDES):
        # Scale each source to fit inside the inner box on the purple canvas,
        # then draw the title in a bottom banner. `drawtext` uses expansion
        # of the caption inline; escape any colons in title to be safe.
        safe_title = title.replace(":", "\\:").replace("'", r"\\\'")
        parts.append(
            f"[{i}:v]scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={MATTE},"
            "setsar=1,fps=30,format=yuv420p,"
            # Bottom title bar — semi-opaque purple pill with white text
            f"drawbox=x=60:y={H-180}:w={W-120}:h=110:color=0x1A1330@0.85:t=fill,"
            f"drawtext=text='{safe_title}':fontcolor=white:fontsize=54:"
            f"x=(w-text_w)/2:y={H-155}:font=Sans:box=0:borderw=0"
            f"[v{i}]"
        )

    prev = "v0"
    offset = 0.0
    for i in range(1, len(SLIDES)):
        offset += SLIDES[i - 1][2]
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:"
            f"offset={offset:.3f}[vx{i}]"
        )
        prev = f"vx{i}"

    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    mus_idx = len(SLIDES)
    parts.append(
        f"[{mus_idx}:a]atrim=duration={TOTAL_SECONDS},"
        f"afade=t=out:st={TOTAL_SECONDS-1.2}:d=1.2,volume=0.9[aout]"
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
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB)  duration≈{TOTAL_SECONDS}s")


def main() -> None:
    synth_music()
    build_video()


if __name__ == "__main__":
    main()
