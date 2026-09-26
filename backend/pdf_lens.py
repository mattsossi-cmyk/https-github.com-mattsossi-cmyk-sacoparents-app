"""Mockup-styled layout blocks for the Professional Alignment Report PDF (brand header, cards, score boxes, pathway steps)."""
from fpdf import FPDF
from fpdf.fonts import FontFace

from pdf_report import FONT, PURPLE, TEAL, BLUE, GREEN, GRAY, DARK, BODY, _s, _body, _stmt_text, _lens_heading, _lens_subhead, _lens_table, _lens_individual_scale, _lens_joint_scale

GOLD_FILL, PURPLE_FILL, TEAL_FILL, BLUE_FILL, GREEN_FILL, ORANGE_FILL, GOLD_SOFT = (255, 243, 201), (243, 237, 251), (232, 247, 247), (234, 244, 251), (234, 247, 241), (255, 240, 232), (255, 247, 223)
ORANGE, GOLD = (216, 105, 54), (214, 156, 32)
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
    full_card(pdf, "RESEARCH BASE (Perplexity Sonar — professional-reviewed)", lines, TEAL_FILL, TEAL)


def render_lens_body(pdf: FPDF, v: dict) -> None:
    """Pages 1–6 of the Professional Alignment Report (everything before the certification block)."""
    from lens_data import CHILD_FOCUS_CATEGORIES, CONFLICT_GUIDANCE, PATHWAYS, RISK_CATEGORIES, SCALE_TABLE, SAFETY_PATHWAY
    rep, c, cls, notes = v["report"], v["case"], v["classification"], v["notes"]
    brand_header(pdf)
    pdf.set_font(FONT, "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 9, "Professional Alignment Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 8.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, "SA CoParents Align Professional Evaluation Report (Legal Lens) — for professionals and the court", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    full_card(pdf, "Purpose", [notes.get("purpose", "")], PURPLE_FILL, PURPLE)
    _lens_heading(pdf, "1. Case & Assessment Snapshot")
    kv_table(pdf, [("Case / Matter", rep.get("matter_name")), ("Case ID", c.get("case_code")), ("Court / County", rep.get("court_county")), ("Cause Number", rep.get("cause_number")),
                   ("Professional", f"{rep.get('professional_name') or ''} · {rep.get('professional_role') or ''}".strip(" ·")), ("Report Date", rep.get("report_date")),
                   ("Parent A", rep.get("parent_a_name")), ("Parent B", rep.get("parent_b_name")), ("Report Status", (rep.get("status") or "draft").replace("_", " ").title())])
    cards_row(pdf, [("Assessments Reviewed", [f"{'☑' if r['done'] else '☐'} {r['label']}" + (" (N/A)" if r.get("na") and not r["done"] else "") for r in v.get("readiness") or []], BLUE_FILL, BLUE),
                    ("Sources of Information Considered", [rep.get("sources_considered") or "—"], PURPLE_FILL, PURPLE)])
    _lens_subhead(pdf, "Current Alignment Levels")
    score_boxes(pdf, [("Parent A", rep.get("parent_a_rating"), (cls["parent_a"] or {}).get("label"), PURPLE_FILL), ("Parent B", rep.get("parent_b_rating"), (cls["parent_b"] or {}).get("label"), TEAL_FILL),
                      ("Co-Parents (Joint)", rep.get("joint_rating"), (cls["joint"] or {}).get("label"), GREEN_FILL)])
    risk = rep.get("risk_screening") or {}
    cards_row(pdf, [(f"Joint process: {rep.get('joint_process_appropriate') or 'Not yet determined'}", [rep.get("safety_takeaway") or "—", "", f"Parent A FV assessment: {rep.get('fv_a_received') or '—'}", f"Parent B FV assessment: {rep.get('fv_b_received') or '—'}", "", notes["safety"]], TEAL_FILL, TEAL),
                    ("Risk Screening Summary", [f"{lbl}: {risk.get(k, {}).get('level', 'Not assessed')}." + (f" {risk[k]['note']}" if risk.get(k, {}).get("note") else "") for k, lbl, _ in RISK_CATEGORIES] + ([f"Safeguards: {rep['safety_notes']}"] if rep.get("safety_notes") else []), ORANGE_FILL, ORANGE)], subhead="Safety Status")
    new_page(pdf)
    _lens_heading(pdf, "2. Individual Parent Perspectives")
    _body(pdf, "PARENT-REPORTED INFORMATION, summarized separately and neutrally by the professional; no determination is made about which account is correct.", italic=True)
    cards_row(pdf, [(rep.get("parent_a_name") or "Parent A", _parent_lines(rep, "a"), PURPLE_FILL, PURPLE), (rep.get("parent_b_name") or "Parent B", _parent_lines(rep, "b"), TEAL_FILL, TEAL)])
    new_page(pdf)
    _lens_individual_scale(pdf, SCALE_TABLE, cls["parent_a"], rep, "a")
    pdf.ln(2)
    _lens_individual_scale(pdf, SCALE_TABLE, cls["parent_b"], rep, "b")
    j = cls["joint"]
    new_page(pdf)
    _lens_heading(pdf, "3. Joint Co-Parenting Assessment")
    _body(pdf, "[SYSTEM-GENERATED COMPARISON — reviewed by the professional]", italic=True)
    full_card(pdf, f"Joint Alignment Level: {rep.get('joint_rating') or '—'} / 10" + (f" — {j['label']} ({j['mode']} Mode)" if j and rep.get("joint_rating") else ""), [], PURPLE_FILL, PURPLE)
    cards_row(pdf, [("Areas of Alignment — Successes", [f"✓ {x}" for x in _lines(rep.get("alignment_agreements") or rep.get("joint_strengths"))] or ["—"], GREEN_FILL, GREEN),
                    ("Areas of Difference — Challenges", [f"! {x}" for x in _lines(rep.get("alignment_disagreements") or rep.get("joint_gaps"))] or ["—"], ORANGE_FILL, ORANGE)])
    cards_row(pdf, [("Partial Alignment", _lines(rep.get("partial_alignment")) or ["—"], BLUE_FILL, BLUE), ("Shared Concerns", _lines(rep.get("shared_concerns")) or ["—"], TEAL_FILL, TEAL)])
    _stmt_text(pdf, "Issues requiring further discussion or professional attention", rep.get("joint_notes"), required=True)
    _lens_joint_scale(pdf, SCALE_TABLE, j, rep)
    new_page(pdf)
    _lens_heading(pdf, "4. Child-Focused Issues")
    cf = rep.get("child_focus") or {}
    ticked = [(lbl, cf[k].get("note") or "Identified as an area affecting the child's needs.") for k, lbl in CHILD_FOCUS_CATEGORIES if cf.get(k, {}).get("checked")]
    fills = [BLUE_FILL, TEAL_FILL, PURPLE_FILL, ORANGE_FILL]
    for i in range(0, len(ticked), 2):
        cards_row(pdf, [(t, [n], fills[(i + k) % 4], BLUE) for k, (t, n) in enumerate(ticked[i:i + 2])])
    if not ticked:
        _body(pdf, "No child-focused categories identified.", italic=True)
    _lens_heading(pdf, "5. Options & Resources")
    rows = [[r.get("category", ""), r.get("resource", ""), r.get("focus", "")] for r in (rep.get("resource_rows") or [])]
    _lens_table(pdf, ["Category", "Recommended Resource / Specialist", "Purpose / Service Focus"], rows, [40, 60, 74]) if rows else _body(pdf, "No resources selected.", italic=True)
    _research_base(pdf, rep.get("research_base"))
    _lens_heading(pdf, "6. Conflict-Resolution Pathway")
    chosen = set(rep.get("conflict_pathways") or ([rep.get("conflict_pathway")] if rep.get("conflict_pathway") else []))
    pathway_steps(pdf, PATHWAYS, chosen)
    small_lines(pdf, [f"{n}. {p['name']}: {p['desc']}" for n, p in enumerate(PATHWAYS, 1)])
    _stmt_text(pdf, "Why these pathways are relevant to the issues identified", rep.get("pathway_rationale") or rep.get("conflict_management_rationale"), required=True)
    full_card(pdf, "Guidance by Type of Conflict", [f"• {t}: {d}" for t, d in CONFLICT_GUIDANCE], BLUE_FILL, BLUE)
    full_card(pdf, f"Safety Override — {SAFETY_PATHWAY[0]}", [SAFETY_PATHWAY[1]], GOLD_SOFT, GOLD)
    _body(pdf, notes["rating"], italic=True)
    _lens_heading(pdf, "7. Professional Observation & Action Plan")
    full_card(pdf, "PROFESSIONAL OBSERVATION", [rep.get("professional_summary") or "—", "", "The professional's own observations and judgment — distinct from parent-reported information and system- or AI-generated summaries."], BLUE_FILL, BLUE)
    plan = ([f"☐ {g}" for g in _lines(rep.get("short_term_goals"))] or ["—"]) + ["", f"Reassessment: {rep.get('reassess_interval') or 'every 90 to 180 days'}" + (f" · next review {rep['next_review_date']}" if rep.get("next_review_date") else "")]
    indicators = _lines(rep.get("success_indicators")) or _lines(rep.get("long_term_goals")) or ["—"]
    cards_row(pdf, [("90-Day Action Plan", plan, TEAL_FILL, TEAL), ("How We Will Know Things Are Improving", [f"• {x}" for x in indicators], BLUE_FILL, BLUE)])
    cards_row(pdf, [("Long-Term Goals (6 to 12 Months)", [f"• {x}" for x in _lines(rep.get("long_term_goals"))] or ["—"], PURPLE_FILL, PURPLE), ("Reassessment Triggers", [rep.get("reassess_up") or "Score moves up: —", "", rep.get("reassess_down") or "Score drops: —"], GREEN_FILL, GREEN)])
    _lens_heading(pdf, "8. Concise Court / Referral Summary")
    full_card(pdf, f"Parent A: Level {rep.get('parent_a_rating') or '—'}   |   Parent B: Level {rep.get('parent_b_rating') or '—'}   |   Joint Co-Parenting: Level {rep.get('joint_rating') or '—'}", _lines(rep.get("court_summary_text")) or ["—"], (255, 255, 255), PURPLE)
    full_card(pdf, "Our Report Principle", notes.get("principle") or [], PURPLE_FILL, PURPLE)
