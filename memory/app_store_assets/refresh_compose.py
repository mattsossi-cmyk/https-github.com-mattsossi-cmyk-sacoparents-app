"""Compose marketing-framed App Store / Play Store screenshots.

Inputs:  /app/memory/app_store_assets/refreshed_feb2026/raw/*.png  (1290x2796 mobile UI)
Outputs:
  iphone_6_7/*.png  → 1290x2796 (Apple required for new submissions)
  android_phone/*.png  → 1080x1920 (Play Store)

Design:
  - Brand gradient background (deep purple #3D1A78 → magenta #5E2DB5 → teal #2DB5B5)
  - Large caption text up top in Plus Jakarta Sans–style (white, bold)
  - Device frame: rounded-rect "phone" with subtle border + dynamic-island notch
  - Phone screen shows the captured UI (scaled to fit, rounded corners)
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAW_DIR = Path("/app/memory/app_store_assets/refreshed_feb2026/raw")
IOS_OUT = Path("/app/memory/app_store_assets/refreshed_feb2026/iphone_6_7")
AND_OUT = Path("/app/memory/app_store_assets/refreshed_feb2026/android_phone")
IOS_OUT.mkdir(parents=True, exist_ok=True)
AND_OUT.mkdir(parents=True, exist_ok=True)

# Captions tuned per screen
CAPTIONS = {
    "01_dashboard": ("Your space, ready", "when you are"),
    "02_child_goals": ("Keep your children", "at the center"),
    "03_communication": ("Reframe before", "you react"),
    "04_summary": ("AI-prepared mediation", "summary in minutes"),
    "05_reflection": ("Quiet space for", "honest reflection"),
    "06_safety": ("Help is always", "one tap away"),
}

# Gradient palette
G1 = (61, 26, 120)     # #3D1A78 deep royal purple
G2 = (94, 45, 181)     # #5E2DB5 magenta-purple
G3 = (45, 181, 181)    # #2DB5B5 teal

# Find a usable font on the system
def _find_font():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


FONT_PATH = _find_font()


def make_gradient(w, h):
    """Vertical → diagonal gradient G1 (top-left) → G2 (mid) → G3 (bottom-right)."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        # Two-stop interpolation through G2 around t=0.55
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
            # slight diagonal tilt
            dx = x / max(1, w - 1)
            sh = int(8 * (dx - 0.5))
            px[x, y] = (max(0, min(255, r + sh)), max(0, min(255, g + sh)), max(0, min(255, b - sh)))
    return img


def add_grain(img, opacity=18):
    """Subtle noise overlay so the gradient doesn't band on phones."""
    import random
    w, h = img.size
    noise = Image.new("L", (w, h))
    np = noise.load()
    for y in range(h):
        for x in range(w):
            np[x, y] = random.randint(0, 255)
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    color = Image.new("RGB", (w, h), (255, 255, 255))
    img = img.convert("RGB")
    img = Image.composite(color, img, noise.point(lambda v: int(v * opacity / 255)))
    return img


def add_blobs(img):
    """Soft accent circles for visual interest."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # Magenta blob upper-right
    r1 = int(w * 0.55)
    od.ellipse((w - r1 // 2, -r1 // 2, w + r1 // 2, r1 // 2), fill=(231, 78, 200, 40))
    # Teal blob lower-left
    r2 = int(w * 0.6)
    od.ellipse((-r2 // 2, h - r2 // 2, r2 // 2, h + r2 // 2), fill=(45, 181, 181, 38))
    overlay = overlay.filter(ImageFilter.GaussianBlur(80))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def rounded_mask(size, radius):
    w, h = size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    return m


def add_drop_shadow(img, offset=(0, 30), blur=40, opacity=120):
    """Return a new image with a soft shadow under `img` (RGBA)."""
    w, h = img.size
    pad = blur * 2
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((0, 0, w, h), radius=110, fill=(0, 0, 0, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(shadow, (pad + offset[0], pad + offset[1]), shadow)
    canvas.paste(img, (pad, pad), img)
    return canvas


def device_frame(content_img, phone_w):
    """Wrap content_img inside a rounded phone-shaped frame.
    phone_w is the desired final width of the phone in px.
    Returns RGBA.
    """
    cw, ch = content_img.size
    phone_h = int(phone_w * ch / cw)
    bezel = int(phone_w * 0.022)  # ~2.2% bezel
    inner_w = phone_w - bezel * 2
    inner_h = phone_h - bezel * 2

    # Frame background (charcoal)
    frame = Image.new("RGBA", (phone_w, phone_h), (24, 22, 36, 255))
    # Round the frame itself
    fm = rounded_mask((phone_w, phone_h), int(phone_w * 0.115))
    frame.putalpha(fm)

    # Scale the screen content to fit inner area
    screen = content_img.resize((inner_w, inner_h), Image.LANCZOS).convert("RGBA")
    sm = rounded_mask((inner_w, inner_h), int(phone_w * 0.09))
    screen.putalpha(sm)
    frame.paste(screen, (bezel, bezel), screen)

    # Dynamic-island notch (centered, near the top)
    notch_w = int(phone_w * 0.28)
    notch_h = int(phone_w * 0.038)
    notch_x = (phone_w - notch_w) // 2
    notch_y = int(phone_w * 0.038)
    notch = Image.new("RGBA", (notch_w, notch_h), (12, 10, 22, 255))
    nm = rounded_mask((notch_w, notch_h), notch_h // 2)
    notch.putalpha(nm)
    frame.alpha_composite(notch, (notch_x, notch_y))

    return frame


def draw_caption(canvas, line1, line2, top_y, max_w):
    """Draw a 2-line caption centered horizontally on canvas at top_y."""
    if not FONT_PATH:
        return
    w, _ = canvas.size
    # Auto-size to fit ~80% of width
    size = 110
    while size > 60:
        font = ImageFont.truetype(FONT_PATH, size)
        b1 = font.getbbox(line1)
        b2 = font.getbbox(line2)
        if (b1[2] - b1[0]) <= max_w and (b2[2] - b2[0]) <= max_w:
            break
        size -= 4
    font = ImageFont.truetype(FONT_PATH, size)
    d = ImageDraw.Draw(canvas)
    # Soft shadow for legibility on the gradient
    def _shadow_text(xy, text):
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.text(xy, text, font=font, fill=(0, 0, 0, 90))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        canvas.alpha_composite(sh)

    line_h = int(size * 1.15)
    b1 = font.getbbox(line1)
    x1 = (w - (b1[2] - b1[0])) // 2
    b2 = font.getbbox(line2)
    x2 = (w - (b2[2] - b2[0])) // 2

    _shadow_text((x1, top_y), line1)
    _shadow_text((x2, top_y + line_h), line2)
    d.text((x1, top_y), line1, font=font, fill=(255, 255, 255, 255))
    d.text((x2, top_y + line_h), line2, font=font, fill=(255, 255, 255, 255))


def draw_brand_eyebrow(canvas, y):
    """Small uppercase brand tag above the headline."""
    if not FONT_PATH:
        return
    font = ImageFont.truetype(FONT_PATH, 38)
    text = "SACOPARENTS  ·  RELATIONAL MEDIATION PREP"
    w, _ = canvas.size
    b = font.getbbox(text)
    x = (w - (b[2] - b[0])) // 2
    d = ImageDraw.Draw(canvas)
    d.text((x, y), text, font=font, fill=(255, 255, 255, 200))


def compose_feature_graphic(content_img, out_path):
    """Play Store feature graphic — landscape 1024x500.
    Brand-forward: gradient + tagline LEFT, phone PEEK on the RIGHT.
    """
    OW, OH = 1024, 500
    bg = make_gradient(OW, OH)
    bg = add_blobs(bg)
    bg = bg.convert("RGBA")

    # Eyebrow
    if FONT_PATH:
        eb = ImageFont.truetype(FONT_PATH, 22)
        d = ImageDraw.Draw(bg)
        d.text((58, 60), "SACOPARENTS  ·  MEDIATION PREP", font=eb, fill=(255, 255, 255, 220))
        # Headline
        hf = ImageFont.truetype(FONT_PATH, 64)
        d.text((58, 110), "Prepare for", font=hf, fill=(255, 255, 255, 255))
        d.text((58, 180), "mediation,", font=hf, fill=(255, 255, 255, 255))
        d.text((58, 250), "calmly.", font=hf, fill=(255, 255, 255, 255))
        # Sub
        sf = ImageFont.truetype(FONT_PATH, 22)
        d.text((58, 350), "Child-centered prep, in your pocket.", font=sf, fill=(255, 255, 255, 220))

    # Phone peek on the right — only top portion visible
    phone_w = 280
    frame = device_frame(content_img, phone_w)
    shaded = add_drop_shadow(frame, offset=(0, 18), blur=30, opacity=130)
    bg.alpha_composite(shaded, (OW - shaded.size[0] + 20, 40))

    bg.convert("RGB").save(out_path, "PNG", optimize=True)


def compose(slug, content_img, out_size, out_path):
    """Compose a single marketing screenshot."""
    OW, OH = out_size
    bg = make_gradient(OW, OH)
    bg = add_blobs(bg)
    bg = bg.convert("RGBA")

    # Header zone: ~30% of height for captions
    eyebrow_y = int(OH * 0.06)
    caption_y = int(OH * 0.085)

    cap1, cap2 = CAPTIONS.get(slug, ("SACOParents", ""))
    draw_brand_eyebrow(bg, eyebrow_y)
    draw_caption(bg, cap1, cap2, caption_y, max_w=int(OW * 0.85))

    # Device frame zone — phone occupies ~60% width, positioned lower 2/3
    phone_w = int(OW * 0.66)
    frame = device_frame(content_img, phone_w)
    fw, fh = frame.size

    # Drop shadow
    shaded = add_drop_shadow(frame, offset=(0, 36), blur=46, opacity=120)
    sw, sh = shaded.size

    # Place phone so it sits ~mid-lower, bleeding off the bottom slightly
    x = (OW - sw) // 2
    y = int(OH * 0.32) - (sw - fw) // 2  # account for shadow padding
    bg.alpha_composite(shaded, (x, y))

    bg = bg.convert("RGB")
    bg.save(out_path, "PNG", optimize=True)


def main():
    raw_files = sorted(RAW_DIR.glob("*.png"))
    if not raw_files:
        print("No raw screenshots — run refresh_capture.py first.")
        return
    SIZES = [
        ("iphone_6_7", (1290, 2796)),       # iPhone 15 Pro Max — required for App Store new submissions
        ("iphone_6_5", (1242, 2688)),       # iPhone Xs Max — fallback for older device tier
        ("ipad_12_9",  (2048, 2732)),       # iPad Pro 12.9" — App Store tablet tier
        ("android_phone", (1080, 1920)),    # Play Store phone
        ("play_feature_graphic", (1024, 500)),  # Play Store feature graphic (NOT a phone shot — special)
    ]
    out_root = Path("/app/memory/app_store_assets/refreshed_feb2026")
    for f in raw_files:
        slug = f.stem
        content = Image.open(f).convert("RGB")
        for dir_name, size in SIZES:
            out_dir = out_root / dir_name
            out_dir.mkdir(parents=True, exist_ok=True)
            if dir_name == "play_feature_graphic":
                if slug != "01_dashboard":
                    continue
                compose_feature_graphic(content, out_dir / "feature_graphic.png")
            else:
                compose(slug, content, size, out_dir / f"{slug}.png")
        print(f"composed {slug}")


if __name__ == "__main__":
    main()
