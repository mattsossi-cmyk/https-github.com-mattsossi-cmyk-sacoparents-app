"""Individual Perspective Reports — ONE frozen packet, TWO separate per-parent sections (owner design 2026-10-12).

Each section: neutral cover, that parent's screening receipt line, that parent's perspective areas (provided / not provided by topic — never the
answer text), and the assigned professional's observations. Never: raw answers, narratives, locations, safe-contact data, pathway reasons,
Version C as LGBTQ+, the other parent's material, or any reason the individual format was chosen.
"""
from datetime import datetime, timezone

from joint_data import QUESTIONS
from pdf_common import FONT, GRAY, PURPLE, _new_pdf, _s
from safety_pathway import public_pathway
from safety_screening import receipt

PACKET_LABEL = "Individual Perspective Reports"
FILENAME_STEM = "court-packet"  # neutral; never reveals the format or any reason


def _areas_for(doc: dict, role: str) -> list[tuple[str, str]]:
    """Professional's one-line neutral summary per topic when written; otherwise provided / not provided. Never the parent's text."""
    answers = ((doc.get("responses") or {}).get(role) or {}).get("answers") or {}
    summaries = ((doc.get("individual_summaries") or {}).get(role) or {})
    out = []
    for key, area, _q in QUESTIONS:
        s = str(summaries.get(key) or "").strip()
        out.append((area, s or ("Perspective provided" if str(answers.get(key) or "").strip() else "Not provided")))
    return out


def _observations(doc: dict) -> str:
    st = doc.get("professional_statement") or {}
    return str(st.get("observations") or "").strip() or "No professional observations recorded."


def _section(pdf, doc: dict, role: str, pro: dict, now: str) -> None:
    p = (doc.get("participants") or {}).get(role) or {}
    label = f"Parent {role.upper()}"
    name = p.get("name") or label
    pdf.add_page()
    pdf.set_text_color(*PURPLE); pdf.set_font(FONT, "B", 20); pdf.cell(pdf.epw, 12, _s(PACKET_LABEL), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 15); pdf.cell(pdf.epw, 10, _s(f"Individual Perspective Report — {name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*GRAY); pdf.set_font(FONT, "", 10)
    pdf.cell(pdf.epw, 7, _s(f"Case {doc.get('case_code') or ''} · Prepared {now} by {pro.get('name') or 'the assigned professional'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 6, _s("This report presents one parent's participation and perspective areas only. It does not quote, compare with, or reference the other parent. "
                            "An assessment is not a finding; a professional report is not a court determination."))
    pdf.ln(3)
    pdf.set_text_color(0, 0, 0); pdf.set_font(FONT, "B", 12); pdf.cell(pdf.epw, 9, _s("1. Screening status"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 10.5); pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 6, _s(receipt((doc.get("safety_screenings") or {}).get(role), label, (doc.get("safety_declined") or {}).get(role))))
    pw = public_pathway(doc)
    if pw and pw.get("label"):
        pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 6, _s(f"Communication pathway (confirmed by the professional): {pw['label']}"))
    pdf.ln(2)
    pdf.set_font(FONT, "B", 12); pdf.cell(pdf.epw, 9, _s("2. Perspective areas"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 10.5)
    for area, status in _areas_for(doc, role):
        pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 6.5, _s(f"• {area}: {status}"))
    pdf.ln(2)
    pdf.set_font(FONT, "B", 12); pdf.cell(pdf.epw, 9, _s("3. Professional observations"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 10.5); pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 6, _s(_observations(doc)))


def build_individual_reports_pdf(doc: dict, pro: dict) -> bytes:
    pdf = _new_pdf()
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    for role in ("a", "b"):
        _section(pdf, doc, role, pro, now)
    return bytes(pdf.output())
