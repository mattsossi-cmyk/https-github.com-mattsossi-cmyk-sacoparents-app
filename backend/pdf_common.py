"""Shared PDF primitives (fonts, brand colours, text sanitising, page factory) used by every PDF builder."""
from pathlib import Path

from fpdf import FPDF

_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_UNICODE_FONTS = all((_FONT_DIR / f).exists() for f in (
    "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf",
))
FONT = "dejavu" if _UNICODE_FONTS else "helvetica"

PURPLE = (91, 42, 134)
TEAL = (37, 161, 154)
GRAY = (110, 100, 120)
GREEN = (102, 139, 105)
BLUE = (96, 150, 186)
YELLOW = (180, 150, 60)
DARK = (30, 25, 40)
BODY = (60, 55, 70)

_REPLACEMENTS = [
    ("—", "-"), ("–", "-"), ("'", "'"), ("'", "'"),
    ('"', '"'), ('"', '"'), ("…", "..."), ("✓", "[x]"), ("•", "-"), ("≠", "!="),
]


def _s(text) -> str:
    if _UNICODE_FONTS:
        return str(text)
    t = str(text)
    for a, b in _REPLACEMENTS:
        t = t.replace(a, b)
    return t.encode("latin-1", "replace").decode("latin-1")


class _JointPDF(FPDF):
    watermark_text: str | None = None
    footer_meta: str = ""
    brand_header_fn = None

    def header(self):
        if self.brand_header_fn:
            self.brand_header_fn(self)

    def footer(self):
        if self.watermark_text:
            self.set_font(FONT, "B", 52)
            self.set_text_color(235, 230, 242)
            with self.rotation(40, self.w / 2, self.h / 2):
                self.text(self.w / 2 - 68, self.h / 2, self.watermark_text)
        self.set_y(-18 if self.footer_meta else -14)
        self.set_font(FONT, "I", 8)
        self.set_text_color(*GRAY)
        if self.footer_meta:
            self.cell(0, 4, _s(self.footer_meta), align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, _s(f"© 2026 sacoparentsalign.com · SA CoParents Align. All rights reserved. · Page {self.page_no()}"), align="C")


def _new_pdf() -> FPDF:
    pdf = _JointPDF()
    if _UNICODE_FONTS:
        pdf.add_font("dejavu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        pdf.add_font("dejavu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        pdf.add_font("dejavu", "I", str(_FONT_DIR / "DejaVuSans-Oblique.ttf"))
        pdf.add_font("dejavu", "BI", str(_FONT_DIR / "DejaVuSans-BoldOblique.ttf"))
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_author("SA CoParents Align · sacoparentsalign.com")
    pdf.set_creator("sacoparentsalign.com")
    pdf.set_subject("© 2026 sacoparentsalign.com · SA CoParents Align. All rights reserved.")
    pdf.add_page()
    return pdf
