from fpdf import FPDF

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


def _s(text):
    t = str(text)
    for a, b in _REPLACEMENTS:
        t = t.replace(a, b)
    return t.encode("latin-1", "replace").decode("latin-1")


class _JointPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, _s(f"SA CoParents - Page {self.page_no()}"), align="C")


def _section_title(pdf, num, title):
    pdf.ln(4)
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(*TEAL)
    pdf.cell(8, 8, _s(f"{num}."))
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, _s(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _body(pdf, text, italic=False, indent=0):
    pdf.set_font("helvetica", "I" if italic else "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.set_x(pdf.l_margin + indent)
    pdf.multi_cell(0, 5.5, _s(text))
    pdf.ln(1)


def _bullet(pdf, text):
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("helvetica", "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5.5, _s(f"-  {text}"))


def _label(pdf, text):
    pdf.set_font("helvetica", "B", 9.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, _s(text), new_x="LMARGIN", new_y="NEXT")


def build_joint_pdf(r):
    pdf = _JointPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, "SA CoParents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("helvetica", "B", 22)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 10, _s(r["report_title"]), align="C")
    pdf.ln(2)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(*GRAY)
    for line in [
        f"Child: {r['child_name']}",
        f"Subject: {r['subject_label']}",
        f"Participants: {r['parent_a_name']} / {r['parent_b_name']}",
        r["date"],
    ]:
        pdf.cell(0, 6, _s(line), align="C", new_x="LMARGIN", new_y="NEXT")
    imported = r.get("imported") or {}
    if imported.get("a") or imported.get("b"):
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 6, _s("Includes material imported from sacoparentsapp.online"), align="C", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 3
    pdf.set_draw_color(220, 215, 230)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)

    _section_title(pdf, 1, "Purpose of This Report")
    _body(pdf, r["purpose"])

    _section_title(pdf, 2, "What Both Parents Agree About")
    pdf.set_font("helvetica", "B", 10.5)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 6, _s("Strong Alignment - both parents indicated that:"), new_x="LMARGIN", new_y="NEXT")
    for stmt in r["alignment_statements"]:
        _bullet(pdf, stmt)

    _section_title(pdf, 3, "Where the Parents See Things Differently")
    if not r["differences"]:
        _body(pdf, "No significant differences in perspective were identified.", italic=True)
    for d in r["differences"]:
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _s(d["area"]), new_x="LMARGIN", new_y="NEXT")
        _label(pdf, f"{r['parent_a_name']}'s Perspective")
        _body(pdf, d["parent_a"], indent=4)
        _label(pdf, f"{r['parent_b_name']}'s Perspective")
        _body(pdf, d["parent_b"], indent=4)
        _body(pdf, d["reframe"], italic=True, indent=4)
        pdf.ln(2)

    _section_title(pdf, 4, "Child's Identified Needs")
    for n in r["child_needs"]:
        _bullet(pdf, n)

    _section_title(pdf, 5, "Alignment Map")
    for row in r["alignment_map"]:
        color = GREEN if row["status"] == "Strong alignment" else (YELLOW if row["status"] == "Moderate alignment" else BLUE)
        pdf.set_font("helvetica", "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(90, 7, _s(row["area"]))
        pdf.set_text_color(*color)
        pdf.cell(0, 7, _s(row["status"]), new_x="LMARGIN", new_y="NEXT")

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

    pdf.ln(8)
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 8, _s(r["philosophy_heading"]), align="C")
    pdf.ln(1)
    _body(pdf, r["philosophy_note"])
    _body(pdf, f'"{r["philosophy"]}"', italic=True)

    return bytes(pdf.output())
