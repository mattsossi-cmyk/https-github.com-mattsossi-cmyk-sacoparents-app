"""Court-ready PDF report for the Neurodivergent Coparenting Risk
Assessment. Formal cover, methodology brief, score card, marked 4×4
heatmap, required-interventions checklist, disclaimer footer, and
optional signature block (with the tamper-evident verify-QR wired up
in iter72)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fpdf import FPDF

from pdf_base import LOGO_PATH, _safe, _section_break, render_pdf_copyright
from pdf_watermark import stamp_watermark, stamp_signature_line

TIER_COLORS: Dict[str, tuple] = {
    "low":      (31, 92, 59),
    "medium":   (170, 116, 40),
    "high":     (176, 42, 42),
    "critical": (110, 22, 22),
}


class _NDPdf(FPDF):
    def header(self):
        if getattr(self, "_first_page", True):
            self._first_page = False
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(133, 126, 156)
        self.set_xy(self.l_margin, 8)
        self.cell(0, 3.6, _safe("Neurodivergent Coparenting Risk Assessment"), ln=1)

    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(133, 126, 156)
        self.cell(0, 3, _safe(
            "Informational and preparation support only. Not legal advice, "
            "medical diagnosis, or a substitute for a licensed professional."
        ), align="C")
        self.set_xy(self.l_margin, -8)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 3, _safe("SA CoParents App · sacoparentsapp.online"), align="C")
        stamp_watermark(self)
        stamp_signature_line(self)


        render_pdf_copyright(self)
def _tier_pill(pdf: _NDPdf, label: str, tier: str) -> None:
    color = TIER_COLORS.get(tier, (61, 26, 120))
    pdf.set_fill_color(*color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, _safe(label), align="C", fill=True, ln=1)
    pdf.set_text_color(30, 24, 54)


def _draw_heatmap(pdf: _NDPdf, threat: int, vuln: int) -> None:
    """4×4 grid, rows are Threat (1 top → 4 bottom), cols are Vulnerability
    (1 left → 4 right). The parent's cell is filled with the tier
    colour; other cells are shaded by product value."""
    origin_x = pdf.l_margin + 20
    origin_y = pdf.get_y() + 4
    cell = 12.0

    # Axis labels
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(133, 126, 156)
    pdf.set_xy(origin_x, origin_y - 5)
    pdf.cell(cell * 4, 4, _safe("VULNERABILITY  (1 low → 4 high)"), align="C")
    # Left axis: vertical label written cell by cell
    for r in range(4):
        pdf.set_xy(origin_x - 18, origin_y + r * cell + cell / 2 - 2)
        pdf.cell(15, 4, _safe(f"Threat {r + 1}"), align="R")

    # Cells
    for r in range(4):
        for c in range(4):
            t_val, v_val = r + 1, c + 1
            product = t_val * v_val
            is_case = (t_val == threat and v_val == vuln)
            if is_case:
                if product <= 3:    color = TIER_COLORS["low"]
                elif product <= 8:  color = TIER_COLORS["medium"]
                elif product <= 12: color = TIER_COLORS["high"]
                else:               color = TIER_COLORS["critical"]
            else:
                # Gradient from cream (1) → deep purple (16) so the map
                # still communicates severity even without a case marker.
                intensity = product / 16.0
                r_ch = int(250 - intensity * 90)
                g_ch = int(245 - intensity * 130)
                b_ch = int(248 - intensity * 60)
                color = (r_ch, g_ch, b_ch)
            pdf.set_fill_color(*color)
            pdf.set_draw_color(220, 214, 232)
            pdf.rect(origin_x + c * cell, origin_y + r * cell, cell, cell, style="FD")
            pdf.set_text_color(*(255, 255, 255) if is_case else (110, 100, 130))
            pdf.set_font("Helvetica", "B" if is_case else "", 8)
            pdf.set_xy(origin_x + c * cell, origin_y + r * cell + cell / 2 - 2)
            pdf.cell(cell, 4, _safe(str(product)), align="C")
    pdf.set_text_color(30, 24, 54)
    pdf.set_y(origin_y + 4 * cell + 6)


from court_report_disclaimer import draw_court_report_disclaimer

def build_nd_risk_pdf(
    *,
    assessment: Dict[str, Any],
    signed_by: Optional[str] = None,
    signed_at: Optional[str] = None,
    signed_note: Optional[str] = None,
) -> bytes:
    """Render the full court-ready PDF for a single ND Risk assessment."""
    pdf = _NDPdf(orientation="P", unit="mm", format="Letter")
    pdf._first_page = True
    if signed_by:  pdf._signed_by = signed_by
    if signed_at:  pdf._signed_at = signed_at
    if signed_note: pdf._signed_note = signed_note

    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=18, top=20, right=18)
    pdf.add_page()

    # ---- Cover -----------------------------------------------------------
    try:
        pdf.image(LOGO_PATH, x=pdf.l_margin, y=pdf.get_y(), w=22)
    except Exception:  # noqa: BLE001
        pass
    pdf.set_y(pdf.get_y() + 24)

    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(133, 126, 156)
    pdf.cell(0, 3.6, _safe("SA COPARENTS APP · PROFESSIONAL INFORMATIONAL REPORT"), ln=1)
    pdf.set_font("Helvetica", "B", 22); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(0, 10, _safe("Neurodivergent Coparenting Risk Assessment"))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        "This report documents a structured, self-administered risk assessment "
        "of coparenting communication dynamics, filtered through a neurodivergent "
        "vulnerability lens. It is intended to support mediation, family court, "
        "or clinical discussions — not to substitute for them."
    ))
    pdf.ln(3)

    scoring = assessment.get("scoring") or {}
    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.cell(45, 5, _safe("Target parent"))
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _safe(assessment.get("target_name") or "—"), ln=1)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(45, 5, _safe("Named coparent"))
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _safe(assessment.get("coparent_name") or "—"), ln=1)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(45, 5, _safe("Assessed on"))
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _safe(assessment.get("created_at", "")[:10]), ln=1)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(45, 5, _safe("Assessment ID"))
    pdf.set_font("Courier", "", 9)
    pdf.cell(0, 5, _safe(assessment.get("assessment_id", "")), ln=1)

    _section_break(pdf)

    # Court-report disclaimer — six caveats a mediator or judge should
    # see before reading the tier + heatmap. Introduced 2026-03-06 per
    # product review. Uses the target parent's name when available.
    draw_court_report_disclaimer(
        pdf,
        author_name=assessment.get("target_name") or None,
        both_parents=False,
    )
    _section_break(pdf)

    # ---- Overall tier ----------------------------------------------------
    pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Overall risk tier"), ln=1)
    _tier_pill(pdf,
               f"{scoring.get('tier_label', '?')} · Total score {scoring.get('total_score', '?')} / 16",
               scoring.get("tier", "low"))
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        f"Threat axis score: {scoring.get('threat_score', '?')} / 4    ·    "
        f"Vulnerability axis score: {scoring.get('vulnerability_score', '?')} / 4    ·    "
        "Total is the product of the two axis scores."
    ))
    pdf.ln(2)

    # ---- Heatmap ---------------------------------------------------------
    pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
    pdf.cell(0, 5, _safe("Risk matrix — this case is highlighted"), ln=1)
    _draw_heatmap(pdf,
                  int(scoring.get("threat_score", 1)),
                  int(scoring.get("vulnerability_score", 1)))
    pdf.set_font("Helvetica", "", 8); pdf.set_text_color(133, 126, 156)
    pdf.multi_cell(0, 4, _safe(
        "Cells 1-3: Low  ·  4-8: Medium  ·  9-12: High  ·  13-16: Critical."
    ))
    _section_break(pdf)

    # ---- Sub-scores ------------------------------------------------------
    from nd_risk_routes import THREAT_DIMENSIONS, VULNERABILITY_DIMENSIONS
    sub = scoring.get("sub_scores") or {}
    for title, dims, key in (
        ("Threat axis — coparent's behaviour",       THREAT_DIMENSIONS,        "threat"),
        ("Vulnerability axis — target parent's state", VULNERABILITY_DIMENSIONS, "vulnerability"),
    ):
        pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
        pdf.cell(0, 5, _safe(title), ln=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 69, 103)
        for k, label, hint in dims:
            v = (sub.get(key) or {}).get(k, "—")
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 9); pdf.cell(6, 4.5, _safe(str(v)))
            pdf.set_font("Helvetica", "", 9); pdf.cell(0, 4.5, _safe(f"/ 4  {label}"), ln=1)
            pdf.set_x(pdf.l_margin + 6)
            pdf.set_font("Helvetica", "I", 8.5); pdf.set_text_color(133, 126, 156)
            pdf.multi_cell(pdf.epw - 6, 4, _safe(hint))
            pdf.set_text_color(75, 69, 103)
            pdf.ln(0.5)
        pdf.ln(1)
    _section_break(pdf)

    # ---- Required interventions ----------------------------------------
    pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Required interventions"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    for item in (scoring.get("interventions") or []):
        pdf.set_x(pdf.l_margin)
        pdf.cell(5, 4.5, _safe("[ ]"))
        pdf.multi_cell(0, 4.5, _safe(item))
        pdf.ln(0.5)

    # ---- Optional notes -------------------------------------------------
    notes = (assessment.get("notes") or "").strip()
    if notes:
        _section_break(pdf)
        pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
        pdf.cell(0, 5, _safe("Target parent notes"), ln=1)
        pdf.set_font("Helvetica", "I", 9); pdf.set_text_color(75, 69, 103)
        pdf.multi_cell(0, 4.5, _safe(notes))

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
