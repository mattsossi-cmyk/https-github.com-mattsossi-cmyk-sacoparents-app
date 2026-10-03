# SA CoParents — North Star Architecture

**Set 2026-02-27 (iter244). The architectural principle that
overrides every future feature decision.**

## The One Rule

**The parent should never have to understand the structure of
the app. The app should understand where the parent is and
guide them.**

Every new feature from this point forward must fit under one of
the five journey steps below. If a feature doesn't fit, the
feature is wrong — not the five steps.

## The Five Steps (parent-facing)

| # | Parent language | What's behind it |
|---|-----------------|------------------|
| 1 | **Start My Journey** | IntroChatBot, two doors (Voluntary + "I was sent here"), SafetyFirstEntryButton |
| 2 | **Understand My Situation** | SafetyScreen modal, Grey-rock toggle chip, 40-Q self-assessment preview, CpProgressTile sparkline, 60-day retake nudge |
| 3 | **Focus on My Child** | 70-Q Co-Parenting Assessment, Educational/Medical/Psychological deep-dives, Guided Journey wizard (child-needs topics), Alignment Records folders |
| 4 | **Explore Options** | BIFF Coach, Communication reflections, Mediation Prep tools, Court-ordered artefacts (surface only when relevant) |
| 5 | **Create My Plan** | Foundation Statement, Guided Journey → Snapshot Library (standard + fridge + fridge pair), Share-with-Mediator PDF, Joint Report request, Email-to-coparent (grey-rock gated) |

**Nothing else is a top-level nav choice.** No tile grid, no door
alley, no artefact names in the parent's navigation. A parent in
grey-rock mode or a parent who just signed up should see **only
the five steps** and whichever one the system puts them on.

## The Two-Site Distinction (rigid)

### SA CoParents App — the parent's journey
- URL (today): `/sacoparents-portal`
- URL (future prod domain): `sacoparentsapp.online`
- Content: the five steps above, only.
- Language: parent-facing. "Your child," "How are things going,"
  "A short private check," never "assessment #4" or "artefact
  7A." Clinical copy only inside the Safety Screen itself.
- Nav: no artefact names. No admin surfaces. No case IDs.

### SA CoParents Align — the professional's view
- URL (today): `/align` (holding page) + `/admin` + `/complete-alignment-report/*` + `/professional-review/*` + `/joint-alignment-*`
- URL (future prod domain): `sacoparentsalign.online`
- Content: artefact-first navigation. Mediators and attorneys
  think in Case IDs, Joint Reports, Alignment Maps, Health
  Indexes. That language is CORRECT for them.
- Language: clinical and formal. Case Reference numbers, PHI
  access logs, HB 300 compliance text, Virtru/Resend send
  receipts. Parent-journey copy is NEVER rendered here.
- Nav: mediator dashboard, case list, bulk history, admin
  analytics.

### Enforcement
- Router guard: `/sacoparents-portal/*` and `/align/*` are
  mutually exclusive — no shared layout component, no shared nav.
- Future DNS split (DevOps): once prod has both domains, each
  app ships ONLY the routes for its side.

## Phase Plan (committed order)

- **Phase A (iter244, this iter)**: Build `<JourneyShell>` as the
  5-step scaffold. New default view at `/sacoparents-portal`.
  Old gateway kept behind `?view=advanced` escape hatch for 2-3
  iters. Scaffold `/align` as a holding page. **All existing
  components reused verbatim** inside the steps — zero PDF/AI/
  report code touched.

- **Phase B (iter245)**: Merge the toolkit tile grid INTO the
  steps. Each existing surface (BIFF Coach, Alignment Records,
  Foundation Statement, Assessment Guide, Snapshot Library)
  moves inside its step. The horizontal tab-switcher
  (`alignment` / `biff` / `pdf-export`) dies. Testids
  preserved.

- **Phase C (iter246)**: Court-Ordered path becomes a Step 1
  variant that fast-forwards to the referred artefact.
  Parse the Court Key, auto-route to the referred assessment
  as Step 3 state, surface the other four steps as context.

- **Phase D (iter247)**: Audit `/align` for parent-journey copy
  leaks and `/sacoparents-portal` for professional-nav leaks.
  Delete the old `screen === "gateway"` code path. Delete
  `?view=advanced` escape hatch.

- **Phase E (DevOps, parallel to C/D)**: Split the two domains in
  prod. `sacoparentsapp.online` ships only `/sacoparents-portal/*`
  routes. `sacoparentsalign.online` ships only `/align/*` and
  `/admin/*` routes.

## What NEVER changes

- Clinical guardrails: Safety Screen, grey-rock mode, DV
  resources. Copy is locked.
- PDF generation code: `fpdf2` builders stay as-is to preserve
  the "PDFs and frontend strings in exact lockstep" invariant.
- `ai_service.py` prompt templates: locked.
- `safety_ack` schema and the Safety-First auto-route: locked.
- Resend / Virtru email paths: locked.

## What's up for grabs

- The parent-facing UI chrome (nav, step indicators, cards,
  copy OUTSIDE the clinical surfaces).
- The toolkit tile grid: scheduled for demolition in Phase B.
- The horizontal hub-section tab-switcher: scheduled for
  demolition in Phase B.
- The old `DoorsGateway` component: scheduled for demolition
  in Phase D.
