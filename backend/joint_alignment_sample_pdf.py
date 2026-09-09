"""Joint Alignment Sample PDF — a printable, sharable version of the
public sample preview at `/samples/joint-alignment-preview`.

Purpose (Iter183): parents landing on the sample page asked for a
version they can *email their co-parent* before signing up. This
module renders the SAME six fictional topics + count summary the
React page shows, in a single-page US-Letter PDF so it forwards
cleanly as an attachment.

Design constraints:
  * FICTION MARKER on every page — the page header and a footer
    watermark explicitly say "Sample - Not real case data". A
    marketing PDF landing in a mediator's inbox with the wrong
    context would be worse than no PDF at all.
  * SAMPLE_TOPICS / SAMPLE_META live inside this module so the PDF
    is not coupled to the frontend build. The React sample page
    holds its own copy — the two are intentionally kept in lockstep
    manually because the data is fictional and stable.
  * Reuses `pdf_base.render_pdf_copyright` so the sacoparentsalign.com
    footer is present on every page (identical to every other
    report the platform emits).
  * Latin-1 safe via the existing `_safe(...)` helper. Never crash
    on a smart quote.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from fpdf import FPDF

from pdf_base import _safe, render_pdf_copyright


# Sample data — MUST mirror the React sample page. Six neutral topics.
SAMPLE_META: Dict[str, object] = {
    "parents": ["Alex", "Sam"],
    "child": {"name": "Rian", "age": 8},
}

SAMPLE_TOPICS: List[Dict[str, str]] = [
    {
        "title": "School morning routines",
        "section": "Weekday transitions",
        "status": "agree",
        "note": "Both parents landed on the same wake / drop-off pattern.",
    },
    {
        "title": "Screen time on weeknights",
        "section": "Daily rhythms",
        "status": "agree",
        "note": "Same limit, same house rule.",
    },
    {
        "title": "Extracurricular activities",
        "section": "Weekly commitments",
        "status": "differ",
        "note": (
            "One parent wants a lighter schedule; worth talking about."
        ),
    },
    {
        "title": "Handover timing on Fridays",
        "section": "Transitions",
        "status": "differ",
        "note": (
            "Different preferred times - a small change to your plan "
            "may resolve this."
        ),
    },
    {
        "title": "Winter holidays",
        "section": "Special occasions",
        "status": "agree",
        "note": "Same view on how to split the school break.",
    },
    {
        "title": "Healthcare decisions",
        "section": "Big-picture parenting",
        "status": "incomplete",
        "note": (
            "One of you didn't finish this section yet - mark it not done."
        ),
    },
]

_STATUS_LABELS = {
    "agree": "You agree",
    "differ": "You differ",
    "incomplete": "Not both completed",
}

# Muted brand palette — matches the React page's Tailwind classes.
_STATUS_COLORS = {
    # (fill_r, fill_g, fill_b, text_r, text_g, text_b)
    "agree":      ((225, 243, 232), (24, 97, 66)),      # #E1F3E8 / #186142
    "differ":     ((255, 246, 229), (138, 91, 0)),      # #FFF6E5 / #8A5B00
    "incomplete": ((241, 238, 244), (92, 84, 113)),     # #F1EEF4 / #5C5471
}


def _summary_counts() -> Dict[str, int]:
    counts = {"agreed": 0, "differed": 0, "incomplete": 0}
    for t in SAMPLE_TOPICS:
        s = t["status"]
        if s == "agree":
            counts["agreed"] += 1
        elif s == "differ":
            counts["differed"] += 1
        else:
            counts["incomplete"] += 1
    return counts


class _SamplePreviewPDF(FPDF):
    """Adds a persistent "Sample - Not real case data" ribbon in the
    header and the standard global copyright footer."""

    def header(self) -> None:  # noqa: D401 - fpdf hook
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(61, 26, 120)  # #3D1A78
        self.cell(0, 6, _safe("SA CoParents - Sample Joint Alignment Preview"), ln=0)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(184, 91, 0)  # #B85B00
        self.cell(
            0,
            6,
            _safe("SAMPLE - fictional data, not a real case"),
            align="R",
            ln=1,
        )
        self.set_text_color(0, 0, 0)
        # Thin brand divider under the header row.
        self.set_draw_color(220, 214, 232)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(4)

    def footer(self) -> None:  # noqa: D401 - fpdf hook
        # Small "fictional data" reminder above the global copyright
        # so a printed page never loses the context.
        try:
            self.set_y(-11)
            self.set_font("Helvetica", "I", 6.5)
            self.set_text_color(133, 126, 156)
            self.cell(
                0,
                3,
                _safe(
                    "This is a fictional sample. Your real preview is "
                    "generated privately from your own reflections."
                ),
                align="C",
                ln=1,
            )
        except Exception:  # noqa: BLE001 — footer must never crash
            pass
        render_pdf_copyright(self)


def _pill(pdf: FPDF, label: str, status: str) -> None:
    """Render a status pill (rounded-ish rectangle with tinted fill +
    coloured label). Advances the cursor to the right of the pill."""
    fill, ink = _STATUS_COLORS.get(status, ((240, 240, 240), (50, 50, 50)))
    pdf.set_fill_color(*fill)
    pdf.set_text_color(*ink)
    pdf.set_font("Helvetica", "B", 8)
    text = _safe(_STATUS_LABELS[status])
    w = pdf.get_string_width(text) + 6
    x, y = pdf.get_x(), pdf.get_y()
    pdf.rect(x, y, w, 5.5, style="F")
    pdf.set_xy(x + 3, y + 1)
    pdf.cell(w - 6, 3.5, text, ln=0)
    pdf.set_xy(x + w + 2, y)
    pdf.set_text_color(0, 0, 0)


def _count_card(pdf: FPDF, x: float, y: float, w: float, count: int, label: str, status: str) -> None:
    """Draw a compact 'count pill' matching the React page's colour
    coding for agreed / differed / incomplete summary counts."""
    fill, ink = _STATUS_COLORS[status]
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*ink)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, w, 16, style="FD")
    pdf.set_xy(x + 4, y + 2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*ink)
    pdf.cell(w - 8, 7, str(count), ln=0)
    pdf.set_xy(x + 4, y + 10)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(w - 8, 4, _safe(label.upper()), ln=0)
    pdf.set_text_color(0, 0, 0)


def build_joint_alignment_sample_pdf() -> bytes:
    """Return the sample preview as PDF bytes. Fixed content — safe
    to serve to every visitor and cache aggressively."""
    pdf = _SamplePreviewPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    pdf.add_page()

    # Sample banner (matches the purple bar on the web page).
    pdf.set_fill_color(61, 26, 120)  # #3D1A78
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    parents = " & ".join(SAMPLE_META["parents"])  # type: ignore[arg-type]
    child = SAMPLE_META["child"]  # type: ignore[assignment]
    banner = (
        f"SAMPLE - Not real case data. {parents} with child "
        f"{child['name']} (fictional)"  # type: ignore[index]
    )
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin, 8, style="F")
    pdf.set_xy(pdf.l_margin + 3, pdf.get_y() + 2)
    pdf.cell(0, 4, _safe(banner))
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)

    # Title.
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(26, 19, 48)  # #1A1330
    pdf.multi_cell(0, 8, _safe("A quick look at where two co-parents land"))
    pdf.ln(1)

    # Intro paragraph.
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(75, 69, 103)  # #4B4567
    pdf.multi_cell(
        0,
        4.6,
        _safe(
            "This is a fictional example of the private preview both "
            "parents see after independently completing their reflections. "
            "You only see whether each topic reads as an agree, a differ, "
            "or a section one of you didn't finish. Neither parent's "
            "actual answers are visible on this page."
        ),
    )
    pdf.ln(2)

    # Privacy reassurance card.
    pdf.set_fill_color(245, 241, 251)  # #F5F1FB
    pdf.set_draw_color(214, 207, 232)
    pdf.set_line_width(0.2)
    box_x, box_y = pdf.l_margin, pdf.get_y()
    box_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.rect(box_x, box_y, box_w, 18, style="FD")
    pdf.set_xy(box_x + 4, box_y + 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 4, _safe("Your real preview is never shared publicly"), ln=1)
    pdf.set_xy(box_x + 4, box_y + 7)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(
        box_w - 8,
        3.6,
        _safe(
            "In the live product, this exact layout is generated only for "
            "the two parents on a case. Releasing the full Joint Alignment "
            "Report to a named professional is a separate action that "
            "requires both of you to record release consent."
        ),
    )
    pdf.set_y(box_y + 20)
    pdf.ln(2)

    # Summary counts.
    counts = _summary_counts()
    counts_row_y = pdf.get_y()
    total_w = pdf.w - pdf.l_margin - pdf.r_margin
    gap = 3
    each_w = (total_w - 2 * gap) / 3
    _count_card(pdf, pdf.l_margin, counts_row_y, each_w, counts["agreed"], "Agreed", "agree")
    _count_card(pdf, pdf.l_margin + each_w + gap, counts_row_y, each_w, counts["differed"], "Differed", "differ")
    _count_card(pdf, pdf.l_margin + 2 * (each_w + gap), counts_row_y, each_w, counts["incomplete"], "Incomplete", "incomplete")
    pdf.set_y(counts_row_y + 20)

    # Topic-by-topic header strip.
    pdf.set_fill_color(250, 248, 253)  # #FAF8FD
    pdf.set_draw_color(238, 232, 247)
    strip_y = pdf.get_y()
    pdf.rect(pdf.l_margin, strip_y, box_w, 7, style="FD")
    pdf.set_xy(pdf.l_margin + 3, strip_y + 1.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 4, _safe("TOPIC-BY-TOPIC"))
    pdf.set_y(strip_y + 8)

    # Topics.
    for topic in SAMPLE_TOPICS:
        row_y = pdf.get_y()
        # Row background outline.
        pdf.set_draw_color(238, 232, 247)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, row_y, pdf.w - pdf.r_margin, row_y)
        pdf.ln(1.2)

        # Status pill left, title/note right.
        pill_x = pdf.l_margin
        pill_y = pdf.get_y()
        pdf.set_xy(pill_x, pill_y)
        _pill(pdf, topic["title"], topic["status"])

        # Title (bold) on the same line, offset to sit after the pill.
        pdf.set_xy(pill_x + 32, pill_y - 0.2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 19, 48)
        pdf.cell(0, 5, _safe(topic["title"]), ln=1)

        # Section label (uppercase, small).
        pdf.set_x(pill_x + 32)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(133, 126, 156)
        pdf.cell(0, 3.5, _safe(topic["section"].upper()), ln=1)

        # Note body.
        pdf.set_x(pill_x + 32)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 69, 103)
        pdf.multi_cell(box_w - 32, 4, _safe(topic["note"]))
        pdf.ln(1.5)

    # Bottom CTA block.
    pdf.ln(3)
    cta_y = pdf.get_y()
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(214, 207, 232)
    pdf.set_line_width(0.4)
    pdf.rect(pdf.l_margin, cta_y, box_w, 22, style="FD")
    pdf.set_xy(pdf.l_margin + 4, cta_y + 2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(26, 19, 48)
    pdf.cell(0, 5, _safe("Ready to build yours?"), ln=1)
    pdf.set_xy(pdf.l_margin + 4, cta_y + 8)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(
        box_w - 8,
        4,
        _safe(
            "Start on your own at sacoparentsapp.online, or - if your "
            "co-parent already sent you a code - use the 'I have an "
            "invitation' path. Both routes end at the private preview "
            "shown above once both of you complete your reflections."
        ),
    )
    # Clickable link overlay for the two hyperlinks in the text — small
    # and best-effort.
    pdf.link(
        pdf.l_margin + 30, cta_y + 8, 55, 4, "https://sacoparentsapp.online",
    )

    # Sticky "Generated on" line above the copyright footer.
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(133, 126, 156)
    pdf.cell(
        0,
        3,
        _safe(
            "Generated on "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d")
            + " - The people, child, and topics on this page are fictional."
        ),
        ln=1,
    )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", errors="replace")
    return bytes(out)
