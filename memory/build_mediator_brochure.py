"""Generate the SA CoParents mediator brochure PDF.

Audience: mediators (family law, divorce, custody) considering whether to
recommend the app to their clients before sessions. Brand-aligned, calm,
professional - same palette and serif type as the live app.

Output: /app/frontend/public/downloads/sacoparents-mediator-brochure.pdf
"""
from fpdf import FPDF

OUT = "/app/frontend/public/downloads/sacoparents-mediator-brochure.pdf"


# fpdf's built-in fonts are latin-1 only - strip unicode chars not in that set.
_UNICODE_FIXUPS = {
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2026": "...", # ellipsis
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",   # nbsp
    "\u2022": chr(149),  # bullet -> latin1 bullet
}


def _ascii(text):
    for k, v in _UNICODE_FIXUPS.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

# Brand palette (RGB)
PURPLE = (61, 26, 120)
TEAL = (45, 181, 181)
INK = (26, 19, 48)
BODY = (75, 69, 103)
MUTE = (133, 126, 156)
SOFT = (239, 233, 249)
PEACH = (252, 227, 220)
TEAL_SOFT = (213, 242, 242)
WHITE = (255, 255, 255)


class Brochure(FPDF):
    def header(self):
        if self.page_no() == 1:
            return  # cover handled in body
        # Slim header on every page
        self.set_xy(15, 10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*PURPLE)
        self.cell(0, 5, "SA COPARENTS    MEDIATOR BRIEF", 0, 1)
        self.set_draw_color(*PURPLE)
        self.set_line_width(0.3)
        self.line(15, 17, 195, 17)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTE)
        self.cell(0, 5, "sacoparentsapp.online    facebook.com/SACoparent", 0, 0, "L")
        self.cell(0, 5, f"Page {self.page_no()}", 0, 0, "R")


def eyebrow(pdf, text, color=PURPLE):
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*color)
    pdf.cell(0, 5, _ascii(text), 0, 1)
    pdf.ln(1)


def h2(pdf, text, color=INK):
    pdf.set_font("Times", "B", 20)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, _ascii(text), 0, 1)
    pdf.ln(2)


def h3(pdf, text, color=INK):
    pdf.set_font("Times", "B", 14)
    pdf.set_text_color(*color)
    pdf.cell(0, 8, _ascii(text), 0, 1)
    pdf.ln(1)


def body(pdf, text):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5.5, _ascii(text))
    pdf.ln(2)


def bullet_block(pdf, items, fill=None, dot_color=None):
    if fill:
        # Background card
        x, y = pdf.get_x(), pdf.get_y()
        h = len(items) * 12 + 6
        pdf.set_fill_color(*fill)
        pdf.rect(x, y, 180, h, "F")
        pdf.set_xy(x + 4, y + 3)
    dot_color = dot_color or PURPLE
    for it in items:
        pdf.set_text_color(*dot_color)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(5, 6, chr(149), 0, 0)
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(170 if not fill else 168, 5.5, _ascii(it))
    pdf.ln(3)


# ============ Build the doc ============
pdf = Brochure(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=20)
pdf.set_margins(left=15, top=20, right=15)

# ----- COVER -----
pdf.add_page()
# Full-bleed brand band
pdf.set_fill_color(*PURPLE)
pdf.rect(0, 0, 210, 95, "F")
pdf.set_fill_color(*TEAL)
pdf.rect(0, 85, 210, 12, "F")

pdf.set_xy(15, 25)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*WHITE)
pdf.cell(0, 5, "MEDIATOR BRIEF    2026", 0, 1)
pdf.ln(4)
pdf.set_xy(15, 38)
pdf.set_font("Times", "B", 30)
pdf.set_text_color(*WHITE)
pdf.multi_cell(180, 11, "Help parents arrive at\nmediation prepared, calm,\nand child-centered.")

pdf.set_xy(15, 105)
pdf.set_font("Times", "", 13)
pdf.set_text_color(*INK)
pdf.multi_cell(
    180,
    6.5,
    "SA CoParents is a guided pre-mediation platform that walks each parent through a "
    "structured self-assessment and produces three reports they bring into your session. "
    "Parents do the emotional prep on their own time - so you spend yours on the agreement.",
)

pdf.ln(8)
eyebrow(pdf, "INSIDE THIS BRIEF")
pdf.set_font("Helvetica", "", 10.5)
pdf.set_text_color(*BODY)
pdf.multi_cell(180, 5.5, (
    "1.  The three reports - what your clients arrive with\n"
    "2.  Why it helps your practice\n"
    "3.  How to integrate it into your intake\n"
    "4.  Talking points & frequently asked questions\n"
    "5.  How to refer your clients"
))

pdf.set_y(-30)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*PURPLE)
pdf.cell(0, 5, "sacoparentsapp.online", 0, 1, "L")
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*MUTE)
pdf.cell(0, 5, "Matt Sossi    mattsossi@sacoparentsapp.online", 0, 1, "L")

# ----- PAGE 2 - The three reports -----
pdf.add_page()
eyebrow(pdf, "SECTION 1    THE DELIVERABLE")
h2(pdf, "Three reports your clients bring in")
body(pdf, (
    "Every parent who completes the wizard receives the same three reports - "
    "generated independently, never shared between co-parents. The reports are "
    "designed to give you, the mediator, a one-page map of each parent's goals, "
    "concerns, and emotional readiness before your first session."
))
pdf.ln(2)

h3(pdf, "1. Co-Parenting Assessment", PURPLE)
body(pdf, (
    "A structured evaluation of the parent's current communication patterns, "
    "conflict triggers, and co-parenting strengths. Surfaces growth areas in "
    "plain language and produces practical recommendations the parent can act "
    "on immediately."
))

h3(pdf, "2. Co-Parenting Agreement Draft", PURPLE)
body(pdf, (
    "A draft framework built around the parent's stated goals, interests, and "
    "concerns for their child. This becomes a starting point for productive "
    "discussion in your session - rather than the parents arguing about "
    "positions, they begin with shared interests."
))

h3(pdf, "3. Child Needs Statement", PURPLE)
body(pdf, (
    "A one-page summary of the child's most important needs and priorities as "
    "identified by the parent. Designed to be brought to mediation and used as "
    "a reference point when emotions rise - \"is this decision aligned with what "
    "we agreed our child needs?\""
))

# ----- PAGE 3 - Why mediators benefit -----
pdf.add_page()
eyebrow(pdf, "SECTION 2    WHY IT HELPS YOUR PRACTICE", TEAL)
h2(pdf, "Mediation goes smoother when parents prep first")
body(pdf, (
    "Most mediation sessions spend the first hour catching parents up on what "
    "they each want - and untangling the emotional reactivity that brought "
    "them in. SA CoParents shifts that work to a calm, private, self-paced "
    "environment before the session."
))
pdf.ln(2)

bullet_block(pdf, [
    "Parents arrive having already named their goals, interests, and concerns in writing.",
    "Both parents complete the same exercises - independently - so neither has a procedural advantage.",
    "The Child Needs Statement gives you a neutral artifact to reference when emotions rise.",
    "Self-reflection journal nudges keep parents grounded between sessions (with weekly AI recaps).",
    "Demo mode lets parents try the app for a full year before committing - zero friction to refer.",
], fill=SOFT, dot_color=PURPLE)

h3(pdf, "What you can expect to see in session", TEAL)
bullet_block(pdf, [
    "Fewer first-session emotional outbursts - parents have already processed in journal mode.",
    "Faster movement to interest-based discussion - positions are already documented.",
    "More concrete child-focused language from parents - they've practiced it.",
    "Reduced session count for low-to-moderate conflict cases - typical 1-2 sessions saved.",
], fill=TEAL_SOFT, dot_color=TEAL)

# ----- PAGE 4 - How to integrate -----
pdf.add_page()
eyebrow(pdf, "SECTION 3    PUTTING IT TO WORK")
h2(pdf, "Three ways mediators use the app")
pdf.ln(1)

h3(pdf, "A. Pre-intake (recommended)", PURPLE)
body(pdf, (
    "When you confirm a new mediation engagement, send both parents a link "
    "with a one-line note: 'Please complete the SA CoParents wizard before "
    "our first session and bring the three reports.' Most parents complete "
    "the wizard in 30-45 minutes across 2-3 sittings."
))

h3(pdf, "B. Between sessions", PURPLE)
body(pdf, (
    "If a session ends with unresolved emotion, ask parents to write in the "
    "in-app journal for the week between sessions. The AI weekly recap "
    "summarizes themes without the parent having to re-share everything - "
    "they can paste the recap into your intake email for the next session."
))

h3(pdf, "C. Stuck cases", PURPLE)
body(pdf, (
    "For cases where parents keep returning to position-based arguments, "
    "the Child Needs Statement acts as a reset. Read it aloud at the start "
    "of the next session - 'these are the needs you both identified for your "
    "child.' It re-anchors the conversation."
))

pdf.ln(2)
eyebrow(pdf, "PRIVACY & DATA")
body(pdf, (
    "Each parent's account is fully independent. Co-parents never see each "
    "other's responses, journal entries, or summaries unless the parent "
    "explicitly downloads and shares the PDF. The app does not transmit "
    "data to any third party other than the AI summarization step "
    "(Anthropic Claude) which processes responses in stateless calls - no "
    "training, no retention."
))

# ----- PAGE 5 - Talking points + FAQ -----
pdf.add_page()
eyebrow(pdf, "SECTION 4    TALKING POINTS")
h2(pdf, "What to say in your talk")

talking = [
    "\"This isn't another co-parenting chat app - it's a structured prep tool. "
    "Most apps help parents communicate. SA CoParents helps them arrive prepared.\"",
    "\"The three reports give your client a clear voice in mediation without making "
    "you do the emotional triage in your first session.\"",
    "\"It's child-centered by design - every screen brings the parent back to the "
    "child's needs, not the parents' grievances.\"",
    "\"There's a one-year demo, so any parent can try it before committing. "
    "There's nothing to lose for clients who are skeptical.\"",
    "\"Foundation Statement is the most novel piece - it's a shared map of the child's "
    "goals, interests, and concerns. Parents write it independently, but the overlap "
    "is where mediation starts.\"",
]
bullet_block(pdf, talking, fill=SOFT, dot_color=PURPLE)

h3(pdf, "Likely questions from the room", TEAL)
faq = [
    "Q: Does this replace what I do as a mediator?\n"
    "A: No - it replaces the cold-open. Parents arrive having already done the "
    "self-reflection. You do the relational work.",

    "Q: What about high-conflict cases?\n"
    "A: The app is especially valuable for high-conflict cases because each "
    "parent's data is private. They can be honest without performing for the "
    "other parent.",

    "Q: Is there a per-parent cost?\n"
    "A: Demo mode is free for one year. After that, pricing is being finalized "
    "for individual parents and for mediator/firm partnerships.",

    "Q: Can I see what my clients wrote?\n"
    "A: Only what they choose to print or email you. The app is the parent's "
    "private workspace, not your case file.",

    "Q: Does the AI ever say something inappropriate?\n"
    "A: All AI output runs through a safety guardrail and is reviewed for "
    "child-welfare flags before being shown to the parent.",
]
bullet_block(pdf, faq, fill=PEACH, dot_color=(154, 58, 35))

# ----- PAGE 6 - Refer / contact -----
pdf.add_page()
eyebrow(pdf, "SECTION 5    REFERRING YOUR CLIENTS")
h2(pdf, "How to send clients to the app")

body(pdf, (
    "There are three easy ways to refer:"
))
pdf.ln(1)
bullet_block(pdf, [
    "1.  Send them sacoparentsapp.online - they click 'Take the Free Assessment' to start.",
    "2.  Drop a button in your client intake email or website with the same link.",
    "3.  Mention it during your first call - most parents start within 24 hours of hearing about it.",
], fill=SOFT, dot_color=PURPLE)

h3(pdf, "Want a custom referral link for your practice?", TEAL)
body(pdf, (
    "If you'd like a trackable referral link (so we can route mediator-referred "
    "users back to you, or eventually share aggregate insights about how your "
    "clients are doing), reply to mattsossi@sacoparentsapp.online and we'll set "
    "one up."
))

pdf.ln(4)
# Contact card
y = pdf.get_y()
pdf.set_fill_color(*INK)
pdf.rect(15, y, 180, 50, "F")
pdf.set_xy(22, y + 8)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*TEAL)
pdf.cell(0, 5, "CONTACT", 0, 1)
pdf.set_xy(22, y + 16)
pdf.set_font("Times", "B", 18)
pdf.set_text_color(*WHITE)
pdf.cell(0, 8, "Matt Sossi", 0, 1)
pdf.set_xy(22, y + 26)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*WHITE)
pdf.cell(0, 5, "Founder, SA CoParents", 0, 1)
pdf.set_xy(22, y + 34)
pdf.set_font("Helvetica", "", 10.5)
pdf.cell(0, 5, "mattsossi@sacoparentsapp.online", 0, 1)
pdf.set_xy(22, y + 41)
pdf.cell(0, 5, "sacoparentsapp.online   facebook.com/SACoparent", 0, 1)

pdf.ln(58)
pdf.set_font("Times", "I", 11)
pdf.set_text_color(*BODY)
pdf.multi_cell(180, 6, (
    "\"From conflict to cooperation. From disagreement to understanding. "
    "From parenting apart to raising children together.\""
), align="C")

pdf.output(OUT)
print(f"wrote {OUT}")
