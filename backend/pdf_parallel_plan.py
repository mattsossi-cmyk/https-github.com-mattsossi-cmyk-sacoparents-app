"""One-page Parallel Parenting Order Summary for judges — drawn from the Safety Override agreement card (neutral, no parent answers)."""
from pdf_common import FONT, GRAY, BODY, _s, _new_pdf
from pdf_foundation import PURPLE, PURPLE_DARK, PURPLE_LIGHT, _W, _banner, _panel, _bullets, _info_cards
from pdf_agreement import GOLD, GOLD_SOFT, TEAL
from safety_gate import PARALLEL

_ORDER_TERMS = [
    ("Communication", "All parent-to-parent communication in writing through a court-approved co-parenting platform; child-related logistics only; no calls, texts or in-person discussion."),
    ("Exchanges", "Neutral site (school, daycare or supervised exchange center) or third party; staggered arrival; no conversation at exchanges; 48-hour written notice for schedule changes."),
    ("Decision-making", "Each parent manages day-to-day decisions during their own parenting time; major decisions follow the existing order and, where required, professional consultation."),
    ("Information sharing", "School, medical and activity information posted on the platform within 2 days; both parents hold independent portal access."),
    ("Disputes", "No direct negotiation. Written proposal → parenting coordinator / facilitator → attorney-assisted process → court motion. Emergencies: 911 / protective-order process."),
    ("Review", "Reassess in 90–180 days through the professional; step-down to cooperative co-parenting only on professional recommendation and court approval."),
]


def build_parallel_plan_pdf(card: dict, case: dict, professional: str) -> bytes:
    so = card.get("safety_override") or {}
    pdf = _new_pdf()
    pdf.footer_meta = f"Parallel Parenting Order Summary · {card.get('case_code') or ''} · {card.get('date') or ''}"
    _banner(pdf, "Judicial Summary\nParallel Parenting", "P A R A L L E L   P A R E N T I N G   O R D E R   S U M M A R Y")
    pdf.set_font(FONT, "B", 8)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 5, "S A   C O P A R E N T S   A L I G N   ·   F O R   T H E   C O U R T", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*PURPLE_DARK)
    pdf.cell(0, 8, "Parallel Parenting Order Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 8.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4.3, "Drawn from the parents' Co-Parenting Agreement rendered under the SA CoParents Safety Override. Proposed terms for the court's consideration only — not an order, finding or recommendation.")
    pdf.ln(2)
    _info_cards(pdf, [("Cause No.", case.get("cause_number") or "—"), ("Court", (case.get("court_name") or "—")[:22]), ("Child", card.get("child_name") or "—"), ("Agreement", card.get("case_code") or "—")])
    _panel(pdf, ("Basis: " + " ".join(so.get("reasons") or [])) if so.get("reasons") else "Family-violence or safety indicators were identified by the professional.", GOLD_SOFT, accent=GOLD, sub=so.get("banner") or PARALLEL["banner"])
    pdf.set_font(FONT, "B", 11)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 7, "Proposed Parallel Parenting Terms", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y()
    pdf.set_font(FONT, "", 8.5)
    for label, text in _ORDER_TERMS:
        h = pdf.multi_cell(_W - 40, 4.3, _s(text), dry_run=True, output="HEIGHT") + 3
        pdf.set_fill_color(*PURPLE_LIGHT)
        pdf.rect(18, y, 36, h, style="F")
        pdf.set_xy(20, y + 1.5)
        pdf.set_font(FONT, "B", 8.5)
        pdf.set_text_color(*PURPLE)
        pdf.cell(32, 4.3, label)
        pdf.set_xy(56, y + 1.5)
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(_W - 40, 4.3, _s(text))
        pdf.set_draw_color(222, 217, 230)
        pdf.line(18, y + h, 18 + _W, y + h)
        y += h
    pdf.set_xy(18, y + 4)
    pdf.set_font(FONT, "", 8)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 4.2, _s("Dispute ladder: " + "  →  ".join(f"{n} {t}" for n, t in PARALLEL["conflict_steps"])))
    pdf.ln(2)
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, "From the parents' agreement (neutral summary)", new_x="LMARGIN", new_y="NEXT")
    _bullets(pdf, [f"Areas of alignment ({(card.get('counts') or {}).get('alignment', 0)}): " + ", ".join(card.get("needs_aligned") or [])[:160],
                   f"Areas still requiring agreement ({(card.get('counts') or {}).get('resolution', 0)}): " + "; ".join(card.get("needs_open") or [])[:160]])
    pdf.set_font(FONT, "I", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, _s(f"Prepared from a hash-sealed court submission by {professional}. SA CoParents Align does not determine custody, make findings or substitute for the court's judgment."))
    return bytes(pdf.output())
