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


def build_agreement_pdf(r):
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
        f"Parents: {r['parent_a_name']} / {r['parent_b_name']}",
        r["date"],
    ]:
        pdf.cell(0, 6, _s(line), align="C", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 3
    pdf.set_draw_color(220, 215, 230)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)

    _body(pdf, r["purpose"])
    pdf.ln(2)
    _body(pdf, r["confidentiality_note"], italic=True)
    pdf.ln(4)

    status_colors = {"Likely aligned": GREEN, "Close": YELLOW, "Needs discussion": BLUE}
    for t in r["terms"]:
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(120, 7, _s(t["label"]))
        pdf.set_text_color(*status_colors.get(t["status"], BLUE))
        pdf.cell(0, 7, _s(t["status"]), new_x="LMARGIN", new_y="NEXT")
        _label(pdf, f"{r['parent_a_name']}'s Proposal")
        _body(pdf, t["parent_a"], indent=4)
        _label(pdf, f"{r['parent_b_name']}'s Proposal")
        _body(pdf, t["parent_b"], indent=4)
        pdf.ln(3)

    _body(pdf, r["next_note"], italic=True)
    pdf.ln(8)

    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Signatures", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for name in (r["parent_a_name"], r["parent_b_name"]):
        pdf.set_font("helvetica", "B", 10.5)
        pdf.cell(0, 6, _s(name), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.l_margin + 80, y)
        pdf.line(pdf.l_margin + 95, y, pdf.l_margin + 140, y)
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(pdf.l_margin, y + 1)
        pdf.cell(80, 5, "Signature")
        pdf.set_xy(pdf.l_margin + 95, y + 1)
        pdf.cell(45, 5, "Date", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 8, _s(r["philosophy_heading"]), align="C")
    pdf.ln(1)
    _body(pdf, f'"{r["philosophy"]}"', italic=True)

    return bytes(pdf.output())


def build_case_pdf(r):
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
        f"Assessment: {r['assessment_title']}",
        f"Parents: {r['parent_a_name']} / {r['parent_b_name']}",
        str(r.get("generated_at", ""))[:10],
    ]:
        pdf.cell(0, 6, _s(line), align="C", new_x="LMARGIN", new_y="NEXT")
    if r.get("is_demo"):
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 6, "Demo report - sample data", align="C", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 3
    pdf.set_draw_color(220, 215, 230)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(6)

    titles = r["page_titles"]

    _section_title(pdf, 1, titles[0])
    for item in r["purpose_items"]:
        _bullet(pdf, item)
    _body(pdf, r["disclaimer"], italic=True)
    snap = r["snapshot"]
    _body(pdf, f"Topics: {snap['total']}  |  Strong alignment: {snap['aligned']}  |  Differences: {snap['different']}  |  Needs more information: {snap['info']}")
    _body(pdf, r["snapshot_note"], italic=True)

    _section_title(pdf, 2, titles[1])
    for g in r["shared_goals"]:
        _bullet(pdf, g)
    _label(pdf, f"{r['parent_a_name']}'s primary concern")
    _body(pdf, r["parent_a_concern"] or "Not provided.", italic=True, indent=4)
    _label(pdf, f"{r['parent_b_name']}'s primary concern")
    _body(pdf, r["parent_b_concern"] or "Not provided.", italic=True, indent=4)
    _body(pdf, r["central_question"], italic=True)

    _section_title(pdf, 3, titles[2])
    if not r["alignments"]:
        _body(pdf, "No strong alignment areas were identified yet.", italic=True)
    for a in r["alignments"]:
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*GREEN)
        pdf.cell(0, 7, _s(a["topic"]), new_x="LMARGIN", new_y="NEXT")
        _body(pdf, a["text"], indent=4)
    _body(pdf, r["alignment_foundation_note"], italic=True)

    _section_title(pdf, 4, titles[3])
    if not r["differences"]:
        _body(pdf, "No significant differences in perspective were identified.", italic=True)
    for d in r["differences"]:
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _s(d["topic"]), new_x="LMARGIN", new_y="NEXT")
        _label(pdf, f"{r['parent_a_name']}'s Perspective")
        _body(pdf, d["parent_a"], indent=4)
        _label(pdf, f"{r['parent_b_name']}'s Perspective")
        _body(pdf, d["parent_b"], indent=4)
        pdf.ln(2)
    _body(pdf, r["differences_note"], italic=True)

    _section_title(pdf, 5, titles[4])
    for n in r["child_needs"]:
        _bullet(pdf, n)

    _section_title(pdf, 6, titles[5])
    for o in r["options"]:
        _bullet(pdf, o)
    _body(pdf, f"{r['options_note']} This distinction preserves the educational and resource nature of this report.", italic=True)

    _section_title(pdf, 7, titles[6])
    for q in r["conversation_questions"]:
        _bullet(pdf, q if isinstance(q, str) else str(q))
    _body(pdf, r["central_question"], italic=True)

    _section_title(pdf, 8, titles[7])
    pm = r.get("professional_map") or {}
    for s_item in pm.get("sequence") or []:
        _bullet(pdf, s_item if isinstance(s_item, str) else str(s_item))
    _body(pdf, f"Alignment areas: {pm.get('alignment_count', 0)}  |  Conversation areas: {pm.get('conversation_count', 0)}  |  Needs professional input: {pm.get('professional_input_count', 0)}  |  Child needs: {pm.get('child_needs_count', 0)}")

    _section_title(pdf, 9, titles[8])
    for item in r["action_plan"]:
        pdf.set_font("helvetica", "B", 11)
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

    pdf.ln(8)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 9, _s(r["philosophy_heading"]), align="C")
    pdf.ln(1)
    _body(pdf, r["philosophy_note"])
    _body(pdf, f'"{r["philosophy"]}"', italic=True)

    return bytes(pdf.output())


def build_complete_pdf(r):
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
    pdf.multi_cell(0, 10, _s(r["title"]), align="C")
    pdf.ln(2)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(*GRAY)
    lines = [r["subtitle"], r["generated_at"]]
    if r.get("prepared_by"):
        lines.insert(1, f"Prepared by: {r['prepared_by']}")
    if r.get("children"):
        lines.append(f"Children: {', '.join(r['children'])}")
    for line in lines:
        pdf.cell(0, 6, _s(line), align="C", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 3
    pdf.set_draw_color(220, 215, 230)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(6)

    _section_title(pdf, 1, "Purpose of This Report")
    _body(pdf, r["purpose"])
    t = r["totals"]
    _body(pdf, f"Strong alignment: {t['aligned']}  |  Differences in perspective: {t['different']}  |  Needs more information: {t['info']}")
    _body(pdf, r["totals_note"], italic=True)

    for i, sec in enumerate(r["sections"], start=2):
        _section_title(pdf, i, sec["title"])
        if sec.get("child_name"):
            _body(pdf, f"Child: {sec['child_name']}", italic=True)
        if sec["kind"] == "assessment":
            s = sec["snapshot"]
            _body(pdf, f"Topics: {s['total']}  |  Strong alignment: {s['aligned']}  |  Differences: {s['different']}  |  Needs more information: {s['info']}")
            for a in sec["alignments"]:
                pdf.set_font("helvetica", "B", 10.5)
                pdf.set_text_color(*GREEN)
                pdf.cell(0, 6, _s(a["topic"]), new_x="LMARGIN", new_y="NEXT")
                _body(pdf, a["text"], indent=4)
            for d in sec["differences"]:
                pdf.set_font("helvetica", "B", 10.5)
                pdf.set_text_color(*DARK)
                pdf.cell(0, 6, _s(d["topic"]), new_x="LMARGIN", new_y="NEXT")
                _body(pdf, d["parent_a"], indent=4)
                _body(pdf, d["parent_b"], indent=4)
            if sec.get("priority"):
                _body(pdf, f"Priority: {sec['priority']}", italic=True)
        else:
            for stmt in sec["alignment_statements"]:
                _bullet(pdf, stmt)
            for row in sec["alignment_map"]:
                color = GREEN if row["status"] == "Strong alignment" else (YELLOW if row["status"] == "Moderate alignment" else BLUE)
                pdf.set_font("helvetica", "B", 10.5)
                pdf.set_text_color(*DARK)
                pdf.cell(90, 7, _s(row["area"]))
                pdf.set_text_color(*color)
                pdf.cell(0, 7, _s(row["status"]), new_x="LMARGIN", new_y="NEXT")
            for d in sec["differences"]:
                pdf.set_font("helvetica", "B", 10.5)
                pdf.set_text_color(*DARK)
                pdf.cell(0, 6, _s(d["area"]), new_x="LMARGIN", new_y="NEXT")
                _body(pdf, d["parent_a"], indent=4)
                _body(pdf, d["parent_b"], indent=4)
                _body(pdf, d["reframe"], italic=True, indent=4)
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

    pdf.ln(6)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 9, _s(r["philosophy_heading"]), align="C")
    pdf.ln(1)
    _body(pdf, r["philosophy_note"])
    _body(pdf, f'"{r["philosophy"]}"', italic=True)

    return bytes(pdf.output())
