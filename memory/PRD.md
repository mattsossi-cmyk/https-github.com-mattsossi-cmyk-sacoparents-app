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

**Standing rule — SAST / Code-Review findings are DO NOT FIX** (reaffirmed
2026-02-26). Every fork since iter60ish has been served the same report
(MD5 in `intervention_compliance_routes.py`, circular imports between
`nd_risk_pdf` ↔ `nd_risk_routes`, ~86 "undefined variables" from Motor
cursor / Pydantic false-positives, 41+ hardcoded test secrets, complexity
warnings on `admin_nd_case_pdf.build_admin_case_history_pdf` +
`_render_assessment_block` + `ai_service.generate_summary` +
`generate_improvement_plan`, 33/32/42-import counts on
`insights_routes.py` / `joint_alignment_routes.py` /
`mediation_routes.py`). Every one of these either (a) risks the
"PDFs and frontend strings must remain in exact lockstep" invariant
(anything touching a PDF builder or an ai_service prompt template),
(b) is a static-analysis false positive, or (c) would orphan existing
stored hashes (MD5 → SHA-256 swap on intervention IDs). Founder has
confirmed on iter226 (and every prior fork) to **ignore this report
in full**. If a future fork sees the same list, the answer is the
same — do not touch it.

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


### 2026-02-26 — Iter227 · Snapshot Library Strip

Follow-on to iter225. Every time a parent hits Confirm & save in
the Guided Journey wizard we now record a snapshot entry so the
Coparenting Journey toolkit can offer "Recent snapshots" one-tap
re-downloads without re-running the wizard. Verified in iter85
(backend 10/10 pytest + frontend 100% at 390×844).

**🟢 P1 — snapshot_history field on portal_state**
- New `snapshot_history: Optional[List[Dict]]` on
  `PortalStatePayload`, defaulted to `None` in
  `_empty_portal_state()`.
- New sanitizer `_sanitize_snapshot_history()` in
  `portal_routes.py`. Per-item validation:
    * `topic` MUST be in `_GUIDED_TOPICS` (unknown topics
      dropped)
    * `answers` MUST be a non-empty list; each Q&A truncated
      (`question` → 400 chars, `answer` → 2000 chars)
    * `saved_at` capped at 40 chars; optional `id`
      (int-coerced), `save_key` (64 chars), `category` (64
      chars), `safety_flagged` (bool)
    * total per-item JSON size capped at
      `_MAX_SNAPSHOT_BYTES=12_000`
    * list capped at `_MAX_SNAPSHOT_HISTORY=12` (newest
      first — client is source of ordering)
- Wired into the existing PUT/GET partial-update pipeline
  so passing `snapshot_history=None` explicitly clears the
  field.

**🟢 P1 — Frontend Snapshot Library UX**
- New localStorage constants `SNAPSHOT_HISTORY_KEY =
  "sacoparents_snapshot_history"` +
  `SNAPSHOT_HISTORY_MAX = 12` exported from
  `portalStorage.js`.
- New `snapshotHistory` state in `SacoparentsPortal.jsx`.
  Hydrates from localStorage on mount; hydrated from
  `portal_state.snapshot_history` on sign-in server-fetch;
  included in the debounced PUT payload so it round-trips
  across devices.
- `onGuidedSave` now prepends a snapshot entry
  `{id, topic, answers, saved_at, save_key, category,
  safety_flagged}` before writing to
  foundation_text/align_records/milestones — so **every
  committed run lands in the library** regardless of which
  save_key branch it took.
- New component
  `/app/frontend/src/pages/portal/SnapshotStrip.jsx`:
    * renders nothing when `history` is empty
    * header: "Recent snapshots" + FA clock-rotate icon +
      "Last N of M" counter
    * one card per snapshot (topic label + optional
      category + N answers + relative age via a compact
      `relativeAge()` helper — "1m ago", "3h ago", "2d
      ago", "1mo ago")
    * three tiny buttons per card: `PDF` (standard, purple
      outline), `Fridge` (amber outline), `×2` (amber
      outline) — testids
      `snapshot-redownload-{standard|fridge|pair}-{idx}`
- Rendered inside `AlignmentHub.jsx`'s
  `hideCourtOnly` toolkit card, above the tile grid so
  it's the first thing a returning parent sees.

**Verified — iter85 test report**
- Backend 10/10 pytest passing; frontend E2E on live wizard
  + seeded snapshots — all 9 re-download buttons produce
  correct filenames + variant + safety_flagged; zero
  horizontal overflow at 390×844.


### 2026-02-26 — Iter225 · Fridge Card Pair Print

Follow-on to iter223's fridge-size recap. Adds a "Print two
side-by-side" option so both parents get an identical fridge
card from one print — cut down the middle and each parent walks
away with their own copy. Verified in iter84 (backend 20/20 +
frontend 100% at 390×844).

**🟢 P1 — Fridge Pair PDF variant**
- Refactored `_build_fridge_snapshot_pdf` into a shared
  `_draw_fridge_card(pdf, x, y, w, h, ...)` helper + a
  `_plain_answers()` extractor. Solo variant now uses the
  helper too, so both variants share pixel-perfect layout
  with zero drift.
- New `_FridgePairPDF` chassis — A5-landscape (210×148 mm,
  orientation='L'), zero margins.
- New `_build_fridge_pair_snapshot_pdf()` draws two copies of
  the card side by side at `x=0` and `x=105` on a single
  A5-landscape sheet. A dashed cut line runs down the
  centerline (`x=105`) drawn as short 3 mm segments, and a
  small "✂ cut" label sits at the very top so users know
  exactly where the scissors go.
- `build_portal_guided_snapshot_pdf()` variant tuple
  extended to `('standard', 'fridge', 'fridge_pair')`.
- Endpoint `POST /api/portal/guided-snapshot-pdf` pattern
  updated to `^(standard|fridge|fridge_pair)$`. Filename
  suffix logic: `fridge`→`-fridge`, `fridge_pair`→
  `-fridge-pair`, standard→no suffix.
- Regression: solo (`variant='fridge'`) filename + layout
  unchanged from iter223 (verified via pypdf mediabox
  105×148 mm + doubled headline text only in the pair
  variant).

**🟢 P1 — Frontend "Print two side-by-side" toggle**
- New `pairPrint` state in `GuidedJourneyModal.jsx`. Default
  unchecked; resets on modal close/reopen.
- New checkbox row below the recap 2-col button grid with
  testid `guided-recap-pair-checkbox-{topic}` inside a
  `guided-recap-pair-toggle-{topic}` label. Copy: *"Print
  two side-by-side (both parents get a fridge card from
  one print)"*.
- Fridge Card button label swaps to "Fridge Card ×2" when
  the checkbox is on.
- `downloadSnapshot('fridge')` resolves to
  `variant='fridge_pair'` when `pairPrint===true`. The
  Snapshot PDF button (standard variant) is INDEPENDENT of
  the checkbox — always ships the A4 standard even when
  pair is toggled on.

**Files touched**
- `/app/backend/portal_pdf.py` — `_draw_fridge_card`,
  `_plain_answers`, `_FridgePDF` (zero-margin refactor),
  `_FridgePairPDF`, `_build_fridge_pair_snapshot_pdf`,
  updated dispatcher.
- `/app/backend/portal_routes.py` — variant pattern +
  filename suffix logic.
- `/app/frontend/src/pages/portal/GuidedJourneyModal.jsx` —
  `pairPrint` state, checkbox row, button label swap,
  variant routing in `downloadSnapshot`.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` —
  `downloadGuidedSnapshot` accepts + forwards
  `variant='fridge_pair'` with `-fridge-pair` filename
  suffix.
- `/app/backend/tests/test_iter225_fridge_pair.py` (new,
  20 tests).

**Verified — iter84 test report**
- Backend 20/20 pytest: filenames per topic, size delta
  pair>solo (~1900 vs ~1500 bytes), pattern 422 for
  bogus/case-sensitive variants, pypdf mediabox verified
  A5-landscape 210×148 mm with doubled headline (once per
  card), empty answers → 200 both variants with empty-state
  stubs, safety_flagged meta on both cards, regression on
  solo dimensions + filename + auth.
- Frontend 100% @ 390×844: recap card renders with
  `guided-recap-actions-{topic}` grid + toggle label with
  copy "Print two side-by-side" + checkbox default
  unchecked; button label swaps `Fridge Card` ↔
  `Fridge Card ×2`; download filenames route correctly
  based on checkbox state; toggle resets on modal close.
- Zero horizontal overflow at 390×844.

**Deferred (P2 — from iter84 review)**
- `portal_pdf.py` now ~1400 lines — split fridge builders
  + standard builder into a submodule at next opportunity.
- Dashed cut line uses a Python loop of short `line()`
  calls — fpdf2 supports `set_dash_pattern()` for cleaner
  rendering. Low priority.


### 2026-02-26 — Iter224 · Nudge Digest for Founder (weekly admin recap)

Follow-on to iter223. Sends a weekly recap email to every
`ADMIN_EMAILS` inbox summarizing last week's Guided Draft Nudge
batch — how many nudges went out, how many parents finished within
7 days, per-topic breakdown, conversion %. Verified in iter83
(15/15 backend pytest passing).

**🟢 P1 — Nudge Digest cron + worker**
- New second cron entry in `/app/.emergent/crons.yml` —
  `nudge-digest` scheduled `0 16 * * 1` (Monday 16:00 UTC,
  one hour after the nudge send at 15:00) so every parent in
  the digest has had a full 7-day follow-up window.
- New endpoint `POST /api/cron/nudge-digest` on the existing
  cron router — same bearer-auth pattern, echoes
  `X-Webhook-Id` as `run_id`, enqueues via `BackgroundTasks`.
- New worker `/app/backend/guided_draft_digest.py`:
  * `compute_digest(db, now)` — pure, no email side-effects,
    reusable by the future admin UI. Scans
    `guided_draft_nudges` for `sent_at` in the 14→7 day
    lookback window. Builds a per-user portal_state index
    once (O(n)).
  * "Finished" heuristic: the parent's
    `portal_state.guided_drafts[topic]` is either
    (a) missing entirely (Confirm & save cleared the draft),
    or (b) has an `updated_at` newer than `sent_at` AND
    within the 7-day follow-up deadline.
  * `send_nudge_digest(db, now)` — computes then dispatches
    to every `ADMIN_EMAILS` recipient. When `total_sent == 0`
    the email is skipped entirely so admins don't get empty
    weekly noise. Per-admin try/except keeps the loop
    resilient to a single Resend transient failure.
- Defensive `_TOPIC_LABELS` whitelist skips legacy/unknown
  topics so a bad legacy row never contaminates the digest.
- `by_topic` output is keyed only by the human-readable
  label ("Foundation Statement", "Medical Needs Assessment",
  etc.) — no user_id in the email body.

**🟢 P1 — Nudge Digest email**
- New `send_nudge_digest()` helper in `email_service.py`.
  Subject: `[SA CoParents] Nudge digest — X of Y finished
  last week`. HTML body has three summary tiles (Nudges
  sent, Finished in 7d, Conversion %) plus a per-topic table
  showing "Finished / Sent" for each topic. Plain-text
  fallback lists the same numbers as a bullet list.
- HTML-escapes every user-visible topic label + date range
  via the existing `_html.escape` path.

**Files touched**
- `/app/.emergent/crons.yml` — added second entry
  `nudge-digest` Monday 16:00 UTC.
- `/app/backend/cron_routes.py` — new
  `POST /cron/nudge-digest` handler.
- `/app/backend/guided_draft_digest.py` (new) —
  `compute_digest()` + `send_nudge_digest()` (~180 lines).
- `/app/backend/email_service.py` — new
  `send_nudge_digest()` helper (~100 lines).
- `/app/backend/tests/test_iter224_nudge_digest.py` (new,
  15 tests).

**Verified — iter83 test report**
- Backend 15/15: cron auth (401/200/X-Webhook-Id echo,
  enqueued='nudge-digest'); compute_digest heuristic across
  three seeded nudges (updated-after → finished; updated-
  before → not finished; drafts=null → finished; totals
  3/2/66.7%); window boundaries (5d fresh + 20d old both
  excluded, 8d included); empty window returns zeros AND
  skips email; unknown-topic defensive skip; multi-admin
  dispatch loop with single-recipient failure isolated;
  email body assertions (3 tiles + per-topic table + window
  range + correct subject); crons.yml has BOTH entries
  scheduled 1 hour apart with matching schema; regression on
  guided-draft-nudge cron + fridge PDF + standard PDF.
- End-to-end main-agent smoke test: `compute_digest` returned
  `{total_sent: 3, total_finished: 2, conversion_pct: 66.7,
  by_topic: {Foundation: 1/1, Medical: 0/1, Educational:
  1/1}}` and `send_nudge_digest` dispatched to
  1 admin (`mattsossi@bsossi.com` via existing Resend).

**Deferred (P2)**
- Admin UI card that surfaces this same `compute_digest()`
  payload in `/admin` so the founder can pull it on-demand
  without waiting for the weekly cron.


### 2026-02-26 — Iter223 · Guided Draft Nudge Cron + Fridge-Size Recap

Two follow-on features layered on iter222 the founder picked from
Next Action Items. Verified in iter82 (backend 15/15 pytest; frontend
2-button recap grid + fridge-download filename smoke-tested by main
agent).

**🟢 P1 — Guided Draft Nudge (weekly cron)**
- New platform cron in `/app/.emergent/crons.yml` — single entry
  `guided-draft-nudge` scheduled `0 15 * * 1` (Monday 15:00 UTC),
  calling `{{BASE_URL}}/api/cron/guided-draft-nudge` via POST.
- New backend module `/app/backend/cron_routes.py` — dedicated
  router prefix `/cron`, bearer-auth via `WEBHOOK_CRON_SECRET`
  env (added to `/app/backend/.env` at bootstrap;
  `hmac.compare_digest` constant-time verification). Missing/empty
  secret refuses every call (401). Endpoint acks 2xx immediately
  and enqueues the sweep as a `BackgroundTasks` job. Echoes the
  dispatcher's `X-Webhook-Id` back as `run_id` for observability.
- New worker `/app/backend/guided_draft_nudge.py` —
  `send_guided_draft_nudges(db, portal_url)` sweeps
  `portal_state` for docs with a non-null `guided_drafts`,
  filters to parents whose newest draft `updated_at` is
  ≥5 days (`NUDGE_MIN_DAYS`) and ≤14 days (`DRAFT_TTL_DAYS`)
  ago — past-TTL drafts are skipped so we never spam a
  parent for a draft that's already been auto-cleared.
- Per-parent-per-topic-per-ISO-week dedupe collection
  `guided_draft_nudges` (`{user_id, topic, week_key,
  sent_at, days_since_update, days_left}`) — first-touch wins;
  running the sweep twice in the same week is a no-op after the
  first send. Users collection is queried by `user_id`
  (this codebase's `users` schema uses `user_id`, not `id`).
- New email helper `send_guided_draft_nudge()` in
  `email_service.py` (uses the shared Resend `_send()`). Subject
  reads "Your {topic_label} is {N} days from expiring"; CTA
  "Finish my guided journey"; body names the exact step and
  days-left. Never mentions the co-parent.
- All 4 age scenarios verified against a real seed:
  7-day stale → stats {eligible:1, sent:1}; second run → dedupe
  {sent:0, skipped_dupes:1}; 2-day fresh → {eligible:0};
  20-day expired → {eligible:0}.

**🟢 P1 — Fridge-Size Recap (postcard variant)**
- New `_FridgePDF` chassis in `portal_pdf.py` — A6 portrait
  (105 × 148 mm), minimal footer, no banner header. Sits
  cleanly on 4×6 photo paper or a fridge magnet.
- New `_build_fridge_snapshot_pdf()` renders a soft-purple
  `_FRIDGE_HEADLINES` title + a meta strip (parent · date ·
  optional "Safety-flagged voice") + a 5-item bullet list of
  the parent's answers ONLY (no scripted questions, each
  truncated to 140 chars). Bottom of the card has two
  hand-sign lines with "Parent A signature" / "Parent B
  signature" labels + a "Signed by both parents" caption
  pinned above the footer.
- `build_portal_guided_snapshot_pdf()` now dispatches on a
  new `variant: Literal['standard','fridge']` kwarg.
- Endpoint `POST /api/portal/guided-snapshot-pdf` gains a
  `variant` field on `GuidedSnapshotPdfBody`
  (`Field(default='standard', pattern='^(standard|fridge)$')`).
  Filename suffix `-fridge` when variant=fridge so parents
  can tell the two downloads apart.
- Frontend recap card in `GuidedJourneyModal.jsx` now
  shows a 2-column grid of buttons:
    * `guided-recap-snapshot-{topic}` — purple outline
      → "Snapshot PDF" (standard A4)
    * `guided-recap-fridge-{topic}` — amber outline
      → "Fridge Card" (postcard A6)
- `snapshotBusy` state now stores `false | "standard" | "fridge"`
  so each button shows "Preparing…" while its own download is
  in-flight; the other button stays disabled in the meantime.

**Files touched**
- `/app/.emergent/crons.yml` (new — single weekly entry).
- `/app/backend/.env` — new `WEBHOOK_CRON_SECRET` (48 URL-safe
  random bytes).
- `/app/backend/cron_routes.py` (new) — cron webhook router.
- `/app/backend/guided_draft_nudge.py` (new) — worker.
- `/app/backend/email_service.py` — new
  `send_guided_draft_nudge()`.
- `/app/backend/portal_pdf.py` — `_FridgePDF` chassis,
  `_build_fridge_snapshot_pdf()`, dispatcher in
  `build_portal_guided_snapshot_pdf()`.
- `/app/backend/portal_routes.py` —
  `GuidedSnapshotPdfBody.variant`, filename suffix logic,
  import of `hmac` + `BackgroundTasks`.
- `/app/backend/server.py` — register `cron_router` on the
  api_router.
- `/app/frontend/src/pages/portal/GuidedJourneyModal.jsx` —
  2-col recap grid, `downloadSnapshot(variant)`, per-variant
  busy state.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` —
  `downloadGuidedSnapshot` accepts + forwards `variant`.
- `/app/backend/tests/test_iter223_guided_nudge_and_fridge.py`
  (new, 15 tests).

**Verified — iter82 test report**
- Backend 15/15 pytest passing: cron auth (missing/wrong/correct
  bearer), X-Webhook-Id echo, worker stats for all 4 draft-age
  scenarios (2d/7d/20d + dedupe), dedup row structure, fridge
  PDF endpoint (5 sub-cases incl. Safety-flagged voice marker via
  pypdf text extraction), regression standard variant for all
  six topics, crons.yml YAML validity.
- Main-agent smoke test @ 390×844: recap card rendered with
  BOTH `guided-recap-snapshot-foundation` + `guided-recap-fridge-foundation`
  in a 2-col grid; fridge download event fired with EXACT
  filename `coparent-snapshot-foundation-fridge.pdf`; standard
  download fired with `coparent-snapshot-foundation.pdf`. No
  horizontal overflow.

**⚠️ Manual DevOps step for the founder**
- The preview environment now has `WEBHOOK_CRON_SECRET` in
  its `/app/backend/.env`. When the app is redeployed to
  production, that secret must also be present in the
  production env — otherwise every cron dispatch will 401.
  I can't set production env vars from preview.

**Deferred (P2 — from iter82 review)**
- Add a `guided-recap-actions-{topic}` testid on the recap
  button grid `<div>` so future E2E tests can assert 2-col
  layout without structural traversal.


### 2026-02-26 — Iter222 · Coparent Snapshot PDF + Draft Sync + Voice Note

Three follow-on features to the iter220/iter221 Guided Journey
wizard the founder picked from Next Action Items. Verified in
iter81 (backend 24/24 pytest + frontend 100% acceptance criteria).

**🟢 P1 — Coparent Snapshot PDF (one-page shareable)**
- New `portal_pdf.build_portal_guided_snapshot_pdf(topic, answers,
  author_name, case_ref, safety_flagged, generated_at)` builds a
  one-page branded PDF with per-topic label + intro + meta rows +
  Q&A card grid. Empty answers render an empty-state stub instead
  of a silent blank. `safety_flagged=true` adds a "Communication
  Style: Grey-rock voice" meta row for the mediator/attorney
  who receives the file.
- New endpoint `POST /api/portal/guided-snapshot-pdf` (public,
  streams application/pdf with attachment Content-Disposition
  `coparent-snapshot-{topic}.pdf`).
- Frontend: recap card in `GuidedJourneyModal.jsx` gets a
  `guided-recap-snapshot-{topic}` button. Container's
  `downloadGuidedSnapshot` uses the shared `downloadPdfFromApi`
  helper so the file lands via `URL.createObjectURL` → click
  download link (same UX as the other portal PDFs).

**🟢 P1 — Draft Sync (cross-device resume)**
- `PortalStatePayload` gains a `guided_drafts: Optional[Dict]`
  field. `_sanitize_guided_drafts` whitelists the six topic
  keys (`foundation`, `coparenting`, `safety`, `medical`,
  `educational`, `psychological`), truncates history/answers
  arrays defensively (40 items each), and enforces a per-topic
  12 KB byte cap after serialization.
- Frontend container hydrates guided_drafts from
  `GET /portal/state` on sign-in (writes each topic to
  `localStorage.sacoparents_guided_draft_${topic}`) so a new
  device can immediately show the resume prompt.
- Modal fires `onDraftPersist()` after every `writeDraft`/
  `clearDraft`. Container bumps `guidedDraftsRev` → the
  debounced `PUT /portal/state` effect re-fires, collects the
  current localStorage drafts, and syncs them up under
  `guided_drafts`.
- Cross-device round-trip verified: parent1 answers Q1 in
  browser A → server has `guided_drafts.foundation.answers=[…]`.
  Same parent in browser B → hydrates draft → resume prompt
  shows the same answer count.

**🟢 P1 — Coach Voice Note (hold-to-record)**
- New Whisper wrapper `portal_ai.transcribe_voice_note(bytes,
  filename)` uses `OpenAISpeechToText` from
  `emergentintegrations.llm.openai` with the shared
  `EMERGENT_LLM_KEY`. Model `whisper-1`, response_format
  `json`, language `en`. Zero on-disk storage — bytes fed
  through a `BytesIO` stream and dropped after transcription.
- New endpoint `POST /api/portal/voice-transcribe` accepts
  multipart `audio: UploadFile`. 25 MB size cap (Whisper's
  hard limit), 400 on empty payload, 415 on wrong
  content-type. Rate-limited via the shared BIFF/guided-
  journey bucket. 502 with a friendly "please type instead"
  message on any Whisper failure.
- Frontend: new `guided-mic-{topic}` button next to the send
  button. Hold to record (mousedown/touchstart), release to
  transcribe (mouseup/touchend). Uses `MediaRecorder` with
  `audio/webm;codecs=opus`. On release, sends the webm blob
  as multipart and prepends the transcript to the input —
  parent reviews + edits before pressing Send. Rose button
  + animate-pulse + "Recording…" placeholder while active.
- Guardrails: min-audio guard (skip upload if blob < 4 KB, i.e.
  <300 ms tap). getUserMedia denial → non-blocking error
  banner + composer still available. Modal-close stops any
  active recorder + releases the mic track.

**Files touched**
- `/app/backend/portal_pdf.py` — new
  `build_portal_guided_snapshot_pdf()` + `_TOPIC_LABELS` +
  `_TOPIC_INTRO` maps (~140 lines).
- `/app/backend/portal_routes.py` — new
  `GuidedSnapshotPdfBody` + `POST /portal/guided-snapshot-pdf`
  + `voice_transcribe` multipart handler +
  `_sanitize_guided_drafts` +
  `PortalStatePayload.guided_drafts` (~110 lines).
- `/app/backend/portal_ai.py` — new
  `transcribe_voice_note()` at bottom (~35 lines).
- `/app/frontend/src/pages/portal/GuidedJourneyModal.jsx` —
  added `onDownloadSnapshot` + `onDraftPersist` props, mic +
  transcription state (`recording`, `transcribing`,
  `mediaRecorderRef`, `audioChunksRef`, `audioStreamRef`),
  start/stopRecording callbacks, mic button next to send,
  snapshot download button in recap footer.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — hydrate
  effect writes server drafts back to localStorage, PUT
  effect collects + includes guided_drafts, new
  `guidedDraftsRev` state + `onGuidedDraftPersist` callback,
  new `downloadGuidedSnapshot` handler.

**Verified — iter81 test report**
- Backend 24/24 pytest passing: PDF endpoint for all 6 topics +
  empty-state + invalid topic 422 + safety_flagged meta row;
  voice endpoint with real WAV → 200 (Whisper responded
  {"text": "Oh"} on a 440 Hz sine) + 400/415/429 error paths;
  guided_drafts sanitizer strips unknown topics + honors 12 KB
  cap + parent1/parent2 isolation; regression PDF endpoints
  all still 200.
- Frontend @ 390×844: full parent1 flow — safety-screen clear
  → toolkit-guided-medical → 4-question wizard → recap card
  target caption "Align-Before-Agreement record (added to
  your folder)" → snapshot download event with EXACTLY
  filename `coparent-snapshot-medical.pdf` → Confirm bumps
  align_records count by 1 AND clears guided_drafts.medical
  on the server. Mic mousedown → bg-rose-600 + animate-pulse
  + "Recording… release to send" placeholder.
- Draft sync verified via GET /api/portal/state after Q1
  close → `guided_drafts.foundation.answers=1, stepIndex=1,
  progress={step:2,total:5}, saveKey='foundation_text'`.
- Zero horizontal overflow at 390×844.

**Deferred (P2 — from iter81 code review)**
- Split guided-journey + voice-transcribe into their own
  rate-limit buckets so voice testing doesn't burn BIFF's
  40/hr quota for the same IP.
- Shallow-copy the incoming snapshot dict in
  `_sanitize_guided_drafts` before truncating history/answers
  arrays (currently mutates in-place — harmless but fragile).
- Extract `useGuidedJourney`, `usePortalShare`,
  `useDraftSync` hooks — `SacoparentsPortal.jsx` now
  ~1794 lines.
- Auto-dismiss the `guided-error-{topic}` banner when the
  parent starts a new recording (currently only clears on
  next successful send).
- Bump the "Guided chat" toolkit pill text to 10px semi-bold
  for low-vision accessibility (currently 9px).


### 2026-02-26 — Iter221 · Guided Journey Resume + Recap

Two quality-of-life follow-ons to iter220 the founder picked from
Next Action Items. Both live inside `GuidedJourneyModal.jsx`.

**🟢 P1 — Resume Where You Left Off**
- New per-topic localStorage draft key
  `sacoparents_guided_draft_${topic}` (14-day TTL). Written on every
  parent send + on isFinal, cleared on Confirm-save.
- On open, if a fresh draft exists we surface a resume prompt
  (`guided-resume-${topic}`) INSTEAD of firing a new intro turn so
  we don't burn a Claude call. Prompt shows the last saved timestamp
  + step X of Y + count of saved answers. Three actions:
    * `guided-resume-continue-${topic}` — hydrate all state from
      the draft (history, answers, stepIndex, progress, isFinal,
      saveKey, category, nextQuestion) and drop into the chat
    * `guided-resume-restart-${topic}` — clear draft, fire intro
    * `guided-resume-discard-${topic}` — clear draft, close modal

**🟢 P1 — Guided Answer Recap**
- Final scripted question is answered → composer swaps to a
  "Save & review recap" button (`guided-save-${topic}`). Clicking
  it flips to a plain-language recap card (`guided-recap-${topic}`)
  showing every Q&A pair as a `guided-recap-item-${i}` card.
- Recap header caption (`guided-recap-target-${topic}`) tells the
  parent EXACTLY where their answers will land based on `save_key`:
    * foundation_text → "Foundation Statement (a paragraph you can
      save + print as PDF)"
    * cop_assessment(_note) → "Co-parenting Assessment note
      (attached to your Health Index)"
    * align_record → "Align-Before-Agreement record (added to your
      folder)"
    * safety_ack → "Private Safety Check summary (kept on this
      device)"
- Footer swaps to `guided-recap-back-${topic}` (return to wizard
  and edit) + `guided-recap-confirm-${topic}` (commit + clear
  draft + close modal + call `onSave`).
- Nothing is stored until Confirm. Cancelling from the recap does
  NOT wipe the draft — the parent can leave, come back, resume,
  and re-open the recap.

**Bonus polish (from iter80 code-review comments)**
- Transient error state now clears the moment the parent hits Send
  again (was iter80 P2 nit — "error only clears on modal close").
- Removed the dead `isQuestion` prop from coach bubbles.

**Files touched**
- `/app/frontend/src/pages/portal/portalStorage.js` — new
  `GUIDED_DRAFT_KEY_PREFIX` + `GUIDED_DRAFT_TTL_MS` constants.
- `/app/frontend/src/pages/portal/GuidedJourneyModal.jsx` —
  rewritten (~460 lines). Added `readDraft`/`writeDraft`/`clearDraft`
  helpers, resume-prompt state, recap-card state, auto-save effect.

**Verified — smoke test @ 390×844**
1. Fresh state → open modal → coach intro renders (no resume prompt)
2. Answer Q1, close mid-flow → draft written to localStorage with
   `answers=1, step=2/5`
3. Reopen → resume prompt appears with correct timestamp + progress
4. Click Continue → 5 messages restored, wizard resumes at Q2
5. Answer Q2–Q5 → final state, "Save & review recap" button
6. Click Save → recap card with 5 Q&A items + correct target caption
   ("This will be added to your Foundation Statement…")
7. Click Confirm & save → modal closes, foundation-text populated
   with 1259-char summary starting "Foundation Statement (guided
   draft)\n\nQ1: …"
8. Draft cleared after Confirm. No horizontal overflow.


### 2026-02-26 — Iter220 · Guided Journey Chat Wizard

Follow-on delta to iter218. Ships a one-question-at-a-time chat
wizard modelled on sacoparentsalign.com so parents can build
their Foundation Statement / Co-parenting Assessment / Safety
Check / Medical / Educational / Psychological records via a
guided conversation with the Claude coach — same voice as BIFF,
same grey-rock switch under IPV/DV flag. Verified in iter80
(backend 16/16 pytest + frontend 100% Playwright).

**🟢 P1 — Guided Journey backend**
- New `portal_ai.guided_journey_step(topic, step_index,
  parent_answer, safety_flagged)` with a `_GUIDED_SCRIPTS`
  dict keyed by topic. Six topics, each with a scripted
  question list and a `save_key` mapping so the frontend
  knows where to write:
    * foundation (5 questions) → `save_key='foundation_text'`
    * coparenting (5 questions) → `save_key='cop_assessment_note'`
    * safety (3 questions) → `save_key='safety_ack'`
    * medical / educational / psychological (4 each) →
      `save_key='align_record'` + `category` matching the
      folder name
- Coach messages generated by Claude Sonnet 4.5 via
  `emergentintegrations`; when `safety_flagged=true`, the
  system prompt swaps to the grey-rock voice (short, factual,
  ≤45 words, no "thanks" / "I appreciate" openers).
- New endpoint `POST /api/portal/guided-journey/step`. Public,
  rate-limited via the shared BIFF `_rate_guard` (40/hr per-IP,
  800/hr global), 502 on Claude failure, 422 on invalid topic,
  200 with graceful fallback on out-of-bounds step_index.

**🟢 P1 — Guided Journey frontend**
- New `/app/frontend/src/pages/portal/GuidedJourneyModal.jsx`.
  Bottom-sheet on mobile, centered card on desktop. Header
  carries a "Guided" purple badge (or "Grey-rock" slate/amber
  when the parent's Safety Check is flagged), Step X of Y
  counter, progress bar. Chat scroll shows coach bubbles
  (white/purple) alternating with parent bubbles (purple).
  Composer is a textarea + send button; final step swaps for
  "Save & continue" + "Discard".
- `AlignmentHub.jsx`: six "▶ Guided chat" pills wired into
  the toolkit tile grid (`toolkit-guided-foundation`,
  `toolkit-guided-medical`, `toolkit-guided-coparenting`,
  `toolkit-guided-safety`, `toolkit-guided-educational`,
  `toolkit-guided-psychological`). Pill sits absolute
  bottom-right of each tile so the underlying "open the full
  assessment page" link keeps working.
- `SacoparentsPortal.jsx` container owns `guidedTopic` state
  + `onGuidedSave({save_key, category, answers, summary})`
  handler that branches on `save_key`:
    * `foundation_text` → appends to `foundationText` +
      persists via existing `saveFoundationText` path
    * `align_record` → creates a new record with `category`
      and pushes to `alignRecords`
    * `cop_assessment_note` → appends to the co-parenting
      note field
    * `safety_ack` → currently just stores the Q&A summary
      locally (no server sync — clinical safety data stays
      on-device unless the parent explicitly saves)
- `openGuidedJourney` prop threaded from container →
  AlignmentHub → each toolkit tile.

**Files touched**
- `/app/backend/portal_ai.py` — new `_GUIDED_SCRIPTS` + async
  `guided_journey_step()` (~120 lines).
- `/app/backend/portal_routes.py` — new
  `GuidedJourneyStepBody` + `POST /guided-journey/step`
  endpoint (~30 lines).
- `/app/frontend/src/pages/portal/GuidedJourneyModal.jsx`
  (new, 313 lines).
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — 6 new
  "Guided chat" pills + `openGuidedJourney` prop.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` —
  guidedTopic state + onGuidedSave handler + `<GuidedJourneyModal/>`
  mount + pass-through prop.
- `/app/backend/tests/test_iter220_guided_journey.py` (new,
  16 tests).

**Verified — iter80 test report**
- Backend: 16/16 pytest passing @ 17s (intro turn for all six
  topics; follow-up advances step_number; final flips is_final;
  save_key + category mapping; grey-rock ≤45 words; 422 on bad
  topic; 200 on out-of-bounds step_index; rate limit 429 within
  45 calls; regression on foundation-pdf / legal-report-pdf /
  weekly-progress-pdf / complete-report-pdf endpoints).
- Frontend @ 390×844: safety screen gates first visit; UNSAFE
  path (phys-no) surfaces flagged card with continue-anyway
  CTA — not blocking; SAFE path lands on parent-journey; six
  toolkit-guided-* pills visible; opening guided modal while
  flagged shows "Grey-rock" badge; full 5-question foundation
  flow advances progress 20→40→60→80→100%; Save writes
  Q&A summary into foundation-text textarea; Close/discard
  dismisses without persisting; reopening starts fresh; no
  horizontal overflow.

**Deferred (P2 — from iter80 code review)**
- Rename `save_key='cop_assessment_note'` → `'cop_assessment'`
  in both `portal_ai._GUIDED_SCRIPTS` and the
  `SacoparentsPortal.onGuidedSave` handler to match the review
  spec. Cosmetic — E2E works today.
- Split guided-journey rate limit into its own bucket so
  chat-wizard usage doesn't burn BIFF's 40/hr quota for the
  same IP.
- Remove unused `isQuestion` prop from
  `GuidedJourneyModal.jsx` line 78.
- Clear the modal's error state on retry send (currently only
  clears on modal close).
- Extract `useGuidedJourney()` + `usePortalShare()` hooks —
  `SacoparentsPortal.jsx` now at ~1710 lines.



### 2026-02-25 — Iter218 · Coparenting Journey Toolkit + Complete Report Bundle PDF

Big delta on top of iter77. Renames "Parent Journey" → "Coparenting
Journey" everywhere user-visible, hides the court-only Legal Report
module on the self-guided door, and adds a full-featured Toolkit tile
grid + a Complete Coparenting Report bundle PDF. Verified in iter78
(backend 8/8 + frontend 13/14 — one z-order overlap bug, now fixed
inline; re-verified via smoke test).

**🟢 P0 — Rename Parent Journey → Coparenting Journey**
- `DoorsGateway.jsx`: `<h3>Coparenting Journey</h3>` + "Enter
  Coparenting Path" CTA.
- `SacoparentsPortal.jsx`: audit-stamp text + print-only header +
  tab label ("I. Alignment & Tools" when no court key, "I. Legal
  Report & Alignment" when court key is set) all reflect the new
  name.
- Internal state keys (`screen === 'parent-journey'`) + testids
  (`door-parent-journey`, `screen-parent-journey`) kept stable to
  avoid regressing tests.

**🟢 P0 — Legal Report hidden on Coparenting Journey door**
- `AlignmentHub.jsx` accepts a new `hideCourtOnly` prop. When true
  (i.e. `!courtKey`), the entire "Official Legal Conflict Resolution
  Report" module is skipped and the new Toolkit tile grid renders in
  its place.
- Court-Key path preserved 1:1 (Legal Report still there, tabs still
  read "I. Legal Report & Alignment").

**🟢 P1 — Coparenting Journey Toolkit tiles**
- Eight tiles rendered in a 2-column grid inside
  `parent-journey-toolkit`:
    1. Co-parenting Assessment → `/nd-risk-assessment`
    2. Safety Screen → `/safety-assessment`
    3. Mediation Prep & Report → `/prep/child-goals`
    4. Foundation Statement PDF → direct download
    5. Medical Needs Assessment → scroll+filter Assessments to
       Medical
    6. Educational Assessment → scroll+filter to Educational
    7. Psychological Assessment → scroll+filter to Psychological
    8. Share Joint Reports → `/joint-reports`
- Removed on user request: "Alignment Before Agreement" tile and
  "Joint Alignment Report" tile.
- New callback `openAssessmentFolder(category)` in
  `SacoparentsPortal` sets `folderFilter` and calls `scrollIntoView`
  on `#assessment-records-section`.
- "Align Before Agreement Records" section renamed to "Assessments"
  with an id anchor for the scroll target.

**🟢 P1 — Complete Coparenting Report bundle PDF**
- New backend endpoint `POST /api/portal/complete-report-pdf`
  assembles a 5-section PDF:
    1. Family Violence / Safety Assessment (from `safety_ack`)
    2. Co-parenting Assessment (from Health Index sliders as
       `cop_assessment`)
    3. Individual Align-Before-Agreement Records — Medical,
       Educational, Psychological (from portal `align_records`)
    4. Joint Align-Before-Agreement Records — empty-state stub with
       pointer to `/joint-agreement` (portal doesn't hold joint
       records)
    5. Foundation Statement (verbatim)
- Empty sections render italic muted stubs so a reader sees exactly
  what the parent still has to complete — never a silent hole.
- New `CompleteReportPdfBody` Pydantic model. `_ALLOWED_ARTEFACT_TYPES`
  extended with `"complete"`; `_FILENAMES["complete"]` +
  `_regenerate_share_pdf` dispatch added.
- Full-width primary CTA `download-complete-report-btn` below the
  toolkit grid + a secondary `share-complete-report-btn` that mints
  a `/api/portal/share` link with `artefact_type='complete'`.
- Manifest string under the CTAs lists every included section.
- Backend curl: rich payload → 200 application/pdf ~2758 bytes;
  empty payload `{}` → 200 application/pdf ~2466 bytes (all
  empty-state stubs).

**🟢 P0 — Nav overlap fix (iter78 discovery)**
- Testing agent found the fixed bottom-nav (z-40) was occluding the
  two new full-width CTAs at 390×844 (button center returned
  `NAV[data-testid=bottom-nav]` from `elementFromPoint`).
- Fix: wrapper `pb-28` → `pb-32` (128px) — pushes scrollable content
  above the fixed nav + crisis-strip stack. Verified via
  `elementFromPoint` at each button's center — both now return the
  correct button testid, and a real click fires the download.

**Files touched**
- `/app/backend/portal_pdf.py` — new
  `build_portal_complete_report_pdf()` + helpers
  (`_draw_empty_state`, `_draw_align_records_section`) (~150 lines).
- `/app/backend/portal_routes.py` — new endpoint + Pydantic body +
  extended `_ALLOWED_ARTEFACT_TYPES` / `_FILENAMES` /
  `_regenerate_share_pdf`.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — new callbacks
  (`openAssessmentFolder`, `buildCompleteReportPayload`,
  `downloadCompleteReportPdf`, `onShareCompleteReport`), tab label
  branches on `courtKey`, print-header + audit-stamp renamed, pb-32
  overlap fix.
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — Toolkit tile
  grid restructured (8 tiles), section renamed "Assessments" with
  scroll anchor id, Legal Report block wrapped in `{!hideCourtOnly}`.
- `/app/frontend/src/pages/portal/DoorsGateway.jsx` — "Coparenting
  Journey" label + "Enter Coparenting Path" CTA.
- `/app/backend/tests/test_iter78_complete_report.py` (8 tests).


### 2026-02-25 — Iter217 · Situation-Aware Milestone Panel

Small delta on top of iter76. Pivots the milestone framing to fit
the parent's stated situation when the Quick Safety Check is
flagged. Verified in iter77 (frontend 5/5, backend skipped — no
change).

**🟢 P1 — Flagged parents see an Advocate Review Log**
- When `safetyFlagged=true`, `BiffTab.jsx` swaps:
    * Heading: "History of Successes & Failures" → "Advocate
      Review Log".
    * 2-column emerald/rose Successful Resolutions / Friction
      Points tiles → single purple `advocate-review-tile` +
      `advocate-review-count` with the note *"Events logged for
      advocate / attorney review."*.
    * "+ Log Milestone" → "+ Log for advocate" (purple).
- `addMilestoneLog` in `SacoparentsPortal.jsx` skips the
  Success/Friction `window.confirm` entirely on the flagged path.
  Every flagged-context entry becomes:
  ```
  {type: "friction", source: "advocate_review",
   note: "Logged for advocate review — flagged safety context."}
  ```
- Individual milestone chips are now source-based: any entry with
  `source: "advocate_review"` renders a purple `ADVOCATE` chip
  regardless of the current safety-flag state — so a parent who
  clears the flag later still sees the advocate-context markers
  in their history.
- `advocateReviewCount` useMemo derives the count from
  `milestones.filter(m => m.source === 'advocate_review')`.

**Files touched**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — branched
  `addMilestoneLog`; new `advocateReviewCount` useMemo; passes
  prop to BiffTab.
- `/app/frontend/src/pages/portal/BiffTab.jsx` — flagged-branch
  rendering of the milestones section header, tile, log-button
  label, and per-row chip.

**Verified**
- iter77 report: 5/5 Playwright scenarios pass — flagged view
  hides success/friction, shows advocate tile; flagged log flow
  fires exactly one prompt + zero confirms; non-flagged view
  restores the 2-column tiles; advocate-review-sourced chips
  remain visible in the non-flagged view; no horizontal overflow
  at 390×844.

**Deferred (P2)**
- Extract handler groups (milestones, share-links, PDF exports)
  from `SacoparentsPortal.jsx` into hooks — container still
  ~1485 lines.


### 2026-02-25 — Iter216 · Grey-Rock Local Fallback (client stub)

Small delta on top of iter75. Closes a subtle guardrail hole: when
Claude was cold or the /biff-refine request errored out, the client-
side local stub was still emitting the warm *"Thank you for your
message… Let's maintain focus on the child's schedule. Thanks."*
line to flagged parents. Verified via smoke tests with `/biff-refine`
network-blocked to force the fallback path.

**🟢 P1 — Grey-rock Local Fallback**
- `runLocalAnalysis(val)` in `SacoparentsPortal.jsx` now branches on
  `safetyAck?.flagged`. When flagged, emits the same grey-rock
  template the server uses on empty Claude replies:
  `Received. Follow-up in writing. — <first 120 chars of draft>`.
- `applyPreset(key)` gets the same treatment — canned warm preset
  copy (e.g. "Thank you for letting me know…") is skipped for
  flagged parents in favour of the grey-rock line.
- Both callbacks include `safetyAck` in their `useCallback` deps so
  the shift is instant when the parent flips their Quick Safety
  Check.

**Files touched**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — two conditional
  branches (typing + preset paths).

**Verified**
- Preview smoke (`/portal/biff-refine` mocked to `route.abort()`):
    - Flagged + typing → grey-rock line, no "Thank you"
    - Flagged + preset → grey-rock line, no canned warm copy
    - Non-flagged + typing → warm fallback preserved
    - Non-flagged + preset → warm canned BIFF preserved
- No layout shift, no horizontal overflow at 390×844.


### 2026-02-25 — Iter215 · Grey-Rock Chip + Undo Toast + PATCH State Semantics

Three quality-of-life deltas on top of iter74. Verified in iter75
(backend 5/5 + frontend 100% assertions passed at 390×844).

**🟢 P1 — Grey-Rock Toggle Chip**
- New `biff-greyrock-chip` in the BIFF composer header. Renders only
  when `safetyFlagged=true` (i.e. the parent's own Quick Safety
  Check returned a flag). Text: `🪨 Grey-rock coach on`, slate-900
  background, amber accent. Title-tooltip explains the switch.
- Composer subtitle swaps to *"Grey-rock BIFF: short, factual,
  neutral. Safer to send to a coercive co-parent."* when the chip
  is on.
- `SacoparentsPortal.jsx` passes the derived `safetyFlagged` prop
  into `<BiffTab />`.

**🟢 P1 — Undo Toast for Safety-Plan Delete**
- Replaced `window.confirm` (modal wall) with an inline slate-900
  undo toast (`safety-plan-undo-toast`) + 5-second Undo button
  (`safety-plan-undo-btn`).
- Delete fires immediately — local state cleared, localStorage
  wiped, `PUT /portal/state` with `{safety_plan: null}` dispatched.
- Undo snapshot (previous values + savedAt + committed plan) held
  in ref state; tapping Undo restores UI + re-saves server-side.
- Auto-dismiss via `setTimeout(5000)` cleared on unmount.

**🟢 P1 — PATCH-Style State Semantics**
- `PUT /api/portal/state` now uses
  `payload.model_dump(exclude_unset=True)` so only fields explicitly
  present in the request body are written. Sanitizers + caps are
  applied conditionally per field. `$set` + `$setOnInsert(user_id)`
  preserves untouched fields.
- Frontend `onSaveSafetyPlan(null)` shrinks the immediate delete PUT
  to `{safety_plan: null}` — no more full-state snapshot on delete.
- Full-state PUTs from the debounced sync still work exactly as
  before (regression preserved).
- Verified via curl: full PUT populates → `{safety_plan: null}` PUT
  clears only safety_plan → `{court_key: 'NEW-KEY'}` PUT updates
  only court_key → `{}` PUT bumps updated_at with no other changes.

**Files touched**
- `/app/backend/portal_routes.py` — merge-style PUT with per-field
  conditional sanitization.
- `/app/frontend/src/pages/portal/BiffTab.jsx` — grey-rock chip +
  subtitle swap.
- `/app/frontend/src/pages/portal/SafetyPlanBuilder.jsx` — undo
  snapshot + toast + auto-dismiss + timer cleanup on unmount.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — pass
  `safetyFlagged` to BiffTab + shrink delete PUT to
  `{safety_plan: null}`.
- `/app/backend/tests/test_iter75_greyrock_undo_patch.py` (new, 5
  tests).

**Deferred (P2 — from iter75 review)**
- Retry / offline-banner around the fire-and-forget delete PATCH
  (currently silent on failure — debounced PUT catches it, but a
  visible signal would be kinder).
- Remove the dead `else if` branch in `undoWipe()` (unsaved-typing
  fall-through is a no-op).


### 2026-02-25 — Iter214 · One-Shot Server Sync on Safety Plan Delete

Tiny follow-on delta to iter73 review comment. Closes the ~700ms
window where a parent could tap "Delete my Safety Plan" and then
immediately close the tab — before the debounced `PUT /portal/state`
had fired — leaving the server-side copy alive.

**🟢 P2 — Immediate PUT on delete**
- `SacoparentsPortal.onSaveSafetyPlan(null)` now fires a
  fire-and-forget `PUT /portal/state` with the full current state
  snapshot and `safety_plan: null`, in addition to clearing local
  state.
- Silent on failure — the state-change-driven debounced PUT will
  still fire ~700ms later and retry (offline queue also picks it up
  via the existing `SYNC_PENDING_KEY`).
- Only fires when `user` is signed in.
- Verified via curl: PUT populated → GET returns plan → PUT with
  `safety_plan:null` → GET returns `safety_plan: None`,
  `safety_ack` preserved.

**Files touched**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — expanded
  `onSaveSafetyPlan` (added ~20 lines) with a full-state PUT and
  the corresponding deps in useCallback.


### 2026-02-25 — Iter213 · Delete My Plan + Situation-Aware Grey-Rock Coach

Small delta on top of iter72. Ships the two follow-on safety
enhancements requested by the founder. All verified in iter73
(backend 8/8 + frontend 4/4).

**🟢 P1 — Delete My Safety Plan**
- New `safety-plan-delete-btn` (rose underline link) inside the
  `SafetyPlanBuilder`, visible only when there's a saved plan.
- On click: `window.confirm` guard → clears the 5 input fields,
  wipes `sacoparents_safety_plan` from localStorage, calls
  `onSave(null)`.
- `SacoparentsPortal.onSaveSafetyPlan` now handles `null` — clears
  local state so the debounced `PUT /portal/state` syncs
  `safety_plan: null` up. Backend sanitizer already returns `None`
  for null/empty, so the server-side copy is wiped on next sync.
- Sync-caveat: cross-device wipe waits for the ~700ms debounce PUT
  to fire (called out in iter73 review as a P2 — a one-shot
  immediate PUT on delete would close the gap).

**🟢 P1 — Situation-Aware Grey-Rock Coach**
- `portal_ai.refine_biff(raw_message, *, safety_flagged=False)` now
  branches on the flag. When true, Claude runs the new
  `_BIFF_GREYROCK_SYSTEM` prompt that produces DV-safe grey-rock
  replies: minimum words, no "thanks" / "I appreciate" openers, no
  emotion words, no explanations, no questions that invite further
  contact.
- `POST /api/portal/biff-refine` accepts an optional
  `safety_flagged: bool = False` (default preserves the existing
  warm coach for un-flagged parents).
- Frontend `runAiRefine` reads `safetyAck?.flagged` and passes it in
  every debounced refine POST — so a flagged parent gets grey-rock
  copy from the moment they type without any extra UI to toggle.
- Grey-rock fallback text (when Claude returns nothing) is also
  short and factual: `"Received. Follow-up in writing. — <draft>"`.
- Verified live: same raw draft
  ("You are always late for pickups and I am sick of your excuses")
  produces "Hi, I've noticed pickup times have been running late …
  Thanks for understanding." (warm) vs. "Pickup is at 6pm on
  Friday." (grey-rock).

**Files touched**
- `/app/backend/portal_ai.py` — new grey-rock system prompt +
  branching + grey-rock fallback.
- `/app/backend/portal_routes.py` — BiffRefineBody + endpoint
  threading of `safety_flagged`.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — thread
  `safetyAck?.flagged` into runAiRefine + null-handling in
  onSaveSafetyPlan.
- `/app/frontend/src/pages/portal/SafetyPlanBuilder.jsx` — new
  `wipe()` handler + `safety-plan-delete-btn` in the saved footer.
- `/app/backend/tests/test_iter73_greyrock_delete.py` (new, 8 tests).

**Deferred (P2 — from iter73 review)**
- Consider `strict=True` on the pydantic bool so 'true'/'false'
  strings don't coerce.
- Replace `window.confirm` in the wipe flow with an inline
  undo-toast to remove the modal hop.
- Fire a one-shot immediate `PUT /portal/state` on delete so the
  server-side wipe doesn't wait on the debounce.
- Extract a `usePortalSync` hook — container still at 1424 lines.


### 2026-02-25 — Iter212 · Safety-Ack Sync + Guided Safety Plan Builder

Follow-on delta to iter71's safety guardrail suite. Ships two safety
follow-through pieces: server sync for the safety flags so signed-in
parents don't re-prompt on a new browser, and an optional 5-field
Safety Plan builder embedded inside the flagged card. All verified
in iter72 (backend 8/8 + frontend 100%).

**🟢 P1 — Safety-Ack + Safety-Plan Sync**
- `PortalStatePayload` (Pydantic) gains two optional fields:
    * `safety_ack: {cleared, flagged, date}`
    * `safety_plan: {safe_place, trusted_contact, essentials,
      code_word, tech_notes, updated_at}`
- New sanitizers `_sanitize_safety_ack` / `_sanitize_safety_plan`
  whitelist keys + cap each plan field at 500 chars server-side.
- `_empty_portal_state()` now returns both as `None`.
- Frontend `SacoparentsPortal.jsx` hydrates both from `GET
  /api/portal/state` on mount and includes them in the debounced
  `PUT /api/portal/state` payload.
- Two-user isolation verified: parent1's safety_plan never visible
  on parent2's GET.

**🟢 P1 — Guided Safety Plan Builder**
- New `SafetyPlanBuilder.jsx` embedded inside the flagged
  `safety-flagged-card`. Collapsible by default so it stays quiet
  when a parent just wants the hotlines.
- Five optional prompts from the National DV Hotline playbook:
    1. Somewhere safe I can go (safe_place)
    2. Someone I can call for help (trusted_contact)
    3. Things to grab if I leave in a hurry (essentials)
    4. A code word or phrase (code_word)
    5. Tech-safety notes (tech_notes)
- Each input capped at 500 chars client-side + server-side. Saves
  to `sacoparents_safety_plan` localStorage AND syncs when signed
  in.
- "Show private summary" panel with copy-to-clipboard for parents
  who want a screenshot or a printed plan. Summary appends the
  standard hotline block (911, 988, 1-800-799-7233, TEXT START to
  88788).
- **Privacy invariant**: the plan is NEVER surfaced to the
  co-parent (no joint reports, no share links carry it).

**Modal state reset fix**
- `SafetyScreen.jsx` now resets `phys/coerce/device/
  showFlaggedCard` on modal re-open via `useEffect([open])` — a
  parent re-taking the check no longer sees the stale flagged card
  from the previous session.

**Files edited / added**
- `/app/backend/portal_routes.py` — model + sanitizers (~50 new lines).
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — safetyPlan state +
  hydrate + PUT + onSaveSafetyPlan handler.
- `/app/frontend/src/pages/portal/portalStorage.js` — SAFETY_PLAN_KEY.
- `/app/frontend/src/pages/portal/SafetyPlanBuilder.jsx` (new).
- `/app/frontend/src/pages/portal/SafetyScreen.jsx` — plumbed
  Safety Plan props into the flagged-card + reset useEffect.
- `/app/backend/tests/test_iter72_safety_sync_plan.py` (new, 8 tests).

**Deferred (P2 — from iter72 review)**
- Add a "Delete my Safety Plan" affordance.
- Consider PATCH-style semantics (or `exclude_unset`) on `PUT
  /portal/state` so partial-update clients don't clobber
  server-side fields.
- Validate `safety_plan.updated_at` as ISO-8601, not just cap chars.
- Extract a `usePortalSync` hook from `SacoparentsPortal.jsx` —
  container still over the 700-line guideline.


### 2026-02-25 — Iter211 · Component Split + Safety-First Guardrail + Passphrase Shares + Kudos Streak

Big architectural + clinical follow-on to iter70. Cuts the 2205-line
monolithic `SacoparentsPortal.jsx` down to a 1383-line container and
adds a full 4-layer safety guardrail that was silently missing from
the new SPA. All layers verified in iter71 (backend 13/13 + frontend
100%).

**🟢 P0 — Component Split**
- `SacoparentsPortal.jsx` (2205 → 1383 lines) now imports from
  `/app/frontend/src/pages/portal/*`:
    * `portalStorage.js` — shared constants, defaults, helpers,
      `computeKudosStreak()`.
    * `DoorsGateway.jsx` — Gateway with sync-chip + optional kudos
      streak badge.
    * `CourtKeyScreen.jsx` — court-key entry + inline error.
    * `AlignmentHub.jsx` — Legal Report + Alignment records +
      Foundation Statement.
    * `BiffTab.jsx` — BIFF composer + history + milestones + weekly
      PDF actions.
    * `TrendSparkline.jsx` — SVG sparkline (moved out of monolith).
    * `ShareLegalModal.jsx` — passphrase + TTL toggle modal.
- Container owns state + effects; sub-components are pure renderers
  with prop callbacks. Every legacy testid preserved (score-slider-*,
  sig-parent-*, folder-*, preset-*, nav-*, etc.).
- `console.warn(exc)` added to `createShareLink` catch branch
  (deferred P2 from iter70).

**🔴 P0 — Safety-First Guardrail Suite (NEW — was missing)**
Clinical review flagged that the new SPA had ZERO IPV / family-
violence guardrails — BIFF, Legal Report signatures, and court-key
entry were all reachable with no safety gate. Fixed with four layers:

1. **Persistent Crisis Strip** — `SafetyCrisisStrip.jsx` pinned above
   the bottom nav on every screen (Gateway, Court-Key, Parent
   Journey). Tap-to-call for 911, 988, DV 1-800-799-7233, and text
   START to 88788. Testid: `portal-crisis-strip` +
   `crisis-{call-911, dv-hotline, text-start, 988}`.

2. **First-Visit Safety Screen** — `SafetyScreen.jsx` renders as a
   modal gate the first time the parent taps either Door 1 or Door 2.
   Three questions (physical safety / coercion & control / device
   privacy). If any answer suggests risk → shows
   `safety-flagged-card` with hotline buttons + deep-link to
   `/safety-assessment` for the full clinical screen + a
   `safety-flagged-continue-btn` (never blocks a parent — clinical
   rule). Cleared → `sacoparents_safety_screen_ack = {cleared:true,
   flagged:false, date}` set in localStorage.

3. **Safety Retake Chip** — `SafetyRetakeChip` on the Parent Journey
   header, always visible. Purple pill when non-flagged, rose pill
   when flagged (reads "Safety concerns flagged — tap to re-check").
   Testid: `safety-retake-chip`.

4. **Soft Banner** — `SafetySoftBanner` renders at the top of
   AlignmentHub and BiffTab whenever the parent's last screening was
   flagged. Names the mismatch clearly (BIFF/Legal assumes both
   parents are safe) but never blocks the tool. Testids:
   `safety-soft-banner-{alignment|biff}` + hotline anchors.

**🟢 P1 — Passphrase + 7-Day TTL on Legal Report Shares**
- `ShareLegalModal.jsx` now surfaces a passphrase input + a 7-day /
  30-day toggle. Frontend passes `{passphrase, ttl_days}` to
  `POST /api/portal/share`; backend was already ready to accept them
  (from iter70 groundwork).
- Passphrase gate on `GET /api/portal/share/{id}.pdf`:
    * No `?p` → 200 HTML "Passphrase required" page (branded).
    * Wrong `?p` → 200 HTML gate + "did not match" error.
    * Correct `?p` → 200 application/pdf %PDF bytes.
- Backend response now includes `requires_passphrase` and `ttl_days`.

**🟢 P1 — Kudos Streak Badge**
- `computeKudosStreak(milestones)` in `portalStorage.js` counts
  consecutive UTC days ending today (or yesterday, ≤1 day gap)
  containing at least one `source: "biff_kudos"` milestone.
  Stale streaks (>1 day old) return 0.
- `DoorsGateway.jsx` renders `kudos-streak-badge` +
  `kudos-streak-count` when streak ≥ 2. Silent when streak < 2 to
  avoid celebrating single kudos events.

**Backend / frontend files edited**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — rewritten as
  container.
- `/app/frontend/src/pages/portal/SafetyCrisisStrip.jsx` (new).
- `/app/frontend/src/pages/portal/SafetyScreen.jsx` (new — exports
  `SafetyScreen`, `SafetyRetakeChip`, `SafetySoftBanner`).
- `/app/frontend/src/pages/portal/portalStorage.js` — added
  `SAFETY_ACK_KEY`.
- `/app/backend/tests/test_iter71_split_safety_passphrase.py` (new,
  13 tests) — passphrase gate states, TTL coercion, share types
  without gate, direct PDF endpoints, court-key verify.

**Verified**
- iter71 report: 13/13 backend + 100% frontend across all critical
  flows (safety gate first-visit, cleared, flagged, retake, soft
  banner on both tabs; passphrase mint + gate all three states;
  kudos streak with today+yesterday seed).
- No horizontal overflow at 390×844.
- Every legacy testid preserved after the split.

**Deferred (P2 — from iter71 review)**
- Tighten `ttl_days` pydantic constraint to `Literal[7,30]` so
  clients don't silently receive 30 when sending 14.
- Sync `sacoparents_safety_screen_ack` into portal_state so
  signed-in users on a new browser don't re-prompt.
- Extract Reassessment / Alignment modals from the container into
  their own components (container still at 1383 lines).
- Replace `_regenerate_share_pdf` smoke build with a lighter
  per-artefact payload validator.


### 2026-02-25 — Iter210 · Trend Line + BIFF Kudos Loop + Share Links

Follow-on batch to iter69. Ships three parent-facing features. All
three verified in iter70 (backend 10/10 new tests + frontend 100%).

**🟢 1. Trend Line (mini sparkline)**
- Reassessment records now snapshot the Health Index at the moment of
  logging: `{stage, notes, date, snapshot:{s1,s2,s3}, avg}`.
- Frontend: new `<TrendSparkline />` component renders under the
  Overall Health Index panel. Shows a compact SVG line chart of the
  last 4 reassessment averages + the current live value.
    * Empty state (< 2 data points): `trend-sparkline-empty` hint
      "Log at least one Reassessment above to unlock your trend line".
    * With ≥ 2 points: `trend-sparkline` + a delta chip
      `trend-delta` ("▲ +0.7", "▼ -0.3", or "◆ Flat").
- Backend: new `_draw_sparkline()` + `_reassessment_series()` helpers
  in `portal_pdf.py`. Weekly Progress PDF now includes a "Trend"
  section right under the Overall Health Index box with the same
  sparkline + a `6.0 → 6.5 → 6.7` textual legend.
- The reassessment array is now tracked in React state, hydrated from
  server, and included in the debounced PUT payload.

**🟢 2. BIFF Kudos Loop**
- `copyToneSafe()` now checks `riskLabel`. When it equals
  "Escalation Flag" at the moment of copy, it also appends a
  Success milestone:
    * `title`: "Coach kept a hot message tone-safe"
    * `note`: describes the reformulation
    * `source: "biff_kudos"` (so the milestone list can be filtered
      or badged if we ever want to)
- Silently no-op for Low-Risk drafts so the milestone log doesn't get
  cluttered with false wins.

**🟢 3. Share Links**
- New collection `portal_pdf_shares` (TTL 30 days).
- Endpoints:
    * `POST /api/portal/share` (public, rate-limited) —
      `{artefact_type: 'foundation'|'legal'|'weekly', payload: {...}}`
      → `{share_id, url, expires_at}`. Smoke-generates the PDF once
      to validate the payload before minting the link.
    * `GET /api/portal/share/{share_id}.pdf` (public) — regenerates
      the PDF on demand from the stored payload, streams as
      `application/pdf` with `Content-Disposition: inline` so it
      previews in-browser when texted. 404 on unknown, 410 on
      expired/revoked. Bumps `hit_count` on each fetch.
- Share URL origin is derived from the request scheme+host
  (`x-forwarded-host` if present), so preview/prod/custom-domain
  deploys all Just Work. Overridable via `PORTAL_SHARE_ORIGIN` env.
- Frontend: three new `share-*-btn` buttons (Foundation, Legal,
  Weekly). On click, POST /portal/share → write URL to clipboard →
  briefly show "Copied!" state. Alert shows the URL for users where
  the clipboard API is blocked.

**Deferred (P2 — from iter70 review)**
- Split `SacoparentsPortal.jsx` (~2200 lines) into per-tab
  sub-components.
- Add optional passphrase / short-TTL toggle to share links for
  privacy-sensitive legal reports.
- Replace `_regenerate_share_pdf` smoke build with a lighter
  per-artefact payload validator to avoid discarding a full weekly
  PDF on mint.
- Log the underlying error in `createShareLink`'s catch branch.


### 2026-02-25 — Iter209 · Signed BIFF Copy + Offline Retry + Weekly Progress PDF

Follow-on batch layering three concrete parent-facing utilities on top
of iter68's backend-connected portal. All three verified in iter69
(100% backend + 100% frontend).

**🟢 1. Signed BIFF Copy (Tone-Safe)**
- New button `copy-tone-safe-btn` (emerald pill) sits between "Copy
  BIFF" and "Archive" in the BIFF composer.
- On click, copies BIFF body + a 5-line audit stamp:
    ```
    <BIFF body>
    ---
    Refined via SA CoParents BIFF Coach
    Refined: 2026-02-25 14:32 UTC
    Case: ALIGN-SA-2026 (or "Self-Guided Parent Journey")
    sacoparentsapp.online
    ```
- Intent: attorneys/mediators can see the message went through the
  coach on a specific date, not that the parent hand-wrote a
  suspiciously calm reply.

**🟢 2. Offline Sync Retry**
- Added localStorage key `sacoparents_sync_pending` (value `"1"` when a
  PUT is queued).
- Debounced PUT effect now checks `navigator.onLine` before firing:
    * Offline → skip the PUT, set flag, chip shows "Offline — changes
      will sync when you're back".
    * Online but PUT fails → also set flag, chip shows "Sync paused —
      your work is safe locally".
    * Online and PUT succeeds → clear flag, chip shows "Synced as
      {email}".
- Auto-flush: on mount, if flag is set + online, bump internal
  `onlineTick` state → force the debounced PUT effect to re-run.
- Also listens on `window.addEventListener("online", ...)` to flush
  the moment connectivity returns without a page reload.

**🟢 3. Weekly Progress PDF**
- Backend: new `build_portal_weekly_progress_pdf()` in
  `portal_pdf.py` + endpoint `POST /api/portal/weekly-progress-pdf`
  (public — same tier as the other two portal PDFs).
- Renders a one-pager:
    * Header with 7-day period + case ref + parent name
    * Health Index (3 sliders + overall label) as horizontal
      progress bars
    * Milestones this week: two summary chips (success / friction) +
      bullet list. Falls back to the 3 most-recent milestones if none
      dated in the last 7 days.
    * Recent BIFF messages (top 5, with timestamp + category chip)
    * Foundation Statement excerpt (first 500 chars)
- Frontend: new button `export-weekly-progress-pdf-btn` in the BIFF
  hub under "History of Successes & Failures". Downloads a real PDF
  via `URL.createObjectURL` (same helper as Foundation/Legal).
- Copy: "One-page snapshot to share with your pediatrician, mediator,
  or attorney."

**New endpoints**
- `POST /api/portal/weekly-progress-pdf` — public, streams application/pdf.

**Deferred (P2 — noted from iter69 review)**
- Tighten `health_index` validation so `s1=0` returns 400 (currently
  coerces via `int(... or 5)`; slider min=1 prevents this in practice).
- Extract a shared `_draw_health_panel` helper between the legal
  report + weekly progress PDFs.
- Split `SacoparentsPortal.jsx` (now ~1940 lines) into per-tab
  sub-components.


### 2026-02-25 — Iter208 · Portal Backend Wire-Up (all 4 next-action items)

Turned the portal from a localStorage-only demo into a real
backend-connected app by shipping the four next-action items in one
batch. All 4 verified working end-to-end (iter68: 100% pass rate,
12/12 backend + 4/4 frontend flows).

**🟢 1. Wire To Backend (cross-device sync)**
- New collection `portal_state` (one doc per user, keyed by `user_id`).
- New endpoints:
    * `GET /api/portal/state` — hydrate signed-in caller's state
    * `PUT /api/portal/state` — upsert; caps arrays (500 records,
      milestones, biff_logs; 200 reassessments), clamps health index to
      1..10, truncates strings.
- Frontend: on mount, if `useAuth().user` exists, `GET /portal/state`
  and merge into localStorage (server wins). Every state change fires a
  debounced (~700ms) `PUT /portal/state`. Sync status pill on gateway:
  "Sign in to sync across devices" (anonymous) → "Synced as {email}"
  (signed in). Testids: `sync-chip`, `sync-signin-link`, `sync-status`.

**🟢 2. Real Key Verify**
- New collection `portal_court_keys` (hashed keys via sha256).
- Endpoint `POST /api/portal/court-keys/verify` returns
  `{verified, case_id, mediator_name, reason?}` — returns 200 with
  `verified:false` for unknown / expired / revoked keys so the UI can
  render an inline error rather than a network failure toast. Rate
  limited (40/hr per-IP, 800/hr global).
- Idempotent seed on backend startup writes the two demo keys the
  mockup ships with: `ALIGN-SA-2026` and `COURT-8842` — both map to
  "Matt Sossi, Licensed Mediator (San Antonio, TX)".
- Frontend court-key screen now shows inline `court-key-error` and a
  "Verifying…" state; verified banner uses the mediator name returned
  by the backend (not a hard-coded string).

**🟢 3. Server PDFs**
- New module `portal_pdf.py` with two builders:
    * `build_portal_foundation_pdf(foundation_text, case_ref, author_name)`
    * `build_portal_legal_report_pdf(health_index, foundation_text, signatures, matrix, case_ref)`
- Both use `fpdf2` with the mockup's purple palette (deep #4A1A6E,
  accent #6D28D9, wash #F4EFFF). Legal Report renders the 3 slider
  scores as inline progress bars, the Dispute Resolution Matrix as a
  table, and the signature lines with underline.
- New endpoints (public, no auth needed to keep the demo/gift path
  frictionless): `POST /api/portal/foundation-pdf`,
  `POST /api/portal/legal-report-pdf`. Both stream `application/pdf`
  with a `Content-Disposition: attachment` header.
- Frontend: two "PDF" buttons (`export-foundation-pdf-btn`,
  `export-legal-pdf-btn`) now trigger a real download via
  `URL.createObjectURL(blob)` — no more `window.print()`.

**🟢 4. Coach AI (BIFF)**
- New module `portal_ai.py` with `refine_biff(raw_message)` calling
  Claude Sonnet 4.5 via `emergentintegrations.llm.chat.LlmChat`, pinned
  to the "claude" tone. Prompt enforces BIFF style + strict JSON output
  `{biff, flags, risk}`, layered on top of the shared
  `SAFETY_GUARDRAIL` from `ai_service`.
- Endpoint `POST /api/portal/biff-refine` — public, rate limited
  (40/hr per-IP, 800/hr global), 502 on provider failure so the UI can
  fall back to local regex.
- Frontend: typing into `raw-input` fires an instant local-regex analysis
  (unchanged) AND a debounced (~900ms) Claude call. A
  `biff-loading` chip shows "Coach refining…" while Claude works.
  When it returns, `biff-output`, `flag-list`, and `risk-badge` all
  update with Claude's tailored rewrite. Presets also trigger an AI
  refine so the demo copy stays fresh.

**Backend files added**
- `/app/backend/portal_routes.py` (7 endpoints + startup seed)
- `/app/backend/portal_ai.py` (Claude BIFF refiner)
- `/app/backend/portal_pdf.py` (Foundation + Legal Report PDFs)
- `/app/backend/server.py` (imports `portal_router`, seeds keys)

**Frontend files edited**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — imports `useAuth`
  and `api`; new hydrate-from-server effect, debounced PUT effect,
  Claude BIFF integration, PDF download handlers, sync chip, inline
  court-key error, dynamic mediator name in the verified banner.

**Verified**
- iter68 report: 12/12 pytest cases + 4/4 Playwright flows pass.
- Claude output confirmed non-local (sample: "Thanks for coordinating.
  I would appreciate it if we could both aim to be on time for
  pickups…" for input "You were late again! You have zero respect.").
- Sync chip flips from "Sign in to sync across devices" to
  "Synced as parent1@test.com" after `POST /api/auth/login`.

**Deferred (P2)**
- Split `SacoparentsPortal.jsx` (~1500 lines) into per-screen
  sub-components for maintainability.
- Move rate limiter off in-memory to Mongo/Redis for multi-worker.
- Consider issuing court keys via a mediator admin route (currently
  only seeded via startup).


### 2026-02-25 — Iter207 · Full Portal Rewrite (SacoparentsPortal)

The user provided a complete HTML/Tailwind mockup for a mobile-first
"Child-Centered Co-Parenting Portal" and chose **option 1a: full
rewrite** — replace the primary user-facing experience.

**🟢 New primary experience at `/`**
- `Landing.jsx` moved to `/legacy`; `/` and `/dashboard` now render
  `SacoparentsPortal.jsx`.
- Single-page portal with three screens (gateway → parent-journey /
  court-key) driven by `useState` and persisted to **localStorage**
  (matches mockup design; **no backend hooks**).
- Font Awesome 6.4.0 CDN added in `public/index.html`.
- All backend routes (`Complete Alignment Report`, `Joint Report`,
  `Foundation Statement PDF`, `Coach Demo`, integration endpoint for
  `sacoparentsalign.com`) remain intact and untouched for the sibling
  Align app.

**LocalStorage keys**
- `sacoparents_biff_logs`, `sacoparents_align_records`,
  `sacoparents_milestone_logs`, `sacoparents_foundation_statement`,
  `sacoparents_legal_report`, `sacoparents_health_index`,
  `sacoparents_court_key`, `sacoparents_reassessments`.

**Modules implemented**
- Gateway with Door 1 (Self-Guided Parent Journey) and Door 2
  (Court Ordered Path — professional-key entry via `sacoparentsalign.com`).
- Court key verify screen with two demo keys (`ALIGN-SA-2026`,
  `COURT-8842`) and persistent verified banner.
- Hub tabs: **I. Legal Report & Alignment** and **II. BIFF & Success History**.
- Official Legal Conflict Resolution Report card with 3 Health Index
  sliders (Info Sharing, Handoff Predictability, Decision-Making
  Collaboration) computing an Overall Co-Parenting Health Index
  (Low / Moderate / High Alignment).
- Legal Dispute Resolution Matrix table.
- Digital Affirmation & Certification signatures (Parent A, Parent B,
  Mediator).
- Align Before Agreement records — Medical / Educational / Psychological
  folders with counters, filter, add-record modal.
- Foundation Statement textarea with save-to-localStorage.
- BIFF Communication Builder with 4 scenario presets (Late Handoff,
  Reimbursement, Schedule Swap, Medical Update), real-time tone risk
  analysis (flags 'always'/'never'/'!!'), archive to history.
- History of Communications + History of Successes & Failures with
  Log Milestone (prompt+confirm).
- Reassessment modal with milestone-stage + notes.
- Bottom mobile nav (Doors / Report / BIFF Tool / PDF Export).
- Export PDF button uses `window.print()` and print-only header/footer.

**Testids** (major): `sacoparents-portal`, `door-parent-journey`,
`door-court-path`, `screen-court-key`, `court-key-input`,
`demo-key-1`, `demo-key-2`, `verify-court-key-btn`,
`screen-parent-journey`, `court-verified-banner`, `verified-case-id`,
`hub-tab-alignment`, `hub-tab-biff`, `hub-section-alignment`,
`hub-section-biff`, `score-slider-1/2/3`, `score-val-1/2/3`,
`overall-health-label`, `log-reassessment-btn`, `sig-parent-a/b`,
`sig-mediator`, `save-legal-report-btn`, `add-alignment-btn`,
`folder-medical/educational/psychological`,
`count-medical/educational/psychological`, `clear-folder-filter`,
`alignment-records-grid`, `foundation-text`, `save-foundation-btn`,
`raw-input`, `risk-badge`, `flag-list`, `biff-output`, `copy-biff-btn`,
`archive-biff-btn`, `biff-history-list`, `success-count`,
`friction-count`, `milestone-history-list`, `add-milestone-btn`,
`modal-reassessment`, `submit-reassessment-btn`, `modal-alignment`,
`align-category/title/provider/date/summary`, `submit-alignment-btn`,
`bottom-nav`, `nav-doors/report/biff/print`, `header-back-btn`,
`export-pdf-btn`.

**Test verification**: iter67 (frontend) — 100% pass across 15 flows;
Font Awesome 6.4.0 renders; localStorage persistence confirmed across
reloads; no horizontal overflow at 390×844; desktop renders as
centered narrow column (intentional per mockup).

**Preserved but no longer primary**
- Old `Landing.jsx` accessible at `/legacy`.
- All existing legacy pages (`Dashboard`, `SafetyAssessment`,
  `CompleteAlignmentReport`, `JointProfessionalReport`, deep-dive
  pages, admin pages, verify pages, etc.) still routed for
  direct/deep-link access and for the sacoparentsalign.com sibling
  integration flows. They are **not linked** from the new portal.


### 2026-09-20 — Iter206 · Coach Demo · Custom Prompt Slot + Before-After Strip

Follow-on polish to iter205's Landing-page Coach demo.

**🟢 Custom Prompt Slot (empty-state composer)**
- Empty state no longer forces visitors to pick one of the 4 starters;
  a full-width textarea labelled "Or in your own words" now sits in
  the chat viewport with a purple→teal "Ask the Coach" button.
  Placeholder: "e.g. My co-parent keeps changing plans last-minute
  and my daughter is left waiting…". Same 600-char cap + rate limits
  as the follow-up composer.
- Mobile empty state gets both: the custom textarea at the top, then
  an "Or try one" starter list beneath it.
- Testids: `coach-demo-empty-composer`, `coach-demo-empty-input`,
  `coach-demo-empty-send-btn`.

**🟢 Before / After Strip (social proof of tone)**
- New `<BeforeAfterStrip />` under the demo panel, three
  side-by-side cards on desktop and stacked on mobile.
- Each card: scenario title (e.g. "Late pickup, third week in a
  row") + a warm-red "Draft (activated)" bubble (the raw activated
  message a parent might otherwise send) + a soothing-teal
  "Coach-refined" bubble (the BIFF-style rewrite).
- Framed honestly as "Real-world reframes / See the tone shift" +
  footer "Illustrative examples · names changed · no real messages
  included." — deliberately NOT presented as user testimonials.
- Testid: `coach-demo-before-after-strip`,
  `coach-demo-before-after-card-{0..2}`.
- Content is in a `BEFORE_AFTER_EXAMPLES` constant at the top of
  CoachDemoSection.jsx — easy to swap in real user-approved
  examples later without touching layout.



### 2026-09-20 — Iter205 · Landing Page Communication Coach Live Demo

**🟢 Feature — Interactive AI Coach preview on Landing**

- New backend module `/app/backend/coach_demo_routes.py` — public,
  unauthenticated slice of the real Coach.
    * `GET  /api/coach/demo/starters` — 4 curated marketing-friendly
      prompts (last-minute visit cancel, new-partner heads-up, chronic
      lateness, pre-mediation anxiety).
    * `POST /api/coach/demo/reply` — calls the SAME
      `ai_service.generate_coach_reply` used by the signed-in Coach at
      `/coach`; passes `history=[]` (stateless demo).
- **Rate limits (in-memory sliding window):** 10 msgs / IP / hour,
  400 msgs / platform / hour, 6 turns max per transcript, 600-char
  user message cap. Zero DB writes.
- **Frontend:** new `<CoachDemoSection />` (`/app/frontend/src/components/CoachDemoSection.jsx`)
  mounted on Landing between `<EcosystemFlow />` and `<AlignmentPhilosophy />`.
  Two-column desktop layout (starters rail + chat viewport), single
  column on mobile. Real-time chat bubbles with `react-markdown`
  rendering of Claude's BIFF-structured replies. Follow-up chips
  clickable to continue the exchange. On safety_flag → sign-up CTA
  card (routes to `/register`) instead of composer. On cap → same
  CTA. "Nothing here is saved" copy + Lock icon prominent in the
  header.
- **Verified live:** cold-hit reply ~4 s; markdown bold in brand
  purple; zero horizontal overflow at 1920px and 390px viewports;
  starters + composer + follow-ups + sign-up CTA all render;
  suggested_followups + safety_flag both propagate to the UI.



### 2026-09-18 — Iter204 · Empty-State CTAs + Bundle Download + Sample Deep-Dives + Re-seed Shares

Iteration_65 · **backend 100% (13/13 passed, 1 skipped) · frontend 100% (previous iter_64)**.

**🔴 P0 — Bundle Download (ZIP of every completed PDF)**
- New module `/app/backend/bundle_routes.py`. Endpoint
  `GET /api/bundle/my-completed.zip` streams a `zipfile.ZipFile` into a
  `Response` (application/zip) with `Content-Disposition: attachment`.
- **Design**: in-process `httpx.ASGITransport` fans out to 8 static PDF
  routes + 1 lookup-first Safety Assessment. Forwards the caller's
  `Authorization` header + cookies verbatim so every builder sees the
  same auth state the parent would. Any sub-endpoint that replies
  404/409 is silently skipped and noted in a plain-text `MANIFEST.txt`
  at the ZIP root.
- **Readiness gate**: each catalog entry carries a `readiness_signal`
  bool. Two endpoints (`/pathway-report/preview/pdf` and
  `/complete-report/mine.pdf`) render placeholder PDFs even for a
  brand-new user, so their presence alone must NOT suppress the 409
  empty-state — flagged `False`. When `readiness_hits == 0` the
  endpoint returns HTTP 409 with a friendly nudge; the shared
  `downloadPdf` frontend helper turns that into a sonner toast with an
  "Open my dashboard" action button.
- **Frontend**: new `BundleDownloadButton` mounted inside
  `YourReportsCard.jsx` below the report list. Full-width purple→teal
  gradient, descriptive helper caption, uses `fetchPdfWithGracefulFailure`.
  Testids: `your-reports-bundle-download-btn`, `your-reports-bundle-download`.
- **Verified**: parent1 → 5 PDFs + MANIFEST (2MB ZIP). Fresh throwaway
  parent → HTTP 409 with the friendly message. Parent1 vs parent2
  bundles are byte-different (auth propagation confirmed).

**🔴 P0 — Empty-State CTAs (finish migration to `downloadPdf` helper)**
- Migrated 4 additional PDF-download pages from ad-hoc
  `fetch(${API}...)` + generic toast → `fetchPdfWithGracefulFailure`
  from `/app/frontend/src/lib/pdf.js`:
    * `CompleteAlignmentReport.jsx` (individual + joint variants)
    * `JointAgreement.jsx`
    * `JointProfessionalReport.jsx`
    * `PathwayReport.jsx`
- Extended `EMPTY_STATE_ROUTES` in `pdf.js` with 5 new prefixes so
  every migrated page's 404/409 produces a friendly toast + action
  button linking to the correct next assessment (or
  `/summary?tab=agreement` / `/safety-assessment` / `/dashboard`).
- Wrapper preserves the existing behaviour on 200 (blob → click
  download) and adds structured handling for 401/403/network errors
  via a compact toast fallback.

**🟠 P1 — Re-seed active deep-dive Compare shares (already done)**
- `/app/backend/seed_deep_dive_shares.py` — standalone idempotent
  script that revokes existing shares and creates one active share per
  pathway (edu/med/psych) between `parent1@test.com` and
  `parent2@test.com` with stable share_ids so QA / testing_agent can
  hit `GET /api/{edu|med|psych}-deep/compare/{share_id}/pdf` reliably.

**🟠 P1 — Sample Deep-Dive PDFs for Landing Tier-2 (already done)**
- `/app/backend/deep_dive_samples.py` builds public sample PDFs for
  Educational / Medical / Psychological deep-dive reports using the
  same `build_deep_dive_report` + `build_deep_dive_pdf` pipeline the
  real endpoints use.
- Routes: `GET /api/insights/samples/deep-dive-{pathway}.pdf` — public,
  no auth, 24h Cache-Control. Adds parity for the 4-card Tier-2 strip
  on the Landing page (previously only Tier-1 Core Reports had
  "View sample (PDF)" links).

**Tests**: `/app/backend/tests/test_bundle_iter204.py` — 13 new tests
(unauth 401, parent1 200 + valid PDFs, manifest lists skipped, fresh
parent 409, parent1 vs parent2 different bytes, all 8 PDF endpoints
respond, safety-assessment lookup chain). All pass.

**Documented next-step for platform ops** (unchanged from iter203):
custom domain wire-up for `sacoparents.com`, prod seed demo,
`CONSENT_ADOPTION_DIGEST_ENABLED=1` env.

**Deferred / intentionally not touched**: SAST warnings, CORS
deployment-scan warning, `test_iter194_cron_analytics_branding.py`
env-load flake.



### 2026-09-18 — Iter203 · Landing Ecosystem Clarity Refactor + Slideshow Image Fix

Feedback source: user reviewed the live sacoparentsapp.online and requested an
8-point structural/UX refactor to make the parent app read as a peer of Align
(not a sub-product), simplify the opener, and make the report hierarchy
explicit.

**🔴 P0 — Immediate content fixes**
- `GlobalCopyright.jsx`: changed the site-wide copyright line from
  "© 2026 sacoparentsalign.com" → **"© 2026 SA CoParents"** so the parent
  site no longer reads as a sub-product of Align.
- `Landing.jsx` Step 5 subtitle: renamed from "Complete Together, Separately"
  → **"Two Parents. Two Perspectives."** with updated body copy: *"Each parent
  completes their assessment separately. When appropriate, the perspectives
  can then be compared to identify areas of alignment and differences that
  need discussion."*
- New `NotAVerdictStatement` component: extracted the *"Not a verdict on
  who's right"* principle out of Step 6's body (where it was buried) into a
  standalone dark-purple hero block mounted between the Three Reports and
  Individual-to-Joint sections. Headline: **"SA CoParents doesn't decide
  which parent is right."** Selector: `[data-testid="not-a-verdict-statement"]`.

**🟠 P1 — Structural clarity**
- 6→4 situation picker: collapsed the flat 6-choice grid into 4 parent-needs
  groups (Co-Parenting, Communication, My Child's Needs, Safety). Underlying
  6-leaf routing preserved via `SITUATION_LEAVES` map; the Communication tile
  opens a lightweight sub-choice card (`situation-group-communication-subchoices`)
  with Communication-is-difficult and Ongoing-high-conflict leaves — the
  high-conflict clinical safety-adjacent path is fully preserved (safety
  banner still fires on that leaf). *"Preparing for mediation or court"* pulled
  out of the tile grid entirely — now a separate destination link
  (`situation-mediation-destination`) below the picker so it reads as a
  process choice, not a fifth substantive assessment category.
- Two-tier reports hierarchy: rewrote `ThreeReportsStrip` into two clearly
  labeled tiers. Tier 1 = "CORE REPORTS · INDIVIDUAL JOURNEY" (Co-Parenting
  Assessment, Foundation Statement, Child Needs Statement — unchanged). Tier
  2 = "WHEN YOUR CHILD NEEDS MORE SUPPORT" — 4 focused-assessment cards
  (Educational, Medical, Psychological, Special Needs 7-domain) inside
  `[data-testid="focused-assessments-tier"]`, each linking to its deep-dive
  route. Removes the ambiguity between "Child Needs Statement" and "Special
  Needs Assessment".

**🟡 P2 — Ecosystem story polish**
- New `EcosystemFlow` component mounted between `ProfessionalConnection` and
  `AlignmentPhilosophy`. Single vertical diagram with 4 stacked tiers
  connected by downward arrows: Individual Parent → Two Parents (Joint
  Alignment Report) → Professional (SA CoParents Align Review) → Next Step
  (mediation / agreement / therapy / educational-medical-psychological
  resource / other appropriate process). Selectors: `[data-testid="full-ecosystem-flow"]`,
  `[data-testid="ecosystem-tier-{individual|two-parents|professional|next-step}"]`.

**Slideshow image fix (parallel with P0-P2)**
- Root cause: the 5 WebPs in `/app/frontend/public/slides/` were 1600x900
  landscape canvases with 499px + 500px hard-edge dark-navy pillar boxes
  padding a 601x900 portrait art strip. When rendered with `object-cover
  object-center` in the 16:8 slideshow frame the pillar boxes dominated the
  visible area, so parents read the frame as "no image".
- Fix: batch-cropped all 5 WebPs to the actual art bounds (`crop(499, 0,
  1101, 900)` → 602x900 portrait) via PIL. Filenames preserved. Switched
  `DashboardSlideshow.jsx` from `object-cover` → `object-contain` so the
  frame's dark-purple gradient background now serves as the natural (soft)
  pillar backdrop — no more hard-edge pillar seams.
- Originals backed up to `/tmp/slides_backup/` in case the founder wants to
  revert.

**Testing** — frontend-only verification via testing agent (iteration_63):
51/52 assertions passed (98%). Zero UI bugs. Zero regressions on Path B,
reset flow, or existing situation-picker safety guardrails.


### 2026-09-17 — Iter202 · Slide-hide rules (safety + court-ordered)

**🟢 P1 — Hide inappropriate slides per situation**
- Extended `personaliseSlides.js` with `hiddenSlideKeys()` helper.
  Rules:
    * `situation="safety"` → hide **communication** + **foundation**
      slides (joint-oriented tools inappropriate when family
      violence present)
    * `courtOrdered=true`  → hide **situation** slide (they didn't
      come to explore, they came to comply)
- Edge case: `safety` + `courtOrdered` both fire → three slides
  hidden (situation, communication, foundation), and since the
  rotation target `foundation` was hidden, rotation is skipped.
  Result: `child-needs · relationship` only.
- DashboardSlideshow's Step counter + dot count already use
  `SLIDES.length` dynamically, so the UI adapts automatically to
  any subset (2 / 3 / 4 / 5 slides).

**Tests**: `test_iter201_slide_personalisation.py` extended with 5
new cases covering the safety hide, court-ordered hide,
safety+court edge case, `hiddenSlideKeys()` contract, and a
no-hides regression (every other situation returns full 5).
All 12 pass.

Verified end-to-end at desktop:
  A) safety-only → 3 slides
  B) court-only  → 4 slides (foundation first)
  C) both        → 2 slides, no rotation
  D) mediation   → 5 slides (communication first)

### 2026-09-17 — Iter201 · Personalised slide order + progress ring overlay

**🟢 P1 — Slide order personalisation**
- New pure helper `/app/frontend/src/lib/personaliseSlides.js` — no
  React, no side effects, fully unit-tested. Given the base 5-slide
  sequence and `{ courtOrdered, situation }`, rotates ONE slide to
  the front (never hides, never shuffles):
    * courtOrdered=true         → Foundation Statement first
    * situation="special-needs" → Identify child's needs first
    * situation="mediation"     → Strengthen communication first
    * else (safety, high-conflict, cooperate, difficult, unknown)
                                → default order (Assess situation first)
- `DashboardSlideshow` reads `localStorage.sacoparents_situation_choice_v1`
  and `localStorage.sacoparents_court_ordered_case_id` on mount and
  memoises the personalised sequence for the session so a re-render
  never shuffles under an active viewer.
- Verified live end-to-end: (a) default → "Assess your family
  situation" first, (b) case linked → "Commit to your Foundation
  Statement" first, (c) special-needs → "Identify your child's
  needs" first.

**🟢 P1 — Progress ring overlay per slide**
- New `useSlideProgress()` hook (`/app/frontend/src/hooks/useSlideProgress.js`)
  fetches `/api/dashboard/progress` + `/api/safety-assessment/me`
  once per session (module-scoped cache) and returns a boolean map
  keyed by slide key. Never throws — endpoint failure resolves to
  all-false so a missing progress endpoint doesn't fill the ring
  with false positives.
- New `ProgressRing` component inside `DashboardSlideshow.jsx`
  renders in the top-left of each frame:
    * `done=true`  → filled green (#186142) with white checkmark
    * `done=false` → soft white outline with a small dot
  Screen-reader label describes state. Pointer events pass through
  to the frame click.
- Mapping (documented in the hook):
    situation      → any recorded Safety Assessment
    child-needs    → dashboard/progress.child_needs_identified
    relationship   → dashboard/progress.foundation_completed
    communication  → dashboard/progress.communication_readiness ≥ 50
    foundation     → dashboard/progress.foundation_completed

**Tests**: `test_iter201_slide_personalisation.py` runs the pure JS
helper via `node --input-type=module` and locks 7 cases (default,
court-ordered wins over situation, each situation branch, safety
falls through to default, rotate-idempotency, base-set preservation).
All pass.

### 2026-09-16 — Iter199 · Two-variant bridge copy + safety-level personalisation + CTR A/B

**🟢 P1 — Mirror eyebrow into Safety Assessment cleared companion CTA**
- `/safety-assessment` "level ≥ 3" companion CTA now shows the same
  eyebrow as the Landing bridge: **"When you're ready to go further —
  no concerns about family violence"** (SafetyAssessment.jsx). Same
  language on both surfaces.

**🟢 P1 — Safety-Concerned variant on Landing + Safety Assessment**
- New "safe-path" card renders when the parent's most recent Safety
  level is 1 or 2. Eyebrow: **"When you're ready, on your own
  timeline — safe paths for when family violence is present"**.
- Routes to individual-only tools (safety plan + journal). Never
  surfaces joint-report CTAs to a concerned parent.
- Landing bridge: `data-testid="safe-path-card"` replaces the Joint
  Journey card. Safety Assessment: `data-testid="safety-concerned-cta"`
  renders when `result.level < 3`.

**🟢 P1 — Personalise by safety result client-side**
- New hook `useSafetyLevel()` (`/app/frontend/src/hooks/useSafetyLevel.js`)
  fetches `/api/safety-assessment/me` once (module-scoped cache),
  returns `{ level, status }` where `status ∈ {cleared, concerned,
  unknown}`. Never throws — endpoint failure resolves to `unknown`
  and consumers default to the historical baseline (cleared).
- `IndividualToJointBridge` component consumes the hook + renders
  the correct variant. `<section data-variant="cleared|concerned">`
  attribute makes the switch easy to assert in tests.

**🟢 P1 — Configurable via existing nudge-copy API + CTR tracking**
- New backend routes on the existing nudge-copy router:
  * `GET /api/public/nudge-copy/individual-to-joint-bridge`
    (public, no auth, two-variant payload with baked-in defaults)
  * `POST /api/admin/nudge-copy/individual-to-joint-bridge`
    (admin — merges cleared/concerned overrides + appends history
    per variant)
  * `POST /api/public/nudge-copy/individual-to-joint-bridge/track`
    (public, 204, writes `{variant, event, target}` to
    `nudge_copy_events` — no user_id association, anonymous only)
  * `GET /api/admin/nudge-copy/individual-to-joint-bridge/analytics`
    (admin — per-variant impressions/clicks/CTR roll-up)
- Frontend `useJointBridgeCopy()` hook fetches copy + exposes
  `trackImpression(variant)` (deduped per mount) and
  `trackClick(variant, target)`.
- Same-origin `cta_route` validator on the Pydantic model rejects
  `//evil.example.com/...` and any non-`/` path so a compromised
  admin can't redirect parents off-site.
- New admin editor page `/admin/bridge-copy`
  (`/app/frontend/src/pages/AdminBridgeCopy.jsx`) — two-variant
  editor with a live CTR analytics tile on top. Linked from the
  Admin Dashboard Consent tile CTA row.

**Tests**: `test_iter199_bridge_copy_variants.py` locks 12 cases
(defaults, single-variant update, off-site CTA rejection, history
row per variant, 204 track, unknown-variant 422, per-variant CTR
math, admin-analytics 401, frontend hook contract, Safety
Assessment testids). All pass.

### 2026-09-16 — Iter197 · Bundle templates, case completion nudges, deep-link recovery

**🟢 P1 — Professional bundle templates**
- New module `/app/backend/professional_bundle_templates.py`
  (mounted under `/api`). Owner-scoped CRUD:
  `GET /professional/bundle-templates`, `POST /professional/bundle-templates`,
  `DELETE /professional/bundle-templates/{id}`.
- 25-template cap per user, unknown assessment_type → 400,
  duplicates dedupe silently, ownership-mismatch → 404 (never
  confirms existence).
- Frontend `BundleTemplatesPanel` in `ProfessionalJointAlignmentNew.jsx`
  lists saved templates with Apply + Trash buttons. Below the
  additional-steps picker a "Save this bundle for reuse" prompt
  surfaces once at least one extra step is added.

**🟢 P1 — Case completion nudge sweep**
- New module `/app/backend/case_completion_nudge.py` with pure-async
  `send_case_completion_nudges(db)` + env-gated
  `case_completion_nudge_loop(app)` (idle unless
  `CASE_COMPLETION_NUDGE_ENABLED=1`). Registered on server startup.
- 5-day grace period from `accepted_at`, filters to REQUIRED steps
  the parent hasn't completed, dedupes per (case_id, parent_email)
  via `case_completion_nudges` collection. Legacy top-level
  `assessment_completed_at` counts as primary-lane completion.
- Email body lists exact incomplete assessments and deep-links to
  `/case/:caseId`. Never mentions the co-parent's status.

**🟢 P1 — Deep-link recovery**
- `ProtectedRoute` gained a `requireRealUser` prop. Applied to
  `/case/:caseId`. Unauth visitors now redirect to
  `/login?redirect=<current-path>` instead of getting silently
  promoted to a guest session (guests 403 on case lookups anyway).
- `Login.jsx` reads `?redirect=…`, allows same-origin relative
  paths only (`_safeRedirect` rejects absolute + protocol-relative
  URLs), and routes both password + demo sign-in to the target.
- Verified end-to-end: cookie-cleared visit to `/case/SA-DEMO01`
  → `/login?redirect=%2Fcase%2FSA-DEMO01` → post-login land on
  `/case/SA-DEMO01` (confirmed via smoke test).

**Tests**: `/app/backend/tests/test_iter197_bundles_nudge_deeplink.py`
locks 13 cases (owner scoping, dedupe, 25-cap, unknown-type 400,
5-day grace, single-shot nudge, required-only filter, env gate,
loop registration, safe-redirect helper). All pass.

### 2026-09-16 — Iter196 · Front Door restructure + multi-assessment case model

**🟢 P0 — Simplified opening dashboard**
- New `FrontDoorHero` component (`/app/frontend/src/components/FrontDoorHero.jsx`)
  mounted at the top of `/dashboard`. Two large decisive cards:
  **Starting on My Own → /situation** (purple) and **Court Ordered / Referred
  → /join** (teal). Plus a small "Already started? Continue My Assessment →"
  strip and a persistent amber "Were you ordered or referred?" banner
  linking to `/join`.
- Existing `FourCircleFrontDoor` still renders below the hero for parents
  who've already picked their path — nothing lost, just no longer the
  first thing every parent has to parse.
- The `<details id="more-tools">` "Explore all tools" block anchors the
  hero's "Continue My Assessment" button.

**🟢 P0 — /situation topic picker**
- New public route `/situation` (`/app/frontend/src/pages/Situation.jsx`)
  showing the four founder-spec topics: Co-Parenting, Communication,
  My Child's Needs, Safety / Family Violence — each routing directly
  into the appropriate pathway.

**🟢 P0 — /case/:caseId scoped court-ordered view**
- New protected route `/case/:caseId` (`/app/frontend/src/pages/CaseView.jsx`)
  showing ONLY the assessments assigned to the parent, split into two
  sections: **Required by Your Referral** (green pill when complete)
  and **Optional — Recommended by Your Professional** (teal). Legacy
  "Additional SA CoParents Tools" collapsed by default.
- Fetches `GET /api/joint-alignment/case/{case_id}` — new endpoint
  that returns a caller-scoped view: `me.steps` with per-step
  required/label/status/completed_at, plus the case-wide
  `assigned_steps` and public parent presence signals.
- Never surfaces co-parent answers — only their name + presence.
- Graceful error states for 403 (not on case), 404 (missing/expired),
  and network errors.

**🟢 P0 — Multi-assessment case model (backwards-compatible)**
- Case documents now persist an `assigned_steps: [{assessment_type,
  required}]` list. Primary lane is ALWAYS the first entry, always
  required; extras are validated + deduped via `_build_case_assigned_steps`.
- Legacy cases (no `assigned_steps` field) still work: `_normalise_assigned_steps`
  synthesises a one-item list from the top-level `assessment_type`
  on read, so downstream consumers see one consistent shape.
- `_case_public_shape` now exposes `assigned_steps` with human-friendly
  labels (`_ASSESSMENT_LABELS`) and per-parent status per step.
- `CreateCaseResponse` echoes `assigned_steps` so professional clients
  don't have to round-trip after creating a bundle.

**🟢 P0 — Professional multi-step assignment UI**
- New `AdditionalStepsPicker` component inside
  `/app/frontend/src/pages/ProfessionalJointAlignmentNew.jsx`.
  Under the primary assessment_type select, a professional can now
  check extra assessments and tag each **Required** or **Optional**
  via pill toggles. Payload includes `assigned_steps` when present.

**🟢 P0 — Court-ordered case badge**
- New `CourtOrderedCaseBadge` component reads
  `localStorage.sacoparents_court_ordered_case_id` (set by JoinCode
  after a successful manual-code link) and renders a persistent
  teal chip on the dashboard with a one-tap "Open case" link to
  `/case/:caseId`. Dismissible.

**Tests**: `/app/backend/tests/test_iter196_front_door_multi_step_case.py`
locks 10 cases (legacy compat, dedupe, unknown-type 400, /case/{id}
403/404/200, `me.steps` shape, POST response echo). All pass.

**Testing agent**: 14/14 backend + all frontend flows verified,
100% success rate. Only minor note (progress label semantics) —
non-blocking. No SAST/CORS drift.

### 2026-09-14 — Iter195 · Admin dashboard reminder-analytics tile


**🟢 P1 — Surface `compute_reminder_analytics()` on `/admin`**
- New `ReminderAnalyticsTile` React component in
  `AdminDashboard.jsx`, placed directly below the Consent
  Adoption tile so ops can eyeball reminder open + click rates
  without cURLing `/api/admin/alignment-reflections/analytics`.
- Renders a totals strip (Sent · Opens % · Clicks % · CTR of
  opens %) and a per-subject table with sent / open rate /
  click rate / CTR-of-opens for every subject the sweep has
  emailed. Empty-state (0 sent) prints an inline note.
- Fetches on mount alongside the other admin analytics calls
  but with an isolated `.catch()` — a failure here NEVER
  blanks the surrounding dashboard, the tile just hides.
- New test: `test_iter195_admin_reminder_analytics_tile.py`
  locks the endpoint contract (auth-gated, zeroed shape on
  empty DB, per-subject rows carry the four numbers the JSX
  reads). All 3 tests pass.
- Verified live at `/admin` (desktop 1920 + mobile 390):
  totals + per-subject table render with real reminder data
  (Co Parenting: 3 sent · 66.7% open · 33.3% click · 50% CTR;
  Communication: 1 sent · 0/0/0). No horizontal overflow from
  the new tile at 390px.

### 2026-09-14 — Iter194 · Cron + Analytics + Sample Personalisation

**🟢 P1 — Reminder scheduler cronned**
- New `alignment_reflection_reminder_loop(app)` — daily sweep,
  registered from `server.py::startup_log` alongside the existing
  weekly / consent-adoption loops.
- Gated behind `ALIGNMENT_REFLECTION_REMINDER_ENABLED=1`. When
  unset, the loop logs a single info line and idles — safe to
  register on every deploy. Verified in the boot log:
  `alignment_reflection_reminder_loop: ALIGNMENT_REFLECTION_REMINDER_ENABLED
  not set; loop idle`.
- Sweep interval defaults to 86400s; override via
  `ALIGNMENT_REFLECTION_REMINDER_SWEEP_SECONDS`.
- Boot-time offset of 600s so the reminder sweep doesn't collide
  with the Monday-morning consent digest sweep.

**🟢 P1 — Reminder analytics (open + click tracking)**
- New `alignment_reflection_analytics.py`:
  - `GET /api/insights/track/reminder-open/{rid}.gif` — 1x1
    transparent GIF, marks `opened_at` on the reminder row.
    First-touch wins; second open never overwrites the first.
  - `GET /api/insights/track/reminder-click/{rid}` — 302 redirect
    to `/alignment/reflect/{subject}`, marks `clicked_at`.
  - Both endpoints ALWAYS return 200/302 — bad rids fall through
    to safe defaults (subject picker for click, blank pixel for
    open) so a stale email link never dead-ends the co-parent.
  - `compute_reminder_analytics(db)` aggregates per-subject
    open/click rates + a total row. Percentages rounded to 1dp.
- Reminder module rewritten to record the reminder FIRST, embed
  the `_id` in the pixel + click-wrapper URLs, then send. If send
  fails, the placeholder row is rolled back so the next sweep can
  retry. HTML email carries the pixel; plain-text keeps a direct
  URL as fallback.
- New admin route `GET /api/admin/alignment-reflections/analytics`.

**🟢 P2 — Sample PDF personalisation for mediators**
- `coparenting_alignment_sample.build_sample_pdf_bytes(firm=..,
  primary_color=..)` — optional branding kwargs.
- Public route `/api/insights/samples/co-parenting-alignment-report.pdf`
  gains `?firm=` and `?primary_color=` query params.
  Invalid colours are silently dropped so a bad URL still returns
  a valid PDF. Branded variants get `Cache-Control: no-store`;
  unbranded stays cached 24h.
- New cover-page footer strip renders "PREPARED FOR / <Firm
  name>" in the branded accent colour. `_hex_to_rgb` helper
  handles #RGB and #RRGGBB, falls back to SA CoParents purple.
- `SampleCoParentingLanding.jsx` gains an inline mediator form:
  firm-name input, color picker + hex field, "Preview branded
  PDF" / "Reset" buttons. Once applied, a share URL row appears
  with a "Copy URL" button; the iframe + download button both
  update to use the branded URL.

**Tests** (`tests/test_iter194_cron_analytics_branding.py`) —
**13 new tests, all passing**:
- Scheduler loop imports cleanly + idles when env flag off; server
  registers the loop task at startup.
- Tracker pixel marks opened_at + returns real GIF89a bytes.
- Tracker pixel is first-touch only (second open doesn't overwrite).
- Tracker click 302-redirects with correct location + marks clicked_at.
- Both tracker endpoints handle malformed rids gracefully.
- Analytics aggregation computes correct per-subject rates.
- Sample PDF renders firm branding on cover; unbranded variant
  does NOT include the "PREPARED FOR" block.
- Invalid `primary_color` is silently dropped.
- Route honours branding params, sets no-store cache for branded,
  keeps 24h cache for unbranded.
- Reminder email HTML includes the tracking pixel + click wrapper.

**Cross-iteration regression**: **68 tests passing** across
iter190 → iter194 (full Joint Alignment Report + Reflections stack).


### 2026-09-14 — Iter193 · Dashboard tile + Sample landing + Reminder sweep

**🟢 P1 — Alignment Reflections dashboard tile**
- New backend `GET /api/alignment-reflection/my-progress` — one
  round-trip returns every subject's answered/total/updated_at.
- New `AlignmentReflectionsCard.jsx` component — 5-row subject list
  with per-subject progress bar + "Complete" badge when
  answered ≥ total. Safety row carries a red "DUAL-CONSENT" pill.
  Two CTAs at the bottom: "Open subject picker" + "Preview the
  sample report" (links to the new landing page).
- Slotted into `Dashboard.jsx` above the "Complete Alignment Report"
  tile so parents see the reflection funnel before the finished
  artefact.

**🟢 P2 — Public `/samples/co-parenting` marketing landing page**
- New `SampleCoParentingLanding.jsx` — public, no auth. Hero,
  three-highlight explainer, embedded PDF iframe preview
  (17-page sample rendered by the existing insights route), soft
  "Sign in" + "Start your own" CTAs. Bottom purple CTA card with
  a downloadable "share the sample with a co-parent" button and a
  safety-sensitive footer note. Renders cleanly at 1920 and 390
  viewports.
- Route added to `App.js` — `/samples/co-parenting`, unauthenticated.

**🟡 P1 — Reflection Reminder Sweep**
- New `alignment_reflection_reminder.py` — pure Python
  `send_reflection_reminders(db, stale_days=3, dry_run=True)` that:
  * Finds every reflection with `updated_at ≤ now - stale_days`.
  * Excludes safety-sensitive subjects (never nudges on Safety).
  * Excludes reflections with no completed answers (blank-save
    guard).
  * Resolves co-parents via ACTIVE `snc2_shares` / `compare_shares`
    (both share shapes handled).
  * Skips when the co-parent has ALREADY started that subject.
  * Skips when a reminder was already sent for the
    (target, coparent, subject) triple — idempotent.
  * Sends via the standard `email_service._send` path (Virtru →
    Resend fallback). Neutral copy that never names WHO completed
    first, keeps focus on the child.
  * Records every send in the new `alignment_reflection_reminders`
    collection.
  * Returns a structured `{ sent, skipped, candidate_count,
    sent_count, dry_run }` payload for admin inspection.
- New admin route `POST /api/admin/alignment-reflections/send-reminders`
  (dry_run defaults to True). Deployment ops owns cadence — no
  self-scheduling.

**Tests** (`tests/test_iter193_dashboard_sample_reminder.py`) —
**7 tests all passing**:
- `/my-progress` returns all 5 subjects in locked order, reflects
  saved answers, requires auth.
- Reminder sweep finds stale reflection + skips safety.
- Sweep skips when co-parent has already started that subject.
- Sweep is idempotent — a second call after a real send finds
  "already_sent" and skips.
- Admin reminder route requires admin (403 for regular users).

**Cross-iteration regression**: **55 tests passing** across
iter190 / iter191 / iter192 / iter193 (Joint Alignment Report full
stack). Frontend renders clean at desktop + mobile viewports.


### 2026-09-14 — Iter192 · Multi-Subject Reports + Sample PDF

**🟢 P1 — 5 subjects with subject-scoped prompts + safety-sensitive routing**
Reflection-prompt engine now covers **General Co-Parenting** +
**Communication** + **Medical** + **Educational** + **Safety** on
top of the same 6-prompt shape.

- **Questions module** (`alignment_reflection_questions.py`):
  - New `_prompts()` helper generates subject-scoped label / prompt /
    placeholder / help text while keeping the 6 prompt IDs stable so
    the analysis engine stays subject-agnostic.
  - `SUBJECTS` registry gains 4 new entries. Safety is marked
    `sensitive: True`; every other subject is `sensitive: False`.
  - New `is_sensitive_subject()` helper.
- **Routes** (`alignment_reflection_routes.py`):
  - New `GET /alignment-reflection/subjects` (public) — subject picker
    payload including `sensitive` flag and prompt count per subject.
  - `POST /{subject}/compare` for **Safety** now returns **HTTP 428
    Precondition Required** unless the request body explicitly sets
    `safety_dual_consent_acknowledged: true`. The flag never
    persists — every safety compare is a fresh deliberate ceremony.
- **Joint-agreement guard** (`joint_agreement_routes.py`):
  - `_load_reflection_answers` short-circuits when the requested
    subject is sensitive — Safety reflections are NEVER auto-merged
    into the joint agreement / alignment report, even if a caller
    accidentally passes `subject="safety"`.
- **Frontend**:
  - New `AlignmentSubjects.jsx` page at `/alignment/subjects` — hero
    + 5-card grid + safety-sensitive footer + sample-PDF preview link.
    Safety card gets the red "DUAL-CONSENT ONLY" badge and a red
    accent gradient. Renders cleanly at 1920 and 390 viewports.
  - Route added to `App.js` (JWT-gated).

**🟢 P2 — Public sample PDF at `/api/insights/samples/co-parenting-alignment-report.pdf`**

- New `coparenting_alignment_sample.py` — fictional Alex R. + Sam R.
  co-parenting Maya (age 9). Populates all 5 merged sections + all 6
  reflection prompts with realistic partial-overlap answers so the
  sample surfaces a genuine mix of Strong / Moderate / Needs
  discussion + real "Both parents mentioned 'consistent, expectations'"
  bullets.
- Sample PDF is rendered through the SAME `build_joint_agreement_pdf`
  code path a real merger uses — any future PDF change flows
  automatically. Output: **17 pages, ~1 MB**, cache-controlled
  `max-age=86400`.
- Route added to `insights_routes.py` next to the existing
  `/samples/joint-alignment-preview.pdf`. Verified live via curl on
  the preview URL.

**Tests** (`tests/test_iter192_multi_subject_and_sample_pdf.py`) —
**17 new tests**, all passing:
- Subject registry order + 6-prompt-ID lock across all 5 subjects
- Only Safety is sensitive; Safety blurb mentions dual-consent
- `/subjects` endpoint exposes every subject + `sensitive` flag
- Schema endpoint works for every new subject
- Safety `/compare` returns 428 without the dual-consent flag, 200 with
- Non-sensitive subjects DO NOT require the safety flag
- `_load_reflection_answers` refuses to load Safety even given a fake
  DB that would raise on access (safety guard runs BEFORE the DB call)
- Sample PDF module produces valid `%PDF-` bytes, correct size, all
  10 section headings + reflection-driven blocks present
- Route serves PDF bytes with cache headers, no auth required

**Full regression**: **204 passed / 4 skipped** across joint /
agreement / alignment / iter191 / iter192 test surface.


### 2026-09-14 — Iter191 · Free-Text Reflection Prompts (Phase 1)

**🟢 P1 — Six sacoparentsalign-style prompts for General Co-Parenting**
Parents can now write free-text reflections on 6 prompts (Primary
Need / What's Working / Concerns / Desired Improvements / Options /
Other Parent's Likely Concerns). When both parents complete the
reflection, the Joint Alignment Report gains verbatim "Both parents
mentioned 'consistent, expectations' when describing..." bullets on
§2 and per-prompt side-by-side quotes on §3.

- **Backend**:
  - New `alignment_reflection_questions.py` — locks the 6 prompt IDs,
    labels, help text, placeholders, and 600-char limits.
  - New `alignment_reflection_analysis.py` — deterministic keyword
    overlap engine. Stopword-filtered token intersection; short
    answers (<=3 words) surface verbatim; child's name is stripped so
    "Both parents mentioned 'maya'" never happens.
  - New `alignment_reflection_routes.py` mounted at
    `/api/alignment-reflection`:
    - `GET /schema/{subject}` (public, no auth)
    - `GET /{subject}/mine` (caller's saved answers)
    - `PUT /{subject}` (upsert; unknown prompt IDs dropped server-side
      to prevent client-side prompt spoofing)
    - `POST /{subject}/compare` (dual-consent — returns
      `waiting_on_coparent` until BOTH have saved; 409 if the caller
      has not answered)
  - `joint_agreement.build_joint_agreement` gains optional
    `reflections_a` / `reflections_b` / `child_name` params. When
    both sides submit, the alignment_report payload gains a
    `reflection_analysis` block. Dual-consent guardrail: NEVER
    emitted when only one parent has answered.
  - `joint_agreement_routes` fetches both parents' reflections
    alongside their agreement drafts and pipes them through.
  - `joint_agreement_pdf` renders two new bullets:
    - §2 "Shared themes from your reflection prompts" — verbatim
      "Both parents mentioned 'X' when describing..." bullets
    - §3 "Reflection quotes — in each parent's own words" — two-
      column strip with each parent's verbatim answer (capped at
      320 chars per side to avoid pushing §4 off the page)
- **Frontend**:
  - New `AlignmentReflection.jsx` at `/alignment/reflect/:subject`
    (JWT-gated). Six textarea cards with label, prompt, help hint,
    live character counter, autosave 800ms after the last keystroke,
    Ctrl-S also saves. Progress pill ("N of 6 answered") + explicit
    Save button + last-saved timestamp.
  - Route added to `App.js`. Testids on every field and button so
    Playwright / testing-agent can drive the form.
- **Data model**: new `alignment_reflections` Mongo collection with
  `{user_id, email, subject, answers:{prompt_id: str}, updated_at,
  created_at}`. Answers are stored verbatim and truncated to 600
  chars server-side per prompt.
- **Tests**: `tests/test_iter191_alignment_reflection.py` — 17
  tests covering (1) question bank contract, (2) analysis engine
  behaviour spec (overlap, short-answer verbatim, empty-safe, child-
  name stripping, differ-row scaffolding), (3) API CRUD, (4)
  compare dual-consent (waiting / 409 / ready states), (5)
  `build_joint_agreement` reflection wiring, (6) PDF rendering of
  shared bullets + verbatim quotes. All pass. Wider joint/alignment
  regression: 186/187 passing (unrelated iter183 test-ordering flake).

**Deferred to Phase 2**:
- Multi-subject reports (Communication / Medical / Educational /
  Safety) — same 6-prompt shape, new subject definitions in the
  questions module + subject picker on the frontend.
- Safety-sensitive routing — never joint-share Safety reflections
  without dual-consent, mirroring sacoparentsalign's guardrail.
- `/samples/co_parenting/pdf` public sample with fictional reflection
  data.


### 2026-09-14 — Iter190 · Joint Alignment Report Refactor

**🟢 P0 — "Step One - Alignment Before Agreement" 10-section flow**
Retitled and restructured the Joint Co-Parenting Agreement Draft to
match sacoparentsalign.com's Joint Alignment Report. Same underlying
merger algorithm; new framing + new PDF flow + new derived data
blocks. Kept fully backward-compatible so consumers reading
`sections` / `parent_view` / `summary` are unaffected.

- **Framing** (`joint_agreement.py`):
  - `report_type` → `"joint_alignment_report"` (was `"joint_coparenting_agreement_draft"`)
  - `report_title` → `"Step One - Alignment Before Agreement"`
  - New `report_subtitle` → `"Joint Alignment Report"`
  - New `report_tagline` → neutral one-liner surfaced on frontend + PDF cover
  - `DISCLAIMER` reframed as "NEUTRAL MAP" while keeping the three
    legal caveats (not signed, not a court order, not custody advice)
- **Derived data** (new `alignment_report` payload block):
  - `alignment_map` — one row per merged section with `alignment`
    band (`strong` / `moderate` / `needs_discussion` / `not_enough_data`),
    both_count, total_count. Threshold arithmetic: ≥0.66 strong,
    ≥0.33 moderate, else needs_discussion.
  - `child_identified_needs` — derived from `child_needs` and
    `priority_items` `both_proposed` clauses, backfilled with 5
    SA CoParents neutral defaults so the section never renders sparse.
  - `potential_alignment` — near-miss pairs (similarity 0.30-0.60,
    below the 0.60 merge threshold) that a mediator's time is best
    spent surfacing. Greedy pairing, max 6 rows.
  - `possible_next_steps` — static 6-item list of neutral next steps
    (Continue Parent Discussion / Discuss With Mediator / etc.).
  - `closing_quote` + `closing_line` — powers the thematic closing page.
- **PDF flow** (`joint_agreement_pdf.py`):
  - Cover page: new title + subtitle + tagline + at-a-glance summary
  - Court-report disclaimer (unchanged)
  - §1 Purpose of This Report (framed as Step One)
  - §2 What Both Parents Agree About
  - §3 Where the Parents See Things Differently (side-by-side)
  - §4 Child's Identified Needs (bullet list)
  - §5 Alignment Map (colour-coded rows — green/amber/red/grey +
    both/total count in muted grey, legend row underneath)
  - §6 Areas for Conversation
  - §7 Options and Resources
  - §8 Potential Areas of Alignment (near-miss pairs)
  - §9 Questions for the Parents
  - §10 Possible Next Steps
  - Closing page: "Alignment Before Agreement" — thematic title,
    line, pull-quote with brand-purple left rule, SA CoParents
    tagline strip
  - Appendix A: Detailed Item Breakdown (kept for attorneys/mediators)
  - PDF running-header text updated to match new framing
  - **15 pages rendered** on a realistic fixture; every §1..§10
    heading + closing page + appendix land as expected.
- **Frontend** (`JointAgreement.jsx`, `JointAgreementShared.jsx`):
  - Error-state H1 → `"Step One — Alignment Before Agreement"`
  - Report H1 auto-flows from `d.report_title`
  - Eyebrow reads `d.report_subtitle || "Joint Alignment Report"`
  - Subline reads `d.report_tagline` with fallback copy
  - Shared-page provenance banner reframed as "Joint Alignment Report"
- **Tests**:
  - New `tests/test_iter190_alignment_report_structure.py` — 14
    tests locking payload contract (`alignment_report` keys,
    canonical section order, band vocabulary, threshold arithmetic)
    + PDF contract (every §1..§10 heading, closing page, appendix
    still present, new header framing). All pass.
  - Updated `tests/test_iter116_joint_agreement.py::test_disclaimer_present`
    from "draft for discussion" → "neutral map" phrase to match the
    reframed disclaimer.
  - Updated `tests/test_iter123_joint_agreement_share_link.py`
    `report_type` assertion → `"joint_alignment_report"`.
  - Updated `tests/test_iter126...` fixture `report_title`.
  - Full regression: **170 passed / 4 skipped** across the joint /
    agreement / alignment surface. Only pre-existing iter184 demo-case
    failures remain (unrelated to this change).

**Deferred to Phase 2:**
- Free-text reflection prompts (Primary Need / What's Working / etc.)
  — would require a new questionnaire + data migration.
- Multiple subjects (Communication / Medical / Safety / etc.) —
  currently one General Co-Parenting subject.
- `/samples/co_parenting/pdf` public sample of the alignment report.


### 2026-09-13 — Iter189i · Snapshot Export (Download PNG)

**🟢 P2 — Download PNG button on the Mobile preview frame**
Admins can snapshot the iPhone-framed preview and drop it straight
into Slack when discussing copy variants with the team.

- **Library**: `html-to-image@1.11.13` (~11 kB gzip, modern
  foreignObject-based rasterizer, works with Tailwind + gradients).
- **Trigger**: `Download PNG` pill button (Camera icon) rendered
  next to the Desktop/Mobile toggle. Only surfaces while
  `viewportMode === "mobile"` because Desktop mode is just a card —
  not a shareable artefact.
- **Ref target**: an inner `mx-auto` wrapper (width fixed at
  `414px`) that contains the phone bezel + notch + status bar +
  nudge card + the "iPhone · 390px viewport" caption. All rendered
  as one polished artefact.
- **Options**: `pixelRatio: 1` (standard resolution per user
  choice — small file, good for Slack), `backgroundColor: '#F6F4FA'`
  (soft page tone so the bezel doesn't float on transparency in
  light-theme Slack), `cacheBust: true`.
- **Filename**: `sacoparents-nudge-preview-YYYY-MM-DD.png` so
  multiple exports don't clobber each other in a Slack thread.
- **Toast**: success ("Downloaded — ready to drop into Slack.")
  and error ("Could not export the preview. Try again in a
  moment.") via `sonner`.
- **Testid**: `admin-nudge-copy-preview-download-png`.
- **Verified end-to-end**: real Playwright click triggered the
  download, PNG dimensions 414×771px, 175 kB — captures phone
  bezel, notch, status bar, nudge card, and caption. Existing
  `wordDiff.test.js` (6/6) still passes.


### 2026-09-13 — Iter189h · Mobile Preview Frame

**🟢 P1 — iPhone-shaped preview at 390px in `/admin/nudge-copy`**
Live preview now supports Desktop / Mobile viewport modes via a
segmented toggle above the preview column.

- **Frame**: pure-CSS iPhone chrome — 418px outer bezel (dark
  `#1A1330`, rounded-[3rem], p-3, shadow-2xl), Dynamic-Island
  notch (h-6 w-28 rounded-full bg-black), fake iOS status bar
  ("9:41" · "•••"), and a 390 × 720 inner screen. No image assets.
- **Toggle**: segmented pill above the preview
  (`admin-nudge-copy-preview-frame-toggle`) with
  `admin-nudge-copy-preview-desktop` (default, active on load)
  and `admin-nudge-copy-preview-mobile` buttons. Uses `Monitor` /
  `Smartphone` icons from lucide-react.
- **Layout safety**: preview column has `min-w-0` so the 418px
  phone frame does not widen its grid column at narrow admin
  viewports. Frame wrapper has `overflow-x-auto -mx-2 px-2` so
  it scrolls horizontally on very small admin screens (like the
  admin's own phone) instead of forcing horizontal page overflow.
- **Preview parity**: both modes render the same nudge markup so
  edits stay in perfect sync — desktop keeps the responsive
  `sm:` variants; mobile hard-codes the small-screen spacing
  because the container is fixed at 390px.
- **Verified**: 1920×1080 (Desktop toggle no overflow; Mobile
  toggle no overflow) and 390×844 (both toggles no overflow).
  Existing `wordDiff.test.js` still passes.


## What's Implemented
### 2026-09-13 — Iter189g · Word-Level Diff Highlighting

**🟢 P2 — LCS word-level diff on the Restore preview**
The Diff Card now highlights only the *changed words* instead of
formatting the whole string. Shared vocabulary stays visually
quiet so admins see the delta at a glance.

- **Algorithm**: classic O(n·m) LCS dynamic programming inline in
  `AdminNudgeCopy.jsx::wordDiff` (~30 lines, no new deps). Splits
  on `/(\s+)/` so whitespace tokens are preserved without their own
  highlighting. Fine for the input sizes (headline max 25 tokens,
  subhead max ~120 tokens).
- **Rendering**: new `DiffText` component renders one `<span>` per
  token. Removed words on the current side get red strikethrough
  + red-tinted background. Added words on the incoming side get
  bold + purple underline + purple-tinted background. Unchanged
  words are muted so the diff pops.
- **Legend row** below the two panels tells admins what the styling
  means (removed = red strike; added = bold+underline+purple).
- **Compares against current EDITOR state** not the server-side
  live copy — if the admin typed manual edits before clicking
  Restore, those edits are what the diff highlights against.
- **Memoized** via `useMemo` so the diff only recomputes when
  `pendingRestore` or the relevant textarea changes.

Direct algorithm verification via Node.js:
  - `"Would you like to send these highlights to your co-parent?"`
    vs `"Share these highlights with your co-parent?"`
    → shared `these highlights`, `your co-parent?` untouched; only
    the actual delta highlighted on each side.
  - Identical strings → zero false positives.
  - Empty current → every incoming word marked added.
  - Word-order changes → detected correctly.

### 2026-09-13 — Iter189g (part 1) · Diff Highlighter + Auto-Open Preview

**🟢 P2 — Two-step Restore with visual diff card**
Clicking Restore on any history row no longer clobbers the
editor immediately. Instead we surface a bordered "Restore
preview · Compare before you apply" card between the page
header and the editor grid:
  * **Current side** (grey, strikethrough) — what's in the editor now
  * **Incoming side** (bold, thick purple border) — the restored version
  * **Apply** loads the values into the textareas + pre-fills the
    Note with the audit reason
  * **Cancel** dismisses the diff card, editor state untouched
  * Restore note preview shown below the diff so admins see the
    exact string that'll land on the next Save's audit trail

- `pendingRestore` state in `AdminNudgeCopy.jsx` gates the swap.
- `applyPendingRestore` + `cancelPendingRestore` handlers make
  the intent explicit — accidental clicks no longer discard
  unsaved edits.
- Verified end-to-end via Playwright: diff card renders, all 4
  subcomponents (`current`, `incoming`, `cancel`, `apply`)
  visible with proper `data-testid` hooks.

**🟢 P2 — Auto-open `/preview.html` after send-test**
After a successful `POST /admin/consent-digest/send-test`, we
`window.open` the digest preview HTML in a new tab so admins
can compare inbox render vs source side-by-side without a
second click. Popup-blocker safe — falls back silently and
the toast tells the admin the preview was opened. The "Preview
digest" button on the tile is still one click away either way.

- Frontend-only change in `AdminDashboard.jsx::SendTestDigestForm`.
- Uses `noopener,noreferrer` for security.

### 2026-09-13 — Iter189f · Restore Note Prompt

**🟢 P3 — Prompt-on-Restore for a clean audit trail**
Clicking "Restore" on any history row now shows a `window.prompt`
asking why the admin is reverting. The reason auto-populates the
Note field so the next Save's history row carries a clear
"reverting because…" attribution. Prefilled suggestion is
`Reverting from: <prior note>` when the older entry had a note,
or `Reverting to prior wording` otherwise. Cancel = no state
change. Empty accept falls back to the prior note or the
suggestion so the note field is never blank on a restore.

- Frontend-only change to `AdminNudgeCopy.jsx::handleRestore`.
- No new backend endpoint or DB migration.
- Existing 31 iter189 tests still pass unchanged.

### 2026-09-13 — Iter189e · Copy History + One-Click Restore

**🟢 P2 — Append-only nudge-copy revision log**
Every admin save writes to a new `nudge_copy_history` collection
so an unsuccessful copy experiment can be undone without retyping.
Reset clears the live override but preserves the log — an admin
who resets and regrets it can still restore a prior version.

- New endpoint `GET /api/admin/nudge-copy/child-needs-share/history?limit=5`
  - Admin-gated (surfaces `updated_by` email).
  - `limit` bounded to 1-20 by Pydantic query param, defaults to 5.
  - Returns entries newest-first.
- `POST /api/admin/nudge-copy/child-needs-share` now appends a
  history row on every successful save (no truncation, append-only).
- `/reset` endpoint intentionally does NOT touch the history log.

**🟢 P2 — Recent versions panel on `/admin/nudge-copy`**
Below the editor + preview grid, a "Recent versions" card lists
the last 5 revisions with:
  - Truncated headline + 2-line subhead preview
  - Optional audit note
  - Relative timestamp (`3d ago`, `12h ago`, `just now`)
  - `updated_by` admin email
  - Small "Restore" button that populates the editor textareas
    without saving — admin still clicks Save to activate.
- Empty state ("No custom versions saved yet…") when the log is
  empty so an admin's first save is clearly attributed as v1.
- Save action refreshes the history list so the new row appears
  at the top with proper timestamp + attribution.
- Restore auto-scrolls the page to the editor so the textarea
  update is obvious.

**🧪 Pytest** `tests/test_iter189e_nudge_copy_history.py`
- 5 tests: admin gate on read, `limit` bounds (1-20 → 422), save
  appends exactly one row + newest-first ordering, default `limit=5`
  caps returned rows, reset preserves history rows.
- Combined suite (`test_iter189_*` × 5 files) = 31/31 pass in ~16s.

### 2026-09-13 — Iter189d · Copy Editor UI + Test-Recipient Digest

**🟢 P1 — `/admin/nudge-copy` editor page**
Two textareas (headline + subhead) with live character counters
that mirror the Pydantic 6-120 / 10-600 guardrails; a "Note" field
for the audit trail; and a live-preview card on the right that
renders the nudge exactly as parents see it on the SNCv2 report
page. Save writes via `POST /api/admin/nudge-copy/child-needs-share`
and immediately reflects in the preview + on the "showing defaults"
vs "custom override active" badge. Revert-to-defaults button calls
`.../reset` with a confirm dialog.

- New route: `/admin/nudge-copy` (React Router, protected)
- New component: `/app/frontend/src/pages/AdminNudgeCopy.jsx`
- Wired from AdminDashboard tile via a new "Edit nudge copy" link
  and the friction copy at the bottom of the consent tile.
- Uses only the existing endpoints from iter189c — zero new backend
  routes.

**🟢 P1 — Test-recipient digest send**
`POST /api/admin/consent-digest/send-test?to_email=you@example.com`
sends the exact Monday HTML to any email address with a `[TEST]`
subject prefix and a yellow banner injected at the top of the
body so it can't be mistaken for a real send. Never touches the
Monday dedupe row — verified by pytest that no
`consent_adoption_digest_sends` insert happens.

- Rebuilt via the same `build_admin_consent_adoption_digest_html`
  helper so preview / test / real send stay in lockstep.
- Rejects malformed recipients (regex + Pydantic-style validation)
  before hitting the mailer.
- Frontend surface on the consent tile — small email input +
  "Send test" button that fires the endpoint and toasts the result.

**🧪 Pytest** `tests/test_iter189d_send_test_digest.py`
- 4 tests: admin gate (401/403), invalid email rejection (422),
  valid recipient accepted (200/502/503 depending on mailer avail),
  and the crucial regression: **no dedupe row is written by the
  test send** — Monday's real digest is never blocked.
- Combined suite (`test_iter189_*` × 4 files) = 26/26 pass in ~11s.

### 2026-09-13 — Iter189c · Digest Preview + Weekly Sparkline + Copy Config + Slack Mirror

**🟢 P1 — In-browser digest preview**
`GET /api/admin/consent-digest/preview.html` renders the exact HTML
that would land in an admin's inbox on Monday, against CURRENT
live consent stats. Yellow "PREVIEW · not sent" banner prevents
screenshots from being confused with a real send. Does NOT touch
the mailer or write a dedupe row.

- Refactored the digest body into a pure builder
  `email_service.build_admin_consent_adoption_digest_html(stats,
  week_start, console_url) -> (subject, html, plain)` — the real
  send + preview endpoint both use this single source of truth.
- Preview button ("Preview digest") added to the Consent Adoption
  tile on `/admin` (opens in new tab).
- `Cache-Control: no-store` header prevents CDN caching of an old
  preview.

**🟢 P2 — 4-week retention sparkline on the admin tile**
`overview.consent.child_needs_share.nudge_dismisses.weekly_4w`
now returns 4 ISO-week buckets (oldest-first) with `{week_start,
first, permanent}` counts. Admin dashboard draws a tiny inline
SVG sparkline (ochre = retry-hides, plum = permanent) directly
under the tile grid. Falls back to "No dismisses in the last 4
weeks — nothing to plot yet." when every bucket is 0.

**🟢 P2 — Admin-editable nudge copy (soft A/B override)**
Not a full A/B framework — a manual override. Admin can tweak the
headline + subhead without cutting a build:

- `GET  /api/public/nudge-copy/child-needs-share` — public read.
- `POST /api/admin/nudge-copy/child-needs-share` — admin update.
- `POST /api/admin/nudge-copy/child-needs-share/reset` — revert
  to hardcoded defaults in one click.
- Payload validated by Pydantic (`headline` 6-120 chars, `subhead`
  10-600 chars) so an oversized string can't blow up the layout.
- `ShareChildNeedsNudge.jsx` fetches on mount, falls back to
  hardcoded defaults on any error so a backend hiccup never blanks
  the nudge.
- Copy stored in `nudge_copy_config` singleton with `updated_by`
  audit trail.

**🟢 P2 — Slack mirror on Monday digest**
When `SLACK_DIGEST_WEBHOOK_URL` is set, every successful email
dispatch also posts a compact summary to the Slack webhook (same
numbers, no verbatim answers). Wrapped so a Slack failure NEVER
blocks the email path. Uses `urllib.request` in an executor —
zero new dependencies.

**🧪 Pytest** `tests/test_iter189c_preview_and_copy_and_sparkline.py`
- 7 tests: preview requires admin, preview renders banner + digest
  body + no-store cache header, public copy returns defaults, admin
  can update + reset, oversized headline rejected (422), non-admin
  write rejected (403), weekly_4w has exactly 4 buckets ordered
  oldest-first.
- Combined suite (`test_iter189_*` × 3 files) = 22/22 pass in ~8s.

### 2026-09-13 — Iter189b · Nudge Dismiss Analytics + Consent Dashboard Tile

**🟢 P1 — Fire-and-forget dismiss event on `ShareChildNeedsNudge`**
Every ✕ click on a case tile now records a lightweight event so
admins can see whether the retry cadence actually converts hesitant
parents. Fires the SAME time the localStorage dismiss is written,
so first-time vs post-retry dismisses land in different buckets.

- **New endpoint** `POST /api/complete-report/joint/{case_id}/nudge-dismiss?is_retry_dismissal=true|false`
  - Membership-gated (same `_load_case_and_members` as the toggle
    endpoint) so callers can't spray events for cases they're not on.
  - 404 on unknown case (not 403) — preserves existence privacy.
  - Writes `{ user_id, case_id, is_retry_dismissal, created_at }`
    to a new `child_needs_share_nudge_dismisses` collection.
  - No PII beyond `user_id` (already known); no verbatim answers.
- **Frontend** — `ShareChildNeedsNudge.jsx::dismissCase` now fires
  the endpoint in parallel with the localStorage write. Errors are
  logged but non-fatal (dismiss must still succeed offline).

**🟢 P1 — Consent Adoption tile on `/admin`**
The AdminDashboard now surfaces the SAME numbers we ship in the
Monday digest — so admins can check the pulse without waiting for
Monday. Four sub-tiles: Parents opted in · Cases fully unlocked ·
Retry-hides · Permanent hides — each with a 7-day delta.

- **New response shape** `overview.consent.child_needs_share.nudge_dismisses`
  - `first_total`, `permanent_total`, `first_7d`, `permanent_7d`.
- **Copy hint** below the tile: "Rising permanent-hides with flat
  opt-ins means the retry cadence isn't converting hesitant parents.
  Consider softening the nudge copy." — directly actionable.
- **data-testid** attributes: `admin-consent-tile`,
  `admin-consent-parents-tile`, `admin-consent-cases-tile`,
  `admin-nudge-first-tile`, `admin-nudge-permanent-tile`.

**🧪 Pytest** `tests/test_iter189_nudge_dismiss_endpoint.py`
- 6 tests: first dismiss, retry dismiss, auth required, 404 on
  unknown case, 422 on malformed case_id, admin overview shape.
- Combined with `test_iter189_consent_adoption_digest.py` = 15/15
  pass in ~4s.

### 2026-09-13 — Iter189 · Consent Adoption Digest + Nudge Retry Cadence

**🟢 P1 — Weekly admin digest for Child-Needs consent adoption**
Every Monday morning (America/Chicago 09-11), a rollup email lands
in every `ADMIN_EMAILS` recipient's inbox summarising Child-Needs
share-consent adoption: cumulative parents opted in, cases where
both parents have unlocked Section 5, unlock rate %, plus 7-day
deltas so friction shows up in-inbox before it becomes a support
ticket. Aggregate telemetry only — no parent names or verbatim
answers ever ship.

- **New sweep** `/app/backend/consent_adoption_digest.py`
  - `_compute_consent_stats()` — pure fn used by the digest and
    testable in isolation. Mirrors the aggregation in
    `analytics_routes.py` and adds 7-day deltas.
  - `send_consent_adoption_digest()` — Monday-only send window
    (Chicago 09-11), dedupes per `(admin_email, ISO-week)` via
    `consent_adoption_digest_sends` collection, short-circuits with
    `no_baseline_activity` when nobody has consented yet (skips the
    "0/0 unlocked" inbox noise before feature has data).
  - `consent_adoption_digest_loop()` — idle no-op unless
    `CONSENT_ADOPTION_DIGEST_ENABLED=1` (safe to always register).
- **New email template** `email_service.send_admin_consent_adoption_digest`
  - Branded HTML + plain-text with 2-tile stat grid, "this week"
    delta pill, aggregate-only reassurance in the footer.
- **New admin route** `POST /api/admin/consent-digest/run-now`
  - `dry_run=true` (default) records the dedupe row + returns stats
    without sending. `dry_run=false` emails all `ADMIN_EMAILS` real.
  - Bypasses the Monday send window so admins can smoke-test.
- **Wired into `server.py`** startup — the loop registers alongside
  the other Monday sweeps and idles silently by default.

**🟢 P2 — Nudge retry cadence on `ShareChildNeedsNudge`**
Case tiles now carry a per-tile ✕ dismiss. A dismissed tile hides
for exactly 7 days, then reappears **once** so hesitant parents
get a gentle second chance. If they dismiss it a second time we
honour that and hide it permanently (`retried=true`). Granting
consent (checking the box) clears the dismissal entirely so the
retry cycle resets cleanly. State lives in localStorage under
`snc2.childNeedsShareNudge.dismissed` — no server round-trip, no
privacy footprint.

**🧪 Pytest** `tests/test_iter189_consent_adoption_digest.py`
- 9 tests: pure-fn stat computation (both/one/none consent cases +
  7-day deltas), send window (Monday CT only), week-start
  Monday-rollback, dry-run + dedupe write, second-admin dispatches
  after first is deduped, outside-window skip, no-recipients skip,
  no-baseline-activity skip (hermetic via ephemeral DB).
- All 9 pass in <1s.

### 2026-09-11 — Iter188 · Onboarding Nudge (Post-Child-Needs Consent Prompt)

**🟢 P2 — Post-completion Child Needs share nudge**
When a parent finishes their Child Needs Statement and lands on the
report page, they now see a friendly card immediately below the
"please review before sharing" notice: "Share these highlights with
your co-parent's joint report?" — with a per-case toggle so they can
grant consent while the context is freshest.

- **New backend endpoint** `GET /api/complete-report/my-active-cases`
  returns the caller's joint cases with `coparent_name`,
  `my_consent_at`, and a boolean `coparent_has_consented` (never the
  co-parent's raw timestamp). Cap 20, sorted most-recent-first.
- **New frontend component** `ShareChildNeedsNudge.jsx`. Returns
  null when the parent is on zero joint cases (no empty prompt).
  Uses the existing `POST /complete-report/joint/{case_id}/consent/child-needs`
  endpoint — no second consent surface, so all iter187 dual-consent
  guarantees still apply.
- **Wired** into `SpecialNeedsV2Report.jsx` between `ReportReviewNotice`
  and the cache-header row.
- **Tests** — 2 new pytest cases (endpoint shape + auth gate).
  All 13 iter184 tests green.


## What's Implemented
### 2026-09-11 — Iter187 · Dual-Consent Child Needs Share + Ops Hardening

**🟢 P1 — Dual-consent gate on Child Needs highlights**
Founder-approved strict policy (Iter186): parents' Child Needs excerpts
are stripped from the joint Complete Alignment Report view by default.
Iter187 adds the mechanically-enforceable ESCAPE HATCH so co-parents can
selectively opt-in without a privacy incident.

- `complete_alignment_aggregator.py::aggregate_for_case` now takes a
  `preserve_fields` tuple. `_scrub_for_joint_view` allowlists any lane
  field in that tuple through the scrub — everything else stays stripped.
- `complete_alignment_report_routes.py::_preserve_fields_for_case`
  inspects `parents[i].child_needs_share_consent_at` on the case doc.
  Returns `("highlights",)` ONLY if BOTH parents' timestamps are set.
- `POST /api/complete-report/joint/{case_id}/consent/child-needs`
  idempotent toggle — records / clears the caller's own consent-at
  timestamp. Returns `{my_consent_at, unlocked}` so the frontend can
  show "Waiting on co-parent" / "Both consented · unlocked" without a
  second round-trip.
- `GET /api/complete-report/joint/{case_id}` now returns a
  `my_consent.child_needs` sub-doc with the caller's own timestamp,
  a boolean `coparent_has_consented`, and derived `unlocked`. Never
  exposes the co-parent's raw timestamp value.
- Frontend `CompleteAlignmentReport.jsx::ChildNeedsExcerpt` completely
  rewritten. Renders a contextual checkbox + a live status pill
  (`Neither has consented yet` / `Waiting on co-parent` / etc.).
  When both consent, highlights render side-by-side labelled with each
  parent's name.
- Pytest `test_child_needs_consent_toggle_unlocks_highlights_only_after_both_consent`
  covers the full 7-step flow (initial scrub → A consents → B consents
  → unlock → A revokes → re-lock). Idempotent setup/teardown.

**🟢 P2 — Reusable dual-consent helper**
New `dual_consent.py` module: `require_dual_consent(case_id, caller_user_id, consent_key)`
+ `record_consent(...)`. Extracts the strict-gate pattern already used by
`snc2_comparison_routes`. Any future cross-parent surface can enforce
the strict privacy contract in one line — closes the "implicit consent"
gap that produced the iter185 leak.

**🟢 P2 — Admin-gated seed endpoint**
`POST /api/admin/seed-demo-case` (gated on `ADMIN_EMAILS`) — runs
`seed_joint_sample_case.run()` against the CURRENT env's Mongo. Lets
the platform owner spin up `SA-DEMO01` on production without shell
access. Idempotent, never destructive. Verified 403 for non-admin, 401
for no-auth.


## What's Implemented
### 2026-09-10 — Iter185 · Joint Seed + Inline Mini-Quiz + Voice Preview

**🟢 P2 — Joint Complete Alignment Report sample-case seed**
- `seed_joint_sample_case.py` — idempotent seed producing case `SA-DEMO01`
  with `parent1@test.com` and `parent2@test.com` both auto-accepted so
  the joint variant of the Complete Alignment Report is exercisable
  without waiting for real professional-created invitations.
- Foundation Statement seeded for BOTH parents (produces "shared"
  status on that lane); Communication seeded ONLY for parent A
  (produces the "one-side" status neutral tri-state) — mirrors real
  in-flight case shapes for a professional walkthrough.
- Test credentials file updated with the case_id + re-seed command.
- `test_iter184_complete_alignment_report.py` grows a new test
  (`test_joint_seeded_demo_case_is_reachable_by_member`) asserting
  the seeded case's alignment status map matches the intended shape.

**🟢 P2 — Inline mini-quiz on `/samples/joint-alignment-preview`**
- New `MiniQuiz.jsx` component embedded on the public sample page,
  matching the 6-prompt "Which scenario matches your family?" quiz
  that already ships as page 2 of the sample PDF. Copy kept in
  LOCKSTEP with `joint_alignment_sample_pdf.py::QUIZ_PROMPTS`.
- Tri-tone answer buttons (agree / differ / incomplete) with live
  tally + outcome banner appearing after the first click. Copy
  Summary button uses `navigator.clipboard`.
- Zero server state — nothing typed here is persisted; explicitly
  labelled as a self-check, not a diagnosis.

**🟢 P2 — 3-second voice preview per ElevenLabs voice**
- New backend endpoint `GET /api/for-professionals/intro-audio/preview`
  serving a ~50KB / 3-4 second MP3 for each of the 4 curated voices.
  Cache key includes a `preview` marker so payloads never collide
  with the full 60-second intro.
- `ProfessionalsIntroAudio.jsx` voice picker now renders a two-part
  pill per voice — label click switches the intro voice, headphone
  icon click plays the 3-second preview via a hidden secondary
  `<audio>` element (does not disturb the main intro player state).
- Manifest exposes `preview_url_base` so the frontend builds preview
  URLs without hard-coding the path.

**🟢 P2 — Bug fix: joint PDF route ordering**
- Starlette's greedy `str` path converter was capturing `SA-DEMO01.pdf`
  into the JSON view's `case_id` parameter, failing its regex → 422.
- Fix: register the PDF route BEFORE the JSON route and accept an
  optional `.pdf` suffix in the PDF route's regex, stripping it
  server-side. Both variants now return 200 correctly.

**Testing agent iteration_61:** 100% backend + 100% frontend, zero
critical / zero minor issues, zero action items. Item 1 (Deploy)
green-lit and dispatched to the deployer.


## What's Implemented
### 2026-09-10 — Iter188 · Complete Alignment Report (unified 10-section)

**🟢 P1 — New unified assessment report mirroring `sacoparentsalign.com`**
Combines every reflection a parent has completed into a single 10-section
report. The skeleton is identical to sacoparentsalign.com's universal
Joint Alignment Report so a mediator trained on Align opens either the
individual or joint variant and always knows where to look.

- **Backend** (`complete_alignment_aggregator.py`) — READ-ONLY pull across
  7 lanes keyed on `user_id`: Foundation (`prep_data`), Communication
  (`communication_reflection`), Activities & Costs (`activities_reflection`),
  Parenting Schedule (`parenting_schedule_reflection`), Child Needs
  (`snc_v2_answers` + `snc2_reports`), Safety (`safety_assessments`),
  Co-Parenting (`cp_reports`). Deterministic `LANES` order shared with
  frontend + PDF. Two entry points: `aggregate_for_user()` and
  `aggregate_for_case()` (joint = both parents on the same case).
- **PDF** (`complete_alignment_report_pdf.py`) — FPDF2-based renderer
  producing the 10 sections verbatim from sacoparentsalign.com:
  01 Complete Alignment Overview · 02 Your Child at the Center ·
  03 Where You Align (joint) / Your Reflection Summary (individual) ·
  04 Where Your Perspectives Differ (joint) / Areas You've Explored
  (individual) · 05 What Might Your Child Need? · 06 Options & Resources ·
  07 Questions for Parent Conversation · 08 Professional Conversation
  Guide · 09 Parent Action Plan · 10 Complete Alignment Summary.
  Clinical guardrails baked in on every page ("Educational and
  organizational tool - not a diagnosis or court submission" +
  sacoparentsalign.com copyright footer).
- **Routes** (`complete_alignment_report_routes.py`, mounted under `/api`):
  * `GET /complete-report/mine` - JSON view for signed-in parent
  * `GET /complete-report/mine.pdf` - individual PDF download
  * `GET /complete-report/joint/{case_id}` - joint JSON (parent-or-professional
    membership required; 404 for unknown/unauthorised to avoid case-id leak)
  * `GET /complete-report/joint/{case_id}.pdf` - joint PDF download
- **Frontend** (`CompleteAlignmentReport.jsx`) - live viewer that mirrors
  the PDF skeleton. Uses `useAuth()` hook (not `localStorage`). Routes:
  `/complete-alignment-report` and `/complete-alignment-report/joint/:caseId`.
  Testids `complete-report-section-01..10`, `complete-report-lane-{id}`,
  `complete-report-download-pdf`.
- **Dashboard** - new tile `dashboard-complete-alignment-card` with primary
  CTA to the individual viewer + secondary link to
  `sacoparentsalign.com/samples`. Placed directly after the EcosystemStrip.
- **Tests** - `test_iter184_complete_alignment_report.py` (8 pytest) covering
  canonical lane order, PDF renders end-to-end (empty + populated + joint
  variants), auth gating (401 no-token, 422 malformed case_id, 404 unknown).
- **Testing agent verification (iter60)** - Backend 15/15 pytest green;
  Frontend 100% pass on all 10 section testids, lane rows, PDF download,
  dashboard tile presence, mobile 390px zero overflow.

### 2026-09-10 — Iter187 · ElevenLabs TTS (replaces OpenAI TTS)

**🟢 P2 — Professional intro audio migrated to ElevenLabs**
- `professionals_intro_voice.py` rewritten to use the ElevenLabs Python
  SDK (v2.67) instead of `emergentintegrations.llm.openai.OpenAITextToSpeech`.
- Four curated voices: **Rachel** (default), **Adam**, **Bella**, **Antoni** -
  ElevenLabs public-library voice IDs (`21m00Tcm4TlvDq8ikWAM`, etc.),
  stable across plans, no cloning required.
- Model: `eleven_multilingual_v2` (highest quality). Also supports
  `eleven_turbo_v2_5` fallback.
- Cache key extended with `provider='elevenlabs'` so any residual OpenAI
  cache entries are auto-invalidated on first play. First-play verified:
  ~1.09 MB MP3. Second play: `x-voice-cache: hit`.
- `ELEVENLABS_API_KEY` added to `/app/backend/.env`.
- `RESEND_API_KEY` rotated at the same time (user provided
  `re_814Lr6Gh_...`). Production UI secret still needs manual rotation.
- Frontend `ProfessionalsIntroAudio.jsx` labels updated: Rachel / Bella /
  Adam / Antoni. Runtime label now reads "~60 seconds · ElevenLabs".
- `test_iter181_professionals_intro_voice.py` rewritten for the new voice
  set + provider (7 pytest, all green).


## What's Implemented
### 2026-09-10 — Iter187 · Voice Picker + Sample PDF Mini-Quiz

**🟢 P2 — Voice picker on `/for-professionals` intro audio**
- `ProfessionalsIntroAudio.jsx` now renders a pill row above the Play
  button letting a visitor toggle between **Shimmer** (default) /
  **Nova** / **Alloy** / **Fable** (all four voices the backend
  supports via `emergentintegrations.llm.openai.OpenAITextToSpeech`).
- Audio URL rebuilt with `?voice=…` on every pick via `useMemo`;
  side-effect `useEffect` calls `audio.load()` on src change so the
  browser fetches the new file the next time Play is pressed.
- Right-side chip auto-updates to reflect the current voice (e.g.,
  "NOVA VOICE"); each pill uses `role="radio"` + `aria-checked` for
  proper accessibility semantics.
- Backend cache is keyed on `(voice, model)` so a re-play of the same
  voice is served from Mongo without a second OpenAI call.
- E2E verified: Nova/Alloy/Fable clicks each flip aria-checked, chip
  label, and audio `src` (`?voice=nova&model=tts-1` etc).

**🟢 P2 — Sample PDF mini-quiz (page 2)**
- The public sample joint alignment PDF at
  `/api/insights/samples/joint-alignment-preview.pdf` now ships a
  **second page**: "Which scenario matches your family?" with six
  neutral prompts (one per topic on page 1) each offering three
  answer chips keyed to agree / differ / incomplete.
- A "your rough result" legend at the bottom maps the score to a next
  step in plain, non-adjudicative language:
  - Mostly same/together → sample 1 scenario, short reflection may
    be enough
  - Mostly different/separately → sample 2 scenario, professional-
    guided joint session likely to add most value
  - Lots of "haven't tested it" → finish the reflection first
- Copy is Latin-1 safe (no em-dashes) — enforced by pytest.
- CTA at page bottom keeps the sacoparentsapp.online hyperlink.
- PDF grew from ~3.5KB (1 page) to ~6.4KB (2 pages).

**Regression:** 15/15 backend + 12/12 frontend tests pass.

### 2026-09-10 — Iter186 · Auth Cookie Migration + Two-Sample Toggle

**🔴 P0 — CRITICAL FIX: Invited-parent flow (user-reported bug)**
- Parents clicking `/join/:token` from a professional's invitation
  were never being routed to their assessment after signing in.
- **Root cause:** 7 frontend files were checking a stale
  `localStorage.getItem("token")` key that the app's cookie-based
  `AuthContext` (httpOnly cookie + `withCredentials: true`) never
  populates. `authToken` was always `null`, so the auto-accept + route
  `useEffect` in `JoinInvitation.jsx` never fired, and every
  `fetch(..., { headers: { Authorization: "Bearer null" }})` failed
  silently.
- **Files fixed** (all now use `useAuth().user` + `api` axios instance):
  `pages/JoinInvitation.jsx`, `pages/JoinCode.jsx`,
  `pages/ProfessionalsDirectory.jsx`,
  `pages/AdminProfessionalsEditor.jsx`,
  `components/dashboard/JointAlignmentRequests.jsx`,
  `components/AssessmentResultHandoff.jsx`,
  `components/CoparentCompletionToaster.jsx`.
- E2E preview-verified: cookie login → 200,
  `/api/joint-alignment/mine` returned 2 real cases for the parent.

**🟢 P2 — Two-Sample Toggle on `/samples/joint-alignment-preview`**
- Low-conflict ↔ high-conflict toggle so a hesitant parent can peek
  at both scenarios before inviting their co-parent.
- Backend `joint_alignment_sample_pdf.py` now exports
  `SAMPLE_TOPICS_LOW`, `SAMPLE_TOPICS_HIGH`, and a `SCENARIOS` map;
  `build_joint_alignment_sample_pdf(scenario)` accepts a
  `low-conflict|high-conflict` key with silent fallback.
- Public endpoint `GET /api/insights/samples/joint-alignment-preview.pdf`
  accepts `?scenario=…` and returns a scenario-suffixed filename
  (`sacoparents-joint-alignment-sample-{scenario}.pdf`). Unknown
  scenarios fall back to the low-conflict default silently — no 400s.
- Frontend renders a pill-style toggle with `aria-selected` state,
  per-scenario summary caption, scenario-aware Download PDF href, and
  a co-parent email body that auto-includes whichever scenario is
  currently selected.
- Both scenarios ship the SAME six topic titles with different
  agree/differ/incomplete mixes; low emphasises shared understanding
  (3/2/1), high emphasises differences with one shared anchor (1/4/1).
  Notes are Latin-1 safe (no em-dashes) — enforced by test.

**Regression:** 13/13 backend + 12/12 frontend tests pass.

### 2026-09-09 — Iter185 · Landing Smoke Render Test (jsdom)

**🟢 P2 — Landing.jsx crash-fail regression test**
- New `frontend/src/pages/Landing.test.jsx` mounts the full `<Landing />`
  tree in jsdom (via raw `react-dom/client` + `act`, same pattern as
  the existing `CodeInput.test.jsx`) and asserts:
  1. The page renders without throwing (would have caught the iter181
     `Briefcase` removal that would have crashed every anonymous
     home-page visit).
  2. 13 marquee `data-testid`s from the ecosystem strip, individual→
     joint bridge, three-reports strip, joint-journey card, and
     professional-connection card all resolve to real DOM nodes.
  3. A healthy count of `svg.lucide` elements ships — belt-and-
     suspenders against an import that silently drops a whole
     component instead of throwing.
- **Mocks** (kept minimal):
  - `react-router-dom` → mocked `virtual: true` because v7 ships ESM-
    first `exports` that CRA's default Jest resolver can't traverse;
    the smoke test doesn't need real routing.
  - `../lib/api` → axios stub so no network call fires in jsdom.
  - `./Orientation` → stub, Landing only imports `markOrientationSeen`
    as a side-effect.
- Sets `global.IS_REACT_ACT_ENVIRONMENT = true` so React 18's `act(...)`
  is recognised under Jest and the test log stays clean.
- **Mutation-tested**: temporarily removing `Briefcase` from Landing's
  lucide imports made all 3 tests fail with the exact "React tried to
  render undefined" error — confirming the test guards the intended
  regression class. Restored + all 3/3 pass. Full frontend suite:
  12/12 across 3 test files.

### 2026-09-09 — Iter184 · Sample Joint Alignment PDF + Email-to-Coparent

**🟢 P2 — Downloadable Sample PDF**
- New `backend/joint_alignment_sample_pdf.py` — builds a single-page
  US-Letter PDF from the SAME fictional dataset the React sample
  page renders. Six neutral topics with agree/differ/incomplete
  flags, agreed/differed/incomplete count cards, privacy reassurance
  box, and a compact "Ready to build yours?" CTA block linking to
  `sacoparentsapp.online`. Header and footer both carry a persistent
  **"SAMPLE — fictional data, not a real case"** ribbon so the PDF
  is unambiguous even if a mediator prints and forwards it.
- New public route: `GET /api/insights/samples/joint-alignment-preview.pdf`
  (added ABOVE the parameterised `/samples/{filename}` route so
  FastAPI matches the literal path). Returns `application/pdf` with
  a stable `Content-Disposition: inline; filename="sacoparents-
  joint-alignment-sample.pdf"` so a browser Save-As matches the
  "Email to my co-parent" pre-composed message.
- Data lockstep: `test_iter183_joint_alignment_sample_pdf.py`
  asserts the six topic titles + the {agree, differ, incomplete}
  status set stay in sync so a frontend copy change without a
  backend update fails the test.

**🟢 P2 — Email-to-Coparent Share Strip**
- New "Share this sample with your co-parent" strip inside the CTA
  card on `JointAlignmentSamplePreview.jsx`. Two buttons:
  - **Download sample PDF** (outline button) → `/api/insights/samples/
    joint-alignment-preview.pdf` (`target="_blank"` so parents can
    review it before saving).
  - **Email to my co-parent** (teal solid) → `mailto:` with a
    pre-composed subject and body. The body is neutral, personal,
    non-adjudicative and includes both the web sample URL and the
    PDF URL so the recipient can pick whichever format they prefer.
- All new elements carry `data-testid` (`sample-preview-share-strip`,
  `sample-preview-download-pdf`, `sample-preview-email-coparent`).

**Regression:** 10/10 pass across `test_iter181`, `test_iter182`,
and `test_iter183`.

### 2026-09-09 — Iter183 · Joint Alignment Sample Preview + Preferred Professionals Strip

**🟢 P2 — Public Joint Alignment Sample Preview**
- New public page `frontend/src/pages/JointAlignmentSamplePreview.jsx`
  mounted at `/samples/joint-alignment-preview`. Mirrors the exact
  layout of the real (auth-gated) `JointAlignmentPreview`:
  purple SAMPLE banner ("Alex & Sam with child Rian — fictional"),
  privacy reassurance card, agreed / differed / incomplete count
  pills, and a topic-by-topic list with agree / differ / incomplete
  flags. Fictional-and-neutral by design — six mixed topics
  (routines, screen time, extracurriculars, handovers, holidays,
  healthcare) chosen so a hesitant parent sees both agreement and
  friction on the same page.
- Three CTAs at the bottom mirror the dual-track landing framing:
  primary **Start on my own** → `/register`, secondary **I have an
  invitation** → `/join`, and tertiary **See other sample reports**
  → `/samples`.
- Discoverability: the Landing `IndividualToJointBridge` card now
  carries a **See a sample joint preview →** teal link that jumps
  straight to the new page.
- Wired in `App.js` at `/samples/joint-alignment-preview` (no auth).
- New pytest `tests/test_iter182_joint_alignment_sample.py` guards
  the public route reachability (200 + `text/html` + SPA root).

**🟢 P2 — Preferred Professionals Strip on `/for-professionals`**
- New `frontend/src/components/PreferredProfessionalsStrip.jsx`
  fetches from the existing public `GET /api/professionals` endpoint
  and renders up to six cards (name · credentials · city, state ·
  mailto link). Silent fallback — if the endpoint fails or returns
  zero rows, the whole strip is hidden so a marketing page never
  shows a broken skeleton.
- Mounted on `ForProfessionals.jsx` between the hero and the four-
  step Align workflow, with a **View full directory →** link back to
  `/professionals`. Currently surfaces Matt Sossi (the only active
  founder-listed practitioner).

### 2026-09-09 — Iter182 · Dashboard Ecosystem Strip + Align Workflow + Intro Audio

**🟢 P2 — Dashboard Ecosystem Strip (compact)**
- Extracted the 3-node ecosystem band from `Landing.jsx` into a shared
  `frontend/src/components/EcosystemStrip.jsx` with a `variant` prop
  (`default` → marketing size; `compact` → dashboard-appropriate).
- Dashboard mounts `<EcosystemStrip variant="compact" />` directly
  under the `FourCircleFrontDoor` so a returning parent sees the
  pathway to their professional without scrolling.
- Landing page now uses the same shared component — single source of
  truth for the ecosystem language across both surfaces.

**🟢 P2 — /for-professionals Align 4-Step Workflow**
- New `for-pros-align-workflow` section between the hero and the FAQ
  block. Renders four numbered step cards mirroring the same verbs
  used on the Landing ecosystem strip:
  1. **Invite** (Send icon)
  2. **Compare** (GitCompare icon)
  3. **Identify Alignment** (Target icon)
  4. **Guide Conversation** (MessageCircle icon)
- Copy is deliberately clinical-neutral (describes what the
  **professional** does; no marketing fluff, no adjudicative claims)
  matching the strict guardrail already enforced on the page.

**🟢 P3 — Shimmer-Voiced Intro Audio**
- New `backend/professionals_intro_voice.py` — mirrors the pattern
  of `foundation_statement_voice.py` (same `emergentintegrations.llm.
  openai.OpenAITextToSpeech` wrapper, same MongoDB-backed cache) but
  uses a **global** cache (`professionals_intro_voice_cache`) keyed
  on `(script_sha, voice, model)` since the marketing script is
  identical for every visitor.
- Fixed ~60-second clinical-neutral script explaining what SA
  CoParents produces + the four-step Align workflow. Never fires the
  TTS endpoint on page-load — the audio element uses `preload="none"`
  and only fetches on the user's Play click.
- New public routes:
  - `GET /api/for-professionals/intro-audio/manifest` — returns the
    transcript + audio URL + supported voices/models.
  - `GET /api/for-professionals/intro-audio` — streams MP3 (browser +
    CDN-cacheable, `Cache-Control: public, max-age=86400`,
    `X-Voice-Cache: hit|miss`).
- New `frontend/src/components/ProfessionalsIntroAudio.jsx` — Play /
  Pause button, "Shimmer voice" chip, ~60-second runtime hint, and a
  collapsible transcript for accessibility + skimmers.
- 5 hermetic tests in `tests/test_iter181_professionals_intro_voice.py`
  — all passing (manifest transcript keywords, public access, cache
  key determinism, voice / model normalisation).

### 2026-09-09 — Iter181 · Landing Ecosystem Clarity + Individual→Joint Bridge

**🟢 P2 — Ecosystem Flow Strip (new)**
- `Landing.jsx :: EcosystemFlow` — new 3-node horizontal band placed
  directly under the Hero: **For Parents (sacoparentsapp.online)** →
  **For Professionals (sacoparentsalign.com)** → **Better Child-Focused
  Agreements**. Nodes stack vertically on mobile with down-arrow
  connectors so the ecosystem is legible before the parent scrolls
  into the six-step journey.

**🟢 P2 — Report Clarity + Individual→Joint Bridge**
- `ThreeReportsStrip` retitled **"Individual Journey"** with the three
  reports relabelled to their canonical names:
  1. Co-Parenting Assessment Report
  2. Foundation Statement
  3. Child Needs Statement
- New `IndividualToJointBridge` component sits directly after the
  three-report strip. Copy: *"Want to compare perspectives? Invite
  your co-parent — or connect with a mediator, attorney or therapist
  — to move from individual reflection into joint alignment."*
  followed by a **Joint Journey** card previewing the
  *Joint Assessment → Joint Alignment Report* path. Resolves the prior
  "3 reports or 4 reports?" ambiguity by making the pivot explicit.

**🟢 P2 — Professional Connection Section**
- New `ProfessionalConnection` component placed **directly after Step
  6** in the six-step journey (`HowItWorks`). Copy: *"Working with a
  mediator, attorney, therapist, or parenting professional? Your
  professional can invite you to connect your completed SA CoParents
  reflections with SA CoParents Align. Your individual reflection
  remains yours. Align helps the professional identify areas of
  shared understanding and differences that may need discussion."*
- Two CTAs:
  - **Primary:** *"I have a professional invitation"* → `/join`
  - **Secondary:** *"Learn about SA CoParents Align"* → external
    `https://sacoparentsalign.com` (`ArrowUpRight` icon, opens in
    new tab with `noopener noreferrer`).
- All new nodes carry `data-testid` attributes (`ecosystem-flow`,
  `ecosystem-node-*`, `individual-to-joint-bridge`, `joint-journey-card`,
  `professional-connection`, `professional-connection-invitation-cta`,
  `professional-connection-align-cta`) for automated testing.

**Page composition (final order):** Hero → EcosystemFlow →
ThreeReportsStrip → IndividualToJointBridge → HowItWorks (Steps 1-6) →
ProfessionalConnection → AlignmentPhilosophy → TrustSignals →
HomepageFAQ → FinalCTA → Footer.

### 2026-09-09 — Iter180 · Auto-Focus + Sample Preview + Delivery Badge

**🟢 P3 — Prof Preview Auto-Focus**
- `JoinInvitation.jsx` now attaches a `ref` to the primary Start My
  Assessment CTA and auto-focuses it 250ms after the invitation is
  accepted (so screen readers announce the "you're linked" heading
  first). Runs once per accept (`autoFocusedRef`) so React strict-
  mode double-invokes don't re-steal focus.
- Small keyboard hint added under the CTAs:
  *"Press Enter to continue."*
- `focus:ring-2 focus:ring-[#3D1A78]` for a visible focus ring
  when the browser announces it.

**🟢 P3 — Path B Sample Link**
- Collapsed Path B card on Landing now shows a tiny
  *"See a sample invited screen →"* link (only on the collapsed
  variant, kept out of the expanded state so real users don't
  see it once they're mid-flow).
- New public route `/join/sample-preview` renders a stub
  invitation page (professional_name "Adele van Wyk (sample)",
  invited_first_name "Alex") with a dismissible amber sample
  banner and a disabled *Begin my reflection* button. Added to
  `PUBLIC_MARKETING_PATHS` so mediators arriving from LinkedIn
  never hit the legal modal.
- Router: route registered BEFORE `/join/:token` since Route
  order matters — the more-specific static path must resolve
  first.

**🟡 P2 — Email Delivery Badge**
- New leaf module `backend/report_deliveries.py` with a
  `record_email_delivery()` helper and a `GET /report-deliveries`
  endpoint. Writes per-user, per-report_type receipts into a new
  `report_deliveries` collection. Never crashes the caller
  (empty user/email/type paths are noops).
- Wired the helper into ALL five email endpoints on success:
  Foundation Statement, SNC report, Educational / Medical /
  Psychological deep-dives.
- New shared `<EmailDeliveryBadge />` component with a
  `formatRelative()` helper. Renders a small green
  *"✓ Sent to X · 2 min ago"* pill next to the Email me button.
  Title attribute shows the exact ISO timestamp on hover.
  Auto-refreshes every 30s via a tick state; also refetches
  when the parent taps Email again via `refreshKey` prop.
- Badge added on all four report pages + inside the Foundation
  Statement share modal.
- Coverage: `tests/test_iter180_email_delivery_badge.py` (7 tests,
  green): endpoint auth + null-slots + write-and-read + timestamp
  bumps on second write + noops on invalid inputs + e2e via
  Foundation Statement email path.


## What's Implemented
### 2026-09-09 — Iter179 · Foundation Email + Prof Personalization + Path B Deep Link

**🟡 P2 — Foundation Statement email parity**
- New backend endpoint `POST /api/mediation/foundation-statement/email-me`
  (403 guest / 409 empty / 502-503 Resend / 200 with `{ok, sent_to,
  filename}`), distinct from the existing `share` flow — this is a
  personal receipt, no share history row written.
- New helper `send_foundation_statement_pdf_to_me()` in
  `email_service.py` with neutral, non-diagnostic copy matching
  the deep-dive email pattern.
- Frontend: **Email me the PDF** button added to the Download
  tab of `FoundationStatementShareModal` alongside Download PDF.

**🟡 P2 — Invitation preview personalization**
- `GET /joint-alignment/invitation/{token}` now returns
  `invited_first_name` — extracted from `parent.name` using
  first-whitespace-token rule (falls back to verbatim for
  single-token names, capped at 30 chars, never falls back to
  the email local-part).
- `JoinInvitation.jsx` renders **Hi, [First Name],** above the
  "You've been invited" title when present.
- Privacy guardrails: response still hides invitee email,
  co-parent name, and full surname. Verified in
  `test_preview_never_leaks_email_or_coparent_name`.

**🟡 P2 — Path B inline deep link**
- Landing hero Path B now expands inline on click into a card with:
    * "I have a link from my email" hint block
    * "I have an Alignment Code" input + Continue button
    * Live format validation on blur (regex against `SA-XXXXXX`)
      — client-side only since the backend endpoint requires JWT.
      Soft-warning shown for malformed codes but Continue always
      forwards to `/join?code=X` for the strict post-auth check.
- `JoinCode.jsx` now reads `?code=` from the URL via
  `useSearchParams` and pre-fills the input so the parent
  doesn't retype after login.
- Coverage: `tests/test_iter179_foundation_email_and_preview.py`
  (7 tests, green): 4 for Foundation email (401, 409, response
  shape, direct helper) + 3 for preview personalization
  (first-token, verbatim single-token, no PII leak).


## What's Implemented
### 2026-09-09 — Iter178 · Dual-Entry Landing + Deep-Dive Email PDFs

**🔴 P0 — Dual-entry Landing hero**
- New two-card hero on `/`: **Path A · I'm starting on my own**
  (scrolls to existing SituationPicker under `#situation-picker`
  anchor) and **Path B · I was invited by a professional**
  (routes to `/join`). Existing SituationPicker preserved
  verbatim so solo flow is unchanged.
- Step 5 refresh: subtitle now reads
  *"Complete Together, Separately"*, body copy expanded to
  match user's brief verbatim, and a new `<Step5CoparentCtas />`
  renders either:
    * Solo default: two CTAs `Invite my co-parent` (→ dashboard)
      + `Connect with a professional` (→ `/join`)
    * Invited variant (`?prof=X` or `sessionStorage
      invited_professional_name`): green
      `✓ Connected to [Prof Name]` banner instead of CTAs.
- `/join/:token` now writes the professional's name into
  `sessionStorage.invited_professional_name` so the invited
  state persists across the parent's login → landing bounce.

**🟡 P1 — Email PDF for the three Deep Dives**
- New shared helper `send_deep_dive_report_pdf(variant, ...)` in
  `email_service.py` with per-variant subject / filename /
  label (Educational / Medical / Psychological). Attaches the
  branded PDF, neutral copy matching the SNC report email.
- Three new endpoints — all mirroring the existing
  `POST /snc2/report/email` guardrails:
    * `POST /api/edu-deep/report/email`
    * `POST /api/med-deep/report/email`
    * `POST /api/psych-deep/report/email`
  (403 for guest, 404 if no report cached, 502/503 on Resend
  error, 200 with `{ok, sent_to, filename}`.)
- Frontend: added **Email me the PDF** button next to the
  existing Download button on each of the three deep-dive
  report pages (Educational / Medical / Psychological), with
  `data-testid`s matching the SNC pattern.
- Coverage: `tests/test_iter178_deep_dive_email.py` (10 tests,
  green): 3 auth guards + 3 no-report guards + 3 render tests
  for the three variants (asserts subject / attachment
  filename / label) + 1 unknown-variant safety check.


## What's Implemented
### 2026-09-08 — Iter177 · Handed-Off Cases Section on Parent Dashboard

**🟡 P2 — Live vs Handed-Off case grouping**
- Backend: `_case_public_shape()` now emits `released_at` +
  `released_professional_name` on every case in
  `/joint-alignment/mine`. `_derived_status()` returns
  `"released"` when the case has a `released_at` (expired /
  cancelled still win — a killed case remains visibly killed).
- Frontend: `JointAlignmentRequests.jsx` splits cases into two
  buckets via `useMemo`:
    * "Live" — rendered inline as before with Start / Continue /
      Preview joint outcome CTAs.
    * "Handed off" — under a collapsible section with a count
      pill, ShieldCheck icon, and per-row "View receipt" link
      that jumps to the Preview page (where the persisted
      released-state banner now shows).
  Handed-off rows are compact: "Released to X · Sept 8, 2026" —
  no start / preview CTAs (they'd be misleading on a terminal
  case).
- Empty-state variants: the whole section still hides when the
  parent has zero cases; when they only have handed-off cases,
  a small "No live cases right now" hint appears above the
  collapsible.
- Coverage: `tests/test_iter177_released_cases_mine.py` (4 tests,
  green): released_at null on new case, flips to `released`
  after execute-release, both parents see terminal state,
  expired precedence preserved.


## What's Implemented
### 2026-09-08 — Iter176 · Referring-Pro BCC + Persisted Released State

**🟡 P2 — Referring professional BCC on release receipts**
- `email_service._send()` now accepts an optional `bcc: List[str]`
  and forwards it to Resend (deduped against the To line to avoid
  self-copies).
- `send_joint_alignment_release_confirmation()` gained a
  `bcc_email` kwarg + injects a transparent "cc'd to X for their
  case file" line in HTML + plain-text bodies — parents are never
  copied silently.
- `execute-release` handler reads `case.professional.email` and
  passes it as BCC on BOTH parents' receipts. Skipped silently
  when the field is missing / invalid so a mis-shaped case never
  crashes the release itself.

**🟡 P1 — /consent-status persisted released state**
- Response now includes `released_at` (ISO string or null),
  `released_professional_name`, and `released_by_user_id` at the
  top level.
- `JointAlignmentPreview.jsx` `anyReleased()` helper now reads
  the persisted field, so a hard refresh on a case that was
  released earlier in the day shows the green terminal banner
  instead of resurfacing the "Continue to release consent" CTA.
- Coverage: `tests/test_iter176_bcc_and_released_status.py`
  (5 tests, green): 3 direct patch-based helper tests
  (bcc forwarding, bcc absence, invalid bcc) + 2 e2e persistence
  tests (`released_at=null` pre-release,
  `released_at=<ISO>` post-release). Route-side BCC plumbing is a
  single-line kwarg pass-through verified by inspection; e2e
  effect covered by the persistence tests.


## What's Implemented
### 2026-09-08 — Iter175 · Release Confirmation Email + Copyright Year Auto

**🟡 P1 — Release confirmation email**
- New `email_service.send_joint_alignment_release_confirmation()` —
  neutral / clinical receipt sent to BOTH parents right after
  `execute-release` succeeds. Includes case_id, assessment label,
  professional name, released_at timestamp, and a
  "review/extend/revoke" CTA linking to
  `/shared-with-professionals`. HTML + plain-text bodies.
- Wired into `execute-release` handler as a best-effort dispatch
  (per-parent try/except so a single delivery failure never
  aborts the release itself or blocks the co-parent's receipt).
  Skipped entirely on the idempotent second call (which returns
  `applied=false` before reaching the email loop).

**🟡 P2 — Copyright year auto**
- Backend: `pdf_base._copyright_line()` now composes the line
  using `datetime.now(timezone.utc).year` at every render so the
  PDF footer rolls over automatically on 1 Jan.
- Frontend: `<GlobalCopyright />` now interpolates
  `new Date().getFullYear()` — same auto-rollover for the web
  footer. Screenshot confirmed `© 2026` today.
- Coverage: `tests/test_iter175_release_email_and_year.py`
  (4 tests, green): direct patch-based test on the email helper
  (asserts to_email, subject, case_id, professional name, and
  assessment label in the rendered HTML + plain text), plus
  execute-release response contract checks and a year-in-line
  assertion.


## What's Implemented
### 2026-09-08 — Iter174 · Clickable PDF Copyright + Preview → Release Modal

**🟡 P2 — PDF copyright as live hyperlink**
- Updated `pdf_base.render_pdf_copyright()` to overlay a
  `pdf.link(...)` annotation on the copyright line, targeting
  `https://sacoparentsalign.com`. Width computed via
  `pdf.get_string_width(...)` so the hit-area matches the text.
- Verified the URI annotation is present via `pdfinfo`/regex on
  a freshly-built Foundation Statement (`/URI (https://sacoparentsalign.com)`).
  No per-report edits needed — all 22 report footers already
  call the shared helper.

**🟡 P1 — Preview to Release modal**
- Enhanced `POST /joint-alignment/cases/{id}/release-consent` to
  return `release_eligible`, `release_professional_name`, and
  `already_released` alongside the caller's consent shape so the
  frontend can react without a second `/consent-status` fetch.
- New endpoint `POST /joint-alignment/cases/{id}/execute-release`:
  party-only, requires `release_eligible=True`, flips case status
  to `released`, records `released_at` + `released_professional_name`,
  fires the sacoparentsalign.com completion webhook, idempotent
  on a second call (`applied=false`).
- New `<ReleaseConsentModal />` inside `JointAlignmentPreview.jsx`:
  prefilled professional name from co-parent's already-recorded
  release consent (locked read-only when the co-parent has named
  someone first), verbatim consent copy from the backend,
  explicit `"I authorize release…"` checkbox, submit button.
- Post-submit flow:
   * Co-parent hasn't consented yet → toast + amber
     "awaiting_coparent" banner on the preview page.
   * Both have consented → auto-fire execute-release, show green
     "Both parents have released" banner, then redirect to
     `/shared-with-professionals` after 3.2s.
- Coverage: `tests/test_iter174_execute_release.py` (9 tests, green)
  + existing iter171 consent-split tests all still passing.


## What's Implemented
### 2026-09-08 — Iter173 · JA Preview + For-Professionals + Global Copyright

**🟡 P1 — Joint Alignment Preview (agreement-flag-only)**
- New endpoint `GET /api/joint-alignment/cases/{case_id}/preview`
  returns per-topic `agree` / `differ` / `incomplete` flags plus a
  `{total, agreed, differed, incomplete}` summary. Guards: caller
  must be a party, both parents must have active
  `comparison_consent`, both must have `assessment_completed_at`.
  Response NEVER exposes raw content — stable hash of each topic's
  minimised payload (volatile `updated_at` / `generated_at` fields
  stripped so identical answers submitted seconds apart still read
  as `agree`).
- New page `/joint-alignment/cases/:caseId/preview`
  (`JointAlignmentPreview.jsx`) with private-review banner, count
  pills, per-topic list, and a legal-note block.
- Dashboard `JointAlignmentRequests` component now surfaces a
  "Preview joint outcome" button once a case flips to
  `both_complete`.
- Coverage: `tests/test_iter173_joint_align_preview.py` (9 tests,
  green).

**🟡 P2 — `/for-professionals` (clinical-neutral refresh)**
- Removed hero and closing-CTA gradients; hero copy tightened to
  a neutral "SA CoParents for mediation practices." headline that
  reads like a directory listing rather than a sales page.
- Added `/for-professionals` to `PUBLIC_MARKETING_PATHS` in
  `LegalAcknowledgment.jsx` so mediators arriving from LinkedIn
  don't hit the disclaimer modal on landing.

**🟡 P2 — Global copyright rollout**
- New `<GlobalCopyright />` component mounted once in `App.js`
  after `<Routes />` so every page ends with
  `© 2026 sacoparentsalign.com · All rights reserved.`
- Replaced the two existing per-page copyright lines
  (`ForProfessionals`, `Watch`) so the new attribution is the
  only copyright shown anywhere.
- New shared helper `pdf_base.render_pdf_copyright(pdf)` writing
  the same line at 6mm from the bottom edge of every PDF page.
  Injected into every `footer(self)` method across 20 report
  builders + added a `footer` method to `_FoundationPDF` and
  `_CaseStatusPDF` (which previously used the FPDF default no-op).
  Rendered on chromeless / cover pages too.


## What's Implemented
### 2026-09-08 — Iter172 · Access-Expiring In-App Banner

**🟡 P1 — Expiring-Soon Banner on /shared-with-professionals**
- New backend endpoint
  `GET /api/parent/professional-invitations/expiring-soon` returns
  invites whose `access_expiration` falls inside the next 7 days,
  excluding revoked / declined / already-expired rows. Scoped to
  the caller. Response advertises `default_extend_days=14`,
  `allowed_extend_days=[7,14,30,60,90]`, and per-row
  `days_until_expiration`.
- Extend endpoint (`POST .../{id}/extend`) now accepts 14-day slot
  and defaults to +14d when the body omits `access_days`. Create
  validator still restricts to {7,30,60,90} — 14 is extend-only.
- New amber banner (`data-testid="expiring-soon-banner"`) on
  `/shared-with-professionals`: lists imminent expirations with a
  one-tap "Extend +14d" button and a session-level dismiss.
- Banner refreshes automatically after a successful extend, and
  the row falls out of the list once its expiration moves past
  the 7-day window.
- Coverage: `tests/test_iter172_expiring_banner.py` (9 tests,
  all passing). Regressions on iter168/171 pass green (28 tests).


## What's Implemented
### 2026-09-08 — Iter171 · 4-in-1 · Sweep + Preview + Handshake Doc + Consent Split

**✨ P2 — Digest Preview**
- New endpoint `POST /api/parent/notification-mode/preview-digest`.
  Rolls up the caller's last 7 days of `report_access_events` (real
  events) OR falls back to a demo payload with fictitious pros
  when the caller has no events yet. Sends via
  `send_parent_share_digest_email`.
- New "Send me a test digest" button on the
  `/shared-with-professionals` notification-preferences card
  (data-testid `notification-mode-preview`). Success toast reports
  whether the digest included real events or a demo sample.

**✨ P2 — Handshake Doc page**
- New public route `/for-portal-engineers` (no auth required —
  added to `PUBLIC_MARKETING_PATHS` so the legal-disclaimer modal
  doesn't gate external portal engineers).
- Six sections: Auth, Permission-check GET, Event POST, Accept-
  webhook (the OTHER direction), CLI simulator, Error contract.
- 30+ copyable code blocks (click-to-copy on hover).
- 100% overflow-free at 390px AND 1920px (verified).
- Mirrors the CLI at `scripts/portal_handshake_simulator.py` so
  external engineers can validate their portal implementation
  byte-for-byte.

**✨ P2 — Access-Expiring Sweep**
- New backend module `access_expiring_sweep.py`:
    * `flip_expired_invitations` — cascades `access_expiration < now`
      invitations to `status="access_expired"` + linked
      `professional_report_permissions.status="expired"`.
      Idempotent — second call is a no-op.
    * `send_access_expiring_warnings` — finds invitations exactly 7
      days from `access_expiration` (±24h band), sends a warning
      email via `send_parent_share_access_expiring_email`, and
      dedupes via `access_expiring_warning_sends` collection.
    * `run_access_expiring_sweep` — public entrypoint that runs
      the warning pass BEFORE the flip pass (so a parent gets one
      last chance to Extend before the row is auto-expired).
- Background loop `access_expiring_sweep_loop` registered on
  server startup. Idle no-op unless
  `ACCESS_EXPIRING_SWEEP_ENABLED=1`.
- New email helper `send_parent_share_access_expiring_email`
  (branded, plaintext + HTML).
- New collection: `access_expiring_warning_sends` (dedupe key).

**✨ P1 — Joint Alignment consent split**
Per the family-safety spec, comparison-of-answers and
release-of-report-to-professional are now TWO distinct consents:

- **New endpoints (all on the case)**:
    * `POST /api/joint-alignment/cases/{id}/comparison-consent` —
      caller records (or revokes) their consent to have their
      answers compared with the co-parent's. `consented=false`
      body revokes.
    * `POST /api/joint-alignment/cases/{id}/release-consent` —
      caller records (or revokes) their consent to release the
      resulting Joint Alignment Report to a NAMED professional
      (`professional_name` field).
    * `GET /api/joint-alignment/cases/{id}/consent-status` —
      returns per-parent state PLUS rollup eligibility flags:
      `comparison_eligible` (both parents consented, no revokes)
      and `release_eligible` (both parents consented to the SAME
      professional_name).
- **Per-parent fields added** to `joint_alignment_cases.parents[]`:
  `comparison_consent_at`, `comparison_consent_version`,
  `comparison_consent_revoked_at`, `release_consent_at`,
  `release_consent_professional_name`, `release_consent_version`,
  `release_consent_revoked_at`.
- **Verbatim consent texts** stored per spec:
    * Comparison: "I authorize SA CoParents to compare the selected
      completed reports from both participating parents for the
      limited purpose of identifying shared child-focused goals…"
    * Release: templated with the professional_name.
- **Auth**: caller is identified by JWT + email match against
  `parents[].email`. Non-parties + non-mediators get 403.
- **Audit-trail-safe revoke**: `consented=false` preserves the
  historical `consented_at` and only adds `revoked_at`, so
  revocation doesn't erase a parent's earlier yes.

**Testing**:
- New file `tests/test_iter171_sweep_preview_consent.py` (9 tests).
- Regression across iter168 + iter169 + iter170 + iter171 = 44/44
  green in ~93s.
- Testing-agent verdict: backend 100%, frontend 100%. Zero
  overflow at 390px and 1920px on the new public page after a
  `max-w-full + whitespace-pre + overflow-hidden` polish on the
  code-block component.

**Files touched**:
- `backend/access_expiring_sweep.py` (new)
- `backend/parent_professional_invitations.py` (adds
  preview-digest endpoint)
- `backend/joint_alignment_routes.py` (adds 3 consent-split
  endpoints)
- `backend/email_service.py` (adds `send_parent_share_access_expiring_email`)
- `backend/server.py` (registers `access_expiring_sweep_loop`)
- `frontend/src/pages/ForPortalEngineers.jsx` (new public page)
- `frontend/src/pages/SharedWithProfessionals.jsx` (adds test-digest
  button + handler)
- `frontend/src/App.js` (new `/for-portal-engineers` route)
- `frontend/src/components/LegalAcknowledgment.jsx` (adds
  `/for-portal-engineers` to `PUBLIC_MARKETING_PATHS`)
- `backend/tests/test_iter171_sweep_preview_consent.py` (new,
  9 tests)


### 2026-09-08 — Notification Digest + Portal Handshake Simulator

**✨ P2 — Daily share-notification digest (iter169)**
Parents with **≥3 active invitations** (non-revoked + not-expired)
are auto-elevated into "digest mode" — one rolled-up email per
morning covering every view / download / accept from the previous
UTC day, replacing per-event pings.

- **Auto rule**: `active_invitations >= 3` → mode auto-resolves to
  `digest` unless the parent has an explicit `immediate` override.
- **Explicit override**: parent can pin `immediate` or `digest`
  regardless of the auto rule, or `auto` to clear the pin.
- **Per-event notification suppression** — when a parent's resolved
  mode is `digest`, the per-event notification email in
  `parent_professional_invitations.record_access_event` is skipped.
  Event recording (view_count / download_count / status flip) still
  runs — only the outgoing email is suppressed. Audit trail stays
  intact.
- **Rollup email content** — per-professional block listing views /
  downloads / accepted/declined + specific report titles that were
  touched. Zero report body content. Zero counterparty info.
- **Idempotency** — dedupe key is `(parent_id, digest_day)` in
  `parent_share_digest_sends`. Silence-is-safety: parent had no
  events that day → we still record `no_events_silent` so the
  loop doesn't re-scan them until tomorrow.
- **Backend endpoints**:
    * `GET /api/parent/notification-mode` — returns
      `{mode, explicit_pref, active_invitation_count, auto_threshold}`.
    * `PUT /api/parent/notification-mode` — body
      `{mode: "digest"|"immediate"|"auto"}`. `"auto"` clears the
      explicit pref so the auto rule kicks in again.
- **Frontend**: new "Notification preferences" card on
  `/shared-with-professionals` (only shown when the parent has at
  least one invitation). Two aria-pressed pill toggles (Immediate
  emails / Daily digest) + a "Use automatic" clear-override link
  when the parent has manually set a pref.
- **Background job** `parent_share_digest_loop` runs on the
  configurable send-window (default `America/Chicago 07:00–10:00`)
  behind the `PARENT_SHARE_DIGEST_ENABLED=1` env flag. Idle no-op
  when unset — safe to leave registered.
- **New collections**:
    * `digest_notification_prefs` (parent_id → mode override)
    * `parent_share_digest_sends` (dedupe key + event_count)
- **Coverage**: `tests/test_iter169_share_digest.py` (11 tests) —
  auth guards, auto rule, explicit overrides, `auto` clears
  pref, `_iter_candidate_parents` respects immediate opt-outs,
  dry-run with-events vs. no-events-silent paths, digest-mode
  event recording still increments view_count.

**✨ P2 — Portal Handshake Simulator (iter170)**
A preview-only CLI for the sacoparentsalign.com portal engineers
so they can validate the contract byte-for-byte BEFORE their
portal ships.

- **New CLI** `/app/scripts/portal_handshake_simulator.py`:
    * Takes `--base-url`, `--integration-key`, `--permission-id`
      and one or more `--events {view,download,accepted,declined}`.
    * Hits the same two endpoints their portal must implement:
        - `GET /api/integrations/report-permissions/{id}` (auth check)
        - `POST /api/integrations/report-permissions/{id}/events`
    * Prints the full request + response for every hop.
    * Prints a **redacted** curl replay line for every request that
      references `$INTEGRATION_SHARED_SECRET` (never embeds the raw
      key — safe to paste into a bug tracker).
    * Exit 0 on success, 1 on any HTTP failure, 2 on missing key.
- **Coverage**: `tests/test_iter170_portal_simulator.py` (5 tests) —
  `--help`, missing-key exit 2, happy-path exit 0 with Active +
  Event-recorded output, curl output never contains the raw
  secret, unknown-permission exits 1.

**Rollup for the week**: 84/84 tests green across iter163
(directory) + iter164 (webhook + templates) + iter165 (samples) +
iter166 (directory swap) + iter167 (opens sparkline) + iter168
(parent-pro invitations) + iter169 (share digest) + iter170
(handshake simulator).

**Files touched**:
- `backend/parent_share_digest.py` (new)
- `backend/parent_professional_invitations.py` (adds
  notification-mode GET/PUT + digest-mode suppression)
- `backend/email_service.py` (adds `send_parent_share_digest_email`;
  fixes `send_parent_professional_share_notification` to keep its
  outgoing `_send` call after a mid-file insert)
- `backend/server.py` (registers `parent_share_digest_loop`)
- `frontend/src/pages/SharedWithProfessionals.jsx` (Notification
  preferences card + mode toggle handlers)
- `scripts/portal_handshake_simulator.py` (new CLI)
- `backend/tests/test_iter169_share_digest.py` (new, 11 tests)
- `backend/tests/test_iter170_portal_simulator.py` (new, 5 tests)


### 2026-09-08 — Opens Sparkline + Parent → Professional Report-Share Flow

**✨ P2 — Opens Sparkline (iter167)**
- New backend aggregator `foundation_statement_analytics.opens_daily_by_jti()`
  returns per-jti 7-day open counts (oldest → today) in a single Mongo
  `$group` pipeline. Rows with no opens still get `[0]*7` so the
  sparkline never null-guards.
- `GET /api/mediation/foundation-statement/shares` history payload now
  includes `daily_opens_7d` on every row.
- New `OpensSparkline.jsx` — pure inline SVG (7 bars, 6px each), auto-
  hides when all-zero. Purple accent on today + peak day, softer
  neutral for the rest. Mounted below the "3 opens · opened 2h ago"
  line on each Share modal history row.
- Coverage: `tests/test_iter167_opens_sparkline.py` (8 tests: window
  math, empty-list, zero-seed for missing jtis, day bucketing, owner
  scoping, 7-day cutoff, multi-jti batching, live-server schema).
  8/8 green. Regression clean across iter161 + iter167 = 19 tests.

**✨ P1 — Parent → Professional report-share workflow (iter168)**

The mediator/professional invite loop that was previously only bindable
to Joint Alignment cases is now available directly on the parent
dashboard for sharing SELECTED completed reports with any professional.

- **New route `/share/professional`** — 5-step wizard exactly per spec:
  1. Professional details (name, email + confirm, role from a 10-item
     list, org, phone, ref number, message).
  2. Report multi-select from a live catalog of the parent's completed
     reports (Foundation, Co-Parenting, Med/Edu/Psych Deep-Dive, SNC).
     No "share everything" default — every report must be affirmatively
     checked.
  3. Access — view-only vs. view+download radio, notify-on-view /
     -download / future-versions toggles, expiration pill (7/30/60/90d).
  4. Review + two unchecked consent boxes with verbatim spec copy:
     the "I authorize…" authorisation AND the "not a professional
     relationship" acknowledgement. Send button disables until BOTH
     are checked.
  5. Confirmation with view-status / invite-another / dashboard CTAs.
- **New route `/shared-with-professionals`** — parent-facing
  management console listing every invitation with status pill,
  reports offered, sent date, access-expiration, view/download
  counts, and per-row Resend / Extend / Revoke actions. Extend
  prompts for {7,30,60,90} days. Revoke double-confirms and hits
  the atomic revoke endpoint. Empty state has "Invite your first
  professional" CTA.
- **New dashboard card** `Invite a professional` with the "Share
  with purpose. Stay in control." eyebrow, positioned directly
  below the Four-Circle Front Door. Secondary link to Shared with
  Professionals.
- **New nav-bar link** "Shared with pros" in the top nav so the
  console is discoverable from every page.
- **New backend module `parent_report_catalog.py`** — enumerates
  every completed report the caller owns (foundation, coparenting,
  med-deep, edu-deep, psych-deep, snc) with title / blurb /
  completed_at / version. Metadata-only — never surfaces body content.
- **New backend module `parent_professional_invitations.py`** — new
  routes under `/api`:
    * `GET /parent/report-catalog` — feeds the wizard's Step 2.
    * `POST /parent/professional-invitations` — creates the invite +
      one `report_permission` row per selected report + emails the
      professional a portal accept URL (no report content in email).
    * `GET /parent/professional-invitations` — list scoped to caller.
    * `GET /parent/professional-invitations/{id}` — detail + per-report
      permissions.
    * `POST /:id/revoke` — atomic revoke across invite + all
      permissions. Idempotent (2nd call → applied=false).
    * `POST /:id/extend` — resets access_expiration to now +
      {7,30,60,90} days. 404 for revoked invites.
    * `POST /:id/resend` — mints a fresh 72h token and re-emails.
- **Sibling-portal enforcement endpoints** (HMAC-authenticated via
  existing `INTEGRATION_SHARED_SECRET`):
    * `GET /integrations/report-permissions/{permission_id}` —
      sacoparentsalign.com portal calls this before every view or
      download. Returns `{active, reason}` where reason is
      `revoked|expired|unknown` when access is off.
    * `POST /integrations/report-permissions/{id}/events` — sibling
      reports view/download/accepted/declined back. Rolls up
      view_count / download_count on the invite doc, flips
      status→accepted, fires notification emails when the parent
      opted in.
- **New collections**:
  - `parent_professional_invitations` — one row per invite with
    hashed token, selected_reports snapshot, permission bits,
    consent_version + verbatim consent texts, counters.
  - `professional_report_permissions` — one row per (invite, report)
    with its own `permission_id` for portal callbacks.
  - `report_access_events` — audit trail of every view/download/
    accept.
- **New email helpers** in `email_service.py`:
    * `send_parent_professional_share_invitation` — the accept-URL
      email. Branded HTML + plaintext. Never contains report bodies,
      child names, safety data, or the other parent's info.
    * `send_parent_professional_share_notification` — soft "Adele
      just opened your report" pings, dispatched only when the
      parent opted in during invite creation.
- **Guardrails enforced server-side**:
    * Foreign report_id → 400 (`completed reports` message).
    * Email confirm mismatch → 400.
    * Either consent unchecked → 400.
    * access_days not in {7,30,60,90} → 422.
    * Rate limit: 30 invites / hour / parent.
    * Cap: 10 reports per single invite.
    * `invitation_token_hash` stored (never raw). Raw token
      returned once to the sender on create/resend.
    * Portal callback endpoints require X-Integration-Key
      (`hmac.compare_digest`).
- **Consent versioning**: every invite persists `consent_version`
  (`2026-09-08`) + the verbatim consent texts. Future legal-copy
  edits don't retroactively rewrite what the parent agreed to.
- **Data-minimisation verified**: never stored / never surfaced —
  journal entries, AI coach conversations, unfinished drafts,
  safety-screen answers, account credentials, other parent's
  reports, unselected reports.
- **Coverage**: `tests/test_iter168_parent_professional_invitations.py`
  (19 tests: catalog auth + scoping; happy-path create; consent /
  email-match / foreign-report / bad-access-days guardrails;
  list/get scoping; revoke idempotency; extend + revoked-invite 404;
  portal permission-check with X-Integration-Key including
  active/revoked/unknown; event-record view increments + accept
  flips status). All 19 green.
- **Regression**: 68/68 tests green across iter163 (13) + iter164 (12)
  + iter165 (5) + iter166 (11) + iter167 (8) + iter168 (19).
- **Testing-agent verdict**: backend 100%, frontend ~95% (all core
  flows pass; one LOW-priority UX polish already applied — Send
  button now visually disables until both consent boxes checked).
- **Live-verified**: parent1@test.com dashboard → clicks "Invite a
  professional" → wizard opens → step 1 filled → step 2 shows 5
  real completed reports (Foundation, SNC, Co-Parenting, Psych,
  Edu) → step 3 access chosen → step 4 both consents checked →
  Send → step 5 confirmation with invitation_id + access expiration
  → link to `/shared-with-professionals` shows the new row with
  Resend / Extend / Revoke.
- **Files touched**:
  - `backend/parent_report_catalog.py` (new)
  - `backend/parent_professional_invitations.py` (new)
  - `backend/email_service.py` (+ 2 new helpers)
  - `backend/server.py` (registers new router)
  - `backend/foundation_statement_analytics.py` (+ `opens_daily_by_jti`
    + `_last_7_day_keys` + `_utc_day_key`)
  - `backend/mediation_routes.py` (history endpoint returns
    `daily_opens_7d`)
  - `frontend/src/pages/ShareWithProfessional.jsx` (new, 5-step wizard)
  - `frontend/src/pages/SharedWithProfessionals.jsx` (new, console)
  - `frontend/src/components/foundation/OpensSparkline.jsx` (new)
  - `frontend/src/components/foundation/FoundationStatementShareModal.jsx`
    (mounts OpensSparkline in each history row)
  - `frontend/src/pages/Dashboard.jsx` (adds "Invite a professional"
    card below the Four-Circle Front Door)
  - `frontend/src/App.js` (registers 2 new routes)
  - `frontend/src/components/AppShell.jsx` (adds "Shared with pros"
    nav link)
  - `backend/tests/test_iter167_opens_sparkline.py` (new, 8 tests)
  - `backend/tests/test_iter168_parent_professional_invitations.py`
    (new, 19 tests)


### 2026-09-08 — Sample Library Extended + Directory API Swap (cutover-ready)

**✨ P2 — Sample Library extended with 3 live-rendered PDFs**
- New generator module `/app/backend/generate_samples.py` renders
  three anonymised sample PDFs using the LIVE production renderers
  with hard-coded fictitious fixtures (Sam & Riley Parent, kids
  Jordan & Alex):
  - **Foundation Statement — Sample** (`sacoparents-foundation-statement-sample.pdf`)
    — the exact one-page reflection a parent emails their mediator
    pre-session, in the same layout parents get in production.
  - **Joint Alignment Case Status Report — Sample**
    (`sacoparents-case-status-report-sample.pdf`) — mediator-facing
    one-page status snapshot with per-parent progress, downloaded
    from `/mine`.
  - **Activities Cost Splitter Ledger — Sample**
    (`sacoparents-cost-splitter-sample.pdf`) — full income-weighted
    split example (42k / 58k) across sport, music, education, and
    medical categories with a side-by-side two-parent ledger.
- All three files land in `/app/frontend/public/downloads/` and are
  served directly by CRA's static handler.
- `Samples.jsx` now shows **30 sample cards** across **7 categories**:
  - "Joint Alignment Reports" grew to **5** (Case Status added).
  - "Co-Parenting Agreement + Foundation" grew to **7** (fresh
    live-rendered Foundation Statement added alongside the legacy
    sample).
  - **New category "Activities Cost Splitter · 1"** with amber
    tone, mounted between Special-Needs and Family-Violence.
- Coverage: `tests/test_iter165_sample_generators.py` (5 tests) —
  each generator returns valid `%PDF-` bytes, `generate_all()`
  writes 3 files, shipped copies exist and are valid PDFs.

**✨ P2 — Directory API swap: cutover-ready via env vars alone**
- `professional_directory._fetch_directory()` now switches from the
  hardcoded `_MOCK_DIRECTORY` roster to a live sibling API call
  **the moment BOTH `SACOPARENTSALIGN_BASE_URL` and
  `SACOPARENTSALIGN_API_KEY` are set** — zero code changes needed
  for the cutover.
- **Live path**: `httpx.AsyncClient` with 8s timeout, hits
  `{BASE}/api/directory/professionals` with
  `Authorization: Bearer {API_KEY}`.
- **60s in-process response cache** so a burst of mediator visits
  doesn't hammer the sibling.
- **Graceful fallback** to `_MOCK_DIRECTORY` on ANY failure:
  timeout, DNS error, transport error, 4xx, 5xx, non-JSON body,
  missing `professionals[]` key, or every row failing validation.
- **Per-row validation**: rows missing string `id`, `name`, or
  `contact_email` are dropped before returning.
- **No cache-poison**: a failed fetch does NOT cache the mock
  fallback — the very next call retries the sibling so a brief
  outage doesn't trap the app in mock-mode for 60 seconds.
- **`INTEGRATION_TODO_sacoparentsalign.md` updated**: the "one file
  to change" section now reads "**Nothing.** Set the two env vars
  and the swap is live." Zero call-site changes, zero UI changes,
  zero deploys required.
- Coverage: `tests/test_iter166_directory_api_swap.py` (11 tests)
  — env-var gating, happy path (URL + Authorization header
  asserted), row validation drops bad rows, fallbacks on 502 +
  timeout + bad-JSON + missing-key + all-invalid-rows, 60s cache
  hit on second call, no cache-poison after a failure, half-set
  env skips network entirely.
- **All 47 tests green** across iter163 (13) + iter164 (12) +
  iter165 (5) + iter166 (11) + iter142 baseline (6). No
  regressions.
- **Live-verified**: `/samples` renders all 30 cards, all 3 new
  PDFs downloadable at `/downloads/*` with HTTP 200 + valid
  `%PDF-` header. Directory endpoint `GET /api/professional/directory`
  still returns 5 mock pros (env vars intentionally unset on
  preview).
- **Files touched**:
  - `backend/generate_samples.py` (new)
  - `backend/professional_directory.py` (env-gated `_fetch_directory`,
    + `_fetch_directory_from_sibling`, + `_cached_directory` /
    `_store_cached_directory` / `_clear_directory_cache`,
    + `_validate_directory_row`)
  - `frontend/src/pages/Samples.jsx` (adds 3 new sample cards,
    new "Activities Cost Splitter" category)
  - `frontend/public/downloads/sacoparents-foundation-statement-sample.pdf` (new)
  - `frontend/public/downloads/sacoparents-case-status-report-sample.pdf` (new)
  - `frontend/public/downloads/sacoparents-cost-splitter-sample.pdf` (new)
  - `memory/INTEGRATION_TODO_sacoparentsalign.md` (documents the
    cutover-ready state)
  - `backend/tests/test_iter165_sample_generators.py` (new, 5 tests)
  - `backend/tests/test_iter166_directory_api_swap.py` (new, 11 tests)


### 2026-09-07 — Accept-webhook + Bulk-Import History Page + Reminder Note Templates

**✨ P1 — Server-to-server accept webhook**
- New endpoint `POST /api/professional/directory/invite/accept-webhook`
  that sacoparentsalign.com calls back when a professional accepts an
  invitation dispatched via `/professional/directory/invite`.
- Auth: HMAC-SHA256 signature over the raw request body, keyed on
  `SACOPARENTSALIGN_WEBHOOK_SECRET`, carried in
  `X-Sacoparentsalign-Signature` (with or without `sha256=` prefix).
  Signature is verified BEFORE the JSON body is parsed so a tampered
  payload never leaks a 400.
- Idempotent: second identical call returns `applied=false` (200).
  Unknown token → 404 (never leaks whether a token was ever valid).
- When the invite was case-bound, the acceptance is pushed to
  `joint_alignment_cases.directory_invite_acceptances` and surfaced
  on `GET /cases-i-created` (mediator-only shape) so mediators see
  "Dr. Nomsa accepted this case invite on Sep 7" without opening
  the sibling site.
- New mediator-facing audit endpoint
  `GET /api/professional/directory/invites` — returns the caller's
  own invites (pending + accepted), scrubbing the raw `invite_token`
  from every row (would enable forged webhook calls otherwise).
- **Storage change**: `professional_directory_invites` rows now
  persist the raw `invite_token` alongside `join_url` so the webhook
  can identify a specific row without URL parsing. Also adds
  `status`, `accepted_at`, `accepted_professional_{id,name,email}`.
- **Integration doc updated**: `INTEGRATION_TODO_sacoparentsalign.md`
  now spec-in-full for the accept webhook contract — exact header,
  body shape, signature algorithm, retry policy, idempotency
  semantics. New env var to set once the sibling ships:
  `SACOPARENTSALIGN_WEBHOOK_SECRET`.

**✨ P1 — Bulk-Import History page** at
`/professional/joint-alignment/bulk/history`
- Two-column layout (mobile-stacked): left column is a 20-row list
  of the caller's past CSV bulk imports (most-recent first), each
  card showing filename · started-at · created/skipped/errored
  pills. Right pane loads the selected import's detail with three
  count tiles + a wrap-flexed list of created case-ID chips (each
  a `<Link>` to `/mine?search=SA-XXXXXX`) + skipped-duplicate chips
  + errored rows with per-row reason.
- Empty-state ("No bulk imports yet") with a "Start a bulk import"
  CTA when the caller has nothing yet.
- New "History" pill on the `/mine` header (next to Bulk import) and
  a "View past imports →" link on the top of the `/bulk` page so
  the audit is one tap away from every entry point.
- No new backend endpoints needed — reuses
  `GET /api/professional/joint-alignment/bulk/history` and
  `GET .../bulk/history/{import_id}` shipped in a prior iteration.

**✨ P2 — Reusable reminder-note templates**
- New CRUD collection `reminder_note_templates`:
  - `GET /api/professional/reminder-note-templates` — list caller's
    templates, alphabetised by label.
  - `POST /api/professional/reminder-note-templates` — save a
    template. Duplicate label 409, empty label/body 400, body >
    240 chars 422, 13th template 409 (hard cap of 12 per user).
  - `DELETE /api/professional/reminder-note-templates/{tid}` —
    owner-only; 404 for foreign template_ids.
- New reusable frontend component
  `ReminderNoteTemplatePicker.jsx` mounted on:
  - `/professional/joint-alignment/new` (below the reminder-note
    textarea) — testids `pj-new-tpl-*`.
  - `/professional/joint-alignment/mine` inline case editor —
    testids `pj-mine-tpl-{case_id}-*`.
- Three actions per instance:
  - "Insert template" dropdown — pastes a saved body into the
    textarea.
  - "Save as template" — inline label input, POST, toast success.
    Disabled when textarea is empty; disabled when label is blank.
  - "Manage" — modal listing every saved template with a Trash
    button per row.
- **Coverage**: `tests/test_iter164_webhook_and_templates.py`
  (12 tests: 6 webhook, 2 audit-list, 6 templates). **57-test
  regression across iter150 + iter159 + iter163 + iter164 green.**
- **Live-verified**: mediator on `/mine` → clicks "History" pill →
  bulk history page loads with real import cards from parent1's
  prior uploads → clicks row → detail pane shows count tiles
  + case-ID chips linking to `/mine?search=SA-XXXXXX`. Mobile
  390px overflow-free. Template picker on `/new` shows correct
  disabled/enabled states as the textarea fills.
- **Files touched**:
  - `backend/joint_alignment_routes.py` (+ webhook endpoint,
    + invites-audit GET, + reminder-note-templates CRUD trio,
    + `Request` import, + directory_invite_acceptances surfaced
    on cases-i-created)
  - `backend/professional_directory.py` (+ invite_token stored,
    + `webhook_secret`, `verify_webhook_signature`,
    `find_invite_by_token`, `mark_invite_accepted`,
    `list_invites_for_inviter`)
  - `backend/.env` (+ `SACOPARENTSALIGN_WEBHOOK_SECRET`)
  - `frontend/src/pages/ProfessionalJointAlignmentBulkHistory.jsx`
    (new)
  - `frontend/src/components/professional/ReminderNoteTemplatePicker.jsx`
    (new)
  - `frontend/src/App.js` (registers the new route)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx`
    (adds "History" pill, mounts template picker in inline editor)
  - `frontend/src/pages/ProfessionalJointAlignmentBulk.jsx`
    (adds "View past imports →" link)
  - `frontend/src/pages/ProfessionalJointAlignmentNew.jsx`
    (mounts template picker below reminder-note textarea)
  - `memory/INTEGRATION_TODO_sacoparentsalign.md` (adds full
    accept-webhook contract + new env var)
  - `backend/tests/test_iter164_webhook_and_templates.py` (new,
    12 tests)


### 2026-09-07 — Reflection Autosave + sacoparentsalign.com Directory Invite

**🐞 Bug fix — Foundation Statement creation autosave**
- Root cause of the reported "parents can't create their foundation
  statements" bug: **no autosave**. Parents typed on mobile, phone
  slept / tab closed / back-tapped before hitting the sticky "Save"
  button, and lost everything. Save button is also often occluded
  by the mobile keyboard.
- Fix: **debounced 1500ms autosave** + **immediate save-on-blur** +
  **`pagehide` / visibilitychange sendBeacon flush** so no
  keystroke is ever lost — even if the parent closes the browser
  mid-sentence.
- New refs in `Reflection.jsx`:
  - `pendingRef` — always holds the latest entries snapshot so
    the debounced flusher sends the newest content.
  - `lastSavedJsonRef` — dedupes; a save fires only when content
    actually changed.
  - `inFlightRef` — prevents overlapping saves.
- Sticky-bar copy updated from *"Unsaved changes"* → *"Autosaving as
  you type…"* / *"Autosaved 09:04 PM"* so parents feel the safety
  net working. The explicit **Save reflection** button stays for
  parents who like the certainty.
- Coverage: `tests/test_iter162_reflection_autosave.py` (3 tests) —
  verifies partial single-prompt saves, progressive writes, and
  down-edits (clearing a prompt).

**✨ Feature — Invite a professional from sacoparentsalign.com**
- **New module `/app/backend/professional_directory.py`** with a
  swappable `_fetch_directory()` seam. Today serves a **hardcoded
  roster of 5 sample pros** (Adele/Nomsa/Kagiso/Priya/Sanet)
  spanning mediation, psychology, family law, therapy, and
  financial mediation. Tomorrow: swap the one function to point at
  the sibling API — no call-site changes.
- **Endpoint `GET /api/professional/directory`** — JWT-required,
  supports `?q=` (substring across name/title/city/specialties)
  and `?specialty=` (exact tag) filters.
- **Endpoint `POST /api/professional/directory/invite`** —
  mediator picks a `professional_id`, optionally binds a
  `case_id` they own, adds a `personal_note`, and we email a warm
  invitation to `{professional}@sacoparentsalign.com` with a
  `sacoparentsalign.com/join?case=&token=...` accept URL.
- **Guardrails**:
  - 20 invitations / hour / mediator rate limit.
  - Same (mediator, professional) pair within 24h returns 409.
  - Foreign `case_id` returns 404 (no leakage).
  - Email delivery failures return 502 with the provider's message.
- **Audit collection**: `professional_directory_invites` — one row
  per dispatch with inviter, case, professional, note, and the
  opaque join-URL token. Powers the future "who did I invite?"
  audit view + the duplicate guard.
- **New frontend `ProfessionalDirectoryModal.jsx`** — two-pane
  modal (searchable list → send composer). Live directory search
  with 250ms debounce, specialty pills, case-binding pill when
  opened from a case row, note textarea with 500-char counter, and
  a "They'll accept from sacoparentsalign.com — no login required"
  reassurance line. Mounted from a new **"Invite a pro"** pill in
  the `/mine` header row.
- **Integration doc**: `/app/memory/INTEGRATION_TODO_sacoparentsalign.md`
  spec-in-full for the sibling directory endpoint — exact JSON
  contract, auth header, error codes, env var names, and the
  webhook-back plan for accept notifications. The one file the
  sibling team needs to read.
- **Coverage**: `tests/test_iter163_professional_directory.py`
  (13 tests: 4 unit + 9 live) covering mock roster shape, filter
  logic, auth guards, happy-path invite, 404 unknown pro, 409
  duplicate, 404 foreign case, case-bound join URL.
- **Live-verified**: mediator on `/mine` → clicks "Invite a pro"
  → modal opens with 5 professionals → search "Cape" narrows to
  Adele Van Wyk → clicks Invite → send pane shows Dr. Nomsa's
  contact email → note filled → Send → toast "Invitation sent to
  nomsa@sacoparentsalign.com" → modal closes cleanly.
- **Files touched**:
  - `backend/professional_directory.py` (new)
  - `backend/email_service.py` (adds `send_professional_directory_invitation`)
  - `backend/joint_alignment_routes.py` (adds `/directory`
    + `/directory/invite` endpoints, imports `uuid`)
  - `frontend/src/pages/Reflection.jsx` (autosave + save-on-blur
    + pagehide flush)
  - `frontend/src/components/professional/ProfessionalDirectoryModal.jsx` (new)
  - `frontend/src/pages/ProfessionalJointAlignmentMine.jsx`
    (mounts modal + adds "Invite a pro" pill)
  - `memory/INTEGRATION_TODO_sacoparentsalign.md` (new doc)
  - `backend/tests/test_iter162_reflection_autosave.py` (new, 3 tests)
  - `backend/tests/test_iter163_professional_directory.py` (new, 13 tests)


### 2026-09-07 — Foundation Statement Recipient-Open Analytics
- **P1 — Closes the "did they read it?" feedback loop.** When a
  parent opens the Share modal's History tab, each row now shows a
  soft eye icon + `2 opens · opened 6m ago` line for the recipients
  who have actually clicked the preview URL.
- **New module `/app/backend/foundation_statement_analytics.py`**
  with three responsibilities:
    - `is_link_preview_bot(user_agent)` — filters ~20 known
      link-preview crawlers (Slack, Discord, WhatsApp, Twitter/X,
      Facebook, LinkedIn, Telegram, Skype) plus scripts (curl,
      wget, python-requests, Postman). A missing UA is treated as
      a bot (real browsers always send one).
    - `record_preview_open()` — inserts one row per human open into
      `foundation_statement_preview_opens` with `{jti, owner,
      opened_at, ip_hash, user_agent, referer}`. Never blocks the
      recipient's response — any DB failure is swallowed.
    - `opens_by_jti()` — one `$group` aggregation returns
      `{jti: {open_count, last_opened_at, unique_ip_count}}` for
      the entire batch of history rows in a single round-trip.
- **Privacy posture**:
    - IPs are hashed with SHA-256 and truncated to 16 chars before
      storage — enough for unique-viewer de-dup, nowhere near enough
      to reverse-engineer.
    - Analytics scope is enforced by `doc_owner_user_id` — a
      foreign parent cannot see another parent's open stats (test
      `test_analytics_are_scoped_per_sender`).
    - Bot filtering runs BEFORE the write so Slack link unfurls
      never inflate the count.
- **Endpoint updates on `/api/mediation`**:
    - `GET /foundation-statement/shared/{token}` — now records an
      open (bot-filtered) as a side effect.
    - `GET /foundation-statement/shares` history payload — now
      returns `{open_count, last_opened_at, unique_ip_count}` per
      row, aggregated in a single Mongo `$group` pipeline.
- **Frontend `FoundationStatementShareModal.jsx`**:
    - New `formatLastOpened(iso)` helper produces human-friendly
      timestamps: `opened now`, `opened 3m ago`, `opened 4h ago`,
      `opened yesterday`, `opened 2d ago`, `opened Sep 5`.
    - Each history row now conditionally renders the analytics
      line under the recipient's email + timestamp. Unopened rows
      render nothing (no `0 opens` noise).
    - Historical opens on revoked links are STILL displayed so a
      parent can see the retro count even after they killed the URL.
- **Coverage** — `tests/test_iter161_foundation_analytics.py`
  (11 tests: 4 pure unit + 7 live-server). Bot-filter false-positive
  guardrails on real browser UAs. Regression clean against
  iter155-160.
- **Live-verified**: parent1 shared statement → 2 human opens (Chrome
  + Safari UAs) → History tab shows `👁 2 opens · opened 1m ago`
  under the top row. Slack + WhatsApp + curl opens on a separate
  share were correctly ignored (0 count). Mobile 390px overflow-free.
- **Files touched**:
  - `backend/foundation_statement_analytics.py` (new)
  - `backend/mediation_routes.py` (wires analytics into shared
    endpoint + extends history payload)
  - `frontend/src/components/foundation/FoundationStatementShareModal.jsx`
    (adds `formatLastOpened` helper + per-row analytics line + Eye icon)
  - `backend/tests/test_iter161_foundation_analytics.py` (new, 11 tests)


### 2026-09-07 — Revoke Shared Preview + CSV Streaming + Preview Test-Send
- **P1 — Revoke Shared Preview Link**: Parents can now switch off a
  specific preview URL on demand, from the Share modal's History tab
  on `/my-plan`.
    - Backend: `GET /foundation-statement/shares` history payload
      now returns `{preview_jti, preview_status, preview_expires_at}`
      per share row (with statuses `active | revoked | expired |
      none`). Legacy pre-preview rows report `none`.
    - New endpoint `POST /foundation-statement/preview-links/revoke`
      (JWT + owner-only, idempotent, 404 for foreign JTI, 400 for
      non-foundation doc types).
    - Frontend: History rows in `FoundationStatementShareModal`
      now display a colored status pill and, for active links, a
      "Revoke preview link" button that flips the row optimistically
      and issues a `window.confirm` before hitting the API.
    - Public shared endpoint already checks `is_share_token_revoked`,
      so revoking a link makes the recipient's URL 404 immediately.
- **P2 — CSV Live Progress Bar**: Bulk imports now stream
  event-by-event so a 100-row upload shows a moving progress bar
  and per-row status instead of freezing for 60-120 seconds.
    - Backend: new `POST /professional/joint-alignment/cases/bulk-csv/stream`
      endpoint returns `application/x-ndjson`. Emits one
      `{"event":"start"}`, one `{"event":"row"}` per parsed row,
      one `{"event":"done"}` — with fatal 4xx errors still surfacing
      BEFORE the stream begins so the client can toast them.
      `X-Accel-Buffering: no` header disables nginx/CDN buffering.
    - Frontend: `ProfessionalJointAlignmentBulk.jsx` swaps axios
      for `fetch()` + `ReadableStream` to consume NDJSON. Renders
      a live purple gradient progress bar (`data-testid="bulk-progress-bar"`),
      running counters for created/skipped/errored, the last-row
      status line, and a Cancel button (backed by `AbortController`).
    - The non-streaming `/bulk-csv` endpoint is retained for the
      pytest suite + any script consumers.
- **P1 — Preview Test-Send**: Mediators can send the exact reminder
  email to their own inbox from the Preview modal — perfect for
  spam-filter / mobile-Gmail / dark-mode QA before the 5-day sweep
  fires against a parent.
    - Backend: new `POST /professional/joint-alignment/cases/{case_id}/reminder-preview/send-test?parent_index=0|1`
      (JWT + owner-only). Rate-limited to 10 sends/hour per mediator
      via a `reminder_preview_test_sends` audit collection.
    - Subject is prefixed with `[TEST PREVIEW]` and the plaintext
      body carries a "this is a TEST — real recipient did NOT
      receive this" preamble so no mediator ever mistakes a QA
      copy for a live send.
    - Frontend: "Send test to my inbox" pill in the ReminderPreviewModal
      footer next to Done. Toast confirms the delivered-to address.
- **Coverage** — `tests/test_iter160_revoke_stream_testsend.py`
  (14 tests: 5 revoke, 5 streaming, 4 test-send). Combined
  regression across iter155-160: **78 tests green** (+ 1 skipped
  live-TTS test that requires the LLM key in env).
- **Live-verified**:
  - Parent 1 → `/my-plan` Share modal → History tab shows 4 rows
    with status pills ("Link revoked" / "Link active"). Revoke
    button flips a row to revoked instantly, public URL 404s.
  - Mediator uploads 6-row CSV → progress bar ticks from `0/6` →
    `6/6` in real time with running counters `5 ✓ · 0 〰 · 1 ⚠`,
    Cancel button visible mid-import. Final `Created 5 · Errored 1`
    matches server response.
  - Mediator opens Preview modal → clicks "Send test to my inbox"
    → toast confirms delivery to `mattsossi@bsossi.com`.
- **Files touched**:
  - `backend/mediation_routes.py` (adds preview_jti/status to
    shares history, new revoke endpoint)
  - `backend/joint_alignment_routes.py` (adds streaming NDJSON
    bulk endpoint, adds send-test endpoint + rate limit collection)
  - `frontend/src/components/foundation/FoundationStatementShareModal.jsx`
    (adds revoke button + status pills)
  - `frontend/src/pages/ProfessionalJointAlignmentBulk.jsx`
    (swaps to fetch+stream, adds progress bar + Cancel)
  - `frontend/src/components/professional/ReminderPreviewModal.jsx`
    (adds test-send button)
  - `backend/tests/test_iter160_revoke_stream_testsend.py` (new, 14 tests)


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
