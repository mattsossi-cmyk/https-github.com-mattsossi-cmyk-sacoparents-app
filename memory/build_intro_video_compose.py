"""Compose the final intro video: scaled tour footage + narration audio.

Output: /app/frontend/public/intro-tour.mp4
"""
import subprocess
from pathlib import Path

RAW_VIDEO = Path("/app/memory/intro_video_work/raw.webm")
NARRATION = Path("/app/frontend/public/intro-narration.mp3")
OUT = Path("/app/frontend/public/intro-tour.mp4")

FW, FH = 1080, 2340  # iPhone 6.7" aspect, browser-friendly portrait
FPS = 30
DURATION = 67.5  # match narration length (~67s) + small tail

# Mux raw footage with narration, trim to narration duration
cmd = [
    "ffmpeg", "-y",
    "-stream_loop", "-1",         # loop video if shorter than audio
    "-i", str(RAW_VIDEO),
    "-i", str(NARRATION),
    "-t", str(DURATION),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
    "-vf", f"scale={FW}:{FH}:flags=lanczos",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "-movflags", "+faststart",
    str(OUT),
]
subprocess.run(cmd, check=True, capture_output=True)

size_kb = OUT.stat().st_size // 1024
print(f"Wrote {OUT} ({size_kb} KB)")
