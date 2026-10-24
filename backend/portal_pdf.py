"""Portal PDF generators — Foundation Statement + Legal Report.

Used by the SacoparentsPortal front-end "PDF" and "Export Legal PDF"
buttons via `portal_routes.py`. Both PDFs share the mockup's purple
brand palette and land as native, downloadable PDFs (not a browser
print-to-PDF).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from pdf_base import _safe
from case_safety import SAFETY_STEP_SEE


# Brand palette matches the SacoparentsPortal.jsx mockup:
#   header/deep purple  =  #4A1A6E  (tailwind purple-950-ish)
#   accent purple       =  #6D28D9  (tailwind purple-700)
#   soft purple wash    =  #F4EFFF
_PURPLE_DEEP = (74, 26, 110)
_PURPLE_ACCENT = (109, 40, 217)
_PURPLE_INK = (26, 19, 48)
_SLATE_INK = (30, 41, 59)
_SLATE_MUTED = (100, 116, 139)
_PURPLE_WASH = (244, 239, 255)
_EMERALD = (16, 185, 129)


class _PortalPDF(FPDF):
    """Shared PDF chassis with the purple portal branding header/footer."""

    def __init__(self, title: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._title = title
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=14, top=28, right=14)

    def header(self) -> None:  # pragma: no cover - visual
        # Deep purple banner
        self.set_fill_color(*_PURPLE_DEEP)
        self.rect(0, 0, self.w, 20, style="F")
        # Wordmark
        self.set_xy(14, 6)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, _safe("sacoparentsapp.online"), ln=1)
        self.set_x(14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(216, 200, 240)
        self.cell(0, 4, _safe("SA CoParents Assessment & Alignment Portal"))
        # Title chip on the right
        chip_w = 60
        self.set_xy(self.w - 14 - chip_w, 7)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(255, 255, 255)
        self.cell(chip_w, 6, _safe(self._title.upper()), align="R")

    def footer(self) -> None:  # pragma: no cover - visual
        self.set_y(-14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_SLATE_MUTED)
        self.cell(
            0,
            4,
            _safe(
                f"(c) {datetime.now(timezone.utc).year} sacoparentsapp.online "
                f"- Page {self.page_no()} of {{nb}}"
            ),
            align="C",
        )
        self.set_y(-9)
        self.cell(
            0,
            4,
            _safe(
                "Educational preparation document - not legal, medical, "
                "or therapeutic advice."
            ),
            align="C",
        )


def _draw_chip(pdf: FPDF, text: str, fill=_PURPLE_ACCENT) -> None:
    pdf.set_fill_color(*fill)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7)
    text_w = pdf.get_string_width(_safe(text)) + 6
    pdf.cell(text_w, 4.5, _safe(text.upper()), align="C", fill=True, ln=0)
    pdf.ln(6)


def _draw_h2(pdf: FPDF, text: str) -> None:
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 6, _safe(text), ln=1)
    pdf.set_draw_color(*_PURPLE_ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y() + 0.5, pdf.l_margin + 30, pdf.get_y() + 0.5)
    pdf.ln(3)


def _draw_text_block(pdf: FPDF, text: str, size: int = 10, color=_SLATE_INK) -> None:
    pdf.set_text_color(*color)
    pdf.set_font("Helvetica", "", size)
    pdf.multi_cell(0, 5, _safe(text))
    pdf.ln(1)


def _draw_meta_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.cell(45, 5, _safe(label.upper()))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_SLATE_INK)
    pdf.cell(0, 5, _safe(value or "-"), ln=1)


def _draw_sparkline(pdf: FPDF, points: List[float], *, x: float, y: float, w: float, h: float) -> None:
    """Draw a tiny line chart of `points` (0..10 range). Nothing rendered
    if we have fewer than 2 points."""
    if not points or len(points) < 2:
        return
    # Frame
    pdf.set_draw_color(*_PURPLE_ACCENT)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, w, h, style="D")
    # Mid line (5/10)
    pdf.set_draw_color(220, 214, 232)
    pdf.set_line_width(0.15)
    pdf.line(x, y + h / 2, x + w, y + h / 2)
    # Points
    n = len(points)
    step = w / (n - 1) if n > 1 else w
    pdf.set_draw_color(*_PURPLE_ACCENT)
    pdf.set_line_width(0.35)
    prev_px = None
    prev_py = None
    for i, val in enumerate(points):
        v = max(0.0, min(10.0, float(val)))
        px = x + i * step
        py = y + h - (v / 10.0) * h
        if prev_px is not None:
            pdf.line(prev_px, prev_py, px, py)
        prev_px = px
        prev_py = py
    # Dots
    pdf.set_fill_color(*_PURPLE_DEEP)
    for i, val in enumerate(points):
        v = max(0.0, min(10.0, float(val)))
        px = x + i * step
        py = y + h - (v / 10.0) * h
        pdf.ellipse(px - 0.7, py - 0.7, 1.4, 1.4, style="F")


def _reassessment_series(reassessments: Optional[List[Dict[str, Any]]], limit: int = 4) -> List[float]:
    """Extract the last `limit` overall averages from reassessment records
    (oldest → newest). Records that don't have a stored `avg` are ignored.
    """
    if not reassessments:
        return []
    # Records are stored newest-first in localStorage; sort by created date
    # if available, otherwise trust insertion order.
    def _key(rec):
        return rec.get("date") or rec.get("created_at") or ""

    ordered = sorted(reassessments, key=_key)
    tail = ordered[-limit:]
    series: List[float] = []
    for rec in tail:
        raw = rec.get("avg")
        if raw is None:
            snap = rec.get("snapshot") or {}
            if isinstance(snap, dict):
                s1 = snap.get("s1")
                s2 = snap.get("s2")
                s3 = snap.get("s3")
                if s1 is not None and s2 is not None and s3 is not None:
                    try:
                        raw = (float(s1) + float(s2) + float(s3)) / 3.0
                    except (TypeError, ValueError):
                        raw = None
        if raw is None:
            continue
        try:
            series.append(float(raw))
        except (TypeError, ValueError):
            continue
    return series


def build_portal_foundation_pdf(
    *,
    foundation_text: str,
    author_name: Optional[str] = None,
    case_ref: Optional[str] = None,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Build the branded Foundation Statement PDF from portal state."""
    text = (foundation_text or "").strip()
    if not text:
        raise ValueError("foundation_text is empty")

    when = generated_at or datetime.now(timezone.utc)
    pdf = _PortalPDF(title="Foundation Statement")
    pdf.alias_nb_pages()
    pdf.add_page()

    _draw_chip(pdf, "Step 4 - Anchor PDF")
    pdf.set_text_color(*_PURPLE_INK)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 9, _safe("Foundation Statement"), ln=1)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0,
        4.5,
        _safe(
            "Your one-page, child-focused anchor statement. Return to it "
            "whenever emotions get hot before you send the next message."
        ),
    )
    pdf.ln(3)

    _draw_meta_row(pdf, "Generated", when.strftime("%B %d, %Y"))
    _draw_meta_row(pdf, "Case Reference", case_ref or "Self-Guided Parent Journey")
    if author_name:
        _draw_meta_row(pdf, "Parent", author_name)
    pdf.ln(4)

    # Body panel — purple wash background
    x, y = pdf.l_margin, pdf.get_y()
    inner_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_fill_color(*_PURPLE_WASH)
    # Draw the wash after measuring text height:
    pdf.set_font("Helvetica", "", 11)
    # Estimate height by rendering into a scratch area — fpdf2 has no
    # dry-run, so we render then rewind. Simplest: fixed padding + rely
    # on auto page break.
    pad = 5
    pdf.set_xy(x, y)
    pdf.set_fill_color(*_PURPLE_WASH)
    pdf.set_draw_color(*_PURPLE_ACCENT)
    pdf.set_line_width(0.3)
    # Draw an outer rounded-look rect by hand (fpdf2 rounded_rect exists
    # in recent versions but we stay conservative).
    text_lines = pdf.multi_cell(
        inner_w - pad * 2,
        6,
        _safe(text),
        border=0,
        align="L",
        split_only=True,
    )
    block_h = pad * 2 + max(len(text_lines), 1) * 6
    pdf.set_xy(x, y)
    pdf.rect(x, y, inner_w, block_h, style="DF")
    pdf.set_xy(x + pad, y + pad)
    pdf.set_text_color(*_PURPLE_INK)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(inner_w - pad * 2, 6, _safe(text))
    pdf.ln(4)

    # Signature area
    _draw_h2(pdf, "Signed acknowledgement")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_SLATE_INK)
    pdf.cell(0, 5, _safe("Parent signature: __________________________________"), ln=1)
    pdf.ln(2)
    pdf.cell(0, 5, _safe("Date: __________________________________"), ln=1)

    return bytes(pdf.output(dest="S"))


def _health_label(avg: float) -> str:
    if avg >= 7.5:
        return "High Alignment"
    if avg >= 5.5:
        return "Moderate Alignment"
    return "Low Alignment"


_DEFAULT_MATRIX: List[Dict[str, str]] = [
    {"area": "Schedule Changes", "protocol": "24-Hr Advance Notice + Cooling Off"},
    {"area": "Child Handoffs", "protocol": "Neutral Public Location Default"},
    {
        "area": "Medical Decision Impasse",
        "protocol": "Referral to Primary Pediatrician",
    },
]


def build_portal_legal_report_pdf(
    *,
    health_index: Dict[str, int],
    foundation_text: Optional[str] = None,
    signatures: Optional[Dict[str, str]] = None,
    matrix: Optional[List[Dict[str, str]]] = None,
    case_ref: Optional[str] = None,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Build the Official Legal Conflict Resolution Report PDF."""
    when = generated_at or datetime.now(timezone.utc)
    sigs = signatures or {}
    rows = matrix or _DEFAULT_MATRIX

    s1 = int(health_index.get("s1", 5) or 5)
    s2 = int(health_index.get("s2", 5) or 5)
    s3 = int(health_index.get("s3", 5) or 5)
    for v in (s1, s2, s3):
        if v < 1 or v > 10:
            raise ValueError("health_index scores must be integers 1..10")
    avg = round((s1 + s2 + s3) / 3, 1)
    label = _health_label(avg)

    pdf = _PortalPDF(title="Legal Conflict Resolution Report")
    pdf.alias_nb_pages()
    pdf.add_page()

    _draw_chip(pdf, "Official Legal Module")
    pdf.set_text_color(*_PURPLE_INK)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 8, _safe("Official Legal Conflict"), ln=1)
    pdf.cell(0, 8, _safe("Resolution Report"), ln=1)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0,
        4.5,
        _safe(
            "San Antonio, TX Court & Mediation Standard Document - "
            "Matt Sossi Methodology"
        ),
    )
    pdf.ln(3)

    _draw_meta_row(pdf, "Generated", when.strftime("%B %d, %Y"))
    _draw_meta_row(pdf, "Case Reference", case_ref or "Self-Guided Parent Journey")
    _draw_meta_row(
        pdf,
        "Mediator",
        sigs.get("sigMed") or "Matt Sossi, Licensed Mediator (San Antonio, TX)",
    )
    pdf.ln(4)

    # Section 1: Conflict Escalation & Compliance Diagnostic
    _draw_h2(pdf, "1. Conflict Escalation & Compliance Diagnostic")

    inner_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_fill_color(*_PURPLE_WASH)
    pdf.set_draw_color(*_PURPLE_ACCENT)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    box_h = 44
    pdf.rect(pdf.l_margin, y, inner_w, box_h, style="DF")

    def _score_row(y_offset: float, label: str, val: int) -> None:
        pdf.set_xy(pdf.l_margin + 4, y + y_offset)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_SLATE_INK)
        pdf.cell(90, 5, _safe(label))
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_PURPLE_ACCENT)
        pdf.cell(20, 5, _safe(f"{val} / 10"), align="R")
        # Progress bar
        bar_x = pdf.l_margin + 4
        bar_y = y + y_offset + 5.5
        bar_w = inner_w - 8
        pdf.set_fill_color(232, 224, 245)
        pdf.rect(bar_x, bar_y, bar_w, 2, style="F")
        pdf.set_fill_color(*_PURPLE_ACCENT)
        pdf.rect(bar_x, bar_y, bar_w * val / 10.0, 2, style="F")

    _score_row(3, "Info Sharing & Transparency", s1)
    _score_row(14, "Handoff & Transition Predictability", s2)
    _score_row(25, "Decision-Making Collaboration", s3)

    # Overall
    overall_y = y + box_h - 8
    pdf.set_xy(pdf.l_margin + 4, overall_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.cell(0, 4, _safe("OVERALL CO-PARENTING HEALTH INDEX"), ln=1)
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_PURPLE_INK)
    pdf.cell(0, 5, _safe(f"{avg} / 10 - {label}"), ln=1)
    pdf.set_y(y + box_h + 3)

    # Section 2: Dispute Resolution Matrix
    _draw_h2(pdf, "2. Legal Dispute Resolution Matrix")
    # Table
    col_a = 70
    col_b = inner_w - col_a
    # Header
    pdf.set_fill_color(240, 240, 245)
    pdf.set_text_color(*_SLATE_INK)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(col_a, 6.5, _safe("Dispute Area"), border="B", fill=True)
    pdf.cell(col_b, 6.5, _safe("Default Resolution Protocol"), border="B", fill=True, ln=1)
    pdf.set_font("Helvetica", "", 9)
    for r in rows:
        pdf.set_text_color(*_SLATE_INK)
        pdf.cell(col_a, 6, _safe(str(r.get("area") or "")), border="B")
        pdf.set_text_color(*_SLATE_MUTED)
        pdf.cell(
            col_b,
            6,
            _safe(str(r.get("protocol") or "")),
            border="B",
            ln=1,
        )
    pdf.ln(4)

    # Section 3: Foundation Statement echo (optional)
    if foundation_text and foundation_text.strip():
        _draw_h2(pdf, "3. Foundation Statement (Anchor)")
        _draw_text_block(pdf, foundation_text.strip())
        pdf.ln(2)

    # Section 4: Signatures
    _draw_h2(pdf, "Digital Affirmation & Certification")
    col_w = (inner_w - 6) / 2

    def _sig_col(x: float, y: float, label: str, value: str) -> None:
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_PURPLE_DEEP)
        pdf.cell(col_w, 4, _safe(label.upper()), ln=2)
        pdf.set_xy(x, y + 4.5)
        pdf.set_draw_color(*_SLATE_MUTED)
        pdf.set_line_width(0.2)
        pdf.line(x, y + 12, x + col_w, y + 12)
        pdf.set_xy(x, y + 6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_SLATE_INK)
        pdf.cell(col_w, 5, _safe(value or ""), ln=2)

    sy = pdf.get_y()
    _sig_col(pdf.l_margin, sy, "Parent A Signature", sigs.get("sigA") or "")
    _sig_col(pdf.l_margin + col_w + 6, sy, "Parent B Signature", sigs.get("sigB") or "")
    pdf.set_y(sy + 16)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.cell(0, 4, _safe("CERTIFIED MEDIATOR / ATTORNEY"), ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_SLATE_INK)
    pdf.cell(0, 6, _safe(sigs.get("sigMed") or "Matt Sossi, Licensed Mediator (San Antonio, TX)"), ln=1)

    return bytes(pdf.output(dest="S"))



# ============================================================
# Weekly Progress snapshot PDF
# ============================================================

def _fmt_date_iso(raw: Any) -> str:
    """Coerce anything that looks like a date/datetime into 'YYYY-MM-DD'."""
    if not raw:
        return ""
    if isinstance(raw, datetime):
        return raw.strftime("%Y-%m-%d")
    s = str(raw).strip()
    if not s:
        return ""
    # Common formats: 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM', ISO 8601
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[: len(fmt) + 2], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s[:10]


def _in_last_7_days(iso_date: str, ref: datetime) -> bool:
    if not iso_date:
        return False
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    delta = ref - d
    return delta.days >= 0 and delta.days <= 7


def build_portal_weekly_progress_pdf(
    *,
    health_index: Dict[str, int],
    biff_logs: Optional[List[Dict[str, Any]]] = None,
    milestones: Optional[List[Dict[str, Any]]] = None,
    reassessments: Optional[List[Dict[str, Any]]] = None,
    foundation_text: Optional[str] = None,
    case_ref: Optional[str] = None,
    author_name: Optional[str] = None,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """One-page snapshot suitable to hand to a pediatrician or attorney.

    Renders:
      * Header: date range + case/parent metadata
      * Current Health Index with progress bars + label
      * Milestones this week (successes vs friction, chip counts)
      * Recent BIFF messages (up to 5 most recent)
      * Foundation Statement anchor (excerpt)

    Everything is filtered to the last 7 days where the underlying record
    carries a date; anything without a date falls into the "recent" bucket.
    """
    when = generated_at or datetime.now(timezone.utc)
    week_start = when
    week_ago = when.replace(hour=0, minute=0, second=0, microsecond=0)
    range_start = when.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta as _td
    range_start = week_ago - _td(days=7)

    s1 = int((health_index or {}).get("s1", 5) or 5)
    s2 = int((health_index or {}).get("s2", 5) or 5)
    s3 = int((health_index or {}).get("s3", 5) or 5)
    for v in (s1, s2, s3):
        if v < 1 or v > 10:
            raise ValueError("health_index scores must be integers 1..10")
    avg = round((s1 + s2 + s3) / 3, 1)
    label = _health_label(avg)

    pdf = _PortalPDF(title="Weekly Progress Snapshot")
    pdf.alias_nb_pages()
    pdf.add_page()

    _draw_chip(pdf, "Weekly Snapshot")
    pdf.set_text_color(*_PURPLE_INK)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 9, _safe("Weekly Progress Snapshot"), ln=1)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0,
        4.5,
        _safe(
            "A one-page summary of your co-parenting alignment this week. "
            "Share with your pediatrician, mediator, or attorney."
        ),
    )
    pdf.ln(2)

    _draw_meta_row(
        pdf,
        "Period",
        f"{range_start.strftime('%b %d, %Y')} - {when.strftime('%b %d, %Y')}",
    )
    _draw_meta_row(pdf, "Case Reference", case_ref or "Self-Guided Parent Journey")
    if author_name:
        _draw_meta_row(pdf, "Parent", author_name)
    pdf.ln(3)

    # ---- Health Index panel ----
    _draw_h2(pdf, "Co-Parenting Health Index")
    inner_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_fill_color(*_PURPLE_WASH)
    pdf.set_draw_color(*_PURPLE_ACCENT)
    pdf.set_line_width(0.3)
    y0 = pdf.get_y()
    box_h = 44
    pdf.rect(pdf.l_margin, y0, inner_w, box_h, style="DF")

    def _score_row(y_offset: float, row_label: str, val: int) -> None:
        pdf.set_xy(pdf.l_margin + 4, y0 + y_offset)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_SLATE_INK)
        pdf.cell(90, 5, _safe(row_label))
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_PURPLE_ACCENT)
        pdf.cell(20, 5, _safe(f"{val} / 10"), align="R")
        bar_x = pdf.l_margin + 4
        bar_y = y0 + y_offset + 5.5
        bar_w = inner_w - 8
        pdf.set_fill_color(232, 224, 245)
        pdf.rect(bar_x, bar_y, bar_w, 2, style="F")
        pdf.set_fill_color(*_PURPLE_ACCENT)
        pdf.rect(bar_x, bar_y, bar_w * val / 10.0, 2, style="F")

    _score_row(3, "Info Sharing & Transparency", s1)
    _score_row(14, "Handoff & Transition Predictability", s2)
    _score_row(25, "Decision-Making Collaboration", s3)

    overall_y = y0 + box_h - 8
    pdf.set_xy(pdf.l_margin + 4, overall_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.cell(0, 4, _safe("OVERALL CO-PARENTING HEALTH INDEX"), ln=1)
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_PURPLE_INK)
    pdf.cell(0, 5, _safe(f"{avg} / 10 - {label}"), ln=1)
    pdf.set_y(y0 + box_h + 3)

    # ---- Trend line (last 4 reassessments) ----
    series = _reassessment_series(reassessments, limit=4)
    # Always include the current avg as the newest point so the chart
    # never renders "empty" for a parent who just started using the tool.
    series_with_current = series + [float(avg)] if series else []
    if len(series_with_current) >= 2:
        _draw_h2(pdf, "Trend (last 4 reassessments + current)")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_SLATE_MUTED)
        pdf.multi_cell(
            0,
            4,
            _safe(
                "Each dot is an overall Health Index score. Higher is "
                "better — the trend matters more than any single point."
            ),
        )
        chart_y = pdf.get_y() + 1
        _draw_sparkline(
            pdf,
            series_with_current,
            x=pdf.l_margin,
            y=chart_y,
            w=inner_w,
            h=18,
        )
        # Legend
        pdf.set_y(chart_y + 20)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_SLATE_MUTED)
        labels = [f"{v:.1f}" for v in series_with_current]
        pdf.cell(0, 3, _safe(" -> ".join(labels)), align="C", ln=1)
        pdf.ln(2)

    # ---- Milestones counts ----
    recent_milestones = [
        m for m in (milestones or []) if _in_last_7_days(_fmt_date_iso(m.get("date")), when)
    ]
    # If nothing in the last 7 days, fall back to the most recent 3.
    if not recent_milestones and milestones:
        recent_milestones = list(milestones)[:3]
    succ = sum(1 for m in recent_milestones if m.get("type") == "success")
    fric = sum(1 for m in recent_milestones if m.get("type") == "friction")

    _draw_h2(pdf, "Milestones this week")
    col_w = (inner_w - 6) / 2
    y_m = pdf.get_y()
    # Successes chip
    pdf.set_fill_color(212, 244, 227)
    pdf.set_draw_color(*_EMERALD)
    pdf.rect(pdf.l_margin, y_m, col_w, 12, style="DF")
    pdf.set_xy(pdf.l_margin, y_m + 2)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(6, 106, 66)
    pdf.cell(col_w, 6, _safe(str(succ)), align="C", ln=2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(col_w, 4, _safe("SUCCESSFUL RESOLUTIONS"), align="C", ln=2)
    # Friction chip
    pdf.set_xy(pdf.l_margin + col_w + 6, y_m)
    pdf.set_fill_color(253, 226, 226)
    pdf.set_draw_color(190, 40, 40)
    pdf.rect(pdf.l_margin + col_w + 6, y_m, col_w, 12, style="DF")
    pdf.set_xy(pdf.l_margin + col_w + 6, y_m + 2)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(160, 40, 40)
    pdf.cell(col_w, 6, _safe(str(fric)), align="C", ln=2)
    pdf.set_xy(pdf.l_margin + col_w + 6, y_m + 8)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(col_w, 4, _safe("FRICTION POINTS"), align="C", ln=1)
    pdf.set_y(y_m + 16)

    # List milestones (bullet)
    for m in recent_milestones[:6]:
        title = str(m.get("title") or "").strip()
        date = _fmt_date_iso(m.get("date"))
        note = str(m.get("note") or "").strip()
        mtype = str(m.get("type") or "").upper() or "SUCCESS"
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_PURPLE_DEEP)
        pdf.cell(0, 4, _safe(f"[{mtype}]  {title}  ({date})"), ln=1)
        if note:
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*_SLATE_MUTED)
            pdf.multi_cell(0, 4, _safe(f"    {note}"))
        pdf.ln(0.5)

    if not recent_milestones:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*_SLATE_MUTED)
        pdf.multi_cell(0, 5, _safe("No milestones logged in the last 7 days."))
    pdf.ln(2)

    # ---- BIFF messages ----
    recent_biff = list(biff_logs or [])[:5]
    _draw_h2(pdf, "Recent BIFF Messages")
    if not recent_biff:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*_SLATE_MUTED)
        pdf.multi_cell(0, 5, _safe("No archived messages yet."))
        pdf.ln(2)
    for entry in recent_biff:
        ts = str(entry.get("timestamp") or "").strip()
        cat = str(entry.get("category") or "BIFF").strip()
        biff = str(entry.get("biff") or "").strip()
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_PURPLE_DEEP)
        pdf.cell(0, 4, _safe(f"{ts}  -  {cat}"), ln=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_SLATE_INK)
        pdf.multi_cell(0, 5, _safe(biff))
        pdf.ln(0.5)

    # ---- Foundation excerpt ----
    if foundation_text and foundation_text.strip():
        _draw_h2(pdf, "Foundation Statement (Anchor)")
        excerpt = foundation_text.strip()
        if len(excerpt) > 500:
            excerpt = excerpt[:500].rstrip() + "..."
        _draw_text_block(pdf, excerpt)

    return bytes(pdf.output(dest="S"))



# ---------------------------------------------------------------------------
# Complete Coparenting Report — bundles every parent-facing artefact into one
# multi-page PDF suitable for sharing with a mediator, attorney, or the
# co-parent. Renders one section per artefact, with an empty-state stub when
# a section hasn't been built yet so the parent sees exactly what to fill in
# next.
# ---------------------------------------------------------------------------

_CATEGORY_ORDER = ("Medical", "Educational", "Psychological")


def _draw_empty_state(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.multi_cell(0, 5, _safe(text))
    pdf.ln(1)


def _draw_align_records_section(
    pdf: FPDF,
    records: List[Dict[str, Any]],
    heading: str,
    empty_stub: str,
) -> None:
    """Render Medical/Educational/Psychological alignment records under
    a subheading, grouped by category. Used for both individual and joint
    variants — pass the pre-filtered list in.
    """
    _draw_h2(pdf, heading)
    if not records:
        _draw_empty_state(pdf, empty_stub)
        return
    for category in _CATEGORY_ORDER:
        bucket = [r for r in records if str(r.get("category", "")) == category]
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_PURPLE_INK)
        pdf.cell(0, 5, _safe(f"{category} ({len(bucket)})"), ln=1)
        if not bucket:
            _draw_empty_state(pdf, f"No {category.lower()} alignment records logged yet.")
            continue
        for r in bucket:
            title = str(r.get("title") or "Untitled").strip()
            provider = str(r.get("provider") or "").strip()
            date = str(r.get("date") or "").strip()
            summary = str(r.get("summary") or "").strip()
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_SLATE_INK)
            pdf.cell(0, 4.5, _safe(title), ln=1)
            meta_bits = [b for b in (provider, date) if b]
            if meta_bits:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*_SLATE_MUTED)
                pdf.cell(0, 4, _safe("  ·  ".join(meta_bits)), ln=1)
            if summary:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*_SLATE_INK)
                pdf.multi_cell(0, 4.5, _safe(summary))
            pdf.ln(0.4)
    pdf.ln(1)


def build_portal_complete_report_pdf(
    *,
    safety_step: Optional[str] = None,
    cop_assessment: Optional[Dict[str, Any]] = None,
    align_records: Optional[List[Dict[str, Any]]] = None,
    joint_records: Optional[List[Dict[str, Any]]] = None,
    joint_summary: Optional[Dict[str, Any]] = None,
    foundation_text: Optional[str] = None,
    case_ref: Optional[str] = None,
    author_name: Optional[str] = None,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Assemble the Complete Coparenting Report PDF.

    ``safety_step`` is the only safety wording (from the Family check-in status). Sections rendered in order:
      1. Co-parenting Assessment (Health Index sliders from the portal;
         when the caller provides a richer external assessment via
         ``cop_assessment`` we surface those values instead).
      3. Individual Align-Before-Agreement Records (portal's own
         alignment records, grouped by Medical / Educational /
         Psychological).
      4. Joint Alignment Summary (``joint_summary`` — the caller's
         latest ``agreements`` doc pulled server-side when auth is
         present) OR any explicitly-provided joint alignment records
         (``joint_records``). If neither is present, an empty-state
         stub points the parent at ``/joint-agreement`` to build one.
      5. Foundation Statement (verbatim, from portal state).

    Empty sections are rendered with an italicised muted stub so the
    consumer of the report sees exactly what the parent still has to
    complete — never a silent hole.
    """
    when = generated_at or datetime.now(timezone.utc)

    pdf = _PortalPDF(title="Complete Coparenting Report")
    pdf.alias_nb_pages()
    pdf.add_page()

    # ---- Header ----
    _draw_chip(pdf, "Complete Coparenting Report")
    pdf.set_text_color(*_PURPLE_INK)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 9, _safe("Complete Coparenting Report"), ln=1)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0,
        4.5,
        _safe(
            "A bundle of the parent's self-guided coparenting work. Share "
            "with a mediator, attorney, or co-parent. Sections the parent "
            "hasn't completed yet are shown as empty so nothing is hidden."
        ),
    )
    pdf.ln(2)

    _draw_meta_row(pdf, "Generated", when.strftime("%b %d, %Y %H:%M UTC"))
    _draw_meta_row(pdf, "Case Reference", case_ref or "Self-Guided Coparenting Journey")
    if author_name:
        _draw_meta_row(pdf, "Parent", author_name)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_SLATE_INK)
    pdf.cell(0, 6, _safe(safety_step or SAFETY_STEP_SEE), ln=1)
    pdf.ln(3)

    # ---- 2. Co-parenting Assessment (Health Index for now) ----
    _draw_h2(pdf, "1. Co-parenting Assessment")
    if cop_assessment and isinstance(cop_assessment, dict):
        s1 = int(cop_assessment.get("s1", 0) or 0)
        s2 = int(cop_assessment.get("s2", 0) or 0)
        s3 = int(cop_assessment.get("s3", 0) or 0)
    else:
        s1 = s2 = s3 = 0
    if s1 and s2 and s3:
        avg = round((s1 + s2 + s3) / 3, 1)
        _draw_meta_row(pdf, "Communication (1-10)", str(s1))
        _draw_meta_row(pdf, "Consistency (1-10)", str(s2))
        _draw_meta_row(pdf, "Emotional Alignment (1-10)", str(s3))
        _draw_meta_row(pdf, "Average", f"{avg} - {_health_label(avg)}")
    else:
        _draw_empty_state(
            pdf,
            "No self-assessment recorded yet. In the Portal, tap the "
            "Co-parenting Assessment tile or move the three Health Index "
            "sliders to save a snapshot.",
        )
    pdf.ln(2)

    # ---- 3. Individual Align Before Agreement ----
    _draw_align_records_section(
        pdf,
        list(align_records or []),
        heading="2. Individual Align Before Agreement",
        empty_stub=(
            "To protect your child's privacy, SA CoParents does not keep "
            "medical, educational or psychological records."
        ),
    )

    # ---- 4. Joint Alignment Summary ----
    # Prefer the server-fetched `agreements` doc (joint_summary) — it
    # holds prose sections (shared_goals, communication, child_needs,
    # household_rules, priority_items, open_for_discussion). Fall
    # back to explicit joint_records if the caller passed them, and
    # finally to an empty-state stub pointing the parent at the
    # /joint-agreement flow.
    _draw_h2(pdf, "3. Joint Alignment Summary")

    joint_sections = [
        ("shared_goals", "Shared Goals"),
        ("communication", "Communication"),
        ("child_needs", "Child Needs"),
        ("household_rules", "Household Rules"),
        ("priority_items", "Priority Items"),
        ("open_for_discussion", "Open for Discussion"),
    ]

    has_joint_summary = False
    if joint_summary and isinstance(joint_summary, dict):
        has_joint_summary = any(
            joint_summary.get(k) for k, _ in joint_sections
        )

    if has_joint_summary:
        overview = str(joint_summary.get("overview") or "").strip()
        if overview:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_SLATE_INK)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, _safe(overview))
            pdf.ln(1)
        for key, label in joint_sections:
            items = joint_summary.get(key) or []
            if not items:
                continue
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_PURPLE_INK)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 5, _safe(label), ln=1)
            for item in items:
                if isinstance(item, dict):
                    # Reuse joint_agreement's clause-shape convention:
                    # try common keys; fall back to any string value.
                    text = (
                        item.get("agreement")
                        or item.get("statement")
                        or item.get("clause")
                        or item.get("text")
                        or item.get("topic")
                        or item.get("value")
                        or ""
                    )
                    area = item.get("area") or item.get("category") or ""
                elif isinstance(item, str):
                    text = item
                    area = ""
                else:
                    continue
                text = str(text).strip()
                if not text:
                    continue
                if area:
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(*_SLATE_MUTED)
                    pdf.set_x(pdf.l_margin)
                    pdf.cell(0, 4, _safe(str(area)), ln=1)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*_SLATE_INK)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, _safe(f"- {text}"))
            pdf.ln(0.5)
        closing = str(joint_summary.get("closing_note") or "").strip()
        if closing:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*_SLATE_MUTED)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, _safe(closing))
        pdf.ln(1)
    elif joint_records:
        # Fallback path: caller supplied categorised joint records.
        _draw_align_records_section(
            pdf,
            list(joint_records or []),
            heading="Joint Records by Category",
            empty_stub="",
        )
    else:
        _draw_empty_state(
            pdf,
            "No joint alignment on file yet. Both parents can build one "
            "in the Co-Parenting Agreement flow at "
            "sacoparentsapp.online/joint-agreement.",
        )

    # ---- 5. Foundation Statement ----
    _draw_h2(pdf, "4. Foundation Statement")
    text = (foundation_text or "").strip()
    if not text:
        _draw_empty_state(
            pdf,
            "No Foundation Statement written yet. In the Portal, open the "
            "Foundation Statement panel and write the child-first anchor.",
        )
    else:
        _draw_text_block(pdf, text)

    return bytes(pdf.output(dest="S"))



# --------------------------------------------------------------------- #
# iter222 · Coparent Snapshot PDF — the "print this and stick it on the
# fridge, or forward it to your mediator" one-pager built from a finished
# Guided Journey wizard run.
# --------------------------------------------------------------------- #
_TOPIC_LABELS = {
    "foundation": "Foundation Statement Snapshot",
    "coparenting": "Co-parenting Assessment Snapshot",
    "safety": "Conflict Readiness Snapshot",
    "medical": "Medical Needs Snapshot",
    "educational": "Educational Snapshot",
    "psychological": "Psychological Snapshot",
}
_TOPIC_INTRO = {
    "foundation": (
        "A child-first anchor built from your guided conversation. Return to "
        "it whenever emotions get hot."
    ),
    "coparenting": (
        "A plain-language summary of where your co-parenting is strong and "
        "where you'd like more support."
    ),
    "safety": (
        "Your plan for staying calm and child-focused in tense moments "
        "and hand-offs."
    ),
    "medical": (
        "A one-page snapshot of your child's medical picture — providers, "
        "appointments, medications, priorities."
    ),
    "educational": (
        "A one-page snapshot of your child's schooling — programs, "
        "supports, upcoming milestones."
    ),
    "psychological": (
        "A one-page snapshot of your child's mental-health picture — "
        "clinicians, plans, observations."
    ),
}


# --- Fridge-card headlines (postcard variant) -------------------- #
_FRIDGE_HEADLINES = {
    "foundation": "Our Foundation",
    "coparenting": "Our Co-parenting Plan",
    "safety": "Our Calm Hand-off Plan",
    "medical": "Our Medical Plan",
    "educational": "Our School Plan",
    "psychological": "Our Support Plan",
}


def _draw_fridge_card(
    pdf: FPDF,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    when: datetime,
    author_name: Optional[str],
    safety_flagged: bool,
    plain: List[str],
) -> None:
    """Draw a single A6-sized fridge card at (x, y) with size (w, h).

    Extracted so ``_build_fridge_snapshot_pdf`` (solo) and
    ``_build_fridge_pair_snapshot_pdf`` (two-up on A5-landscape) can
    share the exact same layout with zero drift.
    """
    inner_pad = 8
    inner_w = w - inner_pad * 2

    # Headline
    pdf.set_xy(x + inner_pad, y + inner_pad)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.cell(inner_w, 8, _safe(label), ln=1)

    # Meta strip
    pdf.set_x(x + inner_pad)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_SLATE_MUTED)
    meta = when.strftime("%B %d, %Y")
    if author_name:
        meta = f"{author_name} \u2022 {meta}"
    if safety_flagged:
        meta = f"{meta} \u2022 Grey-rock voice"
    pdf.cell(inner_w, 3, _safe(meta), ln=1)
    pdf.ln(2)

    if plain:
        pdf.set_draw_color(*_PURPLE_ACCENT)
        pdf.set_line_width(0.3)
        divider_y = pdf.get_y()
        pdf.line(x + inner_pad, divider_y, x + w - inner_pad, divider_y)
        pdf.ln(3)
        for text in plain[:5]:
            pdf.set_x(x + inner_pad)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_PURPLE_ACCENT)
            pdf.cell(4, 5, _safe("\u2022"))
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*_PURPLE_INK)
            pdf.multi_cell(inner_w - 4, 5, _safe(text))
            pdf.ln(1)
    else:
        pdf.set_x(x + inner_pad)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*_SLATE_MUTED)
        pdf.multi_cell(
            inner_w,
            5,
            _safe(
                "Come back and complete a Guided Journey to fill this "
                "postcard with your commitments."
            ),
        )

    # Sign lines pinned to the bottom of the card so they sit right
    # where a fridge magnet would hold the postcard.
    sign_zone_top = y + h - 24
    pdf.set_draw_color(*_SLATE_MUTED)
    pdf.set_line_width(0.2)
    half_w = (inner_w - 4) / 2
    line_y = sign_zone_top + 4
    pdf.line(x + inner_pad, line_y, x + inner_pad + half_w, line_y)
    pdf.line(
        x + inner_pad + half_w + 4,
        line_y,
        x + w - inner_pad,
        line_y,
    )
    pdf.set_xy(x + inner_pad, sign_zone_top + 5)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.cell(half_w, 3, _safe("Parent A signature"), align="C")
    pdf.cell(4, 3, "")
    pdf.cell(half_w, 3, _safe("Parent B signature"), align="C")
    pdf.set_xy(x + inner_pad, sign_zone_top + 9)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_PURPLE_DEEP)
    pdf.cell(inner_w, 3, _safe("Signed by both parents"), align="C")

    # Card label sits just above the page's copyright line (drawn at 6mm from the bottom edge).
    pdf.set_xy(x + inner_pad, y + h - 10)
    pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.cell(inner_w, 3, _safe(f"sacoparentsapp.online \u2022 {label}"), align="C")


def _plain_answers(answers: List[Dict[str, str]]) -> List[str]:
    plain: List[str] = []
    for qa in answers:
        raw = str(qa.get("answer") or "").strip()
        if not raw:
            continue
        if len(raw) > 140:
            raw = raw[:137].rstrip() + "..."
        plain.append(raw)
    return plain


class _FridgePDF(FPDF):
    """Postcard-sized (A6 portrait) fpdf chassis. Solo variant."""

    def __init__(self) -> None:
        # A6: 105 × 148 mm. Fits on a fridge magnet + prints on standard
        # 4×6 photo paper without cropping.
        super().__init__(orientation="P", unit="mm", format=(105.0, 148.0))
        self.set_auto_page_break(auto=False, margin=0)
        self.set_margins(left=0, top=0, right=0)

    def header(self) -> None:  # pragma: no cover - visual
        return

    def footer(self) -> None:  # pragma: no cover - visual
        return


def _build_fridge_snapshot_pdf(
    *,
    topic: str,
    answers: List[Dict[str, str]],
    author_name: Optional[str] = None,
    safety_flagged: bool = False,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Postcard-size (A6) snapshot for the fridge."""
    when = generated_at or datetime.now(timezone.utc)
    label = _FRIDGE_HEADLINES.get(topic, _TOPIC_LABELS[topic])
    pdf = _FridgePDF()
    pdf.add_page()
    _draw_fridge_card(
        pdf,
        x=0,
        y=0,
        w=105.0,
        h=148.0,
        label=label,
        when=when,
        author_name=author_name,
        safety_flagged=safety_flagged,
        plain=_plain_answers(answers),
    )
    return bytes(pdf.output(dest="S"))


class _FridgePairPDF(FPDF):
    """A5-landscape sheet (210×148 mm) that holds two A6 cards side by side."""

    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format=(148.0, 210.0))
        self.set_auto_page_break(auto=False, margin=0)
        self.set_margins(left=0, top=0, right=0)

    def header(self) -> None:  # pragma: no cover - visual
        return

    def footer(self) -> None:  # pragma: no cover - visual
        return


def _build_fridge_pair_snapshot_pdf(
    *,
    topic: str,
    answers: List[Dict[str, str]],
    author_name: Optional[str] = None,
    safety_flagged: bool = False,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Two A6 fridge cards side-by-side on an A5-landscape sheet.

    Prints on a single sheet of A5-landscape paper (210×148 mm) or on
    standard US-Letter (with margins) — cut down the dashed centerline
    and each parent walks away with an identical fridge card.
    """
    when = generated_at or datetime.now(timezone.utc)
    label = _FRIDGE_HEADLINES.get(topic, _TOPIC_LABELS[topic])
    plain = _plain_answers(answers)

    pdf = _FridgePairPDF()
    pdf.add_page()

    # Left card: (0, 0) to (105, 148); right card: (105, 0) to (210, 148).
    _draw_fridge_card(
        pdf,
        x=0,
        y=0,
        w=105.0,
        h=148.0,
        label=label,
        when=when,
        author_name=author_name,
        safety_flagged=safety_flagged,
        plain=plain,
    )
    _draw_fridge_card(
        pdf,
        x=105.0,
        y=0,
        w=105.0,
        h=148.0,
        label=label,
        when=when,
        author_name=author_name,
        safety_flagged=safety_flagged,
        plain=plain,
    )

    # Dashed cutting line down the centerline with a small "cut here"
    # scissors label at the top.
    pdf.set_draw_color(*_SLATE_MUTED)
    pdf.set_line_width(0.15)
    # Dashed by drawing many short segments.
    y = 4.0
    while y < 144.0:
        pdf.line(105.0, y, 105.0, y + 3)
        y += 5
    # Scissors + label at the very top of the centerline.
    pdf.set_xy(101.0, 0.5)
    pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(*_SLATE_MUTED)
    pdf.cell(8, 3, _safe("\u2702 cut"), align="C")

    return bytes(pdf.output(dest="S"))


def build_portal_guided_snapshot_pdf(
    *,
    topic: str,
    answers: List[Dict[str, str]],
    author_name: Optional[str] = None,
    case_ref: Optional[str] = None,
    safety_flagged: bool = False,
    variant: str = "standard",
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Render a finished Guided Journey wizard as a shareable PDF.

    ``variant='standard'`` — A4 portrait, one Q&A card per question,
    signature block reserved for the mediator/attorney workflow.

    ``variant='fridge'`` — A6 postcard (105 × 148 mm), oversized type,
    condensed answer-only layout with a "Signed by both parents ___"
    line at the bottom so parents can stick it on the fridge and
    hand-sign it together.

    ``variant='fridge_pair'`` — Two identical A6 fridge cards laid
    out side-by-side on an A5-landscape sheet (210 × 148 mm) with a
    dashed cut line down the centerline. Print once, cut once, both
    parents walk away with the same card.
    """
    if topic not in _TOPIC_LABELS:
        raise ValueError(f"unknown topic: {topic}")
    if not isinstance(answers, list):
        raise ValueError("answers must be a list")
    if variant not in ("standard", "fridge", "fridge_pair"):
        raise ValueError(f"unknown variant: {variant}")

    if variant == "fridge":
        return _build_fridge_snapshot_pdf(
            topic=topic,
            answers=answers,
            author_name=author_name,
            safety_flagged=safety_flagged,
            generated_at=generated_at,
        )
    if variant == "fridge_pair":
        return _build_fridge_pair_snapshot_pdf(
            topic=topic,
            answers=answers,
            author_name=author_name,
            safety_flagged=safety_flagged,
            generated_at=generated_at,
        )

    when = generated_at or datetime.now(timezone.utc)
    label = _TOPIC_LABELS[topic]
    pdf = _PortalPDF(title=label)
    pdf.alias_nb_pages()
    pdf.add_page()

    _draw_chip(pdf, "Guided Journey Snapshot")
    pdf.set_text_color(*_PURPLE_INK)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 9, _safe(label), ln=1)

    pdf.set_text_color(*_SLATE_MUTED)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 4.5, _safe(_TOPIC_INTRO.get(topic, "")))
    pdf.ln(3)

    _draw_meta_row(pdf, "Generated", when.strftime("%B %d, %Y"))
    _draw_meta_row(pdf, "Case Reference", case_ref or "Self-Guided Parent Journey")
    if author_name:
        _draw_meta_row(pdf, "Parent", author_name)
    if safety_flagged:
        _draw_meta_row(pdf, "Communication Style", "Grey-rock voice")
    pdf.ln(3)

    if not answers:
        _draw_empty_state(
            pdf,
            "No answers captured yet — reopen the Guided chat from your "
            "Coparenting Journey toolkit to complete the wizard.",
        )
        return bytes(pdf.output(dest="S"))

    _draw_h2(pdf, "Your answers")

    inner_w = pdf.w - pdf.l_margin - pdf.r_margin
    pad = 4
    for i, qa in enumerate(answers, start=1):
        question = str(qa.get("question", "") or "").strip()
        answer = str(qa.get("answer", "") or "").strip()
        if not question and not answer:
            continue

        # Measure card height first (split_only) so we can draw the wash.
        pdf.set_font("Helvetica", "", 10)
        q_lines = pdf.multi_cell(
            inner_w - pad * 2, 5, _safe(question), split_only=True
        )
        pdf.set_font("Helvetica", "", 11)
        a_lines = pdf.multi_cell(
            inner_w - pad * 2, 5.5, _safe(answer), split_only=True
        )
        card_h = pad * 2 + 5 + max(len(q_lines), 1) * 5 + max(len(a_lines), 1) * 5.5 + 3

        # Auto page break check — jump if this card would spill.
        if pdf.get_y() + card_h > pdf.page_break_trigger:
            pdf.add_page()

        x, y = pdf.l_margin, pdf.get_y()
        pdf.set_fill_color(*_PURPLE_WASH)
        pdf.set_draw_color(*_PURPLE_ACCENT)
        pdf.set_line_width(0.2)
        pdf.rect(x, y, inner_w, card_h, style="DF")

        pdf.set_xy(x + pad, y + pad)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_PURPLE_ACCENT)
        pdf.cell(0, 4, _safe(f"Q{i}"), ln=1)

        pdf.set_x(x + pad)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_SLATE_MUTED)
        pdf.multi_cell(inner_w - pad * 2, 5, _safe(question))

        pdf.set_x(x + pad)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*_PURPLE_INK)
        pdf.multi_cell(inner_w - pad * 2, 5.5, _safe(answer))

        pdf.ln(3)

    return bytes(pdf.output(dest="S"))
