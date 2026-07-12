"""Build print + digital marketing flyers for SA Coparents.

Message centred on: "Helping parents communicate better."
No mediation copy on the flyer.

Outputs:
  /app/frontend/public/flyers/sacoparents-flyer-letter.png  (2550x3300 @300dpi)
  /app/frontend/public/flyers/sacoparents-flyer-letter.pdf  (print-ready)
  /app/frontend/public/flyers/sacoparents-flyer-square.png  (2160x2160 @2x)
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
try:
    import qrcode
except ImportError:  # pragma: no cover — fallback if not installed
    qrcode = None

# ---- Brand -----------------------------------------------------------------
DEEP_PURPLE = (61, 26, 120)      # #3D1A78
MID_PURPLE = (94, 45, 181)       # #5E2DB5
TEAL = (45, 181, 181)            # #2DB5B5
INK = (26, 19, 48)               # #1A1330
MUTED = (133, 126, 156)          # #857E9C
BODY = (75, 69, 103)             # #4B4567
CREAM = (250, 247, 255)
WHITE = (255, 255, 255)

# Fonts
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF_R = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

OUT_DIR = Path("/app/frontend/public/flyers")
OUT_DIR.mkdir(parents=True, exist_ok=True)

APP_URL = "https://sacoparentsapp.online"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def vgradient(w: int, h: int, top, bottom, mid=None) -> Image.Image:
    """Vertical linear gradient with an optional middle stop."""
    img = Image.new("RGB", (w, h), top)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if mid is None:
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
        else:
            if t < 0.5:
                tt = t / 0.5
                r = int(top[0] + (mid[0] - top[0]) * tt)
                g = int(top[1] + (mid[1] - top[1]) * tt)
                b = int(top[2] + (mid[2] - top[2]) * tt)
            else:
                tt = (t - 0.5) / 0.5
                r = int(mid[0] + (bottom[0] - mid[0]) * tt)
                g = int(mid[1] + (bottom[1] - mid[1]) * tt)
                b = int(mid[2] + (bottom[2] - mid[2]) * tt)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def draw_heart_family(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color=WHITE):
    """Stylised heart-shaped family mark centred at (cx,cy) sized `size` square."""
    from PIL import ImageDraw as _D  # noqa

    # Two circles + triangle = heart silhouette
    r = size // 2
    # left lobe
    draw.ellipse((cx - r, cy - r, cx, cy), fill=color)
    # right lobe
    draw.ellipse((cx, cy - r, cx + r, cy), fill=color)
    # bottom triangle
    draw.polygon(
        [(cx - r, cy - r // 4), (cx + r, cy - r // 4), (cx, cy + r)],
        fill=color,
    )
    # eyes + smile — tiny, inline family motif
    eye_r = max(2, r // 10)
    ex1 = cx - r // 3
    ex2 = cx + r // 3
    ey = cy - r // 6
    draw.ellipse((ex1 - eye_r, ey - eye_r, ex1 + eye_r, ey + eye_r), fill=DEEP_PURPLE)
    draw.ellipse((ex2 - eye_r, ey - eye_r, ex2 + eye_r, ey + eye_r), fill=DEEP_PURPLE)
    # smile
    sy = cy + r // 6
    draw.arc(
        (cx - r // 3, sy - r // 6, cx + r // 3, sy + r // 4),
        start=10, end=170, fill=DEEP_PURPLE, width=max(2, r // 22),
    )


def qr_code(url: str, box_size: int = 12, border: int = 2) -> Image.Image | None:
    if qrcode is None:
        return None
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color=(26, 19, 48), back_color="white").convert("RGB")


def draw_wrap(draw: ImageDraw.ImageDraw, text: str, xy, max_width, ft, fill, line_h_mul=1.15):
    x, y = xy
    words = text.split(" ")
    line = ""
    for w in words:
        trial = (line + " " + w).strip()
        tw = draw.textlength(trial, font=ft)
        if tw > max_width and line:
            draw.text((x, y), line, fill=fill, font=ft)
            y += int(ft.size * line_h_mul)
            line = w
        else:
            line = trial
    if line:
        draw.text((x, y), line, fill=fill, font=ft)
        y += int(ft.size * line_h_mul)
    return y


def sparkle(draw, cx, cy, r, color=WHITE, alpha=None):
    """Little 4-point sparkle for background garnish."""
    draw.polygon(
        [(cx, cy - r), (cx + r // 3, cy), (cx, cy + r), (cx - r // 3, cy)],
        fill=color,
    )
    draw.polygon(
        [(cx - r, cy), (cx, cy - r // 3), (cx + r, cy), (cx, cy + r // 3)],
        fill=color,
    )


# ---- LETTER (US, portrait) -------------------------------------------------

def build_letter() -> Path:
    # 8.5x11 inch @ 300 dpi = 2550 x 3300
    W, H = 2550, 3300
    img = vgradient(W, H, DEEP_PURPLE, TEAL, mid=MID_PURPLE)

    # subtle radial glow top
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius in range(1600, 200, -80):
        alpha = int(60 * (1 - radius / 1600))
        gd.ellipse((W // 2 - radius, -radius + 200, W // 2 + radius, radius + 200),
                   fill=(255, 255, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img.paste(glow, (0, 0), glow)

    d = ImageDraw.Draw(img, "RGBA")

    # sparkles / soft dots (subtle)
    import random
    random.seed(7)
    for _ in range(60):
        x = random.randint(80, W - 80)
        y = random.randint(80, H - 80)
        r = random.choice([6, 8, 10, 14, 18])
        sparkle(d, x, y, r, color=(255, 255, 255, 40))

    # ---- Header logo mark ----
    draw_heart_family(d, W // 2, 480, size=340, color=WHITE)

    # Wordmark
    f_brand = font(SANS_B, 120)
    brand = "SA Coparents"
    bw = d.textlength(brand, font=f_brand)
    d.text(((W - bw) // 2, 720), brand, fill=WHITE, font=f_brand)

    # Tagline eyebrow
    f_eye = font(SANS_B, 44)
    eye = "AN APP FOR FAMILIES · MADE WITH CARE"
    ew = d.textlength(eye, font=f_eye)
    d.text(((W - ew) // 2, 880), eye, fill=(255, 255, 255, 200), font=f_eye)
    # underline bar
    d.rectangle(((W - ew) // 2, 950, (W - ew) // 2 + ew, 954), fill=(255, 255, 255, 180))

    # ---- Big message card (white, soft) ----
    card_top = 1080
    card_bottom = 2560
    card_pad = 160
    card_rect = (card_pad, card_top, W - card_pad, card_bottom)
    d.rounded_rectangle(card_rect, radius=64, fill=WHITE)

    # Headline — the exact requested message
    f_h1 = font(SERIF, 168)
    headline_lines = ["Helping parents", "communicate better."]
    y = card_top + 130
    for line in headline_lines:
        lw = d.textlength(line, font=f_h1)
        d.text(((W - lw) // 2, y), line, fill=INK, font=f_h1)
        y += 195

    # Deck sentence
    f_deck = font(SERIF_R, 66)
    deck = "For separated, divorced, and co-parenting families who want less conflict — and more calm."
    y += 30
    max_w = W - (card_pad + 200) * 2 + 200
    y = draw_wrap(d, deck, (card_pad + 120, y), max_w, f_deck, BODY, line_h_mul=1.28)

    # ---- Three value bullets ----
    y += 60
    bullets = [
        ("Calm, not reactive.",
         "AI-powered coach helps you write replies that stay child-centred — even on the hard days."),
        ("A private space to think.",
         "Journaling prompts, breathing exercises, and reflections that keep you steady."),
        ("Real support when you need it.",
         "Safety tools, crisis hotlines, and communication guidance — always one tap away."),
    ]
    f_bt = font(SANS_B, 60)
    f_bb = font(SANS, 46)
    left_x = card_pad + 130
    right_x = W - card_pad - 130
    for title, body in bullets:
        # dot
        d.ellipse((left_x - 42, y + 22, left_x - 10, y + 54), fill=DEEP_PURPLE)
        d.text((left_x + 20, y), title, fill=INK, font=f_bt)
        y2 = draw_wrap(d, body, (left_x + 20, y + 74), right_x - left_x - 20, f_bb, BODY, 1.32)
        y = y2 + 34

    # ---- Bottom CTA band (dark) ----
    band_top = 2620
    band_bot = 3120
    band = Image.new("RGB", (W - 200, band_bot - band_top), DEEP_PURPLE)
    # soft teal accent
    accent = Image.new("RGB", (W - 200, band_bot - band_top), TEAL)
    mask = Image.new("L", accent.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-400, -200, 900, (band_bot - band_top) + 200), fill=180)
    band.paste(accent, (0, 0), mask.filter(ImageFilter.GaussianBlur(60)))
    # round the band
    band_r = Image.new("L", band.size, 0)
    ImageDraw.Draw(band_r).rounded_rectangle((0, 0, band.width, band.height), radius=56, fill=255)
    img.paste(band, (100, band_top), band_r)

    # Text on band
    dband = ImageDraw.Draw(img)
    f_cta = font(SERIF, 108)
    dband.text((180, band_top + 70), "Start using it today.", fill=WHITE, font=f_cta)

    f_ctasub = font(SANS, 52)
    dband.text((180, band_top + 210), "Free to try. Private by default.", fill=(255, 255, 255, 235), font=f_ctasub)

    f_url = font(SANS_B, 62)
    dband.text((180, band_top + 300), APP_URL, fill=WHITE, font=f_url)

    f_tag = font(SANS, 40)
    dband.text((180, band_top + 380),
               "Works in your browser · No app store required",
               fill=(255, 255, 255, 220), font=f_tag)

    # QR code
    qr = qr_code(APP_URL, box_size=10, border=2)
    if qr is not None:
        qr = qr.resize((400, 400))
        qr_frame = Image.new("RGB", (440, 440), WHITE)
        qr_frame.paste(qr, (20, 20))
        img.paste(qr_frame, (W - 100 - 440 - 40, band_top + 30))
        # Scan tag
        dband.text((W - 100 - 440 - 20, band_top + 480),
                   "Scan to open →", fill=WHITE, font=f_tag)

    # Footer
    f_foot = font(SANS, 36)
    footer = "© 2026 SA Coparents · Helping families communicate better"
    fw = dband.textlength(footer, font=f_foot)
    dband.text(((W - fw) // 2, H - 90), footer, fill=(255, 255, 255, 200), font=f_foot)

    out_png = OUT_DIR / "sacoparents-flyer-letter.png"
    out_pdf = OUT_DIR / "sacoparents-flyer-letter.pdf"
    img.save(out_png, "PNG", optimize=True)
    img.save(out_pdf, "PDF", resolution=300)
    return out_png


# ---- 1080x1080 SQUARE (digital / IG) ---------------------------------------

def build_square() -> Path:
    W = H = 2160  # 2x for retina
    img = vgradient(W, H, DEEP_PURPLE, TEAL, mid=MID_PURPLE)
    d = ImageDraw.Draw(img, "RGBA")

    # sparkles
    import random
    random.seed(3)
    for _ in range(40):
        x = random.randint(60, W - 60)
        y = random.randint(60, H - 60)
        r = random.choice([6, 10, 14, 20])
        sparkle(d, x, y, r, color=(255, 255, 255, 55))

    # Big centred logo mark
    draw_heart_family(d, W // 2, 380, size=280, color=WHITE)

    # Wordmark
    f_brand = font(SANS_B, 92)
    brand = "SA Coparents"
    bw = d.textlength(brand, font=f_brand)
    d.text(((W - bw) // 2, 560), brand, fill=WHITE, font=f_brand)

    # Card
    card = (140, 780, W - 140, H - 260)
    d.rounded_rectangle(card, radius=60, fill=WHITE)

    # Headline
    f_h1 = font(SERIF, 158)
    y = card[1] + 130
    for line in ["Helping parents", "communicate", "better."]:
        lw = d.textlength(line, font=f_h1)
        d.text(((W - lw) // 2, y), line, fill=INK, font=f_h1)
        y += 175

    # Deck
    f_deck = font(SERIF_R, 60)
    deck = "Less conflict. More calm. A private space for co-parenting families."
    y += 40
    y = draw_wrap(d, deck, (card[0] + 130, y), card[2] - card[0] - 260, f_deck, BODY, 1.3)

    # CTA line
    y += 60
    f_url = font(SANS_B, 70)
    url_w = d.textlength(APP_URL, font=f_url)
    d.text(((W - url_w) // 2, y), APP_URL, fill=DEEP_PURPLE, font=f_url)

    out = OUT_DIR / "sacoparents-flyer-square.png"
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    p1 = build_letter()
    p2 = build_square()
    print("wrote:", p1, p1.stat().st_size, "bytes")
    print("wrote:", p2, p2.stat().st_size, "bytes")
