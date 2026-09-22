from pathlib import Path
from datetime import datetime as _dt, timezone as _tz
from io import BytesIO

import qrcode
from fpdf import FPDF
from fpdf.fonts import FontFace

_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_UNICODE_FONTS = all((_FONT_DIR / f).exists() for f in (
    "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf",
))
FONT = "dejavu" if _UNICODE_FONTS else "helvetica"

PURPLE = (91, 42, 134)
TEAL = (37, 161, 154)
GRAY = (110, 100, 120)
GREEN = (102, 139, 105)
BLUE = (96, 150, 186)
YELLOW = (180, 150, 60)
DARK = (30, 25, 40)
BODY = (60, 55, 70)

_REPLACEMENTS = [
    ("—", "-"), ("–", "-"), ("'", "'"), ("'", "'"),
    ('"', '"'), ('"', '"'), ("…", "..."), ("✓", "[x]"), ("•", "-"), ("≠", "!="),
]


def _s(text) -> str:
    if _UNICODE_FONTS:
        return str(text)
    t = str(text)
    for a, b in _REPLACEMENTS:
        t = t.replace(a, b)
    return t.encode("latin-1", "replace").decode("latin-1")


class _JointPDF(FPDF):
    watermark_text: str | None = None
    footer_meta: str = ""

    def footer(self):
        if self.watermark_text:
            self.set_font(FONT, "B", 52)
            self.set_text_color(235, 230, 242)
            with self.rotation(40, self.w / 2, self.h / 2):
                self.text(self.w / 2 - 68, self.h / 2, self.watermark_text)
        self.set_y(-18 if self.footer_meta else -14)
        self.set_font(FONT, "I", 8)
        self.set_text_color(*GRAY)
        if self.footer_meta:
            self.cell(0, 4, _s(self.footer_meta), align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, _s(f"© 2026 sacoparentsalign.com · SA CoParents Align. All rights reserved. · Page {self.page_no()}"), align="C")


def verify_qr_png(url: str) -> bytes:
    img = qrcode.make(url, box_size=6, border=1)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _verify_qr_block(pdf: FPDF, verify: dict) -> None:
    size = 22
    x = pdf.w - pdf.r_margin - size
    y = pdf.t_margin
    pdf.image(BytesIO(verify_qr_png(verify["url"])), x=x, y=y, w=size, h=size)
    pdf.set_xy(x - 2, y + size + 0.5)
    pdf.set_font(FONT, "", 6.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(size + 4, 3, "Scan to verify", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(x - 2, y + size + 3.5)
    pdf.cell(size + 4, 3, _s(verify["case_code"]), align="C")
    pdf.set_xy(pdf.l_margin, pdf.t_margin)


def _new_pdf() -> FPDF:
    pdf = _JointPDF()
    if _UNICODE_FONTS:
        pdf.add_font("dejavu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        pdf.add_font("dejavu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        pdf.add_font("dejavu", "I", str(_FONT_DIR / "DejaVuSans-Oblique.ttf"))
        pdf.add_font("dejavu", "BI", str(_FONT_DIR / "DejaVuSans-BoldOblique.ttf"))
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_author("SA CoParents Align · sacoparentsalign.com")
    pdf.set_creator("sacoparentsalign.com")
    pdf.set_subject("© 2026 sacoparentsalign.com · SA CoParents Align. All rights reserved.")
    pdf.add_page()
    return pdf


def _professional_line(pdf: FPDF, pro: dict) -> None:
    label = f"Facilitating professional: {pro.get('name') or 'Professional'}"
    pdf.set_font(FONT, "", 11)
    pdf.set_text_color(*GRAY)
    if not pro.get("credentials_verified"):
        pdf.cell(0, 6, _s(label), align="C", new_x="LMARGIN", new_y="NEXT")
        return
    badge = "Credentials Verified"
    pdf.set_font(FONT, "", 11)
    w_label = pdf.get_string_width(_s(label))
    pdf.set_font(FONT, "B", 8)
    w_badge = pdf.get_string_width(badge) + 6
    x = (pdf.w - (w_label + 3 + w_badge)) / 2
    y = pdf.get_y()
    pdf.set_xy(x, y)
    pdf.set_font(FONT, "", 11)
    pdf.set_text_color(*GRAY)
    pdf.cell(w_label, 6, _s(label))
    bx = x + w_label + 3
    pdf.set_fill_color(230, 240, 231)
    pdf.set_draw_color(*GREEN)
    pdf.rect(bx, y + 0.8, w_badge, 4.6, style="DF")
    pdf.set_xy(bx, y + 0.8)
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*GREEN)
    pdf.cell(w_badge, 4.6, badge, align="C")
    pdf.set_xy(pdf.l_margin, y + 6)


def _title_header(pdf: FPDF, title: str, lines: list, notes: list | None = None, pro: dict | None = None) -> None:
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font(FONT, "B", 22)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 10, _s(title), align="C")
    pdf.ln(2)
    pdf.set_font(FONT, "", 11)
    pdf.set_text_color(*GRAY)
    for line in lines:
        pdf.cell(0, 6, _s(line), align="C", new_x="LMARGIN", new_y="NEXT")
    if pro:
        _professional_line(pdf, pro)
    for note in notes or []:
        pdf.set_font(FONT, "I", 9)
        pdf.cell(0, 6, _s(note), align="C", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 3
    pdf.set_draw_color(220, 215, 230)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)


def _philosophy_block(pdf: FPDF, heading: str, note: str, quote: str, size: int = 16) -> None:
    pdf.ln(8)
    pdf.set_font(FONT, "B", size)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 8 if size <= 16 else 9, _s(heading), align="C")
    pdf.ln(1)
    if note:
        _body(pdf, note)
    _body(pdf, f'"{quote}"', italic=True)


def _section_title(pdf: FPDF, num, title: str) -> None:
    pdf.ln(4)
    pdf.set_font(FONT, "B", 13)
    pdf.set_text_color(*TEAL)
    pdf.cell(8, 8, _s(f"{num}."))
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, _s(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _body(pdf: FPDF, text: str, italic: bool = False, indent: int = 0) -> None:
    pdf.set_font(FONT, "I" if italic else "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.set_x(pdf.l_margin + indent)
    pdf.multi_cell(0, 5.5, _s(text))
    pdf.ln(1)


def _bullet(pdf: FPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font(FONT, "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5.5, _s(f"-  {text}"))


def _label(pdf: FPDF, text: str) -> None:
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, _s(text), new_x="LMARGIN", new_y="NEXT")


def _joint_differences(pdf: FPDF, r: dict) -> None:
    _section_title(pdf, 3, "Where the Parents See Things Differently")
    if not r["differences"]:
        _body(pdf, "No significant differences in perspective were identified.", italic=True)
    for d in r["differences"]:
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _s(d["area"]), new_x="LMARGIN", new_y="NEXT")
        _label(pdf, f"{r['parent_a_name']}'s Perspective")
        _body(pdf, d["parent_a"], indent=4)
        _label(pdf, f"{r['parent_b_name']}'s Perspective")
        _body(pdf, d["parent_b"], indent=4)
        _body(pdf, d["reframe"], italic=True, indent=4)
        pdf.ln(2)


def _joint_alignment_map(pdf: FPDF, r: dict) -> None:
    _section_title(pdf, 5, "Alignment Map")
    for row in r["alignment_map"]:
        color = GREEN if row["status"] == "Strong alignment" else (YELLOW if row["status"] == "Moderate alignment" else BLUE)
        pdf.set_font(FONT, "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(90, 7, _s(row["area"]))
        pdf.set_text_color(*color)
        pdf.cell(0, 7, _s(row["status"]), new_x="LMARGIN", new_y="NEXT")


def _joint_notes(r: dict) -> list:
    notes = []
    imported = r.get("imported") or {}
    if imported.get("a") or imported.get("b"):
        notes.append("Includes material imported from sacoparentsapp.online")
    if r.get("is_sample"):
        notes.append("SAMPLE - fictional example data shown for illustration")
    return notes


def _joint_front_sections(pdf: FPDF, r: dict) -> None:
    _section_title(pdf, 1, "Purpose of This Report")
    _body(pdf, r["purpose"])
    _section_title(pdf, 2, "What Both Parents Agree About")
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 6, _s("Strong Alignment - both parents indicated that:"), new_x="LMARGIN", new_y="NEXT")
    for stmt in r["alignment_statements"]:
        _bullet(pdf, stmt)
    _joint_differences(pdf, r)
    _section_title(pdf, 4, "Child's Identified Needs")
    for n in r["child_needs"]:
        _bullet(pdf, n)


def _joint_back_sections(pdf: FPDF, r: dict) -> None:
    _joint_alignment_map(pdf, r)
    _section_title(pdf, 6, "Areas for Conversation")
    for q in r["conversation"]:
        _bullet(pdf, q)
    _section_title(pdf, 7, "Potential Areas of Alignment")
    _body(pdf, r["alignment_paragraph"], italic=True)
    _section_title(pdf, 8, "Questions for the Parents")
    for q in r["questions"]:
        _bullet(pdf, q)
    _section_title(pdf, 9, "Possible Next Steps")
    for step in r["next_steps"]:
        _bullet(pdf, step)


def build_joint_pdf(r: dict) -> bytes:
    pdf = _new_pdf()
    if r.get("is_sample"):
        pdf.watermark_text = "SAMPLE REPORT"
    if r.get("verify"):
        _verify_qr_block(pdf, r["verify"])
    _title_header(pdf, r["report_title"], [
        f"Child: {r['child_name']}",
        f"Subject: {r['subject_label']}",
        f"Participants: {r['parent_a_name']} / {r['parent_b_name']}",
        r["date"],
    ], _joint_notes(r), pro=r.get("professional"))

    _joint_front_sections(pdf, r)
    _joint_back_sections(pdf, r)
    _philosophy_block(pdf, r["philosophy_heading"], r["philosophy_note"], r["philosophy"])
    return bytes(pdf.output())


def _agreement_terms(pdf: FPDF, r: dict) -> None:
    status_colors = {"Likely aligned": GREEN, "Close": YELLOW, "Needs discussion": BLUE}
    for t in r["terms"]:
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(120, 7, _s(t["label"]))
        pdf.set_text_color(*status_colors.get(t["status"], BLUE))
        pdf.cell(0, 7, _s(t["status"]), new_x="LMARGIN", new_y="NEXT")
        _label(pdf, f"{r['parent_a_name']}'s Proposal")
        _body(pdf, t["parent_a"], indent=4)
        _label(pdf, f"{r['parent_b_name']}'s Proposal")
        _body(pdf, t["parent_b"], indent=4)
        pdf.ln(3)


def _agreement_foundation(pdf: FPDF, r: dict) -> None:
    if not r.get("foundation_statements"):
        return
    pdf.set_font(FONT, "B", 13)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Foundation Statements", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    _body(pdf, "Each parent's Foundation Statement from the SA CoParents app is included below to ground this agreement.", italic=True)
    for fs in r["foundation_statements"]:
        _label(pdf, f"{fs['parent']} — {fs['title']}")
        _body(pdf, fs["content"], indent=4)
        pdf.ln(1)
    pdf.ln(6)


def _agreement_signatures(pdf: FPDF, r: dict) -> None:
    pdf.set_font(FONT, "B", 13)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Signatures", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for name in (r["parent_a_name"], r["parent_b_name"]):
        pdf.set_font(FONT, "B", 10.5)
        pdf.cell(0, 6, _s(name), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.l_margin + 80, y)
        pdf.line(pdf.l_margin + 95, y, pdf.l_margin + 140, y)
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(pdf.l_margin, y + 1)
        pdf.cell(80, 5, "Signature")
        pdf.set_xy(pdf.l_margin + 95, y + 1)
        pdf.cell(45, 5, "Date", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)


def _agreement_bullets(pdf: FPDF, title: str, items: list, color: tuple, empty: str | None = None) -> None:
    pdf.set_font(FONT, "B", 9)
    pdf.set_text_color(*color)
    pdf.cell(0, 5.5, _s(title), new_x="LMARGIN", new_y="NEXT")
    if not items:
        if empty:
            _body(pdf, empty, italic=True, indent=4)
        return
    for it in items:
        pdf.set_x(pdf.l_margin + 4)
        pdf.set_font(FONT, "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(0, 5, _s(f"• {it}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _agreement_section(pdf: FPDF, s: dict, r: dict) -> None:
    status_colors = {"Agreed": GREEN, "Partly agreed": YELLOW, "Aligned in principle": TEAL, "Requires resolution": BLUE}
    if pdf.get_y() > pdf.h - 70:
        pdf.add_page()
    pdf.set_font(FONT, "B", 12.5)
    pdf.set_text_color(*PURPLE)
    pdf.cell(130, 7, _s(f"{s['num']}. {s['label']}"))
    pdf.set_font(FONT, "B", 9)
    pdf.set_text_color(*status_colors.get(s["status"], BLUE))
    pdf.cell(0, 7, _s(s["status"]), align="R", new_x="LMARGIN", new_y="NEXT")
    _label(pdf, "Shared Goal")
    _body(pdf, s["shared_goal"], indent=4)
    _agreement_bullets(pdf, "Current Alignment", s["current_alignment"], GREEN, empty="The parents' general proposals use different language; see the items below.")
    _agreement_bullets(pdf, "Specific Agreements", s["specific_agreements"], PURPLE, empty="No specific commitments could be confirmed from both parents' answers yet.")
    for title, key in (("Communication Method", "communication_method"), ("Decision Process", "decision_process"), ("Review Trigger", "review_trigger")):
        if s.get(key):
            _label(pdf, title)
            _body(pdf, s[key], indent=4)
    _agreement_bullets(pdf, "Issues Still Requiring Resolution", s["open_issues"], BLUE)
    pdf.set_draw_color(225, 220, 235)
    y = pdf.get_y() + 1
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(5)


def _agreement_summary(pdf: FPDF, r: dict) -> None:
    pdf.set_font(FONT, "B", 13)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "At a Glance", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    sm = r["summary"]
    _agreement_bullets(pdf, f"Areas of Alignment ({len(sm['alignment'])})", sm["alignment"][:12], GREEN, empty="None identified yet.")
    _agreement_bullets(pdf, f"Specific Agreements ({len(sm['specific'])})", sm["specific"][:16], PURPLE, empty="None confirmed yet.")
    _agreement_bullets(pdf, f"Issues Still Requiring Resolution ({len(sm['resolution'])})", sm["resolution"][:16], BLUE, empty="None — every answered item is aligned.")
    pdf.ln(4)


def build_agreement_pdf(r: dict) -> bytes:
    pdf = _new_pdf()
    _title_header(pdf, r["report_title"], [
        f"Child: {r['child_name']}",
        f"Parents: {r['parent_a_name']} / {r['parent_b_name']}",
        r["date"],
    ])
    _body(pdf, r["purpose"])
    pdf.ln(2)
    _body(pdf, r["confidentiality_note"], italic=True)
    pdf.ln(1)
    _body(pdf, r.get("method_note", ""), italic=True)
    pdf.ln(4)

    if r.get("sections"):
        _agreement_summary(pdf, r)
        for s in r["sections"]:
            _agreement_section(pdf, s, r)
    else:
        _agreement_terms(pdf, r)

    _body(pdf, r["next_note"], italic=True)
    pdf.ln(8)

    _agreement_foundation(pdf, r)
    _agreement_signatures(pdf, r)

    _philosophy_block(pdf, r["philosophy_heading"], "", r["philosophy"])
    return bytes(pdf.output())


def _case_snapshot(pdf: FPDF, r: dict, title: str) -> None:
    _section_title(pdf, 1, title)
    for item in r["purpose_items"]:
        _bullet(pdf, item)
    _body(pdf, r["disclaimer"], italic=True)
    snap = r["snapshot"]
    _body(pdf, f"Topics: {snap['total']}  |  Strong alignment: {snap['aligned']}  |  Differences: {snap['different']}  |  Needs more information: {snap['info']}")
    _body(pdf, r["snapshot_note"], italic=True)


def _case_goals(pdf: FPDF, r: dict, title: str) -> None:
    _section_title(pdf, 2, title)
    for g in r["shared_goals"]:
        _bullet(pdf, g)
    _label(pdf, f"{r['parent_a_name']}'s primary concern")
    _body(pdf, r["parent_a_concern"] or "Not provided.", italic=True, indent=4)
    _label(pdf, f"{r['parent_b_name']}'s primary concern")
    _body(pdf, r["parent_b_concern"] or "Not provided.", italic=True, indent=4)
    _body(pdf, r["central_question"], italic=True)


def _case_alignments(pdf: FPDF, r: dict, title: str) -> None:
    _section_title(pdf, 3, title)
    if not r["alignments"]:
        _body(pdf, "No strong alignment areas were identified yet.", italic=True)
    for a in r["alignments"]:
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*GREEN)
        pdf.cell(0, 7, _s(a["topic"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, a["text"], indent=4)
    _body(pdf, r["alignment_foundation_note"], italic=True)


def _case_differences(pdf: FPDF, r: dict, title: str) -> None:
    _section_title(pdf, 4, title)
    if not r["differences"]:
        _body(pdf, "No significant differences in perspective were identified.", italic=True)
    for d in r["differences"]:
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _s(d["topic"]), new_x="LMARGIN", new_y="NEXT")
        _label(pdf, f"{r['parent_a_name']}'s Perspective")
        _body(pdf, d["parent_a"], indent=4)
        _label(pdf, f"{r['parent_b_name']}'s Perspective")
        _body(pdf, d["parent_b"], indent=4)
        pdf.ln(2)
    _body(pdf, r["differences_note"], italic=True)


def _case_action_plan(pdf: FPDF, r: dict, title: str) -> None:
    _section_title(pdf, 9, title)
    for item in r["action_plan"]:
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _s(item["issue"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, f"Child need: {item['child_need']}", indent=4)
        if item.get("already_agree"):
            _body(pdf, f"Already agree: {item['already_agree']}", italic=True, indent=4)
    summ = r["summary"]
    if summ.get("priority"):
        _body(pdf, f"Priority: {summ['priority']}")
    for line in summ.get("aligned", []) + summ.get("info", []) + summ.get("conversation", []):
        _bullet(pdf, line)


def _case_bullet_section(pdf: FPDF, num: int, title: str, items: list, note: str | None = None) -> None:
    _section_title(pdf, num, title)
    for item in items:
        _bullet(pdf, item if isinstance(item, str) else str(item))
    if note:
        _body(pdf, note, italic=True)


def _case_professional_map(pdf: FPDF, r: dict, title: str) -> None:
    pm = r.get("professional_map") or {}
    _case_bullet_section(pdf, 8, title, pm.get("sequence") or [])
    _body(pdf, f"Alignment areas: {pm.get('alignment_count', 0)}  |  Conversation areas: {pm.get('conversation_count', 0)}  |  Needs professional input: {pm.get('professional_input_count', 0)}  |  Child needs: {pm.get('child_needs_count', 0)}")


def build_case_pdf(r: dict) -> bytes:
    demo = bool(r.get("is_demo"))
    pdf = _new_pdf()
    if demo:
        pdf.watermark_text = "SAMPLE REPORT"
    _title_header(pdf, r["report_title"], [
        f"Child: {r['child_name']}",
        f"Assessment: {r['assessment_title']}",
        f"Parents: {r['parent_a_name']} / {r['parent_b_name']}",
        str(r.get("generated_at", ""))[:10],
    ], ["SAMPLE REPORT - demo data shown for illustration"] if demo else [])

    titles = r["page_titles"]
    _case_snapshot(pdf, r, titles[0])
    _case_goals(pdf, r, titles[1])
    _case_alignments(pdf, r, titles[2])
    _case_differences(pdf, r, titles[3])
    _case_bullet_section(pdf, 5, titles[4], r["child_needs"])
    _case_bullet_section(pdf, 6, titles[5], r["options"], f"{r['options_note']} This distinction preserves the educational and resource nature of this report.")
    _case_bullet_section(pdf, 7, titles[6], r["conversation_questions"], r["central_question"])
    _case_professional_map(pdf, r, titles[7])
    _case_action_plan(pdf, r, titles[8])
    _philosophy_block(pdf, r["philosophy_heading"], r["philosophy_note"], r["philosophy"], size=18)
    return bytes(pdf.output())


def _complete_assessment_section(pdf: FPDF, sec: dict) -> None:
    s = sec["snapshot"]
    _body(pdf, f"Topics: {s['total']}  |  Strong alignment: {s['aligned']}  |  Differences: {s['different']}  |  Needs more information: {s['info']}")
    for a in sec["alignments"]:
        pdf.set_font(FONT, "B", 10.5)
        pdf.set_text_color(*GREEN)
        pdf.cell(0, 6, _s(a["topic"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, a["text"], indent=4)
    for d in sec["differences"]:
        pdf.set_font(FONT, "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 6, _s(d["topic"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, d["parent_a"], indent=4)
        _body(pdf, d["parent_b"], indent=4)
    if sec.get("priority"):
        _body(pdf, f"Priority: {sec['priority']}", italic=True)


def _complete_joint_section(pdf: FPDF, sec: dict) -> None:
    for stmt in sec["alignment_statements"]:
        _bullet(pdf, stmt)
    for row in sec["alignment_map"]:
        color = GREEN if row["status"] == "Strong alignment" else (YELLOW if row["status"] == "Moderate alignment" else BLUE)
        pdf.set_font(FONT, "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(90, 7, _s(row["area"]))
        pdf.set_text_color(*color)
        pdf.cell(0, 7, _s(row["status"]), new_x="LMARGIN", new_y="NEXT")
    for d in sec["differences"]:
        pdf.set_font(FONT, "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 6, _s(d["area"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, d["parent_a"], indent=4)
        _body(pdf, d["parent_b"], indent=4)
        _body(pdf, d["reframe"], italic=True, indent=4)


def _complete_section(pdf: FPDF, num: int, sec: dict) -> None:
    _section_title(pdf, num, sec["title"])
    if sec.get("child_name"):
        _body(pdf, f"Child: {sec['child_name']}", italic=True)
    if sec["kind"] == "assessment":
        _complete_assessment_section(pdf, sec)
    else:
        _complete_joint_section(pdf, sec)
    _label(pdf, "Child's identified needs")
    for n in sec["child_needs"]:
        _bullet(pdf, n)
    _label(pdf, "Options and resources")
    for o in sec["options"]:
        _bullet(pdf, o)
    _label(pdf, "Questions for the parents")
    for q in sec["questions"]:
        _bullet(pdf, q if isinstance(q, str) else str(q))
    pdf.ln(2)


def build_complete_pdf(r: dict) -> bytes:
    lines = [r["subtitle"], r["generated_at"]]
    if r.get("prepared_by"):
        lines.insert(1, f"Prepared by: {r['prepared_by']}")
    if r.get("children"):
        lines.append(f"Children: {', '.join(r['children'])}")

    pdf = _new_pdf()
    _title_header(pdf, r["title"], lines)
    pdf.ln(-2)

    _section_title(pdf, 1, "Purpose of This Report")
    _body(pdf, r["purpose"])
    t = r["totals"]
    _body(pdf, f"Strong alignment: {t['aligned']}  |  Differences in perspective: {t['different']}  |  Needs more information: {t['info']}")
    _body(pdf, r["totals_note"], italic=True)

    for i, sec in enumerate(r["sections"], start=2):
        _complete_section(pdf, i, sec)

    _philosophy_block(pdf, r["philosophy_heading"], r["philosophy_note"], r["philosophy"], size=18)
    return bytes(pdf.output())


_METHOD_STAGES = [
    ("Reflection", "Each parent reflects privately, in their own words."),
    ("Comparison", "Align lines up both perspectives side by side."),
    ("Alignment", "Shared ground and differences are named without blame."),
    ("Options", "Neutral options and resources are offered around the child's needs."),
    ("Agreement", "Alignment becomes the foundation for a workable agreement."),
]

_METHOD_STEPS = [
    ("Create a Case", "The professional chooses the family and the issue to address."),
    ("Invite Each Parent", "Each parent receives a private invitation and completes their reflection independently. Responses are never exchanged between parents."),
    ("Generate Joint Alignment Report", "Align identifies shared understanding, differences in perspective, child needs, and subjects requiring discussion."),
    ("Guide the Conversation", "The professional uses the report to move the parents from alignment toward agreement."),
]

_METHOD_PAGES = [
    "Joint Alignment Overview", "Your Child at the Center", "Where You Align", "Where Your Perspectives Differ",
    "What Might Your Child Need?", "Options & Resources", "Questions for Parent Conversation",
    "Professional Conversation Guide", "Parent Action Plan", "Joint Alignment Summary",
]

_METHOD_PRINCIPLES = [
    "Neutral language only: \"Both parents identified...\", \"The parents expressed different perspectives regarding...\"",
    "No custody recommendation, diagnosis, finding of fact, or ranking of parents.",
    "One parent's raw responses are never shown to the other parent.",
    "Safety concerns are routed to the professional through a separate, safety-sensitive process.",
    "If only one parent participates, the result is an individual reflection - never called a joint report.",
]


def _method_stage_row(pdf: FPDF) -> None:
    n = len(_METHOD_STAGES)
    gap = 3
    w = (pdf.w - pdf.l_margin - pdf.r_margin - gap * (n - 1)) / n
    y = pdf.get_y()
    for i, (label, body) in enumerate(_METHOD_STAGES):
        x = pdf.l_margin + i * (w + gap)
        pdf.set_fill_color(245, 242, 250)
        pdf.set_draw_color(220, 215, 230)
        pdf.rect(x, y, w, 24, style="DF")
        pdf.set_xy(x, y + 2)
        pdf.set_font(FONT, "B", 8.5)
        pdf.set_text_color(*PURPLE)
        pdf.cell(w, 5, _s(label.upper()), align="C")
        pdf.set_xy(x + 1.5, y + 8)
        pdf.set_font(FONT, "", 7)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(w - 3, 3.4, _s(body), align="C")
    pdf.set_xy(pdf.l_margin, y + 26)
    pdf.set_font(FONT, "B", 8.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 5, "THE CHILD AT THE CENTER OF EVERY STAGE", align="C", new_x="LMARGIN", new_y="NEXT")


def _method_steps_block(pdf: FPDF) -> None:
    for i, (title, body) in enumerate(_METHOD_STEPS, 1):
        y = pdf.get_y()
        pdf.set_fill_color(*PURPLE)
        pdf.ellipse(pdf.l_margin, y + 0.5, 6, 6, style="F")
        pdf.set_xy(pdf.l_margin, y + 0.5)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(6, 6, str(i), align="C")
        pdf.set_xy(pdf.l_margin + 9, y)
        pdf.set_font(FONT, "B", 9.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 5, _s(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(pdf.l_margin + 9)
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(0, 4.2, _s(body))
        pdf.ln(1.5)


def _method_two_columns(pdf: FPDF) -> None:
    top = pdf.get_y()
    col_w = (pdf.w - pdf.l_margin - pdf.r_margin - 8) / 2
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(col_w, 6, "THE UNIVERSAL 10-PAGE REPORT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 8.5)
    pdf.set_text_color(*BODY)
    for i, p in enumerate(_METHOD_PAGES, 1):
        pdf.cell(col_w, 4.6, _s(f"{i:>2}.  {p}"), new_x="LMARGIN", new_y="NEXT")
    left_end = pdf.get_y()
    x2 = pdf.l_margin + col_w + 8
    pdf.set_xy(x2, top)
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(col_w, 6, "WHAT THE MODEL WILL NOT DO", new_x="LEFT", new_y="NEXT")
    for p in _METHOD_PRINCIPLES:
        pdf.set_x(x2)
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(col_w, 4.2, _s(f"-  {p}"))
        pdf.ln(0.5)
    pdf.set_y(max(left_end, pdf.get_y()))


def build_methodology_pdf(site_url: str) -> bytes:
    pdf = _new_pdf()
    pdf.set_auto_page_break(auto=False)
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents Align", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 8, _s("The SA CoParents Align Model"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 12)
    pdf.multi_cell(0, 7, _s("Reflection → Comparison → Alignment → Options → Agreement"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 4.5, _s(
        "A structured, child-centered methodology for organizing two parents' independent perspectives before a "
        "mediation, counseling session, parenting-coordination meeting, or court-connected conference. Professionals "
        "create the case and invite each parent; parents never exchange codes or see each other's responses."))
    pdf.ln(4)
    _method_stage_row(pdf)
    pdf.ln(4)
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "HOW A CASE MOVES THROUGH THE MODEL", new_x="LMARGIN", new_y="NEXT")
    _method_steps_block(pdf)
    pdf.ln(2)
    _method_two_columns(pdf)
    pdf.ln(4)
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s(
        "SA CoParents Align is an educational, organizational, and mediation-preparation platform. It does not replace "
        "professional judgment, legal advice, psychological evaluation, safety assessment, or individualized case management. "
        f"Learn more: {site_url}/methodology"))
    return bytes(pdf.output())


def _fmt_date(iso) -> str:
    return str(iso or "")[:10] or "—"


def _letterhead(pdf: FPDF, pro: dict, lines: list) -> None:
    """Professional letterhead block: name, role/org, license/contact, verified badge, rule."""
    pdf.set_font(FONT, "B", 13)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 7, _s(pro.get("name") or "Professional"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*GRAY)
    for line in lines:
        if line:
            pdf.cell(0, 5, _s(line), new_x="LMARGIN", new_y="NEXT")
    if pro.get("credentials_verified"):
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 5, "Credentials verified by SA CoParents", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 3
    pdf.set_draw_color(220, 215, 230)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)


def _contact_line(pro: dict) -> str:
    return " · ".join(x for x in (pro.get("license_number") and f"License {pro['license_number']}", pro.get("phone"), pro.get("email")) if x)


def _footnote(pdf: FPDF, text: str) -> None:
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s(text), new_x="LMARGIN", new_y="NEXT")


def build_court_cover_letter_pdf(p: dict) -> bytes:
    """Professional's cover letter to the court + packet index (pages 1-2 of a Court Packet)."""
    pro = p.get("professional") or {}
    pdf = _new_pdf()
    _letterhead(pdf, pro, [pro.get("pro_role"), pro.get("organization"), _contact_line(pro), " ".join(x for x in (pro.get("city"), pro.get("state")) if x)])
    pdf.set_font(FONT, "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 6, _s(_fmt_date(p.get("created_at"))), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for line in [p.get("judge_name") and f"The Honorable {p['judge_name']}", p.get("court_name"), p.get("cause_number") and f"Re: Cause No. {p['cause_number']}"]:
        if line:
            pdf.cell(0, 6, _s(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    _body(pdf, p.get("cover_letter") or "")
    pdf.ln(4)
    _label(pdf, "ENCLOSED IN THIS COURT PACKET")
    for i, item in enumerate(p.get("index") or [], 1):
        _bullet(pdf, f"{i}. {item}")
    if p.get("session_outcome"):
        so = p["session_outcome"]
        pdf.ln(3)
        _label(pdf, "SESSION OUTCOME RECORDED BY THE PROFESSIONAL")
        for s in so.get("chosen_steps") or []:
            _bullet(pdf, s)
        if so.get("summary"):
            _body(pdf, so["summary"], italic=True)
    pdf.ln(4)
    _label(pdf, "PROFESSIONAL ATTESTATION")
    _body(pdf, p.get("attestation_text") or "", italic=True)
    pdf.ln(6)
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s(
        "SA CoParents Align reports compare each parent's independently provided perspective. They are educational and "
        "organizational documents prepared to support professional facilitation; they are not custody recommendations, "
        "psychological evaluations, or findings of fact. Every opening and download of this packet is logged."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def build_transmittal_pdf(p: dict) -> bytes:
    """One-page Certificate of Transmittal for the professional's file."""
    pro = p.get("professional") or {}
    pdf = _new_pdf()
    pdf.set_auto_page_break(auto=False)
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents Align", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, "Certificate of Transmittal - Court Packet", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4.5, _s(f"Packet reference {p['id'][:8].upper()}  |  Generated {_fmt_date(_dt.now(_tz.utc).isoformat())}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    rows = [
        ("Transmitted by", f"{pro.get('name', '')}{', ' + pro['pro_role'] if pro.get('pro_role') else ''}{' - ' + pro['organization'] if pro.get('organization') else ''}"),
        ("License / Bar", pro.get("license_number") or "-"),
        ("Addressed to", f"The Honorable {p.get('judge_name', '')}"),
        ("Court", p.get("court_name") or "-"),
        ("Cause number", p.get("cause_number") or "-"),
        ("Recipient email", p.get("judge_email", "")),
        ("Sent", _fmt_date(p.get("created_at"))),
        ("Access expires", _fmt_date(p.get("expires_at"))),
        ("Current status", (p.get("status") or "sent").replace("_", " ")),
        ("Opens / downloads", f"{p.get('opened_count', 0)} / {p.get('download_count', 0)}"),
    ]
    for k, v in rows:
        pdf.set_font(FONT, "B", 9.5)
        pdf.set_text_color(*DARK)
        pdf.cell(42, 6, _s(k))
        pdf.set_font(FONT, "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(0, 6, _s(v), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    _label(pdf, "ENCLOSURES TRANSMITTED")
    _bullet(pdf, "Professional cover letter with attestation of authority to release")
    for e in p.get("enclosures") or []:
        _bullet(pdf, e)
    pdf.ln(3)
    _label(pdf, "COURT ACKNOWLEDGEMENT AND RESPONSES")
    resps = p.get("responses") or []
    if not resps:
        _body(pdf, "No acknowledgement received yet.", italic=True)
    for x in resps[:5]:
        kind = "Receipt acknowledged" if x.get("kind") == "acknowledged" else "Clarification requested"
        _bullet(pdf, f"{_fmt_date(x.get('at'))}  {kind} by {x.get('by', '')}{': ' + x['message'] if x.get('message') else ''}")
    pdf.ln(3)
    _label(pdf, "ACCESS LOG")
    for e in (p.get("events") or [])[:8]:
        _bullet(pdf, f"{str(e.get('at', ''))[:16].replace('T', ' ')}  {e.get('action', '')}")
    pdf.ln(4)
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s("This certificate is generated by SA CoParents Align from its tamper-evident access log. Court access is read-only; "
                            "every opening, download, and response is recorded with a timestamp."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _stmt_text(pdf: FPDF, title: str, text: str | None, required: bool = False) -> None:
    if not text and not required:
        return
    _label(pdf, title.upper())
    _body(pdf, text or "-")
    pdf.ln(2)


def _stmt_list(pdf: FPDF, title: str, items: list, empty: str | None = None) -> None:
    if not items and not empty:
        return
    _label(pdf, title.upper())
    for item in items:
        _body(pdf, f"• {item}", indent=4)
    if not items:
        _body(pdf, empty, italic=True)
    pdf.ln(2)


def _statement_findings(pdf: FPDF, f: dict) -> None:
    """Joint assessment findings infused from the Joint Report (neutral; no per-parent text)."""
    _label(pdf, "4. JOINT ASSESSMENT FINDINGS")
    _body(pdf, f"Drawn from the Joint Alignment Report ({f.get('subject_label') or 'joint assessment'}). Differences are listed by area only; neither parent's individual responses appear here.", italic=True)
    _stmt_list(pdf, "Areas of alignment", f.get("alignment") or [], "None identified.")
    _stmt_list(pdf, "Differences in perspective", f.get("differences") or [], "None identified.")
    _stmt_list(pdf, "Child-focused considerations", f.get("child_focused") or [])


def _statement_framework(pdf: FPDF, fw: dict) -> None:
    """Co-Parenting Ability Level + options, resources and conflict-management techniques (professional/court only)."""
    if pdf.get_y() > pdf.h - 80:
        pdf.add_page()
    _label(pdf, "5. CO-PARENTING ABILITY LEVEL")
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _s(f"Level {fw['score']} / 10 — {fw['label']}"), new_x="LMARGIN", new_y="NEXT")
    if fw.get("safety_alert"):
        _body(pdf, "High-Conflict / Safety Protocols Active: direct verbal interaction should be eliminated; child-welfare communication through structured digital mediums only.", italic=True)
    _body(pdf, f"{fw['framework_title']}. {fw['framework']}")
    if fw.get("level_change_note"):
        _body(pdf, f"Change since last submission: {fw['level_change_note']}", italic=True)
    _body(pdf, "Level, options and resources are calibrated to the assessed co-parenting dynamic and provided to the professional and court only; they are not findings about either parent.", italic=True)
    pdf.ln(2)


def _statement_level_history(pdf: FPDF, hist: list) -> None:
    """Prior submitted versions' Ability Levels (progress over time)."""
    rows = [h for h in hist if h.get("score")]
    if not rows:
        return
    _label(pdf, "ABILITY LEVEL HISTORY (SUBMITTED VERSIONS)")
    for h in rows:
        _body(pdf, f"• Version {h.get('version')} — {str(h.get('at') or '')[:10]}: Level {h['score']} / 10 — {h.get('label', '')}" + (f" (changed from Level {h['changed_from']}: {h['note']})" if h.get("changed_from") and h.get("note") else ""), indent=4)
    pdf.ln(2)


def build_professional_statement_pdf(p: dict) -> bytes:
    """Professional Report (Professional Assessment Statement) on letterhead — the single professional/court deliverable."""
    pro = p.get("professional") or {}
    st = p.get("statement") or {}
    court = p.get("court") or {}
    pdf = _new_pdf()
    if p.get("is_sample"):
        pdf.watermark_text = "SAMPLE REPORT"
    _letterhead(pdf, pro, [" · ".join(x for x in (pro.get("pro_role"), pro.get("organization")) if x), _contact_line(pro)])
    pdf.set_font(FONT, "B", 16)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, "Professional Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, "Professional Assessment Statement with Joint Assessment Findings" + (" — SAMPLE, fictional data" if p.get("is_sample") else ""), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    _label(pdf, "1. CASE & REFERRAL")
    rows = [("Date", p.get("date")), ("Court", court.get("court_name")), ("Cause number", court.get("cause_number")), ("Presiding", court.get("judge_name") and f"The Honorable {court['judge_name']}"),
            ("Align case", p.get("case_code")), ("Subject", p.get("subject_label")), ("Child", (p.get("child_name") or "")[:1] and f"{p['child_name'][0]}."), ("Professional role", st.get("role")),
            ("Report version", st.get("version") and f"v{st['version']}")]
    for k, v in rows:
        if not v:
            continue
        pdf.set_font(FONT, "B", 9.5)
        pdf.set_text_color(*DARK)
        pdf.cell(38, 5.5, _s(k))
        pdf.set_font(FONT, "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(0, 5.5, _s(str(v)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    _stmt_text(pdf, "Role and basis of involvement", st.get("role_basis"), required=True)
    _stmt_text(pdf, "2. Materials reviewed", " · ".join(st.get("materials_reviewed") or []) or None, required=True)
    _stmt_text(pdf, "3. Process completed by the parents", st.get("process_summary"), required=True)
    if p.get("findings"):
        _statement_findings(pdf, p["findings"])
    if st.get("framework"):
        _statement_framework(pdf, {**st["framework"], "level_change_note": (f"Level {st['level_changed_from']} → {st['framework']['score']}: {st['level_change_note']}" if st.get("level_changed_from") and st.get("level_change_note") else "")})
        _statement_level_history(pdf, p.get("level_history") or [])
    _label(pdf, "6. PARENT ALIGNMENT — BASED ON JOINT REPORT")
    _body(pdf, "Where the parents are aligned, where they are not, and which unresolved issues may require additional professional support or conflict-management intervention.", italic=True)
    _stmt_text(pdf, "Where the parents agree / are aligned", st.get("alignment_areas"), required=True)
    _stmt_text(pdf, "Where the parents do not agree / are not aligned", st.get("further_attention"), required=True)
    _stmt_text(pdf, "Partial alignment / potential areas for agreement", st.get("partial_alignment"))
    _stmt_text(pdf, "Professional alignment summary", st.get("alignment_summary"))
    if st.get("framework"):
        fw = st["framework"]
        _label(pdf, "7. CONFLICT MANAGEMENT — APPROACHES TO CONFLICT")
        _stmt_list(pdf, "Options & resources", (fw.get("subject_options") or []) + (fw.get("resources") or []) + (fw.get("tools") or []), "None selected.")
        _stmt_list(pdf, "Conflict-management techniques", fw.get("techniques") or [], "None selected.")
    _stmt_text(pdf, "Resources / interventions considered by the professional", st.get("resources_considered"))
    _stmt_text(pdf, "Safety considerations", st.get("safety_considerations"))
    _label(pdf, "8. ROADMAP")
    _stmt_text(pdf, "Current status", st.get("current_status"))
    _stmt_text(pdf, "Recommended next steps for facilitation", st.get("next_steps"), required=True)
    _label(pdf, "9. PROFESSIONAL SUMMARY")
    _stmt_text(pdf, "Professional observations", st.get("observations"), required=True)
    _label(pdf, "PROFESSIONAL ATTESTATION")
    _body(pdf, p.get("attestation_text") or "", italic=True)
    pdf.ln(6)
    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 6, _s(f"Respectfully submitted,  {pro.get('name', '')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s("This Professional Report describes the facilitation process, the joint assessment findings and the professional's observations. It is not a custody evaluation and makes no recommendation "
                            "regarding conservatorship or possession. It is prepared for the professional and the court only and is not shared with the parents. Prepared through SA CoParents Align."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def merge_pdfs(parts: list[bytes]) -> bytes:
    import pymupdf
    out = pymupdf.open()
    for b in parts:
        with pymupdf.open(stream=b, filetype="pdf") as src:
            out.insert_pdf(src)
    out.set_metadata({"author": "SA CoParents Align · sacoparentsalign.com", "creator": "sacoparentsalign.com", "producer": "sacoparentsalign.com",
                      "subject": "© 2026 sacoparentsalign.com · SA CoParents Align. All rights reserved.", "title": "Court Packet"})
    return out.tobytes()


def _prep_heading(pdf: FPDF, text: str) -> None:
    pdf.ln(2)
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, _s(text.upper()), new_x="LMARGIN", new_y="NEXT")


def _prep_line(pdf: FPDF, text: str, size: float = 9, italic: bool = False) -> None:
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font(FONT, "I" if italic else "", size)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 4.6, _s(f"-  {text}" if not italic else text), new_x="LMARGIN", new_y="NEXT")


def _prep_checkbox(pdf: FPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5, _s(f"[  ]  {text}"), new_x="LMARGIN", new_y="NEXT")


def _legal_kv(pdf: FPDF, rows: list) -> None:
    for k, v in rows:
        if not v:
            continue
        pdf.set_font(FONT, "B", 9.5)
        pdf.set_text_color(*DARK)
        pdf.cell(42, 5.5, _s(k))
        pdf.set_font(FONT, "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(0, 5.5, _s(str(v)), new_x="LMARGIN", new_y="NEXT")


def _lens_heading(pdf: FPDF, text: str) -> None:
    if pdf.get_y() > pdf.h - 50:
        pdf.add_page()
    pdf.set_fill_color(243, 238, 250)
    pdf.set_font(FONT, "B", 11.5)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, _s(f"  {text}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _lens_rating(pdf: FPDF, who: str, rating, cls: dict | None, joint: bool = False) -> None:
    if not rating or not cls:
        _body(pdf, f"{who} rating: not yet entered.", italic=True)
        return
    _body(pdf, f"{who} rating: {rating} / 10 — {cls['label']} ({cls['range']})" + (f" · Mode: {cls['mode']}" if joint else ""))
    _stmt_list(pdf, "Where this level may do well", cls["strengths"])
    _stmt_list(pdf, "Possible gaps", cls["gaps"])


def _lens_resources(pdf: FPDF, title: str, items: list, provider: dict | None) -> None:
    _lens_heading(pdf, title)
    _stmt_list(pdf, "Selected resources", items, "None selected.")
    if provider and provider.get("name"):
        _body(pdf, f"Additional provider: {provider['name']} — {provider.get('specialty', '')} — {provider.get('contact', '')}")
    pdf.ln(1)


def _lens_table(pdf: FPDF, headers: list, rows: list, widths: list, active: set | None = None) -> None:
    pdf.set_font(FONT, "", 8)
    with pdf.table(col_widths=widths, text_align="LEFT", line_height=4.2, headings_style=FontFace(emphasis="BOLD", color=PURPLE, fill_color=(243, 238, 250)), borders_layout="ALL") as table:
        hdr = table.row()
        for h in headers:
            hdr.cell(_s(h))
        for i, r in enumerate(rows):
            style = FontFace(fill_color=(254, 243, 199)) if active and i in active else None
            row = table.row(style=style)
            for cell in r:
                row.cell(_s(str(cell)))
    pdf.ln(2)


def _lens_parent(pdf: FPDF, name: str, rep: dict, role: str, cls: dict | None) -> None:
    rating = rep.get(f"parent_{role}_rating")
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, _s(f"{name} (Rated: Level {rating})" if rating else f"{name} (not yet rated)"), new_x="LMARGIN", new_y="NEXT")
    if cls:
        _body(pdf, f"Band {cls['range']} — {cls['label']}", italic=True)
    _stmt_text(pdf, "What's Working Well (Strengths)", rep.get(f"parent_{role}_strengths"), required=True)
    _stmt_text(pdf, "Real-World Example (Gaps)", rep.get(f"parent_{role}_gaps"), required=True)
    _stmt_list(pdf, "Key Growth Areas", [g.strip() for g in (rep.get(f"parent_{role}_growth") or "").split("\n") if g.strip()], "Not yet entered.")
    _stmt_text(pdf, "Professional notes (PARENT-REPORTED INFORMATION summarized by the professional)", rep.get(f"parent_{role}_notes"))


def _lens_scale(pdf: FPDF, scale: list, cls: dict, rep: dict) -> None:
    a, b, j = cls.get("parent_a"), cls.get("parent_b"), cls.get("joint")
    rows, active = [], set()
    for i, r in enumerate(scale):
        place = [f"PARENT A (L{rep.get('parent_a_rating')})" if a and a["row"] == i else "", f"PARENT B (L{rep.get('parent_b_rating')})" if b and b["row"] == i else "",
                 f"JOINT (L{rep.get('joint_rating')})" if j and j["row"] == i else ""]
        if any(place):
            active.add(i)
        rows.append([f"{r['lo']} – {r['hi']}", f"{r['label']} ({r['mode']})", f"Joint: {r['well']['joint']} Parent A: {r['well']['a']} Parent B: {r['well']['b']}",
                     f"Joint: {r['poor']['joint']} Parent A: {r['poor']['a']} Parent B: {r['poor']['b']}", "\n".join(p for p in place if p)])
    _lens_table(pdf, ["Score", "Dynamic & Mode", "Where Co-Parents Do Well (Strengths)", "Where Co-Parents Do Poorly (Gaps)", "Case Placement"], rows, [14, 30, 50, 50, 30], active)


def build_legal_lens_pdf(v: dict) -> bytes:
    """SA CoParents Align Professional Evaluation Report — court-ready PDF (7 sections + certification)."""
    from legal_lens import PATHWAYS, RISK_CATEGORIES, SCALE_TABLE
    rep, c, cls, notes = v["report"], v["case"], v["classification"], v["notes"]
    pdf = _new_pdf()
    pdf.footer_meta = f"{notes['tagline']} · Case {c.get('case_code') or ''} · {rep.get('professional_name') or ''} · {rep.get('report_date') or ''}"
    if rep.get("status") not in ("final", "submitted_to_court"):
        pdf.watermark_text = "DRAFT"
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents Align", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 8, "SA CoParents Align Professional Evaluation Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*PURPLE)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
    pdf.ln(4)
    _legal_kv(pdf, [("Platform", "sacoparentsalign.com"), ("Focus", "Comprehensive 1–10 Scale Analysis (Joint & Individual Behaviors), Stage-Specific Profiles, Resources & Actionable Roadmap"),
                    ("Case / Matter", rep.get("matter_name")), ("Case ID", c.get("case_code")), ("Court / County", rep.get("court_county")), ("Cause Number", rep.get("cause_number")),
                    ("Professional", f"{rep.get('professional_name') or ''} · {rep.get('professional_role') or ''}".strip(" ·")), ("Report Date", rep.get("report_date")),
                    ("Parent A", rep.get("parent_a_name")), ("Parent B", rep.get("parent_b_name")), ("Report Status", (rep.get("status") or "draft").replace("_", " ").title())])
    _lens_heading(pdf, "What This Report Covers")
    _body(pdf, notes.get("intro", ""))
    _lens_heading(pdf, "1. Safety First: Checking for Domestic Violence & IPV Risks")
    _body(pdf, "Before evaluating co-parenting scores or suggesting joint meetings, we screen for Intimate Partner Violence (IPV) and coercive control.")
    _body(pdf, notes.get("alert", ""), italic=True)
    _legal_kv(pdf, [("Parent A FV Assessment", rep.get("fv_a_received")), ("Parent B FV Assessment", rep.get("fv_b_received")), ("Joint Process Appropriate?", rep.get("joint_process_appropriate"))])
    risk = rep.get("risk_screening") or {}
    _stmt_list(pdf, "Risk Screening Summary", [f"{lbl}: {risk.get(k, {}).get('level', 'Not assessed')}." + (f" {risk[k]['note']}" if risk.get(k, {}).get("note") else "") for k, lbl, _ in RISK_CATEGORIES])
    _stmt_text(pdf, "Safety notes / safeguards", rep.get("safety_notes"))
    _stmt_text(pdf, "Takeaway", rep.get("safety_takeaway"), required=True)
    _body(pdf, notes["safety"], italic=True)
    _lens_heading(pdf, "2. Detailed Individual Breakdown for Parent A & Parent B")
    _lens_parent(pdf, rep.get("parent_a_name") or "Parent A", rep, "a", cls["parent_a"])
    _lens_parent(pdf, rep.get("parent_b_name") or "Parent B", rep, "b", cls["parent_b"])
    j = cls["joint"]
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, _s(f"Joint Dynamic Summary (Rated: Level {rep.get('joint_rating')})" if rep.get("joint_rating") else "Joint Dynamic Summary (not yet rated)"), new_x="LMARGIN", new_y="NEXT")
    _legal_kv(pdf, [("Operating Dynamic", f"{j['mode']} Mode — {j['label']}" if j else "")])
    _stmt_text(pdf, "Where the parents do well together", rep.get("joint_strengths"))
    _stmt_text(pdf, "Where the parents struggle together", rep.get("joint_gaps"))
    _stmt_text(pdf, "Summary", rep.get("joint_notes"), required=True)
    _lens_heading(pdf, "3. Comprehensive 1–10 Co-Parenting Scale: Joint & Individual Behaviors")
    _lens_scale(pdf, SCALE_TABLE, cls, rep)
    _lens_heading(pdf, "4. Post-Rating Roadmap: Short-Term & Long-Term Goals")
    _stmt_list(pdf, "A. Short-Term Goals (Next 30 to 90 Days)", [g.strip() for g in (rep.get("short_term_goals") or "").split("\n") if g.strip()], "Not yet entered.")
    _stmt_list(pdf, "B. Long-Term Goals (6 to 12 Months)", [g.strip() for g in (rep.get("long_term_goals") or "").split("\n") if g.strip()], "Not yet entered.")
    _lens_heading(pdf, "5. Resource & Support Options")
    rows = [[r.get("category", ""), r.get("resource", ""), r.get("focus", "")] for r in (rep.get("resource_rows") or [])]
    if rows:
        _lens_table(pdf, ["Category", "Recommended Resource / Specialist", "Service Focus & Scope"], rows, [40, 60, 74])
    else:
        _body(pdf, "No resources selected.", italic=True)
    _lens_heading(pdf, "6. Checking In: Regular Reassessments")
    _body(pdf, f"By checking in {(rep.get('reassess_interval') or 'every 90 to 180 days').lower()} via SA CoParents Align, parents can track progress against their roadmap:")
    _stmt_text(pdf, "When Score Moves Up", rep.get("reassess_up"))
    _stmt_text(pdf, "When Score Drops", rep.get("reassess_down"))
    _legal_kv(pdf, [("Next review / reassessment", rep.get("next_review_date"))])
    _lens_heading(pdf, "7. Conflict Resolution Pathways (Levels 1–10)")
    rec = (j or {}).get("pathway") or {}
    chosen = rep.get("conflict_pathway") or rec.get("key")
    for n, p in enumerate(PATHWAYS, 1):
        mark = f" — [Level {rep.get('joint_rating')} Recommendation]" if p["key"] == chosen and rep.get("joint_rating") else ""
        _body(pdf, f"{n}. {p['name']} ({p['levels']}){mark}: {p['desc']}", indent=2)
    _stmt_text(pdf, "Rationale / recommended structure", rep.get("conflict_management_rationale"), required=True)
    _body(pdf, notes["rating"], italic=True)
    _lens_heading(pdf, "Professional Certification")
    _body(pdf, "This report reflects the professional's review of the individual assessments, safety screenings and Joint Report. It contains no custody recommendation, credibility determination, diagnosis or legal conclusion.", italic=True)
    _legal_kv(pdf, [("Professional signature", rep.get("signature_name")), ("Title", rep.get("professional_title")), ("Date finalized", (rep.get("finalized_at") or "")[:10])])
    _lens_ai_appendix(pdf, rep)
    pdf.ln(3)
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _s(notes["tagline"]), align="C", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


LENS_FIELD_TITLES = {"safety_takeaway": "Safety takeaway", "parent_a_growth": "Parent A key growth areas", "parent_b_growth": "Parent B key growth areas", "joint_notes": "Joint dynamic summary",
                     "conflict_management_rationale": "Conflict resolution rationale", "short_term_goals": "Short-term goals", "long_term_goals": "Long-term goals",
                     "alignment_summary": "Professional alignment summary", "professional_summary": "Professional summary"}


def _lens_ai_appendix(pdf: FPDF, rep: dict) -> None:
    drafts = rep.get("ai_drafts") or {}
    if not drafts:
        return
    review = rep.get("ai_review") or {}
    _lens_heading(pdf, "Appendix — AI-Assisted Drafting Disclosure")
    _body(pdf, "The sections listed below were initially drafted with an AI drafting aid at the professional's request. The professional reviewed each section and remains solely "
               "responsible for its content. AI text makes no legal conclusion, credibility finding, diagnosis or custody recommendation.", italic=True)
    rows = []
    for k, d in drafts.items():
        rv = review.get(k)
        state = ("Edited by professional" if rv["edited"] else "Accepted without edits") if rv else "Under professional review"
        rows.append((LENS_FIELD_TITLES.get(k, k), f"{d.get('model', '')} · drafted {str(d.get('at', ''))[:10]} · {state}"))
    _legal_kv(pdf, rows)


def _legal_parent(pdf: FPDF, title: str, summary: dict) -> None:
    _label(pdf, title.upper())
    _body(pdf, summary.get("label", "PARENT-REPORTED INFORMATION"), italic=True)
    for it in summary.get("items") or []:
        pdf.set_font(FONT, "B", 9.5)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5, _s(it["heading"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, it["text"], indent=4)
    pdf.ln(2)


LENS_PDF = (("Professional observations", "observations"), ("Issues requiring attention", "further_attention"), ("Areas of existing agreement", "alignment_areas"),
            ("Areas appropriate for further agreement building", "partial_alignment"), ("Procedural considerations", "procedural_considerations"), ("Other professional comments", "professional_comments"))


def _legal_status(p: dict, st: dict) -> str:
    if p.get("is_sample"):
        return "SAMPLE ONLY"
    return {"finalized": f"Finalized · Version {st.get('legal_version', 1)}", "professional_review": "Professional Review"}.get(st.get("legal_status"), "Draft")


def _legal_generated(pdf: FPDF, d: dict, case: dict) -> None:
    j = d.get("joint") or {}
    _label(pdf, "4. INDIVIDUAL PARENT ASSESSMENT SUMMARY")
    _body(pdf, "Parent-reported information. Disputed statements are not presented as established facts.", italic=True)
    _legal_parent(pdf, f"Parent A — {case.get('parent_a') or ''}", d.get("parent_a_summary") or {})
    _legal_parent(pdf, f"Parent B — {case.get('parent_b') or ''}", d.get("parent_b_summary") or {})
    _label(pdf, "5. JOINT ASSESSMENT FINDINGS")
    if not j.get("available"):
        _body(pdf, j.get("note") or "No completed Joint Assessment was available at the time this draft was generated.", italic=True)
    for title, key in (("Areas of alignment", "alignment"), ("Areas of difference", "differences"), ("Unresolved issues", "unresolved"), ("Shared child-focused priorities", "shared_priorities"), ("Potential areas for agreement", "potential_agreement")):
        if j.get("available"):
            _stmt_list(pdf, title, j.get(key) or [], "None identified.")
    _label(pdf, "6. CHILD-FOCUSED ISSUES")
    for it in d.get("child_focused_summary") or []:
        _body(pdf, f"• {it['topic']}: {it['text']}", indent=4)
    if not d.get("child_focused_summary"):
        _body(pdf, "No child-specific subjects were available in the case records.", italic=True)
    pdf.ln(2)
    _label(pdf, "7. COMMUNICATION AND CONFLICT PATTERNS")
    for it in d.get("communication_summary") or []:
        _body(pdf, f"• {it['pattern']}: {it['text']}", indent=4)
    pdf.ln(2)


def build_legal_report_pdf(p: dict) -> bytes:
    """Professional Legal Report (12 sections). Watermarked DRAFT until certified; SAMPLE for the fictional sample."""
    st, case, pro = p["report"], p["case"], p.get("professional") or {}
    d = st.get("legal_draft") or {}
    pdf = _new_pdf()
    if p.get("is_sample"):
        pdf.watermark_text = "SAMPLE"
    elif not st.get("professional_certified") or st.get("legal_status") != "finalized":
        pdf.watermark_text = "DRAFT - NOT CERTIFIED"
    _letterhead(pdf, pro, [" · ".join(x for x in (pro.get("pro_role"), pro.get("organization")) if x), _contact_line(pro)])
    pdf.set_font(FONT, "B", 16)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, "Professional Legal Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*GRAY)
    status = _legal_status(p, st)
    pdf.cell(0, 5, _s(f"SA CoParents Align · Legal Lens · Report status: {status}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    _label(pdf, "1. CASE INFORMATION")
    court = case.get("court") or {}
    child = case.get("child_name") if p.get("is_sample") else ((case.get("child_name") or "")[:1] and f"{case['child_name'][0]}.")
    _legal_kv(pdf, [("Case ID", case.get("case_code")), ("Court case number", court.get("cause_number")), ("Court", court.get("court_name")), ("Professional", pro.get("name")), ("Professional role", st.get("role") or pro.get("pro_role")),
                    ("Parent A", case.get("parent_a")), ("Parent B", case.get("parent_b")), ("Children", child), ("Date generated", (d.get("generated_at") or p.get("date") or "")[:10]), ("Report status", status)])
    pdf.ln(2)
    _label(pdf, "2. PURPOSE OF REPORT")
    _body(pdf, p.get("purpose", ""))
    pdf.ln(2)
    _stmt_list(pdf, "3. Information reviewed", p.get("information_reviewed") or [], "No records were available.")
    _legal_generated(pdf, d, case)
    if pdf.get_y() > pdf.h - 70:
        pdf.add_page()
    _label(pdf, "8. PROFESSIONAL LEGAL LENS")
    _body(pdf, "The following section is reserved for the reviewing professional's independent observations and analysis.", italic=True)
    for title, key in LENS_PDF:
        _stmt_text(pdf, title, st.get(key))
    if st.get("framework"):
        _body(pdf, f"Co-Parenting Ability Level: {st['framework'].get('score')}/10 — {st['framework'].get('label')}", italic=True)
        pdf.ln(1)
    _stmt_list(pdf, "9. Options and resources", (st.get("options_resources") or []) + (st.get("options_custom") or []), "None selected by the professional.")
    _body(pdf, "Options are identified for professional consideration only; none is stated to be legally required unless an entered court order provides otherwise.", italic=True)
    pdf.ln(2)
    _stmt_list(pdf, "10. Possible conflict-resolution path", st.get("conflict_resolution_paths") or [], "Not yet selected.")
    _stmt_text(pdf, "Professional explanation", st.get("conflict_resolution_explanation"))
    if d.get("safety_notice"):
        _label(pdf, "11. SAFETY CONSIDERATIONS")
        _body(pdf, p.get("safety_notice_text") or "", italic=True)
        pdf.ln(2)
    _label(pdf, "12. PROFESSIONAL STATEMENT AND CERTIFICATION")
    _body(pdf, p.get("certification_text", ""), italic=True)
    if st.get("professional_certified"):
        c = st.get("certification") or {}
        _legal_kv(pdf, [("Certified by", st.get("professional_certified_name")), ("Date", st.get("professional_certified_date")), ("Title", c.get("title")), ("Bar number", c.get("bar_number")),
                        ("Firm / organization", c.get("organization")), ("Email", c.get("email")), ("Phone", c.get("phone")), ("Finalized", (st.get("finalized_at") or "")[:19].replace("T", " ") + " UTC"), ("Version", st.get("legal_version"))])
    else:
        _body(pdf, "NOT YET CERTIFIED — DRAFT. Professional review and certification are required before this report is final.", italic=True)
    pdf.ln(2)
    _body(pdf, "Parent-reported statements remain identified as parent-reported information. This report makes no custody recommendation, credibility finding or legal conclusion. Prepared through SA CoParents Align.", italic=True)
    return bytes(pdf.output())



def build_communications_log_pdf(r: dict) -> bytes:
    """Exhibit: chronological list of every email/notice sent for a case."""
    pdf = _new_pdf()
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents Align", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, _s("Case Communications Log"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(*GRAY)
    meta = f"Case {r.get('case_code') or '-'}  |  {r.get('subject_label') or ''}  |  Child: {r.get('child_name') or ''}  |  Prepared by {r.get('professional_name') or 'Professional'}  |  Generated {r['generated']}"
    pdf.multi_cell(0, 4.5, _s(meta), new_x="LMARGIN", new_y="NEXT")
    _footnote(pdf, "System-generated record of every email, reminder, and court notice sent through SA CoParents Align for this case. Message bodies are not reproduced; recipient addresses are partially masked.")
    pdf.ln(3)
    widths = (34, 40, 66, 34)
    pdf.set_font(FONT, "B", 8.5)
    pdf.set_fill_color(240, 236, 246)
    pdf.set_text_color(*PURPLE)
    for w, h in zip(widths, ("Sent (UTC)", "Type", "Subject", "Recipient")):
        pdf.cell(w, 6, h, border="B", fill=True)
    pdf.ln(6)
    pdf.set_font(FONT, "", 8.5)
    pdf.set_text_color(*BODY)
    if not r["items"]:
        _prep_line(pdf, "No communications have been sent for this case.", italic=True)
    for c in r["items"]:
        if pdf.get_y() > pdf.h - 30:
            pdf.add_page()
        x0, y0 = pdf.get_x(), pdf.get_y()
        cells = (c["at"][:16].replace("T", " "), c["kind_label"], c["subject"], f"{c['to_role']} {c['to_masked']}".strip())
        bottom = y0
        x = x0
        for w, t in zip(widths, cells):
            pdf.set_xy(x, y0)
            pdf.multi_cell(w, 4.2, _s(t), border=0, new_x="RIGHT", new_y="TOP", max_line_height=4.2)
            bottom = max(bottom, pdf.get_y())
            x += w
        pdf.set_xy(x0, bottom + 1.2)
        pdf.set_draw_color(230, 226, 238)
        pdf.line(x0, pdf.get_y() - 0.6, x0 + sum(widths), pdf.get_y() - 0.6)
    return bytes(pdf.output())


def build_session_prep_pdf(r: dict) -> bytes:
    pdf = _new_pdf()
    pdf.set_auto_page_break(auto=False)
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents Align", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, _s("Session Prep Sheet - Facilitator Agenda"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(*GRAY)
    meta = f"Case {r.get('case_code') or '-'}  |  {r['subject_label']}  |  Child: {r['child_name']}  |  {r['parent_a_name']} / {r['parent_b_name']}  |  {r['date']}"
    pdf.multi_cell(0, 4.5, _s(meta), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "I", 8)
    pdf.multi_cell(0, 4, _s("Private facilitator working document. Neutral by design: it organizes perspectives and never recommends custody or judges a parent."), new_x="LMARGIN", new_y="NEXT")

    _prep_heading(pdf, "1. Open with shared ground (3-5 min)")
    for s in r["alignment_statements"][:4]:
        _prep_line(pdf, s)

    _prep_heading(pdf, "2. Top differences to work through")
    diffs = [d for d in r["differences"]][:3]
    if not diffs:
        _prep_line(pdf, "No significant differences identified - use the time to firm up options.", italic=True)
    for d in diffs:
        pdf.set_x(pdf.l_margin + 3)
        pdf.set_font(FONT, "B", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 4.6, _s(d["area"]), new_x="LMARGIN", new_y="NEXT")
        _prep_line(pdf, d["reframe"], size=8.5, italic=True)

    _prep_heading(pdf, "3. Opening questions")
    for q in (r["conversation"][:3] + r["questions"][:2]):
        _prep_line(pdf, q)

    _prep_heading(pdf, "4. Options on the table")
    for o in r["options"][:4]:
        _prep_line(pdf, o)

    _prep_heading(pdf, "5. Close - choose one or two next steps")
    for s in r["next_steps"][:4]:
        _prep_checkbox(pdf, s)

    pdf.ln(3)
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s(f'"{r["philosophy"]}"'), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _closing_kv_rows(pdf: FPDF, r: dict) -> None:
    rows = [
        ("Case opened", _fmt_date(r.get("created_at"))),
        ("Case closed", _fmt_date(r.get("closed_at"))),
        ("Closed by", r.get("closed_by_name") or r.get("professional_name", "")),
        ("Professional reference", r.get("case_reference") or "—"),
        ("Child", r.get("child_name", "")),
    ]
    for label, value in rows:
        pdf.set_font(FONT, "B", 10)
        pdf.set_text_color(*DARK)
        pdf.cell(55, 6.5, _s(label))
        pdf.set_font(FONT, "", 10)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(0, 6.5, _s(str(value)), new_x="LMARGIN", new_y="NEXT")


def _participation_line(r: dict, role: str) -> str:
    p = (r.get("participants") or {}).get(role) or {}
    resp = (r.get("responses") or {}).get(role)
    if resp:
        status = f"Completed {_fmt_date(resp.get('completed_at'))}"
    elif p.get("accepted"):
        status = "Accepted, not completed"
    else:
        status = "Invited, not completed"
    return f"Parent {role.upper()}: {p.get('name') or '—'} — {status}"


def _closing_sections(pdf: FPDF, r: dict) -> None:
    _section_title(pdf, 1, "Parent participation")
    for role in ("a", "b"):
        _body(pdf, _participation_line(r, role))
    pdf.ln(2)
    _section_title(pdf, 2, "Joint Alignment Report")
    generated = r.get("report_generated_at")
    _body(pdf, f"Report first generated: {_fmt_date(generated)}" if generated else "No Joint Alignment Report was generated for this case.")
    _body(pdf, f"Report views: {r.get('view_count', 0)}   PDF downloads: {r.get('download_count', 0)}")
    pdf.ln(2)
    _section_title(pdf, 3, "Session outcome")
    outcome = r.get("session_outcome") or {}
    steps = outcome.get("chosen_steps") or []
    if not steps and not outcome.get("summary"):
        _body(pdf, "No session outcome was recorded.", italic=True)
    for s in steps[:8]:
        _bullet(pdf, s)
    if outcome.get("summary"):
        _body(pdf, outcome["summary"], italic=True)
    if outcome.get("recorded_at"):
        _label(pdf, f"Recorded {_fmt_date(outcome['recorded_at'])} by {outcome.get('recorded_by') or r.get('professional_name', '')}")
    pdf.ln(2)
    _section_title(pdf, 4, "Closing note")
    _body(pdf, r.get("closed_note") or "No closing note recorded.", italic=not r.get("closed_note"))
    pdf.ln(2)
    _section_title(pdf, 5, "Case timeline")
    for ev in (r.get("lifecycle") or [])[:6]:
        _body(pdf, f"{str(ev.get('at', ''))[:16].replace('T', ' ')} — {ev.get('action', '')} ({ev.get('by_name', '')})")


def build_closing_summary_pdf(r: dict) -> bytes:
    """One-page case closing summary for the professional's file."""
    pdf = _new_pdf()
    pdf.set_auto_page_break(auto=False)
    _title_header(pdf, "Case Closing Summary", [
        f"Case ID: {r.get('case_code') or r.get('id', '')[:8]}",
        f"Subject: {r.get('subject_label', 'Joint Alignment Report')}",
        f"Professional: {r.get('professional_name', '')}",
    ])
    pdf.ln(4)
    _closing_kv_rows(pdf, r)
    pdf.ln(3)
    _closing_sections(pdf, r)
    pdf.ln(3)
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s("This summary records administrative case activity only. It contains no parent assessment responses and is not a finding, recommendation, or evaluation."))
    return bytes(pdf.output())
