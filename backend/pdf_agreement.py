"""Brand-styled Co-Parenting Agreement PDF (brand header on every page, colored cards, status badges)."""
from fpdf import FPDF

from pdf_report import FONT, PURPLE, TEAL, BLUE, GREEN, GRAY, DARK, BODY, _s, _new_pdf, _lens_heading
from pdf_lens import brand_header, cards_row, full_card, kv_table, PURPLE_FILL, TEAL_FILL, BLUE_FILL, GREEN_FILL, ORANGE_FILL, GOLD_SOFT, ORANGE, GOLD

_STATUS = {"Agreed": (GREEN, GREEN_FILL), "Partly agreed": (GOLD, GOLD_SOFT), "Aligned in principle": (TEAL, TEAL_FILL), "Requires resolution": (BLUE, BLUE_FILL)}


def _badge(pdf: FPDF, text: str, color: tuple, fill: tuple) -> None:
    pdf.set_font(FONT, "B", 7.5)
    w = pdf.get_string_width(text) + 6
    x, y = pdf.w - pdf.r_margin - w, pdf.get_y() + 1
    pdf.set_fill_color(*fill)
    pdf.rect(x, y, w, 5.5, style="F", round_corners=True, corner_radius=2.7)
    pdf.set_xy(x, y)
    pdf.set_text_color(*color)
    pdf.cell(w, 5.5, text, align="C")


def _eyebrow(pdf: FPDF, text: str, color: tuple = DARK) -> None:
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*color)
    pdf.cell(0, 5, _s(text.upper()), new_x="LMARGIN", new_y="NEXT")


def _bullets(pdf: FPDF, title: str, items: list, color: tuple, empty: str | None = None) -> None:
    if not items and not empty:
        return
    _eyebrow(pdf, title, color)
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*BODY)
    for it in items or [empty]:
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(0, 4.8, _s(f"• {it}"))
    pdf.ln(1.5)


def _section(pdf: FPDF, s: dict, r: dict) -> None:
    if pdf.get_y() > pdf.h - 75:
        pdf.add_page()
    color, fill = _STATUS.get(s["status"], (BLUE, BLUE_FILL))
    y = pdf.get_y()
    pdf.set_fill_color(*PURPLE_FILL)
    pdf.rect(pdf.l_margin, y, pdf.w - pdf.l_margin - pdf.r_margin, 9, style="F", round_corners=True, corner_radius=2)
    pdf.set_xy(pdf.l_margin + 3, y)
    pdf.set_font(FONT, "B", 12)
    pdf.set_text_color(*PURPLE)
    pdf.cell(120, 9, _s(f"{s['num']}. {s['label']}"))
    pdf.set_y(y + 1.5)
    _badge(pdf, s["status"], color, fill)
    pdf.set_xy(pdf.l_margin, y + 12)
    _eyebrow(pdf, "Shared Goal", GRAY)
    pdf.set_font(FONT, "I", 9.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 4.8, _s(s["shared_goal"]))
    pdf.ln(1.5)
    _bullets(pdf, "Current Alignment", s["current_alignment"], GREEN, "The parents' general proposals use different language; see the items below.")
    _bullets(pdf, "Specific Agreements", s["specific_agreements"], PURPLE, "No specific commitments could be confirmed from both parents' answers yet.")
    roles = [(t, s[k]) for t, k in (("Communication Method", "communication_method"), ("Decision Process", "decision_process"), ("Review Trigger", "review_trigger")) if s.get(k)]
    if roles:
        cards_row(pdf, [(t, [v], TEAL_FILL, TEAL) for t, v in roles])
    _bullets(pdf, "Issues Still Requiring Resolution", s["open_issues"], ORANGE)
    pdf.ln(3)


def _signatures(pdf: FPDF, r: dict) -> None:
    if pdf.get_y() > pdf.h - 70:
        pdf.add_page()
    _lens_heading(pdf, "Signatures")
    gap, w = 8, (pdf.w - pdf.l_margin - pdf.r_margin - 8) / 2
    y = pdf.get_y()
    for i, name in enumerate((r["parent_a_name"], r["parent_b_name"])):
        x = pdf.l_margin + i * (w + gap)
        pdf.set_fill_color(*(PURPLE_FILL if i == 0 else TEAL_FILL))
        pdf.rect(x, y, w, 34, style="F", round_corners=True, corner_radius=2.5)
        pdf.set_xy(x + 4, y + 3)
        pdf.set_font(FONT, "B", 10.5)
        pdf.set_text_color(*(PURPLE if i == 0 else TEAL))
        pdf.cell(w - 8, 6, _s(name))
        pdf.set_draw_color(*GRAY)
        pdf.line(x + 4, y + 20, x + w - 4, y + 20)
        pdf.line(x + 4, y + 30, x + w * 0.55, y + 30)
        pdf.set_font(FONT, "", 7.5)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x + 4, y + 20.5)
        pdf.cell(40, 4, "Signature")
        pdf.set_xy(x + 4, y + 30.5)
        pdf.cell(40, 4, "Date")
    pdf.set_y(y + 40)


def build_agreement_pdf(r: dict) -> bytes:
    pdf = _new_pdf()
    pdf.footer_meta = f"SA CoParents Co-Parenting Agreement · {r['child_name']} · {r['date']}"
    if r.get("is_sample"):
        pdf.watermark_text = "SAMPLE"
    pdf.brand_header_fn = brand_header
    brand_header(pdf)
    pdf.set_font(FONT, "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 9, _s(r["report_title"]), new_x="LMARGIN", new_y="NEXT")
    kv_table(pdf, [("Child", r["child_name"]), ("Parents", f"{r['parent_a_name']} / {r['parent_b_name']}"), ("Date", r["date"]), ("Process", r.get("method_note") or "Reflection → Alignment → Specific Action → Agreement")])
    full_card(pdf, "Purpose", [r["purpose"]], PURPLE_FILL, PURPLE)
    full_card(pdf, "Confidentiality", [r["confidentiality_note"]], BLUE_FILL, BLUE)
    sm = r.get("summary") or {"alignment": [], "specific": [], "resolution": []}
    _lens_heading(pdf, "At a Glance")
    cards_row(pdf, [(f"Areas of Alignment ({len(sm['alignment'])})", [f"✓ {x}" for x in sm["alignment"][:10]] or ["None identified yet."], GREEN_FILL, GREEN),
                    (f"Issues Still Requiring Resolution ({len(sm['resolution'])})", [f"! {x}" for x in sm["resolution"][:10]] or ["None — every answered item is aligned."], ORANGE_FILL, ORANGE)])
    full_card(pdf, f"Specific Agreements ({len(sm['specific'])})", [f"• {x}" for x in sm["specific"][:14]] + ([f"…and {len(sm['specific']) - 14} more in the sections below."] if len(sm["specific"]) > 14 else []) or ["None confirmed yet."], PURPLE_FILL, PURPLE)
    pdf.add_page()
    _lens_heading(pdf, "Agreement Sections")
    for s in r.get("sections") or []:
        _section(pdf, s, r)
    full_card(pdf, "Before This Document Is Finalized", [r["next_note"]], GOLD_SOFT, GOLD)
    if r.get("foundation_statements"):
        _lens_heading(pdf, "Foundation Statements")
        for fs in r["foundation_statements"]:
            full_card(pdf, f"{fs['parent']} — {fs['title']}", [fs["content"]], BLUE_FILL, BLUE)
    _signatures(pdf, r)
    pdf.ln(4)
    pdf.set_font(FONT, "B", 15)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, _s(r["philosophy_heading"]), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "I", 9.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5, _s(f'"{r["philosophy"]}"'), align="C")
    return bytes(pdf.output())
