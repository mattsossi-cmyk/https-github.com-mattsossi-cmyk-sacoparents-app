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
- `/journey` Journey Flow (`pages/JourneyFlow.jsx`). Step 1 opens the Self Journey guide. Parallel path = one card: Step 3 Parallel Parenting Builder.
- `/self-journey` + `/self-journey/:stepId` READING Self Journey (`pages/SelfJourney.jsx`, founder's file): public, 7 pages,
  finished-page ticks in localStorage `sacp_self_journey_done` only; Safety First page shows StartWithSafetyBanner; finish links
  comm-builder / guided summary PDF / help / court. Old guided slugs redirect to the guided URL. Home picture + door-self -> here.
  /journey-library(/:id) redirects here (old ticks `sacp_journey_library_done` merged once, then removed; JourneyLibrary.jsx deleted).
  Each page has "Print this page" (sjr-print) -> one-page print-only handout (`pages/SelfJourneyHandout.jsx/.css`, portal to body,
  3 writing lines per reflection question, disclaimer + hotlines + page URL). Browser print / Save as PDF; nothing sent anywhere.
- `/self-journey/guided/:step` guided Self Journey (`pages/selfJourney/SelfJourney.jsx` + `SelfJourneyPage.jsx`,
  API `backend/self_journey_routes.py` → collection `self_journey_progress`):
  Safety (link out to Align + the parent's own clear/concern pick) → Situation (private notes) → existing
  Self-Assessment → existing Co-Parenting Assessment → existing Child Needs forms → Foundation (approve saves into
  `/api/foundation-builder/me` fields.statement) → Mediation (private notes) → Summary (statuses only; print + /summary).
- Private notes and the safety pick appear only on the parent's own screen: never on the Summary, PDF, /summary,
  email, Align export or AI.
- Journey Guide help: `/api/journey-guide/self-journey/chat` (session_id reused), behind the AI notice. Avatar
  `/images/guide-avatar.webp` (user's heart-family logo, purple + dark blue + white) in a circle; turns 360° once per
  question; no spin in Calm Mode.

## Self Journey extras (2026-10-23)
- Awards: 4 milestones only (Self-Assessment, Co-Parenting Assessment, Foundation approved, whole journey) + certificate PDF.
- Monthly check-in: in-app only, every 30 days after the Self-Assessment, never on Safety, private (never printed/shared).
- Server PDF GET /api/self-journey/pdf: 7 sections, notes/check-ins/safety pick left out.
- Journey Guide uses the founder's system prompt and receives the parent's own safety pick.

- No reminder / progress emails to parents for Self-Assessment retakes or the Self Journey (in-app only).
- Co-Parenting report swaps joint suggestions for separate ones when the parent shared concerns (pick or safety flag).

## Privacy & wording (2026-10-24)
- Parent-facing name for the Align check-in is **Safety First** (was "Family check-in"), incl. NOT_AVAILABLE note + court checklist row (user chose).
- `components/PrivacyGuard.jsx` (founder's code) disables GA/fbq/PostHog on /self-journey, /start-with-safety, /safety-first. No trackers exist in the app.
- `components/Disclaimer.jsx` on reading + guided Self Journey, home portal, Start with Safety. ConsentGate leaves public reading/safety pages open.

## Test accounts
See `test_credentials.md`.
