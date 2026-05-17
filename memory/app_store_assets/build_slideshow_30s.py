"""Build the punchier 30-second SA Coparents promo.

6 scenes × 5 seconds. Same Ken Burns + caption fade, sharper headlines.
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS_DIR = os.path.join(ROOT, "screenshots")
WORK = os.path.join(ROOT, "frames")
OUT_MP4 = os.path.join(ROOT, "sa_coparents_promo_30s.mp4")

WIDTH, HEIGHT = 1080, 1920
FPS = 30
SCENE_SEC = 5
FRAMES_PER_SCENE = SCENE_SEC * FPS

BG = (253, 250, 243)
SAGE = (132, 157, 142)
TERRA = (194, 135, 113)
TEXT_DARK = (42, 54, 49)
TEXT_MID = (92, 107, 100)

# Tighter, snappier scene set — 6 scenes for 30 seconds.
SCENES = [
    ("06-child-goals.png",
     "Step 1",
     "What does your child\nneed most?",
     ""),

    ("02-priority.png",
     "Rank what matters",
     "11 custody topics.\n4 buckets.",
     ""),

    ("08-communication.png",
     "Notice patterns",
     "Honest, gentle\nself-check.",
     ""),

    ("03-summary.png",
     "AI-synthesized",
     "Ready for your\nmediator.",
     ""),

    ("09-readiness.png",
     "Track your growth",
     "Things I can\nimprove on.",
     ""),

    ("05-safety.png",
     "Always there",
     "Safety, one\ntap away.",
     ""),
]


def find_font(size, serif=False, bold=False):
    cands = []
    if serif:
        cands += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    else:
        if bold:
            cands += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        cands += ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in cands:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


HEAD_FONT = find_font(92, serif=True)
EYE_FONT = find_font(24, bold=True)


def draw_frame(shot_path, eyebrow, headline, t):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)

    # Soft accent circles
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    dr.ellipse([-200, -200, 700, 700], fill=(*SAGE, 22))
    dr.ellipse([WIDTH - 600, HEIGHT - 600, WIDTH + 200, HEIGHT + 200], fill=(*TERRA, 18))
    canvas.paste(layer, (0, 0), layer)

    # Phone screenshot
    img = Image.open(shot_path).convert("RGB")
    iw, ih = img.size
    phone_w = int(WIDTH * 0.72)
    phone_h = int(phone_w * (ih / iw))
    # Slightly faster Ken Burns for punchier feel
    zoom = 1.0 + 0.10 * t
    zw, zh = int(phone_w * zoom), int(phone_h * zoom)
    img_z = img.resize((zw, zh), Image.LANCZOS)
    cx = (zw - phone_w) // 2
    cy = (zh - phone_h) // 2
    img_c = img_z.crop((cx, cy, cx + phone_w, cy + phone_h))

    radius = 56
    mask = Image.new("L", (phone_w, phone_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, phone_w, phone_h], radius, fill=255)
    img_c.putalpha(mask)

    shadow = Image.new("RGBA", (phone_w + 80, phone_h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [40, 40, phone_w + 40, phone_h + 40], radius, fill=(0, 0, 0, 90)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))

    px = (WIDTH - phone_w) // 2
    py = int(HEIGHT * 0.34)
    canvas.paste(shadow, (px - 40, py - 30), shadow)
    canvas.paste(img_c, (px, py), img_c)

    # Snappier text fade — fully visible by 20% of scene
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    alpha = min(1.0, t * 5.0)

    eye_col = (*SAGE, int(220 * alpha))
    od.text((90, 140), eyebrow.upper(), font=EYE_FONT, fill=eye_col, spacing=10)
    od.rectangle([90, 180, 200, 184], fill=(*SAGE, int(180 * alpha)))

    head_col = (*TEXT_DARK, int(255 * alpha))
    od.multiline_text((90, 220), headline, font=HEAD_FONT, fill=head_col, spacing=10)

    canvas.paste(overlay, (0, 0), overlay)
    return canvas


def render():
    os.makedirs(WORK, exist_ok=True)
    for f in os.listdir(WORK):
        os.remove(os.path.join(WORK, f))

    idx = 0
    for i, (fname, eyebrow, headline, _) in enumerate(SCENES):
        shot = os.path.join(SHOTS_DIR, fname)
        if not os.path.exists(shot):
            print(f"  ! missing {fname} — skipping")
            continue
        print(f"  scene {i + 1}/{len(SCENES)}: {fname}")
        for f in range(FRAMES_PER_SCENE):
            t = f / FRAMES_PER_SCENE
            img = draw_frame(shot, eyebrow, headline, t)
            img.save(os.path.join(WORK, f"frame_{idx:05d}.jpg"), quality=88)
            idx += 1

    print("\nEncoding…")
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", os.path.join(WORK, "frame_%05d.jpg"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "medium",
            "-movflags", "+faststart",
            OUT_MP4,
        ],
        check=True,
    )
    size_mb = os.path.getsize(OUT_MP4) / (1024 * 1024)
    print(f"  ok — {OUT_MP4} ({size_mb:.1f} MB, {idx} frames)")


if __name__ == "__main__":
    render()
