# SA CoParents — Product Requirements Document

History of every change: `CHANGELOG.md` (the old long PRD). Open work: `ROADMAP.md`.

## Original Problem Statement
SA CoParents is a private parent-support platform for separated / co-parenting parents preparing for mediation
or court: Self Journey and Court Ordered paths, Self / Co-Parenting / Child Needs assessments, Foundation Statement,
Parallel Parenting Option Builder, BIFF Communication Builder, joint professional reports, HIPAA / Texas HB 300
hardening, secure sharing, and an AI coach.

## Product principles (permanent)
- Safety data: the Family check-in lives only on SACOparentsAlign. SA CoParents never renders, stores, infers or
  sends those answers, and never uses them to pick a parenting path. Align links use the shared `case_id` (SA-...),
  never `align_ref`. Status is "Confirmed by SACOparentsAlign on [date]" or "See SACOparentsAlign".
- The parent picks their own path after the check-in.
- Red "In danger?" crisis strip on every signed-in screen.
- Neutral, non-adjudicative language in reports; explicit consent before sharing.
- SAST / code-review findings list is DO NOT FIX (see CHANGELOG top).
- Old inbound webhooks are OFF in code (`backend/webhook_switch.py`; only `WEBHOOKS_ENABLED=true` turns them on).
  Keep `INTEGRATION_SHARED_SECRET` (Align pull export).

## Personas
Separated parents; mediators, family attorneys and DV practitioners; coordinators / admins; HB 300 reviewers.

## Architecture
React 19 + Tailwind + shadcn/ui · FastAPI + Motor/MongoDB · fpdf2 PDFs · Resend email · Claude via Emergent LLM
key · custom JWT auth (`auth.py`).

## Journey pages
- `/journey` Journey Flow (`pages/JourneyFlow.jsx`). Step 1 opens the Self Journey guide.
- `/self-journey/:step` guided Self Journey (`pages/selfJourney/SelfJourney.jsx` + `SelfJourneyPage.jsx`,
  API `backend/self_journey_routes.py` → collection `self_journey_progress`):
  Safety (link out to Align + the parent's own clear/concern pick) → Situation (private notes) → existing
  Self-Assessment → existing Co-Parenting Assessment → existing Child Needs forms → Foundation (approve saves into
  `/api/foundation-builder/me` fields.statement) → Mediation (private notes) → Summary (statuses only; print + /summary).
- Private notes and the safety pick appear only on the parent's own screen: never on the Summary, PDF, /summary,
  email, Align export or AI.
- Journey Guide help: `/api/journey-guide/self-journey/chat` (session_id reused), behind the AI notice. Avatar
  `/images/guide-avatar.webp` (user's heart-family logo, purple + dark blue + white) in a circle; turns 360° once per
  question; no spin in Calm Mode.

## Test accounts
See `test_credentials.md`.
