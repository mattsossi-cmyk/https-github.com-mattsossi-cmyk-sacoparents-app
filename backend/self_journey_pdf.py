"""Self Journey summary PDF (7 sections), the parent's own copy.

Never printed here: the safety pick, or the private Situation / Co-parenting / Mediation notes (status only).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from self_assessment_pdf import _safe

try:
    from pdf_copyright import render_pdf_copyright  # type: ignore
except Exception:  # pragma: no cover
    def render_pdf_copyright(_pdf):
        return

PURPLE = (91, 63, 160)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
LAVENDER = (243, 239, 254)
DISCLAIMER = "Private to you. General guidance only, not legal, medical or psychological advice."

APPROACHES = {"cooperative": "Working together", "parallel": "Parallel parenting", "unsure": "Not sure yet"}
CHILD_AREAS = {
    "educational": "Educational needs",
    "medical": "Medical needs",
    "emotional": "Emotional & psychological needs",
    "developmental": "Developmental & special needs",
}
MEDIATION_OPTIONS = [
    "Child-focused mediation with a qualified family mediator.",
    "Separate-room (shuttle) or online mediation, where you never have to sit together.",
    "Attorney-assisted negotiation.",
    "Ask a professional which option fits your family before you agree to one.",
]
RESOURCES = [
    "In immediate danger: call 911.",
    "National Domestic Violence Hotline: 1-800-799-7233 or text START to 88788.",
    "Family Violence Prevention Services (San Antonio, 24/7): 210-733-8810.",
    "Bexar County Family Justice Center: 210-631-0100.",
    "PEACE Initiative (San Antonio): 210-533-2729.",
]
NEXT_STEPS = [
    "Bring this summary to your mediator, attorney or counselor.",
    "Revisit your Self-Assessment in a few weeks to see how things have changed.",
]
PRIVATE_NOTE = "Your notes for this step stay private on your screen and are not included in this PDF."


class _SJPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PURPLE)
        self.cell(0, 6, _safe("SA CoParents  ·  Self Journey Summary"), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(216, 199, 251)
        self.line(self.l_margin, self.get_y() + 1.5, self.w - self.r_margin, self.get_y() + 1.5)
        self.ln(5)

    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, _safe(f"{DISCLAIMER}   Page {self.page_no()}"), align="C")
        render_pdf_copyright(self)


def _date(iso: Optional[str]) -> str:
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    except (TypeError, ValueError):
        return ""


def _filled(d: Dict[str, Any]) -> bool:
    return any(isinstance(v, str) and v.strip() for v in (d or {}).values())


def _section(pdf: _SJPDF, n: int, title: str, lines: List[str], status: str = "", bullets: bool = True) -> None:
    if pdf.get_y() > 230:
        pdf.add_page()
    pdf.set_fill_color(*PURPLE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 7.5, _safe(f"  {n}. {title}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(*LAVENDER)
    if status:
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.multi_cell(pdf.epw, 5.4, _safe(status), fill=True, padding=(2.5, 3, 0, 3), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    body = "\n".join(f"- {line}" if bullets else line for line in lines) if lines else " "
    pdf.multi_cell(pdf.epw, 5.2, _safe(body), fill=True, padding=(2, 3, 2.5, 3), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def build_self_journey_pdf(
    *, progress: Dict[str, Any], sa_entries: List[Dict[str, Any]], cp_report_at: Optional[str], parent_name: str = ""
) -> bytes:
    pdf = _SJPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 10, _safe("Your SA CoParents Self Journey"), new_x="LMARGIN", new_y="NEXT")
    now = datetime.now(timezone.utc)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    who = f" for {parent_name}" if parent_name else ""
    pdf.cell(0, 6, _safe(f"Prepared{who} on {now.strftime('%B')} {now.day}, {now.year}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    situation = progress.get("situation") or {}
    _section(pdf, 1, "Parenting Situation Overview", [PRIVATE_NOTE], "Completed" if _filled(situation) else "Not started")

    sa_lines = [
        f"{_date(e.get('completed_at'))}" + (f": goal - {e['goal'].strip()}" if (e.get("goal") or "").strip() else "")
        for e in sa_entries
    ]
    _section(pdf, 2, "Self Assessment Reflections", sa_lines,
             f"{len(sa_entries)} dated reflection(s)" if sa_entries else "Not started")

    cp = progress.get("coparenting") or {}
    cp_lines = [f"Approach you chose: {APPROACHES[cp['approach']]}"] if cp.get("approach") in APPROACHES else []
    cp_lines.append(f"Co-Parenting Assessment completed {_date(cp_report_at)}" if cp_report_at else "Co-Parenting Assessment not completed yet")
    _section(pdf, 3, "Co-Parenting Relationship", cp_lines)

    opened = [CHILD_AREAS[k] for k in (progress.get("childNeeds") or {}).get("opened", []) if k in CHILD_AREAS]
    _section(pdf, 4, "Child's Identified Needs", opened, f"{len(opened)} area(s) explored" if opened else "Not started")

    fd = progress.get("foundation") or {}
    approved = bool(fd.get("approved")) and (fd.get("draft") or "").strip()
    _section(pdf, 5, "Foundation Statement", [fd["draft"].strip()] if approved else [],
             f"Approved by you on {_date(fd.get('approvedAt'))}" if approved else "Not approved yet", bullets=False)

    mediation = progress.get("mediation") or {}
    _section(pdf, 6, "Mediation Preparation & Options", [PRIVATE_NOTE, *MEDIATION_OPTIONS],
             "Completed" if _filled(mediation) else "Not started")

    _section(pdf, 7, "Next Steps & Available Resources", [*NEXT_STEPS, *RESOURCES])
    return bytes(pdf.output())
