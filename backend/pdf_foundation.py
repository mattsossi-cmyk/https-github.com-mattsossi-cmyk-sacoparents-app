"""Child-Focused Foundation Statement PDF — purple banner, teal accents, 10 numbered sections (matches the supplied HTML design)."""
from fpdf import FPDF

from pdf_report import FONT, TEAL, GRAY, BODY, _s, _new_pdf

PURPLE, PURPLE_DARK, PURPLE_LIGHT, TEAL_LIGHT, BORDER, PANEL, COMMIT = (75, 42, 123), (47, 23, 79), (244, 240, 250), (234, 247, 247), (221, 215, 230), (250, 249, 252), (248, 246, 251)
_W = 210 - 36


def _banner(pdf: FPDF, right: str) -> None:
    pdf.set_fill_color(*PURPLE_DARK)
    pdf.rect(0, 0, pdf.w, 30, style="F")
    pdf.set_fill_color(*PURPLE)
    pdf.rect(pdf.w * 0.45, 0, pdf.w * 0.55, 30, style="F")
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(18, 8, 14, 14, style="F", round_corners=True, corner_radius=3)
    pdf.set_fill_color(*PURPLE)
    pdf.ellipse(21, 11, 8, 8, style="F")
    pdf.set_fill_color(*TEAL)
    pdf.ellipse(25, 11, 4, 8, style="F")
    pdf.set_xy(36, 8)
    pdf.set_font(FONT, "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 8, "SA CoParents")
    pdf.set_xy(36, 16.5)
    pdf.set_font(FONT, "", 7)
    pdf.cell(100, 4, "F O U N D A T I O N   S T A T E M E N T")
    pdf.set_xy(pdf.w - 18 - 60, 9)
    pdf.set_font(FONT, "", 7)
    pdf.multi_cell(60, 4.5, right.upper(), align="R")
    pdf.set_xy(18, 38)


def _heading(pdf: FPDF, n: int, title: str) -> None:
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    y = pdf.get_y()
    pdf.set_fill_color(*PURPLE)
    pdf.ellipse(18, y, 8, 8, style="F")
    pdf.set_xy(18, y)
    pdf.set_font(FONT, "B", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(8, 8, str(n), align="C")
    pdf.set_xy(29, y)
    pdf.set_font(FONT, "B", 13.5)
    pdf.set_text_color(*PURPLE_DARK)
    pdf.cell(0, 8, _s(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.2)
    pdf.line(18, y + 10, pdf.w - 18, y + 10)
    pdf.set_y(y + 13)


def _panel(pdf: FPDF, text: str, fill: tuple, accent: tuple | None = None, label: str | None = None, sub: str | None = None, x: float = 18, w: float = _W, h_min: float = 0) -> float:
    pdf.set_font(FONT, "", 9.5)
    body_h = pdf.multi_cell(w - 10, 5, _s(text), dry_run=True, output="HEIGHT")
    h = max(body_h + 10 + (6 if label else 0) + (7 if sub else 0), h_min)
    y = pdf.get_y()
    if y + h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*BORDER)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
    if accent:
        pdf.set_fill_color(*accent)
        pdf.rect(x, y, 1.6, h, style="F")
    pdf.set_xy(x + 5, y + 4)
    if label:
        pdf.set_font(FONT, "B", 7.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 4, _s(label.upper()), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x + 5)
    if sub:
        pdf.set_font(FONT, "B", 12)
        pdf.set_text_color(*PURPLE)
        pdf.cell(0, 6, _s(sub), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x + 5)
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(w - 10, 5, _s(text))
    pdf.set_xy(18, y + h + 5)
    return h


def _bullets(pdf: FPDF, items: list, boxed: bool = False, accent: tuple | None = None, x: float = 18, w: float = _W) -> None:
    pdf.set_font(FONT, "", 9.5)
    hs = [pdf.multi_cell(w - 16, 5, _s(t), dry_run=True, output="HEIGHT") for t in items]
    h = sum(hs) + 2 * len(items) + (8 if boxed else 0)
    y = pdf.get_y()
    if y + h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()
    if boxed:
        pdf.set_fill_color(*(COMMIT if accent else PANEL))
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
        if accent:
            pdf.set_fill_color(*accent)
            pdf.rect(x, y, 1.6, h, style="F")
        y += 4
    for t, th in zip(items, hs):
        pdf.set_fill_color(*TEAL)
        pdf.ellipse(x + 5, y + 1.6, 2.6, 2.6, style="F")
        pdf.set_xy(x + 11, y)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(w - 16, 5, _s(t))
        y += th + 2
    pdf.set_xy(18, y + (4 if boxed else 0) + 3)


def _info_cards(pdf: FPDF, items: list) -> None:
    gap, w = 4, (_W - 8) / 3
    y = pdf.get_y()
    for i, (label, value) in enumerate(items):
        x = 18 + i * (w + gap)
        pdf.set_fill_color(*PURPLE_LIGHT)
        pdf.set_draw_color(238, 231, 245)
        pdf.rect(x, y, w, 18, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_xy(x + 4, y + 3)
        pdf.set_font(FONT, "B", 6.5)
        pdf.set_text_color(*PURPLE)
        pdf.cell(w - 8, 4, _s(label.upper()))
        pdf.set_xy(x + 4, y + 8)
        pdf.set_font(FONT, "B", 11)
        pdf.set_text_color(*BODY)
        pdf.cell(w - 8, 7, _s(value))
    pdf.set_xy(18, y + 24)


def build_foundation_pdf(d: dict) -> bytes:
    pdf = _new_pdf()
    pdf.footer_meta = f"SA CoParents Foundation Statement · {d.get('parent_name') or 'Parent'} · {d.get('statement_date') or ''}"
    if d.get("is_sample"):
        pdf.watermark_text = "SAMPLE"
    pdf.brand_header_fn = lambda p: _banner(p, "Child-Focused\nParent Report")
    child = d.get("child_short") or d.get("child_name") or "my child"
    _banner(pdf, "Child-Focused\nParent Report")
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 5, "S A   C O P A R E N T S   P A R E N T   R E P O R T", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 22)
    pdf.set_text_color(*PURPLE_DARK)
    pdf.cell(0, 11, "Child-Focused Foundation Statement", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 10.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 6, "A parent's statement of goals, priorities, concerns and commitments for their child.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    _info_cards(pdf, [("Parent", d.get("parent_name") or "—"), ("Child", d.get("child_name") or "—"), ("Statement Date", d.get("statement_date") or "—")])
    _panel(pdf, d.get("purpose") or "", TEAL_LIGHT, accent=TEAL, sub="Purpose of This Statement")
    _heading(pdf, 1, "Shared Purpose")
    _panel(pdf, d.get("shared_purpose") or "—", PANEL)
    _heading(pdf, 2, "My Vision for My Child")
    _panel(pdf, d.get("vision") or "—", PURPLE_LIGHT, label="Child at the Center", sub=f"The future I want for {child}")
    _heading(pdf, 3, "Parenting Priorities")
    _bullets(pdf, d.get("priorities") or ["—"])
    pdf.add_page()
    _heading(pdf, 4, "Understanding My Child")
    gap, w = 6, (_W - 6) / 2
    y = pdf.get_y()
    pdf.set_font(FONT, "", 9.5)
    hl = pdf.multi_cell(w - 10, 5, _s(d.get("strengths") or "—"), dry_run=True, output="HEIGHT") + 17
    hr = sum(pdf.multi_cell(w - 16, 5, _s(t), dry_run=True, output="HEIGHT") + 2 for t in d.get("needs") or ["—"]) + 17
    h = max(hl, hr)
    for i, title in enumerate(("My Child's Strengths", "My Child's Current Needs")):
        x = 18 + i * (w + gap)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_xy(x + 5, y + 4)
        pdf.set_font(FONT, "B", 11.5)
        pdf.set_text_color(*PURPLE)
        pdf.cell(w - 10, 7, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x + 5, y + 13)
        if i == 0:
            pdf.set_font(FONT, "", 9.5)
            pdf.set_text_color(*BODY)
            pdf.multi_cell(w - 10, 5, _s(d.get("strengths") or "—"))
        else:
            _bullets(pdf, d.get("needs") or ["—"], x=x, w=w)
    pdf.set_xy(18, y + h + 6)
    _heading(pdf, 5, "Areas of Concern")
    _bullets(pdf, d.get("concerns") or ["—"], boxed=True)
    _heading(pdf, 6, "What My Child May Need")
    _panel(pdf, d.get("child_may_need") or "—", PURPLE_LIGHT, label="Child-Focused Reflection")
    _heading(pdf, 7, "Commitments I Am Making")
    _bullets(pdf, d.get("commitments") or ["—"], boxed=True, accent=PURPLE)
    pdf.add_page()
    _heading(pdf, 8, "Goals for the Next 12 Months")
    _bullets(pdf, d.get("goals") or ["—"])
    _heading(pdf, 9, "My Child's Future")
    _panel(pdf, d.get("future") or "—", PURPLE_LIGHT, label="Looking Forward")
    _heading(pdf, 10, "Parent Commitment")
    _panel(pdf, d.get("parent_commitment") or "—", COMMIT, accent=PURPLE, sub="My Foundation Statement")
    pdf.ln(14)
    y = pdf.get_y()
    pdf.set_draw_color(68, 68, 68)
    pdf.line(18, y, 18 + 80, y)
    pdf.line(18 + 100, y, pdf.w - 18, y)
    pdf.set_font(FONT, "", 7)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(18, y + 1.5)
    pdf.cell(80, 4, "P A R E N T   S I G N A T U R E")
    pdf.set_xy(118, y + 1.5)
    pdf.cell(60, 4, "D A T E", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    y = pdf.get_y()
    pdf.set_draw_color(*BORDER)
    pdf.line(18, y, pdf.w - 18, y)
    pdf.set_xy(18, y + 4)
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*PURPLE)
    contact = d.get("contact") or ["SA CoParents"]
    pdf.cell(70, 5, _s(contact[0]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 7.5)
    pdf.set_text_color(*GRAY)
    for line in contact[1:]:
        pdf.cell(70, 3.8, _s(line), new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(95, y + 4)
    pdf.set_font(FONT, "I", 7.5)
    pdf.multi_cell(pdf.w - 18 - 95, 3.8, _s(d.get("disclaimer") or ""))
    return bytes(pdf.output())
