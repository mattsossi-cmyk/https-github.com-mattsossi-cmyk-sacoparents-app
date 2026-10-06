"""Mockup-styled layout blocks for the Professional Alignment Report PDF (brand header, cards, score boxes, pathway steps)."""
from fpdf import FPDF
from fpdf.fonts import FontFace

from pdf_report import FONT, PURPLE, TEAL, BLUE, GREEN, GRAY, DARK, BODY, _s, _body, _stmt_text, _lens_heading, _lens_subhead, _lens_table, _lens_individual_scale, _lens_joint_scale, _legal_kv, _new_pdf
from safety_import import screening_summary

GOLD_FILL, PURPLE_FILL, TEAL_FILL, BLUE_FILL, GREEN_FILL, ORANGE_FILL, GOLD_SOFT = (255, 243, 201), (243, 237, 251), (232, 247, 247), (234, 244, 251), (234, 247, 241), (255, 240, 232), (255, 247, 223)
ORANGE, GOLD = (216, 105, 54), (214, 156, 32)
SLATE, SLATE_FILL = (100, 116, 139), (241, 245, 249)
SECTION_COLORS = {0: (PURPLE, PURPLE_FILL), 1: (SLATE, SLATE_FILL), 2: (PURPLE, PURPLE_FILL), 3: (PURPLE, PURPLE_FILL), 4: (BLUE, BLUE_FILL), 5: (TEAL, TEAL_FILL), 6: (TEAL, TEAL_FILL),
                  7: (BLUE, BLUE_FILL), 8: (GREEN, GREEN_FILL), 9: (ORANGE, ORANGE_FILL), 10: (BLUE, BLUE_FILL), 11: (GOLD, GOLD_SOFT)}
LENS_FIELD_TITLES = {"safety_takeaway": "Safety takeaway", "parent_a_growth": "Parent A key growth areas", "parent_b_growth": "Parent B key growth areas", "joint_notes": "Joint dynamic summary",
                     "conflict_management_rationale": "Conflict resolution rationale", "short_term_goals": "Short-term goals", "long_term_goals": "Long-term goals",
                     "alignment_summary": "Professional alignment summary", "professional_summary": "Professional statement", "shared_concerns": "Shared concerns", "pathway_rationale": "Pathway rationale"}
_lines = lambda t: [g.strip() for g in (t or "").split("\n") if g.strip()]  # noqa: E731


def brand_header(pdf: FPDF) -> None:
    y = pdf.get_y()
    pdf.set_fill_color(*PURPLE)
    pdf.ellipse(pdf.l_margin, y, 12, 12, style="F")
    pdf.set_fill_color(*TEAL)
    pdf.ellipse(pdf.l_margin + 6, y, 6, 12, style="F")
    pdf.set_xy(pdf.l_margin + 15, y)
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*PURPLE)
    pdf.cell(pdf.get_string_width("SA CoParents ") + 1, 8, "SA CoParents ")
    pdf.set_text_color(*TEAL)
    pdf.cell(30, 8, "Align")
    pdf.set_xy(pdf.l_margin + 15, y + 7.5)
    pdf.set_font(FONT, "B", 8.5)
    pdf.set_text_color(*BLUE)
    pdf.cell(100, 4, "Starting With Alignment, Ending With Agreement")
    pdf.set_xy(pdf.w - pdf.r_margin - 40, y)
    pdf.set_font(FONT, "B", 7)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(40, 3.6, "CHILD FOCUSED\nSOLUTIONS\nSTRONGER TOMORROWS", align="R")
    pdf.set_draw_color(*PURPLE)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, y + 14, pdf.w - pdf.r_margin, y + 14)
    pdf.set_xy(pdf.l_margin, y + 18)


def new_page(pdf: FPDF) -> None:
    if pdf.get_y() > pdf.t_margin + 20:
        pdf.add_page()


def _paint(pdf, x, w, title, lines, title_color):
    pdf.set_xy(x + 3, pdf.get_y() + 3)
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*title_color)
    pdf.multi_cell(w - 6, 5, _s(title))
    pdf.set_font(FONT, "", 8.3)
    pdf.set_text_color(*BODY)
    for ln in lines:
        pdf.set_x(x + 3)
        pdf.multi_cell(w - 6, 4.0, _s(ln) if ln else " ")


def _measure(pdf, w, title, lines) -> float:
    pdf.set_font(FONT, "B", 10)
    h = pdf.multi_cell(w - 6, 5, _s(title), dry_run=True, output="HEIGHT")
    pdf.set_font(FONT, "", 8.3)
    return h + sum(pdf.multi_cell(w - 6, 4.0, _s(ln) if ln else " ", dry_run=True, output="HEIGHT") for ln in lines) + 6


def card(pdf: FPDF, x: float, w: float, title: str, lines: list, fill: tuple, title_color=BLUE, h_min: float = 0) -> float:
    """Soft rounded card (measured with dry-run, then painted). Returns height; cursor left at top."""
    y = pdf.get_y()
    h = max(_measure(pdf, w, title, lines), h_min)
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(220, 215, 230)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2.5)
    pdf.set_y(y)
    _paint(pdf, x, w, title, lines, title_color)
    pdf.set_xy(pdf.l_margin, y)
    return h


def full_card(pdf, title, lines, fill, title_color=BLUE) -> None:
    w = pdf.w - pdf.l_margin - pdf.r_margin
    if pdf.get_y() + _measure(pdf, w, title, lines) > pdf.h - pdf.b_margin:
        new_page(pdf)
    h = card(pdf, pdf.l_margin, w, title, lines, fill, title_color)
    pdf.set_y(pdf.get_y() + h + 4)


def cards_row(pdf: FPDF, cards: list, subhead: str | None = None) -> None:
    """cards: (title, lines, fill, title_color); equal widths, equal heights; moves to a new page (with optional subhead kept together) if it would overflow."""
    gap, n = 4, len(cards)
    w = (pdf.w - pdf.l_margin - pdf.r_margin - gap * (n - 1)) / n
    h = max(_measure(pdf, w, t, ls) for t, ls, _, _ in cards)
    if h > pdf.h - pdf.t_margin - pdf.b_margin - 30:
        if subhead:
            _lens_subhead(pdf, subhead)
        for t, ls, f, tc in cards:
            full_card(pdf, t, ls, f, tc)
        return
    if pdf.get_y() + h + (7 if subhead else 0) > pdf.h - pdf.b_margin:
        new_page(pdf)
    if subhead:
        _lens_subhead(pdf, subhead)
    y = pdf.get_y()
    for i, (t, ls, f, tc) in enumerate(cards):
        pdf.set_y(y)
        card(pdf, pdf.l_margin + i * (w + gap), w, t, ls, f, tc, h_min=h)
    pdf.set_y(y + h + 4)


def score_boxes(pdf: FPDF, items: list) -> None:
    gap, n = 4, len(items)
    w = (pdf.w - pdf.l_margin - pdf.r_margin - gap * (n - 1)) / n
    y = pdf.get_y()
    for i, (label, score, band, fill) in enumerate(items):
        x = pdf.l_margin + i * (w + gap)
        pdf.set_fill_color(*fill)
        pdf.rect(x, y, w, 27, style="F", round_corners=True, corner_radius=2.5)
        for yy, size, color, txt, style in ((1.5, 9, DARK, label, "B"), (6.5, 22, PURPLE, str(score) if score else "—", "B"), (16.5, 8, GRAY, "/10", ""), (20.5, 8, DARK, band or "Not yet rated", "B")):
            pdf.set_xy(x, y + yy)
            pdf.set_font(FONT, style, size)
            pdf.set_text_color(*color)
            pdf.cell(w, 11 if size == 22 else 5, _s(txt), align="C")
    pdf.set_y(y + 31)


def kv_table(pdf: FPDF, rows: list) -> None:
    pdf.set_font(FONT, "", 9)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(*BODY)
    with pdf.table(col_widths=[45, 137], text_align="LEFT", line_height=4.6, first_row_as_headings=False, borders_layout="ALL") as table:
        for k, v in rows:
            row = table.row()
            row.cell(_s(k), style=FontFace(emphasis="BOLD", color=DARK))
            row.cell(_s(str(v or "—")))
    pdf.ln(2)


def pathway_steps(pdf: FPDF, pathways: list, chosen: set) -> None:
    gap, n = 3, len(pathways)
    w = (pdf.w - pdf.l_margin - pdf.r_margin - gap * (n - 1)) / n
    y = pdf.get_y()
    for i, p in enumerate(pathways):
        x, sel = pdf.l_margin + i * (w + gap), p["key"] in chosen
        pdf.set_fill_color(*(TEAL_FILL if sel else PURPLE_FILL))
        pdf.set_draw_color(*(TEAL if sel else (217, 204, 239)))
        pdf.set_line_width(0.6 if sel else 0.2)
        pdf.rect(x, y, w, 34, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_fill_color(*PURPLE)
        pdf.ellipse(x + w / 2 - 3.5, y + 2.5, 7, 7, style="F")
        pdf.set_xy(x, y + 3)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(w, 6, str(i + 1), align="C")
        pdf.set_xy(x + 1.5, y + 11)
        pdf.set_font(FONT, "B", 7.5)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(w - 3, 3.6, _s(p["name"]), align="C")
        if sel:
            pdf.set_fill_color(*GREEN)
            pdf.rect(x + w / 2 - 10, y + 27, 20, 5, style="F", round_corners=True, corner_radius=2.5)
            pdf.set_xy(x + w / 2 - 10, y + 27)
            pdf.set_font(FONT, "B", 6.5)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(20, 5, "SELECTED", align="C")
    pdf.set_y(y + 38)


def small_lines(pdf: FPDF, lines: list) -> None:
    pdf.set_font(FONT, "", 8.5)
    pdf.set_text_color(*BODY)
    for ln in lines:
        pdf.set_x(pdf.l_margin + 2)
        pdf.multi_cell(0, 4.2, _s(ln))
    pdf.ln(2)


def _parent_lines(rep: dict, role: str) -> list:
    from lens_data import growth_lines
    g = growth_lines(rep, role)
    met, total = sum(1 for x in g if x["met"]), len(g)
    caption = [f"{met} of {total} growth areas met ({round(met / total * 100)}%)"] if total else []
    return ([f"Current Level: {rep.get(f'parent_{role}_rating') or '—'}/10", "", "SUCCESSES"] + [f"✓ {x}" for x in _lines(rep.get(f"parent_{role}_strengths"))]
            + ["", "CHALLENGES / FAILURES"] + [f"! {x}" for x in _lines(rep.get(f"parent_{role}_gaps"))]
            + ["", "GROWTH PRIORITIES"] + [f"{'☑' if x['met'] else '☐'} {x['text']}{'  [MET at reassessment]' if x['met'] else ''}" for x in g] + caption
            + ([f"Notes: {rep.get(f'parent_{role}_notes')}"] if rep.get(f"parent_{role}_notes") else []))


def _research_base(pdf: FPDF, rb: dict | None) -> None:
    """'Research Base' footer for Section 5 — live Perplexity Sonar insight with numbered citations (professional-reviewed, never a finding)."""
    if not rb or not rb.get("text"):
        return
    cites = [f"[{c.get('index', i)}] {c.get('url', '')}" for i, c in enumerate(rb.get("citations") or [], 1)][:10]
    lines = [rb["text"], "", "SOURCES"] + (cites or ["No citations returned."]) + ["", f"Research Base — fetched {str(rb.get('fetched_at') or '')[:10]} via Perplexity {rb.get('model') or 'Sonar'}"
             + (f" for ZIP {rb['zip']}" if rb.get("zip") else "") + ". Real-time web research reviewed by the professional; not a finding, diagnosis or recommendation."]
    full_card(pdf, "RESEARCH BASE (Perplexity — professional-reviewed)", lines, TEAL_FILL, TEAL)


SOURCE_PDF = {"parent": ("PARENT-REPORTED", BLUE), "system": ("SYSTEM-GENERATED COMPARISON", PURPLE), "ai": ("AI-ASSISTED DRAFT", GOLD), "professional": ("PROFESSIONAL OBSERVATION", GREEN)}


def _ai_tag(rep: dict, *keys: str) -> str:
    """Inline suffix for a card/label whose text began as an AI draft — so AI-assisted wording is visible in the body, not only the appendix."""
    drafts, review = rep.get("ai_drafts") or {}, rep.get("ai_review") or {}
    hit = [k for k in keys if k in drafts and (rep.get(k) or "").strip()]
    if not hit:
        return ""
    edited = any((review.get(k) or {}).get("edited") or (rep.get(k) or "").strip() != (drafts[k].get("text") or "").strip() for k in hit)
    return "  [AI-assisted draft — edited by professional]" if edited else "  [AI-assisted draft — reviewed by professional]"


def heading(pdf: FPDF, n: int, text: str) -> None:
    """Numbered circle badge + title + hairline, tinted per section (SECTION_COLORS), then the question it answers and its source label."""
    from lens_walkthrough import QUESTION_OF_SECTION, SOURCE_OF_SECTION
    if pdf.get_y() > pdf.h - 50:
        pdf.add_page()
    color, fill = SECTION_COLORS.get(n, (PURPLE, PURPLE_FILL))
    y = pdf.get_y()
    pdf.set_fill_color(*color)
    pdf.ellipse(pdf.l_margin, y, 7.5, 7.5, style="F")
    pdf.set_xy(pdf.l_margin, y + 0.4)
    pdf.set_font(FONT, "B", 8.5)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(7.5, 6.7, str(n) if n else "?", align="C")
    pdf.set_xy(pdf.l_margin + 10, y)
    pdf.set_font(FONT, "B", 12.5)
    pdf.set_text_color(*color)
    pdf.cell(0, 7.5, _s(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*fill)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, y + 9, pdf.w - pdf.r_margin, y + 9)
    pdf.set_line_width(0.2)
    pdf.set_y(y + 12)
    if n in QUESTION_OF_SECTION:
        label, scol = SOURCE_PDF[SOURCE_OF_SECTION[n]]
        pdf.set_x(pdf.l_margin)
        pdf.set_font(FONT, "I", 8.2)
        pdf.set_text_color(*GRAY)
        pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin - 62, 4.5, _s(QUESTION_OF_SECTION[n]))
        pdf.set_font(FONT, "B", 6.8)
        pdf.set_text_color(*scol)
        pdf.cell(62, 4.5, _s(f"SOURCE: {label}"), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)


def statement_band(pdf: FPDF) -> None:
    """Heavy divider: everything below is the professional's own statement, not parent or system content."""
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    y, w = pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_fill_color(*GREEN)
    pdf.rect(pdf.l_margin, y, w, 11, style="F")
    pdf.set_xy(pdf.l_margin + 3, y + 1)
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(w - 6, 5, _s("PROFESSIONAL STATEMENT — Sections 9 to 11"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font(FONT, "I", 7.4)
    pdf.cell(w - 6, 4, _s("From here on, the words are the professional's own observation and analysis — separate from parent-reported information (Sections 3–4) and the system-generated comparison (Sections 2, 5)."))
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(*BODY)
    pdf.set_y(y + 15)


def title_band(pdf: FPDF, title: str, sub: str) -> None:
    y, w = pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin
    steps = 40
    for i in range(steps):
        t = i / (steps - 1)
        pdf.set_fill_color(int(PURPLE[0] + (BLUE[0] - PURPLE[0]) * t), int(PURPLE[1] + (BLUE[1] - PURPLE[1]) * t), int(PURPLE[2] + (BLUE[2] - PURPLE[2]) * t))
        pdf.rect(pdf.l_margin + w * i / steps, y, w / steps + 0.3, 20, style="F")
    pdf.set_xy(pdf.l_margin, y + 2.5)
    pdf.set_font(FONT, "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(w, 9, _s(title), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 8.5)
    pdf.cell(w, 5, _s(sub), align="C")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(*DARK)
    pdf.set_y(y + 24)


def score_cards(pdf: FPDF, items: list) -> None:
    """Solid-colour score cards with white text (Parent A purple, Parent B blue, Joint teal)."""
    gap, n = 4, len(items)
    w = (pdf.w - pdf.l_margin - pdf.r_margin - gap * (n - 1)) / n
    y = pdf.get_y()
    for i, (label, score, band, color) in enumerate(items):
        x = pdf.l_margin + i * (w + gap)
        pdf.set_fill_color(*color)
        pdf.rect(x, y, w, 30, style="F", round_corners=True, corner_radius=3)
        for yy, size, txt, style in ((2, 9.5, label, "B"), (7.5, 22, f"{score}/10" if score else "—", "B"), (21, 8.5, band or "Not yet rated", "B")):
            pdf.set_xy(x, y + yy)
            pdf.set_font(FONT, style, size)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(w, 11 if size == 22 else 5, _s(txt), align="C")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_y(y + 34)


def _perspective(pdf: FPDF, rep: dict, role: str, scale, cls) -> None:
    from lens_data import growth_lines
    g = growth_lines(rep, role)
    met, total = sum(1 for x in g if x["met"]), len(g)
    growth = [f"{'☑' if x['met'] else '☐'} {x['text']}{'  [MET at reassessment]' if x['met'] else ''}" for x in g] + ([f"{met} of {total} growth areas met ({round(met / total * 100)}%)"] if total else [])
    cards_row(pdf, [("Successes", [f"✓ {x}" for x in _lines(rep.get(f"parent_{role}_strengths"))] or ["—"], GREEN_FILL, GREEN),
                    ("Challenges", [f"! {x}" for x in _lines(rep.get(f"parent_{role}_gaps"))] or ["—"], ORANGE_FILL, ORANGE),
                    ("Growth Priorities" + _ai_tag(rep, f"parent_{role}_growth"), growth or ["—"], BLUE_FILL, BLUE)])
    if rep.get(f"parent_{role}_notes"):
        _body(pdf, f"Notes: {rep[f'parent_{role}_notes']}", italic=True)
    _lens_individual_scale(pdf, scale, cls, rep, role)


def _cover_images(pdf: FPDF, images: dict) -> None:
    """Headshot and firm logo, top-right under the brand header; skipped silently if storage is unavailable."""
    from io import BytesIO
    from storage import get_object
    x, y = pdf.w - pdf.r_margin, pdf.get_y()
    for slot in ("firm_logo", "headshot"):
        path = images.get(slot)
        if not path:
            continue
        try:
            data, _ = get_object(path)
            pdf.image(BytesIO(data), x=x - 22, y=y - 1, w=22, h=22, keep_aspect_ratio=True)
            x -= 26
        except Exception:  # noqa: BLE001
            continue
    pdf.set_y(y + 23)


def cover_page(pdf: FPDF, pro: dict) -> None:
    """Page 1 — Professional Contact cover: title band, Professional Information, Purpose cards, Align→Focus→Resolve→Agree."""
    brand_header(pdf)
    title_band(pdf, "Professional Alignment Report", "Prepared for: Court • Attorneys • Mediators • Parent Facilitators • Other Authorized Professionals")
    pdf.set_font(FONT, "", 8.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, _s("Understanding Differences. Identifying Alignment. Meeting the Needs of the Child."), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    y0 = pdf.get_y()
    _lens_heading(pdf, "Professional Information")
    if pro.get("images"):
        pdf.set_y(y0)
        _cover_images(pdf, pro["images"])
        pdf.set_y(max(pdf.get_y(), y0 + 25))
    blank = "_" * 44
    kv_table(pdf, [("Professional Name", pro.get("name") or blank), ("Email", pro.get("email") or blank), ("Phone", pro.get("phone") or blank), ("Office / Mailing Address", pro.get("address") or f"{blank}\n{blank}")])
    pdf.ln(3)
    _lens_heading(pdf, "Purpose")
    full_card(pdf, "FROM DIFFERENCES TO DIRECTION", ["This report helps professionals understand where the parents align, where perspectives differ, what the child may need, and what options, resources, and resolution pathways may help."], PURPLE_FILL, PURPLE)
    full_card(pdf, "THE SA COPARENTS APPROACH", ["The goal is not to determine which parent is right. The goal is to understand the co-parenting situation, keep the child's needs at the center, and identify constructive pathways toward resolution and agreement."], TEAL_FILL, TEAL)
    pdf.ln(3)
    steps = [("ALIGN", "Understand the situation", PURPLE), ("FOCUS", "Identify child needs", TEAL), ("RESOLVE", "Explore pathways", BLUE), ("AGREE", "Build next steps", PURPLE)]
    gap, bw, y = 12, 36, pdf.get_y()
    x0 = pdf.l_margin + (pdf.w - pdf.l_margin - pdf.r_margin - (bw * 4 + gap * 3)) / 2
    for i, (t, sub, color) in enumerate(steps):
        x = x0 + i * (bw + gap)
        pdf.set_fill_color(*color)
        pdf.rect(x, y, bw, 18, style="F", round_corners=True, corner_radius=2)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(x, y + 3)
        pdf.set_font(FONT, "B", 9)
        pdf.cell(bw, 5, t, align="C")
        pdf.set_xy(x + 2, y + 8.5)
        pdf.set_font(FONT, "B", 6.5)
        pdf.multi_cell(bw - 4, 3.2, _s(sub), align="C")
        if i < 3:
            pdf.set_xy(x + bw, y + 6)
            pdf.set_font(FONT, "", 12)
            pdf.set_text_color(*PURPLE)
            pdf.cell(gap, 6, _s("→"), align="C")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(*BODY)
    pdf.set_y(y + 22)


def _legend_and_distinctions(pdf: FPDF) -> None:
    from lens_walkthrough import DISTINCTIONS, SIX_QUESTIONS, SOURCE_LEGEND
    full_card(pdf, "This report answers six questions — then gives a clearly separated Professional Statement",
              [f"Q{i}. {q}  (Section {' & '.join(map(str, s))})" for i, (q, s) in enumerate(SIX_QUESTIONS, 1)] + ["Professional Statement  (Sections 9–11) — the professional's own observation, analysis and court summary."], PURPLE_FILL, PURPLE)
    cards_row(pdf, [(f"■ {lb}", [d], {"parent": BLUE_FILL, "system": PURPLE_FILL, "ai": GOLD_SOFT, "professional": GREEN_FILL}[k], SOURCE_PDF[k][1]) for k, lb, d in SOURCE_LEGEND[:2]], subhead="Who is speaking? Every section is labelled with its source")
    cards_row(pdf, [(f"■ {lb}", [d], {"parent": BLUE_FILL, "system": PURPLE_FILL, "ai": GOLD_SOFT, "professional": GREEN_FILL}[k], SOURCE_PDF[k][1]) for k, lb, d in SOURCE_LEGEND[2:]])
    full_card(pdf, "Four distinctions to keep in mind", [f"{a}  ≠  {b}.  {n}" for a, b, n in DISTINCTIONS], (255, 255, 255), ORANGE)


def how_to_read_page(pdf: FPDF) -> None:
    """One-page reader's guide inserted after the title band."""
    from lens_walkthrough import READER_INTRO, SCALE_NOTE, WALKTHROUGH
    pdf.add_page()
    heading(pdf, 0, "How to Read This Report")
    _body(pdf, READER_INTRO, italic=True)
    _legend_and_distinctions(pdf)
    if pdf.get_y() > pdf.h - 80:
        pdf.add_page()
    pdf.set_font(FONT, "", 8.4)
    for i, (title, what, _how, guard) in enumerate(WALKTHROUGH, 1):
        if pdf.get_y() > pdf.h - 30:
            pdf.add_page()
        y = pdf.get_y()
        pdf.set_fill_color(*PURPLE)
        pdf.ellipse(pdf.l_margin, y + 0.6, 5, 5, style="F")
        pdf.set_xy(pdf.l_margin, y + 0.8)
        pdf.set_font(FONT, "B", 6.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(5, 4.6, str(i), align="C")
        pdf.set_xy(pdf.l_margin + 7, y)
        pdf.set_font(FONT, "B", 8.6)
        pdf.set_text_color(*PURPLE)
        pdf.cell(0, 5, _s(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(pdf.l_margin + 7)
        pdf.set_font(FONT, "", 8.2)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 7, 3.9, _s(f"{what}  Reader's guardrail: {guard}"), align="L")
        pdf.ln(0.6)
    full_card(pdf, "Reading the 1–10 scale", [SCALE_NOTE], TEAL_FILL, TEAL)
    new_page(pdf)


def render_lens_body(pdf: FPDF, v: dict) -> None:
    """Pages 1–6 of the Professional Alignment Report (everything before the certification block)."""
    from lens_data import CHILD_FOCUS_CATEGORIES, CONFLICT_GUIDANCE, PATHWAYS, RISK_CATEGORIES, SCALE_TABLE, SAFETY_PATHWAY
    rep, c, cls, notes = v["report"], v["case"], v["classification"], v["notes"]
    cover_page(pdf, v.get("professional") or {})
    how_to_read_page(pdf)
    heading(pdf, 1, "Case & Assessment Overview")
    kv_table(pdf, [("Case / Matter", rep.get("matter_name")), ("Case ID", c.get("case_code")), ("Court / County", rep.get("court_county")), ("Cause Number", rep.get("cause_number")),
                   ("Professional", f"{rep.get('professional_name') or ''} · {rep.get('professional_role') or ''}".strip(" ·")), ("Report Date", rep.get("report_date")),
                   ("Parent A", rep.get("parent_a_name")), ("Parent B", rep.get("parent_b_name")), ("Report Status", (rep.get("status") or "draft").replace("_", " ").title())])
    cards_row(pdf, [("Assessments Reviewed", [f"{'☑' if r['done'] else '☐'} {r['label']}" + (" (N/A)" if r.get("na") and not r["done"] else "") for r in v.get("readiness") or []], BLUE_FILL, BLUE),
                    ("Sources of Information Considered", [rep.get("sources_considered") or "—"], PURPLE_FILL, PURPLE)])
    heading(pdf, 2, "Alignment Snapshot")
    score_cards(pdf, [("Parent A", rep.get("parent_a_rating"), (cls["parent_a"] or {}).get("label"), PURPLE), ("Parent B", rep.get("parent_b_rating"), (cls["parent_b"] or {}).get("label"), BLUE),
                      ("Joint Co-Parenting", rep.get("joint_rating"), (cls["joint"] or {}).get("label"), TEAL)])
    risk = rep.get("risk_screening") or {}
    scr = v.get("safety_screening") or {}
    from safety_screening import SCALE_NOTE as _SCR_NOTE
    imported = [screening_summary(scr.get(r), rep.get(f"parent_{r}_name") or f"Parent {r.upper()}") for r in ("a", "b")] + [_SCR_NOTE]
    cards_row(pdf, [(f"Joint process: {rep.get('joint_process_appropriate') or 'Not yet determined'}" + _ai_tag(rep, "safety_takeaway"), [rep.get("safety_takeaway") or "—", "", f"Parent A FV assessment: {rep.get('fv_a_received') or '—'}", f"Parent B FV assessment: {rep.get('fv_b_received') or '—'}", *([""] + imported if imported else []), "", notes["safety"]], TEAL_FILL, TEAL),
                    ("Risk Screening Summary", [f"{lbl}: {risk.get(k, {}).get('level', 'Not assessed')}." + (f" {risk[k]['note']}" if risk.get(k, {}).get("note") else "") for k, lbl, _ in RISK_CATEGORIES] + ([f"Safeguards: {rep['safety_notes']}"] if rep.get("safety_notes") else []), ORANGE_FILL, ORANGE)], subhead="Safety Screening & Process Considerations")
    new_page(pdf)
    heading(pdf, 3, f"Parent A Perspective — {rep.get('parent_a_name') or 'Parent A'}")
    _body(pdf, "PARENT-REPORTED INFORMATION, summarized separately and neutrally by the professional; no determination is made about which account is correct.", italic=True)
    _perspective(pdf, rep, "a", SCALE_TABLE, cls["parent_a"])
    new_page(pdf)
    heading(pdf, 4, f"Parent B Perspective — {rep.get('parent_b_name') or 'Parent B'}")
    _perspective(pdf, rep, "b", SCALE_TABLE, cls["parent_b"])
    j = cls["joint"]
    new_page(pdf)
    heading(pdf, 5, "Joint Co-Parenting Assessment")
    _body(pdf, "[SYSTEM-GENERATED COMPARISON — reviewed by the professional]", italic=True)
    full_card(pdf, f"Joint Alignment Level: {rep.get('joint_rating') or '—'} / 10" + (f" — {j['label']} ({j['mode']} Mode)" if j and rep.get("joint_rating") else ""), [], PURPLE_FILL, PURPLE)
    cards_row(pdf, [("Areas of Alignment — Successes", [f"✓ {x}" for x in _lines(rep.get("alignment_agreements") or rep.get("joint_strengths"))] or ["—"], GREEN_FILL, GREEN),
                    ("Areas of Difference — Challenges", [f"! {x}" for x in _lines(rep.get("alignment_disagreements") or rep.get("joint_gaps"))] or ["—"], ORANGE_FILL, ORANGE)])
    cards_row(pdf, [("Partial Alignment", _lines(rep.get("partial_alignment")) or ["—"], BLUE_FILL, BLUE), ("Shared Concerns" + _ai_tag(rep, "shared_concerns"), _lines(rep.get("shared_concerns")) or ["—"], TEAL_FILL, TEAL)])
    _stmt_text(pdf, "Issues requiring further discussion or professional attention" + _ai_tag(rep, "joint_notes"), rep.get("joint_notes"), required=True)
    _lens_joint_scale(pdf, SCALE_TABLE, j, rep)
    new_page(pdf)
    heading(pdf, 6, "Child-Focused Legal Issues")
    _body(pdf, "What do the parents' differences mean for the child and the dispute?", italic=True)
    cf = rep.get("child_focus") or {}
    ticked = [[lbl, cf[k].get("note") or "Identified as an area affecting the child's needs.", "Structured, child-focused discussion; written protocol where helpful."] for k, lbl in CHILD_FOCUS_CATEGORIES if cf.get(k, {}).get("checked")]
    _lens_table(pdf, ["Issue", "Current Concern", "Potential Focus"], ticked, [40, 74, 60], header=(TEAL_FILL, TEAL)) if ticked else _body(pdf, "No child-focused categories identified.", italic=True)
    heading(pdf, 7, "Options & Resources")
    rows = [[r.get("category", ""), r.get("resource", ""), r.get("focus", "")] for r in (rep.get("resource_rows") or [])]
    _lens_table(pdf, ["Category", "Recommended Resource / Specialist", "Purpose / Service Focus"], rows, [40, 60, 74], header=(BLUE_FILL, BLUE)) if rows else _body(pdf, "No resources selected.", italic=True)
    _research_base(pdf, rep.get("research_base"))
    new_page(pdf)
    heading(pdf, 8, "Conflict Resolution Pathways")
    chosen = set(rep.get("conflict_pathways") or ([rep.get("conflict_pathway")] if rep.get("conflict_pathway") else []))
    pathway_steps(pdf, PATHWAYS, chosen)
    small_lines(pdf, [f"{n}. {p['name']}: {p['desc']}" for n, p in enumerate(PATHWAYS, 1)])
    _stmt_text(pdf, "Why these pathways are relevant to the issues identified" + _ai_tag(rep, "pathway_rationale", "conflict_management_rationale"), rep.get("pathway_rationale") or rep.get("conflict_management_rationale"), required=True)
    full_card(pdf, "Guidance by Type of Conflict", [f"• {t}: {d}" for t, d in CONFLICT_GUIDANCE], BLUE_FILL, BLUE)
    full_card(pdf, f"Safety Override — {SAFETY_PATHWAY[0]}", [SAFETY_PATHWAY[1]], GOLD_SOFT, GOLD)
    _body(pdf, notes["rating"], italic=True)
    statement_band(pdf)
    heading(pdf, 9, "Legal Conflict & Agreement-Building Analysis")
    cards_row(pdf, [("Areas Potentially Capable of Agreement", [f"✓ {x}" for x in _lines(rep.get("agreement_building_opportunities") or rep.get("alignment_agreements"))] or ["—"], GREEN_FILL, GREEN),
                    ("Issues Requiring Further Resolution", [f"! {x}" for x in _lines(rep.get("issues_requiring_attention") or rep.get("alignment_disagreements"))] or ["—"], ORANGE_FILL, ORANGE)])
    cards_row(pdf, [("Existing Agreements / Orders Noted", _lines(rep.get("existing_agreements")) or ["—"], BLUE_FILL, BLUE), ("Procedural Considerations", _lines(rep.get("procedural_considerations")) or ["—"], PURPLE_FILL, PURPLE)])
    heading(pdf, 10, "Professional Legal Statement & Roadmap")
    full_card(pdf, "PROFESSIONAL OBSERVATION" + _ai_tag(rep, "professional_summary"), [rep.get("professional_summary") or "—", "", "The professional's own observations and judgment — distinct from parent-reported information and system- or AI-generated summaries."], BLUE_FILL, BLUE)
    plan = ([f"☐ {g}" for g in _lines(rep.get("short_term_goals"))] or ["—"]) + ["", f"Reassessment: {rep.get('reassess_interval') or 'every 90 to 180 days'}" + (f" · next review {rep['next_review_date']}" if rep.get("next_review_date") else "")]
    indicators = _lines(rep.get("success_indicators")) or _lines(rep.get("long_term_goals")) or ["—"]
    cards_row(pdf, [("30–90 Day Goals" + _ai_tag(rep, "short_term_goals"), plan, TEAL_FILL, TEAL), ("How We Will Know Things Are Improving", [f"• {x}" for x in indicators], BLUE_FILL, BLUE)])
    cards_row(pdf, [("Long-Term Goals (6 to 12 Months)" + _ai_tag(rep, "long_term_goals"), [f"• {x}" for x in _lines(rep.get("long_term_goals"))] or ["—"], PURPLE_FILL, PURPLE), ("Reassessment Triggers", [rep.get("reassess_up") or "Score moves up: —", "", rep.get("reassess_down") or "Score drops: —"], GREEN_FILL, GREEN)])
    heading(pdf, 11, "Concise Court Summary")
    full_card(pdf, f"Parent A: Level {rep.get('parent_a_rating') or '—'}   |   Parent B: Level {rep.get('parent_b_rating') or '—'}   |   Joint Co-Parenting: Level {rep.get('joint_rating') or '—'}" + _ai_tag(rep, "court_summary_text"), _lines(rep.get("court_summary_text")) or ["—"], (255, 255, 255), PURPLE)
    full_card(pdf, "Our Report Principle", notes.get("principle") or [], PURPLE_FILL, PURPLE)


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


def _signature_image(pdf: FPDF, path: str) -> None:
    """Uploaded signature above the certification block (finalized reports only); skipped if storage is unavailable."""
    from io import BytesIO
    from storage import get_object
    try:
        data, _ = get_object(path)
    except Exception:  # noqa: BLE001
        return
    if pdf.get_y() > pdf.h - 45:
        pdf.add_page()
    y = pdf.get_y() + 1
    pdf.image(BytesIO(data), x=pdf.l_margin + 2, y=y, w=50, h=18, keep_aspect_ratio=True)
    pdf.set_draw_color(*GRAY)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin + 2, y + 19, pdf.l_margin + 60, y + 19)
    pdf.set_y(y + 21)


def build_legal_lens_pdf(v: dict) -> bytes:
    """SA CoParents Align Professional Alignment Report — court-ready PDF (11 sections + certification)."""
    from lens_data import REPORT_DISCLAIMER
    rep, c, notes = v["report"], v["case"], v["notes"]
    pdf = _new_pdf()
    pdf.footer_meta = f"{notes['tagline']} · Case {c.get('case_code') or ''} · {rep.get('professional_name') or ''} · {rep.get('report_date') or ''}"
    if rep.get("status") not in ("final", "submitted_to_court"):
        pdf.watermark_text = "DRAFT"
    pdf.brand_header_fn = brand_header
    render_lens_body(pdf, v)
    _lens_heading(pdf, "Professional Certification")
    _body(pdf, "Important: " + REPORT_DISCLAIMER, italic=True)
    _body(pdf, "This report reflects the professional's review of the individual assessments, safety screenings and Joint Report. It contains no custody recommendation, credibility determination, diagnosis or legal conclusion.", italic=True)
    sig = ((v.get("professional") or {}).get("images") or {}).get("signature")
    if sig and rep.get("status") in ("final", "submitted_to_court"):
        _signature_image(pdf, sig)
    _legal_kv(pdf, [("Professional signature", rep.get("signature_name")), ("Title", rep.get("professional_title")), ("Date finalized", (rep.get("finalized_at") or "")[:10])])
    _lens_ai_appendix(pdf, rep)
    pdf.ln(3)
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _s(notes["tagline"]), align="C", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
