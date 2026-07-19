"""Certificate of Completion generator.

Composes a personalised PNG (and optional PDF) certificate by overlaying the
parent's name and today's date on the pre-designed template stored at
`frontend/public/images/certificate-template.png`.

The template already contains the SA CoParents branding, seal, signature and
copy — we only fill in the two dynamic fields:

  - Name  → cursive teal script, centred
  - Date  → serif dark navy, above the DATE underline

Public entry points
-------------------
build_certificate_png(name, date_str=None) -> bytes
build_certificate_pdf(name, date_str=None) -> bytes
"""

import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# Match the template we ship in the app bundle.
_TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "frontend",
        "public",
        "images",
        "certificate-template.png",
    )
)

_FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
_CURSIVE_FONT = os.path.join(_FONT_DIR, "GreatVibes-Regular.ttf")
_SERIF_FONT = os.path.join(_FONT_DIR, "PlayfairDisplay-Bold.ttf")

# Colours sampled from the on-template artwork so the overlay reads as one piece.
_TEAL = (32, 118, 130)          # cursive name
_NAVY = (20, 40, 78)            # date
_PAPER = (253, 250, 245)        # cream background — sampled from blank areas

# Layout constants calibrated for the 1426x1103 template.
# The template ships with pre-baked placeholder text ("Parent Name Here" and
# "May 15, 2026") that we mask out with `_PAPER` before drawing the real values.
_NAME_MASK = (250, 420, 1180, 550)   # bounding box of the placeholder cursive
_NAME_CENTER_X = 713
_NAME_BASELINE_Y = 505               # visual baseline where the cursive sits
_NAME_MAX_WIDTH = 1050
_NAME_MAX_FONT = 130
_NAME_MIN_FONT = 55

_DATE_MASK = (335, 905, 585, 945)    # bounding box of the placeholder date
_DATE_CENTER_X = 460
_DATE_BASELINE_Y = 935
_DATE_FONT_SIZE = 32


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _fit_name_font(draw: ImageDraw.ImageDraw, name: str) -> ImageFont.FreeTypeFont:
    """Return the largest Great Vibes size that keeps the name within the
    divider. Long names naturally shrink so they still look balanced."""
    size = _NAME_MAX_FONT
    while size > _NAME_MIN_FONT:
        font = _load_font(_CURSIVE_FONT, size)
        w = draw.textlength(name, font=font)
        if w <= _NAME_MAX_WIDTH:
            return font
        size -= 4
    return _load_font(_CURSIVE_FONT, _NAME_MIN_FONT)


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: int,
    top_y: int,
    font: ImageFont.FreeTypeFont,
    fill,
):
    """Draw `text` centred horizontally around `center_x`, top edge at `top_y`."""
    w = draw.textlength(text, font=font)
    x = center_x - (w / 2)
    draw.text((x, top_y), text, font=font, fill=fill)


def _format_date(date_str: Optional[str]) -> str:
    if date_str:
        # Accept ISO-ish strings; fall back to raw string.
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%B %-d, %Y")
        except Exception:  # noqa: BLE001
            return date_str
    return datetime.utcnow().strftime("%B %-d, %Y")


def _render(name: str, date_str: Optional[str]) -> Image.Image:
    if not os.path.exists(_TEMPLATE_PATH):
        raise FileNotFoundError(f"Certificate template missing at {_TEMPLATE_PATH}")

    display_name = (name or "").strip() or "Committed Co-Parent"
    display_date = _format_date(date_str)

    img = Image.open(_TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Mask out the baked-in placeholder text so we can drop the real values in.
    draw.rectangle(_NAME_MASK, fill=_PAPER)
    draw.rectangle(_DATE_MASK, fill=_PAPER)

    name_font = _fit_name_font(draw, display_name)
    # Great Vibes needs a small optical lift because of its long descenders.
    name_top = _NAME_BASELINE_Y - int(name_font.size * 0.85)
    _draw_centered(draw, display_name, _NAME_CENTER_X, name_top, name_font, _TEAL)

    date_font = _load_font(_SERIF_FONT, _DATE_FONT_SIZE)
    date_top = _DATE_BASELINE_Y - int(_DATE_FONT_SIZE * 1.1)
    _draw_centered(draw, display_date, _DATE_CENTER_X, date_top, date_font, _NAVY)

    return img


def build_certificate_png(name: str, date_str: Optional[str] = None) -> bytes:
    img = _render(name, date_str)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_certificate_pdf(name: str, date_str: Optional[str] = None) -> bytes:
    img = _render(name, date_str)
    buf = BytesIO()
    # Landscape US Letter feel — save the composed image directly as PDF.
    img.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()
