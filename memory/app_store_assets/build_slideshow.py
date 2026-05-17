"""Build the SA Coparents animated slideshow.

Pipeline:
1. Compose each scene as a PNG sequence (Ken Burns zoom + caption fade)
2. Stitch with ffmpeg into an MP4 at 1080x1920, 30 fps, ~120 seconds total
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS_DIR = os.path.join(ROOT, "screenshots")
WORK = os.path.join(ROOT, "frames")
OUT_MP4 = os.path.join(ROOT, "sa_coparents_promo.mp4")

WIDTH, HEIGHT = 1080, 1920
FPS = 30
SCENE_SEC = 15
FRAMES_PER_SCENE = SCENE_SEC * FPS

# Brand palette
BG = (253, 250, 243)
SAND = (245, 243, 233)
SAGE = (132, 157, 142)
TERRA = (194, 135, 113)
TEXT_DARK = (42, 54, 49)
TEXT_MID = (92, 107, 100)

# Each scene: (image filename, eyebrow, headline, body)
SCENES = [
    ("00-landing.png",
     "SA Coparents",
     "Mediation,\nprepared with care.",
     "A quieter way to walk into your next session."),

    ("01-dashboard.png",
     "Step by step",
     "Five short reflections.\nThirty minutes.",
     "At your pace — calm, structured, child-centered."),

    ("02-priority.png",
     "Rank what matters",
     "Sort 11 custody topics\ninto 4 buckets.",
     "Build your mediation agenda — drag and drop."),

    ("08-communication.png",
     "Notice patterns",
     "A judgment-free\ncommunication check.",
     "Awareness, not blame. AI-coached reflection."),

    ("03-summary.png",
     "AI-synthesized",
     "Your prep — ready for\nthe mediator.",
     "A focused summary your mediator reads in two minutes."),

    ("12-improve.png",
     "Your growth, tracked",
     "Things I can\nimprove on.",
     "Specific tips for everyday life and communication."),

    ("13-email-mediator.png",
     "One tap",
     "Email your mediator\ndirectly.",
     "PDF attached. Reply goes straight to you."),

    ("05-safety.png",
     "Always one tap away",
     "24/7 support, when\nyou need it most.",
     "Safety, parallel parenting, 988 — built right in."),
]


def find_font(size, bold=False, serif=False):
    candidates = []
    if serif:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    else:
        if bold:
            candidates += [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


HEADLINE_FONT = find_font(76, serif=True)
EYEBROW_FONT = find_font(22, bold=True)
BODY_FONT = find_font(30)


def draw_scene_frame(shot_path, eyebrow, headline, body, t):
    """t in [0,1] — progress through the scene."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)

    # Subtle bg circle
    circ = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(circ)
    d.ellipse([-200, -200, 700, 700], fill=(*SAGE, 22))
    d.ellipse([WIDTH - 600, HEIGHT - 600, WIDTH + 200, HEIGHT + 200], fill=(*TERRA, 18))
    canvas.paste(circ, (0, 0), circ)

    # ---- Phone-style screenshot with Ken Burns + soft shadow + rounded corners
    img = Image.open(shot_path).convert("RGB")
    iw, ih = img.size
    # Target frame for the phone preview
    phone_w = int(WIDTH * 0.72)
    phone_h = int(phone_w * (ih / iw))
    # Ken Burns: zoom from 1.00 → 1.06 over the scene
    zoom = 1.0 + 0.06 * t
    zw, zh = int(phone_w * zoom), int(phone_h * zoom)
    img_z = img.resize((zw, zh), Image.LANCZOS)
    # Crop center-down to phone_w x phone_h
    cx = (zw - phone_w) // 2
    cy = (zh - phone_h) // 2 + int((zh - phone_h) * 0.0)
    img_c = img_z.crop((cx, cy, cx + phone_w, cy + phone_h))

    # Rounded corners
    radius = 56
    mask = Image.new("L", (phone_w, phone_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, phone_w, phone_h], radius, fill=255)
    img_c.putalpha(mask)

    # Drop shadow
    shadow = Image.new("RGBA", (phone_w + 80, phone_h + 80), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([40, 40, phone_w + 40, phone_h + 40], radius, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))

    # Position: lower 2/3 of canvas
    px = (WIDTH - phone_w) // 2
    py = int(HEIGHT * 0.32)
    canvas.paste(shadow, (px - 40, py - 30), shadow)
    canvas.paste(img_c, (px, py), img_c)

    # ---- Text overlay (top third)
    draw = ImageDraw.Draw(canvas)
    # Fade in over first 12% of scene
    text_alpha = min(1.0, t * 8.0)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # eyebrow
    eyebrow_color = (*SAGE, int(220 * text_alpha))
    od.text((90, 120), eyebrow.upper(), font=EYEBROW_FONT, fill=eyebrow_color, spacing=10)
    # tiny rule
    od.rectangle([90, 158, 170, 162], fill=(*SAGE, int(180 * text_alpha)))

    # headline
    headline_color = (*TEXT_DARK, int(255 * text_alpha))
    od.multiline_text((90, 200), headline, font=HEADLINE_FONT, fill=headline_color, spacing=12)

    # body
    body_color = (*TEXT_MID, int(220 * text_alpha))
    od.multiline_text((90, 460), body, font=BODY_FONT, fill=body_color, spacing=8)

    canvas.paste(overlay, (0, 0), overlay)
    return canvas


def render():
    os.makedirs(WORK, exist_ok=True)
    # Clean
    for f in os.listdir(WORK):
        os.remove(os.path.join(WORK, f))

    frame_idx = 0
    for scene_idx, (fname, eyebrow, headline, body) in enumerate(SCENES):
        shot = os.path.join(SHOTS_DIR, fname)
        if not os.path.exists(shot):
            print(f"  ! missing {shot} — skipping")
            continue
        print(f"  rendering scene {scene_idx + 1}/{len(SCENES)}: {fname}")
        for f in range(FRAMES_PER_SCENE):
            t = f / FRAMES_PER_SCENE
            img = draw_scene_frame(shot, eyebrow, headline, body, t)
            img.save(os.path.join(WORK, f"frame_{frame_idx:05d}.jpg"), quality=88)
            frame_idx += 1

    # Stitch with ffmpeg
    print("\nEncoding MP4 with ffmpeg…")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(WORK, "frame_%05d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "20",
        "-preset", "medium",
        "-movflags", "+faststart",
        OUT_MP4,
    ]
    subprocess.run(cmd, check=True)
    size_mb = os.path.getsize(OUT_MP4) / (1024 * 1024)
    print(f"\n  ok — {OUT_MP4} ({size_mb:.1f} MB, {frame_idx} frames)")


if __name__ == "__main__":
    render()
