"""Detailed marketing flyer for SA Coparents.

Composes:
  * Real SA Coparents logo (heart-shaped family — /app/backend/assets/sa_coparents_logo.png)
  * "Three Reports. One Goal." infographic
    (/app/frontend/public/images/three-reports-poster.png)
  * Feature grid (Coach-drafted replies, journaling, safety, Gmail assistant)
  * "How it works" numbered strip
  * CTA band with QR code + URL

Headline anchor: "Helping parents communicate better."

Outputs:
  /app/frontend/public/flyers/sacoparents-flyer-detailed-letter.png (2550x3300 @300dpi)
  /app/frontend/public/flyers/sacoparents-flyer-detailed-letter.pdf
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import qrcode

# ---- Brand tokens ----------------------------------------------------------
DEEP_PURPLE = (61, 26, 120)      # #3D1A78
MID_PURPLE = (94, 45, 181)       # #5E2DB5
TEAL = (45, 181, 181)            # #2DB5B5
INK = (26, 19, 48)               # #1A1330
MUTED = (133, 126, 156)          # #857E9C
BODY = (75, 69, 103)             # #4B4567
CREAM = (250, 247, 255)
WHITE = (255, 255, 255)

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF_R = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

LOGO_PATH = Path("/app/backend/assets/sa_coparents_logo.png")
REPORTS_POSTER = Path("/app/frontend/public/images/three-reports-poster.png")
PHONE_MOCKUP = Path("/app/memory/app_store_assets/refreshed_feb2026/iphone_6_7/01_dashboard.png")
OUT_DIR = Path("/app/frontend/public/flyers")
OUT_DIR.mkdir(parents=True, exist_ok=True)

APP_URL = "https://sacoparentsapp.online"


def font(path, size):
    return ImageFont.truetype(path, size)


def draw_wrap(draw, text, xy, max_width, ft, fill, line_h_mul=1.28):
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


def vgradient(w, h, top, bottom, mid=None):
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


def rounded_paste(base: Image.Image, overlay: Image.Image, xy: tuple, radius: int):
    """Paste `overlay` onto `base` at `xy` with rounded corners."""
    mask = Image.new("L", overlay.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, overlay.width, overlay.height),
                                           radius=radius, fill=255)
    base.paste(overlay, xy, mask)


def qr(url: str, size_px: int) -> Image.Image:
    q = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12, border=1,
    )
    q.add_data(url)
    q.make(fit=True)
    im = q.make_image(fill_color=(26, 19, 48), back_color="white").convert("RGB")
    return im.resize((size_px, size_px), Image.LANCZOS)


def draw_icon_tile(draw, cx, cy, r, color):
    """Simple rounded tile behind a glyph."""
    draw.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=r // 3, fill=color)


def glyph_speech(draw, cx, cy, r, color=WHITE):
    """A little speech-bubble glyph."""
    pad = r // 3
    draw.rounded_rectangle((cx - r + pad, cy - r + pad - 4, cx + r - pad, cy + r - pad - 12),
                           radius=r // 4, fill=color)
    # tail
    draw.polygon(
        [(cx - r // 4, cy + r - pad - 12), (cx, cy + r - pad + 8), (cx + r // 6, cy + r - pad - 12)],
        fill=color,
    )


def glyph_shield(draw, cx, cy, r, color=WHITE):
    r2 = r - r // 4
    draw.polygon(
        [(cx, cy - r2), (cx + r2, cy - r2 // 2),
         (cx + r2 - r2 // 6, cy + r2), (cx, cy + r2 + r2 // 6),
         (cx - r2 + r2 // 6, cy + r2), (cx - r2, cy - r2 // 2)],
        fill=color,
    )
    # check
    draw.line([(cx - r2 // 3, cy), (cx - 4, cy + r2 // 3), (cx + r2 // 2, cy - r2 // 3)],
              fill=DEEP_PURPLE, width=max(3, r // 10))


def glyph_pen(draw, cx, cy, r, color=WHITE):
    from math import cos, sin, radians
    # tilted rectangle "pen"
    length = r * 1.5
    width = r * 0.4
    ang = radians(-35)
    pts = [
        (cx - length / 2 * cos(ang) - width / 2 * sin(ang), cy - length / 2 * sin(ang) + width / 2 * cos(ang)),
        (cx + length / 2 * cos(ang) - width / 2 * sin(ang), cy + length / 2 * sin(ang) + width / 2 * cos(ang)),
        (cx + length / 2 * cos(ang) + width / 2 * sin(ang), cy + length / 2 * sin(ang) - width / 2 * cos(ang)),
        (cx - length / 2 * cos(ang) + width / 2 * sin(ang), cy - length / 2 * sin(ang) - width / 2 * cos(ang)),
    ]
    draw.polygon(pts, fill=color)


def glyph_mail(draw, cx, cy, r, color=WHITE):
    box = (cx - r, cy - r // 2, cx + r, cy + r // 2)
    draw.rounded_rectangle(box, radius=r // 6, fill=color)
    draw.polygon(
        [(cx - r, cy - r // 2), (cx, cy + r // 6), (cx + r, cy - r // 2)],
        fill=DEEP_PURPLE,
    )


def build_letter() -> Path:
    W, H = 2550, 3300
    img = vgradient(W, H, DEEP_PURPLE, TEAL, mid=MID_PURPLE)

    # Top glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius in range(1600, 200, -80):
        alpha = int(60 * (1 - radius / 1600))
        gd.ellipse((W // 2 - radius, -radius + 260, W // 2 + radius, radius + 260),
                   fill=(255, 255, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img.paste(glow, (0, 0), glow)

    d = ImageDraw.Draw(img, "RGBA")

    # ============ HEADER ============
    # Real logo (chip on white for legibility)
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_size = 460
    logo_thumb = logo.copy()
    logo_thumb.thumbnail((logo_size, logo_size))
    # White circular chip
    chip_r = 250
    chip_cx, chip_cy = W // 2, 340
    d.ellipse((chip_cx - chip_r, chip_cy - chip_r,
               chip_cx + chip_r, chip_cy + chip_r), fill=WHITE)
    lx = chip_cx - logo_thumb.width // 2
    ly = chip_cy - logo_thumb.height // 2
    img.paste(logo_thumb, (lx, ly), logo_thumb)

    # Wordmark
    f_brand = font(SANS_B, 120)
    brand = "SA Coparents"
    bw = d.textlength(brand, font=f_brand)
    d.text(((W - bw) // 2, 640), brand, fill=WHITE, font=f_brand)

    # Eyebrow tagline
    f_eye = font(SANS_B, 42)
    eye = "AN APP FOR FAMILIES · MADE WITH CARE"
    ew = d.textlength(eye, font=f_eye)
    d.text(((W - ew) // 2, 790), eye, fill=(255, 255, 255, 220), font=f_eye)
    d.rectangle(((W - ew) // 2, 850, (W - ew) // 2 + ew, 854), fill=(255, 255, 255, 180))

    # Headline
    f_h1 = font(SERIF, 150)
    y = 940
    for line in ["Helping parents", "communicate better."]:
        lw = d.textlength(line, font=f_h1)
        d.text(((W - lw) // 2, y), line, fill=WHITE, font=f_h1)
        y += 175

    # Deck
    f_deck = font(SERIF_R, 56)
    deck = "Less conflict. More calm. A private space for co-parenting families to reflect, plan, and communicate — with their child at the centre."
    y += 20
    y = draw_wrap(d, deck, (200, y), W - 400, f_deck, (255, 255, 255, 235), 1.32)

    # ============ THREE REPORTS PANEL ============
    y += 60
    reports = Image.open(REPORTS_POSTER).convert("RGB")
    # Fit width, respect aspect
    target_w = W - 240
    ratio = target_w / reports.width
    target_h = int(reports.height * ratio)
    reports = reports.resize((target_w, target_h), Image.LANCZOS)
    rounded_paste(img, reports, (120, y), radius=48)
    y += target_h + 60

    # ============ FEATURE GRID ============
    grid_top = y
    # Feature card background (soft white)
    grid_pad = 100
    grid_h = 620
    d.rounded_rectangle((grid_pad, grid_top, W - grid_pad, grid_top + grid_h),
                        radius=48, fill=WHITE)

    # Title
    f_gt = font(SERIF, 76)
    d.text((grid_pad + 60, grid_top + 45), "What you get inside the app", fill=INK, font=f_gt)
    f_gs = font(SANS, 40)
    d.text((grid_pad + 60, grid_top + 145),
           "Built to help you show up steady — for yourself and for your kids.",
           fill=BODY, font=f_gs)

    # 4 feature tiles in a row
    tiles = [
        ("Coach-drafted replies",
         "AI rewrites emotionally-loaded messages into calm, child-centred responses.",
         glyph_speech, DEEP_PURPLE),
        ("Journaling & breathing",
         "Guided prompts and a 4-7-8 breathing widget to steady you before you reply.",
         glyph_pen, TEAL),
        ("Safety-first tools",
         "Danger-Assessment-informed check-in, quick exit, hotlines always one tap away.",
         glyph_shield, MID_PURPLE),
        ("Gmail assistant",
         "Read, search & send co-parenting emails from inside the app, with coach support.",
         glyph_mail, DEEP_PURPLE),
    ]
    tile_w = (W - 2 * grid_pad - 120) // 4
    tile_x = grid_pad + 60
    tile_y = grid_top + 240
    tile_h = 340
    for title, body, gfn, color in tiles:
        # icon disc
        icx, icy = tile_x + 62, tile_y + 62
        draw_icon_tile(d, icx, icy, 60, color)
        gfn(d, icx, icy, 40, WHITE)
        # title
        f_tt = font(SANS_B, 40)
        d.text((tile_x, tile_y + 150), title, fill=INK, font=f_tt)
        # body
        f_tb = font(SANS, 32)
        draw_wrap(d, body, (tile_x, tile_y + 210), tile_w - 20, f_tb, BODY, 1.35)
        tile_x += tile_w + 40

    y = grid_top + grid_h + 60

    # ============ HOW IT WORKS ============
    steps = [
        ("1", "Reflect",
         "Journal what's going on, so you're not reacting from a raw moment."),
        ("2", "Plan",
         "Name your child-centred goals, priorities, and communication style."),
        ("3", "Communicate",
         "Draft replies with the coach and send them straight from the app."),
    ]
    hw_bg_h = 460
    d.rounded_rectangle((grid_pad, y, W - grid_pad, y + hw_bg_h),
                        radius=48, fill=(255, 255, 255, 40))
    f_hw = font(SERIF, 76)
    d.text((grid_pad + 60, y + 45), "How it works", fill=WHITE, font=f_hw)

    step_x = grid_pad + 60
    step_y = y + 190
    step_w = (W - 2 * grid_pad - 120 - 120) // 3
    for num, label, desc in steps:
        d.ellipse((step_x, step_y, step_x + 96, step_y + 96), fill=WHITE)
        f_num = font(SERIF, 62)
        nw = d.textlength(num, font=f_num)
        d.text((step_x + (96 - nw) // 2, step_y + 8), num, fill=DEEP_PURPLE, font=f_num)
        f_lb = font(SANS_B, 44)
        d.text((step_x + 120, step_y + 8), label, fill=WHITE, font=f_lb)
        f_ds = font(SANS, 32)
        draw_wrap(d, desc, (step_x + 120, step_y + 70), step_w - 130, f_ds,
                  (255, 255, 255, 235), 1.32)
        step_x += step_w + 60

    y += hw_bg_h + 60

    # ============ CTA BAND ============
    band_top = y
    band_h = 380
    # solid dark band with teal accent
    band = Image.new("RGB", (W - 200, band_h), DEEP_PURPLE)
    acc = Image.new("RGB", band.size, TEAL)
    mask = Image.new("L", band.size, 0)
    ImageDraw.Draw(mask).ellipse((-400, -180, 900, band_h + 200), fill=170)
    band.paste(acc, (0, 0), mask.filter(ImageFilter.GaussianBlur(60)))
    r_mask = Image.new("L", band.size, 0)
    ImageDraw.Draw(r_mask).rounded_rectangle((0, 0, band.width, band.height),
                                             radius=48, fill=255)
    img.paste(band, (100, band_top), r_mask)

    dband = ImageDraw.Draw(img)
    f_cta = font(SERIF, 92)
    dband.text((180, band_top + 55), "Start using it today.", fill=WHITE, font=f_cta)
    f_ctasub = font(SANS, 44)
    dband.text((180, band_top + 175),
               "Free to try. Private by default. Works in your browser.",
               fill=(255, 255, 255, 235), font=f_ctasub)
    f_url = font(SANS_B, 60)
    dband.text((180, band_top + 250), APP_URL, fill=WHITE, font=f_url)

    # QR
    qr_size = 300
    qr_img = qr(APP_URL, qr_size)
    qr_frame = Image.new("RGB", (qr_size + 40, qr_size + 40), WHITE)
    qr_frame.paste(qr_img, (20, 20))
    img.paste(qr_frame, (W - 100 - qr_size - 60, band_top + (band_h - qr_size) // 2 - 20))
    f_scan = font(SANS_B, 32)
    dband.text((W - 100 - qr_size - 60, band_top + band_h - 60),
               "SCAN TO OPEN →", fill=WHITE, font=f_scan)

    # Footer
    footer_y = band_top + band_h + 30
    f_foot = font(SANS, 32)
    footer = "© 2026 SA Coparents · Helping families communicate better · Contact: mattsossi@bsossi.com"
    fw = dband.textlength(footer, font=f_foot)
    dband.text(((W - fw) // 2, footer_y), footer, fill=(255, 255, 255, 210), font=f_foot)

    out_png = OUT_DIR / "sacoparents-flyer-detailed-letter.png"
    img.save(out_png, "PNG", optimize=True)
    return img, out_png


# ============================================================================
# BACK SIDE — App preview + QR to open the app
# ============================================================================

def build_back() -> tuple[Image.Image, Path]:
    W, H = 2550, 3300
    img = vgradient(W, H, DEEP_PURPLE, TEAL, mid=MID_PURPLE)

    # Ambient glow behind phone
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius in range(1400, 200, -80):
        alpha = int(70 * (1 - radius / 1400))
        gd.ellipse((W // 2 - radius, 1200 - radius, W // 2 + radius, 1200 + radius),
                   fill=(255, 255, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    img.paste(glow, (0, 0), glow)

    d = ImageDraw.Draw(img, "RGBA")

    # ---- Small logo chip top-left ----
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_thumb = logo.copy()
    logo_thumb.thumbnail((260, 260))
    chip_r = 140
    d.ellipse((100, 100, 100 + chip_r * 2, 100 + chip_r * 2), fill=WHITE)
    img.paste(logo_thumb,
              (100 + chip_r - logo_thumb.width // 2,
               100 + chip_r - logo_thumb.height // 2),
              logo_thumb)

    # Wordmark next to chip
    f_wm = font(SANS_B, 84)
    d.text((100 + chip_r * 2 + 40, 100 + chip_r - 42),
           "SA Coparents", fill=WHITE, font=f_wm)
    f_wmsub = font(SANS, 34)
    d.text((100 + chip_r * 2 + 40, 100 + chip_r + 46),
           "Helping parents communicate better",
           fill=(255, 255, 255, 220), font=f_wmsub)

    # ---- Headline ----
    f_h1 = font(SERIF, 138)
    y = 500
    for line in ["See it inside", "the app."]:
        lw = d.textlength(line, font=f_h1)
        d.text(((W - lw) // 2, y), line, fill=WHITE, font=f_h1)
        y += 160

    # Deck
    f_deck = font(SERIF_R, 52)
    deck = "A calm, private space to reflect, plan, and reply — with your child at the centre."
    y += 20
    y = draw_wrap(d, deck, (280, y), W - 560, f_deck, (255, 255, 255, 235), 1.32)

    # ---- Phone mockup ----
    phone = Image.open(PHONE_MOCKUP).convert("RGBA")
    # The phone mockup already has brand gradient + tagline. Take just the
    # phone body: crop the bottom 60% to isolate the device.
    ph_w, ph_h = phone.size
    crop = phone.crop((0, int(ph_h * 0.32), ph_w, ph_h))
    # scale
    target_w = 1050
    ratio = target_w / crop.width
    target_h = int(crop.height * ratio)
    crop = crop.resize((target_w, target_h), Image.LANCZOS)

    # Position: centre horizontally, below deck
    px = (W - target_w) // 2
    py = y + 60

    # soft drop shadow
    shadow = Image.new("RGBA", (target_w + 200, target_h + 200), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (100, 100, 100 + target_w, 100 + target_h),
        radius=80, fill=(0, 0, 0, 130),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(50))
    img.paste(shadow, (px - 100, py - 60), shadow)
    img.paste(crop, (px, py), crop)

    # ---- Side callouts (tips floating around the phone) ----
    callouts = [
        (py + 260, "Personalised dashboard",
         "Pick up where you left off — nothing here is graded.", "left"),
        (py + 720, "Coach-drafted replies",
         "Rewrite emotionally-charged messages into calm, child-centred ones.", "left"),
        (py + 260, "Journal & breathe",
         "4-7-8 breathing widget and guided prompts to steady you.", "right"),
        (py + 720, "Safety-first tools",
         "DA-informed check-in, quick exit, and hotlines one tap away.", "right"),
    ]
    card_w = 620
    card_h = 220
    f_ct = font(SANS_B, 42)
    f_cb = font(SANS, 32)
    for cy, title, body, side in callouts:
        if side == "left":
            card_x = 100
            line_x1 = card_x + card_w
            line_x2 = px + target_w // 6
        else:
            card_x = W - 100 - card_w
            line_x1 = card_x
            line_x2 = px + target_w - target_w // 6
        d.rounded_rectangle((card_x, cy, card_x + card_w, cy + card_h),
                            radius=32, fill=(255, 255, 255, 235))
        d.text((card_x + 34, cy + 26), title, fill=INK, font=f_ct)
        draw_wrap(d, body, (card_x + 34, cy + 88), card_w - 68, f_cb, BODY, 1.32)
        line_y = cy + card_h // 2
        d.line([(line_x1, line_y), (line_x2, line_y)],
               fill=(255, 255, 255, 200), width=3)
        d.ellipse((line_x2 - 8, line_y - 8, line_x2 + 8, line_y + 8),
                  fill=WHITE)

    # ---- Bottom "open the app" card ----
    band_top = py + target_h + 80
    band_h = 500
    if band_top + band_h > H - 120:
        band_top = H - 120 - band_h
    d.rounded_rectangle((100, band_top, W - 100, band_top + band_h),
                        radius=56, fill=WHITE)

    # left side text
    f_open = font(SERIF, 110)
    d.text((180, band_top + 55), "Open the app.", fill=INK, font=f_open)
    f_openb = font(SANS, 44)
    y2 = draw_wrap(
        d,
        "Free to try. Private by default. No download required — it works in your phone or laptop browser.",
        (180, band_top + 190), 1400, f_openb, BODY, 1.32,
    )
    f_url = font(SANS_B, 68)
    d.text((180, y2 + 20), APP_URL, fill=DEEP_PURPLE, font=f_url)

    # small "add to home screen" hint
    f_hint = font(SANS, 32)
    hint = "Tip: on your phone, tap Share → Add to Home Screen for an app-like icon."
    d.text((180, y2 + 110), hint, fill=MUTED, font=f_hint)

    # QR right side
    qr_size = 380
    qr_img = qr(APP_URL, qr_size)
    qr_frame = Image.new("RGB", (qr_size + 40, qr_size + 40), WHITE)
    qr_frame.paste(qr_img, (20, 20))
    # frame with subtle border
    frame_border = Image.new("RGB", (qr_frame.width + 12, qr_frame.height + 12), DEEP_PURPLE)
    frame_border.paste(qr_frame, (6, 6))
    img.paste(frame_border, (W - 100 - qr_frame.width - 60,
                             band_top + (band_h - qr_frame.height) // 2 - 30))
    f_scan = font(SANS_B, 36)
    d.text((W - 100 - qr_frame.width - 60,
            band_top + (band_h - qr_frame.height) // 2 + qr_frame.height - 10),
           "SCAN TO OPEN →", fill=DEEP_PURPLE, font=f_scan)

    # Footer
    f_foot = font(SANS, 32)
    footer = "© 2026 SA Coparents · Helping families communicate better · Contact: mattsossi@bsossi.com"
    fw = d.textlength(footer, font=f_foot)
    d.text(((W - fw) // 2, H - 90), footer, fill=(255, 255, 255, 210), font=f_foot)

    out_png = OUT_DIR / "sacoparents-flyer-detailed-back.png"
    img.save(out_png, "PNG", optimize=True)
    return img, out_png


def combine_pdf(front: Image.Image, back: Image.Image) -> Path:
    out = OUT_DIR / "sacoparents-flyer-detailed-2page.pdf"
    # Convert to RGB if needed
    front_rgb = front.convert("RGB")
    back_rgb = back.convert("RGB")
    front_rgb.save(out, "PDF", resolution=300, save_all=True, append_images=[back_rgb])
    return out


if __name__ == "__main__":
    front_img, front_png = build_letter()
    back_img, back_png = build_back()
    pdf = combine_pdf(front_img, back_img)
    print("front PNG :", front_png, front_png.stat().st_size, "bytes")
    print("back  PNG :", back_png, back_png.stat().st_size, "bytes")
    print("2-page PDF:", pdf, pdf.stat().st_size, "bytes")
