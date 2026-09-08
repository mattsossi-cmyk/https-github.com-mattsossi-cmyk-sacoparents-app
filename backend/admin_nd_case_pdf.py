"""Court-ready case history PDF for the admin drilldown drawer.

Aggregates the full ND Risk assessment history for a single parent
into a single professional PDF the coordinator can hand to a mediator
or judge without editing. Reuses the visual language of the
per-assessment `nd_risk_pdf.py` — same cover, same tier pill colours,
same disclaimer footer — but iterates every assessment newest-first
so the escalation arc is legible on one document.

Never leaks:
    * raw matrix answers (we only surface the derived sub-scores)
    * reviewer IP hashes
    * the parent's password / account metadata

Access is gated at the API layer (admin only). The PDF itself is
generated purely from data the admin drilldown endpoint already
returns, so there is no fresh path to protected data here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fpdf import FPDF

from pdf_base import LOGO_PATH, _safe, _section_break, render_pdf_copyright


TIER_COLORS = {
    "low":      (31, 92, 59),
    "medium":   (170, 116, 40),
    "high":     (176, 42, 42),
    "critical": (110, 22, 22),
}
TIER_LABELS = {
    "low":      "Low",
    "medium":   "Medium",
    "high":     "High",
    "critical": "Critical",
}


class _CasePdf(FPDF):
    def header(self):
        if getattr(self, "_first_page", True):
            self._first_page = False
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(133, 126, 156)
        self.set_xy(self.l_margin, 8)
        self.cell(0, 3.6, _safe("ND Risk Assessment · Case History"), ln=1)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(133, 126, 156)
        self.cell(0, 3, _safe(
            "Informational and preparation support only. Not legal advice, "
            "medical diagnosis, or a substitute for a licensed professional."
        ), align="C")
        self.set_xy(self.l_margin, -8)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 3, _safe(
            f"SA CoParents App · sacoparentsapp.online · Page {self.page_no()}"
        ), align="C")


        render_pdf_copyright(self)
def _tier_pill(pdf: _CasePdf, label: str, tier: str, *, width: float = 0.0) -> None:
    color = TIER_COLORS.get(tier, (61, 26, 120))
    pdf.set_fill_color(*color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(width or 0, 6, _safe(label), align="C", fill=True, ln=1 if not width else 0)
    pdf.set_text_color(30, 24, 54)


def _kv(pdf: _CasePdf, key: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.cell(45, 5, _safe(key))
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
    pdf.cell(0, 5, _safe(value), ln=1)


def _tier_distribution(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for r in rows:
        t = (r.get("tier") or "").lower()
        if t in out:
            out[t] += 1
    return out


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return iso[:10]
    except Exception:  # noqa: BLE001
        return iso


def build_admin_case_history_pdf(
    *,
    case: Dict[str, Any],
    admin_display_name: str = "",
) -> bytes:
    """Render the case history PDF.

    ``case`` is the payload returned by
    ``GET /api/admin/nd-risk-coordinator/case/{target_user_id}``:
        {target_user_id, target_name, assessment_count,
         history: [...], alerts: [...]}
    """
    pdf = _CasePdf(orientation="P", unit="mm", format="Letter")
    pdf._first_page = True
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
    pdf.cell(0, 3.6, _safe(
        "SA COPARENTS APP · ADMIN CASE HISTORY · CONFIDENTIAL"
    ), ln=1)
    pdf.set_font("Helvetica", "B", 22); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(0, 10, _safe("ND Risk · Case history report"))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(0, 5, _safe(
        "This document compiles every Neurodivergent Coparenting Risk "
        "Assessment on file for the target parent below. It is intended "
        "to support case coordination and professional review — not to "
        "substitute for clinical judgment."
    ))
    pdf.ln(3)

    history = list(case.get("history") or [])
    alerts = list(case.get("alerts") or [])
    latest = history[0] if history else {}
    dist = _tier_distribution(history)

    _kv(pdf, "Target parent", str(case.get("target_name") or "—"))
    _kv(pdf, "Target user ID",
        f"{case.get('target_user_id') or '—'}")
    _kv(pdf, "Assessments on file", str(case.get("assessment_count") or 0))
    _kv(pdf, "Most recent assessment", _fmt_date(latest.get("created_at", "")))
    _kv(pdf, "Report generated",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    if admin_display_name:
        _kv(pdf, "Generated by", admin_display_name)

    _section_break(pdf)

    # ---- Summary strip: most-recent tier + tier distribution ------------
    pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Case summary"), ln=1)

    if latest:
        _tier_pill(
            pdf,
            f"Most recent: {latest.get('tier_label', '—')}  ·  Total {latest.get('total_score', '—')} / 16"
            f"  ·  T{latest.get('threat_score', '—')} × V{latest.get('vulnerability_score', '—')}",
            (latest.get("tier") or "low"),
        )
    else:
        pdf.set_font("Helvetica", "I", 9.5); pdf.set_text_color(133, 126, 156)
        pdf.cell(0, 5, _safe("No assessments on file."), ln=1)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(30, 24, 54)
    pdf.cell(0, 5, _safe("Distribution across all assessments on file"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(75, 69, 103)
    for t in ("critical", "high", "medium", "low"):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*TIER_COLORS[t])
        pdf.cell(22, 4.5, _safe(TIER_LABELS[t].upper()))
        pdf.set_font("Helvetica", "", 9); pdf.set_text_color(30, 24, 54)
        pdf.cell(0, 4.5, _safe(f"{dist[t]} on file"), ln=1)
    pdf.ln(1)

    # ---- Coordinator email audit trail ----------------------------------
    if alerts:
        _section_break(pdf)
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 6, _safe("Coordinator alert audit"), ln=1)
        pdf.set_font("Helvetica", "", 9); pdf.set_text_color(75, 69, 103)
        pdf.multi_cell(0, 4.5, _safe(
            "Automated email alerts triggered by high or critical tier "
            "assessments. Each row reflects a real delivery attempt."
        ))
        pdf.ln(1)
        for a in alerts:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*TIER_COLORS.get(a.get("tier") or "low", (61, 26, 120)))
            pdf.cell(22, 4.5, _safe((a.get("tier") or "").upper()))
            status = "Delivered" if a.get("email_ok") else "Send failed"
            pdf.set_font("Helvetica", "", 9); pdf.set_text_color(30, 24, 54)
            pdf.cell(30, 4.5, _safe(status))
            pdf.set_text_color(133, 126, 156)
            pdf.cell(0, 4.5, _safe(_fmt_date(a.get("created_at") or "")), ln=1)

    # ---- Assessment history — newest first ------------------------------
    _section_break(pdf)
    pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Assessment history · newest first"), ln=1)

    if not history:
        pdf.set_font("Helvetica", "I", 9.5); pdf.set_text_color(133, 126, 156)
        pdf.multi_cell(0, 4.5, _safe("No assessments on file for this parent."))
    else:
        for idx, h in enumerate(history):
            _render_assessment_block(pdf, h, is_latest=(idx == 0))

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


def _render_assessment_block(pdf: _CasePdf, h: Dict[str, Any], *, is_latest: bool) -> None:
    """One assessment section — tier pill, scores line, sub-scores grid,
    and (if present) the parent's free-text notes."""
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    pdf.ln(2)

    # Header row: latest badge (if applicable) + when.
    if is_latest:
        pdf.set_fill_color(61, 26, 120)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(22, 4.5, _safe("LATEST"), align="C", fill=True)
        pdf.cell(4, 4.5, "")
    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(133, 126, 156)
    pdf.cell(0, 4.5, _safe(_fmt_date(h.get("created_at") or "")), ln=1)

    tier = (h.get("tier") or "low").lower()
    _tier_pill(
        pdf,
        f"{h.get('tier_label') or TIER_LABELS.get(tier, '?')}"
        f"  ·  Total {h.get('total_score', '—')} / 16"
        f"  ·  T{h.get('threat_score', '—')} × V{h.get('vulnerability_score', '—')}",
        tier,
    )
    pdf.ln(1)

    if h.get("coparent_name"):
        pdf.set_font("Helvetica", "", 9); pdf.set_text_color(75, 69, 103)
        pdf.cell(0, 4.5, _safe(f"Named coparent: {h['coparent_name']}"), ln=1)

    # Sub-scores summary (compact, no matrix answer leak).
    sub = h.get("sub_scores") or {}
    threat_sub = sub.get("threat") or {}
    vuln_sub = sub.get("vulnerability") or {}
    if threat_sub or vuln_sub:
        pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(30, 24, 54)
        pdf.cell(0, 4.5, _safe("Sub-scores"), ln=1)
        col_w = (pdf.epw - 2) / 2
        y_start = pdf.get_y()
        pdf.set_font("Helvetica", "", 9); pdf.set_text_color(75, 69, 103)
        # Threat column
        pdf.set_xy(pdf.l_margin, y_start)
        pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(61, 26, 120)
        pdf.cell(col_w, 4, _safe("Threat"), ln=2)
        pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(75, 69, 103)
        pdf.set_x(pdf.l_margin)
        for k, v in threat_sub.items():
            pdf.cell(col_w, 3.8, _safe(
                f"  {k.replace('threat_', '').replace('_', ' ')}: {v}"
            ), ln=2)
            pdf.set_x(pdf.l_margin)
        threat_end = pdf.get_y()
        # Vulnerability column (right side)
        pdf.set_xy(pdf.l_margin + col_w + 2, y_start)
        pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(61, 26, 120)
        pdf.cell(col_w, 4, _safe("Vulnerability"), ln=2)
        pdf.set_x(pdf.l_margin + col_w + 2)
        pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(75, 69, 103)
        for k, v in vuln_sub.items():
            pdf.cell(col_w, 3.8, _safe(
                f"  {k.replace('vuln_', '').replace('_', ' ')}: {v}"
            ), ln=2)
            pdf.set_x(pdf.l_margin + col_w + 2)
        vuln_end = pdf.get_y()
        # Advance to whichever column is taller.
        pdf.set_y(max(threat_end, vuln_end))
        pdf.set_x(pdf.l_margin)

    # Notes.
    notes = (h.get("notes") or "").strip()
    if notes:
        pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(30, 24, 54)
        pdf.cell(0, 4.5, _safe("Target parent notes"), ln=1)
        pdf.set_font("Helvetica", "I", 9); pdf.set_text_color(75, 69, 103)
        pdf.multi_cell(0, 4.5, _safe(notes))

    # Divider between assessments.
    pdf.ln(2)
    pdf.set_draw_color(224, 220, 232)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(1)
