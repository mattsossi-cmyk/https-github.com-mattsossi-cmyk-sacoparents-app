# Phase 3 · Question-Tone Rewrites — Draft Diff for Sign-Off

**Status:** DRAFT — no code has shipped. Reply "approve" to ship all, or
line-edit any row and I'll apply just the ones you keep.

**Goal:** Soften accusatory phrasing across intake questions per your
"How easy or difficult is it for the two of you to exchange important
information about your child?" pattern. Keep clinical precision for
DV/coercion items (Safety Assessment) — those must NOT be softened.

---

## 1 · Co-Parenting Relationship Assessment (SNC / `coparenting_questions.py`)

Current tone is mostly first-person self-reflection already ("I share
important updates…") — good baseline. Only a handful lean accusatory
or blame-shaped. Suggested rewrites below; blanks = leave as-is.

| # | Section | Current | Suggested rewrite |
|---|---|---|---|
| s1q6 | Communication | "The other parent shares information with me when they should." | "How easy is it to get the information you need from the other parent about our child?" *(scale wording may need adjustment — see note below)* |
| s1q7 | Communication | "Conversations with the other parent escalate into conflict." | "How often do your conversations stay on the child rather than tipping into personal conflict?" *(reverse-scored flag flips: higher = better)* |
| s2q6 | Transitions | "My child shows anxiety in the hours before an exchange." | Keep — this is a factual observation about the child, not a judgment |
| s4q7 | Medical | "Medical decisions are made with both parents' input." | "How easy is it to make medical decisions together when they come up?" |
| s10 (all) | Long-term | Already first-person, no change | — |

> **Scale note:** if we shift several items from "Never / Rarely /
> Sometimes / Often / Always" (frequency) toward "Very difficult /
> Difficult / Neutral / Easy / Very easy" (ease), the scoring engine
> needs the same 0-4 mapping and reverse-flag revisited. Recommendation:
> keep the 0-4 frequency scale, only rewrite the *stem* — this
> preserves back-compatibility with past submissions.

---

## 2 · Special Needs Deep Dive — Medical (`med_deep_questions.py`)

Several "Does the other parent…" prompts. Full extract needed before
final rewrite; suggested pattern:

| Current pattern | Suggested rewrite pattern |
|---|---|
| "Does the other parent get a confirmation once medication has been picked up?" | "How easy is it to confirm that medication has been picked up between the two of you?" |
| "Does the other parent fail to communicate about missed doses?" | "How easy is it to hear about a missed dose in time to plan around it?" |
| "Do you disagree about medication timing?" | "When medication timing comes up, how easy is it to find a way forward?" |

**Action requested:** approve the pattern in principle and I'll enumerate
every "Does the other parent…" / "Do you disagree…" item across
`med_deep_questions.py`, `edu_deep_questions.py`, and
`psych_deep_questions.py` with a full before/after table in a follow-up.

---

## 3 · Special Needs Deep Dive — Educational

Same pattern as Medical. Full enumeration pending your approval on the
rewrite style.

---

## 4 · Special Needs Deep Dive — Psychological

Same pattern. Some items may be too therapeutic-vocabulary to soften
without losing signal ("Does your child dissociate during transitions?")
— those stay as-is.

---

## 5 · Trauma-Informed Safety Lens (TISFL) — **NO CHANGE**

The DV/coercion items ("Threatened to hurt or kill you, the children,
themselves, or someone you love?") are deliberately precise for a
reason — softening these would degrade clinical utility of a
family-violence screen. **Recommendation:** leave every item in
`safety_assessment_routes.py` unchanged.

---

## 6 · Special Needs V2 Intake

Currently phrased as neutral inquiries ("Which of the following
describe your child's current needs? Select all that apply.") — no
change proposed.

---

## Meta-Guidelines the Rewrite Follows

1. **Never accuse.** "Does the other parent fail to…" → "How easy is it
   to…" or "When X comes up, how easy is it to find a way forward?"
2. **Anchor to the child, not the adults' behaviour.** "Do you disagree
   about educational decisions?" → "When an educational decision comes
   up, how easy is it for our child to have a way forward?"
3. **Feelings-safe, not clinical.** "Rate your co-parenting conflict"
   → "Which description feels closest to your situation right now?"
4. **Keep signal.** For reverse-scored items where "worse" is the
   whole point (escalation, blame, control), the phrasing can be
   softer but the scoring flag must not change.
5. **DV/coercion items are exempt** — clinical precision protects
   safety screening.

---

## What I Need From You

- **Approve as-is** and I'll enumerate every remaining item across all
  three Deep Dive question banks in a follow-up diff, then ship
- **Line-edit** any row above with your preferred wording
- **Reject a rewrite pattern** if the current phrasing serves better
  clinical signal
- **Confirm the scale-note recommendation** (keep 0-4 frequency scale,
  only rewrite stems — no scoring engine changes)

Once you sign off on this draft, I'll do the full enumeration + ship
the code changes to the three Deep Dive banks and the SNC v2 stems
listed above. Ship will be one commit; no user-facing content changes
until then.
