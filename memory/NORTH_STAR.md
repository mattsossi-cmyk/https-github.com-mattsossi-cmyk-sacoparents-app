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

## Phase Plan (status)

- **Phase A** ✅ **DONE (iter244)**: Built `<JourneyShell>` as the
  5-step scaffold. New default view at `/`.
  Scaffolded `/align`.

- **Phase B** ✅ **DONE (iter245)**: Merged the toolkit tile grid
  INTO the steps. Each existing surface (BIFF Coach,
  Alignment Records, Foundation Statement, Assessment Guide,
  Snapshot Library) now has a home inside its step panel.
  Testids preserved. Shell's `expanded` state now falls
  through to `pickCurrentStep` dynamically so late-hydrating
  signals (courtKey, safetyAck) correctly auto-expand.

- **Phase C** ✅ **DONE (iter246)**: Court-Ordered path is a
  Step 1 variant that fast-forwards. `verifyProfessionalKey`
  routes to the journey shell + auto-elevates Step 3. Banner
  renders with Case ID + mediator name.

- **Phase D** ✅ **DONE (iter247)**: Deleted `?view=advanced`
  kill-switch, DoorsGateway import, `screen === "gateway"`
  render path, and the "Advanced view (legacy)" escape hatch.
  The old gateway cannot be reached from the UI at all.

- **Phase E (DevOps, future)**: Split the two domains in
  prod. `sacoparentsapp.online` ships only `/*` (parent).
  `sacoparentsalign.online` ships only `/align/*` and
  `/admin/*` routes.

- **iter248 (future)**: Inline BIFF Coach into Step 4 panel
  + Alignment Records folder into Step 3 panel. Currently
  these still route into the legacy parent-journey screen
  for the heavy modal UI. Once inlined, `screen === "parent-journey"`
  can also be deleted.

- **iter249 (future)**: Render the grey-rock audit timeline
  on the Mediator Progress PDF (`cp_progress_pdf.py`). The
  audit log backend was built for exactly this clinical use.

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
