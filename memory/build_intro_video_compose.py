"""Build the intro tour video by prepending a designer-supplied branded clip
to the existing narrated 67-second tour.

Output:  /app/frontend/public/intro-tour.mp4

Input clips:
  - new_intro_v4.mp4  → 1080x1350 ≈ 8s (branded opener, has audio)
  - raw.webm + intro-narration.mp3 → tour footage + 3-reports narration

Both clips are normalized to 1080x2340 H.264 + 44.1kHz AAC so they concatenate
cleanly with no resolution / sample-rate mismatch.
"""
import subprocess
from pathlib import Path

WORK = Path("/app/memory/intro_video_work")
INTRO_RAW = WORK / "new_intro_v4.mp4"
TOUR_RAW = WORK / "raw.webm"
NARRATION = Path("/app/frontend/public/intro-narration.mp3")
OUT = Path("/app/frontend/public/intro-tour.mp4")

FW, FH = 1080, 2340
FPS = 30
AR = 44100  # audio sample rate

INTRO_NORM = WORK / "intro_norm.mp4"
TOUR_NORM = WORK / "tour_norm.mp4"


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)


# 1. Normalize the branded opener to 1080x2340 (pad with black bars).
run([
    "ffmpeg", "-y",
    "-i", str(INTRO_RAW),
    "-vf", (
        f"scale={FW}:-2:flags=lanczos,"
        f"pad={FW}:{FH}:({FW}-iw)/2:({FH}-ih)/2:color=black,"
        f"setsar=1,fps={FPS}"
    ),
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-ar", str(AR), "-ac", "2", "-b:a", "192k",
    "-movflags", "+faststart",
    str(INTRO_NORM),
])

# 2. Build the narrated tour at 1080x2340 from raw.webm + intro-narration.mp3.
run([
    "ffmpeg", "-y",
    "-stream_loop", "-1",
    "-i", str(TOUR_RAW),
    "-i", str(NARRATION),
    "-shortest",
    "-vf", f"scale={FW}:{FH}:flags=lanczos,setsar=1,fps={FPS}",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-ar", str(AR), "-ac", "2", "-b:a", "192k",
    "-movflags", "+faststart",
    str(TOUR_NORM),
])

# 3. Concatenate via the concat demuxer.
concat_list = WORK / "concat.txt"
concat_list.write_text(f"file '{INTRO_NORM}'\nfile '{TOUR_NORM}'\n")
run([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat_list),
    "-c", "copy",
    "-movflags", "+faststart",
    str(OUT),
])

size_kb = OUT.stat().st_size // 1024
print(f"✅ Wrote {OUT} ({size_kb} KB)")
