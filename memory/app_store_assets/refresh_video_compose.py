"""Post-process the recorded raw.webm into App-Store-ready MP4 previews.

Outputs:
  preview_iphone_6_7.mp4 — H.264 / 1080x2340, ~25s (within Apple's 15-30s window)
  preview_play_store.mp4 — same content, often a slightly longer cut is OK on Play

Steps:
  1. Generate intro card (3s) + outro card (3s) as PNGs, then turn into mp4 clips
  2. Trim the raw recording to the middle ~22s of best content (skips the login flash)
  3. Concat: intro + trimmed_tour + outro
  4. Encode with H.264 yuv420p, AAC silent audio, 30fps
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path("/app/memory/app_store_assets/refreshed_feb2026/preview_video")
RAW = OUT_DIR / "raw.webm"
APPLE_OUT = OUT_DIR / "preview_iphone_6_7.mp4"
PLAY_OUT = OUT_DIR / "preview_play_store.mp4"

# Final video size — 1080x2340 (Apple-acceptable, matches 540x1170 * 2)
FW, FH = 1080, 2340
FPS = 30

G1 = (61, 26, 120)
G2 = (94, 45, 181)
G3 = (45, 181, 181)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_PATH = next((c for c in FONT_CANDIDATES if os.path.exists(c)), None)


def gradient(w, h):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.55:
            f = t / 0.55
            r = int(G1[0] + (G2[0] - G1[0]) * f)
            g = int(G1[1] + (G2[1] - G1[1]) * f)
            b = int(G1[2] + (G2[2] - G1[2]) * f)
        else:
            f = (t - 0.55) / 0.45
            r = int(G2[0] + (G3[0] - G2[0]) * f)
            g = int(G2[1] + (G3[1] - G2[1]) * f)
            b = int(G2[2] + (G3[2] - G2[2]) * f)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img.convert("RGBA")


def with_blobs(img):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((w - w // 2, -w // 3, w + w // 2, w // 3), fill=(231, 78, 200, 50))
    od.ellipse((-w // 2, h - w // 2, w // 2, h + w // 2), fill=(45, 181, 181, 50))
    overlay = overlay.filter(ImageFilter.GaussianBlur(80))
    return Image.alpha_composite(img, overlay)


def make_card(text_lines, sub=None, eyebrow=None, save_path=None):
    img = gradient(FW, FH)
    img = with_blobs(img)
    d = ImageDraw.Draw(img)
    if FONT_PATH:
        if eyebrow:
            ef = ImageFont.truetype(FONT_PATH, 30)
            eb = ef.getbbox(eyebrow)
            d.text(
                ((FW - (eb[2] - eb[0])) // 2, int(FH * 0.32)),
                eyebrow,
                font=ef,
                fill=(255, 255, 255, 220),
            )
        line_size = 120
        line_h = int(line_size * 1.15)
        hf = ImageFont.truetype(FONT_PATH, line_size)
        total_h = line_h * len(text_lines)
        start_y = int((FH - total_h) // 2) - int(FH * 0.04)
        for i, ln in enumerate(text_lines):
            b = hf.getbbox(ln)
            d.text(
                ((FW - (b[2] - b[0])) // 2, start_y + i * line_h),
                ln,
                font=hf,
                fill=(255, 255, 255, 255),
            )
        if sub:
            sf = ImageFont.truetype(FONT_PATH, 36)
            sb = sf.getbbox(sub)
            d.text(
                ((FW - (sb[2] - sb[0])) // 2, start_y + total_h + 40),
                sub,
                font=sf,
                fill=(255, 255, 255, 230),
            )
    if save_path:
        img.convert("RGB").save(save_path, "PNG")
    return img


def make_card_mp4(png_path, mp4_path, duration_s):
    """Loop a still image into a silent mp4 clip."""
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(png_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-t", str(duration_s),
        "-vf", f"scale={FW}:{FH}",
        "-c:a", "aac", "-shortest",
        str(mp4_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def transcode_tour(raw_path, mp4_path, start_s=5.5, duration_s=22.0):
    """Trim raw.webm to the interesting middle section and upscale to FWxFH."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_s),
        "-t", str(duration_s),
        "-i", str(raw_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-vf", f"scale={FW}:{FH}:flags=lanczos",
        "-c:a", "aac",
        "-shortest",
        str(mp4_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_mp4s(parts, out_path):
    """Concat mp4s using the concat demuxer."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in parts:
            f.write(f"file '{p}'\n")
        list_path = f.name
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy", str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        os.unlink(list_path)


def main():
    if not RAW.exists():
        print(f"Missing {RAW}. Run refresh_video_record.py first.")
        return

    work = OUT_DIR / "_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    # Intro card (3s)
    intro_png = work / "intro.png"
    make_card(
        ["Prepare for", "mediation,", "calmly."],
        sub="Child-centered prep, in your pocket.",
        eyebrow="SACOPARENTS  ·  RELATIONAL MEDIATION PREP",
        save_path=intro_png,
    )
    intro_mp4 = work / "intro.mp4"
    make_card_mp4(intro_png, intro_mp4, 3.0)
    print(f"Built intro: {intro_mp4}")

    # Outro card (3s)
    outro_png = work / "outro.png"
    make_card(
        ["Download today.", "Free to use."],
        sub="sacoparentsapp.online",
        eyebrow="SACOPARENTS",
        save_path=outro_png,
    )
    outro_mp4 = work / "outro.mp4"
    make_card_mp4(outro_png, outro_mp4, 3.0)
    print(f"Built outro: {outro_mp4}")

    # Tour middle (22s)
    tour_mp4 = work / "tour.mp4"
    transcode_tour(RAW, tour_mp4, start_s=4.0, duration_s=22.0)
    print(f"Built tour: {tour_mp4}")

    # Concat → preview_iphone_6_7.mp4 (~28s)
    concat_mp4s([intro_mp4, tour_mp4, outro_mp4], APPLE_OUT)
    print(f"✅ Wrote {APPLE_OUT}")

    # Play store is identical content — just copy
    shutil.copy(APPLE_OUT, PLAY_OUT)
    print(f"✅ Wrote {PLAY_OUT}")

    # Clean up work dir
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
