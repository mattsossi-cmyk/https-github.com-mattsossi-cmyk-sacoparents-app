"""Generate the Open Graph image for SACOParents.

Output: /app/frontend/public/og-image.png  (1200x630 — Facebook/Twitter/LinkedIn/iMessage)

Brand purple→magenta→teal gradient + family-illustration logo + 2-line headline.
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path("/app/frontend/public/og-image.png")
LOGO = Path("/app/frontend/public/icon-512.png")

W, H = 1200, 630

G1 = (61, 26, 120)
G2 = (94, 45, 181)
G3 = (45, 181, 181)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT = next((c for c in FONT_CANDIDATES if os.path.exists(c)), None)


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
            dx = x / max(1, w - 1)
            sh = int(8 * (dx - 0.5))
            px[x, y] = (
                max(0, min(255, r + sh)),
                max(0, min(255, g + sh)),
                max(0, min(255, b - sh)),
            )
    return img.convert("RGBA")


def with_blobs(img):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((w - 250, -200, w + 250, 220), fill=(231, 78, 200, 60))
    od.ellipse((-200, h - 220, 300, h + 220), fill=(45, 181, 181, 60))
    overlay = overlay.filter(ImageFilter.GaussianBlur(60))
    return Image.alpha_composite(img, overlay)


def draw_text(canvas, text, font_size, xy, color=(255, 255, 255, 255), shadow=True):
    font = ImageFont.truetype(FONT, font_size)
    d = ImageDraw.Draw(canvas)
    if shadow:
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.text(xy, text, font=font, fill=(0, 0, 0, 100))
        sh = sh.filter(ImageFilter.GaussianBlur(5))
        canvas.alpha_composite(sh)
    d.text(xy, text, font=font, fill=color)


def main():
    bg = gradient(W, H)
    bg = with_blobs(bg)

    # Layout zones (left-aligned text, logo on the right)
    pad = 64

    # Eyebrow
    draw_text(
        bg, "SACOPARENTS  ·  RELATIONAL MEDIATION PREP",
        18, (pad, 70),
        color=(255, 255, 255, 220),
    )

    # Headline (3 lines for the longer copy)
    draw_text(bg, "The First Steps", 78, (pad, 120))
    draw_text(bg, "to Co-Parenting", 78, (pad, 215))
    draw_text(bg, "Starts Here.", 78, (pad, 310))

    # Subhead
    draw_text(
        bg, "Child-centered prep, in your pocket.",
        28, (pad, 420),
        color=(255, 255, 255, 235),
    )

    # CTA pill
    pill = Image.new("RGBA", (320, 56), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((0, 0, 319, 55), radius=28, fill=(255, 255, 255, 235))
    bg.alpha_composite(pill, (pad, 490))
    cf = ImageFont.truetype(FONT, 20)
    cd = ImageDraw.Draw(bg)
    cta_text = "sacoparentsapp.online  →"
    tb = cf.getbbox(cta_text)
    cta_x = pad + (320 - (tb[2] - tb[0])) // 2
    cd.text((cta_x, 490 + (56 - (tb[3] - tb[1])) // 2 - 4), cta_text, font=cf, fill=(61, 26, 120, 255))

    # Logo — right side, vertical center, with subtle glow
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        target = 320
        logo = logo.resize((target, target), Image.LANCZOS)
        # Soft glow halo
        halo = Image.new("RGBA", (target + 80, target + 80), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        hd.ellipse((10, 10, target + 70, target + 70), fill=(255, 255, 255, 70))
        halo = halo.filter(ImageFilter.GaussianBlur(30))
        bg.alpha_composite(halo, (W - target - 100, (H - target) // 2 - 40))
        bg.alpha_composite(logo, (W - target - 60, (H - target) // 2))

    bg.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"✅ Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
