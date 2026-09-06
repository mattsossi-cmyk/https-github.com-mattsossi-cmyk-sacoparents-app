"""PDF renderer for the Activity Cost Ledger + Suggested Split.

Emits a single-page A4 summary of one parent's activity-cost ledger
alongside a neutral suggested split (50/50, income-weighted, or
custom-%). Intended as a hand-off artefact for mediators or attorneys
who want the numbers on paper without hunting through the app.

Non-adjudicative guardrails:
  * Every rendered value is a fact the caller already saw in-app.
  * Notes on the co-parent's rows are redacted upstream by the
    compare endpoint before the payload reaches this renderer.
  * The suggested split carries a captioned disclaimer stating that
    it is a suggestion — never an order.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, WARN, INFO, OK,
    ORG_NAME, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe,
)


PAGE_W = 210
LEFT_M = 12
RIGHT_M = 12
CONTENT_W = PAGE_W - LEFT_M - RIGHT_M

# Column widths for the ledger table (must sum to CONTENT_W = 186).
COL_ACTIVITY = 66
COL_CATEGORY = 34
COL_DATE = 26
COL_AMOUNT = 24
COL_NOTE = CONTENT_W - (COL_ACTIVITY + COL_CATEGORY + COL_DATE + COL_AMOUNT)


class _CostLedgerPDF(FPDF):
    def __init__(self, *, generated_at: str, self_name: str, coparent_name: Optional[str]):
        super().__init__()
        self._generated_at = generated_at
        self._self_name = self_name
        self._coparent_name = coparent_name

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        self.set_fill_color(*SAND)
        self.rect(0, 0, PAGE_W, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=3, w=16, h=16)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(32, 5)
        self.cell(0, 5, "Activity Cost Ledger & Suggested Split", ln=1)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_MID)
        self.set_x(32)
        self.cell(0, 4, f"{ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(26)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Prepared for mediator reference - Suggested split is not an order or court decision - "
            f"Generated {self._generated_at}",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


def _fmt_usd(cents: int) -> str:
    n = (cents or 0) / 100
    return f"${n:,.2f}"


def _fmt_pct(ratio: float) -> str:
    return f"{round(ratio * 100)}%"


def _draw_totals(pdf: _CostLedgerPDF, self_total: int, coparent_total: int, combined: int) -> None:
    y = pdf.get_y()
    box_w = (CONTENT_W - 6) / 3
    labels = [
        ("YOU", _fmt_usd(self_total), OK),
        ("CO-PARENT", _fmt_usd(coparent_total), INFO),
        ("COMBINED", _fmt_usd(combined), TEXT_DARK),
    ]
    for i, (lbl, val, color) in enumerate(labels):
        x = LEFT_M + i * (box_w + 3)
        pdf.set_xy(x, y)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*TEXT_MID)
        pdf.rect(x, y, box_w, 22, "DF")
        pdf.set_xy(x + 3, y + 2.5)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*color)
        pdf.cell(box_w - 6, 3.5, lbl, ln=1)
        pdf.set_xy(x + 3, y + 7)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(box_w - 6, 8, val, ln=1)
    pdf.set_y(y + 25)
    pdf.set_text_color(*TEXT_DARK)


def _draw_split(
    pdf: _CostLedgerPDF,
    *,
    mode: str,
    self_share_ratio: float,
    self_share_cents: int,
    coparent_share_cents: int,
    self_paid: int,
    coparent_name: str,
    self_income: Optional[int],
    coparent_income: Optional[int],
    custom_pct: Optional[int],
) -> None:
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 5, "Suggested split", ln=1)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_MID)

    mode_line = {
        "even": "50/50 even - each parent covers half of the combined total.",
        "income": (
            f"Income-weighted - your monthly income {_fmt_usd(self_income or 0)}, "
            f"{coparent_name}'s {_fmt_usd(coparent_income or 0)}."
        ),
        "custom": f"Custom - your share set to {custom_pct or 0}%.",
    }.get(mode, "50/50 even.")
    pdf.multi_cell(CONTENT_W, 4.2, mode_line)
    pdf.ln(1)

    balance = self_share_cents - self_paid
    abs_balance = abs(balance)
    if abs_balance < 100:
        head_txt = "You are roughly square."
        head_color = TEXT_DARK
    elif balance > 0:
        head_txt = f"You still owe {_fmt_usd(balance)}."
        head_color = WARN
    else:
        head_txt = f"{coparent_name} owes you {_fmt_usd(abs_balance)}."
        head_color = OK

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*head_color)
    pdf.cell(0, 5.5, head_txt, ln=1)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(
        CONTENT_W, 4.2,
        f"Your {_fmt_pct(self_share_ratio)} share is {_fmt_usd(self_share_cents)}. "
        f"{coparent_name}'s {_fmt_pct(1 - self_share_ratio)} share is {_fmt_usd(coparent_share_cents)}. "
        f"You have paid {_fmt_usd(self_paid)}.",
    )
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1)


def _draw_category_table(
    pdf: _CostLedgerPDF, per_category_pair: List[Dict[str, Any]]
) -> None:
    if not per_category_pair:
        return
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 5, "By category", ln=1)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(*SAND)
    pdf.set_text_color(*TEXT_MID)
    col_label_w = CONTENT_W - 60
    col_amount_w = 30
    pdf.cell(col_label_w, 5, "Category", border=0, fill=True)
    pdf.cell(col_amount_w, 5, "You", border=0, align="R", fill=True)
    pdf.cell(col_amount_w, 5, "Co-parent", border=0, align="R", fill=True, ln=1)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    for cat in per_category_pair:
        pdf.cell(col_label_w, 4.6, cat.get("label", cat.get("key", "")), border=0)
        pdf.cell(col_amount_w, 4.6, _fmt_usd(cat.get("self_cents", 0)), border=0, align="R")
        pdf.cell(col_amount_w, 4.6, _fmt_usd(cat.get("coparent_cents", 0)), border=0, align="R", ln=1)
    pdf.ln(1.5)


def _draw_ledger_header(pdf: _CostLedgerPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 5, title, ln=1)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(*SAND)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(COL_ACTIVITY, 5, "Activity", fill=True, border=0)
    pdf.cell(COL_CATEGORY, 5, "Category", fill=True, border=0)
    pdf.cell(COL_DATE, 5, "Date", fill=True, border=0)
    pdf.cell(COL_AMOUNT, 5, "Amount", fill=True, border=0, align="R")
    pdf.cell(COL_NOTE, 5, "Note", fill=True, border=0, ln=1)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*TEXT_DARK)


def _draw_ledger_rows(
    pdf: _CostLedgerPDF,
    rows: List[Dict[str, Any]],
    categories: Dict[str, str],
    *,
    max_rows: int,
    show_notes: bool,
) -> int:
    """Render up to `max_rows` and return how many were rendered."""
    if not rows:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*TEXT_MID)
        pdf.cell(0, 4.4, "No entries logged yet.", ln=1)
        pdf.set_text_color(*TEXT_DARK)
        return 0
    rendered = 0
    for r in rows[:max_rows]:
        cat_label = categories.get(r.get("category") or "other", r.get("category") or "other")
        note = (r.get("note") or "") if show_notes else "-"
        pdf.cell(COL_ACTIVITY, 4.4, (r.get("activity_label") or "")[:38], border=0)
        pdf.cell(COL_CATEGORY, 4.4, cat_label[:20], border=0)
        pdf.cell(COL_DATE, 4.4, r.get("incurred_on") or "", border=0)
        pdf.cell(COL_AMOUNT, 4.4, _fmt_usd(r.get("amount_cents", 0)), border=0, align="R")
        pdf.cell(COL_NOTE, 4.4, (note or "")[:44], border=0, ln=1)
        rendered += 1
    if len(rows) > max_rows:
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*TEXT_MID)
        pdf.cell(
            0, 3.8,
            f"+ {len(rows) - max_rows} more entries not shown - open the app for the full history.",
            ln=1,
        )
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1.5)
    return rendered


def _resolve_split_ratio(
    mode: str,
    self_income: Optional[int],
    coparent_income: Optional[int],
    custom_pct: Optional[int],
) -> tuple[str, float]:
    """Return the (normalised_mode, caller_share_ratio) tuple."""
    if mode == "income" and (self_income or 0) + (coparent_income or 0) > 0:
        return "income", (self_income or 0) / ((self_income or 0) + (coparent_income or 0))
    if mode == "custom" and custom_pct is not None:
        return "custom", max(0, min(100, int(custom_pct))) / 100
    return "even", 0.5


def _draw_meta_strip(pdf: _CostLedgerPDF, self_name: str, coparent_name: Optional[str]) -> None:
    """Render the small "Prepared for … | Co-parent: …" strip at the top."""
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_MID)
    parent_line = f"Prepared for: {self_name}"
    if coparent_name:
        parent_line += f"  |  Co-parent: {coparent_name}"
    pdf.multi_cell(CONTENT_W, 4.5, parent_line)
    pdf.ln(1)


def _draw_ledger_pair(
    pdf: _CostLedgerPDF,
    self_bundle: Dict[str, Any],
    coparent_bundle: Dict[str, Any],
    cat_lookup: Dict[str, str],
) -> None:
    """Render caller's ledger, then co-parent's (notes redacted)."""
    _draw_ledger_header(pdf, f"Your entries ({self_bundle.get('count', 0)})")
    _draw_ledger_rows(
        pdf,
        self_bundle.get("rows") or [],
        cat_lookup,
        max_rows=10,
        show_notes=True,
    )
    if coparent_bundle.get("rows"):
        _draw_ledger_header(pdf, f"Co-parent entries ({coparent_bundle.get('count', 0)})")
        _draw_ledger_rows(
            pdf,
            coparent_bundle.get("rows") or [],
            cat_lookup,
            max_rows=10,
            show_notes=False,
        )


def build_cost_ledger_pdf(
    *,
    compare_payload: Dict[str, Any],
    self_name: str,
    coparent_name: Optional[str],
    mode: str = "even",
    self_income: Optional[int] = None,
    coparent_income: Optional[int] = None,
    custom_pct: Optional[int] = None,
    categories: Optional[List[Dict[str, str]]] = None,
) -> bytes:
    """
    Build the one-page PDF from a `/activities-costs/compare` payload
    plus a caller-selected split mode.

    The compare payload is trusted — notes on the co-parent's rows are
    already redacted upstream. The renderer does not fetch anything new
    from the database.
    """
    self_bundle = compare_payload.get("self") or {}
    coparent_bundle = compare_payload.get("coparent") or {}
    combined = int(compare_payload.get("combined_total_cents") or 0)
    self_total = int(self_bundle.get("total_cents") or 0)
    coparent_total = int(coparent_bundle.get("total_cents") or 0)
    per_category_pair = compare_payload.get("per_category_pair") or []

    resolved_mode, ratio = _resolve_split_ratio(mode, self_income, coparent_income, custom_pct)
    self_share_cents = round(combined * ratio)
    coparent_share_cents = combined - self_share_cents

    cat_lookup: Dict[str, str] = {c["key"]: c["label"] for c in (categories or [])}

    pdf = _CostLedgerPDF(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        self_name=self_name,
        coparent_name=coparent_name,
    )
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_left_margin(LEFT_M)
    pdf.set_right_margin(RIGHT_M)

    _draw_meta_strip(pdf, self_name, coparent_name)
    _draw_totals(pdf, self_total, coparent_total, combined)
    _draw_split(
        pdf,
        mode=resolved_mode,
        self_share_ratio=ratio,
        self_share_cents=self_share_cents,
        coparent_share_cents=coparent_share_cents,
        self_paid=self_total,
        coparent_name=coparent_name or "Co-parent",
        self_income=self_income,
        coparent_income=coparent_income,
        custom_pct=custom_pct,
    )
    _draw_category_table(pdf, per_category_pair)
    _draw_ledger_pair(pdf, self_bundle, coparent_bundle, cat_lookup)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
