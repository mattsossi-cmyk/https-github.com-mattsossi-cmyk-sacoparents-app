"""Combined Four-Dimension Briefing — single PDF that stitches together
the parent's latest Safety Assessment (Dim 1) with their latest Dimension
Companion Assessment (Dim 2 / 3 / 4).

Designed to be handed to a mediator, parent facilitator ad litem, or
trial court as a single unified briefing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fpdf import FPDF

from pdf_base import LOGO_PATH, _safe, _section_break, render_pdf_copyright
from pdf_watermark import stamp_watermark, stamp_signature_line


# ---------------------------------------------------------------------------
# Briefing-level verify QR — stamped in the footer of every page, bottom-left.
# Distinct from the signature-line QR (bottom-right) so both can coexist on
# a signed briefing. Points to a public "Was this briefing issued by SA
# CoParents?" verify page.
# ---------------------------------------------------------------------------

def _stamp_briefing_verify_qr(pdf: Any) -> None:
    sig_id = getattr(pdf, "_briefing_sig_id", None)
    verify_url = getattr(pdf, "_briefing_verify_url", None)
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

        # 12x12mm QR anchored inside the LEFT margin, aligned with the
        # signature baseline. Micro-label underneath tells the reader
        # this is the "issued by" stamp rather than the signature QR.
        qr_size = 12.0
        qr_x = pdf.l_margin
        qr_y = (pdf.h - 6.0) - qr_size - 1.5

        pdf.image(buf, x=qr_x, y=qr_y, w=qr_size, h=qr_size)
        pdf.set_font("Helvetica", "", 5.6)
        pdf.set_text_color(133, 126, 156)
        pdf.set_xy(qr_x - 6, qr_y + qr_size + 0.2)
        pdf.cell(qr_size + 12, 2.6, _safe("Scan to verify"), align="C")
    except Exception:  # noqa: BLE001
        # Non-fatal — QR is a nice-to-have, PDF must still render.
        pass
    finally:
        if prev_font_family:
            pdf.set_font(prev_font_family, prev_font_style or "", prev_font_size or 10)
        pdf.set_text_color(0, 0, 0)


# -----------------------------------------------------------------------------
# Colour palette shared by all four dimensions.
# -----------------------------------------------------------------------------

# Safety pathway (Dim 1) — colour keyed by level (1 = deepest concern, 4 = safest).
SAFETY_LEVEL_COLORS: Dict[int, tuple] = {
    1: (110, 22, 22),   # deep red
    2: (176, 42, 42),   # red
    3: (170, 116, 40),  # amber
    4: (31, 92, 59),    # green
}

# Companion tiers (Dim 2 / 3 / 4).
COMPANION_TIER_COLORS: Dict[str, tuple] = {
    "strong":    (31, 92, 59),
    "steady":    (45, 122, 74),
    "stretched": (170, 116, 40),
    "strained":  (176, 42, 42),
}


class _BriefingPDF(FPDF):
    def header(self):
        if getattr(self, "_first_page", True):
            self._first_page = False
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(133, 126, 156)
        self.set_xy(self.l_margin, 8)
        self.cell(0, 3.6, _safe("Four-Dimension Co-Parenting Briefing"), ln=1)

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
        self.cell(
            0, 3,
            _safe(f"SA CoParents App - sacoparentsapp.online - Page {self.page_no()}"),
            align="C",
        )
        stamp_watermark(self)
        _stamp_briefing_verify_qr(self)
        stamp_signature_line(self)


        render_pdf_copyright(self)
def _pill(pdf: _BriefingPDF, label: str, rgb: tuple, *, height: float = 6, width: float = 0) -> None:
    pdf.set_fill_color(*rgb)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(width, height, _safe(label), align="C", fill=True, ln=1)
    pdf.set_text_color(30, 24, 54)


def _kv(pdf: _BriefingPDF, key: str, value: str, *, key_w: float = 45) -> None:
    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.cell(key_w, 5, _safe(key))
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _safe(value or "-"), ln=1)


def _dimension_gauge_bar(pdf: _BriefingPDF, concern_score: float, tier: str) -> None:
    """1..5 concern bar. Lower is better."""
    total_w = pdf.epw - 40
    x = pdf.l_margin
    y = pdf.get_y()
    pdf.set_fill_color(240, 238, 248)
    pdf.rect(x, y, total_w, 3, style="F")
    pct = max(0.05, min(1.0, (concern_score - 1) / 4))
    color = COMPANION_TIER_COLORS.get(tier, (61, 26, 120))
    pdf.set_fill_color(*color)
    pdf.rect(x, y, total_w * pct, 3, style="F")
    pdf.set_y(y + 4)
    pdf.set_font("Helvetica", "", 8); pdf.set_text_color(133, 126, 156)
    pdf.cell(0, 4, _safe(f"Concern level {concern_score:.2f} / 5 (lower is better)"), ln=1)
    pdf.set_text_color(30, 24, 54)


def _executive_summary_row(
    pdf: _BriefingPDF,
    label: str,
    tier_label: str,
    tier_color: tuple,
    note: str,
) -> None:
    """One row in the at-a-glance table on the cover page."""
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    pdf.set_draw_color(220, 214, 232); pdf.set_line_width(0.2)
    pdf.rect(x0, y0, pdf.epw, 14)

    # Left: dimension label
    pdf.set_xy(x0 + 3, y0 + 2)
    pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(30, 24, 54)
    pdf.cell(60, 4, _safe(label))
    pdf.set_xy(x0 + 3, y0 + 6.5)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(60, 3.8, _safe(note))

    # Right: tier pill
    pill_w = 40
    pdf.set_xy(x0 + pdf.epw - pill_w - 3, y0 + 4)
    pdf.set_fill_color(*tier_color); pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(pill_w, 6, _safe(tier_label), align="C", fill=True)
    pdf.set_text_color(30, 24, 54)

    pdf.set_y(y0 + 15)


def build_four_dimension_briefing_pdf(
    *,
    parent_name: str,
    audience: str,
    safety_doc: Optional[Dict[str, Any]],
    companion_doc: Optional[Dict[str, Any]],
    compliance: Optional[Dict[str, Any]] = None,
    generated_at: str,
    signed_by: Optional[str] = None,
    signed_at: Optional[str] = None,
    signed_note: Optional[str] = None,
    briefing_sig_id: Optional[str] = None,
    briefing_verify_url: Optional[str] = None,
) -> bytes:
    pdf = _BriefingPDF(orientation="P", unit="mm", format="Letter")
    pdf._first_page = True
    if signed_by:   pdf._signed_by = signed_by
    if signed_at:   pdf._signed_at = signed_at
    if signed_note: pdf._signed_note = signed_note
    if briefing_sig_id:      pdf._briefing_sig_id = briefing_sig_id
    if briefing_verify_url:  pdf._briefing_verify_url = briefing_verify_url

    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=18, top=20, right=18)
    pdf.add_page()

    # ---------------- Cover ----------------
    try:
        pdf.image(LOGO_PATH, x=pdf.l_margin, y=pdf.get_y(), w=22)
    except Exception:
        pass
    pdf.set_y(pdf.get_y() + 24)

    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(133, 126, 156)
    pdf.cell(0, 3.6, _safe("SA COPARENTS APP - PROFESSIONAL INFORMATIONAL BRIEFING"), ln=1)
    pdf.set_font("Helvetica", "B", 22); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(0, 10, _safe("Four-Dimension Co-Parenting Briefing"))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        "This briefing consolidates the parent's most recent Safety Assessment "
        "(Dimension 1) with the Companion Assessment (Dimensions 2, 3 & 4) into a "
        "single document. It is intended to support mediation, parent facilitators "
        "ad litem, or the trial court in understanding the whole picture at a glance."
    ))
    pdf.ln(3)

    _kv(pdf, "Prepared for",  audience or "Mediator / Facilitator / Court")
    _kv(pdf, "Parent",        parent_name or "-")
    _kv(pdf, "Generated on",  generated_at[:19].replace("T", " "))
    if briefing_sig_id:
        _kv(pdf, "Briefing ID", briefing_sig_id)

    _section_break(pdf)

    # ---------------- Executive summary ----------------
    pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Executive summary - four dimensions at a glance"), ln=1)
    pdf.ln(1)

    # Dim 1 (Safety)
    if safety_doc:
        r = (safety_doc.get("result") or {})
        lvl  = int(r.get("level") or 4)
        pway = r.get("pathway_title") or "-"
        note = r.get("pathway_headline") or r.get("pathway_summary") or ""
        _executive_summary_row(
            pdf, "Dim 1 - Safety",
            f"Level {lvl} - {pway}",
            SAFETY_LEVEL_COLORS.get(lvl, (61, 26, 120)),
            note[:110],
        )
    else:
        _executive_summary_row(pdf, "Dim 1 - Safety", "Not yet completed",
                               (133, 126, 156),
                               "Complete the Safety Assessment before relying on this briefing.")

    # Dim 2 / 3 / 4 (Companion)
    if companion_doc:
        dims = ((companion_doc.get("scoring") or {}).get("dimensions") or {})
        order = ["communication", "emotional_regulation", "executive_function"]
        labels = {
            "communication":        "Dim 2 - Communication",
            "emotional_regulation": "Dim 3 - Emotional regulation",
            "executive_function":   "Dim 4 - Executive function",
        }
        for k in order:
            d = dims.get(k) or {}
            tier = d.get("tier", "steady")
            _executive_summary_row(
                pdf, labels[k],
                f"{d.get('tier_label', '-')} - score {d.get('score', 0)} / 5",
                COMPANION_TIER_COLORS.get(tier, (61, 26, 120)),
                (d.get("summary") or "")[:110],
            )
    else:
        for lbl in ("Dim 2 - Communication", "Dim 3 - Emotional regulation", "Dim 4 - Executive function"):
            _executive_summary_row(pdf, lbl, "Not yet completed",
                                   (133, 126, 156),
                                   "Complete the Companion Assessment to populate this section.")

    # Follow-through row (compliance summary at a glance)
    if compliance and (compliance.get("current_week") or compliance.get("streak")):
        cw = compliance.get("current_week") or {}
        st = compliance.get("streak") or {}
        pct = cw.get("compliance_pct")
        total = cw.get("total") or 0
        followed = cw.get("followed") or 0
        cur = st.get("current_streak") or 0
        if pct is None:
            tier_label = "No data this week"
            row_color = (133, 126, 156)
        elif pct >= 80:
            tier_label = f"{pct:.0f}% - on track"
            row_color = (31, 92, 59)
        elif pct >= 50:
            tier_label = f"{pct:.0f}% - partial"
            row_color = (170, 116, 40)
        else:
            tier_label = f"{pct:.0f}% - lagging"
            row_color = (176, 42, 42)
        note = (
            f"{followed} of {total} interventions followed this week"
            + (f" - {cur} week streak" if cur else "")
        )
        _executive_summary_row(
            pdf, "Follow-through",
            tier_label,
            row_color,
            note[:110],
        )

    _section_break(pdf)

    # ---------------- Dimension 1 · Safety ----------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 7, _safe("Dimension 1 - Safety"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        "Family violence, coercive control, and communication safety. Scored "
        "independently first so a genuine safety concern is never diluted by "
        "communication-difference answers from the other three dimensions."
    ))
    pdf.ln(2)

    if not safety_doc:
        pdf.set_font("Helvetica", "I", 10); pdf.set_text_color(133, 126, 156)
        pdf.multi_cell(0, 5, _safe(
            "The parent has not yet completed the Safety Assessment. This section is "
            "left intentionally blank; it must not be assumed to be safe."
        ))
    else:
        r = safety_doc.get("result") or {}
        lvl = int(r.get("level") or 4)
        _pill(pdf,
              f"Level {lvl} - {r.get('pathway_title', '-')}",
              SAFETY_LEVEL_COLORS.get(lvl, (61, 26, 120)))
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
        pdf.cell(0, 5, _safe("Recommended communication pathway"), ln=1)
        pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
        pdf.multi_cell(0, 5, _safe(r.get("pathway_summary") or "-"))
        pdf.ln(2)

        recs: List[str] = list(r.get("recommendations") or [])
        if recs:
            pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
            pdf.cell(0, 5, _safe("Safety recommendations"), ln=1)
            pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
            for item in recs:
                pdf.set_x(pdf.l_margin)
                pdf.cell(5, 4.5, _safe("[ ]"))
                pdf.multi_cell(0, 4.5, _safe(item))
                pdf.ln(0.3)

        pdf.ln(1)
        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(133, 126, 156)
        assessed = (safety_doc.get("created_at") or "")[:10]
        pdf.cell(0, 4, _safe(
            f"Safety Assessment ID: {safety_doc.get('assessment_id', '-')} - assessed on {assessed}"
        ), ln=1)

    # ---------------- Dimensions 2 / 3 / 4 ----------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 7, _safe("Dimensions 2, 3 & 4 - Companion Assessment"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        "Communication, Emotional Regulation, and Executive Function are scored "
        "together after Safety has cleared. Each dimension is rated on a 1-5 concern "
        "scale (lower is better) and mapped to a tier: Strong / Steady / Stretched / Strained."
    ))
    pdf.ln(2)

    if not companion_doc:
        pdf.set_font("Helvetica", "I", 10); pdf.set_text_color(133, 126, 156)
        pdf.multi_cell(0, 5, _safe(
            "The parent has not yet completed the Companion Assessment for Dimensions "
            "2, 3 & 4. This section is left intentionally blank."
        ))
    else:
        scoring = companion_doc.get("scoring") or {}
        overall = scoring.get("overall_note") or ""
        if overall:
            pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
            pdf.cell(0, 5, _safe("Focus first on"), ln=1)
            pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
            pdf.multi_cell(0, 5, _safe(overall))
            pdf.ln(1)

        dims_scored = scoring.get("dimensions") or {}
        order = [
            ("communication",        "Dimension 2 - Communication"),
            ("emotional_regulation", "Dimension 3 - Emotional regulation"),
            ("executive_function",   "Dimension 4 - Executive function"),
        ]
        for key, heading in order:
            d = dims_scored.get(key) or {}
            if not d:
                continue
            _section_break(pdf)
            pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
            pdf.cell(0, 6, _safe(heading), ln=1)
            _pill(pdf,
                  f"{d.get('tier_label', '-')} - concern score {d.get('score', 0)} / 5",
                  COMPANION_TIER_COLORS.get(d.get("tier", "steady"), (61, 26, 120)))
            _dimension_gauge_bar(pdf, float(d.get("score") or 0), d.get("tier", "steady"))
            pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
            pdf.multi_cell(0, 4.8, _safe(d.get("summary") or ""))
            pdf.ln(1)

            interventions = list(d.get("interventions") or [])
            if interventions:
                pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(30, 24, 54)
                pdf.cell(0, 5, _safe("Recommended supports"), ln=1)
                pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
                for item in interventions:
                    pdf.set_x(pdf.l_margin)
                    pdf.cell(5, 4.5, _safe("[ ]"))
                    pdf.multi_cell(0, 4.5, _safe(item))
                    pdf.ln(0.3)

        pdf.ln(1)
        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(133, 126, 156)
        assessed = (companion_doc.get("created_at") or "")[:10]
        pdf.cell(0, 4, _safe(
            f"Companion Assessment ID: {companion_doc.get('assessment_id', '-')} - assessed on {assessed}"
        ), ln=1)

    # ---------------- Follow-Through (Compliance) ----------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 7, _safe("How this parent is following through"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        "Tier scores show where a parent stands. This section shows what they are "
        "actually doing about it: which enforced interventions they have ticked off "
        "this week, and whether they have sustained a compliance streak over time."
    ))
    pdf.ln(2)

    if not compliance or (not compliance.get("current_week") and not compliance.get("streak")):
        pdf.set_font("Helvetica", "I", 10); pdf.set_text_color(133, 126, 156)
        pdf.multi_cell(0, 5, _safe(
            "The parent has not yet logged any interventions this week. Follow-through "
            "cannot be evaluated from this briefing alone."
        ))
    else:
        cw = compliance.get("current_week") or {}
        st = compliance.get("streak") or {}

        # This week
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 6, _safe("This week"), ln=1)
        pct = cw.get("compliance_pct")
        total = cw.get("total") or 0
        followed = cw.get("followed") or 0
        wk = cw.get("week_start") or ""
        if pct is None:
            tone = (133, 126, 156)
            headline = "No log entries this week yet"
        elif pct >= 80:
            tone = (31, 92, 59);   headline = f"{pct:.0f}% - on track"
        elif pct >= 50:
            tone = (170, 116, 40); headline = f"{pct:.0f}% - partial follow-through"
        else:
            tone = (176, 42, 42);  headline = f"{pct:.0f}% - lagging follow-through"
        _pill(pdf, headline, tone)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
        pdf.multi_cell(0, 5, _safe(
            f"Week of {wk} (Mon-Sun, UTC): {followed} of {total} enforced interventions ticked."
        ))
        pdf.ln(1)

        # Streak + longest
        _section_break(pdf)
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 6, _safe("Compliance streak"), ln=1)
        cur = st.get("current_streak") or 0
        longest = st.get("longest_streak") or 0
        threshold = st.get("threshold_pct") or 80
        pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
        pdf.multi_cell(0, 5, _safe(
            f"Current streak: {cur} week(s) at >= {threshold:.0f}% compliance.  "
            f"Longest streak: {longest} week(s).  "
            "A streak is broken by any week below threshold or a silent week (no ticks)."
        ))
        pdf.ln(1)

        # Badges earned
        badges = st.get("badges") or []
        earned = [b for b in badges if b.get("earned")]
        if earned:
            pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
            pdf.cell(0, 5, _safe("Badges earned"), ln=1)
            pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
            for b in earned:
                pdf.set_x(pdf.l_margin)
                pdf.cell(5, 4.5, _safe("*"))
                pdf.multi_cell(0, 4.5, _safe(
                    f"{b.get('label', '-')}: {b.get('description', '')}"
                ))
                pdf.ln(0.3)
        else:
            pdf.set_font("Helvetica", "I", 9.5); pdf.set_text_color(133, 126, 156)
            pdf.multi_cell(0, 5, _safe(
                "No streak badges earned yet - the first badge unlocks at 4 consecutive weeks of >= 80% compliance."
            ))
            pdf.ln(1)

        # Next-badge progress
        nb = st.get("next_badge")
        if nb:
            pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(30, 24, 54)
            pdf.cell(0, 5, _safe("Working toward"), ln=1)
            pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
            pdf.multi_cell(0, 5, _safe(
                f"{nb.get('label', '-')} - {nb.get('weeks_to_go', '?')} week(s) to go "
                f"({nb.get('progress_pct', 0):.0f}% of the way there)."
            ))

    # ---------------- Advisory ----------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Important advisory"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(0, 5, _safe(
        "This briefing documents structured, self-administered assessments of "
        "co-parenting dynamics. It is intended to support mediators, parent "
        "facilitators ad litem, and trial courts in understanding the parent's "
        "self-reported situation. It is not a legal, psychological, or medical "
        "opinion, and does not diagnose family violence, determine legal rights, "
        "or predict future behaviour."
    ))
    pdf.ln(2)
    pdf.multi_cell(0, 5, _safe(
        "Consider consulting a qualified family law attorney to understand the "
        "parent's legal rights and available protections; a licensed therapist "
        "or domestic-violence professional experienced in intimate partner "
        "violence; and, if this parent is currently at risk, the National Domestic "
        "Violence Hotline at 1-800-799-7233."
    ))

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
