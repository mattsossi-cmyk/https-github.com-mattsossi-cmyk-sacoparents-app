"""Dispute Resolution Pathway Report — professional PDF export.

Renders the same content as the on-screen report at `/pathway-report`,
using the shared visual system from `four_dimension_briefing_pdf.py`
(brand colors, helper widgets, `_safe` text sanitiser). Layout, in
order:

    1. Cover — eyebrow + hero + subhead + generation timestamp
    2. Primary pathway card — pill + one-liner + safety hard-lock panel
       if applicable
    3. Factors supporting this pathway
    4. Goals before or during this process
    5. Process suitability profile — table
    6. Considerations
    7. Data inputs used
    8. Legal / clinical disclaimer footer

Same language guardrails as the algorithm: never says "you should",
always "the combined assessment data indicates". Safety hard-locks
are surfaced prominently — red banner immediately after the primary
pathway.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fpdf import FPDF

from pdf_base import _safe, _section_break


# ---- Brand colours (mirror the briefing PDF) ---------------------------------
BRAND_PURPLE = (61, 26, 120)
BRAND_TEAL   = (45, 181, 181)
INK          = (26, 19, 48)
MID_INK      = (75, 69, 103)
SOFT_INK     = (133, 126, 156)
CARD_BORDER  = (214, 207, 232)
CARD_BG      = (250, 248, 254)
DANGER       = (176, 42, 42)
DANGER_BG    = (252, 237, 235)
DANGER_LINE  = (239, 180, 180)


# ---- Suitability chip colours (mirror the on-screen `LEVEL_META`) ------------
_LEVEL_COLOR = {
    "high":          {"bg": (241, 249, 244), "border": (181, 223, 197), "text": (31, 92, 59)},
    "moderate":      {"bg": (255, 249, 235), "border": (228, 216, 184), "text": (138, 107, 18)},
    "low":           {"bg": DANGER_BG,       "border": DANGER_LINE,     "text": DANGER},
    "not_indicated": {"bg": (241, 238, 247), "border": CARD_BORDER,     "text": MID_INK},
}
_LEVEL_LABEL = {
    "high":          "High suitability",
    "moderate":      "Moderate suitability",
    "low":           "Low suitability",
    "not_indicated": "Not indicated at this time",
}


def _stamp_pathway_verify_qr(pdf: Any) -> None:
    """Stamp a small verify QR in the footer left margin.

    Mirrors `_stamp_briefing_verify_qr` in four_dimension_briefing_pdf.py.
    Points at the public /verify/pathway/{sig_id} page. Non-fatal — the
    PDF must still render if qrcode isn't installed for any reason.
    """
    sig_id = getattr(pdf, "_pathway_sig_id", None)
    verify_url = getattr(pdf, "_pathway_verify_url", None)
    if not sig_id or not verify_url:
        return

    prev_font_family = pdf.font_family
    prev_font_style = pdf.font_style
    prev_font_size = pdf.font_size_pt

    try:
        import io
        import qrcode

        img = qrcode.make(verify_url, box_size=8, border=1)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        qr_size = 12.0
        qr_x = pdf.l_margin
        qr_y = (pdf.h - 6.0) - qr_size - 1.5

        pdf.image(buf, x=qr_x, y=qr_y, w=qr_size, h=qr_size)
        pdf.set_font("Helvetica", "", 5.6)
        pdf.set_text_color(*SOFT_INK)
        pdf.set_xy(qr_x - 6, qr_y + qr_size + 0.2)
        pdf.cell(qr_size + 12, 2.6, _safe("Scan to verify"), align="C")
    except Exception:  # noqa: BLE001
        # Non-fatal — QR is a nice-to-have, PDF must still render.
        pass
    finally:
        if prev_font_family:
            pdf.set_font(prev_font_family, prev_font_style or "", prev_font_size or 10)
        pdf.set_text_color(0, 0, 0)


class _PathwayPDF(FPDF):
    def header(self):
        if getattr(self, "_first_page", True):
            self._first_page = False
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*SOFT_INK)
        self.set_xy(self.l_margin, 8)
        self.cell(0, 3.6, _safe("Dispute Resolution Pathway Report"), ln=1)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*SOFT_INK)
        self.cell(0, 3, _safe(
            "Informational summary. Not legal advice, a psychological determination, "
            "or a substitute for a qualified professional's own assessment."
        ), align="C")
        self.set_xy(self.l_margin, -8)
        self.set_font("Helvetica", "", 7)
        self.cell(
            0, 3,
            _safe(f"SA CoParents App - sacoparentsapp.online - Page {self.page_no()}"),
            align="C",
        )
        _stamp_pathway_verify_qr(self)


# ---- Reusable low-level widgets ----------------------------------------------

def _eyebrow(pdf: _PathwayPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*BRAND_PURPLE)
    pdf.cell(0, 4, _safe(text.upper()), ln=1)
    pdf.set_text_color(*INK)


def _hero(pdf: _PathwayPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 9, _safe(text))
    pdf.ln(1)


def _paragraph(pdf: _PathwayPDF, text: str, *, size: float = 10.5,
               color: tuple = MID_INK, italic: bool = False) -> None:
    style = "I" if italic else ""
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5.2, _safe(text))
    pdf.ln(1)


def _bullet_list(pdf: _PathwayPDF, items: List[str], *,
                 size: float = 10.5, color: tuple = INK) -> None:
    if not items:
        return
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*color)
    for it in items:
        # Bullet + hanging indent.
        pdf.set_x(pdf.l_margin + 3)
        pdf.cell(4, 5.2, "-")
        pdf.multi_cell(0, 5.2, _safe(it))
    pdf.ln(1)


def _section_heading(pdf: _PathwayPDF, text: str) -> None:
    _section_break(pdf)
    _eyebrow(pdf, text)
    pdf.ln(1)


def _card(pdf: _PathwayPDF, *, border: tuple, bg: tuple, pad: float = 4.0) -> float:
    """Draw a card background at the current Y, returning the top-y so
    the caller can position content. Height must be computed by caller."""
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*border)
    return pdf.get_y()


def _draw_primary_card(
    pdf: _PathwayPDF, *, label: str, one_liner: str, hard_locked: bool,
) -> None:
    """Coloured card showing the primary pathway."""
    border = DANGER_LINE if hard_locked else CARD_BORDER
    bg     = DANGER_BG   if hard_locked else CARD_BG

    top = pdf.get_y()
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*border)
    # Reserve height, filled retroactively — fpdf2 doesn't give us
    # variable-height rectangles without measuring, so we use rect+text.
    pdf.rect(pdf.l_margin, top, pdf.epw, 24, style="DF")

    pdf.set_xy(pdf.l_margin + 4, top + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*(DANGER if hard_locked else BRAND_PURPLE))
    pdf.cell(0, 4, _safe("PRIMARY PATHWAY"), ln=1)

    pdf.set_xy(pdf.l_margin + 4, top + 8)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.epw - 8, 6, _safe(label))

    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*MID_INK)
    pdf.multi_cell(pdf.epw - 8, 4.5, _safe(one_liner))
    pdf.ln(2)


def _draw_hard_lock_panel(pdf: _PathwayPDF, reasons: List[str]) -> None:
    if not reasons:
        return
    top = pdf.get_y()
    pdf.set_fill_color(*DANGER_BG)
    pdf.set_draw_color(*DANGER_LINE)
    # Compute height ~ 6mm eyebrow + 5mm per reason + 4mm padding.
    height = 12 + 5.5 * len(reasons) + 10
    pdf.rect(pdf.l_margin, top, pdf.epw, height, style="DF")
    pdf.set_xy(pdf.l_margin + 4, top + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*DANGER)
    pdf.cell(0, 4, _safe("SAFETY TRIGGER APPLIED"), ln=1)
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*DANGER)
    for r in reasons:
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(pdf.epw - 8, 5, _safe(f"- {r}"))
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MID_INK)
    pdf.multi_cell(pdf.epw - 8, 4.5, _safe(
        "This app never recommends mediation or a consensual process when the "
        "assessment data shows a safety trigger. A qualified family-violence "
        "advocate, forensic psychologist, or family-law attorney should be "
        "consulted before any further step is taken."
    ))
    pdf.set_y(top + height + 2)


def _draw_suitability_table(pdf: _PathwayPDF, rows: List[Dict[str, Any]]) -> None:
    """Small table: pathway label | rated chip."""
    pdf.set_font("Helvetica", "", 10)
    for row in rows:
        level = row.get("suitability") or "not_indicated"
        color = _LEVEL_COLOR.get(level, _LEVEL_COLOR["not_indicated"])
        chip_label = _LEVEL_LABEL.get(level, level)

        y0 = pdf.get_y()
        # Left column — pathway label.
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(pdf.epw * 0.55, 7, _safe(row.get("label") or ""))

        # Right column — chip.
        chip_w = pdf.epw * 0.45
        chip_x = pdf.l_margin + pdf.epw - chip_w
        pdf.set_xy(chip_x, y0 + 0.5)
        pdf.set_fill_color(*color["bg"])
        pdf.set_draw_color(*color["border"])
        pdf.set_text_color(*color["text"])
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(chip_w, 6, _safe(chip_label), align="C", fill=True, border=1, ln=1)
        pdf.ln(0.5)


# ---- Public entry point ------------------------------------------------------

def build_pathway_report_pdf(
    *,
    result: Dict[str, Any],
    caller_display_name: str = "",
    data_inputs_present: Optional[Dict[str, bool]] = None,
    share_id: Optional[str] = None,
    pathway_sig_id: Optional[str] = None,
    pathway_verify_url: Optional[str] = None,
) -> bytes:
    """Return PDF bytes for a pathway result payload — the same shape the
    JSON endpoints return via `PathwayResult.to_public_dict()`."""
    pdf = _PathwayPDF(orientation="P", unit="mm", format="Letter")
    pdf._first_page = True
    if pathway_sig_id:     pdf._pathway_sig_id = pathway_sig_id
    if pathway_verify_url: pdf._pathway_verify_url = pathway_verify_url
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=18, top=18, right=18)
    pdf.add_page()

    # ---- 1. Cover ----------------------------------------------------------
    _eyebrow(pdf, "Dispute Resolution Pathway Report")
    _hero(pdf, "Primary pathway for professional consideration")

    subhead_parts = []
    if result.get("is_dual_party"):
        subhead_parts.append("Two-parent report — both parents have consented via the Compare share.")
    else:
        subhead_parts.append("Single-parent preview — the full professional report requires the co-parent's data as well.")
    subhead_parts.append("The recommendation below is generated from a deterministic rule engine over both parents' assessment data, not by an AI model.")
    _paragraph(pdf, " ".join(subhead_parts), size=9.5, italic=True)

    meta_lines = []
    if caller_display_name:
        meta_lines.append(f"Requested by: {caller_display_name}")
    if share_id:
        meta_lines.append(f"Compare share ID: {share_id}")
    if result.get("generated_at"):
        meta_lines.append(f"Generated (UTC): {result['generated_at'][:19].replace('T', ' ')}")
    if meta_lines:
        _paragraph(pdf, " | ".join(meta_lines), size=8.5, color=SOFT_INK, italic=True)

    # ---- 2. Primary pathway card ------------------------------------------
    pdf.ln(2)
    _draw_primary_card(
        pdf,
        label=result.get("primary_pathway_label", "Unknown"),
        one_liner=result.get("primary_pathway_summary", ""),
        hard_locked=bool(result.get("hard_locked_by")),
    )
    _draw_hard_lock_panel(pdf, list(result.get("hard_locked_by") or []))

    # ---- 3. Factors --------------------------------------------------------
    _section_heading(pdf, "Factors supporting this pathway")
    _bullet_list(pdf, list(result.get("factors_supporting_primary") or []))

    # ---- 4. Goals ----------------------------------------------------------
    _section_heading(pdf, "Goals before or during this process")
    _bullet_list(pdf, list(result.get("goals_before_or_during") or []))

    # ---- 5. Suitability profile -------------------------------------------
    _section_heading(pdf, "Process suitability profile")
    _draw_suitability_table(pdf, list(result.get("suitability_profile") or []))

    # ---- 6. Considerations -------------------------------------------------
    _section_heading(pdf, "Considerations")
    _bullet_list(pdf, list(result.get("considerations") or []),
                 size=9.5, color=MID_INK)

    # ---- 7. Data inputs ----------------------------------------------------
    if data_inputs_present:
        _section_heading(pdf, "Data inputs used")
        pretty = {
            "safety_screen":       "Safety Screen",
            "dimension_companion": "Dimension Companion (Dims 2, 3, 4)",
            "nd_risk":             "ND Risk Assessment",
            "compliance":          "Intervention Compliance Log",
        }
        rows = [
            f"{pretty.get(k, k)}: {'present' if v else 'not on file'}"
            for k, v in data_inputs_present.items()
        ]
        _bullet_list(pdf, rows, size=9.5)

    # ---- 8. Legal disclaimer ---------------------------------------------
    _section_heading(pdf, "Not legal advice")
    _paragraph(pdf,
        "This report is a summary of self-reported data intended to help a "
        "qualified professional (mediator, family-law attorney, therapist, or "
        "advocate) frame their own assessment. It is not a psychological "
        "determination, a legal opinion, or a substitute for a mediator's own "
        "screening. If either parent's circumstances change - a safety "
        "incident, a change in mental-health status, a new family-violence "
        "concern - this report should be re-generated.",
        size=9.5, italic=True, color=MID_INK,
    )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1", errors="replace")
    return bytes(out)
