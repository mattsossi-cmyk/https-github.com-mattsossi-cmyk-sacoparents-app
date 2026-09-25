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
