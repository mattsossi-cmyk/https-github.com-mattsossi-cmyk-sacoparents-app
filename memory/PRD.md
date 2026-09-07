# SA CoParents — Product Requirements Document

## Original Problem Statement
Enhance the SA CoParents platform with comprehensive Joint Professional artefacts
(Joint Report, Joint Agreement, Professional Intro PDF) designed for mediators
and attorneys with strict neutral-language guardrails. Implement deep HIPAA and
Texas HB 300 compliance hardening (PHI access logs, legal pages, breach
runbooks), security audits, secure sharing flows, and encrypted email
transmission via Virtru.

**Product principles:** strict clinical guardrails on safety data, neutral
non-adjudicative language in all reports, explicit user consent before sharing,
and robust privacy policies.

## Core User Personas
- Separated / co-parenting parents preparing for mediation or court
- Mediators, family attorneys, and DV practitioners receiving reports
- Coordinators & admin operators monitoring high-risk cases
- Texas HB 300 covered entities reviewing PHI handling

## Architecture Snapshot
Frontend: React 19 + Tailwind + shadcn/ui
Backend: FastAPI + Motor/MongoDB
PDF: `fpdf2` (`pdf_service.py`, `joint_*_pdf.py`, `admin_nd_case_pdf.py`)
Email: Resend SDK (default) + Virtru Gateway SMTP (flag-gated, BAA-pending)
LLM: Claude Sonnet 4.5 via Emergent LLM Key
Auth: Custom JWT (`auth.py`)

## What's Implemented
### 2026-09-07 — Shared Preview Page + Reminder Preview Modal + Bulk CSV
- **P1 — Foundation Statement Shared Preview** (`/foundation/shared/:token`) —
  every share now mints a **30-day revocable JWT preview link** the
  recipient (co-parent, mediator, attorney) can open in-browser without
  logging in.
    - New endpoints on `/api/mediation`:
      - `GET /foundation-statement/shared/{token}` — public JSON with
        the four canonical sections + sender name + optional landing
        note. Never leaks the sender's user_id / email / other prep
        surfaces.
      - `GET /foundation-statement/shared/{token}/voice/manifest` +
        `.../voice/section/{key}` — public voice endpoints that share
        the SAME per-user cache as the authenticated `/my-plan` player
        (parent's own play + recipient's play never re-bill for the
        same content).
    - Share + resend endpoints on `/api/mediation` now embed the
      `preview_url` in the emailed HTML (purple "Open the statement
      online" pill) AND return it in the JSON response so the
      Share modal can copy-to-clipboard for the sender.
    - New public page `FoundationStatementShared.jsx` — reads the
      manifest, renders sender name + sections + Read-to-me
      (Shimmer/Nova/Alloy/Fable), highlights each section as it
      plays, and closes with the neutral court-report disclaimer.
    - 404s cleanly for expired / revoked / invalid tokens AND for
      cases where the sender wiped their reflection after minting.
- **P1 — Reminder Preview Modal** — the mediator now taps a
  **Preview** pill next to the reminder-note field on `/mine` and
  sees the EXACT email the 5-day gentle-nudge sweep will send:
    - Backend: new `render_joint_alignment_invitation_reminder(...)`
      pure renderer in `email_service.py`. Existing send helper
      delegates to it, so preview + send stay in lockstep forever.
    - New endpoint
      `GET /api/professional/joint-alignment/cases/{case_id}/reminder-preview?parent_index=0|1`
      (JWT + owner-only). 400 for out-of-range parent index,
      404 for foreign cases.
    - Response shape: `{subject, html, text, parent_email,
      parent_name, parent_accepted, has_reminder_note}`.
    - Frontend `ReminderPreviewModal.jsx` — 2-tab modal
      (HTML in a `sandbox=""` iframe / plain-text fallback) with
      Parent 1 / Parent 2 toggle and an "already accepted — this
      email would NOT fire" info badge when the sweep would skip
      that recipient.
- **P2 — Bulk CSV Invite** — mediators can now mint up to **100
  Joint Alignment cases per upload** from one CSV.
    - Backend: refactored `professional_create_case` into a
      shared `_create_and_invite_case(...)` core so the new bulk
      endpoint reuses the exact minting + invite path (no
      code-drift risk).
    - `POST /api/professional/joint-alignment/cases/bulk-csv`
      (multipart) — parses the CSV with flexible header aliases
      (`parent1_email` / `parent_1_email` / `email_1`, etc.),
      silently skips rows that would duplicate an active case
      owned by the caller, and returns per-row `created` /
      `skipped` / `errored` arrays so partial uploads never abort.
      128 KB / 100 row caps. Optional `default_assessment_type` +
      `default_reminder_note` query params fill blank cells.
    - `GET .../bulk-csv/template` — JWT-required CSV template
      download with headers + example row.
    - Frontend `ProfessionalJointAlignmentBulk.jsx` at
      `/professional/joint-alignment/bulk`:
      3-step layout (template → defaults → upload) + a
      dropzone + a per-row results table with `Copy all
      invitation URLs` action for the mediator to paste into
      their case-management sheet.
    - New "Bulk import" pill in the `/mine` header row.
- **Coverage** — `tests/test_iter159_shared_preview_and_bulk.py`
  (19 tests: 5 shared preview, 5 reminder preview, 9 bulk CSV).
  Combined regression against iter150-159: **145 tests green**.
- **Live-verified**: parent1 shares statement → email + preview URL
  → mediator opens URL unauthenticated → 4 sections rendered +
  Read-to-me plays with Shimmer → section highlight follows.
  Admin mediator opens `/mine` → Preview pill on a case row →
  modal shows exact HTML + plaintext with case ID + note.
  Bulk upload of 3-row CSV (2 valid, 1 invalid email) → 2 cases
  created, 1 errored, results tiles render correctly.
- **Files touched**:
  - `backend/mediation_routes.py` (adds `_mint_foundation_share_link`,
    public shared endpoints, preview_url in share/resend responses)
  - `backend/email_service.py` (adds `preview_url` param to
    Foundation share email, adds `render_joint_alignment_invitation_reminder`
    pure renderer)
  - `backend/joint_alignment_routes.py` (extracts
    `_create_and_invite_case`, adds bulk CSV endpoint + template
    endpoint + reminder-preview endpoint, imports UploadFile +
    ValidationError)
  - `frontend/src/pages/FoundationStatementShared.jsx` (new)
  - `frontend/src/pages/ProfessionalJointAlignmentBulk.jsx` (new)
  - `frontend/src/components/professional/ReminderPreviewModal.jsx` (new)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx` (mounts
    the ReminderPreviewModal + adds `Bulk import` pill in header +
    Preview button on each reminder-note pill)
  - `frontend/src/components/foundation/FoundationStatementShareModal.jsx`
    (auto-copies preview_url to clipboard on successful share)
  - `frontend/src/App.js` (registers 2 new routes)
  - `backend/tests/test_iter159_shared_preview_and_bulk.py` (new, 19 tests)


### 2026-09-07 — Foundation Statement Voice Playback ("Read to me")
- **New `/app/backend/foundation_statement_voice.py`** — pure module
  that sanitises reflection text (strips emoji / URLs / markdown
  before TTS), composes the spoken form (section 0 gets a "Here is
  your Foundation Statement..." preamble so a forwarded recording is
  self-contained), and provides a per-section idempotent Mongo cache
  keyed on `(user_id, section_key, text_sha, voice, model, format)`.
  Supported voices: `shimmer` (default), `nova`, `alloy`, `fable`.
  Supported models: `tts-1` (default), `tts-1-hd`.
- **New endpoints** on `/api/mediation`:
    - `GET /foundation-statement/voice/manifest?voice=…&model=…`
      returns the ordered [{index, key, label, text, word_count,
      audio_url}] payload matching the PDF renderer's section order,
      plus `supported_voices` + `supported_models` so the frontend
      can build the voice dropdown from a single source of truth.
      409 when the reflection is empty; unknown voice/model
      degrades silently to the defaults.
    - `GET /foundation-statement/voice/section/{key}?voice=…&model=…`
      streams `audio/mpeg` bytes for a single section. Cached forever
      per (user, content, voice); tweak the text and only that
      section re-bills. Emits `X-Voice-Cache: hit|miss` so QA can
      inspect. 404 for unknown section, 409 for empty reflection.
- **`FoundationStatementVoicePlayer` (React)** — the "Read to me"
  component. Two variants share the same underlying state:
    - `variant="inline"` — pill button next to Send/PDF on the
      Foundation Statement card, plus a small voice dropdown.
    - `variant="floating"` — fixed bottom-right FAB (mobile-first).
      Only mounts when the parent actually has statement content.
    - Play/Pause/Resume/Stop, session-scoped blob-URL cache, and
      pre-warms the next section while the current one plays so
      playback is gapless. Emits `onSectionChange(sectionKey|null)`
      up to MyPlan.
- **`/my-plan` highlighting** — Foundation Statement card lights each
  section with a soft purple background (`data-voice-active="true"`)
  as it's read aloud. Follows `prefers-reduced-motion` for the
  transition.
- **Coverage** — new `tests/test_iter158_foundation_voice.py` (19
  tests, 18 pure + 1 live-TTS smoke that verifies audio/mpeg content
  and cache-hit round-trip). Regression: 51 tests green across
  iter154 + iter155 + iter157 + iter158 combined.
- **Live-verified**: parent1@test.com → /my-plan → clicked "Read to
  me" → audio played back through Shimmer voice at 10.7s duration →
  first section highlighted purple → Nova voice switch worked →
  Pause + Stop + Resume all worked → mobile 390px viewport clean.
- **What's not shipped**: mediator-facing playback. Mediators
  currently receive the statement as an emailed PDF, and there is
  no in-app screen where they view the statement's prose content
  (`/mine` shows cases, not reflections). Adding a token-based
  shared-statement preview page (like `/joint-agreement/shared/`)
  would unlock mediator-side Read-to-Me in one iteration.
- **Files touched**:
  - `backend/foundation_statement_voice.py` (new)
  - `backend/mediation_routes.py` (adds `/voice/manifest` +
    `/voice/section/{key}` endpoints)
  - `backend/requirements.txt` (adds `emoji==2.15.0` for TTS
    text sanitisation)
  - `frontend/src/components/foundation/FoundationStatementVoicePlayer.jsx` (new)
  - `frontend/src/pages/MyPlan.jsx` (mounts inline + floating
    players, wires section highlight state)
  - `backend/tests/test_iter158_foundation_voice.py` (new, 19 tests)


### 2026-09-07 — Coach model chip + Case Notes + Share History
- **Coach Model Picker Chip** — `/coach` page shows a two-state pill
  "Sharper (GPT) ⇄ Warmer (Claude)" (top-right of both empty state
  and active session). Choice persists to
  `localStorage['sacoparents.coach.model']` and forwards as `body.model`
  on every send. `null` (no pick) uses the app-wide primary.
- **Renamed "Start reflecting"** CTA on the Communicate More Effectively
  circle → "Draft a message" (last "reflection" text purged from
  above-the-fold dashboard).
- **Case Notes** (private, mediator-only) — new field
  `case_notes` (max 2000 chars) on `joint_alignment_cases`.
    - `PATCH /api/professional/joint-alignment/cases/{case_id}/case-notes`
      (owner-only, 404 on stranger)
    - Surfaces in `/cases-i-created` (mediator-authenticated), but
      NEVER in any parent-facing payload — regression test locks
      the contract.
    - New inline expand-to-edit UI on `/mine` row, clearly labelled
      "Private notes · never shared with parents".
- **Foundation Statement Share History** — parents see every past send
  from the "History" tab in the Share modal, with one-tap Resend.
    - `GET  /api/mediation/foundation-statement/shares` (last 25)
    - `POST /api/mediation/foundation-statement/shares/{share_id}/resend`
      — regenerates the PDF from the CURRENT reflection and reuses
      the original recipient + note, share-quota shared with first sends.
    - Old audit rows now store `share_id` + `personal_note` verbatim
      (previously only `had_personal_note` bool).
- **Tests** — new `tests/test_iter157_case_notes_and_share_history.py`
  (10 green: owner guard, private-notes non-leak, resend uses
  original recipient + note, resend 409 when reflection wiped,
  resend 404 for stranger).
- **All 86 in-scope backend tests: green.**


### 2026-09-07 — ChatGPT-first: app-wide model default flipped to GPT
- **New shared config** — `/app/backend/ai_models.py` exposes
  `resolve_model(preference)` returning `(provider, model_name)`.
  App-wide primary is `gpt-5.4` (openai) with `claude-sonnet-4-5-20250929`
  (anthropic) as the on-demand fallback. Flip via
  `AI_PRIMARY_MODEL=gpt|claude` env var.
- **9 AI surfaces refactored** to use the shared config: `ai_service.py`
  (coach, coaching, agreement drafts), `ai_summary.py`,
  `ai_summary_activities.py`, `ai_summary_communication.py`,
  `ai_summary_parenting_schedule.py`, `deep_dive_section_coach.py`,
  `insights_routes.py`, `learning_routes.py`, `safety_ai_summary.py`.
- **`?model=` / `body.model` toggle** now flows through the coach
  chat + all summary surfaces. Parents can pin a specific tone
  ("claude" for the warmer voice, "gpt" for the sharper one)
  without changing the app-wide default.
- **`/coach` chat page** — pre-existing chat UI (starters library,
  past-conversations sidebar, session persistence) now runs on
  GPT-5.4 by default. Verified end-to-end with 800-char reply +
  followups + safety_flag detection.
- **Regression tests** — `tests/test_iter156_ai_models_config.py`
  (12 green: env matrix, override precedence, primary/fallback
  pins, coach endpoint passes `model_preference` through).
- **All 76 in-scope backend tests: green.**


### 2026-09-07 — Foundation Statement Share (send-before-session)
- **New PDF** — `foundation_statement_pdf.py` composes a one-page,
  parent-authored artefact from the four canonical Reflection prompts.
  Includes purpose strip, court-report disclaimer, and provenance
  watermark (author + timestamp) on every page.
- **New endpoints**:
    - `GET  /api/mediation/foundation-statement.pdf` — download own
      Foundation Statement PDF (409 when reflection is empty).
    - `POST /api/mediation/foundation-statement/share` — email PDF to
      recipient. Rate-limited to 5/hour per user, refuses self-address
      (400), refuses empty reflection (409), 502 on provider failure,
      200 with `remaining_this_hour` counter on success.
- **New email helper** — `send_foundation_statement_share()` in
  `email_service.py`. Neutral, non-adjudicative copy; reply-to points
  to the sender's email; optional personal note rendered as a callout.
- **Frontend**:
    - `FoundationStatementShareModal` (React) — two tabs (Email /
      Download PDF), form validation, dialog semantics + Escape close.
    - Wired into `/my-plan` Foundation Statement card ("Send to
      co-parent or mediator" pill).
    - Wired into `/reflection` sticky footer — appears after Save.
- **Audit trail** — new `foundation_statement_shares` collection.
- **Tests** — `tests/test_iter155_foundation_share.py` (14 green,
  incl. live-server API + Resend delivery via `delivered@resend.dev`).


### 2026-09-07 — Foundation Statement rendering bug fix
- **Root cause 1** (`MyPlan.jsx:100`) — `data = prep.data` but the
  `/api/mediation/prep` endpoint returns `reflection`/`child_goals`/
  etc. at the TOP level, no `.data` envelope. This silently emptied
  every card on `/my-plan` — Foundation Statement, Child Goals,
  Assessments Completed all showed empty-state placeholders even
  when the parent had completed them.
- **Root cause 2** (`MyPlan.jsx:105`, `ai_service.py:924`) — both
  read a non-existent `reflection.text` / `reflection.foundation`
  field. Reflection.jsx actually saves prompts under keyed fields:
  `child_lens`, `own_part`, `best_outcome`, `coparent_feedback`.
- **Fix** — MyPlan now reads `prep` directly and composes the
  Foundation Statement as four labelled sections. `_coach_context_block`
  now composes the same excerpt from the four canonical prompt keys
  (with legacy-key + monolith fallbacks). Regression suite in
  `tests/test_iter154_foundation_composition.py` (6 tests, all green).
- **Verified end-to-end** — parent1@test.com has a saved reflection;
  `/my-plan` now renders "Through your child's eyes / Your own part /
  Your best-case outcome / Through your co-parent's eyes" as four
  distinct labelled sections and Assessments Completed shows 6/6.


### 2026-09-07 — Code Review action items (Professional Joint Alignment scope)
- **P1 — PDF watermark clipping fix** (`court_report_disclaimer.py`) —
  Right-aligns the "Downloaded by …" firm-name + timestamp stamp by
  subtracting the measured `get_string_width` so long firm names no
  longer overflow off the page edge. Fresh regression tests in
  `tests/test_iter153_watermark_placement.py` cover the fix.
- **P2 — `prefers-reduced-motion` respected** (`frontend/src/index.css`) —
  Kills the infinite `.recommended-pulse` and staggered entrances for
  users with OS reduced-motion set (WCAG 2.2.2 / 2.3.3).
- **P2 — Weekly digest send window now in local TZ**
  (`weekly_case_analytics_email.py`) — Monday-morning digest window
  is evaluated in the configured local timezone (defaults to
  `America/Chicago` — the app's operating market). Test suite
  updated to match; new env vars `WEEKLY_CASE_ANALYTICS_TZ`,
  `WEEKLY_CASE_ANALYTICS_START_HOUR`, `WEEKLY_CASE_ANALYTICS_END_HOUR`.
- **P2 — Download-PDF modal has proper dialog semantics**
  (`ProfessionalJointAlignmentMine.jsx`) — `role="dialog"`,
  `aria-modal="true"`, `aria-labelledby`, Escape-to-close, and
  focus returned to the trigger button on close.
- **Minor a11y polish** — `aria-pressed` on status-filter pills +
  `WeeklyDigestToggle`; `role="alert" aria-live="polite"` on error
  banners in `/mine`, `/new`, and `CaseAnalyticsCard`;
  `<main id="main-content">` landmark on `/for-professionals`.
- **UX consistency** — Revoke button hidden on `both_complete`
  cases (Download PDF remains); revoking a completed case wasn't
  a coherent action from the mediator's mental model.


### 2026-03-07 — Custom Reminder Copy for the 5-day nudge
- **Data model** — case docs now carry an optional
  `reminder_note` (max 240 chars) captured at mint time. Existing
  cases store `None` and behave exactly as before (generic
  reminder copy).
- **Backend endpoints**:
    - `POST /api/professional/joint-alignment/cases` accepts
      `reminder_note` in the body — the string is stripped and
      normalised to `None` when empty.
    - `PATCH /api/professional/joint-alignment/cases/{id}/reminder-note`
      (JWT + owner-only). Idempotent upsert to set or clear
      (`{"reminder_note": null}`) the note post-mint. 404 on
      cross-professional attempts (ownership guard).
    - `GET /api/professional/joint-alignment/cases-i-created`
      now exposes `reminder_note` on each row so the console can
      preview / edit inline.
- **Reminder email pass-through** — the 5-day gentle nudge sweep
  (`joint_alignment_invite_nudge`) now attaches
  `reminder_note` to every (case, parent) dispatch row.
  `email_service.send_joint_alignment_invitation_reminder`
  renders the note as a purple-left-bordered `<blockquote>`
  right below the greeting with a small
  "A NOTE FROM [Mediator Name]" eyebrow — the parent sees their
  mediator's voice, not a generic template. Plaintext email
  fallback also includes the note.
- **Frontend `/new`** — added a 240-char textarea "Personal
  reminder note (optional)" (`pj-reminder-note`) with a live
  `X/240` character counter and helper copy "Shown to the
  parent if we send the 5-day gentle nudge."
- **Frontend `/mine`** — every non-terminal case row now shows
  either:
    - A tap-to-edit purple pill with the current note (italicised
      quote + "tap to edit" hint) →
      `pj-mine-note-preview-{case_id}`.
    - Or a subtle "Add a personal reminder note" link when no
      note is set → `pj-mine-note-add-{case_id}`.
  Editing swaps the pill for an inline textarea (`Cancel` /
  `Save` buttons with save-in-flight spinner). Save calls
  PATCH, refreshes the list, and toasts "Reminder note saved"
  (or "Reminder note cleared" when saved empty).
- **Coverage grew iter150 from 21 → 25** (persist on create,
  240-char cap enforced, PATCH set + clear round trip, PATCH
  owner-only 404), and **iter151 from 6 → 7** (reminder_note
  threads through to the dispatch row picked up by
  `_find_stale_pending_parents`). All 42 tests green together
  across iter150 + iter151 + iter152.
- **Live E2E verified**: minted new case with a 37-char note,
  navigated to `/mine`, saw the purple preview pill, tapped it
  to edit, saved a new value, and confirmed the updated text
  rendered. Also added a fresh note to a previously-no-note
  case successfully.
- **Files touched**:
  - `backend/joint_alignment_routes.py` (adds
    `reminder_note` field on `ProfessionalCreateCaseRequest`,
    `ReminderNoteRequest` model, `PATCH /reminder-note`
    endpoint, exposes `reminder_note` on
    `cases-i-created`)
  - `backend/joint_alignment_invite_nudge.py` (threads
    `reminder_note` from case doc through to dispatch rows and
    into `send_joint_alignment_invitation_reminder`)
  - `backend/email_service.py` (adds `reminder_note` param
    on the reminder email + purple blockquote HTML rendering)
  - `frontend/src/pages/ProfessionalJointAlignmentNew.jsx`
    (adds textarea + counter + submit wiring)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx`
    (adds preview pill + inline edit + save flow)
  - `backend/tests/test_iter150_in_app_professional_cases.py`
    (+4 tests)
  - `backend/tests/test_iter151_joint_alignment_invite_nudge.py`
    (+1 test)

### 2026-03-07 — Weekly-Digest Opt-Out Toggle on `/mine`
- **Two new JWT-authenticated endpoints** in `joint_alignment_routes.py`:
    - `GET /api/professional/joint-alignment/digest-pref` —
      returns `{opted_in: bool, updated_at: iso|null}`. Absent
      row defaults to `opted_in=True` matching the "Reply STOP
      to opt out" copy on the email.
    - `POST /api/professional/joint-alignment/digest-pref` —
      body `{opted_in: bool}`. Idempotent upsert into a new
      `weekly_case_analytics_prefs` collection.
- **Sweep loop honours opt-out** — `_dispatch_one` now checks
  `_is_opted_in(db, user_id)` before every send and short-circuits
  with `reason="opted_out"` when the flag is False. Default (no
  row) still opts in so the toggle is opt-out, not opt-in.
- **`WeeklyDigestToggle.jsx`** — new component in
  `frontend/src/components/professional/`. Reads the pref on
  mount, renders a green "Weekly digest: On" (Mail icon) or
  neutral "Weekly digest: Off" (MailX icon) pill. One-tap
  toggle with optimistic UI + rollback on failure. Shows a
  friendly toast on both directions and a skeleton placeholder
  while the pref loads so the header layout doesn't jump.
- **`/mine` header** — toggle sits in the top-right actions row
  beside "Refresh" and "New case", so a mediator seeing the
  Monday email in their inbox and thinking "yeah no thanks" can
  disable it before their coffee cools.
- **Coverage grew iter150 from 18 → 21** (default GET,
  opt-out+opt-back-in round trip, auth-required) and iter152
  from 8 → 10 (sweep skips opted-out, sweep sends when
  explicitly opted-in). Full 31 tests green together across
  iter150 + iter152; 46-test cross-file suite still clean.
- **Live E2E verified**: initial pill = "On", toggle → "Off",
  reload → still "Off" (persisted), toggle again → "On" with
  toast confirmation.
- **Files touched**:
  - `backend/joint_alignment_routes.py` (adds
    `GET/POST /digest-pref` endpoints + `DigestPrefRequest`
    model)
  - `backend/weekly_case_analytics_email.py` (adds
    `_PREFS_COLLECTION` constant + `_is_opted_in` helper +
    the short-circuit in `_dispatch_one`)
  - `frontend/src/components/professional/WeeklyDigestToggle.jsx`
    (new)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx`
    (mounts the toggle in the header)
  - `backend/tests/test_iter150_in_app_professional_cases.py`
    (+3 tests)
  - `backend/tests/test_iter152_weekly_case_analytics.py`
    (+2 tests)

### 2026-03-07 — Weekly Analytics Email (Monday snapshot for mediators)
- **`weekly_case_analytics_email` sweep module** — new
  `backend/weekly_case_analytics_email.py` mirroring the existing
  `weekly_compliance_reminder` pattern. Rules:
    - Runs once daily; sends only inside the Monday 09-11 UTC
      window (configurable via `WEEKLY_CASE_ANALYTICS_START_HOUR_UTC` /
      `WEEKLY_CASE_ANALYTICS_END_HOUR_UTC`).
    - Candidate set: distinct `professional_created_by` ids over
      `origin=in_app_professional` cases — sibling-site cases
      never trigger this digest.
    - Per-week dedupe row keyed on `(user_id, week_start_ISO)` so
      a mediator gets exactly one snapshot per week even if the
      loop re-runs.
    - Skips demo-looking emails (`@demo.local`, `@guest.local`).
    - Falls back to the professional block on the mediator's
      first minted case when their `users` doc is missing.
    - Env-gated on `WEEKLY_CASE_ANALYTICS_ENABLED=1` — idle no-op
      when unset. Registered from `server.py`.
- **`_compute_analytics(cases, week_ago)`** — self-contained
  aggregator that mirrors the `/api/professional/joint-alignment/analytics`
  endpoint's math plus two extra fields: `new_this_week` and
  `completed_this_week` so the email can lead with a "This week"
  delta strip. No routes-layer imports keeps the sweep loop
  cleanly separable.
- **`email_service.send_weekly_case_analytics_email`** — new
  branded HTML email with:
    - Purple "This week: N new · M completed" call-out.
    - 4-tile HTML `<table>` grid mirroring the on-screen
      `<CaseAnalyticsCard />` (Total cases, Acceptance rate,
      Time to first accept, Time to both complete).
    - Top-lane hint row.
    - Reply-STOP opt-out footer and PHI-safe reminder that only
      aggregate rollups are shared — no verbatim parent answers.
    - Deep-link CTA to `/professional/joint-alignment/mine`.
- **Coverage**: `tests/test_iter152_weekly_case_analytics.py` — 8
  tests (Monday window guard, `_week_start` Monday rollback, happy
  dry-run + dedupe row, dedupe blocks second send in the same
  week, skips zero-cases professionals, skips outside-window
  timestamps, skips demo emails, `new_this_week` delta
  correctness). Full 46 tests green (iter139 + iter150 + iter151
  + iter152 combined).
- **Dry-run against live DB**: 48 candidates → 48 sent with
  stats-shape validated.
- **Files touched**:
  - `backend/weekly_case_analytics_email.py` (new)
  - `backend/email_service.py` (adds
    `send_weekly_case_analytics_email` + `_fmt_hours` / `_fmt_lane`
    helpers)
  - `backend/server.py` (registers the new sweep loop)
  - `backend/tests/test_iter152_weekly_case_analytics.py` (new, 8 tests)

### 2026-03-07 — Case Analytics Card on `/mine`
- **`GET /api/professional/joint-alignment/analytics`** — new
  JWT-authenticated aggregate endpoint. Returns:
  `total_cases`, `active_cases`, `cancelled_cases`,
  `completed_cases`, `acceptance_rate` (%),
  `avg_hours_to_first_accept`, `avg_hours_to_both_complete`,
  `assessment_type_breakdown` (dict), `most_common_assessment_type`.
    - Data-minimisation: rollups only, never per-case or
      per-parent detail — safe for a paralegal to view.
    - Scoping is strict — the query filters by
      `professional_created_by == current_user.id` OR
      `professional.id == current_user.id AND origin=in_app_professional`
      so cross-professional bleed is impossible.
    - New `_as_aware_utc()` helper in
      `joint_alignment_routes.py` normalises Mongo-returned
      (tz-naive) and ISO-string datetimes before delta arithmetic
      so time-to-first-accept / time-to-both-complete never
      TypeErrors on mixed timezone inputs.
- **`CaseAnalyticsCard.jsx`** — new component in
  `frontend/src/components/professional/`. Renders as the top
  card on `/professional/joint-alignment/mine`:
    - `INTAKE FUNNEL · AT A GLANCE` eyebrow + top-lane pill
      showing the most-common assessment lane.
    - 4-tile stat grid (BarChart / TrendingUp / Timer /
      CheckCircle2 icons) — Total cases, Acceptance rate, Time
      to first accept, Time to both complete.
    - Assessment-lane breakdown bar chart (only shown when
      ≥ 2 lanes exist) — each lane gets a purple horizontal bar
      scaled against the top lane so uneven distributions are
      instantly readable.
    - Loading + error + empty-state paths (zero cases → card
      renders nothing so first-visit mediators aren't confused
      by a wall of dashes).
- **Coverage**: iter150 grew from 13 → 18 tests. Added:
  zero-shape returns None-valued rates, multi-case aggregation
  correctness, cross-professional scoping guard, auth-required
  401, and a full time-delta test that Mongo-updates a case's
  parents' `accepted_at` + `assessment_completed_at` and asserts
  the aggregator returns positive average hours. Full 24
  (iter150 + iter151) tests green.
- **Files touched**:
  - `backend/joint_alignment_routes.py` (adds
    `_as_aware_utc` helper + analytics endpoint)
  - `frontend/src/components/professional/CaseAnalyticsCard.jsx`
    (new)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx`
    (mounts the card above the search + filter block)
  - `backend/tests/test_iter150_in_app_professional_cases.py`
    (+5 tests)

### 2026-03-07 — Case Reminder Emails + Filed-PDF Watermark
- **Case reminder emails (5-day nudge)** — a new hourly sweep loop
  `joint_alignment_invite_nudge` in
  `backend/joint_alignment_invite_nudge.py` matching the existing
  `compare_invite_nudge` pattern. Rules:
    - Only touches cases with `origin=in_app_professional` (server-
      to-server cases from the sibling site handle their own
      reminders on that side — no double-nudging).
    - Fires for parents whose `accepted_at` is null AND the case
      was minted ≥ 5 days ago AND the invitation token hasn't
      expired yet.
    - Dedupe row per (case_id, parent_email) with a 60-day TTL
      (functionally "one reminder ever" — case TTL is 60 days).
    - Skips demo-looking emails (`@demo.local`, `@guest.local`).
    - New `email_service.send_joint_alignment_invitation_reminder`
      uses a softer tone than the initial invite ("gentle reminder",
      "no need to reply, click when you're ready").
    - Gated on `JOINT_ALIGN_INVITE_NUDGE_ENABLED=1` — idle no-op
      when unset. Registered from `server.py` alongside the
      existing four sweep loops.
    - Coverage: `tests/test_iter151_joint_alignment_invite_nudge.py`
      — 6 tests (dispatches at 5+ days, skips fresh, skips
      accepted, skips expired tokens, only in-app cases, dedupe
      prevents repeats). All green.
- **Filed-PDF watermark** — new `apply_professional_watermark(pdf,
  firm_name)` helper in `court_report_disclaimer.py` walks every
  rendered page via `pages_count` + `pdf.page` navigation and
  stamps a muted grey bottom-right footer:
  "Downloaded by \<firm\> on \<UTC timestamp\> · SA CoParents" —
  provenance, not a court seal.
- **Case-status PDF download from `/mine` console** — new endpoint
  `GET /api/professional/joint-alignment/cases/{id}/status-report.pdf?firm=X`
  (JWT + owner-only). New `case_status_pdf.py` builder produces a
  small PDF containing: title block, case meta (assessment lane,
  status, dates, professional-of-record), per-parent status
  labels (no verbatim parent answers surfaced), the court-report
  disclaimer, and the watermark on every page.
  - Watermark falls back to the caller's account name if `firm`
    query param omitted — never leaves the PDF unstamped.
  - Filename: `SA-XXXXXX-status-report.pdf`.
- **`/mine` UI additions** — every non-cancelled case row now has a
  purple "Download PDF" button beside the red "Revoke" button.
  Clicking opens a modal (`pj-download-modal`) with a firm-name
  input (saved to LS under `sacoparents.pj.mine.firm_name.v1` so
  a mediator only types it once). Confirm downloads the
  watermarked PDF via a blob-URL + toast.
- **`/for-professionals` hero** gained a secondary outlined CTA
  "Manage my cases" (`for-pros-manage-cases-cta`) linking to the
  new console alongside the primary "Create a Joint Alignment
  case".
- **Coverage**: iter150 grew from 9 → 13 tests (added
  status-report-watermarked-and-valid, fallback-to-account-name,
  owner-only-404, auth-required). All 19 (iter150 + iter151)
  tests green together.
- **Files touched**:
  - `backend/joint_alignment_invite_nudge.py` (new)
  - `backend/case_status_pdf.py` (new)
  - `backend/court_report_disclaimer.py` (adds
    `apply_professional_watermark`)
  - `backend/email_service.py` (adds
    `send_joint_alignment_invitation_reminder`)
  - `backend/joint_alignment_routes.py` (adds status-report
    download endpoint)
  - `backend/server.py` (registers the new sweep loop)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx`
    (Download PDF button + firm-name modal + LS persistence)
  - `frontend/src/pages/ForProfessionals.jsx` (Manage-my-cases CTA)
  - `backend/tests/test_iter150_in_app_professional_cases.py` (+4 tests)
  - `backend/tests/test_iter151_joint_alignment_invite_nudge.py` (new, 6 tests)

### 2026-03-07 — Court-Facing Disclaimer Sweep + Auto-Invite Emails + Cases-I-Created Full Page
- **Court-report disclaimer sweep** — every remaining court-facing
  artefact now carries the six-caveat "not a custody evaluation"
  disclaimer, matching the existing coverage on `nd_risk_pdf` and
  `safety_court_report_pdf`.
    - Frontend: `<CourtReportDisclaimer />` added to
      `SpecialNeedsV2MedicalDeepDiveReport`,
      `SpecialNeedsV2EducationalDeepDiveReport`,
      `SpecialNeedsV2PsychologicalDeepDiveReport` (right after
      `<AssessmentResultHandoff />`, above the numbered sections).
      Each is wired with `authorName={cover.parent_name}` and
      `bothParents={false}`. `SafetyAssessment` already carried
      the disclaimer via `SafetyAssessmentResultsCard` (verified —
      no duplicate insertion).
    - Backend PDFs: `draw_court_report_disclaimer(...)` now runs on
      `joint_professional_report_pdf` (its own page right after the
      cover, `both_parents=True`), `joint_agreement_pdf` (same),
      `snc2_report_pdf` (own page after cover, single-parent),
      and `pathway_report_pdf` (below the primary-pathway card).
      All four smoke-tested — every renderer returns a valid
      `%PDF-` byte stream.
- **Auto-invite emails from the in-app professional flow** — when
  a mediator mints a case at `/professional/joint-alignment/new`,
  both parents now receive the invitation email automatically via
  Resend so the copy-paste dance is no longer required.
    - New `email_service.send_joint_alignment_invitation(...)` with
      professional-driven framing (case ID, professional name,
      assessment lane, 7-day expiry, "sign in with matching email"
      hint).
    - Wired into `POST /api/professional/joint-alignment/cases`
      as best-effort — a Resend outage never fails the mint.
    - Response gained an optional `email_deliveries` list, one row
      per parent with `{email, delivered: bool}` so the frontend
      renders a green ✓ / amber "copy manually" hint per parent.
    - Frontend result panel: per-parent delivery indicator with
      `data-testid="pj-result-parent-{i}-delivery"` +
      `data-delivered` attribute. Headline copy adapts to
      all-sent / partial / none-sent states.
- **Cases-I-Created full-page management console** at
  `/professional/joint-alignment/mine` (protected):
    - New JWT-authenticated endpoint
      `POST /api/professional/joint-alignment/cases/{id}/cancel` —
      owner-only revoke that expires unclaimed invitation tokens,
      records the revoker's `user_id`, and returns 404 on
      cross-professional attempts (ownership guard).
    - Full-page UI: search bar (case_id / email / ref number),
      5 filter chips with live counts (all / pending / in_progress /
      both_complete / cancelled), per-row invitation-URL copy,
      confirm-gated revoke that flips the status pill to red
      "cancelled" and hides the revoke button. Empty state and
      loading/error states covered.
    - `/professional/joint-alignment/new` gains a "See all my
      cases →" link both in the sidebar-list header and in the
      post-mint success actions.
    - Live E2E-tested: mint → email-delivery indicator renders
      (delivered=false in preview since Resend key absent) →
      `/mine` lists all 3 cases → search filters to 1 → revoke
      → status flips to `cancelled` → revoke button removed →
      toast "Case SA-XXXXXX revoked".
- **Coverage grew from 6 → 9 iter150 pytest cases** — added:
  professional-can-cancel-own-case (with idempotent-404 second
  cancel), professional-cannot-cancel-anothers (ownership
  guard 404), and response-carries-email-delivery-status
  (shape lock). All 20 (iter139 + iter150) still green.

### 2026-03-07 — In-App Joint Alignment case creation + Situation-Pick Freshness Fade
- **In-App Joint Alignment case creation** — mediators/attorneys/paralegals
  can now spin up a two-parent case from inside the parent app
  without bouncing to `sacoparentsalign.com`.
    - Backend (in `joint_alignment_routes.py`): two new
      JWT-authenticated endpoints on `/api`:
      - `POST /professional/joint-alignment/cases` — same shape as
        the server-to-server variant but the caller becomes the
        professional of record (or overrides via
        `professional_name` / `professional_email`). Mints
        `SA-XXXXXX` case_id, generates two invitation URLs, records
        `origin=in_app_professional` + `professional_created_by=<user_id>`.
      - `GET /professional/joint-alignment/cases-i-created` —
        lists the caller's minted cases. Copy-paste UX: each row
        surfaces the raw `invitation_url` per parent (until expiry)
        so a mediator can re-send the link at any time.
    - Frontend: new page `/professional/joint-alignment/new`
      (protected). Purple gradient hero + form (assessment lane +
      two parent email/name inputs + optional firm reference) +
      privacy assurance strip. On success flips to a green result
      panel showing `SA-XXXXXX` + two copyable invitation URLs
      + "Create another case" CTA. Sidebar lists the caller's
      cases-i-created for one-tap resend.
    - `/for-professionals` marketing page hero now leads with a
      solid-purple **"Create a Joint Alignment case"** CTA
      (`data-testid="for-pros-create-case-cta"`) linking to the
      new page. Contact + Samples remain as outlined secondaries.
    - Coverage: `tests/test_iter150_in_app_professional_cases.py`
      — 6 tests (happy path, case-doc records caller as
      professional + origin, unauthenticated 401, wrong parent
      count 400, duplicate emails 400, unknown assessment_type 400,
      cases-i-created does not leak other professionals' cases).
      All 20 (iter139 + iter150) tests green together.
- **Situation-Pick Freshness Fade** — the pulsing "Recommended"
  halo on the Four-Circle Front Door now auto-decays after 14
  days so a parent whose family situation has shifted since their
  last visit isn't nagged by a stale recommendation.
    - New companion LS key `sacoparents_situation_choice_savedAt_v1`
      stamped every time `saveSituation(key)` fires.
    - New `isSituationFresh(savedAt)` helper in `Dashboard.jsx`
      checks the timestamp is < 14 days old.
    - Only the pulsing halo uses `freshSituationChoice`; the raw
      `situationChoice` continues to power the prep-modules
      recommendation chip + the "you chose X — change my answer"
      pill inside "Explore All Tools" (those still make sense at
      the parent's request).
    - Backfill-safe: existing pre-timestamp LS entries return
      `savedAt=null` → treated as stale → no pulse until the parent
      re-saves.
    - Smoke-tested live: 15-day-old stale entry shows no badge; 2-day-
      old fresh entry shows the pulsing badge.

### 2026-03-07 — First-Visit Callout on 4 Circles (pulsing badge for returning parents)
- **`FourCircleFrontDoor.jsx`** now accepts an optional `situationChoice`
  prop and maps it via a new `SITUATION_TO_CIRCLE` table
  (cooperate/difficult/mediation → co-parenting · high-conflict/safety
  → safety · special-needs → child-needs) so returning parents land
  on a pathway highlighted specifically for what they told us last
  visit.
- **Pulsing "Recommended for you" badge** — new `.recommended-pulse`
  CSS class in `index.css` drives a soft brand-purple halo
  (`recommendedPulse` keyframes, 1.6s loop). The badge only pulses
  when the recommendation came from the *situation pick* (a passive
  signal that needs eye-catching); explicit **"Help me choose"** quiz
  answers still show a static badge (they already came with an
  in-your-face result card so a pulse would be redundant).
- **Precedence rule**: helper-quiz answer wins over the
  situation-pick when both are set. When only the situation-pick
  is present, the matching circle gets the pulsing badge. When
  neither is set, no badge appears (fresh-visit baseline).
- **`Dashboard.jsx`** now passes `situationChoice={situationChoice}`
  (already lifted to state via `readSituation()`) into the
  `FourCircleFrontDoor`. No additional writes — the existing
  `SituationPickerHero` inside "Explore All Tools" continues to
  seed the LS key.
- **Smoke-tested live** across all three states (no signal, situation
  only pulsing, helper-quiz-wins static) — badge testids include
  `data-pulsing="true"` so the state is legible from automation.
- **Files touched**:
  - `frontend/src/components/dashboard/FourCircleFrontDoor.jsx`
  - `frontend/src/pages/Dashboard.jsx`
  - `frontend/src/index.css` (adds `@keyframes recommendedPulse` + `.recommended-pulse` class)

### 2026-03-07 — Dashboard "Overload" Restructure (Wave 1a) + `/for-professionals`
- **P0 Orientation flow no longer blocks the dashboard** — the
  auto-redirect at `Dashboard.jsx` mount that yanked first-time
  visitors onto `/orientation` (hiding the 4-circle Front Door) has
  been removed. A dismissible pill banner
  (`data-testid="dashboard-tour-banner"`) now appears at the top of
  the dashboard for first-timers with a purple "Take the tour" CTA
  linking to `/orientation` and a "Dismiss" button that stamps the
  `sacoparents.orientation_seen.v1` LS flag.
- **`/orientation` Skip button re-styled as a prominent CTA pill** —
  was a 12px grey text link in the corner; now a solid purple
  filled pill with a right arrow (`text-sm font-semibold text-white
  bg-[#3D1A78]`), so parents who reached the walkthrough by accident
  can bail to the dashboard in one clear tap.
- **Dashboard restructured — legacy secondary tools collapsed** —
  the "SituationPickerHero" (legacy Step 1) and the full
  four-category "Preparation modules" jump-menu (previously ~150
  lines above the fold) are now wrapped inside a new
  `dashboard-explore-all-tools` `<details>` collapsible so the 4
  primary pathways stay the uncontested first surface. Everything
  is one tap away — nothing removed.
- **`/for-professionals` public landing page shipped** — new
  `pages/ForProfessionals.jsx` at `/for-professionals` (no auth).
  Hero + 4-highlight strip + 7 collapsible FAQs answering the exact
  mediator/attorney questions from the founder's spec (admissibility,
  neutrality guardrails, DV safety, co-parent privacy, data policy,
  workflow fit, and sample-report access). Deep-links to `/samples`
  and mailto Matt Sossi. Closing dark CTA panel. Registered in
  `App.js`. Landing footer gained `footer-for-professionals-link`
  and `footer-samples-link` so mediators can find it from the
  public front door.
- **Testing**: iter54 frontend Playwright report — all 7
  review-request features PASS at 100% (`/app/test_reports/iteration_54.json`).
  Verified: first-visit lands on dashboard, tour banner dismissable
  and persisted, 4 front-door tiles above the fold, prep-modules
  hidden behind Explore-All-Tools collapsible, Orientation skip
  navigates + stamps LS, /for-professionals renders publicly with 7
  FAQs all expanding, Landing footer surfaces both new links.
- **Still pending from Wave 1a-3**: bring the joint-report process
  inside the main app, court-report disclaimer applied everywhere.

### 2026-03-06 — Code-review remediation round 3 (scoped)
- **`build_cost_ledger_pdf()` refactor**: 108 → 46 lines by extracting
  three focused helpers into `activities_costs_pdf.py`:
  `_resolve_split_ratio()` (mode → ratio math),
  `_draw_meta_strip()` (parent-name banner), and
  `_draw_ledger_pair()` (caller + co-parent ledger render). Cyclomatic
  complexity dropped meaningfully. All 5 iter149 PDF tests still green.
- **`CostSplitterPanel.jsx` split**: 512 → 401 lines by extracting
  three subcomponents into a new `components/cost/` directory
  (matches the `components/safety/`, `components/joint/`,
  `components/activities/` split pattern already in the codebase):
    - `CostSplitterTotals.jsx` — the three-box You / Co-parent / Combined card
    - `CostSplitterCategoryBreakdown.jsx` — the "By category" bars + `CategoryBar` primitive
    - `CostSplitterEntriesList.jsx` — the expandable my-entries list + delete-per-row
  Fixed a duplicate `window.confirm` that would have fired twice
  after the extraction. Live smoke: all 5 panel elements
  (totals · categories · download · split · toggle) render
  identically on `/activities/alignment`.
- **Explicitly NOT touched** (documented regression landmines per
  prior handoffs — every attempt to fix these has broken the app
  30+ times):
    - Circular imports (function-scoped on purpose to dodge FastAPI
      startup deadlocks)
    - 231 hook-dep warnings (mass-adding causes infinite fetch loops
      on this codebase)
    - MD5 in `intervention_compliance_routes.py`
      (`usedforsecurity=False`; non-security dedupe hash)
    - 49 localStorage instances (all non-sensitive UX state)
    - "Hardcoded secrets" in test files (`TestPass123!` literals are
      pytest fixtures, not real secrets)
    - `ai_service.py` + `admin_nd_case_pdf.py` complexity
      (P2 backlog per handoff)
    - "Undefined variables (56)" — SAST tool false positives on
      `TYPE_CHECKING`-guarded imports and conditional branches
    - `AuthContext.useMemo` + `ReportShareControls.useCallback` deps
      — same hook-deps landmine
- **Wave 1-3 restructure work started**: two shared components in
  place (`components/JourneyStepper.jsx` and
  `components/CourtReportDisclaimer.jsx`). Diagnostic-sounding
  labels softened everywhere they surface to users:
  "Trauma-Informed Safety and Functioning Lens" →
  **"Family Safety and Functioning Reflection"** and
  "Neurodivergent Risk Assessment" →
  **"Neurodivergent Child Support Planning Tool"** (Dashboard.jsx,
  SafetyAssessment.jsx, SafetyAssessmentResultsCard.jsx,
  VerifyCourtReport.jsx, HipaaNotice.jsx). The "ongoing high
  conflict" tile on Landing.jsx no longer says "start with the
  safety screen" — now says "we'll run a short private safety
  check first" so high-conflict ≠ family-violence.
- **Still pending from Wave 1-3** (paused for these code-review
  fixes; will resume): Dashboard collapse into Four-Circle-only
  primary decision, `<ExploreAllTools>` collapsible for the rest of
  the surface, `/for-professionals` public page, court-report
  disclaimer applied to every court-facing PDF/screen.

### 2026-03-06 — Code-review remediation round 2 (privacy + consent)
- **HIGH — Co-parent private notes leak (fixed)**: the compare
  endpoints on all three alignment surfaces (Communication,
  Parenting Schedule, Activities) were shipping the co-parent's
  private free-text `notes` and raw `answers` in the payload via
  `**coparent_shape` — the UI didn't render them but they were
  visible in DevTools/Network, contradicting the on-screen
  guarantee that "individual notes stay private". Introduced a new
  `_shape_public()` helper in each of `communication_alignment_routes.py`,
  `parenting_schedule_alignment_routes.py`, and
  `activities_alignment_routes.py` that drops both fields before
  the co-parent branch is returned. Caller's own branch is
  unchanged.
- **MEDIUM — Cost-splitter email-enumeration (fixed)**: the
  `/activities-costs/compare` and `/compare.pdf` endpoints
  previously served any registered email's itemized ledger to any
  authenticated caller. Added a 403 consent gate: the caller must
  have logged at least one of their own entries before another
  account's rows are returned. Mirrors the existing alignment
  pattern that gates `/compare` on the caller's own reflection.
- **LOW — Dead imports removed** (`useMemo` from
  `ParentingScheduleReflection.jsx` and `ActivitiesReflection.jsx`).
- **LOW — Comment aligned with cap** in
  `activities_costs_routes.py` (`≤ $100,000 sanity cap`).
- **Regression tests added**:
    - iter138: co-parent branch of `/communication-alignment/compare`
      asserted free of `notes` and `answers`.
    - iter146: same guard for `/parenting-schedule-alignment/compare`.
    - iter147: same guard for `/activities-alignment/compare`.
    - iter148: new `test_compare_without_own_entries_is_forbidden`
      confirms both `/compare` and `/compare.pdf` return 403 when the
      caller has nothing logged; the existing 404 tests updated to
      log an entry first so they still exercise the 404 branch.
- Full 34/34 across iter138 + iter146 + iter147 + iter148 + iter149
  green. Frontend compiled clean.

### 2026-03-06 — Cost Splitter PDF Export
- **`GET /api/activities-costs/compare.pdf`** — new endpoint that
  returns a single-page A4 PDF combining the caller's cost ledger,
  the co-parent's ledger (when paired), the per-category breakdown,
  and a neutral suggested split (50/50 / income-weighted /
  custom-%). All query params (`coparent_email`, `mode`,
  `self_income`, `coparent_income`, `custom_pct`) are optional; the
  PDF renders solo (just the caller's ledger, no split) when no
  co-parent is passed. Reuses the existing `_load_bundle()` +
  `_pair_categories()` helpers so the shape matches
  `/compare` exactly. Notes on the co-parent's rows are redacted
  upstream — the PDF renderer double-guards by only showing notes
  on `show_notes=True` rows (caller's own).
- **`activities_costs_pdf.py`** (new) — the renderer. Layout:
  header strip + org contact block + parent-line meta + three-box
  totals card + suggested-split card (mode-specific line +
  amber/green/neutral balance headline + share-math subline) +
  per-category two-column table + caller's ledger rows (10 max) +
  co-parent's ledger rows (10 max, notes redacted). Neutrality
  footer: "Prepared for mediator reference — Suggested split is
  not an order or court decision".
- **Frontend**: `CostSplitterPanel.jsx` gains a compact green
  outlined "PDF" pill in the top-right of the panel header,
  visible whenever any expense is logged. Clicking fires a
  `fetch(..., {credentials: "include"})` → blob → programmatic
  `<a download>` (mirrors the JointAgreement PDF pattern; JWT
  auth is httpOnly-cookie based). Reads the caller's current
  split preferences from the shared `sacoparents.costSplitter.split`
  localStorage key via the new exported `loadSplitPrefs()` helper —
  no state lifting, just a lightweight shared read.
- **Coverage**: `tests/test_iter149_activities_costs_pdf.py` — 5
  tests (auth required, solo-mode PDF, paired-mode across all three
  split modes, unknown-coparent 404, content-disposition inline).
  Full 33/33 across iter138 + iter146 + iter147 + iter148 + iter149
  green. Live smoke: PDF endpoint returns 990KB valid PDF-1.3
  bytes; the download pill mounts on the panel once the parent has
  logged an entry.

### 2026-03-06 — Code-review remediation (scoped)
- **`activities_costs_routes.compare()` refactor**: extracted the
  inner `_bundle` closure into a module-level `_load_bundle()`
  helper and pulled the per-category merge logic into
  `_pair_categories()`. The endpoint body itself dropped from 70 →
  27 lines with no behaviour change. All 7 iter148 tests still green.
- **`ActivitiesAlignment.jsx` split**: 511 → 345 lines by extracting
  three sub-components into a new `components/activities/` directory
  (mirrors the `components/safety/` + `components/joint/` split
  pattern already in the codebase):
    - `ActivitiesDimensionPrimitives.jsx` — `ScoreBar` + `DimensionRow`
    - `ActivitiesSummaryCard.jsx` — the "Neutral summary" card
    - `ActivitiesShareCodeCard.jsx` — the mint / shareCode / shareError render
- **Explicitly NOT touched** (documented as regression landmines in
  prior handoffs — every attempt to "fix" these breaks the app):
    - Circular imports (function-scoped on purpose to dodge FastAPI
      startup deadlocks)
    - 230 React hook-dep warnings (mass-adding causes infinite fetch
      loops on this codebase)
    - MD5 in `intervention_compliance_routes.py` (already flagged
      `usedforsecurity=False`; not a security use)
    - 28 localStorage instances (all non-sensitive UX state:
      dismissal flags, orientation, choice preferences)
    - "Hardcoded secrets in test files" (test-only literals like
      `TestPass123!` used to register throwaway users — fixtures,
      not secrets)
    - `ai_service.generate_nd_report` / `admin_nd_case_pdf` complexity
      (parked on P2 backlog per handoff)

### 2026-03-06 — Samples Search + Split Suggestions
- **Samples Search** (`pages/Samples.jsx`) — a plain search box above
  the category grid filters cards live by title, blurb, filename, and
  parent-category label (case-insensitive substring). When a query is
  active the jumplink strip is replaced with a compact
  "Showing N of 27 samples matching …" caption; categories with zero
  matches are hidden entirely so the visitor never scrolls empty
  headers. When the query has no matches a friendly empty state
  offers example broader terms + a one-click Clear button. Verified
  live: 27 → 4 for "medical", 27 → 0 with the empty state for
  nonsense.
- **Split Suggestions** (`components/SplitSuggestion.jsx`, mounted
  inside `CostSplitterPanel.jsx`) — a neutral, deterministic
  suggested split rendered under the totals card whenever any
  parent has logged an expense. Three modes:
    1. **50/50 even** — each parent covers 50% of the combined total.
    2. **Income-weighted** — parents type each other's monthly gross
       income → share = income / combined.
    3. **Custom %** — a range slider from 0-100% for the parent's
       share (co-parent auto-inverts).
  Output: a single "Balance" card that flips colour by state —
  amber when the caller still owes money, green when the co-parent
  owes them, purple when they're roughly square. When the caller
  has no co-parent linked yet, the balance line degrades to a "Link
  your co-parent to see a suggested balance" hint instead of a
  misleading zero.
  Guardrails: caption reads *"This is a suggestion, not an order —
  take it to your mediator."* All income + custom-% values live in
  `localStorage` under the `sacoparents.costSplitter.split` key —
  never sent to the server, never shown to the co-parent. A
  "Clear inputs" button drops them at any time.
- Frontend compiled clean (only pre-existing intentional warnings).
  Live smoke-tested: `/samples` filters correctly on "medical",
  "psychological", and unknown terms; `/activities/alignment` mounts
  the split-suggestion panel with all three modes + a balance line
  once the parent has logged an expense.

### 2026-03-06 — Sample Library + AI-Drafted Pill + Cost Splitter
- **Sample Library `/samples`** (`pages/Samples.jsx`) — public
  browsable index of all 27 sample PDFs living in
  `frontend/public/downloads/`. Grouped into six categories (Joint
  Alignment Reports, Child Needs Deep-Dives, SNC, Co-Parenting +
  Foundation, Family Violence & Safety, For Professionals) with a
  jumplink strip so a visitor lands on the section they need without
  scrolling. Each card exposes an "Open" + "Download" button. Public
  route (no auth) so mediators and attorneys can evaluate the
  artefact library before signing up. Linked from
  `JointReportsPicker.jsx`.
- **AI-Drafted Pill** (`components/AIDraftedPill.jsx`) — reusable
  `<AIDraftedPill model="claude|gpt" tone="…" />` badge that marks a
  summary block as LLM-authored so mediators immediately see what
  came from the model versus the parents' verbatim answers. Applied
  next to the "Neutral summary" eyebrow on all three alignment
  pages:
    - `CommunicationAlignment.jsx` (tone="blue")
    - `ParentingScheduleAlignment.jsx` (tone="amber")
    - `ActivitiesAlignment.jsx` (tone="green")
  Each page now stores `summaryModel` in state so the label reflects
  Claude vs. GPT 5.6 Terra when the parent regenerates.
- **Cost Splitter** — a live activity-cost ledger that pairs by
  co-parent email.
  - Backend: `activities_costs_routes.py` (mounted at
    `/api/activities-costs`, prefix-scoped). Endpoints:
    `GET /categories` (public chip list),
    `GET /mine` (list + total),
    `POST ""` (create),
    `DELETE /{cost_id}` (delete-own-only, 404 on foreign id),
    `GET /compare?coparent_email=…` (you-vs-coparent totals +
    per-category pair breakdown + row-level entries). Notes are
    **always redacted on the co-parent's rows** — the parent's own
    free-text stays private. Storage: `activity_costs` collection.
  - Frontend: `components/CostSplitterPanel.jsx` — mounted on
    `ActivitiesAlignment.jsx`. Renders three totals cards
    (You / Co-parent / Combined), a stacked "By category" strip so
    parents see the balance at a glance, a compact log-entry form
    (activity label, category select, amount, private note, date),
    and an expandable "my entries" list with delete. Auto-refreshes
    after every write. Passes `coparentEmail` from the compare
    payload so totals update live once the pair is linked.
  - Coverage: `tests/test_iter148_activities_costs.py` — 7 tests
    (categories public, create+read+total, unknown-category downgrades
    to 'other', invalid amount 422, delete-own-only, compare totals
    + note redaction, unknown-coparent 404). All green.
- **Full 28-test suite** across iter138 + iter146 + iter147 + iter148
  green. Frontend compiled clean (only pre-existing intentional
  warnings). Live smoke-tested: `/samples` renders 27 cards across
  6 categories, `/activities/alignment` mounts the cost splitter
  once the parent's reflection is saved.

### 2026-03-06 — Parenting Schedule + Activities Joint Alignment Reports (fka "Coming soon")
- **Two new Joint Alignment Reports** matching the Communication
  Alignment pattern shipped in iter138. Both surface on the
  `/joint-reports` picker as fully-interactive tiles (no longer
  "Coming soon").
- **Parenting Schedule** — 12-question reflection scored across three
  dimensions (Predictability, Flexibility, Transitions). Neutral
  first-person stems only.
  - Backend: `parenting_schedule_questions.py`,
    `parenting_schedule_alignment_routes.py`,
    `ai_summary_parenting_schedule.py`.
  - Endpoints: `GET /api/parenting-schedule-reflection/schema`,
    `PUT /api/parenting-schedule-reflection`,
    `GET /api/parenting-schedule-reflection/mine`,
    `POST /api/parenting-schedule-alignment/compare`,
    `POST /api/parenting-schedule-alignment/compare/summary`.
  - Storage: `parenting_schedule_reflections` collection.
  - Frontend: `pages/ParentingScheduleReflection.jsx` at
    `/schedule/reflection` (one-question-per-screen, auto-advance,
    debounced auto-save 800ms) and `pages/ParentingScheduleAlignment.jsx`
    at `/schedule/alignment` (solo → pair-by-email → waiting/ready
    states → neutral LLM summary + `context="parenting_schedule"`
    share-link mint). Amber palette so it visually reads distinct
    from Communication (blue) and Activities (green).
- **Activities** — same shape, 12 questions across Awareness,
  Support, Logistics. Scope explicitly limited to kids'
  extracurriculars — never medical / educational / therapeutic
  decisions (those live on their own deep-dive pathways).
  - Backend: `activities_reflection_questions.py`,
    `activities_alignment_routes.py`, `ai_summary_activities.py`.
  - Endpoints: `GET /api/activities-reflection/schema`,
    `PUT /api/activities-reflection`,
    `GET /api/activities-reflection/mine`,
    `POST /api/activities-alignment/compare`,
    `POST /api/activities-alignment/compare/summary`.
  - Storage: `activities_reflections` collection.
  - Frontend: `pages/ActivitiesReflection.jsx` at
    `/activities/reflection` and `pages/ActivitiesAlignment.jsx` at
    `/activities/alignment`. Green palette. `context="activities"`
    on share-link mint.
- **Joint Reports Picker updates**: three tiles (`communication`,
  `schedule`, `activities`) flipped from `comingSoon: true` to
  interactive links via the new `alwaysStandalone: true` flag on
  `TopicCircle` (routes to reflection directly, bypassing the SNC2
  Compare share-id check).
- **Neutrality guardrails** (identical to iter138): both LLM summary
  modules short-circuit to the safety sentence when either parent's
  `intake_choice == "unsafe"`, use Claude Sonnet 4.5 by default with
  GPT-5.6 Terra opt-in, never adjudicate, ~150-220 words,
  parent-attributed language only, never invent specifics.
- **Completion hook**: both save endpoints wire into
  `joint_alignment_routes.mark_assessment_completed` so professional-
  driven Joint Alignment Cases mark the correct parent slot as
  completed when the reflection is finished.
- **Coverage**: `tests/test_iter146_parenting_schedule_alignment.py`
  (7 tests) + `tests/test_iter147_activities_alignment.py` (7 tests).
  Full iter138 + iter146 + iter147 suite: 21/21 green. Frontend
  compiled clean.
- **Verified live**: `/joint-reports` renders all three previously-
  "Coming soon" tiles as interactive `<a>` tags; `/schedule/reflection`,
  `/schedule/alignment`, `/activities/reflection`, and
  `/activities/alignment` all render with the correct hero, dimension
  labels, and pair-by-email panels.

### 2026-03-05 — Unsure Pathway + One Clear Ending + Dashboard refactor start
- **"I'm not sure — help me choose"** mini-quiz on the Four-Circle
  Front Door (`FourCircleFrontDoor.jsx`). Two soft, no-wrong-answer
  questions map the parent to one of the four pathways and stamp a
  bright "Recommended" badge on the matching circle in place. No
  navigation, no interruption — just a subtle nudge so undecided
  parents don't have to guess. Data-testids: `front-door-helper-open`,
  `front-door-helper-panel`, `front-door-helper-q-focus-opt-*`,
  `front-door-{circle}-recommended`.
- **`PathwayEndCTA.jsx`** (new shared component) — a single, prominent
  "what's next" panel that closes every pathway with one clear button
  so parents never see competing terminal actions. Applied to five
  terminal pages:
  - `SpecialNeedsV2Report.jsx` → "Invite the other parent to compare"
  - `SpecialNeedsV2EducationalDeepDiveReport.jsx` → same, edu path
  - `SpecialNeedsV2MedicalDeepDiveReport.jsx` → same, medical path
  - `SpecialNeedsV2PsychologicalDeepDiveReport.jsx` → same, psych path
  - `JointAgreement.jsx` → "Create a shareable link" (opens the
    existing share-link modal)
  - `SafetyAssessment.jsx` results → "Send my case to a mediator"
    (opens the DV-informed warm-handoff dialog)
- **Dashboard.jsx refactor (start)** — extracted the ~90-line "What
  best describes your situation?" hero into
  `components/dashboard/SituationPickerHero.jsx` along with the
  `INLINE_SITUATIONS` constant. Dashboard.jsx dropped from 1571 →
  1484 lines with no behaviour change. Remaining splits (SafetyAssessment,
  JointAgreement, deeper Dashboard sections) tracked as P2 backlog.

### 2026-03-05 — Global "Back to main menu" navigation
- **`BackToDashboardPill.jsx`** (new) — fixed bottom-left floating pill
  ("Main menu") rendered globally via `App.js`. Visible on every
  authenticated screen, hides itself on `/dashboard`, onboarding, auth
  callbacks, and all public routes (landing, login, verify links,
  shared reports, etc.). Uses `AuthContext` so unauthenticated visitors
  never see it. `data-testid="back-to-dashboard-pill"`.
- **`BackToDashboardLink.jsx`** (new) — reusable inline "← Back to main
  menu" link component placed at the top of report / assessment pages
  so users don't need to scroll to the pill.
- Added the inline link to the four deep-dive / alignment report pages
  that were missing an explicit dashboard shortcut at the top:
  - `SpecialNeedsV2EducationalDeepDiveReport.jsx`
  - `SpecialNeedsV2MedicalDeepDiveReport.jsx`
  - `SpecialNeedsV2PsychologicalDeepDiveReport.jsx`
  - `CommunicationAlignment.jsx` + `CommunicationReflection.jsx`
- Smoke-tested with playwright: pill correctly hidden on `/dashboard`
  and `/safety` (public), visible on `/communication/reflection`,
  `/special-needs-v2`, and `/safety-assessment` (a page that does not
  use `AppShell`), so coverage is truly global.

### 2026-03-04 — Family-violence safety gate + single-invite lifetime rule
- **`safety_gate.py`** (new backend module) — `require_ipv_clearance` /
  `ipv_gate_status`. Blocks any parent-to-co-parent invitation unless the
  parent has completed the family-violence safety screen AND scored Level 3
  or 4 (Level 1 = high concern, Level 2 = coercive control both block).
  Wired into:
  - `POST /api/invites/coparent` (email invite) — 403 with structured
    `{code, message, level, hotline, safety_screen_url}` payload.
  - `POST /api/link-codes` (sibling-site join code) — same gate.
  - New `GET /api/invites/coparent/gate` — non-raising probe so the UI
    can render the correct panel on mount without submitting.
  - Professional-directed sends (`/api/professionals/{id}/send-alignment-code`)
    are deliberately NOT gated — a professional is not the safety risk.
- **Single-invite lifetime rule** — a parent may issue AT MOST one
  invitation to their co-parent through this app. Any second POST to a
  different email, or after the prior invite expired, or after the
  co-parent accepted → 400 with a compassionate message. Resends to
  the *same* still-pending recipient are OK (they don't create a new
  invite). Enforced in `invite_routes.py` via `_effective_status`
  (auto-expires pending invites past their `expires_at`).
- **`GET /api/invites/coparent`** enriched with `invite_used`,
  `latest_status`, `can_send_new`, `policy:"one_invite_per_parent_lifetime"`
  so the frontend can decide whether to render the form at all.
- **`InviteCoparentCard.jsx`** rewritten to render four states based on
  gate probe + invite_used: (a) safety-screen-required amber panel with a
  "Take the safety screen" CTA, (b) safety-screen-blocked red panel with
  hotline + DV advocate copy, (c) fresh clear-gate input with a new
  "One invitation per co-parent" lock-icon caption, (d) already-used
  panel showing the single invitation's status.
- **`JointAlignmentPromoCard.jsx`** — same four-state UX mirrored in the
  promo card's waiting variant so parents reaching the invite CTA from
  the Summary / NextSteps pages see the same guardrail messaging.
- **STATUS_META** picks up an "expired / not accepted" pill tone so the
  presumed-rejected state is legible without needing a legend.
- **Coverage**: `tests/test_iter144_safety_gate_on_invites.py` (12 tests)
  + `tests/test_iter145_one_invite_per_parent.py` (7 tests). Full 65
  iter137–iter145 suite still green. Legacy `test_coparent_invite.py`
  and `test_iter137_sibling_integration.py` updated to seed a Level 4
  safety assessment via Mongo so their invite-flow assertions still
  run under the new gate.
- **Verified live** on the preview URL for `parent1@test.com`:
  no-screen state renders the amber "Take the safety screen" panel;
  seeding Level 4 flips to the clean input + one-shot notice; seeding
  Level 2 flips to the red "Direct outreach isn't recommended right
  now" panel with the hotline strip.

### 2026-03-04 — Front Door problem-led language shift complete
- `FourCircleFrontDoor.jsx` — every circle now leads with the *problem*
  the parent is trying to solve, not the tool name:
  - Make a Co-Parenting Agreement (was: Co-Parenting)
  - Communicate More Effectively (was: Communication)
  - Address Safety Concerns (was: Family Violence & Safety)
  - Address My Child's Needs (was: Child Needs)
  Each circle now also renders a `detail` body paragraph (the previous
  session forgot to add the field and every tile rendered blank body
  text). Preserved: staggered entrance animations, hover-lift, and the
  Co-Parenting / Child-Needs inline reveal panels.
- Verified live at `/dashboard` — all four circles + bodies + CTAs
  render as designed.

### 2026-02-21 — Compliance & Joint Artefact hardening
- Full 32-section Privacy Policy + Policy Refresh Banner
- Texas HB 300 endpoints (`hb300_routes.py`), Notice page, breach runbook,
  breach drill executed
- Virtru Hosted Gateway SMTP relay (flag-off pending BAA)
- `PreShareConsentDialog` on all 4 sharing entry points
- "Private by Default" + "No Privilege" banners on all agreement PDFs
- Sample PDF dynamic serving `/api/insights/samples/{filename}` (fixed
  static SPA fallback bug)
- SEC-001: redacted reset/verification tokens from failure logs

### 2026-02-22 — Scoped safe-only code-review refactor
- Extracted shared `bandPillClass` / `bandBarClass` helpers into
  `/app/frontend/src/lib/scoreBandStyles.js`; replaced 4 nested-ternary
  blocks across `SpecialNeedsV2PsychologicalDeepDiveReport.jsx` and
  `SpecialNeedsV2EducationalDeepDiveReport.jsx`.
- Replaced dynamic `__import__("os")` in `safety_assessment_routes.py`
  with a proper module-level `import os`.
- Refactored `_coach_context_block` in `ai_service.py` (was
  cyclomatic 26, depth 6) into three small helpers:
  `_extract_goal_labels`, `_extract_priority_topics`, and a linear
  `_coach_context_block`. Behaviour parity verified with unit checks.
- Deliberately deferred (per user + prior handoff): mass hook-deps,
  circular-import "fixes", MD5 swap, localStorage swap — all documented
  as regressions in previous sessions.

### 2026-02-22 — Public shareable link for the Joint Agreement Draft
- New backend endpoints in `joint_agreement_routes.py`:
  - `POST /api/joint-agreement/{share_id}/share-link` — mints JWT
    (revocable + time-limited, defaults 7 days, 1/7/14/30 choices).
  - `GET /api/joint-agreement/shared/{token}` — public JSON view.
  - `GET /api/joint-agreement/shared/{token}/pdf` — public PDF.
  Consent-gated at mint; every read records a PHI-access log entry
  against the sending parent (`external_read_via_share_link` /
  `external_download_via_share_link`).
- New frontend page `pages/JointAgreementShared.jsx` at
  `/joint-agreement/shared/:token` — no login, provenance banner
  ("Shared by <parent>"), full side-by-side content, PDF button.
- Extracted `Bucket` + `Section` render into
  `components/joint/JointAgreementSections.jsx` so authenticated and
  public views share layout without duplication.
- "Get shareable link" button + dialog added to `JointAgreement.jsx`
  next to "Email to professional". Uses `requestPreShareConsent()`
  gate, offers expire-days selector, copy button, and revoke.
- Coverage: `tests/test_iter123_joint_agreement_share_link.py` — 4
  tests cover mint → view → PDF → revoke, wrong-doc-type rejection,
  and invalid-token rejection. All pass.

### 2026-02-22 — P1 shipments: Email + Link for Joint Report + PDF Parent View
- `POST /api/joint-professional-report/{share_id}/email` now mints a
  30-day preview share token, records it under the sending parent
  with an `Emailed to <recipient>` label, and passes an absolute
  `/api/joint-professional-report/preview/{token}` URL down to
  `send_joint_professional_report`. Response gained
  `preview_included`/`preview_jti` fields; `joint_report_emails` rows
  now carry a `preview_jti` link back to the minted token.
- `email_service.send_joint_professional_report` accepts optional
  `preview_url`; when provided, HTML body renders an "Open the joint
  report online" pill button and plaintext gets the URL block.
  Backward-compatible: absent → block is omitted.
- Joint Agreement PDF (`joint_agreement_pdf.py`) rebuilt to lead
  with the 5-bucket Parent View (matches JointAgreementParentView.jsx
  on-screen). The classic row-strip layout moved to "Appendix A -
  Detailed Item Breakdown". Backward-compatible: payloads without
  `parent_view` render the appendix only.
- Phase 3 Question-Tone Rewrites — Table 1 (SNC v2) shipped:
  s1q6, s1q7, s4q7 rewritten to neutral tone in
  `coparenting_questions.py`. Scoring engine untouched; reverse
  flags preserved so past submissions still map correctly. Deep
  Dive banks (Med/Edu/Psych) still pending per-item enumeration.
- Coverage: `tests/test_iter126_...py` — 5 new tests (30-day expiry
  verified, preview URL passthrough, HTML+text block presence,
  PDF parent-view+appendix presence, empty-payload safety).
  All 60 combined iter113-126 tests pass.

### 2026-02-22 — Share Management Panel + Reviewer Analytics + Phase 3 Deep-Dive
- `record_phi_access(...)` accepts optional `jti`; the four shared
  endpoints (`/joint-agreement/shared/*`, `/joint-professional-report/shared/*`)
  now stamp the token id on every external read + download so per-link
  analytics can be aggregated.
- `record_share_token(...)` persists the signed JWT under `token` on
  the `share_tokens` row (owner-scoped, filtered by `user_id`) so the
  owner's UI can surface copy-link / open-preview actions.
- `GET /api/share/mine` enriched: each row carries `view_count`,
  `download_count`, `last_opened_at`, `token`, `note` alongside the
  existing status split (active/expired/revoked).
- New frontend component
  `/app/frontend/src/components/ShareManagementPanel.jsx`, mounted on
  the Dashboard below `YourReportsCard`. Hidden entirely when the
  parent has no active shares so it never clutters a fresh dashboard.
  Every row shows the "viewed N times · opened <relative>" pill, a
  copy-link, an open-in-new-tab button, and a confirm-gated revoke.
- Phase 3 Deep-Dive tone rewrite: Med Deep Dive `s2_confirmation`
  rewritten to neutral "How often does a pick-up confirmation reach
  both parents..." (was "Does the other parent get a confirmation..."
  which read accusatory). Edu-Deep and Psych-Deep v2 already use
  first-person "We..." aspirational stems — no changes needed.
- Coverage: `tests/test_iter127_...py` — 6 tests (jti persistence,
  token persistence, analytics aggregation, active/expired split,
  Med-Deep prompt neutrality). Iter123/124/126 fixtures updated
  to accept the `token=` kwarg. All 79 joint-artefact + Med-Deep
  tests pass.

### 2026-02-22 — Code review fix: 14-day share links honoured
- Code review surfaced a source-confirmed HIGH: parents choosing the
  "14 days" duration on the Joint Agreement / Joint Report share
  dialog silently got a 7-day token. `auth.SHARE_TOKEN_WINDOWS` was
  missing 14 while the route + UI advertised it, so
  `create_share_token` fell back to the 7-day default.
- Fix: added 14 to `SHARE_TOKEN_WINDOWS`. The emailed Joint
  Agreement preview link (hard-coded `expire_days=14`) also now lives
  the full 14 days.
- Coverage: `tests/test_iter128_...py` — 3 regression tests
  (round-trip every advertised window, disallowed value downgrades
  correctly, route choice sets stay a subset of the allowed windows).
  All 28 combined tests pass.

### 2026-02-22 — Silent-Reviewer Nudge sweep
- New backend module `silent_reviewer_nudge.py` — daily scheduler that
  emails the SENDING PARENT (never the reviewer) when a share they
  emailed via `/joint-agreement/{id}/email` or
  `/joint-professional-report/{id}/email` has gone unopened for
  N days. Defaults: threshold 3 days, sweep every 60 min, gated by
  `SILENT_REVIEWER_NUDGE_ENABLED=1`.
- Guards: idempotent (`nudged_at` stamped after first send so no
  candidate ever fires twice), skips revoked / expired tokens, skips
  manually-minted "Get shareable link" tokens (label prefix check),
  skips tokens whose `phi_access_log` already carries an
  `external_read_via_share_link` row.
- Nudge audit-logged as `silent_reviewer_nudge` on the parent's
  PHI-access history so their accounting-of-disclosures export stays
  complete.
- New `email_service.send_silent_reviewer_nudge(...)` template — HTML
  + plain, CTA back to `/dashboard` so the parent can re-send from
  the Share Management Panel with one tap.
- Coverage: `tests/test_iter129_...py` — 5 tests (ripe unopened is
  nudged and stamped, already-opened is stamped without send,
  revoked/expired/manual tokens skipped, dry_run reports without
  side effects, below-threshold share not nudged). Full 33-test
  joint-artefact suite green.

### 2026-02-22 — ChatGPT integration (Regenerate with GPT 5.6 Terra)
- New `ai_summary_gpt.generate_executive_summary_gpt(...)` — companion
  to `ai_summary.generate_executive_summary` that targets
  `openai/gpt-5.6-terra` via the Emergent Universal LLM Key. Same
  prompt, same neutral guardrails, same signals extraction. Never
  raises — the endpoint layer falls back to Claude on failure.
- `/api/edu-deep/report/regen-summary` gained an optional `model`
  param (`"claude"` default, `"gpt"` for the 5.6 Terra alternative).
  Invalid values downgrade to Claude. The regenerated report row
  now carries `ai_summary_model` so the UI can label who wrote it.
- `SpecialNeedsV2EducationalDeepDiveReport.jsx` — added a
  Claude / GPT 5.6 toggle beside the existing short/standard/long
  length toggle. Regenerate button sends both length and model.
  The timestamp caption now surfaces which model wrote the current
  summary.
- **Rollout note**: shipped on Edu Deep as the pilot surface. Same
  pattern will drop cleanly onto Med Deep / Psych Deep / Joint
  Report once the parent-side signal on Edu is clear.
- Coverage: `tests/test_iter130_...py` — 6 tests (module targets
  gpt-5.6-terra, fail-soft without key, fail-soft on exception,
  endpoint defaults to Claude, `model=gpt` dispatches to GPT,
  garbage values fall back to Claude). Full 39-test suite green.

### 2026-02-22 — Marketing Consent Toggle UI
- New reusable frontend component
  `/app/frontend/src/components/account/MarketingConsentToggle.jsx` —
  one-click HB 300 §181.152 marketing opt-in switch. Optimistic UI
  with roll-back on failure, toasts on both success + revert, and a
  "Currently opted IN / OUT" state chip so parents never guess.
- Mounted on `DataRetention.jsx` (parents' current account hub)
  above the retention schedule. Same component can drop into a
  future dedicated `/account` page with zero refactor.
- Wired to the existing backend endpoints (no new server code):
  - `GET  /api/me/hb300/status` for initial state
  - `POST /api/me/hb300/marketing` for the flip
- Every toggle change lands in `phi_access_log` as
  `marketing_opt_in` / `marketing_opt_out` per the existing HB 300
  route implementation, so the auditor can reconstruct the exact
  moment.
- Coverage: `tests/test_iter131_...py` — 3 contract tests
  (status returns flag, opt-in flips flag + writes PHI log,
  opt-out flips it back + writes log). All 28 recent iter-tests
  green.

### 2026-02-22 — Three-fer: /account page + Recent Shared on Joint Agreement + GPT toggle on Med/Psych
- **Dedicated `/account` page**: New `pages/Account.jsx` — settings hub
  hosting the marketing toggle, basic identity block, and deep-link
  tiles to Data & Retention / HB 300 Notice / Privacy Policy.
  Protected route (`<ProtectedRoute>`), reachable via a new
  `Settings` icon in `AppShell.jsx` next to Sign Out.
- **RecentlySharedWith on Joint Agreement**: Imported + mounted on
  `pages/JointAgreement.jsx` right below the action-buttons row.
  Same compact re-send strip already live on the Joint Report page.
- **GPT toggle extended to Med + Psych Deep Dive**:
  - Backend: `med_deep_routes.py` and `psych_deep_routes.py`
    `regen-summary` now take a `model` param and dispatch to
    Claude (default) or GPT 5.6 Terra. Invalid values downgrade
    to Claude. Row payload gains `ai_summary_model`.
  - Frontend: `SpecialNeedsV2MedicalDeepDiveReport.jsx` and
    `SpecialNeedsV2PsychologicalDeepDiveReport.jsx` mirror the
    Edu Deep model toggle + timestamp label pattern.
  - Joint Report doesn't have an LLM regen path (summary is
    composed from the Compare payload, not an LLM), so no toggle
    surface there.
- Coverage: `tests/test_iter132_...py` — 6 parametrised route tests
  (`med-deep` + `psych-deep`, defaults to Claude, `model=gpt`
  dispatches to GPT, invalid falls back). Full 48-test suite green.

### 2026-02-22 — Consent History modal
- New backend endpoint `GET /api/me/hb300/consent-history` — returns
  the caller's marketing opt-in / opt-out plus HB 300 acknowledgement
  rows from `phi_access_log`, newest first, capped at 200. No writes,
  filters strictly to the caller's own `user_id`, drops unrelated
  `phi_access_log` actions.
- New frontend component
  `/app/frontend/src/components/account/ConsentHistoryModal.jsx` —
  accessible dialog (Escape closes, click-outside closes, aria-modal
  set) with per-event icon + timestamp + IP + UA + notice version.
  Empty / loading / error states covered.
- `MarketingConsentToggle` now surfaces a compact "See history"
  button below the state chip that pops the modal open. Zero new
  data — just a mirror of the log the parent already generates.
- Coverage: `tests/test_iter133_...py` — 4 tests
  (filters to consent actions only, newest-first, row shape carries
  resource_id for ack rows, empty for a brand-new user). Full
  27-recent + 48-existing-iter test suite green.

### 2026-02-22 — New-Comment Toast (live reviewer-comment ping)
- New headless React component
  `/app/frontend/src/components/NewCommentToaster.jsx` — polls
  `/api/pathway-report/comments/mine` every 30s (plus on tab-focus)
  and fires a `sonner` toast for each newly-arrived reviewer
  comment. Aggregates when 3+ land at once so the corner stays
  tidy. Toast action deep-links to the
  `#pathway-reviewer-comments` anchor on the Dashboard for
  smooth-scroll (or navigates + hashes when the parent is
  elsewhere).
- Baseline: on first-ever mount, the newest `created_at` is
  written to `localStorage.pathwayCommentSeenAt` silently so a
  returning parent doesn't get a wall of toasts for comments
  that were already visible on the dashboard.
- Wired into `Dashboard.jsx` (only visible / active while the
  parent is on the primary in-app surface). Anchor `id` added
  to `PathwayReviewerCommentsCard` so scroll-into-view works.
- No new backend code — the endpoint has existed since the
  cosign portal work. Coverage `tests/test_iter134_...py` —
  3 contract tests locking the shape the toaster relies on
  (`total`+`comments` keys, per-row `comment_text` field name,
  newest-first ordering). All 30 recent iter-tests green.

**Upcoming and Future Tasks**
    Future Tasks:
    - P3: Audio Intro for Professionals (Shimmer-voiced audio file).
    - P3: Anchored Badge pill on regenerated clauses.
    - P3: Centralised /samples landing page for all 18 sample PDFs.

## Prioritized Backlog

### 2026-03-04 — Professionals directory + parent-initiated send-code + co-parent completion toaster
- **Professionals directory (iter142)**:
  - New `professionals_routes.py` module.
  - `GET /api/professionals` (public) — returns active professionals
    ordered by `sort_order` then name. Idempotent seed inserts Matt
    Sossi on first read of an empty collection:
    - name: *Matt Sossi*
    - credentials: *San Antonio Attorney, Family Law Mediator,
      Parent Facilitator*
    - license: *Licensed to Practice in the State of Texas*
    - email: `mattsossi@bsossi.com`
    - address: `16607 Blanco #703, San Antonio, Texas 78205`
    - bio line focused on child-centered outcomes.
    - NOTE: 78205 came from the founder's message; the prior HIPAA
      contact block used 78232. Kept 78205 as the newer directive.
  - `POST /api/professionals/{professional_id}/send-alignment-code`
    (parent JWT). Mints an `SA-XXXXXX` code (reusing the
    integration_routes helpers), tags the persisted link_codes doc
    with `professional_id` + `assessment_type` + optional
    `parent_message`, and emails the professional via Resend using
    the branded template. Best-effort delivery — a Resend outage
    surfaces `delivered: false` + a friendly message but never
    fails the mint. Rate limit reuses the 5/hr guard from
    parent-driven mints.
  - Coverage: `tests/test_iter142_professionals_directory.py` —
    6 tests (seed, idempotent seed, auth required, unknown id,
    happy path, persisted context tag). All green.
- **`pages/ProfessionalsDirectory.jsx`** at `/professionals`:
  - Card grid rendering each professional (avatar initials in the
    signature purple gradient, name, credentials, license, bio,
    email, address). Selecting a card reveals a send-form with
    an assessment-type select, an optional 1000-char message
    textarea, and a purple-tinted reassurance strip explaining
    "your individual answers stay private; the professional
    receives only the code + your name + your message".
  - Successful send flips to a green confirmation panel
    displaying the code in a large monospaced pill + Copy Code
    button (fallback for parents whose email didn't land) +
    "Send to another professional" / "Back to dashboard" CTAs.
    Preserves the code visibility even when Resend delivery
    fails.
  - Accepts `?assessment=<type>` in the URL so a completion CTA
    on the assessment page can preselect the lane.
- **Nudge added to `JointReportsPicker`** — a "Ready to hand this
  off?" strip above the picker with a CTA to `/professionals`.
- **Co-parent completion toaster (iter141)**:
  - `GET /api/joint-alignment/mine` now returns a compact
    `coparent` sub-object per case: `{name, completed_at}`. Never
    the co-parent's email, user_id, or any answers. `completed_at`
    is `None` until the co-parent finishes.
  - `components/CoparentCompletionToaster.jsx` — headless poller
    (60 s cadence + focus-triggered re-poll) mirroring the
    conventions of `NewCommentToaster.jsx`. Fires a `sonner` toast
    with a "Case SA-482731 — your turn" / "both of you are done"
    description whenever a co-parent's `completed_at` crosses the
    stored `coparentCompletionSeenAt` ISO in localStorage.
    Aggregates when >2 events land at once. Mounted on the
    Dashboard alongside the existing NewCommentToaster.
  - Coverage: `tests/test_iter141_coparent_signal.py` — 2 tests
    locking the shape leakage and the completed-timestamp flow.
- **Test totals**: 46/46 pytest green across iter137–142. Frontend
  compiled clean. Live smoke-tested — `/professionals` renders
  Matt Sossi's card and the send-form reveals correctly.

### 2026-03-04 — Joint Alignment Phase B UI + Phase C completion hook & cancellation
- **Completion hook (backend, Phase C partial)**:
  `mark_assessment_completed(db, user_id, assessment_type,
  assessment_ref=None)` — public helper wired into
  `med_deep_routes.py`, `edu_deep_routes.py`, `psych_deep_routes.py`
  (both fresh + cached branches of `/report/generate`) and
  `communication_alignment_routes.py::save_reflection`. Marks the
  parent slot as `assessment_completed_at` on every open case
  matching the assessment_type, and flips the top-level case to
  `both_complete` when both parents are done.
  - MongoDB bug caught + fixed: original two-field `parents.*`
    filter matched different array elements on the same doc; now
    uses `$elemMatch` so the same parent slot is queried and
    updated together.
- **Outbound Align webhook**:
  `_notify_align_completion(payload)` posts to
  `ALIGN_COMPLETION_WEBHOOK_URL` (env var, currently unset;
  helper logs and no-ops until Align publishes their URL).
  Body is signed with HMAC-SHA256 of the request body using the
  same `INTEGRATION_SHARED_SECRET`, header
  `X-Integration-Signature`. Fail-soft: the parent-facing
  completion path never fails because of a webhook problem.
- **Align cancellation endpoint**:
  `POST /api/integrations/joint-alignment/cases/{case_id}/cancel`
  — server-to-server. Moves the case to `cancelled`, expires
  every unclaimed invitation token on it (via
  `parents.$[unclaimed].token_expires_at`). Idempotent: a
  second cancel returns 404 ("no work to do").
- **Phase B UI**:
  - `pages/JoinInvitation.jsx` at `/join/:token` — the landing
    the parent lands on from an Align email. Three-state page:
    (1) unauthed → shows the invitation preview + auth wall
    (Sign in / Create account), (2) authed + accepting → spinner,
    (3) authed + accepted → "You're linked" panel + "Start My
    Assessment" CTA that routes to the correct lane
    (`/edu-deep`, `/med-deep`, `/psych-deep`, `/communication`,
    or `/special-needs-v2`). 403 email-mismatch and 410 expired
    both have their own friendly explainers. `data-testid`s on
    every branch for testing.
  - `pages/JoinCode.jsx` at `/join` — manual `SA-XXXXXX` entry
    for parents who lost the email. Monospaced tracking-widest
    input with the exact SA-482731 placeholder. Guardrail strip
    explains code-alone is never sufficient. On success shows
    the "linked" panel with the same Start Assessment CTA.
  - `components/dashboard/JointAlignmentRequests.jsx` — new
    dashboard section that hides itself when the parent has zero
    cases (so solo parents don't grow an empty panel). Renders
    the parent's cases with status pills (Invitation received /
    In progress / Your assessment complete / Cancelled /
    Expired), Continue / Start Assessment CTA per row, and a
    top-right "Have an Alignment Code?" fallback link.
  - Mounted directly under `FourCircleFrontDoor` on
    `pages/Dashboard.jsx` so a parent invited by a professional
    sees the case immediately.
- **Companion spec shared**: `SACOPARENTSALIGN_BUILD_SPEC.md`
  copied to `frontend/public/` so it's downloadable at
  `https://sacoparentsapp.online/SACOPARENTSALIGN_BUILD_SPEC.md`
  — the Align build team can grab it directly.
- **Coverage**: `tests/test_iter140_completion_hook_and_cancel.py`
  — 7 new tests. All 38 (iter137 + iter138 + iter139 + iter140)
  green together. Frontend compiled clean. End-to-end preview
  smoke-tested: preview renders no PII, auth wall works, manual
  code page renders.
- **Still pending for Phase C**: Align must publish their inbound
  webhook URL before we can drop it into
  `ALIGN_COMPLETION_WEBHOOK_URL`. The signing side is ready.

### 2026-03-04 — Joint Alignment (professional-driven cases) — Phase A backend + Align build spec
- **Architectural shift**: the earlier parent-driven `link_codes`
  mint was reframed by the founder into a **professional-driven**
  Joint Alignment Case flow — a mediator / attorney / therapist
  creates the case on `sacoparentsalign.com`, Align emails BOTH
  parents secure per-parent invitation tokens, each parent
  completes their assessment privately on `sacoparentsapp.online`,
  and Align generates the 10-page Joint Alignment Report only
  after both are done. The parent-driven mint stays live for the
  "I want to invite my co-parent from inside the app" case.
- **`joint_alignment_routes.py`** (new module, mounted on `/api`):
  - `POST /integrations/joint-alignment/cases` (server-to-server,
    `X-Integration-Key`) — Align creates the case, receives back
    `case_id` (`SA-XXXXXX`, 6 digits) + one `invitation_url` per
    parent + `case_expires_at` (60d). Rejects non-two-parent
    payloads, duplicate emails, and unknown assessment types.
  - `GET /integrations/joint-alignment/cases/{case_id}` (server-
    to-server) — Align polls case status. When both parents
    complete, the payload additionally includes the two
    data-minimised `assessments` bundles (only the lane the case
    was opened for; never other lanes / foundation / notes /
    mediation prep). `schema_version: 1`.
  - `GET /joint-alignment/invitation/{token}` — public preview
    the `/join/:token` landing page renders BEFORE the parent
    signs in. Deliberately returns only `case_id`,
    `assessment_type`, `professional_name`, `token_expires_at`,
    `already_accepted`, `assessment_completed`. Never leaks
    email / other parent / professional email — so a stolen link
    can't enumerate PII.
  - `POST /joint-alignment/invitation/{token}/accept` (JWT
    required) — associates the invitation with the parent's
    account. **The authenticated user's email must match the
    invitation email** — this is the mechanism that stops
    someone else claiming a stray token. 403 on mismatch.
  - `POST /joint-alignment/manual-code` (JWT required) — alternate
    entry when the parent only has the visible `SA-XXXXXX` code
    from the email. Same email-match guardrail; the code alone
    is never sufficient.
  - `GET /joint-alignment/mine` (JWT required) — powers the
    dashboard "Joint Alignment Requests" section for the parent.
    Includes `my_status` per row (invited / in_progress /
    completed). Never includes co-parent answers.
- Invitation tokens: 32-byte urlsafe random, TTL 7 days.
- Timezone hardening: `_is_expired()` normalises Motor's tz-naive
  reads to UTC before comparing — one pytest failure surfaced,
  fixed centrally.
- **Docs shipped**:
  - `SACOPARENTS_INTEGRATION_API.md` — updated with the joint-
    alignment endpoints.
  - `SACOPARENTSALIGN_BUILD_SPEC.md` — companion build brief for
    the Align-side team covering their professional dashboard,
    parent invitation email template, report generation trigger,
    and the seven non-negotiable guardrails (no shared DB,
    data-minimisation, email-match guardrail, no PII in
    preview, reminders live on Align, secret rotation cadence).
- **Coverage**: `tests/test_iter139_joint_alignment_cases.py` —
  14 tests. All 32 (iter137 + iter138 + iter139) green together.
- **Live curl verified**: full flow (create case → preview →
  parent signs in → accept → dashboard listing) works end-to-end
  on the preview URL. Preview does not leak email, professional
  email, or other-parent info. Mismatched-email accept returns
  403.
- **Phase B (frontend, next session)**: `/join/:token` landing
  page (auth wall → "You've Been Invited" screen), `/join`
  manual code entry, new "Joint Alignment Requests" dashboard
  section, and the "Your Assessment Is Complete" post-completion
  screen.
- **Phase C (later)**: App→Align completion webhook once Align
  publishes an inbound URL; cancellation endpoint from Align.
  Placeholder env var `ALIGN_COMPLETION_WEBHOOK_URL` reserved.

### 2026-03-04 — Sibling integration (`sacoparentsalign`) + Communication Alignment Phase 2a + circle animations
- **P0 dropped-task RESOLVED — sibling integration wired**: three
  new endpoints in `integration_routes.py`, registered on the
  `/api` router.
  - `POST /api/link-codes` — parent-authenticated JWT. Mints an
    8-char single-use code (alphabet strips ambiguous glyphs
    I/O/1/0), 15-minute TTL, bcrypt-hashed at rest. Rate-limited
    to 5 mints per parent per hour. Minting a new code marks any
    outstanding unused code as `superseded`.
  - `POST /api/integrations/verify-link-code` — server-to-server,
    gated on `X-Integration-Key` header via `hmac.compare_digest`.
    Consumes the code (single-use) and returns `{"email": …}`.
    404 for unknown/expired/consumed codes.
  - `GET  /api/integrations/export-assessments?email=…` — same
    header gate. Returns a JSON bundle with `situation_snapshot`
    (child_goals + issues + priority + comm_style + readiness),
    `foundation_statement` (the 4 reflection prompts saved via
    /api/mediation/reflection), and `special_needs.{medical,
    educational, psychological}` (compact projection of each
    deep-dive report — profile, foundation statement,
    questions-for-professional, rating areas, signals).
    `schema_version: 1` locked. Free-text notes never leave the
    server.
  - Shared secret (verbatim from spec) in `backend/.env` as
    `INTEGRATION_SHARED_SECRET`. Missing secret => 503 (fails
    fast rather than silently accepting anything).
  - Coverage: `tests/test_iter137_sibling_integration.py` — 9
    tests locking mint format, supersede-older-codes,
    single-use consumption, unknown-code 404, integration-key
    required, integration-key wrong-value 401, export shape for
    a fresh parent, unknown-email 404, missing-secret 503. All
    green.
- **Communication Alignment Report — Phase 2a (backend only)**:
  - `communication_reflection_questions.py`: 12-item first-person
    question bank across three dimensions (Clarity, Regulation,
    Structure). Neutral parent-attributed stems only — safety
    items live on the Safety pathway, not here.
  - `communication_alignment_routes.py`: `GET /communication-
    reflection/schema`, `PUT /communication-reflection`,
    `GET /communication-reflection/mine`, `POST /communication-
    alignment/compare` (pair-by-email → `shared` / `gaps`
    ≤ or > 15-point delta per dimension), and `POST /communication-
    alignment/compare/summary` (regenerate LLM-authored neutral
    summary; Claude default, GPT 5.6 Terra optional). Malformed
    answers are gracefully dropped instead of 422-ing.
  - `ai_summary_communication.py`: dedicated prompt module with a
    strict neutral guardrail block — never adjudicative, never
    diagnostic, structured (framing / shared / gaps / child-
    focused close). Hard short-circuit: if either parent's
    `intake_choice == "unsafe"`, the function returns the safety
    sentence directly without calling the LLM.
  - Coverage: `tests/test_iter138_communication_alignment.py` —
    7 tests locking schema shape, save+read, out-of-range
    filtering, compare waiting state, compare ready state with
    shared+gaps computed correctly, compare requires-self-first
    409, and the unsafe short-circuit. All green.
  - Phase 2b (next session): frontend intake + report page +
    share-link mint.
- **Circle animations on `FourCircleFrontDoor`**: staggered
  fade-up entrance (90 ms per tile via inline `animationDelay`),
  hover-lift (`hover:-translate-y-1 hover:shadow-xl`), tap-scale
  (`active:scale-[0.98]`), icon glow-up on hover
  (`group-hover:scale-110`), CTA gap-widen on hover so the arrow
  chase feels alive. New global rule
  `.front-door-tile` in `index.css` binds the existing `fadeUp`
  keyframe.
- **Live curl verification** (`sacoparentsapp.online → parent1@test.com`):
  mint returned `V2TFFB6W`, verify returned `parent1@test.com`,
  export returned the full reconciled shape with all three
  special-needs lanes.

### 2026-03-04 — Four-Circle Front Door (new dashboard IA — Phase 1)
- **Founder-driven redesign**: the signed-in dashboard root now leads
  with four pathway circles instead of the old single "Step 1"
  situation picker. Copy taken verbatim from the founder's spec:
  🟣 Co-Parenting · 🔵 Communication · 🟠 Family Violence & Safety
  · 🟢 Child Needs. The old Step 1 hero now sits below as the
  secondary layer so nothing existing regressed.
- **`components/dashboard/FourCircleFrontDoor.jsx`** (new): four
  circle tiles, each carrying the pathway prompt, a description
  strip drawn from the founder's spec, a per-tone color palette
  (purple / blue / orange / green), and a CTA. The Child Needs
  circle expands *inline* into four sub-tiles (School & Education,
  Medical, Emotional & Psychological, Special Needs) plus a
  "Complete Child Needs Assessment" escape button. Above the
  circles a 6-step journey strip names the unifying philosophy
  (Reflect → Understand → Identify → Explore → Align → Agree). A
  crisis banner (911 · 1-800-799-7233 · text START to 88788) sits
  pinned below the circles.
- **`pages/CommunicationPathway.jsx`** (new, `/communication`):
  Phase 1 placeholder for the new Communication pathway. Asks
  "What best describes your communication?" with the founder's
  five choices (Generally productive / Difficult / High conflict /
  Very limited / Communication feels unsafe). For the first four,
  the page surfaces a recommended-tool list (BIFF, CLEAR Path,
  written comms, boundaries, etc.). For "Communication feels
  unsafe", the page auto-swaps to a "Safety comes first" panel
  that routes the parent to `/safety` and offers a one-tap
  1-800-799-7233 call. Choice is persisted in localStorage so the
  dashboard can remember on return.
- **`pages/JointReportsPicker.jsx`**: added a purple nudge banner
  at the top ("New home for co-parenting pathways — try the new
  front door →") that routes bookmarked visitors to `/dashboard`.
  Both routes stay live for a release cycle per the founder's
  choice.
- **Wiring**: `App.js` registers `/communication` and imports
  `CommunicationPathway`. `Dashboard.jsx` imports and renders
  `FourCircleFrontDoor` immediately above the existing
  `dashboard-step1-hero`. All new circles route to existing pages
  (SNC v2 compare, Safety, Med/Edu/Psych Deep, Special Needs V2).
- **Verification** via preview screenshots (`parent1@test.com`):
  Front Door renders "Where would you like to start, Sam?" with
  all 4 circles + 6-step strip + crisis strip; Child Needs
  expansion works. Communication pathway "unsafe" choice triggers
  the safety escalation panel. Joint Reports Picker nudge banner
  renders above the two-circle picker.
- **Phase 2 (next)**: backend + LLM prompts for the Communication
  Alignment Report + Co-Parenting Reflection Alignment Report.
- **Phase 3**: sunset the 8-topic grid inside JointReportsPicker
  and fold that surface into the Front Door once parents have
  migrated.

### 2026-03-04 — Meta / footer tagline refresh + App Store privacy disclosure
- **Tagline propagation**: `frontend/public/index.html` `<title>`, `meta description`, `og:title`, `og:description`, `twitter:title`, `twitter:description`, `<noscript>` H1 + intro paragraph, and the JSON-LD WebApplication `description` now all carry the "With Reflection. Build Alignment. Create Better Agreements." headline + the reconciled paragraph copy. `frontend/public/manifest.json` `description` updated to the same. Landing marketing footer subline replaced ("From conflict to cooperation.") with the new three-part tagline (`data-testid="footer-tagline"`).
- **App Store privacy disclosure**: new page `pages/AppStorePrivacy.jsx` at `/legal/app-store-privacy` — the single reconciled short-form statement referenced from both the Apple App Store Connect (App Privacy) and Google Play Console (Data Safety) submissions. Contents: five headline commitments (no tracking, no model training, encrypted in transit/at rest, delete anytime, adult-parent-only surface), 8-row reconciled data table (each row lists the Apple category + Google category, "Linked to user?", "Used for tracking?", and "Optional?"), a "data we deliberately do not collect" list, a data-sharing section, a parent-controls section, and a "store-console quick answers" copy-paste block for the operator submitting to each store. Linked from the main `/privacy` "See also" section as the first entry.
- **Sibling integration is still the P0 dropped task** — waiting on the spec paste to wire the 3 endpoints and shared-secret handling.
- Frontend compiled clean (only pre-existing intentional ESLint warnings). Iter135+136 backend tests still green (9/9). Verified via screenshot: `/legal/app-store-privacy` renders with title `Apple App Privacy & Google Play Data Safety — Reconciled Disclosure`; Landing footer now displays the new tagline.

### 2026-03-04 — Landing hero copy refresh (deploy prep)
- `Landing.jsx` hero (`Hero()`): replaced "Let's Start With You And Your
  Children." headline + supporting paragraph with the parent-facing
  tagline requested by the founder:
    - **WITH REFLECTION.**
    - **BUILD ALIGNMENT.**
    - **CREATE BETTER AGREEMENTS.**
  Followed by: *"SA CoParents helps parents independently identify their
  child's needs, concerns and parenting priorities, discover areas of
  shared understanding, identify differences without assigning blame,
  and explore options and resources for moving forward."*
- Styling: serif, uppercase, tracking-tight; purple `#3D1A78` accent on
  *Reflection / Alignment / Agreements*. Removed the italic
  reassurance line to keep the intro focused. New `data-testid`s:
  `hero-headline`, `hero-supporting-copy`.
- Frontend compiled clean (only pre-existing intentional ESLint
  warnings). Verified via screenshot on the preview URL.
- Dispatched to deployer alongside the Joint Reports Picker, 6-digit
  OTP flows, Foundation Statement Demo, Demo→Real upgrade CTAs, and
  Assessment History joint-report links.

### 2026-03-03 — Joint Reports Picker (two-circle chooser + topic grid)
- New `frontend/src/pages/JointReportsPicker.jsx` route at
  `/joint-reports` (protected). Two big primary circles
  (**Complete Joint Alignment Report** + **Family Violence /
  Communication Safety**) plus an 8-topic grid (Co-Parenting,
  Education, Medical, Psychological, Special Needs, Communication,
  Parenting Schedule, Activities). Topics with existing routes deep-
  link into the corresponding compare/intake; the last three render
  as non-interactive "Coming soon" chips.
- Crisis-line banner (911 + 1-800-799-7233 + text START to 88788)
  sits immediately below the Safety circle so parents in immediate
  danger see it without entering the assessment.
- Legend at the top names the **Private Reflection → Shared
  Alignment** boundary explicitly ("Your reflective answers stay
  private. Only the material you intentionally choose for comparison
  appears in the joint report."). Copy work only — no server-side
  privacy behavior changed (the boundary was already enforced).
- Dashboard: `ShareReportQuickAction` now shows *"See all report
  types →"* next to the pills so parents can jump straight to the
  picker.
- Verified in browser with `parent1@test.com`: title, legend, both
  primary circles, crisis banner, and all 8 topic tiles render. Deep-
  link URLs confirmed for Complete (routes with share_id) and 5
  wired topics; 3 "Coming soon" tiles are non-clickable.
- Regressions: 31 iter13x tests green (backend readiness PASS).

### 2026-03-02 — Code review remediation
- **[MEDIUM] `CodeInput.jsx` completion guard fix**: dropped the
  permanently-false `!joined.includes("")` clause. `onComplete` now
  fires reliably when all six OTP boxes are filled — auto-focus to
  password field in `ForgotPassword` and auto-verify in
  `VerificationBanner` work as designed. Added regression suite
  `CodeInput.test.jsx` (3 cases: digit-by-digit fill, SMS-autofill
  paste into box 0, non-digit stripping).
- **[LOW] URL builder helper**: extracted
  `frontend/src/lib/jointArtefactUrls.js` (`jointReportUrl`,
  `jointAgreementUrl`). Consolidated three previously-duplicated
  hand-built URL strings in `ShareReportQuickAction`,
  `JointAlignmentPromoCard`, `AssessmentHistoryCard`.
- **[LOW] Rate limit hardening for shared NAT**: `/verify-email/send-
  code` and `/password-reset/request-code` now require BOTH per-IP AND
  per-email counts to exceed `CODE_RATE_LIMIT_PER_HOUR` before
  returning 429. Two co-parents on the same home Wi-Fi can each
  request their own code without locking each other out; a single IP
  hammering many accounts still hits the cap.
- Backend regressions: all 87 iter tests green.
- Frontend regressions: 3/3 new `CodeInput` tests green.

### 2026-03-01 — Third access point: Assessment History card on Dashboard
- New `frontend/src/components/AssessmentHistoryCard.jsx` — compact
  table of every completed prep module. Each row exposes a right-side
  action:
    - If Compare share is ready → *"View Joint Alignment Report →"*
      routing to `/joint-professional-report?share=<id>&mint=1` (one-tap
      to the mint dialog).
    - Otherwise → subtle *"Review"* link to the module route so the
      row still deep-links back into the flow.
  Only renders when at least one module is complete.
- Mounted below the SNC highlights block in `Dashboard.jsx`. Reads
  from the existing `prep.completed` state and `sncHighlights` prop —
  zero new network calls.
- Header shows a *"Joint Report ready"* chip and a soft waiting hint
  when no share exists yet ("Invite your co-parent to see a Joint
  Alignment Report link appear next to each row.").
- Verified in browser with `parent1@test.com`: 5 completed rows, 5
  View Joint Alignment Report links, ready chip visible. All 87 iter
  tests green.

### 2026-02-28 — Foundation Demo on Landing + Sign In on demo banner
- `Landing.jsx` "How it works" section:
  - Step 4 (Foundation Statement) card now shows a *"See what one looks
    like →"* link routing to `/foundation/demo`.
  - New outlined pill *"See a sample Foundation Statement →"* below the
    six-step grid so visitors can peek at a real artefact before
    signing up.
- `DemoModeBanner.jsx`: added an outlined *"Sign in to my account"*
  pill next to the existing solid *"Keep it forever →"* CTA. Gives
  demo users two clear paths — sign into an existing account or claim
  the current demo as a new one. Complements the header pill added
  earlier for redundancy.

### 2026-02-27 — Header Sign In pill for demo users
- `frontend/src/components/AppShell.jsx`: purple "Sign in" pill in the
  top nav rendered only when `user?.is_guest === true`, routing to
  `/login`. Mirrored into the mobile menu. Real (non-guest) accounts
  see no change. Solves the demo-user complaint that there was no way
  to sign into an existing account from within the dashboard without
  hitting Landing.

### 2026-02-26 — Report navigation trap fixes + Foundation Statement demo view
- **Fix "stuck in report" trap**:
  - `JointProfessionalReport.jsx` + `JointAgreement.jsx`: strip `?mint=1`
    from the URL immediately after the auto-open fires, so a refresh /
    back-forward / PWA relaunch doesn't retrigger the mint dialog.
  - New `frontend/src/components/SignedInEscapeHatch.jsx`: subtle "Back
    to your dashboard" affordance that renders only when a real user is
    signed in. Mounted on `JointReportShared.jsx` and
    `JointAgreementShared.jsx` so signed-in parents landing on their
    own public shared link have an in-app way home. Reviewers see
    nothing — their view stays clean.
- **New route** `/foundation/demo`:
  - Public preview of a completed Foundation Statement using composite
    fictional content mirroring the four Reflection prompts (child's
    eyes / own part / best-case outcome / co-parent's eyes). Every
    panel watermarked *EXAMPLE* so it can never be confused with real
    data. Two CTAs (start your own / explore dashboard). Shareable
    without auth — plants nicely in marketing emails or Landing.
  - New entry points: `/my-plan` empty state adds *"See what one looks
    like →"* under *"Write it →"*; `Reflection.jsx` intro adds *"See
    what a finished Foundation Statement looks like →"*.
- All 87 iter tests still green. UI verified in browser.

### 2026-02-25 — "Joint Alignment Report" terminology + assessment-completion promo card
- New `frontend/src/components/JointAlignmentPromoCard.jsx` — the
  "unmistakable next action" card. Two states via the existing
  `/snc2/compare/dashboard/highlights` + `/invites/coparent` endpoints:
  - Waiting: big **Create a Joint Alignment Report** headline, inline
    "Co-Parent's email" field + **Invite Co-Parent** button. Copy
    reassures: *"You never share passwords."*
  - Ready: **Your Joint Alignment Report is ready** with two solid
    CTAs — *View Joint Alignment Report* / *View Joint Alignment
    Agreement* — both routed with `?mint=1` so the parent lands in the
    share-link mint dialog in one tap.
- Mounted at the top of `/next-steps/:assessment` (`NextSteps.jsx`) and
  above the video block on `/summary` (`Summary.jsx`).
- Parent-facing terminology swept from "Joint Professional Report" and
  "Joint Agreement Draft" → **Joint Alignment Report** / **Joint
  Alignment Agreement** across `Dashboard.jsx`, `PathwayReport.jsx`,
  `SpecialNeedsV2CompareView.jsx`, `JointProfessionalReport.jsx`,
  `JointAgreement.jsx`, `ShareReportQuickAction.jsx`, `Landing.jsx`.
- Kept on-artefact professional-facing labels ("Joint Co-Parenting
  Summary for Professional Review", "Joint Co-Parenting Agreement
  Draft") unchanged on the shared-view pages and PDF outputs so
  mediators/attorneys still recognise the artefact they receive.
- Added parent-facing sublines directly under the artefact H1s on both
  Joint pages: *"This is your Joint Alignment Report — send it to your
  mediator or attorney. Your co-parent sees the same version."*
- New `tests/test_iter136_promo_card_endpoints_contract.py` — 3 tests
  locking the read-shape of the two endpoints the promo card depends
  on. All 87 iter tests green. UI verified in browser: both waiting
  and ready states render as designed.

### 2026-02-24 — In-app 6-digit code flows for email verify & password reset
- New auth endpoints on `/api/auth/`:
  - `POST /verify-email/send-code` — mints a bcrypt-hashed 6-digit code
    (15-min TTL, 5 attempts, 5/hr per-IP rate limit) and emails it via
    Resend. Always 200 for privacy.
  - `POST /verify-email/confirm-code` — validates `{email, code}`,
    flips `email_verified: true`.
  - `POST /password-reset/request-code` — same shape, mode `reset_code`.
  - `POST /password-reset/confirm-code` — validates `{email, code,
    password}`, rotates the password, marks the email verified,
    burns any other outstanding auth tokens for the user, signs them in.
- `email_service.py`: new `send_verification_code` and
  `send_password_reset_code` templates with a big letter-spaced code
  block and no CTA button (parents type the code back into the app).
- New reusable `frontend/src/components/CodeInput.jsx` — 6-box numeric
  entry with auto-advance, backspace clear-previous, arrow-key nav,
  paste distribution, and `one-time-code` autocomplete hint.
- `ForgotPassword.jsx` rewritten as a two-step flow: enter email →
  receive code → type code + new password → auto sign-in. Toast
  messaging preserves account-existence privacy.
- `VerificationBanner.jsx` gains an "Enter code instead" button — the
  banner sends the code inline and swaps in the 6-box input without
  navigating away.
- `Register.jsx`: added a subtle "Already have an account? Reset
  password" link below the password field so returning users don't
  have to bounce back to Login first.
- New `tests/test_iter135_code_based_verification_and_reset.py` — 6
  pytest cases covering happy path, wrong-code attempts,
  invalidate-older-codes, already-verified short-circuit, unknown-email
  privacy, and 5-attempt lockout. All 84 iter tests pass.

### 2026-02-23 — OG image swap + Dashboard "Share a report" quick action
- `frontend/public/index.html`: swapped `og:image` / `twitter:image` to the
  new `screenshots/joint-composite-og.png` (1200×630 letterboxed) with the
  full-res `joint-composite.png` (2560×987) as a secondary tag. Titles /
  descriptions updated to "Two separated parents — one shared story."
  So every share of `sacoparentsapp.online` on Slack, iMessage, WhatsApp,
  or Twitter renders the composite instead of the generic logo.
- `frontend/public/screenshots/joint-composite-og.png`: generated
  1200×630 letterboxed version of the composite for social scrapers.
- New `frontend/src/components/ShareReportQuickAction.jsx`: compact pill
  in the Dashboard Step 1 hero. Routes to
  `/joint-professional-report?share=<id>&mint=1` when the Compare share
  is ready; otherwise a soft-locked "unlocks after your Compare is ready"
  state so the entry point is always visible.
- `frontend/src/pages/JointProfessionalReport.jsx`: auto-fires the mint
  dialog when `?mint=1` is present (once the report finishes loading).
- Verified with screenshot tool — pill renders in ready state for
  `parent1@test.com` (active Compare share) and routes cleanly.

### P1 — Upcoming
- Policy-Refresh Email Blast (returning parents notice of new privacy)
- Marketing-toggle UI on account page (backend endpoint exists)
- Multi-State OCR payload (`total_individuals_affected`,
  `ocr_threshold_crossed` for federal ≥500 breach line)
- Live Operator Alert on breach draft filing
- Nudge Operator Preview endpoint (admin-only next-Monday preview)
- New-Comment toast on dashboard when reviewer comments land
- HTML Co-Parenting Agreement form (user request — clarifying qs pending)

### P2 — Future
- Multi-reviewer chain for co-sign portal (stack second signature)
- MongoDB field-level encryption at rest on safety/snc2/agreements
- Split `Dashboard.jsx` (1,190 lines), `SafetyAssessment.jsx` (~1,086),
  `Privacy.jsx` (618), `AppRoutes` (402)
- Refactor `ai_service.generate_nd_report` and
  `admin_nd_case_pdf.build_admin_case_history_pdf` (complexity 21)
- Hoist static Safety.jsx inline arrays to module constants

### P3 — Backlog
- Audio Intro for Professionals (Shimmer TTS on 3-min transcript)
- "Anchored Badge" pill on regenerated clauses
- Centralised /samples landing page for all 18 sample PDFs

## Known Non-Regressions (do NOT auto-fix)
- SAST hook-deps: mass-adding causes infinite fetch loops on this repo
- Circular imports: function-scoped intentionally to dodge FastAPI
  startup deadlocks
- MD5 in `intervention_compliance_routes.py`: `usedforsecurity=False`
  for stable user dedupe hashes
- localStorage instances (28): non-sensitive UX state (banner
  dismissals, orientation flags)

## Integrations Status
| Service | Purpose | Status |
|---|---|---|
| Claude Sonnet 4.5 | AI summaries + coaching | Live via Emergent LLM Key |
| OpenAI TTS (Shimmer) | Report audio | Live via Emergent LLM Key |
| Resend | Transactional email | Live (user API key) |
| Virtru Gateway SMTP | PHI-tier email | Wired, flag-off, BAA pending |

## Key API Endpoints
- `POST /api/me/hb300/acknowledge`
- `GET /api/me/hb300/status`
- `POST /api/auth/register` (auto-adds HB 300 ack)
- `GET /api/insights/samples/{filename}`
- `POST /api/safety-assessment/{id}/regenerate-summaries`
