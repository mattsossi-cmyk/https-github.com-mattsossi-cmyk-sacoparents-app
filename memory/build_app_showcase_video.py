"""Build a companion 45-second landscape (16:9) showcase video that leads
with the app's hero graphic ("Better co-parenting starts with a plan"),
walks the parent through the 9 earned badges, and closes on the
Certificate reveal. Suited for YouTube, Facebook feed, LinkedIn, and the
website hero.

Output: /app/frontend/public/videos/app-showcase.mp4
"""
import subprocess
from pathlib import Path

VIDEO_OUT = Path("/app/frontend/public/videos/app-showcase.mp4")
MUSIC_OUT = Path("/app/memory/_app_showcase_music.wav")

STEPS_DIR = Path("/app/frontend/public/images/steps")
APP_HERO = Path("/app/frontend/public/images/dashboard-welcome-poster.jpg")
CERT = Path("/app/frontend/public/images/certificate-template.png")

W, H = 1920, 1080  # 16:9 landscape

# (image_path, caption, duration_seconds)
SLIDES = [
    (APP_HERO,                                          "The SA CoParents App",             4.0),
    (STEPS_DIR / "step-child-goals.png",                "Badge 1 · Child Goals",            3.5),
    (STEPS_DIR / "step-issues.png",                     "Badge 2 · Issues & Concerns",      3.5),
    (STEPS_DIR / "step-priority.png",                   "Badge 3 · Priority Agenda",        3.5),
    (STEPS_DIR / "step-comm-style.png",                 "Badge 4 · Communication",          3.5),
    (STEPS_DIR / "step-foundation.png",                 "Badge 5 · Foundation Statement",   3.5),
    (Path("/app/memory/summary_journey_frames/source.png"),
                                                        "Badge 6 · Your Summaries",         3.5),
    (Path("/app/memory/ipv_frames/01-title.png"),       "Badge 7 · Family Violence Screen", 3.5),
    (STEPS_DIR / "step-safety-assessment.png",          "Badge 8 · Assess Your Family",     3.5),
    (STEPS_DIR / "step-readiness.png",                  "Badge 9 · Mediation Readiness",    3.5),
    (CERT,                                              "Certificate of Completion",        4.5),
]
FADE = 0.4
TOTAL_SECONDS = round(sum(d for _, _, d in SLIDES) + FADE * (len(SLIDES) - 1))

MATTE = "0x3D1A78"
IMAGE_SCALE = 0.86


def synth_music() -> None:
    """Warm Cmaj7 pad, same family as the trailer beds, sized for the reel."""
    notes = [130.81, 164.81, 196.00, 246.94, 329.63]
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.12*t+{i}))"
        for i, f in enumerate(notes)
    )
    chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.7,lowpass=f=2800,"
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
    inputs += ["-i", str(MUSIC_OUT)]

    inner_w = int(W * IMAGE_SCALE)
    inner_h = int(H * IMAGE_SCALE)
    parts = []
    for i, (_p, title, _d) in enumerate(SLIDES):
        safe = title.replace(":", "\\:").replace("'", r"\\\'")
        parts.append(
            f"[{i}:v]scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={MATTE},"
            "setsar=1,fps=30,format=yuv420p,"
            # bottom title bar
            f"drawbox=x=80:y={H-140}:w={W-160}:h=80:color=0x1A1330@0.85:t=fill,"
            f"drawtext=text='{safe}':fontcolor=white:fontsize=40:"
            f"x=(w-text_w)/2:y={H-120}:font=Sans:box=0:borderw=0"
            f"[v{i}]"
        )

    prev = "v0"
    off = 0.0
    for i in range(1, len(SLIDES)):
        off += SLIDES[i - 1][2]
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={off:.3f}[vx{i}]")
        prev = f"vx{i}"
    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    m = len(SLIDES)
    parts.append(
        f"[{m}:a]atrim=duration={TOTAL_SECONDS},"
        f"afade=t=out:st={TOTAL_SECONDS-1.2}:d=1.2,volume=0.9[aout]"
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
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB)  duration≈{TOTAL_SECONDS}s")


def main() -> None:
    synth_music()
    build_video()


if __name__ == "__main__":
    main()
