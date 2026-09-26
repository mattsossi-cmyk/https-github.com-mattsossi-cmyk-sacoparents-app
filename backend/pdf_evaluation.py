"""Professional Evaluation Report PDF — mirrors the SACO ParentAlign HTML card (navy/teal, amber safety callout, highlighted 1-10 matrix)."""
from fpdf import FPDF

from pdf_common import FONT, _s, _new_pdf

NAVY, TEAL, SLATE, BORDER, PANEL, HEAD = (30, 58, 138), (15, 118, 110), (75, 85, 99), (226, 232, 240), (248, 250, 252), (239, 246, 255)
AMBER, AMBER_BG, AMBER_TXT = (245, 158, 11), (254, 243, 199), (180, 83, 9)
_W = 210 - 36

MATRIX = [("1 – 2", "Crisis / High Conflict", "Follow legal orders; use 3rd-party exchange sites.", "Total communication collapse; hostile outbursts; safety risks."),
          ("3 – 4", "Restricted / Reactive", "Honor swap times; update portal records; attend public events.", "Transition verbal friction; defensive texts; tardiness; gatekeeping."),
          ("5 – 6", "Business-Like / Functional", "Task-focused texts; advance 48h schedule swaps.", "Struggle with unannounced shifts; minor passive-aggression."),
          ("7 – 8", "Cooperative / Collaborative", "Proactive consultation on school/health; informal swaps.", "Clash over secondary house rules or discipline styles."),
          ("9 – 10", "Unified Partnership", "Matching household rules; joint events; fluid updates.", "Absence of post-divorce dysfunction or conflict.")]


def _band(score) -> int | None:
    try:
        s = int(score)
    except (TypeError, ValueError):
        return None
    return None if not 1 <= s <= 10 else (s - 1) // 2


def _h3(pdf: FPDF, text: str) -> None:
    if pdf.get_y() > pdf.h - 45:
        pdf.add_page()
    pdf.ln(4)
    pdf.set_font(FONT, "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, _s(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BORDER)
    pdf.line(18, pdf.get_y(), 18 + _W, pdf.get_y())
    pdf.ln(2)


def _header(pdf: FPDF, meta: dict) -> None:
    pdf.set_fill_color(255, 255, 255)
    pdf.set_font(FONT, "B", 7.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 4, _s("SACO PARENTALIGN  •  EMERGENT AI INTEGRATION"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "B", 17)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, _s("Professional Evaluation Report"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.7)
    pdf.line(18, pdf.get_y() + 1, 18 + _W, pdf.get_y() + 1)
    pdf.set_line_width(0.2)
    pdf.ln(5)
    y = pdf.get_y()
    lines = [("Case", f"{meta.get('case_code') or '—'}  ·  {meta.get('subject_label') or ''}  ·  Child: {meta.get('child_name') or '—'}"),
             ("Portal Link", "sacoparentsalign.com"), ("Operating Mode", meta.get("mode_line") or "—"), ("Prepared by", meta.get("professional") or "—"), ("Date", meta.get("date") or "")]
    h = 5.2 * len(lines) + 6
    pdf.set_fill_color(*PANEL)
    pdf.set_draw_color(*BORDER)
    pdf.rect(18, y, _W, h, style="DF", round_corners=True, corner_radius=1.5)
    pdf.set_xy(22, y + 3)
    for k, v in lines:
        pdf.set_font(FONT, "B", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.cell(30, 5.2, _s(k + ":"))
        pdf.set_font(FONT, "", 8.5)
        pdf.cell(0, 5.2, _s(v), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(22)
    pdf.set_y(y + h + 2)
    pdf.set_font(FONT, "I", 7.5)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(_W, 4, _s("AI-assisted draft reviewed and approved by the case professional. Professional-only working document — not shared with parents and never attached to a court packet automatically. Scores describe the co-parenting context, never parental fitness or credibility."))


def _safety(pdf: FPDF, text: str) -> None:
    pdf.set_font(FONT, "", 9)
    h = pdf.multi_cell(_W - 10, 4.8, _s(text), dry_run=True, output="HEIGHT") + 6
    y = pdf.get_y()
    pdf.set_fill_color(*AMBER_BG)
    pdf.rect(18, y, _W, h, style="F")
    pdf.set_fill_color(*AMBER)
    pdf.rect(18, y, 1.6, h, style="F")
    pdf.set_xy(23, y + 3)
    pdf.set_text_color(*SLATE)
    pdf.set_font(FONT, "B", 9)
    pdf.write(4.8, _s("Safety Status: "))
    pdf.set_font(FONT, "", 9)
    pdf.multi_cell(_W - 10 - pdf.get_string_width("Safety Status: "), 4.8, _s(text), align="L")
    pdf.set_y(y + h + 2)


def _profiles(pdf: FPDF, a: dict, b: dict, scale: dict, names: tuple) -> None:
    gap, w = 5, (_W - 5) / 2
    y = pdf.get_y()
    heights = []
    for prof in (a, b):
        pdf.set_font(FONT, "", 8.5)
        h = 12
        for lab in ("strengths", "gaps"):
            h += pdf.multi_cell(w - 8, 4.4, _s(prof.get(lab) or "—"), dry_run=True, output="HEIGHT") + 7
        heights.append(h)
    h = max(heights)
    if y + h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()
    for i, (prof, name, key) in enumerate(((a, names[0], "parent_a"), (b, names[1], "parent_b"))):
        x = 18 + i * (w + gap)
        pdf.set_fill_color(*PANEL)
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
        pdf.set_xy(x + 4, y + 3)
        pdf.set_font(FONT, "B", 10)
        pdf.set_text_color(*TEAL)
        sc = scale.get(key)
        pdf.cell(w - 8, 5.5, _s(f"{name}" + (f"  (Score {sc} · {MATRIX[_band(sc)][1]})" if _band(sc) is not None else "")), new_x="LMARGIN", new_y="NEXT")
        for lab, title in (("strengths", "Strengths (Doing Well): "), ("gaps", "Gaps (Struggling): ")):
            pdf.set_xy(x + 4, pdf.get_y() + 1.5)
            pdf.set_text_color(*SLATE)
            pdf.set_font(FONT, "B", 8.5)
            pdf.cell(w - 8, 4.4, _s(title.strip()), new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(x + 4)
            pdf.set_font(FONT, "", 8.5)
            pdf.multi_cell(w - 8, 4.4, _s(prof.get(lab) or "—"), align="L")
    pdf.set_y(y + h + 3)


def _matrix(pdf: FPDF, scale: dict, names: tuple) -> None:
    cols = (16, 36, 50, 50, _W - 152)
    heads = ("Score", "Mode", "Strengths (Doing Well)", "Gaps (Struggling)", "Placement")
    if pdf.get_y() > pdf.h - 90:
        pdf.add_page()
    pdf.set_font(FONT, "B", 8)
    pdf.set_fill_color(*HEAD)
    pdf.set_text_color(*NAVY)
    pdf.set_draw_color(*BORDER)
    for wdt, hd in zip(cols, heads):
        pdf.cell(wdt, 7, _s(hd), border=1, fill=True)
    pdf.ln(7)
    bands = {k: _band(scale.get(k)) for k in ("parent_a", "parent_b", "joint")}
    for i, (rng, mode, good, bad) in enumerate(MATRIX):
        placed = [lbl for k, lbl in (("parent_a", names[0]), ("parent_b", names[1]), ("joint", "Joint")) if bands[k] == i]
        hit = bands["joint"] == i
        cells = (rng, mode, good, bad, "\n".join(placed) if placed else "--")
        pdf.set_font(FONT, "", 7.8)
        h = max(pdf.multi_cell(wdt - 2, 4, _s(c), dry_run=True, output="HEIGHT") for wdt, c in zip(cols, cells)) + 3
        y, x = pdf.get_y(), 18
        pdf.set_fill_color(*(AMBER_BG if hit else (255, 255, 255)))
        for j, (wdt, c) in enumerate(zip(cols, cells)):
            pdf.rect(x, y, wdt, h, style="DF")
            pdf.set_xy(x + 1, y + 1.5)
            bold = j in (0,) or (j == 1 and hit) or (j == 4 and placed)
            pdf.set_font(FONT, "B" if bold else "", 7.8)
            pdf.set_text_color(*(AMBER_TXT if j == 4 and placed else SLATE))
            pdf.multi_cell(wdt - 2, 4, _s(c), align="L")
            x += wdt
        if hit:
            pdf.set_draw_color(*AMBER)
            pdf.set_line_width(0.6)
            pdf.rect(18, y, _W, h)
            pdf.set_line_width(0.2)
            pdf.set_draw_color(*BORDER)
        pdf.set_y(y + h)
    if scale.get("rationale"):
        pdf.ln(2)
        pdf.set_font(FONT, "I", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.multi_cell(_W, 4.5, _s("Rationale: " + scale["rationale"]))


def _roadmap(pdf: FPDF, short: list, long: list) -> None:
    for title, items in (("Short-Term Goals (Next 30–90 Days):", short), ("Long-Term Goals (6–12 Months):", long)):
        pdf.set_font(FONT, "B", 9.5)
        pdf.set_text_color(*SLATE)
        pdf.cell(0, 6, _s(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT, "", 9)
        for it in items or ["—"]:
            pdf.set_x(24)
            pdf.multi_cell(_W - 6, 4.8, _s("•  " + it))
        pdf.ln(2)


def _resources(pdf: FPDF, rows: list) -> None:
    cols = (40, 62, _W - 102)
    pdf.set_font(FONT, "B", 8)
    pdf.set_fill_color(*HEAD)
    pdf.set_text_color(*NAVY)
    pdf.set_draw_color(*BORDER)
    for wdt, hd in zip(cols, ("Category", "Resource / Specialist", "Scope")):
        pdf.cell(wdt, 6.5, _s(hd), border=1, fill=True)
    pdf.ln(6.5)
    pdf.set_text_color(*SLATE)
    for r in rows or [{"category": "—", "resource": "Professional selects appropriate resources", "scope": ""}]:
        cells = (r.get("category", ""), r.get("resource", ""), r.get("scope", ""))
        pdf.set_font(FONT, "", 8)
        h = max(pdf.multi_cell(wdt - 2, 4, _s(c), dry_run=True, output="HEIGHT") for wdt, c in zip(cols, cells)) + 3
        y, x = pdf.get_y(), 18
        for j, (wdt, c) in enumerate(zip(cols, cells)):
            pdf.rect(x, y, wdt, h)
            pdf.set_xy(x + 1, y + 1.5)
            pdf.set_font(FONT, "B" if j == 1 else "", 8)
            pdf.multi_cell(wdt - 2, 4, _s(c), align="L")
            x += wdt
        pdf.set_y(y + h)


def build_evaluation_pdf(ev: dict, meta: dict) -> bytes:
    pdf = _new_pdf()
    pdf.footer_meta = f"Professional Evaluation · {meta.get('case_code') or ''} · professional working document · {meta.get('ai_model') or 'AI-assisted'} draft approved by {meta.get('professional') or 'the case professional'}"
    scale = ev.get("scale") or {}
    jb = _band(scale.get("joint"))
    meta = {**meta, "mode_line": f"Joint score {scale.get('joint')} – {MATRIX[jb][1]} (Level {MATRIX[jb][0]})" if jb is not None else "Not scored"}
    names = (meta.get("parent_a_name") or "Parent A", meta.get("parent_b_name") or "Parent B")
    _header(pdf, meta)
    _h3(pdf, "1. Safety First: Domestic Violence & IPV Screening")
    _safety(pdf, ev.get("safety_status") or "No safety status was drafted. The professional records safety-screening observations here.")
    _h3(pdf, f"2. Individual Profiles: {names[0]} & {names[1]}")
    _profiles(pdf, ev.get("parent_a_profile") or {}, ev.get("parent_b_profile") or {}, scale, names)
    _h3(pdf, "3. Comprehensive 1–10 Scale Analysis Matrix")
    _matrix(pdf, scale, names)
    _h3(pdf, "4. Actionable Growth Roadmap")
    _roadmap(pdf, ev.get("short_term_goals") or [], ev.get("long_term_goals") or [])
    _h3(pdf, "5. Resource & Referral Network")
    _resources(pdf, ev.get("resources") or [])
    return bytes(pdf.output())
