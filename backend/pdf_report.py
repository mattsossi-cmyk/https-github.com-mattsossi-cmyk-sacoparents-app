from pathlib import Path
from io import BytesIO

import qrcode
from fpdf import FPDF

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

    def footer(self):
        if self.watermark_text:
            self.set_font(FONT, "B", 52)
            self.set_text_color(235, 230, 242)
            with self.rotation(40, self.w / 2, self.h / 2):
                self.text(self.w / 2 - 68, self.h / 2, self.watermark_text)
        self.set_y(-14)
        self.set_font(FONT, "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, _s(f"Copyright 2026 SA CoParents. All Rights Reserved. - sacoparentsalign.com - Page {self.page_no()}"), align="C")


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
    _section_title(pdf, 7, "Options and Resources")
    _body(pdf, "Neutral options - SA CoParents does not decide; it builds options.", italic=True)
    for o in r["options"]:
        _bullet(pdf, o)
    _section_title(pdf, 8, "Potential Areas of Alignment")
    _body(pdf, r["alignment_paragraph"], italic=True)
    _section_title(pdf, 9, "Questions for the Parents")
    for q in r["questions"]:
        _bullet(pdf, q)
    _section_title(pdf, 10, "Possible Next Steps")
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
    pdf.ln(4)

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


def build_court_cover_letter_pdf(p: dict) -> bytes:
    """Professional's cover letter to the court + packet index (pages 1-2 of a Court Packet)."""
    pro = p.get("professional") or {}
    pdf = _new_pdf()
    pdf.set_font(FONT, "B", 13)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 7, _s(pro.get("name") or "Professional"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*GRAY)
    for line in [pro.get("pro_role"), pro.get("organization"),
                 " · ".join(x for x in (pro.get("license_number") and f"License {pro['license_number']}", pro.get("phone"), pro.get("email")) if x),
                 " ".join(x for x in (pro.get("city"), pro.get("state")) if x)]:
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


def merge_pdfs(parts: list[bytes]) -> bytes:
    import pymupdf
    out = pymupdf.open()
    for b in parts:
        with pymupdf.open(stream=b, filetype="pdf") as src:
            out.insert_pdf(src)
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
