"""Child-Focused Co-Parenting Agreement PDF — purple banner, teal bullets, 15 numbered sections (supplied HTML design)."""
from fpdf import FPDF

from pdf_common import FONT, GRAY, BODY, _s, _new_pdf
from pdf_foundation import PURPLE, PURPLE_DARK, PURPLE_LIGHT, TEAL_LIGHT, BORDER, _W, _banner, _heading, _panel, _bullets, _info_cards, _footer_block
from agreement_model import court_agreement_model

TEAL = (21, 154, 156)
GREEN, GREEN_LIGHT, ORANGE, ORANGE_LIGHT = (45, 138, 100), (237, 248, 243), (198, 122, 38), (255, 246, 234)
GOLD, GOLD_SOFT = (176, 125, 16), (255, 247, 223)


def _choices(pdf: FPDF, items: list) -> None:
    n, gap = len(items), 4
    w = (_W - gap * (n - 1)) / n
    pdf.set_font(FONT, "", 8.5)
    h = max(pdf.multi_cell(w - 8, 4.3, _s(v), dry_run=True, output="HEIGHT") for _, v in items) + 12
    y = pdf.get_y()
    if y + h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()
    for i, (t, v) in enumerate(items):
        x = 18 + i * (w + gap)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
        pdf.set_xy(x + 4, y + 3)
        pdf.set_font(FONT, "B", 8.5)
        pdf.set_text_color(*PURPLE)
        pdf.cell(w - 8, 4.5, _s(t), new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x + 4, y + 8)
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(w - 8, 4.3, _s(v))
    pdf.set_xy(18, y + h + 6)


def _two_boxes(pdf: FPDF, left: tuple, right: tuple) -> None:
    gap, w = 6, (_W - 6) / 2
    pdf.set_font(FONT, "", 9)
    hs = [sum(pdf.multi_cell(w - 18, 4.8, _s(t), dry_run=True, output="HEIGHT") + 2 for t in items) + 14 for _, items, _, _ in (left, right)]
    h = max(hs)
    y = pdf.get_y()
    if y + h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()
    for i, (title, items, color, fill) in enumerate((left, right)):
        x = 18 + i * (w + gap)
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_xy(x + 5, y + 4)
        pdf.set_font(FONT, "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(w - 10, 6, _s(title))
        pdf.set_xy(x, y + 11)
        _bullets(pdf, items, x=x, w=w)
    pdf.set_xy(18, y + h + 6)


def _card(pdf: FPDF, header: str, items: list) -> None:
    pdf.set_font(FONT, "", 9.5)
    h = sum(pdf.multi_cell(_W - 16, 5, _s(t), dry_run=True, output="HEIGHT") + 2 for t in items) + 16
    y = pdf.get_y()
    if y + h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()
    pdf.set_draw_color(*BORDER)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(18, y, _W, h, style="DF", round_corners=True, corner_radius=2.5)
    pdf.set_fill_color(250, 248, 252)
    pdf.rect(18, y, _W, 9, style="F")
    pdf.set_xy(22, y + 1.5)
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_text_color(*PURPLE)
    pdf.cell(_W - 8, 6, _s(header))
    pdf.set_xy(18, y + 12)
    _bullets(pdf, items)
    pdf.set_xy(18, y + h + 6)


def _signatures(pdf: FPDF, m: dict) -> None:
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    pdf.ln(12)
    y = pdf.get_y()
    w = (_W - 16) / 2
    pdf.set_draw_color(68, 68, 68)
    pdf.set_font(FONT, "", 7)
    pdf.set_text_color(*GRAY)
    for i, name in enumerate((m["parent_a_name"], m["parent_b_name"])):
        x = 18 + i * (w + 16)
        pdf.line(x, y, x + w, y)
        pdf.set_xy(x, y + 1.5)
        pdf.cell(w, 4, _s(f"{name.upper()}   S I G N A T U R E"))
        pdf.line(x, y + 16, x + w, y + 16)
        pdf.set_xy(x, y + 17.5)
        pdf.cell(w, 4, "D A T E")
    pdf.set_xy(18, y + 26)


def build_agreement_pdf(r: dict, doc: dict | None = None, is_sample: bool = False, safety: dict | None = None) -> bytes:
    """`doc` is the agreement case; `r` (legacy generate_agreement output) is accepted for callers that only have the report."""
    m = court_agreement_model(doc, safety) if doc else r
    pdf = _new_pdf()
    pdf.footer_meta = f"SA CoParents Co-Parenting Agreement · {m['child_name']} · {m['date']}"
    if is_sample or r.get("is_sample"):
        pdf.watermark_text = "SAMPLE"
    pdf.brand_header_fn = lambda p: _banner(p, "Starting With Alignment\nEnding With Agreement", "C O - P A R E N T I N G   A G R E E M E N T")
    _banner(pdf, "Starting With Alignment\nEnding With Agreement", "C O - P A R E N T I N G   A G R E E M E N T")
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 5, "S A   C O P A R E N T S", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 21)
    pdf.set_text_color(*PURPLE_DARK)
    pdf.cell(0, 11, _s(m["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 5.5, _s(m["subtitle"]))
    pdf.ln(4)
    _info_cards(pdf, [("Parent A", m["parent_a_name"]), ("Parent B", m["parent_b_name"]), ("Child", m["child_name"]), ("Agreement Date", m["date"])])
    _panel(pdf, m["purpose"], TEAL_LIGHT, accent=TEAL, sub="Purpose of This Agreement")
    so = m.get("safety_override")
    if so:
        _panel(pdf, so["note"] + ("\n\nBasis: " + " ".join(so["reasons"]) if so.get("reasons") else ""), GOLD_SOFT, accent=GOLD, sub=so["banner"])
    _heading(pdf, 1, "Our Shared Child-Focused Purpose")
    _panel(pdf, "\n".join(f"• {x}" for x in m["shared_purpose"]), PURPLE_LIGHT, label="Shared Foundation")
    for f in m.get("foundation_statements") or []:
        _panel(pdf, f["content"], TEAL_LIGHT, label=f"{f['parent']} — {f['title']}")
    _heading(pdf, 2, "Our Child's Strengths")
    _bullets(pdf, m["strengths"])
    _heading(pdf, 3, "Our Child's Current Needs")
    _two_boxes(pdf, ("Areas of Alignment", m["needs_aligned"], GREEN, GREEN_LIGHT), ("Areas Requiring Agreement", m["needs_open"], ORANGE, ORANGE_LIGHT))
    pdf.add_page()
    _heading(pdf, 4, "Communication Between Parents")
    _card(pdf, "Our Communication Agreement" if not so else "Parallel Parenting — Written Communication Only", m["communication"])
    _choices(pdf, m["communication_choices"])
    _heading(pdf, 5, "Parenting Transitions")
    _bullets(pdf, m["transitions"])
    _heading(pdf, 6, "Daily Routines & Consistency")
    _choices(pdf, m["routines"])
    _heading(pdf, 7, "Information Sharing")
    _bullets(pdf, m["information"])
    pdf.add_page()
    _heading(pdf, 8, "Educational Decisions")
    _bullets(pdf, m["education"])
    _heading(pdf, 9, "Medical & Psychological Needs")
    _bullets(pdf, m["medical"])
    _heading(pdf, 10, "Conflict Resolution Plan")
    _panel(pdf, m["conflict_intro"], PURPLE_LIGHT)
    if m["conflict_agreed"]:
        _bullets(pdf, m["conflict_agreed"])
    _choices(pdf, m["conflict_steps"][:3])
    _choices(pdf, m["conflict_steps"][3:])
    _heading(pdf, 11, "Options & Resources")
    _bullets(pdf, m["options"])
    pdf.add_page()
    _heading(pdf, 12, "Our Parenting Commitments")
    _card(pdf, "What we are each committing to", m["commitments"])
    _heading(pdf, 13, "Goals for the Next 12 Months")
    _bullets(pdf, m["goals"])
    _heading(pdf, 14, "Reviewing Our Agreement")
    _bullets(pdf, m["review"])
    _choices(pdf, m["review_choices"])
    _heading(pdf, 15, "Our Shared Commitment")
    _panel(pdf, "\n".join(m["shared_commitment"]), PURPLE_LIGHT, sub="Alignment Before Agreement")
    _signatures(pdf, m)
    _footer_block(pdf, {"disclaimer": m["disclaimer"]}, signature=False)
    return bytes(pdf.output())
