"""PDF renderer for the v2 Special Needs Coordination Report (6 parts).

Matches the FPDF pattern used by pdf_service.build_summary_pdf. Ships one
downloadable document with:

    1. Child Profile
    2. Areas of Parent Agreement
    3. Coordination Gaps
    4. Priority Levels (Immediate / 30-day / Longer-term)
    5. Recommended Co-Parenting Structure
    6. Special Needs Parenting Plan Worksheet (action-plan table)
"""

from io import BytesIO
from typing import Any, Dict, List

from fpdf import FPDF


class _SNReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 18, 15)
        self.alias_nb_pages()

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(61, 26, 120)  # brand purple
        self.cell(0, 6, "SA CoParents  ·  Special Needs Coordination Report", ln=1)
        self.set_draw_color(220, 214, 232)
        self.line(15, 26, 195, 26)
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(133, 126, 156)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}  ·  Planning tool, not clinical or legal advice.", align="C")

    def h1(self, text: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(26, 19, 48)
        self.multi_cell(0, 8, _safe(text))
        self.ln(2)

    def h2(self, text: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(61, 26, 120)
        self.multi_cell(0, 7, _safe(text))
        self.ln(1)

    def body(self, text: str):
        if not text:
            return
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(52, 46, 78)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 5.4, _safe(text))
        self.ln(1)

    def bullets(self, items: List[str]):
        if not items:
            return
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(52, 46, 78)
        for it in items:
            if not str(it).strip():
                continue
            # Force full page width — avoids "not enough horizontal space"
            # when the cursor is left at odd x by a prior cell.
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 5.4, f"  - {_safe(str(it).strip())}")
        self.ln(1)


def _safe(text) -> str:
    """FPDF classic core fonts only support latin-1. Fall back gracefully."""
    if text is None:
        return ""
    s = str(text)
    # Normalise the common typographic characters an LLM tends to emit
    # (em/en dash, curly quotes, ellipsis) to their latin-1 equivalents so
    # the reader doesn't see "?" placeholders where "—" belonged.
    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2212": "-",   # minus
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "-",   # bullet
        "\u00a0": " ",   # nbsp — safe but be explicit
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _bullets_from(items) -> List[str]:
    if not items:
        return []
    if isinstance(items, str):
        return [items]
    return [_safe(i) for i in items]


def _obj_bullets(items, title_key, detail_key) -> List[str]:
    out = []
    for it in items or []:
        if isinstance(it, dict):
            title = _safe(it.get(title_key) or "").strip()
            detail = _safe(it.get(detail_key) or "").strip()
            if title and detail:
                out.append(f"{title} — {detail}")
            elif title or detail:
                out.append(title or detail)
        else:
            out.append(_safe(it))
    return out


def build_special_needs_pdf(
    *,
    user_name: str,
    child_name: str,
    report: Dict[str, Any],
    excluded_sections: set | list | None = None,
) -> bytes:
    """Compose the 6-part care plan as a PDF."""
    ex = set(excluded_sections or [])
    pdf = _SNReportPDF()
    pdf.add_page()

    pdf.h1(_safe(f"Care plan for {child_name or 'your child'}"))
    if user_name:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(133, 126, 156)
        pdf.multi_cell(0, 5, _safe(f"Prepared by {user_name}"))
        pdf.ln(2)

    # 1. Child Profile
    if "child_profile" not in ex:
        profile = report.get("child_profile") or {}
        pdf.h2("1. Child profile")
        pdf.body(_safe(profile.get("summary")))
        if profile.get("strengths"):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(26, 19, 48)
            pdf.cell(0, 6, "Strengths & interests", ln=1)
            pdf.bullets(_bullets_from(profile.get("strengths")))
        if profile.get("what_helps"):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(26, 19, 48)
            pdf.cell(0, 6, "What helps this child feel safe and successful", ln=1)
            pdf.bullets(_bullets_from(profile.get("what_helps")))
        if profile.get("support_needs"):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(26, 19, 48)
            pdf.cell(0, 6, "Support needs (documented, under evaluation, or observed)", ln=1)
            pdf.bullets(_bullets_from(profile.get("support_needs")))

    # 2. Areas of Parent Agreement
    if "agreement_areas" not in ex:
        pdf.h2("2. Areas of parent agreement")
        agreements = _obj_bullets(report.get("agreement_areas"), "title", "detail")
        if agreements:
            pdf.bullets(agreements)
        else:
            pdf.body("No agreement areas surfaced yet — a good place to start the conversation.")

    # 3. Coordination Gaps
    if "coordination_gaps" not in ex:
        pdf.h2("3. Coordination gaps")
        gaps = _obj_bullets(report.get("coordination_gaps"), "title", "detail")
        if gaps:
            pdf.bullets(gaps)
        else:
            pdf.body("No major gaps flagged.")

    # 4. Priority Levels
    if "priorities" not in ex:
        priorities = report.get("priorities") or {}
        pdf.h2("4. Priority levels")
        for label, key in (
            ("Immediate", "immediate"),
            ("Within 30 days", "thirty_day"),
            ("Longer-term", "longer_term"),
        ):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(26, 19, 48)
            pdf.cell(0, 6, label, ln=1)
            items = _bullets_from(priorities.get(key))
            if items:
                pdf.bullets(items)
            else:
                pdf.body("- (none flagged)")

    # 5. Recommended Structure
    if "structure" not in ex:
        pdf.h2("5. Recommended co-parenting structure")
        pdf.body(_safe(report.get("structure_reasoning")))

    # 6. Safeguards & disagreement pathway (Phase D)
    if "safeguards_pathway" not in ex:
        pw = report.get("safeguards_pathway") or {}
        if pw:
            pdf.h2("6. Safeguards & disagreement pathway")
            tier = pw.get("tier") or {}
            sg = pw.get("safeguards") or {}
            disagree = pw.get("disagreement") or {}
            actions = pw.get("actions") or []

            def _reset_x():
                pdf.set_x(pdf.l_margin)

            # Tier callout
            if tier.get("label"):
                _reset_x()
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(61, 26, 120)
                pdf.multi_cell(pdf.epw, 6, _safe(tier["label"]))
                _reset_x()
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(52, 46, 78)
                pdf.multi_cell(pdf.epw, 5, _safe(tier.get("summary", "")))
                pdf.ln(2)

            # Safeguards snapshot
            if sg:
                overall = sg.get("overall_score")
                if overall is not None:
                    _reset_x()
                    pdf.set_font("Helvetica", "B", 10.5)
                    pdf.set_text_color(26, 19, 48)
                    pdf.multi_cell(pdf.epw, 6, _safe(f"Safeguards score: {overall} / 100"))
                for label, items in (
                    ("In place", sg.get("in_place") or []),
                    ("Partial", sg.get("partial") or []),
                    ("Not yet in place", sg.get("missing") or []),
                ):
                    if not items:
                        continue
                    _reset_x()
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.set_text_color(61, 26, 120)
                    pdf.multi_cell(pdf.epw, 5.5, _safe(label))
                    pdf.bullets([_safe(it.get("label") or "") for it in items])

            # Disagreement index
            if disagree:
                _reset_x()
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(61, 26, 120)
                pdf.multi_cell(pdf.epw, 5.5, _safe(f"Disagreement index: {disagree.get('index', 0)} / 10"))
                cr = disagree.get("concern_response") or ""
                if cr:
                    _reset_x()
                    pdf.set_font("Helvetica", "", 9.5)
                    pdf.set_text_color(52, 46, 78)
                    pdf.multi_cell(pdf.epw, 4.5, _safe(f"Your response to concerns: {cr}"))
                    pdf.ln(1)

            # Actions
            if actions:
                _reset_x()
                pdf.set_font("Helvetica", "B", 10.5)
                pdf.set_text_color(26, 19, 48)
                pdf.multi_cell(pdf.epw, 6, "Recommended next steps")
                for a in actions:
                    title = _safe(a.get("title", ""))
                    when = _safe(a.get("when", ""))
                    detail = _safe(a.get("detail", ""))
                    _reset_x()
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.set_text_color(61, 26, 120)
                    if when:
                        pdf.multi_cell(pdf.epw, 5, f"- {title}  ({when})")
                    else:
                        pdf.multi_cell(pdf.epw, 5, f"- {title}")
                    if detail:
                        _reset_x()
                        pdf.set_font("Helvetica", "", 9.5)
                        pdf.set_text_color(52, 46, 78)
                        pdf.multi_cell(pdf.epw, 4.5, f"  {detail}")
                    pdf.ln(0.5)

    # 7. Action Plan (worksheet)
    if "action_plan" not in ex:
        pdf.h2("7. Special Needs Parenting Plan worksheet")
        rows = report.get("action_plan") or []
        if rows:
            # Table header
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_fill_color(239, 233, 249)
            pdf.set_text_color(61, 26, 120)
            col_widths = [38, 52, 30, 32, 28]
            headers = ["Child's need", "Agreed action", "Responsible", "Info shared by", "Review date"]
            for w, h in zip(col_widths, headers):
                pdf.cell(w, 6.5, h, border=0, fill=True)
            pdf.ln(6.5)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(52, 46, 78)
            for r in rows:
                def _clip(text, max_len):
                    # Break unusually long unbroken tokens (URLs, emails) so
                    # multi_cell always has a word-break option in narrow cells.
                    t = _safe(text)
                    out = []
                    for word in t.split(" "):
                        if len(word) > max_len:
                            for i in range(0, len(word), max_len):
                                out.append(word[i:i + max_len])
                        else:
                            out.append(word)
                    return " ".join(out) if out else ""

                values = [
                    _clip(r.get("need") or "", 22),
                    _clip(r.get("action") or "", 32),
                    _clip(r.get("responsible") or "", 18),
                    _clip(r.get("channel") or "", 20),
                    _clip(r.get("review") or "", 18),
                ]
                # Compute row height as the max of multi_cell heights.
                heights = []
                for w, v in zip(col_widths, values):
                    lines = pdf.multi_cell(w, 4.2, v or " ", split_only=True)
                    heights.append(max(1, len(lines)) * 4.2)
                row_h = max(heights) + 1
                # Break-page guard.
                if pdf.get_y() + row_h > pdf.h - 20:
                    pdf.add_page()
                x0 = pdf.get_x()
                y0 = pdf.get_y()
                for w, v in zip(col_widths, values):
                    x = pdf.get_x()
                    y = pdf.get_y()
                    pdf.rect(x, y, w, row_h)
                    pdf.multi_cell(w, 4.2, v or " ")
                    pdf.set_xy(x + w, y0)
                pdf.set_xy(x0, y0 + row_h)
        else:
            pdf.body("(No action rows yet — regenerate the report once more answers are in.)")

    # Disclaimer footer
    pdf.ln(3)
    pdf.set_draw_color(220, 214, 232)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(133, 126, 156)
    pdf.multi_cell(0, 4.5, _safe(report.get("disclaimer") or ""))

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
