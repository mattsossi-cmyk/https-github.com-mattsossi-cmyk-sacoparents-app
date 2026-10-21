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


### 2026-06 — Iter131 · Court codes + Professional Progress View + weekly requested reminders
- In-app court codes: `court_codes_routes.py` (`/api/professional/court-codes` POST/GET, `/{case_id}/revoke`). Code `SAC-XXXX-XXXX` shown once (hash only stored), case `CC-XXXXXX`, 30/60/90/180 days, requested keys auto-tick on the parent's Court page.
- Progress View (status only, never answers): `court_checklist.progress_rows`; `cases-i-created` parents carry `requested_progress` (null until joined). UI in My cases: `components/professional/CourtCodesPanel.jsx`, `CourtCodeForm.jsx`, `RequestedProgress.jsx`.
- Align: `GET /api/integrations/court-keys/{case_id}/progress` (X-Integration-Key, Align-made codes only; in-app codes 404). Setup note: `/app/memory/ALIGN_COURT_CODES_SETUP.md`.
- Reminders: `requested_reminders.py` (pre-syncs professional ticks from joint cases + court codes; neutral count-only email + unsubscribe; skips safety-flagged / unsubscribed / finished; once per ISO week). Runs inside the daily 9am Central `sa-reassess-reminder` cron, Mondays only (5-cron limit).
- Testing: iteration_131 backend 14/14, frontend 100%. Not deployed.
- Follow-up (user-approved): Notice of Confidentiality on Educational/Medical/Psychological forms now reads "…intended only for you and the professionals you choose to send it to." (frontend + backend mirror of child-needs content).

### 2026-06 — Iter132 · Progress PDF + right-away completion alert + reminder switch
- Progress PDF (status only): `progress_pdf.py` — `GET /api/professional/court-codes/{id}/progress.pdf` and `GET /api/professional/joint-alignment/cases/{id}/progress.pdf` (owner only). UI: `ProgressPdfButton.jsx` on court-code rows and joint-case rows in My cases.
- Completion alert: `completion_alerts.py` fires right after a completion save (self-assessment complete, co-parenting report, child-needs submit, foundation save, parallel plan completed). Emails the in-app professional once per parent per case; names case reference + private label only. Align-made codes skipped. A failed send is retried on the next save.
- Reminder switch: `GET/PUT /api/court-path/reminders` + `components/account/RequestedRemindersSwitch.jsx` on Account (works both ways, re-enables after email unsubscribe).
- Testing: iteration_132 backend 28/28, frontend 100%.

### 2026-06 — Iter133 · Parent completion summary
- `GET /api/court-path/completion-summary.pdf` (progress_pdf.parent_router): one page, "You've finished what your professional asked for.", case + professional name, each requested item Done · date; no answers; 409 until every requested item is done.
- UI: `pages/portal/court/CourtCompleteCard.jsx` above the Court menu when all requested items are done (signed-in parents).
- Testing: iteration_133 backend + frontend 100%. Not deployed yet (previous deploy queued before this feature).

### 2026-06 — Iter134 · Share summary with professional + Alert Preferences + Gentle Nudge
- Share: `completion_summary_routes.py` — `GET /api/court-path/completion-summary/recipients` ({professionals:[{ref,name}], can_type_email}; never emails), `POST .../send` {ref}|{email} → secure link + one-time code via `email_service.send_completion_summary` (attachment intercepted by `_send`). 5 sends/day. UI `pages/portal/court/CourtSendSummary.jsx` in the completion card. Typed email only for Align-made codes / no known professional.
- Alert Preferences: `GET/PUT /api/professional/completion-alerts` ({eligible, enabled}; stored in `professional_prefs`); `completion_alerts` honours opt-out (`skipped_opted_out`). UI `components/account/CompletionAlertsSwitch.jsx` (shared `AccountSwitch.jsx`), shown only to code/case creators.
- Gentle Nudge: `professional_nudges.py` `POST /api/professional/nudges` {ref, pid} (opaque pid; owner only; 7-day limit; 409 when all done). Suppressed silently for safety-flagged / unsubscribed parents with the same reply. UI `components/professional/NudgeButton.jsx` on court-code and joint-case parent cards.
- Testing: iteration_134 backend 16/16 + frontend 100%.

### 2026-06 — Iter135 · Nudge history + Case archive
- Nudge history: `professional_nudges.nudge_info` → parents[] carry `nudge_last_at`, `nudge_count` (suppressed nudges count too). UI line "Last nudged <date> · N nudges total" in `NudgeButton.jsx`, shown even after the parent finishes.
- Archive: `PUT /api/professional/archive {ref, archived}` (owner only; court codes → `portal_court_keys.archived_at`, joint cases → `professional_archived_at`, returned as `archived_at`). View-only: parents, reminders, completion emails, PDFs unaffected. UI `ArchiveLink.jsx`; Court codes "Show archived (N)" toggle; joint cases "Archived" filter chip (excluded from other filters/counts).
- Testing: iteration_135 backend 9/9 + frontend 100%.

### 2026-06 — Iter136 · Archive search, Bulk archive, Case-notes PDF, Monday digest
- Archive search: `CourtCodesPanel.jsx` search box (reference or private label) across active + archived codes; joint-case search already works inside the Archived filter. `CourtCodeItem.jsx` split out (`stateOf`, `isFinishedCode`).
- Bulk archive: `POST /api/professional/archive/finished {kind}` (codes: revoked/expired/all parents done; cases: both_complete/cancelled/expired) + `PUT /api/professional/archive/bulk {refs, archived}` for Undo. UI `ArchiveFinishedButton.jsx` (confirm → toast with Undo).
- Case notes in PDF: joint `progress.pdf?include_notes=true` adds "Private professional notes, not shared with parents". UI tick box in `ProgressPdfButton.jsx` (only when the case has notes; off by default).
- Monday digest: `professional_digest.py` (counts only over non-archived codes + active cases; once per ISO week; skipped when off / empty / unchanged since last sent). `GET/PUT /api/professional/digest`, `GET /api/professional/digest/unsubscribe?token=`. Runs in the existing daily 9am Central cron, Monday gate. UI `ProfessionalDigestSwitch.jsx` on Account (creators only).
- Testing: iteration_136 backend + frontend 100%.

### 2026-06 — Admin account counts (preview only, not deployed)
- `GET /api/analytics/admin/account-counts` (require_admin / ADMIN_EMAILS): total, parents, professionals, created_last_30_days (+ split), guest_sessions. Counts only. No role field exists: "professional" = account that created an in-app court code or joint case.
- UI `/admin/accounts` → `pages/AdminAccountCounts.jsx` (no DomainGuard, so it works on sacoparentsapp.online). Self-tested: admin 200, non-admin 403, no auth 401; desktop + 390px no overflow.
- User asked to never publish without an explicit "deploy" in that message.


### 2026-06 — Iter271–273 · Self-Assessment v2 (chat-style) + Progress Graph

Founder ask: replace Self Journey Card 1 with a new chat-style Self-Assessment,
save every completed run, measure the parent against themselves, set a goal.

- Copy (single source, lockstep): `backend/self_assessment_content.json` ==
  `frontend/src/pages/portal/selfAssessmentContent.json` (pytest
  `tests/test_self_assessment.py` asserts equality). Title renamed to
  **"Self-Assessment"** everywhere. `bands: []` — **score labels pending from
  founder** (drop `{min,label}` items into `bands` in BOTH files to enable).
- Content: chat intro (3 bubbles + safety note) → 4 rated sections × 5 Qs
  (1–5 Rarely…Consistently) → 5 open "My Progress" reflections → goal prompt
  "What would you like to work on next?" (prefilled from reflection #5).
- Scoring: overall = sum of 20 answers (/100); section = raw × 4 (/100).
- Backend `self_assessment_routes.py` (`/api/self-assessment`): GET/PUT `/me`
  (draft, auth), POST `/complete` (422 unless 20 answered; appends to
  `self_assessment_history`, deletes draft), GET `/history` (+current_goal),
  POST `/pdf` (public; body {entry, history}). Collections:
  `self_assessment_drafts`, `self_assessment_history` (old `self_assessments` dropped).
- PDF `self_assessment_pdf.py`: overall + 4 bars, Your Progress list, line
  graph (overall + 4 areas), first → latest deltas, central message, goal,
  cycle, full responses + reflections.
- Frontend `pages/portal/selfAssessment/*`: fully chat-style one-question-at-a-
  time flow (typing indicator, section dividers, "Change my last answer",
  resume with "Welcome back"), overview/results with score cards, Your
  Progress list, recharts graph with "Show the four areas" toggle, central
  message, cycle strip, PDF download, Quick Exit in modal header.
- Personal Co-Parenting Goal banner on landing (`door-landing-goal`) and top of
  Self Journey below Safety First (`door-self-goal`); Card 1 shows latest score.
- Testing: iteration_89 (v1 save/PDF) + iteration_90 (v2 full flow) 100% pass;
  graph + rename self-tested (PDF render + 390px screenshot, toggle 1→5 lines).

**Iter274 (2026-06) · Score Labels + Goal Check-ins + Reassess Reminders**
- Bands (founder-approved) in content JSON: 85+ Consistent Strength · 70 Growing
  Strength · 55 Developing · 40 Building Foundations · 0 Starting Point, each with
  a supportive `body`; shown on overall + 4 area cards and in PDF.
- Goal check-ins: POST `/api/self-assessment/goal/checkin` {entry_id, date}
  (one per local day, today±1 window), collection `self_assessment_checkins`;
  `/history` returns `goal_practice` for latest entry. GoalBanner shows running
  count + "I practised this today".
- Reminders: `self_assessment_reminders.py` sweep (6w at ≥42d, 8w at ≥56d if 6w
  sent ≥10d before; skips safety_ack.flagged / IPV level ≤2 / unsubscribed /
  guest / bounced; dedupe in `self_assessment_reminders`). Email
  `email_service.send_reassess_reminder` subject "Your reflection check-in" +
  unsubscribe link → GET `/api/self-assessment/reminders/unsubscribe?token=`
  (JWT kind `sa_reminder_unsub`, prefs in `self_assessment_reminder_prefs`).
  Cron `sa-reassess-reminder` daily 15:00 UTC → POST `/api/cron/self-assessment-reminders`.
  In-app "Time to reassess" note on GoalBanner (≥42 days); deep link
  `/dashboard?open=self-assessment` opens chat directly.
- Resend in preview is sandbox → real delivery needs verified domain in prod.
- Testing: iteration_91 backend 40/40; frontend verified (check-in tap re-verified by main agent).

**Iter275–276 (2026-06) · Streak, Card 2 reconnect, Mediator extras, Growth Moment, Child Needs page, CP line graph**
- Streak: GoalBanner 7-day dot strip + flame "N-day streak" (consecutive days ending today/yesterday); `/history` + `/goal/checkin` return `recent_dates`.
- Card 2 "Understand Your Relationship" now opens `portal/coparenting/CoparentingAssessmentModal` (67 Qs / 10 sections, one section per screen, auto-save via /api/coparenting/answer, finish → /complete + /report/generate, results with ratings, priority focus, PDF, retake). Guided chat no longer opened from Card 2 / roadmap step.
- Mediator Progress PDF: opt-in `include_safety` / `include_biff` (GET query + share body) → `cp_progress_extras.py` (grey_rock_audit timeline, 5 latest biff_pair snapshots). UI tick boxes (default OFF + warnings) in CpProgressTile, now mounted in Card 2 results (`cp-assess-mediator`). CpProgressTile + PDF charts replaced by ONE line graph "Overall score over time" (0–4 avg, dates on x-axis); movers bars, radar and sparkline removed.
- Growth Moment: results screen card + confetti when overall/any area moves up a band vs PREVIOUS assessment (`growthMoves` in OverviewPanel; copy `growth` in SA content JSON).
- Card 3 replaced by founder mockup "Your Child's Specific Needs" (Medical / Educational / Psychological forms). Content `child_needs_content.json` == `frontend/.../childNeedsContent.json`. API `/api/child-needs`: GET/PUT `/me/{category}` (auth), POST `/pdf` (public, combined PDF of filled categories). Cards show "Completed ✓ · Edit".
- Testing: iteration_92 (backend 60/60) + iteration_93 (frontend 100%); line-graph swap self-tested (PDF render + 390px screenshot).
- Seeded test data on parent1: grey_rock_audit (2), 1 biff_pair snapshot, completed 67-Q run.

**Iter277–278 (2026-06) · Landing welcome image + Card 4 saving/PDF**
- Landing: old `door-hero` banner removed; founder "Welcome to SA CoParents" artwork (`/images/sa-welcome*.webp`, compressed from 1.9MB PNG) sits UNDER the two door buttons with 3 tappable hotspots (self / court / BIFF Communication Builder); Goal card + 6-step roadmap below it.
- Card 4 Foundation Statement builder: `foundation_builder_routes.py` GET/PUT `/api/foundation-builder/me` (latest only, overwrite), POST `/pdf` (public, branded, ONE parent signature + date line per founder). Copy `foundation_builder_content.json` == `frontend/.../foundationBuilderContent.json`. Hook `portal/foundation/useFoundationBuilder.js` (autosave 1s debounce, legacy localStorage key migrated). "Saved ✓ · Edit" on tile + Access button. Older reflection-based Foundation Statement (mediation_routes) untouched.
- Testing: iteration_94 100% (backend 10/10, frontend all areas); single-signature change self-tested.
- Deployment health check: PASS (no blockers).

**Next / backlog:** to 65-Q backend
assessment (orphaned); Mediator PDF grey-rock timeline (P1); post-deploy smoke
script (P1); prod env toggles (digest, PUBLIC_BACKEND_URL, domain split).


### 2026-02-27 — Iter269/270 · Child-Needs View + Foundation Statement View

Founder ask (two sequential mockups):
- "When we get to item 3 - specific needs when action button is
  pushed i want the parent to see the following" (child-needs
  mobile mockup).
- "when parents click on action button 4 - foundation statement -
  i want parents directed to following page" (foundation
  statement mockup).

**Iter269 — Child-Needs sub-view (`door-view-child-needs`)**
- New component `/app/frontend/src/pages/portal/ChildNeedsView.jsx`.
- Reached from `door-self-card-child-needs` which now pushes
  `setView("child_needs")` instead of opening the old picker
  Dialog (dialog removed).
- Brand header + hero card ("What does my child need?") with the
  `child-needs-explore` CTA that opens the "all-needs" overview
  checklist.
- Three colour-coded category chips: `child-needs-cat-educational`
  (blue), `-medical` (rose), `-psychological` (teal); each opens
  a checklist dialog with 4 items.
- Checkbox state persists per category in
  `localStorage.sacoparents_child_needs_checklist_{category}` as
  an array of checked indices.
- Co-Parenting Roadmap (1–4) and Communication Builder repeated
  per mockup so parents can jump back out without leaving the
  flow.
- Back button returns to Self Journey without clearing the door
  memory (`setView("self")`).

**Iter270 — Foundation Statement sub-view (`door-view-foundation`)**
- New component `/app/frontend/src/pages/portal/FoundationStatementView.jsx`.
- Reached from `door-self-card-foundation` which now pushes
  `setView("foundation")` instead of calling `onOpenReport`
  directly. The existing Foundation drawer is still reachable
  from the finale rewards block in Self Journey.
- Brand header + hero card ("A Brighter Future for Your Child")
  with four pillars (`foundation-pillar-goals`, `-child`,
  `-values`, `-path`), colour-coded icons per the mockup.
- `foundation-access` button opens a `foundation-builder-dialog`
  with six fields (parent names, child info, core hopes, child
  needs, co-parenting principles, personal commitments).
- Form state persists to
  `localStorage.sacoparents_foundation_statement_v1` on every
  change. `foundation-print` triggers `window.print()` (clinical
  PDF lockstep preserved — no new backend PDF route).
- Sub-banner footer "Same Goals. A Brighter Future. · Safer
  Children · Stronger Families · Healthier Tomorrows" matches
  the mockup.
- Back returns to Self Journey.

Both sub-views receive the existing `QuickExit` chip and the
Safety-First strip as slot props so the clinical safety rails
remain one tap away.

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved. ESLint warnings unchanged.



### 2026-02-27 — Iter267 · Polling Jitter + Badge Preview + Pair Nudge Email

Founder ask:
- "Pair Polling Jitter: Add a small randomised jitter to the
  60-second interval so a thousand simultaneous parents don't all
  hit the endpoint on the same tick".
- "Joint Badge Preview: Show the joint badge inline before saving
  so both parents can see the shared design before downloading".
- "Pair Celebration Nudge Email: Send a short Resend email to the
  invited co-parent the moment the inviter completes their three,
  warm nudging them to finish theirs".

**Pair polling jitter — `SacoparentsPortal`**
Replaced the fixed `setInterval(60000)` with a recursive
`setTimeout` that schedules the next tick with
`60000 + Math.floor(Math.random() * 20001) - 10000`, giving a
50–70 s uniform jitter per device. Still gated on
`document.visibilityState === "visible"`, still refetches on
`visibilitychange`, still auto-stops once
`coparent_all_three_done` returns true.

**Badge preview dialog — iter267**
- Replaced the one-tap share flow with a two-step: tap chip →
  render PNG → open shadcn `Dialog` (`door-self-badge-preview-dialog`)
  showing the preview image (`door-self-badge-preview-image`),
  then tap `door-self-badge-preview-save` to run the share-sheet
  / download fallback. "Not yet"
  (`door-self-badge-preview-cancel`) revokes the blob URL and
  closes the dialog.
- Both the solo and the joint badge share the same preview
  dialog — `openBadgePreview("solo"|"joint")` branches on the
  renderer. Removed the now-unused `shareCelebrationBadge` and
  `shareJointCelebrationBadge` helpers to keep the file lean.

**Pair celebration nudge email**
- Backend: new helper
  `email_service.send_pair_celebration_nudge(to_email, link_url,
  inviter_name)` mirrors the branding + style of
  `send_coparent_invite`, subject
  `"{Inviter} finished their reflections — your turn, no rush"`,
  CTA "Pick up my private prep".
- Backend: new endpoint
  `POST /api/invites/coparent/pair-nudge` (invite_routes.py).
  Gated by `require_ipv_clearance` (defence in depth) and only
  runs when (a) the inviter has a signed-up co-parent, (b) the
  inviter has really finished all three primary modules
  server-side, and (c) `pair_nudge_sent_at` is not yet set.
  Writes `pair_nudge_sent_at` after a successful send so the
  endpoint is idempotent on repeat calls.
- Frontend: the existing all-three finale effect in
  `JourneyShell` now additionally fires a fire-and-forget
  `api.post("/invites/coparent/pair-nudge")`. 404/503/502/403
  responses are expected in the no-op branches (no invite,
  Resend not configured, IPV flagged) and silently ignored.

Backend endpoint smoke-tested with parent1 — returned
`{"ok":false,"reason":"no_signed_up_coparent"}` for the no-pair
baseline. Frontend badge preview verified end-to-end at 390×844:
dialog opens, PNG rendered inline, both Save and Not-yet actions
wired.

No PDF or AI-service touch — clinical lockstep preserved.



### 2026-02-27 — Iter266 · Pair Polling + Joint Badge Share

Founder ask:
- "Pair Progress Polling: Poll the pair-progress endpoint
  periodically so the celebration fires while the parent is still
  in the app, not only on refresh".
- "Pair Celebration Share: Offer a joint badge after both parents
  finish so each can save a two-side version of the Reflection
  Milestone".

**Pair progress polling — `SacoparentsPortal`**
The pair-progress effect now:
- Fires once immediately on mount.
- Then every 60 s via `setInterval`, but skips the fetch when
  `document.visibilityState !== "visible"` so a backgrounded tab
  doesn't drain battery or hit the API unnecessarily.
- Also refetches on `visibilitychange` so a parent returning to a
  foregrounded tab gets a fresh read without waiting the full
  interval.
- Stops the interval as soon as `coparent_all_three_done` is true —
  there's no reason to keep polling once the milestone fires (the
  local `PAIR_CELEBRATED_KEY` flag prevents double-firing anyway).
- All timers / listeners cleaned up on unmount.

**Joint celebration share — `door-self-share-joint-badge`**
A second canvas renderer `renderJointCelebrationBadge(myName,
coparentName)` draws a 1200×630 PNG with an emerald→purple
gradient, the brand pill, the two-line title "Shared Reflection
Milestone", a subtitle "A · B · C — Complete (both parents)", and
two signed name columns separated by a vertical divider (`Earned
by {myName}` on the left, `With {coparentName}` on the right).

The chip is rendered inside the existing finale-rewards block, but
only when `pairBothDone` is true — both the current parent's
`allThreeDone` AND the paired co-parent's
`coparent_all_three_done` must be set. The chip reuses the
`navigator.share({ files })` → direct-download fallback pattern
from the solo badge and shows a "Joint badge saved" toast on
success.

Note on end-to-end testing: Playwright `page.route` mocking is
unreliable in this preview environment for same-origin API calls,
so the joint chip visibility was validated by code inspection +
backend endpoint curl + reuse of the already-verified solo-badge
share pattern.

No PDF or AI-service touch — clinical lockstep preserved.



### 2026-02-27 — Iter265 · Hero Banner + Roadmap Progress + Partner Pair Celebration

Founder ask:
- "Hero Image Banner: Add the 'A Brighter Future for Your Child'
  hero image + tagline above the two doors so the landing has the
  same emotional pull as the mockup".
- "Journey Progress Bar: Show a thin bar at the top of the roadmap
  counting completed steps so parents see momentum at a glance".
- "Partner Pair Celebration: Fire a shared confetti when the
  invited co-parent accepts and finishes their own three modules
  so both sides feel the shared milestone".

**Hero banner — `door-hero` / `door-hero-tagline`**
Rendered above the `door-landing` section on the landing. An
Unsplash CDN image (`photo-1476703993599-0035a21b17a9`, loaded with
`loading="lazy"`) sits under a purple vertical gradient. The brand
lockup "SA CoParents · Start with alignment, end with agreement"
sits above the tagline "A Brighter Future for Your Child" rendered
in a cursive script face to echo the mockup.

**Roadmap progress bar — `door-roadmap-progress`**
Thin 1.5-px purple bar at the top of the `door-journey-roadmap`
section, labelled "{n}/6 steps complete" and
`door-roadmap-progress-pct` (0–100%). Completion is derived from
the same `completedWhen` flags each step already carries.

**Partner Pair Celebration**
- New backend endpoint `GET /api/invites/coparent/pair-progress`
  (invite_routes.py, right after `coparent_invite_gate`). Looks at
  both directions of the invite link: inviter→invitee (via
  `coparent_invites.signed_up_user_id`) and invitee→inviter (via
  `users.invited_by_user_id`). Reads the paired user's
  `portal_state` and derives
  `coparent_all_three_done` from the same primary-topic rule the
  frontend uses locally (`snapshot_history` topics + `foundation_text`
  + `safety_ack.ack_at`). Returns `{paired, coparent_user_id,
  coparent_all_three_done, coparent_display_name, direction}`.
- `SacoparentsPortal` polls the endpoint once on mount and passes
  the result to `JourneyShell` as a new `pairProgress` prop.
- `JourneyShell` has a new `celebratePairConfetti()` (two bursts
  converging from the upper corners + a small central follow-up),
  a `PAIR_CELEBRATED_KEY = "sacoparents_pair_celebrated"` flag,
  and a dedicated effect that fires exactly once when
  `pairProgress.paired && coparent_all_three_done` turn true.
- Toast title "{Name} completed their reflections too" (or a
  generic variant when the name is unavailable); description
  "You're both ready to carry the momentum into the joint report."
- The effect is decoupled from the current parent's own
  completion, so a parent can be nudged the moment their invited
  co-parent crosses the line.

No PDF or AI-service touch — clinical lockstep preserved.



### 2026-02-27 — Iter264 · Co-Parenting Journey Roadmap on Landing

Founder ask (via Figma-style mockup PNG): add a six-step
"YOUR CO-PARENTING JOURNEY" roadmap directly beneath the two
primary doors on the landing. Each row is a live tap-through to
the matching existing feature, with a green completion tick when
the parent has finished that step.

**Delivered — `door-journey-roadmap`**
A new section on the landing (below `door-court` + `door-self`),
with a horizontally-ruled section label and six tappable rows
styled per the mockup (number badge, icon tile, title, body,
chevron):

| # | Title | Handler | Completion signal |
|---|-------|---------|-------------------|
| 1 | Assess Your Situation | `onOpenSafety` | `progressByTopic.safety === "completed"` |
| 2 | Understand Your Relationship | `onOpenGuidedJourney("coparenting")` | `progressByTopic.coparenting === "completed"` |
| 3 | Identify Your Child's Needs | `onOpenGuidedJourney("educational")` | any of Educational/Medical/Psychological completed |
| 4 | Create Your Foundation Statement | `onOpenGuidedJourney("foundation")` | `progressByTopic.foundation === "completed"` |
| 5 | Prepare for Mediation | `openDoor("court")` | `!!courtKey` (court key verified) |
| 6 | Strengthen Communication | `onOpenBiffCoach` | `biffAuthoredCount > 0` |

Testids:
- `door-roadmap-{assess|relationship|child|foundation|mediation|communicate}`
- `door-roadmap-{key}-check` (green tick icon when completed)
- `data-completed="true|false"` on each row for test assertions.

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved. ESLint warnings unchanged.



### 2026-02-27 — Iter263 · Celebration Share + Partner Invite Nudge

Founder ask:
- "Celebration Share: Let a parent save a short celebration badge
  image after the finale so they can keep a tangible marker of
  their reflection milestone".
- "Partner Invite Nudge: After the finale, offer a one-tap invite
  to the other parent so the momentum carries into the joint
  report — provided that there is no family violence accusations".

Delivered inside `JourneyShell`:

**Finale rewards block — `door-self-finale-rewards`**
Rendered inside the Self Journey sub-view only when
`PRIMARY_MODULES.every(m => progressByTopic[m.topic] === "completed")`
— i.e. after the all-three finale has been earned.

**Celebration Share — `door-self-share-badge`**
- `renderCelebrationBadge(name)` draws a 1200×630 PNG on an
  off-screen canvas: purple gradient background, decorative dots,
  rounded card, brand pill `SA COPARENTS`, title `Reflection
  Milestone`, chip `A · B · C — Complete`, name line
  `Earned by {first-name}`, today's date, and the
  `sacoparentsapp.online` footer.
- `shareCelebrationBadge()` wraps the blob as a `File`, prefers
  `navigator.share({ files })` on mobile Safari / Chrome, and
  falls back to a direct `<a download>` click. Shows "Badge
  saved" success toast once the file is on disk.

**Partner Invite Nudge — `door-self-invite-partner`**
- Clinical guardrail (defence in depth): the chip is **not
  rendered** when `safetyFlag` is on (grey-rock active or DV
  flagged in `safetyAck`). The backend `/api/invites/coparent`
  endpoint ALSO enforces IPV clearance via
  `require_ipv_clearance`, so the parent cannot bypass by DOM
  manipulation.
- Tap opens a shadcn `Dialog` (`door-self-invite-dialog`) that
  wraps the existing `InviteCoparentCard` (variant `"summary"`),
  which handles the whole send flow: safety-gate check, rate
  limit, one-shot flag, success state. No new backend wiring.

No backend changes. No PDF or AI-service touch — clinical
lockstep preserved. ESLint warnings unchanged.



### 2026-02-27 — Iter262 · All-Three Finale + Celebration Replay

Founder ask:
- "All-Three Celebration: Fire a bigger confetti plus a special
  toast when all three primary modules are completed so the finale
  really lands".
- "Celebration Replay: Add a tiny 'Replay celebration' link in
  Report tab so parents can relive each completion whenever they
  want".

Delivered inside `JourneyShell`:

**All-three finale**
- New `celebrateFinaleConfetti()` fires two staggered confetti
  bursts from the left (x 0.2) and right (x 0.8) edges, 140
  particles each, 90° spread, 5-colour palette, 220 ticks — bigger
  than the per-module burst but still restrained for a clinical
  surface.
- A new `ALL_THREE_KEY = "sacoparents_all_three_celebrated"`
  localStorage flag de-dupes the finale.
- The existing celebration `useEffect` now also checks
  `PRIMARY_MODULES.every(m => completed)`; when true and the flag
  is unset, it schedules the finale after the per-module toasts
  (delay = `newly.length * 500 + 200` ms) and sets the flag.
- Toast title `"All three reflections complete"`, description
  `"A, B, and C are done. Your Foundation Statement is ready to
  review."`, 6.5-second duration.

**Replay celebration chip**
- New `door-self-replay-celebration` chip rendered inside the Self
  Journey sub-view directly under the Foundation Statement row
  (the closest surface to the retired "Report tab").
- `replayCelebration()` re-fires confetti + per-module toasts for
  every module currently marked `completed`, staggered 450 ms
  apart, with the toast description switched to
  `"Replay — your reflection stays saved privately."`. If all
  three are completed, the finale burst + a short-form finale
  toast ("Replay — A, B, and C are done.") plays last.
- Important: Replay does NOT touch `CELEBRATED_KEY` or
  `ALL_THREE_KEY`, so first-time auto-celebrations still run their
  own path on fresh devices.
- Empty-state fallback: tapping replay with no completed modules
  shows a neutral toast ("No celebrations to replay yet / Finish
  one of the three reflections to earn your first.").

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved.



### 2026-02-27 — Iter261 · Progress Celebrations + Switch-Door Chip

Founder ask:
- "Progress Celebrations: Show a subtle confetti plus toast when a
  parent completes a primary module so the sub-views reward
  momentum".
- "Door Memory Chip: Add a tiny 'Switch door' chip on the sub-views
  so parents can jump straight to the other door without going
  through the landing".

**Progress Celebrations**
- `canvas-confetti` (already in `package.json`) fires a quiet burst
  (60 particles, 70° spread, 0.75 y-origin, 150-tick duration) from
  the bottom-centre of the viewport whenever a primary A/B/C module
  transitions to `"completed"`.
- `sonner` toast at bottom-right (Toaster already mounted in
  `App.js`): title `"You completed {module title}"`, description
  `"Nice work. Your reflection is saved privately."`.
- A new `useEffect` in `JourneyShell` watches `progressByTopic` and
  diffs against a `CELEBRATED_KEY = "sacoparents_celebrated_modules"`
  localStorage array so each module celebration fires at most once
  per device. Stagger of 500 ms between simultaneous completions.
- `useRef` holds the current celebrated set in-memory so the effect
  doesn't re-fire when React batches renders.

**Switch-Door Chip**
- New `door-switch` chip rendered inside the shared `SubViewHeader`
  between the Back and Quick Exit buttons.
- Reads the current `view` and derives the opposite door; label and
  icon flip between "Switch to Court Ordered" (gavel) and "Switch to
  Self Journey" (door-open). Tapping it calls `openDoor(otherDoor)`,
  which both updates the view AND rewrites `DOOR_MEMORY_KEY` so a
  subsequent reload lands straight on the switched door.
- `data-target` attribute mirrors the destination door for test
  assertions.

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved.



### 2026-02-27 — Iter260 · Quick Exit + Door Memory

Founder ask:
- "Quick Exit In Doors: Add a tiny Quick Exit button back on both
  sub-views so parents in distress can leave even once they are
  deep inside a path".
- "Door Memory: Remember the last door the parent picked so
  returning parents land straight back in Self Journey or Court
  Ordered instead of the landing".

Delivered inside `JourneyShell`:

**Quick Exit — `door-quick-exit`**
- Rendered inside the shared `SubViewHeader` next to the Back
  button, visible on both the Court Ordered and Self Journey
  sub-views.
- Replaces the current tab with `https://www.weather.com/` via
  `window.location.replace`, the standard low-friction DV pattern.
  The Back button of the browser cannot bring the app back.

**Door Memory — `DOOR_MEMORY_KEY = "sacoparents_last_door"`**
- `useState` lazy-initialiser reads the key from localStorage so
  returning parents open the door they last picked without having
  to see the landing again. Values are strictly whitelisted to
  `"court"` or `"self"`.
- Picking either door writes the memory via `openDoor(next)`.
- Tapping Back calls `goBack()` which **clears** the memory before
  returning the parent to the landing — a deliberate exit must
  reset the memory so a returning session doesn't jump back into
  the sub-view they just left.

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved.



### 2026-02-27 — Iter259 · Two-Door Landing

Founder ask: "we need to simplify the first page - we need three
options - court ordered, self journey, after those two options...
After click under court ordered - safety first, choose option
a, b and c, and professional report invite from sacoparentsalign.com.
Under self journey - we need safety first, choose option a, b and
c and coparenting journey, along with self assessment and alignment
reports and foundation statements."

The 3-tab dashboard (iter258) is replaced by a two-door landing +
two lean sub-views. The SA CoParents Guide chatbot auto-open is
suppressed in `SacoparentsPortal` (`iter259` comment on the mount
effect); the modal itself is still reachable from the "Chat with
the Guide" chip inside Self Journey.

**Landing — `door-landing`**
Only two primary buttons: `door-court` (Court Ordered) and
`door-self` (Self Journey). Nothing else on the landing — no
banner, no tabs, no chatbot auto-open.

**Court Ordered — `door-view-court`**
- `door-back` (returns to the landing).
- `door-court-banner` (shown when a court key is verified).
- `door-safety-first` (opens the DV/IPV screen; grey-rock chip
  below when the parent is flagged).
- `door-court-abc`: three primary modules (`door-module-foundation`
  = Child Needs & Priorities, `door-module-coparenting` =
  Co-Parenting Dynamics, `door-module-safety` = Conflict
  Readiness). Each row shows the `completed`/`in_progress`/
  `not_yet` chip from `progressByTopic`.
- `door-court-pro-invite` panel with `door-court-pro-link` →
  `REACT_APP_ALIGN_SITE_URL` (default `https://sacoparentsalign.online`,
  opens in a new tab).
- `door-court-enter-key` chip (only when no court key is verified
  yet) → opens the existing court-key entry screen.

**Self Journey — `door-view-self`**
Section order (top to bottom), matching the founder's spec:
1. `door-safety-first` + optional grey-rock chip.
2. `door-self-abc` — same A/B/C modules.
3. `door-self-coparenting` — 40-Q co-parenting journey card.
4. `door-self-selfassessment` — 40-Q interactive preview (opens
   the static HTML preview in a new tab).
5. `door-self-alignment-{educational|medical|psychological}` —
   three alignment-report chips with completion ticks.
6. `door-self-foundation` — opens the Foundation drawer via
   `onOpenReport`.
7. `door-self-biff` — Communication Builder entry.
8. `door-self-chat-guide` (first-time only) — manual chatbot
   trigger so the Guide stays reachable.

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved. ESLint warnings unchanged.



### 2026-02-27 — Iter258 · 3-Tab Dashboard

Founder ask (via Tailwind HTML mockup): "we need to redo the
dashboard - with the three tabs - keeping the chatbot introduction
messages intact".

Full rewrite of `JourneyShell.jsx` from a 2-tile layout into the
founder's 3-tab dashboard. The auto-opened SA CoParents Guide
chatbot modal is rendered by `SacoparentsPortal` and is left
completely untouched.

**Layout (top to bottom)**
- `dashboard-banner` — dark gradient welcome + overall progress bar
  (`dashboard-progress-pct`; % = share of the three primary modules
  marked completed).
- `dashboard-controls` — a strip with:
  - `dashboard-mode-toggle` (Self-Guided ↔ Court-Ordered; opens the
    court access-key screen, auto-flips label once `courtKey` is
    verified).
  - `dashboard-privacy-btn` opens `dashboard-privacy-card` (what
    stays on your device explainer).
  - `dashboard-quick-exit` — DV best practice; replaces the page
    with `https://www.weather.com/`.
- `dashboard-court-banner` (when a court key is verified).
- `dashboard-safety-strip` — persistent on every tab:
  - `dashboard-safety-first` (always visible, opens DV/IPV screen).
  - Grey-rock chip (`AlignmentHub.GreyRockToggleChip`) only when
    `safetyFlag` is on.
- `dashboard-tabs` with three tabs: `dashboard-tab-reflect`,
  `dashboard-tab-report`, `dashboard-tab-coach`.

**Tab 1 — `dashboard-view-reflect`**
- `dashboard-open-intro-guide` — "Not sure where to start? Chat with
  the Guide" (opens the same intro guide modal — chatbot messages
  intact).
- `dashboard-cta-help` → inline `dashboard-help-card` with the 4
  "What brings you here today?" choices and the 3-way
  Educational/Medical/Psychological sub-choice stage.
- Reflection roadmap card with three primary modules:
  `dashboard-module-foundation` → Foundation (topic `foundation`),
  `dashboard-module-coparenting` → Co-Parenting Dynamics (topic
  `coparenting`), `dashboard-module-safety` → Conflict Readiness
  (opens the Safety screen). Each shows a `completed`/`in_progress`/
  `not_yet` chip and a context-sensitive CTA label
  (Review responses / Continue / Start). No hard-lock gating.
- `dashboard-preview-link` — the 40-Q interactive preview.
- `dashboard-deepdives` row — three deep-dive chips
  (`dashboard-deepdive-educational`, `-medical`, `-psychological`)
  with completion ticks when the parent has filed an align-record
  or snapshot for that topic.
- `dashboard-cta-commit` (first-time only).

**Tab 2 — `dashboard-view-report`**
- Foundation Statement Summary card with
  `dashboard-report-open` (opens the Foundation drawer via the new
  `onOpenReport` prop → `setFoundationDrawerOpen(true)`).
- "What's included" list.

**Tab 3 — `dashboard-view-coach`**
- Communication Builder block: `dashboard-cta-biff` (opens BIFF
  drawer), `dashboard-biff-info-btn` → `dashboard-biff-info-card`
  with the "What's a BIFF rewrite?" explainer and the Bill-Eddy
  book affiliate link, and `dashboard-biff-progress` growth-record
  chip.
- `dashboard-coach-deepdives` — the three deep-dive chips repeated
  here so parents in the Coach tab can jump to a child-focused
  journey without switching tabs.

**Progress signal**
- New `progressByTopic` memo in `SacoparentsPortal.jsx` derives
  completion from `snapshotHistory`, `foundationText` vs
  `DEFAULT_FOUNDATION`, `safetyAck`, and `alignmentCounts`. The dep
  array includes `guidedDraftsRev` so the memo re-evaluates when a
  draft is added/removed.

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved. ESLint warnings are the same long-standing ones from
earlier iters (intentional `guidedDraftsRev` dep included).



### 2026-02-27 — Iter257 · Help Me Choose + Deep-Dive Return

Founder ask:
- "Guided Entry Chip: Add a one-tap 'Help me choose' flow inside
  Self Journey that routes parents to the right assessment based
  on a single question".
- "Deep-Dive Return: Surface Educational, Medical and Psychological
  deep-dives as a tiny secondary row inside Self Journey so parents
  can still find them".

Delivered inside `JourneyShell` Self Journey expanded panel (no
backend / handler changes — reuses existing
`onOpenGuidedJourney(topic)`, `onOpenBiffCoach`, `onEnterCourt`
props):

**Help me choose (top of panel, above Privacy Check)**
- Collapsed chip `journey-path-self-cta-help` (purple outline).
- Opens inline card `journey-path-self-help-card` with the single
  question "What brings you here today?" and four choices:
  - `journey-help-choice-coparenting` → `onOpenGuidedJourney("coparenting")`
  - `journey-help-choice-communication` → `onOpenBiffCoach()`
  - `journey-help-choice-child` → reveals sub-stage with three
    buttons: `-child-educational`, `-child-medical`,
    `-child-psychological`, each routing via
    `onOpenGuidedJourney(topic)`. A `-child-back` link returns
    to the main stage.
  - `journey-help-choice-referral` → `onEnterCourt()`
- `helpStage` local state is set back to `null` (collapsed) on any
  terminal choice.

**Deep-Dive Return row (below the 40-Q preview, above Commit chip)**
- Container `journey-path-self-deepdives` with a small
  "Child-focused deep dives" label and a three-column grid of
  colored secondary chips:
  - `journey-deepdive-educational` (emerald) → `onOpenGuidedJourney("educational")`
  - `journey-deepdive-medical` (sky) → `onOpenGuidedJourney("medical")`
  - `journey-deepdive-psychological` (fuchsia) → `onOpenGuidedJourney("psychological")`

Verified at 390×844: all testids present, no horizontal overflow,
"Back" navigation works from the child sub-stage. No backend / PDF /
AI-service changes — clinical lockstep preserved.



### 2026-02-27 — Iter256 · Communication Builder nested inside Self Journey

Founder ask (via Flow-1 "Two Doors" HTML mockup): "we're going to
move the third tab - communication builder into an [option] which
will appear as an additional option when parents select self journey".

Delivered inside `JourneyShell`:
- Dashboard reduced to **two top-level paths**: Self Journey and
  Court Ordered. Communication Builder removed from the `PATHS`
  array (no more `journey-path-biff` tile at the top level).
- Communication Builder now lives inside the Self Journey expanded
  panel as `journey-path-self-cta-biff` (amber button). Attached to
  it: the "?" BIFF explainer (`journey-path-self-biff-info-btn` →
  `journey-path-self-biff-info-card`) with the Bill Eddy book
  affiliate link, and the growth-record chip
  (`journey-path-self-biff-progress`) showing "X messages reworked".
- Welcome copy updated from "Three ways in" → "Two ways in".
- Dead top-level biff progress block + the `handleCardClick`
  biff branch removed.

Order inside Self Journey panel (top to bottom):
Privacy Check → (Grey-rock chip when flagged) → Safety First →
Communication Builder (button + "?" explainer + growth record) →
Progress tracker (40-Q) → 40-Q preview → Commit chip (first-time
only).

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved.



### 2026-02-27 — Iter255 · Privacy / Grey-Rock / Safety inside Self Journey

Founder ask: "PRIVACY CHECK, GREY ROCK MODE AND SAFETY CHECK NEED TO
BE PRESENT AFTER PARENTS CHECK SELF JOURNEY, KEEP REMAINING 3 TABS
SELF JOURNEY COURT ORDERED AND COMMUNICATION BUILDER".

Delivered inside `JourneyShell` Self Journey expanded panel:
- `journey-path-self-cta-privacy` — new indigo button, taps open an
  inline explainer (`journey-path-self-privacy-card`) describing what
  stays on the device, what syncs, what is never shared.
- Grey-rock chip stays visually above Safety First when `safetyFlag`
  is on (behaviour unchanged — still only shown when flagged).
- `journey-path-self-cta-safety` — renamed from "Private Safety Check"
  → "Safety First"; still routes to the DV/IPV screen via `onOpenSafety`.
- Progress tracker (40-Q) and 40-Q preview remain below.
- Three main tabs on the dashboard untouched (Self Journey / Court
  Ordered / Communication Builder).

No backend changes. No PDF or AI-service touch — clinical lockstep
preserved.



### 2026-02-27 — Iter250 · Draft-to-Snapshot

Founder ask: "Add a one-tap action inside the BIFF drawer to
file the raw-first-draft + BIFF-rewrite pair into the Snapshot
Library, so a mediator can see the actual tone progression."

**🟢 P1 — New `biff_pair` snapshot topic**
- Backend: `_GUIDED_TOPICS` whitelist in
  `/app/backend/portal_routes.py` extended with `"biff_pair"`.
  Everything else stayed intact — the sanitizer's existing
  per-entry byte cap (12 KB), answer length cap (2000 chars),
  and 12-item history cap all apply unchanged. Zero new fields,
  zero new routes.
- Reuses the existing `answers: [{question, answer}, ...]`
  shape:
    * `answers[0] = {question:"Original message", answer:rawInput}`
    * `answers[1] = {question:"BIFF rewrite",     answer:biffOutput}`
- Frontend: `SnapshotStrip.jsx` adds `biff_pair` to
  `TOPIC_LABEL` ("BIFF rewrite") and `TOPIC_ICON`
  (`fa-wand-magic-sparkles`). All existing rename / pin /
  delete / share flows work on BIFF snapshots unchanged.

**🟢 P1 — Draft-to-Snapshot card inside BiffCoachDrawer**
- New card rendered BELOW the BiffTab content so the parent
  sees the rewrite first, then the save CTA. Testids:
    * `biff-draft-to-snapshot-card` — the card container.
    * `biff-save-snapshot-btn` — the primary CTA. Disabled
      with greyed-out styling until BOTH `rawInput` and
      `biffOutput` are non-empty.
    * `biff-save-snapshot-hint` — emerald confirmation line
      appears after a successful save ("Saved — view it in
      your Snapshot Library on Step 5.")
- On tap, calls `onSaveBiffSnapshot({raw, biff})` which
  returns a boolean. On success, fires a sonner toast:
  _"Filed to your Snapshot Library. Your mediator will see
  the before and after when you share it next."_

**🟢 P1 — `onSaveBiffSnapshot` handler (SacoparentsPortal.jsx)**
- Builds the `biff_pair` entry with the standard id
  (`Date.now()`), `safety_flagged` from the current
  `safetyFlagged` state, prepends to `snapshotHistory`
  (capped at `SNAPSHOT_HISTORY_MAX`), mirrors to
  `localStorage` via `writeJson(SNAPSHOT_HISTORY_KEY, ...)`.
  The existing debounced `PUT /api/portal/state` round-trip
  picks up the change and persists server-side.
- Guards: if either raw or biff trims to empty, returns
  `false` without side-effects. The drawer's `canSave`
  flag mirrors the same check at the UI level.

**Clinical lockstep invariant preserved**
- Zero changes to the BIFF rewrite logic, grey-rock variant,
  safety guardrails, PDF generation, or AI prompts. The
  Draft-to-Snapshot card is a thin new UI layer plus one
  whitelist add on the sanitizer.

**Verified end-to-end at 390×844 mobile**
- Open BIFF drawer → Draft-to-Snapshot card renders →
  save button DISABLED initially (`save_btn_disabled=1`).
- Fill raw input + click Rewrite (AI generates BIFF
  output) → save button ENABLES (`can_save=1`).
- Click save → toast fires + emerald hint appears
  (`hint=1 toast=1`) + localStorage carries one new
  `biff_pair` entry (`biff_pair_in_history=1`).
- Snapshot shape verified in localStorage: topic
  `"biff_pair"`, answers has both "Original message" and
  "BIFF rewrite" entries, `safety_flagged: false`,
  `save_key: biff_pair_<id>`.
- No horizontal overflow (sonner `<ol>` same as iter243/245
  — not an app layout bug).

**Next iters (unchanged)**
- iter251: Mediator Progress PDF reads `biff_pair`
  snapshots and renders a tone-progression table.
- iter252: Progress dot tooltips.
- iter253: True-delete `AlignmentHub.jsx` + `DoorsGateway.jsx`.


### 2026-02-27 — Iter249 · DevOps Split (code-side) + Progress Dots

Two deliverables shipped together: the architectural
preparation for the two-domain production split, and the
glanceable 5-dot progress strip at the top of the shell.

**🟢 P1 — DomainGuard (code-side DNS split preparation)**
- New `/app/frontend/src/components/DomainGuard.jsx`. Reads
  `window.location.hostname` + env-configured production
  hostnames; if the current host doesn't match the side a
  route belongs to, renders a 2.5-second redirect card
  (testid `domain-guard-redirect`) with a manual escape
  button (`domain-guard-go-now`) and then auto-forwards
  to the correct hostname with path + query preserved.
- No-op by design when either `REACT_APP_PARENT_HOSTNAME` or
  `REACT_APP_ALIGN_HOSTNAME` is missing (preview, localhost,
  staging all pass through untouched). Verified on preview:
  `domain_guard_shown=0 shell_shown=1`.
- Env config in `/app/frontend/.env`:
    * `REACT_APP_PARENT_HOSTNAME=sacoparentsapp.online`
    * `REACT_APP_ALIGN_HOSTNAME=sacoparentsalign.online`
    * `REACT_APP_PARENT_URL=https://sacoparentsapp.online`
    * `REACT_APP_ALIGN_URL=https://sacoparentsalign.online`
- Routes wrapped in `/app/frontend/src/App.js`:
    * `/`     → `<DomainGuard side="parent">`
    * `/align` → `<DomainGuard side="align">`
    * `/admin` → `<DomainGuard side="align">`
- `/app/memory/DEPLOYMENT.md` (new) — complete DNS / ingress /
  TLS runbook the account owner can hand to DevOps. Covers:
  Kubernetes ingress excerpt, A/CNAME records, cert-manager
  config, verification curl commands, rollback.

**🟢 P1 — Step Progress Dots**
- `ProgressDots` component inside
  `/app/frontend/src/pages/portal/JourneyShell.jsx`. Rendered
  between the welcome card and the (optional) grey-rock
  banner so a parent sees their progress strip BEFORE
  scrolling the step cards.
- 5 dots + connector segments + `filledCount/5` counter chip.
  Fill signals (one per step, driven by actual completion,
  not by the current-step cursor):
    * Dot 1 "Started"  → `pathPickedAt` (any door chosen)
    * Dot 2 "Checked"  → `safetyAck` (any — flagged or cleared)
    * Dot 3 "Assessed" → `firstEngagementAt` (any assessment opened)
    * Dot 4 "Explored" → `biffUsedAt` (parent authored at least one
      BIFF rewrite beyond the demo seed; signal computed as
      `biffLogs.length > 1` in SacoparentsPortal)
    * Dot 5 "Planned"  → `snapshotCount > 0` (any snapshot saved)
- Visual: filled dot = purple-700 bg + white checkmark;
  empty dot = slate-100 bg + numbered 1-5 + slate border.
  Connector between adjacent filled dots = purple-700/60;
  else slate-200.
- Testids: `journey-progress-dots`, `journey-progress-dot-{1..5}`
  (plus `data-filled="true|false"` attribute),
  `journey-progress-count`.

**Verified at 390×844 mobile across three journey states**
- Fresh parent: `filled=[0,0,0,0,0] counter=0/5` — all empty.
- Partial: `filled=[1,1,1,0,0] counter=3/5` — dots 1-3 filled.
- Advanced: `filled=[1,1,1,1,1] counter=5/5` — all 5 filled,
  all connectors purple.
- No horizontal overflow at either viewport.

**Clinical lockstep invariant preserved**
- DomainGuard renders only a redirect card — never touches
  clinical screens or copy.
- ProgressDots is a pure derivation from existing signals;
  no new state, no new backend route, no PDF/AI touch.


### 2026-02-27 — Iter248 · Phase B Tail Inlined + BIFF Grey-Rock Mirror

Final architectural cleanup. The `screen === "parent-journey"`
code path — along with its hub-tabs toggle (`alignment` /
`biff`), the inline SafetyRetakeChip, the AlignmentHub tile
grid, and the BiffTab wrapper — has been deleted. The parent-
facing surface is now exclusively the five-step JourneyShell +
three modal drawers.

**🟢 P1 — JourneyDrawers module (new)**
- `/app/frontend/src/pages/portal/JourneyDrawers.jsx` exports
  three bottom-sheet drawer wrappers that share a `DrawerShell`
  (body-scroll lock + ESC-to-close + rounded-top mobile sheet):
    * **BiffCoachDrawer** (`biff-coach-drawer` testid) wraps the
      existing `<BiffTab>` verbatim. Zero changes to BiffTab or
      its handlers.
    * **RecordsDrawer** (`records-drawer`) renders the Alignment
      Records section (folders filter + records grid + empty
      state) — JSX lifted from AlignmentHub, props threaded
      through unchanged (`folderFilter`, `setFolderFilter`,
      `alignmentCounts`, `filteredRecords`, `onAddAlignment`).
      Testids preserved verbatim (`assessment-records-section`,
      `folder-medical/educational/psychological`,
      `count-*`, `clear-folder-filter`, `add-alignment-btn`,
      `assessment-empty-*`).
    * **FoundationDrawer** (`foundation-drawer`) renders the
      Foundation Statement textarea + Save / PDF / Share +
      email-to-coparent guardrail. All existing testids
      preserved (`foundation-text`, `save-foundation-btn`,
      `export-foundation-pdf-btn`, `share-foundation-btn`,
      `foundation-email-coparent-blocked`,
      `email-foundation-coparent-btn`). iter219 safety guardrail
      — Email to Co-parent is BLOCKED when `safetyFlagged` —
      ships intact.

**🟢 P1 — BIFF Grey-Rock Mirror (iter248 ask)**
- `BiffCoachDrawer` renders the full `<GreyRockToggleChip>` at
  the top of the drawer body (between the SafetySoftBanner and
  the BIFF content) when `safetyFlagged === true`. A parent
  revising a BIFF message no longer has to navigate back to
  Step 2 to turn grey-rock off.
- Reuses the SAME iter243 `GreyRockToggleChip` component,
  `onClearGreyRock` + `onOpenSafetyRetake` handlers, and the
  iter245 grey-rock audit backend log. One source of truth,
  mirrored into a second surface.
- End-to-end verified: toggle inside BIFF drawer → confirm → yes
  → `safety_ack = {cleared:true, flagged:false}` persisted,
  toast fires, BiffTab's internal "GREY-ROCK COACH ON" header
  reverts to "De-Escalation Engine" immediately (same safety
  flag used by both surfaces).

**🟢 P1 — Delete parent-journey screen**
- `screen === "parent-journey"` render block (166 lines)
  removed from SacoparentsPortal.jsx. Lines 1724-1890 deleted.
- `hubSection` / `setHubSection` state removed entirely —
  dead after the hub-tabs died.
- `setScreen("parent-journey")` call sites rerouted:
    * Door entry (`requestDoorEntry`) now sets `setScreen("journey")`.
    * `onSafetyCleared` + `onSafetyContinueFlagged` with
      `pendingDoorRef = "parent"` now set `setScreen("journey")`.
    * `verifyProfessionalKey` success already sets `journey`
      (iter246 Phase C).
- `onStartAssessment("communication")` now opens the BIFF
  Drawer directly instead of switching hub-section + entering
  parent-journey.
- Dead imports removed (`AlignmentHub`, `BiffTab`).

**🟢 P1 — Bottom-nav wired to drawers**
- `nav-report` → opens FoundationDrawer. The parent's primary
  "report" artefact is the Foundation Statement PDF; no other
  nav choice calls itself a report.
- `nav-biff` → opens BiffCoachDrawer directly.
- Active-state styling driven by drawer open state, not by
  `screen` + `hubSection` gymnastics.

**Clinical lockstep invariant preserved**
- Zero changes to SafetyScreen, AI service, PDF builders,
  grey-rock chip component, iter219 email-coparent guardrail,
  Safety-First auto-routing, or any clinical copy.
- Every drawer invokes the EXACT handler the old parent-
  journey screen called. The only change is where in the UI
  the handler is invoked from.
- AlignmentHub.jsx + the records-section JSX inside it
  remain on disk unimported (webpack tree-shakes). A future
  true-delete iter can `rm` the file once there's no
  rollback risk; keeping it this iter is zero-cost.

**Verified at 390×844 mobile**
- BiffCoachDrawer opens from Step 4 CTA + bottom-nav. Grey-rock
  mirror chip renders when flagged, two-step-confirms, clears
  grey-rock, toast fires, BIFF content flips variant.
- RecordsDrawer opens from Step 3 CTA. 3 folders render with
  correct counts. Empty state renders when no records.
- FoundationDrawer opens from Step 5 CTA + bottom-nav. Textarea
  renders with current text. Save / PDF / Share buttons work.
  Email-to-coparent BLOCKED when flagged, enabled otherwise.
- `data-testid='screen-parent-journey'` NOT in DOM anywhere.
- No horizontal overflow (only sonner `<ol>` internal element,
  same as iter243 — not an app layout bug).

**Next phases (updated)**
- Phase E (DevOps): split prod to `sacoparentsapp.online` +
  `sacoparentsalign.online`.
- iter249: Render the grey-rock audit timeline on the
  Mediator Progress PDF (`cp_progress_pdf.py`). The audit
  backend built in iter245 was explicitly for this.
- iter250: True-delete `/app/frontend/src/pages/portal/AlignmentHub.jsx`
  + `DoorsGateway.jsx` once rollback risk window closes.


### 2026-02-27 — Iter245-247 · Phase B/C/D + Grey-Rock Audit Log

Four deliverables landed in one session, in dependency order:

**🟢 Backend — Grey-Rock Audit Log (new)**
- New `/app/backend/grey_rock_audit.py` module. Mongo
  collection `grey_rock_audit` with doc shape:
  `{user_id, event: "on"|"off", source: "safety_screen"|"toggle_chip"|"import", at: ISO 8601 UTC}`.
- Routes mounted at `/api/portal/grey-rock/*`:
    * `POST /audit` — appends one transition event (401 if
      unauthenticated).
    * `GET /audit` — returns newest-first list, capped at 200
      events (plenty for the mediator PDF timeline).
- Server-side timestamp (`datetime.now(timezone.utc)`) — client
  clock drift can't tamper with the clinical timeline.
- Frontend wiring in `SacoparentsPortal.jsx`:
    * `onSafetyContinueFlagged` → POST `{event:"on", source:"safety_screen"}`
    * `onClearGreyRock` → POST `{event:"off", source:"toggle_chip"}`
    * Fire-and-forget via `api.post(...).catch(()=>{})` so a
      network blip never blocks the Safety-First routing.
- End-to-end tested via curl (`parent1@test.com`): POST on →
  POST off → GET list returns both events in newest-first
  order.

**🟢 Phase B — Toolkit Merged Into Step Panels**
- `/app/frontend/src/pages/portal/JourneyShell.jsx` step panels
  rewritten to render rich inline CTAs that invoke the SAME
  handlers the old AlignmentHub tiles used — zero PDF/AI/report
  code touched, every existing testid on existing components
  preserved.
- Step 2 "Understand My Situation" panel:
    * `journey-step-2-cta-safety` → opens SafetyScreen modal
    * Inline `<GreyRockToggleChip>` (only when flagged) — the
      iter243 toggle moved INTO Step 2 where it belongs
    * `journey-step-2-cta-progress` → `onOpenGuidedJourney("coparenting")`
      (the 40-Q profile also doubles as the progress tracker)
    * `journey-step-2-cta-preview` → external link to the
      static 40-Q interactive HTML preview
- Step 3 "Focus on My Child" panel:
    * Court-verified banner (`journey-step-3-court-banner`)
      visible when a court key is present
    * `journey-step-3-cta-coparenting` (emerald CTA) →
      `openGuidedJourney("coparenting")`
    * 3-column secondary grid: Educational / Medical /
      Psychological, each wiring to `openGuidedJourney(topic)`
    * `journey-step-3-cta-records` → `openAssessmentFolder("All")`
      + routes into parent-journey screen for the folder list
      (iter247 will inline the folder too)
- Step 4 "Explore Options" panel:
    * `journey-step-4-cta-biff` → `setHubSection("biff")` +
      enter parent-journey screen (BIFF Coach is still a
      heavy UI; a future iter can modal-ise it)
    * `journey-step-4-cta-mediation` → mediation-prep script
- Step 5 "Create My Plan" panel:
    * `journey-step-5-cta-foundation` → opens Foundation
      Statement textarea (scrolls to `#foundation-statement-section`
      anchor added in AlignmentHub)
    * `journey-step-5-cta-download-complete` →
      `downloadCompleteReportPdf`
    * `journey-step-5-cta-share-complete` → `onShareCompleteReport`
      (email to mediator)
    * Snapshot count hint when the parent has existing snapshots
- Fix: shell's `expanded` state now initialises to `null` and
  falls through to `pickCurrentStep` dynamically, so the
  shell auto-expands the correct step even when `courtKey` /
  `safetyAck` hydrate from localStorage AFTER mount.

**🟢 Phase C — Court Fast-Forward**
- `verifyProfessionalKey` success handler routes to the
  Journey shell (`setScreen("journey")`) instead of dumping
  the parent in the legacy parent-journey screen's artefact
  grid.
- `pickCurrentStep` updated: a verified court key auto-
  elevates to Step 3 as the "You're here" step. The court
  banner renders with Case ID + mediator name inside Step 3's
  panel, so a referred parent sees: "Court access verified:
  Case SA-DEMO01 · [Mediator]. Your assessment feeds the
  mediator's joint report."
- End-to-end verified: localStorage `court_key=SA-DEMO01` →
  shell lands on Step 3 "You're here" → banner renders → 4
  assessment CTAs visible inline (Co-Parenting, Educational,
  Medical, Psychological) with Alignment Records as a
  secondary.

**🟢 Phase D — Legacy Deleted**
- `?view=advanced` kill-switch removed. `advancedView` state
  deleted from `SacoparentsPortal.jsx`.
- `DoorsGateway` import removed; the `screen === "gateway"`
  render block removed in its entirety. (The component file
  stays on disk unimported — Webpack tree-shakes it out of
  the production bundle; a hypothetical future true-delete
  would just `rm` the file.)
- "Advanced view (legacy)" link + `journey-advanced-view-link`
  testid removed from JourneyShell.jsx.
- `openDoorGateway` simplified to `setScreen("journey")` with
  no advanced branch.
- Bottom-nav "Journey" button's active state no longer checks
  for `screen === "gateway"` (which can't happen).
- `showBackBtn` simplified to `screen !== "journey"`.
- Verified: `/?view=advanced` now renders the shell exactly
  like `/`. The old gateway and DoorsGateway cannot be
  reached from the UI at all.

**Clinical lockstep invariant preserved**
- Zero touch to SafetyScreen, AI service, PDF builders,
  Grey-rock chip component, or any clinical copy.
- Every tile CTA invokes the SAME handler the old
  AlignmentHub tile called (`openGuidedJourney`,
  `openAssessmentFolder`, etc.) — behaviour identical, just
  shelved under the right step.
- SAST/CORS warnings still ignored per founder standing rule.

**Verified at 390×844 mobile**
- Phase B: Step 2 panel renders safety + progress + preview
  CTAs; Step 3 renders coparenting + 3-col topics + records;
  Step 5 renders foundation + download + share.
- Phase C: `court_key=SA-DEMO01` → shell auto-expands Step 3
  + banner reads "Court access verified: Case SA-DEMO01…" +
  4 assessment CTAs inline.
- Phase D: `/?view=advanced` returns the shell (not the
  old gateway); `door-parent-journey` testid gone from DOM.
- No horizontal overflow at any step.
- Audit log: 2 live events (`on` + `off`) retrieved via
  authenticated GET.

**Next phases (updated)**
- Phase E (DevOps): Split prod to `sacoparentsapp.online` +
  `sacoparentsalign.online`.
- iter248: inline the BIFF Coach INTO Step 4 panel (currently
  still routes to the heavy parent-journey screen for the
  modal). Same for Alignment Records in Step 3.
- iter249: render the grey-rock audit timeline on the Mediator
  Progress PDF (`cp_progress_pdf.py`) so the clinical artifact
  the audit log was built for actually surfaces.


### 2026-02-27 — Iter244 · Phase A: Five-Step JourneyShell + /align scaffold

Strategic turn: the app has grown feature-rich at the cost of
parent-brain simplicity. Standing from this iter forward, the
architecture obeys ONE rule (NORTH_STAR.md):

> The parent should never have to understand the structure of
> the app. The app should understand where the parent is and
> guide them.

Every parent-facing surface now fits under one of five journey
steps. Every professional surface moves under `/align`. Two sites,
rigid separation, no leaks.

**🟢 P1 — NORTH_STAR.md**
- New `/app/memory/NORTH_STAR.md` captures the 5-step scaffold,
  the two-site distinction, and the committed phase plan (A → E).
  Future forks read this before touching UI chrome.

**🟢 P1 — JourneyShell (parent-facing default)**
- New `/app/frontend/src/pages/portal/JourneyShell.jsx` renders
  the 5 steps as a vertical card list:
    1. Start My Journey (purple)
    2. Understand My Situation (indigo)
    3. Focus on My Child (emerald)
    4. Explore Options (amber)
    5. Create My Plan (rose)
- Each step card is tappable → expands a panel with context +
  one or two CTAs that route into the existing surfaces. The
  tools underneath (SafetyScreen, CpProgressTile, AlignmentHub,
  BiffTab, Guided Journey, Foundation Statement, Snapshot
  Library) are reused VERBATIM — no PDF/AI/report code touched.
- "You're here" chip auto-picks the current step from signals
  the container already tracks (`PATH_PICKED_KEY`,
  `FIRST_ENGAGEMENT_KEY`, `snapshotHistory.length`, `safetyAck`).
  New user → Step 1; returning user with snapshots → Step 4.
- Grey-rock soft banner surfaces at the top of the shell when
  `safetyFlagged === true` so a parent in grey-rock mode knows
  the state before tapping any step. Mirrors the Alignment Hub
  chip without duplicating logic.
- Step 1 has two doors as sibling cards (same handlers the old
  Gateway used, so the Safety-First gate still fires):
    * Voluntary (purple) → `enterParentJourney`
    * "I was sent here" (amber) → `enterCourtPath`

**🟢 P1 — SacoparentsPortal.jsx wiring**
- New `screen === "journey"` state is the DEFAULT. The old
  gateway is reachable at `/?view=advanced` as a kill-switch
  for 2-3 iters (deletable in Phase D).
- `openDoorGateway` routes to the journey screen (not the
  legacy gateway) unless `?view=advanced` is in the URL.
- Bottom-nav "Doors" button renamed "Journey" with a compass
  icon so the parent-facing navigation reads as a path, not a
  room selector. Active state covers both `journey` and
  `gateway` screens for continuity.
- Header back button copy flipped "Doors" → "Journey".
- IntroChatBot auto-open preserved verbatim — Phase A doesn't
  touch the welcome triage, just the surface it lands on.

**🟢 P1 — Align landing (`/align`)**
- New `/app/frontend/src/pages/Align.jsx` scaffolds the
  professional entry at `/align`. Slate + emerald visual
  language (intentionally different from the parent portal's
  purple/rose). Content:
    * Header: "Professional Workspace · SA CoParents Align"
    * Role explainer line linking back to `/` for parents who
      landed here by mistake
    * 4 tiles: Case Dashboard (`/admin`), Joint Reports
      (`/joint-reports`), Reviewer Workbench
      (`/admin/reviewers`), Sample Reports (`/samples`)
    * Compliance footer naming HB 300 / HIPAA / BAA — correct
      language for professionals, never surfaced on the
      parent portal
- `/app/frontend/src/App.js` registers the `/align` route.
- No new backend routes; this re-frames surfaces that already
  exist. DNS split to `sacoparentsalign.online` is DevOps
  Phase E.

**Verified at both viewports**
- Mobile 390×844: Shell renders at `/`; Step 1 "You're here"
  chip visible; Step 1 panel shows voluntary + court doors;
  Step 2 panel shows "Private Safety Check" + workspace CTAs;
  `?view=advanced` returns the old DoorsGateway (door-parent-
  journey testid intact); `/align` renders landing with 4
  tiles. No horizontal overflow.
- Desktop 1920×800: Shell max-w-md column centered; Align
  landing renders 2×2 tile grid; no overflow.
- Smoke-tested: `shell=1, step1=1, step5=1, current_count=1,
  adv_link=1, step2_panel=1, doors voluntary=1 court=1,
  advanced: gateway_doors=1 shell=0, align_landing=1 tiles=4`.

**Clinical lockstep invariant preserved**
- Zero changes to SafetyScreen, AI service, PDF builders,
  Grey-rock chip, or any clinical copy.
- All existing testids on existing components untouched.
- Safety-First auto-route still fires via `enterParentJourney`
  / `enterCourtPath` — the same handlers the old Gateway
  called.

**Next phases (committed)**
- Phase B (iter245): Merge toolkit tile grid INTO the steps.
  Delete the horizontal hub-section tab switcher.
- Phase C (iter246): Court-Ordered Step 1 variant fast-
  forwards to the referred artefact after Court Key verify.
- Phase D (iter247): Delete legacy DoorsGateway code path +
  `?view=advanced` escape hatch.
- Phase E (DevOps): Split prod to `sacoparentsapp.online` +
  `sacoparentsalign.online`.


### 2026-02-27 — Iter243 · Grey-rock Toggle Chip on Alignment & Tools

Founder ask: "Grey-rock Mode Toggle: Add a one-tap 'Turn grey-rock
off' chip on Alignment & Tools once safety has stabilized — the
modal already promises this control exists, so build it to match
the promise."

Context: `SafetyScreen.jsx:332` promises *"You can turn it off
from the Alignment & Tools page any time."* — but no such control
existed. The only path out of grey-rock mode was re-running the
full Safety Screen questionnaire. This iter closes the loop.

**🟢 P1 — GreyRockToggleChip component**
- New named export in `/app/frontend/src/pages/portal/AlignmentHub.jsx`.
  Amber chip (shield-halved icon + "Grey-rock mode is on." headline
  + "Tools and language are quietly adapted." subhead + "Turn off"
  button). Two-step confirm pattern prevents a single mis-tap from
  disabling the clinical guardrail:
    * Confirm card copy: *"Are you back on safe ground?"* +
      "Turning grey-rock off brings back full tool language and
      lets you email the co-parent again from the Portal. You can
      turn it back on any time by re-running the Safety Check."
    * Primary "Yes, turn grey-rock off" (amber solid) +
      secondary "Not yet" (amber outline) + tertiary link
      "Re-run the full safety check instead" (routes back into
      the full Safety Screen modal via `onOpenSafetyRetake`).
- Testids: `grey-rock-toggle-chip` /
  `grey-rock-toggle-off-btn` / `grey-rock-toggle-confirm` /
  `grey-rock-toggle-confirm-yes` /
  `grey-rock-toggle-confirm-cancel` /
  `grey-rock-toggle-retake-link`.
- Rendered only when `safetyFlagged === true`, inside the
  Coparenting Journey Toolkit card, between the SnapshotStrip
  and the inline Assessment Guide — so a returning parent in
  grey-rock mode sees it before any other control.

**🟢 P1 — Container plumbing**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — new
  `onClearGreyRock` callback (sibling to the existing
  `onSafetyCleared`). Unlike `onSafetyCleared` it does NOT
  touch `pendingDoorRef` or `setScreen` — it only writes
  `safety_ack = {cleared:true, flagged:false}` to localStorage
  and `setSafetyAck`, so the parent stays exactly where they
  are. The debounced `PUT /api/portal/state` pipeline persists
  the clear across devices.
- `AlignmentHub` receives two new props: `onClearGreyRock`
  (chip "Yes" wire) and `onOpenSafetyRetake` (reuses the
  existing retake handler for the tertiary link).

**Clinical lockstep invariant preserved**
- Reuses the existing `safety_ack` schema — single source of
  truth for the flag.
- No new SafetyScreen variant, no new triage questions, no
  new modal copy. The modal's existing promise is honoured
  verbatim; no copy changes needed anywhere else.
- Backend sanitizer already whitelists `safety_ack.cleared`
  and `safety_ack.flagged` — no backend route changes.

**Verified at both viewports**
- Mobile 390×844: chip renders at the top of the toolkit;
  Turn off → confirm card; Cancel keeps chip; Yes clears
  chip + flips AssessmentGuideChat header from "GREY-ROCK"
  back to "ASSESSMENT GUIDE" (proving `safetyFlagged` state
  propagated). localStorage `safety_ack` round-trips
  cleanly to `{cleared:true, flagged:false}`.
- Desktop 1920×800: chip renders left-aligned at
  `max-w-md` card width, no overflow.
- No horizontal overflow at either viewport.


### 2026-02-27 — Iter242 · Safety-First button moved from Gateway to both paths

Founder clarification: "the family violence button — should be
renamed Safety First — remove it from the first dashboard — when
parents select individual journey or court-ordered — include safety
first button on both paths."

**🟢 P1 — Removed from Gateway**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — the iter239
  `gateway-safety-first-btn` block was deleted from the
  `screen === "gateway"` render. The Gateway is now focused on
  the single decision (Individual Journey vs Court-Ordered Path)
  with just the Guide chat chip and the two Doors.

**🟢 P1 — Added to both paths**
- `screen === "court-key"` now renders a Safety-First card
  (test id `court-safety-first-btn`) ABOVE the Enter Professional
  Access Key input. Sets `pendingDoorRef.current = "court"` so a
  flagged safety submission lands inside the Court-Ordered flow.
- `screen === "parent-journey"` renders the same Safety-First
  card (test id `parent-safety-first-btn`) as the first element
  of the Individual Journey, before the court-verified banner,
  tabs, SafetyRetakeChip or any toolkit. Always visible — even
  when `safetyFlagged === true` the button stays rendered with
  adaptive sub-copy ("Re-run the private safety check — crisis
  hotlines and the grey-rock path are still one tap away.") so a
  parent in grey-rock mode has a one-tap re-check without having
  to hunt for the thin retake chip.
- Both buttons reuse the SafetyScreen modal (`setSafetyOpen(true)`)
  and the iter241 flagged-exit auto-route logic, so clinical
  guardrails are preserved verbatim.

**UI framing**
- Primary label: **"Safety First"** (was "Start here if you have
  family-violence or IPV concerns" headline + "SAFETY FIRST" eyebrow
  pill in iter239 — now simply "Safety First" as the primary line).
- Secondary line (adaptive): "Short, private safety check — crisis
  hotlines and a grey-rock path if family-violence or IPV concerns
  are present." (not-yet-flagged) OR the re-run copy (flagged).
- Rose gradient card, shield-heart icon, arrow-right chevron,
  identical visual on both paths.

**Verified at 390**
- Gateway: `gateway-safety-first-btn` count = 0.
- Parent-Journey: button renders at y=86, 358x75 px, click opens
  the Quick Safety Check modal.
- Court-Ordered: button renders at y=86, 358x88.5 px, above the
  Enter Professional Access Key card.
- No horizontal overflow on either path.


### 2026-02-27 — Iter241 · Safety-First auto-route · Preview-to-Account · Branded Profile PDF · Self Assessment tile

Four tightly-related follow-ups shipped together.

**🟢 P1 — Safety-First auto-route (intimidation=yes locks the exit)**
- `/app/frontend/src/pages/portal/SafetyScreen.jsx` — when
  `coerce === "yes"` on the Quick Safety Check:
    * The flagged-card footer copy flips from the generic
      "You can still enter the Portal" to a protective-wording
      explainer: "Grey-rock mode is on — the Portal will quietly
      adapt its tools and language so nothing you do here can be
      used against you. You can turn it off from the Alignment &
      Tools page any time."
    * The "Continue to the Portal anyway" button relabels to
      "Enter the Portal in grey-rock mode".
    * The "Close" button relabels to "Not now" AND its onClick
      now calls `onContinueFlagged` instead of `resetAndClose`,
      so a parent in a flagged state can't exit the modal into
      an unprotected gateway. Both buttons route to grey-rock.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — the Gateway
  Safety-First button now pre-seeds `pendingDoorRef.current =
  "parent"`, so `onSafetyContinueFlagged` lands the parent
  inside the Parent Journey (grey-rock) instead of back on the
  Gateway when the button was opened directly (not via a Door).
- Verified: filling `coerce=yes` + clicking "Not now" landed on
  Alignment & Tools (gateway button count 0, toolkit tiles
  count 2) with 3 SafetySoftBanner instances rendering —
  grey-rock mode confirmed active.

**🟢 P1 — Preview-to-Account save**
- `/app/backend/coparenting_routes.py` — two new auth-aware
  Pydantic models (`PreviewProfileScoreRow`,
  `PreviewProfileReflection`, `PreviewProfileRequest`) and two
  new routes:
    * `POST /api/coparenting/preview-profile/pdf` — public (no
      auth); accepts posted scores + reflection, returns the
      branded one-page PDF so the HTML form can offer a
      download.
    * `POST /api/coparenting/preview-profile/save` — auth
      required; writes a snapshot into the SAME
      `cp_report_history` collection the 70-question flow uses,
      with stable section ids `d_0..d_7` and extra fields
      `source: "preview"` + the three reflection answers.
      Section ids are distinct from the 70-question `s1..s10`
      ids so `_pick_baseline` / `_section_movers` only match
      preview-to-preview and report-to-report (mixing is
      silently ignored, which is correct — the two assessments
      aren't comparable).
- `/app/frontend/public/coparenting-self-assessment-preview.html`:
    * New results-panel action strip with two buttons
      ("Download my profile (PDF)" ghost + "Save to my account"
      solid). Toast strip underneath for success/error states.
    * `wireResultActions(results)` fires inside
      `displayResults` to bind both buttons to the computed
      scores. `collectPayload` serialises scores + the three
      reflection textareas; `downloadProfilePdf` POSTs to the
      PDF route and streams the result into an anchor-click
      download; `saveToAccount` POSTs to the save route with
      `credentials: "include"` so the same-origin httpOnly
      session cookie carries.

**🟢 P1 — Branded one-page Profile PDF**
- `/app/backend/cp_preview_profile_pdf.py` — new sister module
  to `cp_progress_pdf.py`. Single-page portrait with: overall
  rating card (coloured to the band), per-domain progress bars
  (purple-filled against ivory track, 8 rows), Profile Summary
  (strengths and areas-to-attention), optional Parent
  Reflection block (3 textareas) when any were filled. Band
  cutoffs mirror the HTML form's `getProfileLabel` exactly so
  the parent's screen and the shared PDF say the same words.
  Verified by analyze_file_tool: single page, all requested
  blocks present, correct scores + reflection rendered.

**🟢 P1 — Self Assessment tile on Alignment & Tools**
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — new
  gradient-purple tile between the Co-Parenting Assessment and
  Safety Screen tiles. Magic-wand sparkle icon (amber on
  purple), "Self Assessment · 40 quick questions · 8-domain
  profile · save or share". Opens the static preview page in a
  new tab (test id `toolkit-link-self-assessment`).

**End-to-end verified at mobile 390**
- Preview page: 40 radios + 8 domains render; filling all with
  "4" and clicking View Profile → results panel with 8 bars,
  Profile Summary, Download PDF + Save-to-account buttons.
- Save-to-account toast: "Saved. Your 8-domain profile
  (overall Good) is now in your Alignment & Tools progress
  tile." (confirmed via Progress endpoint: 5 snapshots, latest
  with 8 sections and `source=preview`).
- Download toast: "Downloaded. Share it with your mediator the
  same way you'd share any PDF."
- No horizontal overflow on any surface.


### 2026-02-27 — Iter240 · Co-Parenting Self-Assessment preview replaced

Founder swapped the 30-question / 6-section / 4-point Likert
version from iter238 for a new 40-question / 8-domain /
5-point Likert version. All three discovery entry points
(toolkit tile, Assessment Guide recap, Progress Tile
empty-state) point at the same path, so the only wiring change
was the "30" → "40" text in the two React copy strings.

**🟢 P1 — File replacement**
- `/app/frontend/public/coparenting-self-assessment-preview.html`
  overwritten verbatim with the pasted HTML. Served at the
  unchanged path. Visual: purple gradient header (replaces the
  previous navy blue), per-domain cards, response scale legend
  (Rarely / Sometimes / Developing / Usually / Consistently),
  Parent Reflection textarea block, "View My Co-Parenting
  Profile" CTA → results panel with 8 progress-bar rows and a
  summary of top strengths and areas to attention.

**🟢 P1 — Discovery-link copy updates**
- `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx` —
  recap-card preview link now reads "Try the preview — 40
  quick questions" (was "30").
- `/app/frontend/src/pages/portal/CpProgressTile.jsx` — empty
  state preview link now reads "Or try the preview — 40 quick
  questions" (was "30").

**Verified**
- Mobile 390: 8 domains render in order (My Child's Needs,
  My Parenting, Supporting the Other Parent, Communication,
  Managing Conflict, Shared Parenting Decisions, Flexibility &
  Problem Solving, Moving Forward), 40 questions render, 5
  Likert values per question. Filling all 40 with "4" and
  clicking View My Co-Parenting Profile produced 8 score rows
  (4.0 / 5 · "Generally Working") and a Profile Summary with
  top-3 strengths and bottom-3 areas-to-attention. No
  horizontal overflow.


### 2026-02-27 — Iter239 · Safety-First button on the Gateway

Founder ask: "when the coparents start their journey, I want a
safety first button to address family violence IPV concerns."

**🟢 P1 — Safety-First Gateway button**
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — new button
  rendered as the FIRST element inside `screen === "gateway"`,
  above the existing "Talk to the SA CoParents Guide" button and
  the two Doors. Rose gradient card with shield-heart icon,
  "SAFETY FIRST" uppercase pill, headline "Start here if you
  have family-violence or IPV concerns", subhead "A short,
  private check before anything else — includes crisis hotlines
  and a grey-rock path." Right-chevron on the right. Test id
  `gateway-safety-first-btn`.
- Click handler reuses the existing `setSafetyOpen(true)` state
  that already drives the SafetyScreen modal at the portal root
  — so **no new triage flow was built**. Opening via the
  gateway button lands on the same Quick Safety Check (three
  questions: physical safety, intimidation/coercion/control, is
  this device private) + the "Full safety screen" fallback the
  Parent Journey already uses.
- The parent in a crisis sees it FIRST (y=86px on mobile, 358px
  wide) before committing to either Door; the existing
  IntroChatBot still auto-opens for first-time visitors on top,
  but the Safety-First button is the first thing visible once
  the intro is dismissed and the first thing on every
  subsequent visit.

**Clinical lockstep invariant preserved**
- No new SafetyScreen variant, no new triage questions, no new
  copy. The existing clinical screen is the single source of
  truth; the Gateway button is purely a new entry point into
  the same flow.

**Verified**
- Mobile 390: button renders at y=86 above the gateway content
  (bounding 358x109). Clicking opens the SafetyScreen modal —
  heading reads "Quick Safety Check", three questions render,
  "Prefer not to say" / "Not sure" options present, "Continue"
  button and "Full safety screen" fallback visible. No
  horizontal overflow.


### 2026-02-27 — Iter238 · Interactive 30-question Co-Parenting Self-Assessment preview

Founder dropped in a self-contained 30-question Co-Parenting
Self-Assessment HTML (6 sections × 5 Likert prompts + Foundation
Statement textarea block + tier analysis + JSON export + print).
Served verbatim as a static asset so parents can **try the
questions themselves** before committing — complementing the
iter234 "See a sample report" PDF, which only shows the output.

**🟢 P1 — Static preview page**
- `/app/frontend/public/coparenting-self-assessment-preview.html`
  — HTML/CSS/JS exactly as provided, no modifications. Served at
  `https://.../coparenting-self-assessment-preview.html` with
  type `text/html` and ~25 KB payload. Self-contained: sticky
  progress + total-score bar, 6 Likert sections (Child-Focused
  Parenting, Communication, Reliability/Routines/Transitions,
  Decision-Making/Information Sharing, Conflict Management/
  Boundaries, Alignment/Readiness), tier bands (30-55 / 56-75 /
  76-95 / 96-120), six Foundation Statement textareas, Export
  Data (JSON) and Print/PDF buttons. Safety-first preamble
  retained ("not a diagnosis, custody evaluation, …").

**🟢 P1 — Three discovery entry points**
- `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx` —
  recap-card IIFE now renders two links as a vertical pair when
  Co-Parenting is selected: the existing "See a sample report"
  (purple, PDF) plus a new "Try the preview — 30 quick
  questions" (amber, test id
  `assessment-guide-preview-link-coparenting`). Other options
  are unchanged (the deep-dive options have only the sample
  link because no interactive preview exists for them).
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` —
  Co-Parenting Assessment tile now shows the new
  `toolkit-coparenting-preview-link` right next to the existing
  "See a sample" link.
- `/app/frontend/src/pages/portal/CpProgressTile.jsx` — empty
  state (no history yet) now ends with "Or try the preview —
  30 quick questions" below "See a sample report" so first-time
  visitors have a zero-commit way to engage.

**Verified**
- Static page: 200 / 25218 B / text/html; 6 sections render,
  30 radio questions render, sticky bar progress ticks from 0
  to 1 and score ticks from 0 to 4 on first Q=4 click.
- Mobile 390: tile + guide-recap + empty-state entry points all
  reachable; both links visible side-by-side in the recap card
  (sample PDF + preview). No horizontal overflow.


### 2026-02-27 — Iter237 · Snapshot Pin + Progress Share Open Tracking

Two parent-facing follow-ups to iter235. Pin keeps an active plan
pinned to the top of the Snapshot library; open tracking closes
the loop on "did the mediator actually see what I sent?"

**🟢 P1 — Snapshot Pin (toggle + drag-to-top)**
- `/app/frontend/src/pages/portal/SnapshotStrip.jsx`:
  - New pushpin icon button on each row (test id
    `snapshot-pin-{idx}`), toggles `snap.pinned`. Pinned rows
    get an amber ring + amber-filled thumbtack; unpinned rows
    show a greyed-out thumbtack that gains colour on hover.
  - Sorter runs pinned-first (by `pinned_at` desc so the most
    recently pinned sits on top), then falls back to insertion
    order for unpinned.
  - Native HTML5 drag: each row is `draggable`. When a drag is
    in flight a dashed "Drop here to pin to the top" zone
    materialises above the list (test id
    `snapshot-pin-dropzone`). Dropping on it flips `pinned=true`
    with no modifier keys needed.
  - Delete button nudged right (`pr-6` → `pr-12`) to make room
    for the pin button in the top-right corner.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — new
  `onPinSnapshot(idOrIdx, nextPinned)` callback stamps
  `pinned=true, pinned_at=now()` or strips both fields on
  unpin. Rides the same debounced
  `PUT /api/portal/state` → `snapshot_history` sync as rename.
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — threads
  `onSnapshotPin` through to the strip.
- `/app/backend/portal_routes.py` — `_sanitize_snapshot_history`
  whitelists `pinned` (bool) and `pinned_at` (ISO string, 40
  chars). Without this the pin would be stripped on round-trip.
- Round-trip verified: `GET /api/portal/state` returned
  `pinned=True, pinned_at=2026-10-01T15:13:36Z` on the pinned
  snapshot, `pinned=None` on the sibling. UI confirmed the
  Co-parenting snapshot moved from row 2 → row 1 after pinning.

**🟢 P1 — Progress Share Open Tracking**
- `/app/backend/progress_share_analytics.py` — new module
  (collection `progress_shares`). Helpers:
    * `mint_share_id()` → `sh_<12 hex>`
    * `record_share(user_id, parent_name, to_email, mediator_name)`
    * `record_open(share_id)` — idempotent: first open stamps
      `opened_at`; subsequent opens `$inc` `open_count` and
      stamp `last_opened_at`. Unknown share_id is a no-op.
    * `recent_shares_for(user_id)` — N most recent shares,
      sorted by `sent_at` desc.
- `/app/backend/email_service.py` —
  `send_cp_progress_share(..., tracking_pixel_url=None)`. When
  the pixel URL is passed, append a hidden 1x1
  `<img src="{pixel_url}" width=1 height=1 ...>` AFTER the
  branded shell wraps the body — keeps `_branded_html` template
  untouched.
- `/app/backend/coparenting_routes.py`:
  - Share route mints a `share_id`, persists a `progress_shares`
    row BEFORE calling Resend (so a send failure leaves an
    honest "Sent · never opened" row), then passes
    `tracking_pixel_url` = `{PUBLIC_BACKEND_URL}/api/coparenting/progress-share/{share_id}/pixel.gif`
    into the email send. Response now includes `share_id`.
  - New `GET /api/coparenting/progress-share/{share_id}/pixel.gif`
    (public, no auth, no cache) — returns a 43-byte 1x1 GIF
    and records the open.
  - New `GET /api/coparenting/report/progress/shares` — recent
    share history for the current parent with open status.
- `/app/backend/.env` — added `PUBLIC_BACKEND_URL` so the
  tracking pixel URL embeds an externally-reachable host.
  (Pre-existing `REACT_APP_BACKEND_URL` in the frontend .env
  isn't visible to backend, so this is a new backend variable;
  no existing key renamed or removed.)
- `/app/frontend/src/pages/portal/CpProgressTile.jsx`:
  - Fetches `/report/progress/shares` on mount and polls every
    30 s so a new open shows up without a page reload.
  - Refreshes shares immediately after a successful send.
  - New "Share history" strip inside the share block
    (test id `cp-progress-share-history`): one row per recent
    share, test id `cp-progress-share-row-{share_id}`. Row
    reads "Opened by Dr. Rivera · 2m ago · 2 opens" (emerald)
    when opened, "Sent to … · not yet opened" (grey) when not.

**Verified end-to-end**
- Backend: share → shares list → pixel GET → shares list
  sequence recorded `opened_at` on first pixel hit and bumped
  `open_count` to 2 on a second hit.
- Mobile 390: pinning the Co-parenting snapshot moved it from
  row 2 to row 1 and persisted on the server. Share history
  strip rendered "Opened by Dr. Rivera · 2m ago · 2 opens".
  No horizontal overflow.


### 2026-02-27 — Iter236 · Deep-Dive Samples in Assessment Guide

Follow-up on the iter234 "See a sample" treatment: three more
sample links so parents can preview Educational, Medical, and
Psychological deep-dive reports before committing to the
assessment.

**🟢 P1 — AssessmentGuideChat recap · sample link lookup**
- `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx` —
  replaced the single-key hard-coded coparenting block with a
  `SAMPLE_URL_BY_KEY` lookup inside the recap-card IIFE. Keys
  map 1:1 to Assessment Guide options:
    * `coparenting`   → `/api/insights/samples/coparenting-self-assessment.pdf` (dynamic, iter234)
    * `educational`   → `/api/insights/samples/snc-sample-individual-report-educational.pdf` (static SNC artefact)
    * `medical`       → `/api/insights/samples/snc-sample-individual-report-medical.pdf`
    * `psychological` → `/api/insights/samples/snc-sample-individual-report-psychological.pdf`
  The remaining Assessment Guide options (`communication`,
  `safety`, `court`) deliberately return no sample — the first
  two don't have individual-report artefacts and the third is a
  routing path, not a report. Each link carries the stable test
  id `assessment-guide-sample-link-{key}`.

**Verified in preview**
- Backend GET on each of the three deep-dive sample URLs: 200 /
  ~1 MB / valid %PDF magic / 3 pages each.
- Mobile 390: clicked through each option in the Assessment
  Guide; the sample link renders only for coparenting +
  educational + medical + psychological. Safety and Court
  recaps correctly show no link. No horizontal overflow.


### 2026-02-27 — Iter235 · Snapshot Rename + Progress Share-with-Mediator

Two parent-facing features. Both ride on infrastructure shipped in
iter234 (progress history + the inline Assessment Guide).

**🟢 P1 — Snapshot Rename**
- `/app/frontend/src/pages/portal/SnapshotStrip.jsx` — small pencil
  icon on each row flips the title into an inline input (40-char
  cap, Enter saves, Esc cancels). Row shows `snap.label` when set
  with a small uppercase topic subtitle underneath; falls back to
  the original "Foundation" / "Co-parenting" header when the
  parent clears the name.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — new
  `onRenameSnapshot(idOrIdx, rawLabel)` callback mirrors
  `onDeleteSnapshot`: updates state + writeJson, which trips the
  existing debounced PUT /api/portal/state. Empty string clears
  the label cleanly (deletes the `label` key off the snapshot).
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — threads
  `onSnapshotRename` through to the strip.
- `/app/backend/portal_routes.py` — `_sanitize_snapshot_history`
  now whitelists `label` (max 40 chars) so the rename survives
  the server round-trip. Without this the label was being
  silently stripped by the sanitizer and bounced back empty on
  reload.
- Round-trip verified end-to-end: rename in UI → debounced PUT →
  server returns the labelled snapshot via GET /api/portal/state.

**🟢 P1 — Progress Share-with-Mediator**
- `/app/backend/cp_progress_pdf.py` — new one-page portrait PDF
  builder. Blocks: latest-rating badge card, overall-rating
  sparkline (coloured dot per submission + guide-lines at every
  rating band), top-5 section movers (↑/↓ arrows and bars),
  10-row "All sections — latest rating" table with latest +
  ~60d-ago columns, optional parent note. Rendered from the
  SAME progress payload the Alignment & Tools tile reads
  (`cp_report_history.build_progress_payload`), so wording never
  drifts between the two surfaces.
- `/app/backend/email_service.py` — new public
  `send_cp_progress_share()` using the existing `_send()` helper
  (Virtru-first, Resend fallback). Reply-To is set to the parent
  so the mediator's reply comes straight back. PDF goes as a
  single attachment (`Progress_Snapshot_{parent_name}.pdf`),
  plain-text + branded HTML body both include the optional note.
- `/app/backend/coparenting_routes.py` — two new routes:
    * `GET /api/coparenting/report/progress/pdf` → inline PDF
      download, optional `?mediator_name&note` query params so a
      parent can preview the exact file before emailing.
    * `POST /api/coparenting/report/progress/share` →
      `{to_email, mediator_name?, note?}` body, generates the
      same PDF, dispatches via `send_cp_progress_share`. 400 on
      a bad email, 404 if the parent has no history yet, 502 on
      Resend failures (surfaces the detail string the SDK gives
      back).
- `/app/frontend/src/pages/portal/CpProgressTile.jsx` — bottom
  of the tile now shows a two-button row:
    * **Download PDF** (opens the inline-pdf route in a new tab).
    * **Share with mediator** (opens an inline mini-form:
      email + optional mediator name + optional note, Cancel
      and Send controls, spinner during send, success card
      "Progress Snapshot sent" when the API returns ok, error
      line in the form on failure).

**Verified end-to-end**
- Backend: PDF route 200 / 2.7 KB, share route 200 to
  `delivered@resend.dev` sandbox (2.8 KB attached), rejected a
  bad `example.com` recipient with a surfaced 502 (Resend
  sandbox block).
- One-page PDF content audit (via analyze_file_tool): confirmed
  single page, every rendered block present (latest-rating
  badge, sparkline, movers with ^/v arrows, all-sections
  table with both columns, parent note).
- Mobile 390 preview: rename pencil → inline edit → save →
  title now reads "Emma's summer plan" with "FOUNDATION"
  subtitle; share form submit → emerald "Progress Snapshot
  sent" card. No horizontal overflow.
- Server persistence confirmed via GET /api/portal/state:
  renamed snapshot shows `label="Emma's summer plan"`, the
  untouched sibling shows `label=None`.


### 2026-02-27 — Iter234 · Self Co-Parenting Assessment · sample PDF + progress + 60-day retake

Parents and professionals asked to **see** what the thorough
10-section Self Co-Parenting Assessment report actually looks like
before taking it or inviting a client to. Shipped three joined
pieces:

**🟢 P1 — Public sample PDF**
- `/app/backend/coparenting_self_assessment_sample.py` — fixture
  of a plausible mid-range parent "Jamie R." (no PII). Fixture
  spans every rating band (Excellent / Good / Fair / Needs
  Improvement) so the output exercises every rendered block:
  strengths, growth areas, section detail, communication toolkit,
  recommended next steps.
- `GET /api/insights/samples/coparenting-self-assessment.pdf`
  (added in `insights_routes.py` right above the existing
  `/samples/joint-alignment-preview.pdf` route). Public, 24h
  cached, no auth. Renders through the SAME
  `compute_scores → build_report → build_coparenting_pdf` code
  path a real submission uses, so any future tweak to the live
  assessment flows automatically to the sample.

**🟢 P1 — Progress history + chart**
- `/app/backend/cp_report_history.py` — new append-only
  `cp_report_history` collection (`{_id: user_id, snapshots: [...] }`).
  Each snapshot is lightweight: `{submitted_at, overall_rating,
  overall_value, section_avgs, answered, total}`. Helpers:
  `append_history()`, `build_progress_payload()`.
- `/app/backend/coparenting_routes.py` — `POST /report/generate`
  now also calls `append_history` (fire-and-forget: a history
  write never fails the parent's save). New `GET /report/progress`
  returns `{snapshots, overall_series, recent, baseline,
  section_movers, radar, days_since_last, retake_due,
  retake_interval_days, sample_pdf_url}`. Baseline picked as the
  snapshot closest to RETAKE_INTERVAL_DAYS (60) before the latest.
- `/app/frontend/src/pages/portal/CpProgressTile.jsx` — new
  component mounted inside the Coparenting Journey Toolkit on
  Alignment & Tools. Four rendered blocks when history exists:
    1. 60-day retake soft banner (amber) with Retake button —
       only when `retake_due`.
    2. Overall-rating sparkline (4 bands guide-lines, coloured
       dot per data point).
    3. Per-section change bars — top 5 movers vs ~60d-ago
       baseline, up (emerald) / down (amber) / flat.
    4. 10-axis radar chart comparing latest (filled purple) vs
       ~60d-ago baseline (dashed grey).
  Empty-state (no history yet) shows a short invite + the
  public sample PDF link. Fetches via the shared cookie-auth
  `api` client in `lib/api.js` — no bespoke token handling.

**🟢 P1 — "See a sample" links in UI**
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — small
  "See a sample" link under the Co-Parenting Assessment tile
  description. `stopPropagation` on the click so tapping the
  link opens the sample PDF without triggering the tile's
  parent Link navigation.
- `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx` —
  inside the recap card for "Co-Parenting Assessment" (and
  only that option), a "See a sample report" line sits above
  the "Choose Another Area" link so parents can preview before
  tapping Start.

**Verified in preview**
- 1920×800 desktop + 390×844 mobile:
  - Logged-out: empty-state tile + "See a sample report" + tile
    "See a sample" link render.
  - Logged-in (parent1@test.com, seeded 4 history snapshots over
    180 days): retake banner shows "It's been 65 days since
    your last check-in" with Retake button; sparkline draws 4
    points trending up ("Latest · Good"); 5 top movers listed
    (Therapy +0.40, Communication +0.30, Medical +0.30,
    Pick-Up/Drop-Off +0.20, Emotional +0.20); 10-axis radar
    renders both latest (filled) and baseline (dashed).
- Backend asserts: sample PDF 200 / 7966 B / application/pdf;
  progress route 401 unauth, authenticated payload asserts on
  `retake_due=True`, `days_since_last=65`, 4 series points, 10
  movers, 10 radar labels, correct `sample_pdf_url`.


### 2026-02-27 — Iter233 · Assessment Guide moves inline on Alignment & Tools

Founder feedback: "we want the chat box insert we just talked about
to go on alignment and tools page". The Assessment Guide is now
mounted inline directly above the toolkit tile grid instead of
opening as a popup.

**🟢 P1 — AssessmentGuideChatInline export**
- Refactored `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx`.
  The chat body (list · recap · help · help-recap phases + all
  option cards and copy) was extracted into an internal
  `<AssessmentGuideBody />` sub-component and is now shared between
  two exports:
  - `AssessmentGuideChat` (unchanged) — modal, key-remounted on
    each open so phase resets cleanly. Still available for import
    by any future intro/follow-up flow.
  - `AssessmentGuideChatInline` (new) — same body wrapped in a
    normal card (no fixed overlay, no viewport-height column, no
    close button). Scroll area capped at `max-h-[520px]` so it
    can't swallow the toolkit below it. After a routing tap the
    chat auto-resets to the list phase for the next triage cycle.
- Copy stays byte-for-byte identical between the two variants —
  strict lockstep invariant preserved.

**🟢 P1 — AlignmentHub wiring**
- `/app/frontend/src/pages/portal/AlignmentHub.jsx`:
  - Removed the `open-assessment-guide` purple CTA button.
  - New prop `onStartAssessment` (replaces
    `onOpenAssessmentGuide`), passed straight through to the
    inline chat's routing callback.
  - Renders `<AssessmentGuideChatInline />` between the
    `SnapshotStrip` and the tool tile grid.

**🟢 P1 — SacoparentsPortal wiring**
- `/app/frontend/src/pages/SacoparentsPortal.jsx`:
  - Removed dead state (`assessmentGuideOpen` /
    `setAssessmentGuideOpen`) and the mounted modal instance —
    nothing was left calling `setAssessmentGuideOpen(true)` after
    the CTA button was removed.
  - Removed the now-unused `AssessmentGuideChat` import (the modal
    export is still available in the module for future flows).
  - Passes `onStartAssessment={onStartAssessment}` to
    `<AlignmentHub />`. Routing table is unchanged (safety →
    SafetyScreen; communication → BIFF tab; court → Court door;
    coparenting/educational/medical/psychological → Guided
    Journey wizard).

**Verified in preview**
- Screenshot 390×844 (mobile): inline chat card visible above the
  four tool tiles, option list renders (Educational, Medical,
  Psychological, Court-ordered, "I'm Not Sure Where to Start"),
  `open-assessment-guide count = 0`, no horizontal overflow.
- Screenshot 1920×800 (desktop): tapping "Co-Parenting Assessment"
  transitions to the recap phase inline (Start CTA test-id
  present, `assessment-guide-modal count = 0`).


### 2026-02-26 — Iter232 · SA CoParents Assessment Guide Chatbot

Second chatbot layered on the Coparenting Journey. Unlike the
`IntroChatBot` (iter228) which decides between VOLUNTARY vs
COURT-ORDERED paths, this one helps a parent who is already
inside the Coparenting Journey pick WHICH ASSESSMENT to open
first. Copy is authored verbatim by the founder; do not
paraphrase. Verified in iter88 (frontend 100% — 7/7 routes + 5/5
triage branches).

**🟢 P1 — AssessmentGuideChat component**
- New `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx`
  (~485 lines). Chat-style modal with four phases:
    * `list` — greeting + 7 numbered assessment cards
      (Co-Parenting / Communication / Safety / Educational
      / Medical / Psychological / Court-Ordered) + a dashed
      "I'm Not Sure Where to Start" card that opens the
      mini-triage.
    * `recap` — per-selection card showing "You've selected
      {label}" + "Why parents choose this assessment" +
      "What you'll explore" (topic bullets) + optional
      italic footnote (Communication + Safety only) +
      "What happens afterward". Footer swaps to the
      option's own CTA label (e.g. "Start Medical
      Assessment") plus "Choose Another Area".
    * `help` — 3-question triage (Yes/No/Not-sure for
      safety, 4-way multi-choice for child-area, Yes/No/
      Not-sure for communication focus).
    * `help-recap` — recommend card + start-recommended CTA
      + "Show me the full list".
- `recommendFromHelp(answers)` logic: safety-yes → safety;
  else specific child area if answered; else
  communication-yes → communication; else default →
  coparenting.
- Two visual color tracks: purple for the 5 co-parenting/
  child-focused options + safety-color amber for the two
  Safety + Court-Ordered options. Header chip flips to
  "Grey-rock" when `safetyFlagged` prop is true, mirroring
  the IntroChatBot header parity.
- No LLM — copy is fully static so it stays in exact
  lockstep with the founder's authored text.

**🟢 P1 — Container routing (`onStartAssessment(key)`)**
- New callback in `SacoparentsPortal.jsx` that maps each
  option key to its correct existing surface — never
  introduces a new dead-end screen:
    * `coparenting` / `educational` / `medical` /
      `psychological` → `openGuidedJourney(key)` which
      opens the existing Guided Journey wizard for that
      topic (also marks first-engagement so the iter231
      follow-up nudge stops).
    * `communication` → `setHubSection('biff')` + scroll
      to the newly-added `#biff-tab-section` anchor so
      the BIFF Coach is front-and-center.
    * `safety` → `setSafetyOpen(true)` so the parent can
      retake the Safety Screen through the existing
      safeguard flow.
    * `court` → `setHubSection('alignment')` +
      `setScreen('gateway')` + `enterCourtPath()` so the
      parent lands on the Court-Key verification screen
      via the existing door + safety-first flow.

**🟢 P1 — Entry point**
- New "Ask the Assessment Guide — which one should I start
  with?" pill (`open-assessment-guide` testid) at the top of
  the Coparenting Journey toolkit card in `AlignmentHub.jsx`,
  sandwiched between the SnapshotStrip and the tile grid.
  Purple gradient so it reads as the primary "not sure?"
  entrypoint without competing with the toolkit tiles.

**Files touched**
- `/app/frontend/src/pages/portal/AssessmentGuideChat.jsx`
  (new).
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — new
  `onOpenAssessmentGuide` prop + pill button rendered
  above the tile grid.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` —
  `assessmentGuideOpen` state, `onStartAssessment`
  callback (~35 lines), `<AssessmentGuideChat>` mount,
  `#biff-tab-section` id on the BiffTab wrapper.

**Verified — iter88 test report**
- Modal opens via the toolkit pill; all 7 numbered options
  visible + 8th "I'm Not Sure Where to Start" card.
- Copy fidelity: all 7 headings, why-strings, topic
  bullets, and both italic footnotes (Communication +
  Safety) render verbatim.
- All 7 routes hit their intended surface: guided modal
  for coparenting/educational/medical/psychological,
  BIFF tab (`#biff-tab-section`) for communication,
  safety modal (`modal-safety-screen`) for safety,
  Court-Key verification screen for court.
- All 5 triage branches recommend correctly (safety-yes →
  Safety; area=medical → Medical; area=psychological →
  Psychological; communication-yes → Communication;
  default → Co-Parenting).
- Zero horizontal overflow at 390×844.

**Deferred (P2 — iter88 review, informational)**
- Safety-yes on Q1 still walks the parent through Q2+Q3
  before showing the recap. Founder-approved: lets the
  triage capture the fuller picture even when Q1 has
  already decided the recommendation.
- Legacy stale-closure note on `openGuidedJourney` — the
  callback captures no state so no risk today.


### 2026-02-26 — Iter229–231 · Delete + Trendline + Follow-up Guide

Three follow-on features to iter228, all shipped in one batch and
verified in iter87 (backend 4/4 pytest + frontend 8/8 Playwright
scenarios across the two UI features). No SAST rule changes.

**🟢 P1 — iter229 · Snapshot Delete**
- `SnapshotStrip.jsx` grew a ✕ button in each card's top-right
  corner (`snapshot-delete-{idx}`) that flips the card body
  into a rose-tinted two-tap confirm pane
  (`snapshot-delete-confirm-{idx}` /
  `snapshot-delete-confirm-cancel-{idx}` /
  `snapshot-delete-confirm-yes-{idx}`). Confirm-state is
  transient + component-local so a fresh click starts fresh.
- New `onDeleteSnapshot(idOrIdx)` in `SacoparentsPortal.jsx`
  filters by stable `id` (with index fallback for legacy
  entries), writes back to localStorage, and rides the
  existing debounced `PUT /portal/state` so the delete
  round-trips across devices.

**🟢 P1 — iter230 · Digest Trendline**
- `guided_draft_digest.compute_digest()` refactored to share a
  `_compute_window(now, offset_days)` helper. Runs twice:
  offset_days=0 for the current window, offset_days=7 for
  the prior window.
- Digest payload gains
  `previous_window_start/end`, `previous_total_sent`,
  `previous_total_finished`, `previous_conversion_pct`,
  `trend_delta_pct` (rounded to 1dp), and `trend_direction`
  (`'new' | 'up' | 'down' | 'flat'`). Thresholds: >0.5 pts →
  up, <-0.5 → down, else flat. `'new'` when the prior window
  has zero nudges.
- Email template in `send_nudge_digest()` gets a
  `Vs last week` panel with ↗ / ↘ / → / ☆ arrow + delta pts
  + colored badge (emerald up, rose down, slate flat, muted
  new). Plain-text fallback mirrors the same summary line.
- Verified live: prev-week 4 sent / 1 finished / 25% vs
  current 3 sent / 2 finished / 66.7% → direction=up,
  delta=+41.7 pts. Also verified: zero prior data →
  direction='new'.

**🟢 P1 — iter231 · Guide Follow-up Nudge**
- New `/app/frontend/src/pages/portal/GuideFollowupModal.jsx`
  (~135 lines). Chat-style card with 3 bot messages ("how's
  it going?", "you picked {path} {N days ago}", "no
  pressure"), a primary CTA "Show me my first assessment"
  (color-coded to the picked path — purple for parent,
  amber for court), and a subtle "Not now, thanks — remind
  me next week" secondary link.
- Three new localStorage keys in `portalStorage.js`:
    * `sacoparents_path_picked_at` — set inside
      `enterParentJourney()` / `enterCourtPath()` on every
      pick (overwrite is fine; parents can flip doors)
    * `sacoparents_first_engagement_at` — set on the first
      call to `openAssessmentFolder` or `openGuidedJourney`
      (whichever the parent taps first)
    * `sacoparents_followup_dismissed_at` — set only on the
      explicit "Not now, thanks" snooze
- Mount-time check inside the existing
  `useEffect(() => {…}, [])`: opens the follow-up modal iff
  intro-already-seen AND path picked AND no first-engagement
  AND ≥ `FOLLOWUP_MIN_HOURS` (24h) since pick AND no active
  snooze (`FOLLOWUP_SNOOZE_DAYS` = 7d).
- The "Show me my first assessment" CTA sets
  first-engagement itself (so a bounce from the safety
  screen still counts) and re-invokes the container's
  existing `enterParentJourney` / `enterCourtPath` so the
  safety guardrail stays intact.

**Files touched**
- `/app/frontend/src/pages/portal/SnapshotStrip.jsx` — ✕
  button + two-tap confirm pane + `onDelete` prop.
- `/app/frontend/src/pages/portal/AlignmentHub.jsx` — new
  `onSnapshotDelete` prop threaded to `<SnapshotStrip>`.
- `/app/frontend/src/pages/portal/GuideFollowupModal.jsx`
  (new).
- `/app/frontend/src/pages/portal/portalStorage.js` — new
  `PATH_PICKED_KEY`, `FIRST_ENGAGEMENT_KEY`,
  `FOLLOWUP_DISMISSED_KEY`, `FOLLOWUP_MIN_HOURS`,
  `FOLLOWUP_SNOOZE_DAYS` exports.
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — path-
  picked writes in `enterParentJourney/enterCourtPath`,
  first-engagement writes in
  `openAssessmentFolder/openGuidedJourney`, mount-time
  follow-up check, `<GuideFollowupModal>` mount,
  `onDeleteSnapshot` callback.
- `/app/backend/guided_draft_digest.py` — split into
  `_compute_window` helper + trend fields on `compute_digest`.
- `/app/backend/email_service.py` — `send_nudge_digest`
  gains the week-over-week panel + plain-text summary line.
- `/app/backend/tests/test_iter230_digest_trendline.py`
  (new, 4 tests).

**Verified — iter87 test report**
- Backend 4/4 pytest: trendline math with real seed
  (prev/current windows across parent1+parent2); zero-prior
  → 'new'; flat threshold ±0.5 pts; per-topic breakdown
  round-trips through both windows.
- Frontend 8/8 Playwright: snapshot delete (2→confirm→
  cancel→2→confirm→delete→1 with localStorage sync);
  follow-up modal auto-opens for 3-day-old parent-path pick
  with no engagement; correct label + days copy; dismiss
  persists across reload; resume routes into the picked
  door + sets engagement flag; no-nag guarantee after
  engagement.
- Zero horizontal overflow at 390×844.

**Deferred (P2 — iter87 review, informational)**
- Close(X) on the follow-up does NOT snooze — parents can
  keep seeing it every visit until they use the explicit
  "Not now, thanks" or open a tile. Founder-approved UX
  (explicit snooze CTA is right there).
- Legacy snapshots without `id` fall back to index-match
  on delete — safe today because history is
  prepend-only and confirm state is per-mount.


### 2026-02-26 — Iter228 · SA CoParents Guide Intro Chatbot

Founder-authored welcome flow layered on the Doors Gateway. Chat-
style modal greets first-time visitors, describes the two paths
(Coparenting Journey vs Court-Ordered), and offers a "Help Me
Choose" mini-triage. Verified in iter86 (frontend 8/8 scenarios).

**🟢 P1 — Intro chatbot component**
- New `/app/frontend/src/pages/portal/IntroChatBot.jsx`
  (~430 lines) with three phases:
    * `paths` — greeting messages + two path cards (Parent
      / Court) + Help-Me-Choose card + closing aphorism
    * `help` — 3-question triage (Yes/No/Not sure buttons):
        1. Was a professional directing you here?
        2. Are you in an active custody case?
        3. Are you here voluntarily?
    * `recommend` — bot-recap card + primary CTA to enter
      the recommended door
- `recommendFrom(answers)` logic: court_directed=yes OR
  active_case=yes → **court** door; voluntary=yes → **parent**
  door; all-No / all-Not-sure → parent door (safer default —
  parent can switch anytime).
- Uses no LLM — copy is authored and rendered deterministically
  so it stays in exact lockstep with the founder's marketing.
- localStorage `sacoparents_intro_chat_seen_v1` flag persisted
  on every exit path (X close, direct CTA, recommend CTA) so
  the modal doesn't re-auto-open on subsequent visits.

**🟢 P1 — Portal integration**
- New `introOpen` state in `SacoparentsPortal.jsx`. On mount,
  auto-opens when `hasIntroBeenSeen() === false`.
- Wired above the Doors Gateway (not below) so the "Talk to
  the SA CoParents Guide" pill stays visible above the fold
  on mobile (previously below-fold at 390×844).
- Both direct CTAs and both recommend CTAs call the container's
  existing `enterParentJourney()` / `enterCourtPath()`
  handlers — so the safety-first gate still fires before
  either door as before.

**Files touched**
- `/app/frontend/src/pages/portal/IntroChatBot.jsx` (new).
- `/app/frontend/src/pages/SacoparentsPortal.jsx` — import,
  `introOpen` state, auto-open effect, gateway pill above
  DoorsGateway, modal mount.

**Verified — iter86 test report**
- 100% pass across 8 scenarios: auto-open on first visit,
  seen-flag persistence, both direct-CTA paths, all 4
  Help-Me-Choose recommendation branches, Back-to-paths,
  X-close-marks-seen, and gateway re-open pill. Zero
  horizontal overflow. Pill bounding-box at y=86 (well
  above the 844px fold on mobile).

**Deferred (P2 — from iter86 review, informational)**
- Help-Me-Choose flow doesn't allow editing a prior answer
  individually — the only way back is "Back to the paths"
  which clears everything. Acceptable given only 3
  questions.
- `unsure` on court_directed/active_case falls through to
  the voluntary path (safer default per spec). Could be
  softened to "consult a professional" if the founder
  wants a more conservative nudge later.


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

## 2026-06 — Self Journey welcome artwork
- Self Journey's text "Welcome to SA CoParents" banner was replaced with the same welcome artwork the dashboard uses (`/images/sa-welcome*.webp`), via the shared `portal/WelcomeArtwork.jsx`.
- Self Journey order: header → SafetyStrip → goal card → artwork → 4 action cards.
- All three pictured cards work as action buttons on both screens. Dashboard: Individual → Self door, Court → Court door, Comm → BIFF coach. Self Journey: Individual → smooth-scrolls to the 4 cards, Court → Court door, Comm → BIFF coach.
- testids: `door-welcome-image` / `door-welcome-hotspot-{self,court,comm}` (dashboard), `door-self-welcome-image` / `door-self-welcome-hotspot-{self,court,comm}` (Self Journey). The old `door-self-brand` has been removed.
- Dashboard landing order is now: welcome artwork (3 tappable cards) → "Pick your door" + Court Ordered / Self Journey buttons → goal card → journey roadmap. This replaces the earlier "doors → artwork" order.
- The "Safety First" bar and the Grey-rock chip were removed from the Self Journey and Court Ordered screens (user request), and the unused `SafetyStrip` was deleted. What stays: the pre-door safety gate, Quick Exit, the "In danger?" bar, grey-rock behaviour, and the Grey-rock chip on the Card 3/Card 4 sub-screens, BIFF and Alignment Hub.
- The test goals (`TEST_*`) were blanked in the preview DB and their check-ins deleted. The goal card still renders for real goals.

## 2026-06 — Cleanup, tap glow, Court artwork, release check (iteration_95: all passed)
- The Safety First bar and grey-rock note were also removed from the Card 3 and Card 4 sub-screens. Quick Exit and the "In danger?" bar remain.
- The "Your Co-Parenting Journey" 6-step roadmap was deleted from the dashboard landing. Landing order: artwork → doors → goal card.
- Card 2 is renamed "Understand Your Co-Parenting Relationship" (tile + modal title). The text baked into the artwork image is unchanged.
- WelcomeArtwork hotspots now glow purple on hover/tap (`.sa-hotspot`) and pulse once after the image loads (`.sa-hotspot-pulse`, fill-mode backwards so the hover glow still works). Reduced-motion users get no pulse.
- The Court Ordered screen shows the artwork under its header (`door-court-welcome-image`). Hotspots: self → Self Journey, court → scrolls to `door-court-abc`, comm → BIFF.
- Release check (`release_check.py`): runs 9 checks (3 pages, app JS bundle, /api/health, Card 1/3/4 PDFs over HTTP, Mediator PDF in-process). Triggers:
  - post-boot, 90s after start; retries once after 90s before alerting; 10-min throttle lock; skipped on preview hosts
  - daily cron `release-check` at 14:00 UTC
  - admin "Run check now" button
- Alerts email ADMIN_EMAILS on failure, with a 12h cooldown while failures persist. Runs are stored in `release_checks`; the live origin is stored in `release_check_state` (from the cron request or an admin visit).
- Admin tile: `ReleaseCheckTile.jsx` on /admin. APIs: `GET /api/admin/release-checks`, `POST /api/admin/release-checks/run`, `POST /api/cron/release-check`.

## 2026-06 — Artwork text + weekly Self Journey note (iteration_96: all passed)
- Welcome artwork pixel-edited: the Individual Journey checklist now reads "Understand Your / Co-Parenting Relationship". Reused the image's own glyphs; the list was re-spaced slightly. Served as `?v=2` to bust the cache.
- Weekly note (`self_journey_weekly.py`): Sunday 17:00 America/Chicago (cron `sj-weekly-note`, the 5th and last allowed cron).
  - Sent only to parents with Self Journey activity in the last 7 days: Card 1 completions, practice check-ins + streak, Card 2 snapshots, Card 3 categories, Card 4 updated.
  - Subject: "Your weekly note". Safety-flagged parents are skipped; separate one-tap unsubscribe (`GET /api/self-journey/weekly-note/unsubscribe`, prefs in `self_journey_weekly_prefs`); one note per user per ISO week (`self_journey_weekly_notes`). Links use the cron request's origin.
- Tests: `/app/backend/tests/test_self_journey_weekly.py`.

## 2026-06 — Weekly note stats (self-tested: curl + in-process + screenshots; pytest 25/25)
- The email button now goes through a tracked link, `GET /api/self-journey/weekly-note/open?token=` (signed JWT, kind `sj_weekly_click`, sub + wk). It records the first `clicked_at` on the note doc, then always 302s to `<request origin>/dashboard`, so there's no open redirect.
- "Came back with progress" means any Self Journey activity within 7 days after `sent_at`: Card 1 entry, check-in `created_at`, Card 2 snapshot, Card 3/4 `updated_at` (`came_back()`).
- `GET /api/admin/self-journey-weekly/stats` (admin only) returns the last 8 ISO weeks: sent, progressed, clicked, and a `counting` flag while the 7-day window is still open, plus totals.
- `WeeklyNoteStatsTile.jsx` on /admin, under the Release check tile: totals cards, a weekly table, and an empty state explaining that the first notes go out Sunday 5pm CT.
- Still pending from the earlier ask (no answers yet): the live address allowlist (needs the URL), the weekly note sample button, and custom domain steps.

## 2026-06 — Card 1 Self-Assessment redone as a full page (iteration_97: all passed + mobile self-test)
- `SelfAssessmentView.jsx` replaces the chat modal (deleted `SelfAssessmentModal.jsx` and `ChatTranscript.jsx`; `ChatComposer.jsx` now has only `TextReply` and `BackLink`).
  - Portal to body, `fixed inset-0 z-50`; it hides itself while the BIFF drawer is open (`biffCoachOpen` prop from SacoparentsPortal → JourneyShell).
- Layout follows the user's HTML mockup:
  - safety banner (911 + DV tel links), header with Emergent badge, back button and Quick Exit
  - "Step X of 6" pill: steps 1-4 are the rated sections, 5 the reflection, 6 the goal
  - 4 journey cards whose done/current/upcoming status follows progress, question panel, START CTA
  - glass AI Insight sidebar and the Caveat bottom banner
- Same 20 questions and 1-5 scale, one at a time with auto-advance; same draft/history/PDF/score labels/chart/goal/check-ins/streak/Growth Moments/reminders. `useSelfAssessmentDraft` gained a `ready` flag, so a skeleton shows until the account draft loads (no overview→question flip).
- AI (`self_assessment_ai.py`, Claude via `ai_service._make_chat(..., "claude")` + SAFETY_GUARDRAIL; rate-limited; optional auth; grey-rock voice when flagged):
  - `POST /api/self-assessment/ai/tip` (a section key or "overall")
  - `POST /api/self-assessment/ai/framing` returns {advice, suggested}
  - Frontend: `useSaInsight.js` (tip after each completed section; the overall tip is cached per entry in localStorage).
- AI Examples / Quick Templates are curated static content (`aiLibrary.js`), with grey-rock variants for flagged parents. The BIFF button opens the existing Communication Builder.
- Non-streaming (installed emergentintegrations 0.1.0 has no `stream_message`; upgrading would touch every AI feature).
- Tests: `/app/backend/tests/test_self_assessment_ai.py`.
- Still pending from earlier: user check of the Card 4 Foundation Statement PDF (one signature/date line).



## 2026-06 — Court Ordered full page + BIFF Before & After (iteration_98: all passed)
- The Court Ordered door (dashboard button, artwork Court hotspot, Guide chat / follow-up nudge via `courtRequest`) now opens `CourtOrderedView.jsx`, a full-page portal (`court-page`) built from the user's HTML mockup. The old court sub-view, the `court-key` screen and `CourtKeyScreen.jsx` were removed.
  - Parts: `court/CourtHero.jsx`, `court/CourtPathCards.jsx` (A/B/C module rows with real progress, Generate Reports = Legal Report PDF, Support Your Child = Card 3 with Back to court), `court/CourtCodeCard.jsx` (verify via `POST /api/portal/court-keys/verify`; green Accept button verifies, then opens the first incomplete module), `court/CourtAiPanel.jsx`.
  - Sidebar actions: Court-Ready PDF = `downloadLegalPdf`; BIFF check = Communication Builder scrolled to `cb-history` (`onOpenCommBuilder("history")`); Save Case & Open sacoparentsalign.online = PUT `/portal/state {court_key}` + new tab.
  - The legal claims in the mockup were replaced with honest wording (user choice): no "court-admissible", "certified", "legal network" or "direct export".
  - The page hides itself while inline overlays are open (`overlayOpen` prop from SacoparentsPortal: Safety screen, Guided Journey, drawers, comm builder, intro, share modals).
  - SaChrome: `SafetyBanner` takes icon/label props, `PageHeader` takes tagline/badgeLabel/tm props, and there's a new `useLockScroll` export.
- AI: `POST /api/court-path/ai/guide` in `court_path_ai.py` (Claude via the shared `_ask`, plus the grey-rock voice for flagged parents; rate-limited; general info only, never legal advice or claims of court certification). Tests: `/app/backend/tests/test_court_path_ai.py`.
- Communication Builder: `commBuilder/BeforeAfterCard.jsx` is a split view, "Original Text (High Friction)" next to "AI Transformed (BIFF)".
  - It shows the user's example first: "You're late again and you never tell me!" → "Hi, please let me know your ETA for pickup today so I can ensure Sam is ready. Thanks!". Safety-flagged parents see a grey-rock example instead.
  - After Transform (or a preset chip) it switches to the parent's own draft and AI rewrite, with Example / Your message chips.
  - It sits above the draft box before the first Transform and moves below the response card after (the user picked both spots).
- Still pending: weekly-note sample preview button, AI tip history in the Self-Assessment PDF, the live-address CORS allowlist (needs the URL), custom domain steps, and the user's check of the Card 4 PDF.


## 2026-06 — AI Tip History + Court Checklist (iteration_99: all passed)
- AI Tip History: "Ask AI for framing" replies are now saved for signed-in parents in `self_assessment_framing_tips` ({advice, suggested, user_id, created_at}). The parent's own typed text is never stored (user choice).
  - The Self-Assessment PDF (`POST /api/self-assessment/pdf`, optional auth via `_optional_user`, which now lives in `self_assessment_routes.py`) has a "Your AI Tip History" section, built by `self_assessment_pdf.tip_history()`. It covers every section and overall tip from all history entries plus the saved framing replies, newest first, each with a date and source label. It replaces the old per-entry "Tips from your AI Guide" section.
- Court Checklist: `court_checklist.py` adds `POST /api/court-path/checklist` (JSON) and `POST /api/court-path/checklist/pdf` (a one-page PDF). Both need auth, and the body is {modules: {foundation|coparenting|safety: completed|in_progress|not_yet}}.
  - 10 items: case code, safety check (never shows flagged), modules A/B/C (statuses sent by the page), Cards 1-4 from their collections, and BIFF logs (not counting seed id 1).
  - The PDF has a "What's left" list, mediator note lines, and a "not a legal document or proof of compliance" footer.
  - Frontend: `court/CourtChecklistCard.jsx` + `court/useCourtChecklist.js`, placed below the Accept button on the Court page. It refreshes when module statuses or the case code change, or when the page is shown again.
- Tests: `/app/backend/tests/test_tip_history_and_court_checklist.py`.


## 2026-06 — Parallel Parenting Option Builder (iteration_100: all passed)
- Self Journey: a wide banner `door-self-card-parallel` (`parallel/PpBanner.jsx`) sits below the 4 cards and opens the full-page portal `ParallelParentingView.jsx` (`pp-page`, hidden while overlays are open).
- Built from the user's partial HTML mockup (it was cut off; the user OK'd building the rest).
  - Screens: welcome (hero, banner, 6 feature cards, Start/Continue CTA) → 6 steps → summary.
  - Steps: Communication Boundaries, Parenting Time & Exchanges, Decision-Making, Information Sharing, Household Routines, Changes & Disagreements. Each has 2-3 single-choice questions and optional notes.
  - Header with brand, Step N of 6 progress, Back and Quick Exit; the crisis banner stays.
- Copy: `backend/parallel_parenting_content.json`, mirrored at `frontend/src/pages/portal/parallel/ppContent.json` (keep them identical).
- Backend `parallel_parenting_routes.py` (all endpoints require auth):
  - GET/PUT `/api/parallel-parenting/me`: collection `parallel_parenting_plans` {answers, notes, tips, step 0-6, completed_at}. Invalid ids are dropped.
  - POST `/ai/tip`: a 2-sentence tip after each step, saved to tips.{step}; grey-rock voice for flagged parents.
  - GET/POST `/ai/chat`: Guide chat with session_id, multi-turn via the stored transcript (last 12 turns) plus the plan's choices as context. Stored in `parallel_parenting_chats` (60-message cap). `_plain()` strips markdown.
  - POST `/pdf`: branded plan PDF (`parallel_parenting_pdf.py`) with choices, notes, Guide tips, a closing "Before you rely on this plan" box, and a "Planning tool only" footer.
- Frontend: `parallel/usePp.js` (usePpPlan with a 700ms debounced autosave; usePpChat), PpHeader, PpWelcome, PpStep, PpSummary, PpChat.
- Tests: `/app/backend/tests/test_parallel_parenting.py`.
- Dashboard image: the user saw an image at the end of the live dashboard. The preview no longer has it (the artwork was moved to the top earlier); the pending deploy fixes production. No code change.


## 2026-06 — Weekly note preview, Plan change log, page artwork (iteration_101: all passed; CB artwork screenshot-verified)
- Admin Weekly Note Preview: `components/WeeklyNotePreview.jsx` adds a "Preview note" button on the Weekly note tile.
  - It opens a dialog with 5 switches (sa, checkins, cp, cn, fb) and an iframe of the exact email (sandboxed; the unsubscribe link is the inert `#unsubscribe-preview`), plus "Email me this version".
  - Backend: `POST /api/admin/self-journey-weekly/preview {types?}` uses the new pure renderer `email_service.render_self_journey_weekly_note`. `/sample` now accepts an optional `{types}`; all-off returns 400. Both are admin-only.
- Parallel Parenting plan change log: collection `parallel_parenting_versions`.
  - A version is saved on PUT /me with completed:true (reaching "Your Plan") or on POST /pdf, only if answers/notes changed. The newest 20 are kept.
  - `GET /api/parallel-parenting/versions` (newest first, with diff strings like "Exchanges: A neutral public place → At school or daycare", using each question's `short` label in the content JSON) and `GET /versions/{id}/pdf`.
  - The plan PDF has a "Changes since your last version" box. Frontend: `parallel/PpHistory.jsx`, the "Plan history" section on the summary.
- Page artwork (user images): `selfAssessment/SaArtwork.jsx` (props name/alt; files `/images/{name}.webp` + `-640.webp`).
  - The user picked both placements, so it's responsive: on phones the image is at the top and the text title/subtitle are hidden (`Hero textClassName="hidden lg:block"`; the step pill stays); on desktop the text title stays and the image sits in the right column above the AI Insight panel.
  - Used on the Self-Assessment page (`sa-self-assessment`, testids sa-artwork-mobile/desktop) and the Communication Builder (`comm-builder-art`, testids cb-artwork-mobile/desktop).

## 2026-06 — Court Ordered page replaced with interactive Court-Ordered Journey picture (iteration_102: backend 7/7, frontend passed; FAB/toast overlap fixed after)
- New Court page = user's HTML mockup: header (SA CoParents Path, Hide/Show Hints, Emergent AI badge, Back, Quick Exit) + crisis bar, picture with hotspots, floating Emergent AI chat.
- Hotspots (courtContent.js): Accept invite -> popup (court reference number + full legal name, real code verify, saves court_key + new portal field court_legal_name, then opens next unfinished step). Steps: 1=Co-Parenting Relationship (card2), 2=Self-Assessment (card1), 3=Child Needs, 4=Foundation (Back returns to Court). Each step shows a live progress pill + popup with Start/Continue/Review + Ask Emergent AI.
- Summary hotspots: Alignment/Difference/Child show the parent's own results (GET /api/court-path/summary, backend/court_summary.py) + "Both-parent view coming soon"; Options & Resources lists BIFF builder, Parallel Parenting, court-ready PDF, checklist PDF, professional site, BIFF book, DV hotline.
- Tools under the picture: case details, Court-Ready PDF, BIFF check, Save Case & Open sacoparentsalign.online, Court Modules A/B/C, Court Checklist + PDF (PDF uses legal name).
- Court AI chat: multi-turn, saved per account (court_path_chats), "Start new chat" (POST /api/court-path/ai/chat/new; also /parallel-parenting/ai/chat/new), Grey-Rock for flagged parents, general guidance not legal advice.
- PENDING: user's real picture "SA CoParents Court-Ordered Journey_3.png" never arrived (ask_human can't carry files). A TEMPORARY stand-in drawn at the mockup's exact hotspot positions is at frontend/public/images/court-journey.webp (+ -640). When the user attaches the real image in chat: convert to webp (1024 wide + 640), replace both files, update srcSet widths, re-align hotspot % in courtContent.js, re-check desktop + 390px.
- Valid demo court keys: ALIGN-SA-2026, COURT-8842 (SA-DEMO01 is a joint-report case id, not a court key).

## 2026-06 — Both-parent comparison + AI drafts into Step 4 (iteration_103: backend 12/12, frontend passed; follow-ups self-tested)
- Comparison (backend/court_compare.py, GET /api/court-path/compare, POST /api/court-path/compare/share {shared}): parents linked by the SAME verified case code (exactly one other parent on the case), BOTH opt in ("Share my results for comparison", off anytime, collection court_compare_shares tied to the case code), never when either parent is safety-flagged (is_safety_flagged: safety_ack.flagged or IPV level). States: safety_off (flagged self, no toggle) / no_case / not_shared / waiting (also shown when the co-parent is flagged or not sharing — nothing leaks) / ready.
- Ready view in the Alignment / Difference / Child-Focused Needs popups (CourtCompare.jsx), area by area: Co-Parenting sections aligned when ratings match, Self-Assessment within 15 points; Child Needs shows both parents' actual answers side by side.
- AI drafts: long Court chat replies get "Send to Step 4" (new first Foundation field `statement` = "Our Foundation Statement", also printed in the Foundation PDF) and "Split into Step 4 boxes" (POST /api/court-path/ai/foundation-split → core_goals/child_needs/co_values/commitments). Replace / Add below when text already exists; saved to the account immediately (useFoundationBuilder.updateMany); "Open Step 4" opens the Foundation page with the builder open and "Back to Court Page".
- Court AI asked for a draft now returns only the draft (no questions/intro/outro).
- Demo pair: parent3/parent4 on PAIR-DEMO-01 (backend/seed_court_compare_pair.py).
- STILL PENDING: real Court-Ordered Journey picture (temporary stand-in in place).

## 2026-06 — Comparison PDF, shared talking points, sharing alert emails (iteration_104: backend 11/11 new + 12/12 regression, frontend passed)
- GET /api/court-path/compare/pdf (court_compare_pdf.py): only when both parents share (else 409). Names = court_legal_name (fallback account name), caller first; case code; Alignment / Difference (with "Talking point:" lines unless stale) / Child-Focused Needs answers side by side. Buttons: court-compare-pdf in each side-by-side section + court-tool-compare-pdf under the picture (muted + info toast until ready).
- POST /api/court-path/compare/talking-points: one calm AI opener per differing area (max 8), saved per case in court_talking_points (both parents see the same set), refresh button, `stale` when the difference set changes (perspective-free sha256 basis).
- Sharing alerts (court_compare_alerts.py, email_service.send_compare_share_alert / send_compare_ready_alert): on turning sharing on → co-parent gets "turned on sharing" email if not sharing yet; once both share → "ready to view" email to both. Max once a week per type per parent; never to safety-flagged parents; neutral wording, no results/names; failures logged in *_error and never break sharing; timestamps only on success.
- Seed resets shares, alert history and talking points for PAIR-DEMO-01.
- STILL PENDING: real Court-Ordered Journey picture (temporary stand-in in place).

## 2026-06 — Agreement tracker + celebration (iteration_105: backend 11/11, frontend passed)
- court_agreements.py (collections court_agreements per case+area, court_celebrations per parent+case). Either parent's "Mark as agreed" agrees a differing area for both; each parent can only undo their own mark ("I agree too" adds the other mark); optional shared "What we agreed" note (300 chars, kept after undo).
- Routes: POST /api/court-path/compare/agree {area key "<source>|<area>", agreed}, PUT /api/court-path/compare/agree/note, POST /api/court-path/compare/celebrated. Compare payload adds per-row key/agreed/by_me/by_them/note/agreed_at, progress {agreed,total,all_agreed,celebrated}, intent_notice.
- Required wording (user): "By marking an area as agreed, the parties have evidenced their intent to make an agreement. This document does not reflect a binding agreement on the parties." Shown in the Difference popup progress, the celebration, and the Comparison PDF (with "X of Y differing areas marked agreed", "Marked agreed by <names> on <date>", "What we agreed:").
- UI: court-agree-card progress bar under the picture (opens Difference), per-row controls, "Agreed after talking" list in Alignment, confetti "You did this together" dialog once per parent (canvas-confetti, reduced-motion safe).
- STILL PENDING: real Court-Ordered Journey picture (temporary stand-in in place).
- 2026-06: Court header toggle relabelled "Hide Action Buttons" / "Show Action Buttons" per user's latest HTML (same layout/hotspots otherwise). User's HTML references image "99e6eedf-aaa3-42b8-bfcc-a1aee76f22d5.png" — still not uploaded; stand-in remains.

## 2026-06 — Agreement alert emails + agreements to Step 4 (iteration_106: backend 10/10, frontend passed)
- court_agreement_alerts.py: on "Mark as agreed" (not undo) or a saved non-empty note, queue an item for the co-parent (collection court_agreement_alerts: pending[], last_sent_at). Send now if no email in the last 6 hours, else bundle into the next email (next change after the window, or the daily self-assessment-reminders cron, which now also calls flush_all — app is at the 5-cron limit). Email (send_agreement_update_alert) lists areas + note text and the intent wording; only while both share and neither is flagged; pending cleared if the pair breaks.
- Step 4: "Add to Step 4" per agreed area with a note + "Add all agreements to Step 4" → Foundation field co_values ("Agreed co-parenting principles & values") lines "<area> (agreed): <note>"; existing exact lines skipped; an edited note replaces that area's line. Foundation PDF prints the intent wording under any box containing " (agreed): ".
- User pasted a NEW, TRUNCATED HTML "SA CoParents - Safety & Communication Assessment" (quick-exit red bar, inclusive-care banner, 3-pillar assessment grid…) — cut off mid-CSS; not built yet. Ask the user to resend the full file and say where it goes.
- STILL PENDING: real Court-Ordered Journey picture (temporary stand-in in place).


### 2026-06 — Iter108 · Self Journey assessment artwork (replaces cards 1–3)
- Picture 1 `/images/sa-journey-assess(-640).webp` (founder upload "SA CoParents Journey Assessment Screen") —
  Self-Assessment + Co-Parenting Assessment panels; panel + arrow hotspots + 2 labeled buttons.
- Picture 2 `/images/sa-child-needs-assess(-640).webp` (agent-generated, same style) — Educational /
  Psychological / Medical; panel + arrow hotspots + 3 labeled buttons that open the matching
  Child Needs form directly (`openChildNeeds("self", key)` → `ChildNeedsView initialOpenKey`).
- Files: `portal/selfJourney/JourneyArtCard.jsx`, `portal/selfJourney/selfJourneyArt.js` (hotspot coords),
  `court/CourtJourneyArt.jsx` (`Spot` exported). Card 4 Foundation, PP banner, Comm Builder unchanged.
- Court hints toggle no longer wraps at 390px (verified iter108). Testing agent iter108: all pass.


### 2026-06 — Iter109 · Self Journey progress ring + Completed badges
- `selfJourney/AssessProgressRing.jsx` above Picture 1: "N of 5 assessments done", Next: <name>; tap opens next
  unfinished (order self → coparent → educational → psychological → medical); disabled at 5/5.
- "Completed ✓" pill on all 5 labeled buttons (`JourneyArtCard` `done` prop).
- Done sources: self = Self-Assessment history length > 0; coparent = GET /coparenting/me exists && completed
  (`useCoparentingDone`, refetch on modal close); child needs = `useChildNeeds` lifted into JourneyShell and passed
  to `ChildNeedsView` as `needs` prop (live sync, no reload).
- User re-attached Picture 1 (pixel-identical) — Educational/Psych/Medical picture stays agent-generated until founder
  uploads own artwork (then swap `/images/sa-child-needs-assess*.webp` + re-align `NEEDS_ART` coords).
- Testing agent iter109: all pass.


### 2026-06 — Iter110 · Founder Child Needs picture swapped in
- Picture 2 now founder artwork `/images/sa-child-needs-steps(-640).webp` (1024×1536, "Identify Your Child's Needs",
  boy tying shoe). Agent-generated `sa-child-needs-assess*` removed.
- Tap targets = the three icon+label bubbles (no arrows; `arrow` optional in JourneyArtCard). Coords in `NEEDS_ART`.
- Order everywhere (buttons + ring) now matches picture: Educational → Medical → Psychological.
- Self-tested via screenshot: each bubble opens the matching form, ring "Next" follows new order, no overflow at 390px.


### 2026-06 — Iter110 · Celebration, glow, Journey Summary PDF, PP picture + quick checks, full-screen option pages
- 5/5 celebration (`selfJourney/JourneyCelebration.jsx`, confetti, once per parent): backend `journey_summary_routes.py`
  GET/POST `/api/journey-summary/celebrated` (collection `journey_celebrations`). Shown only on Self Journey view with no overlay open.
- Next-step glow: `journey-next-glow` CSS on next unfinished picture spot + button, plus "Next" tag.
- Journey Summary PDF: GET `/api/journey-summary/pdf` (`journey_summary_pdf.py`), button under ring + in celebration dialog.
  Includes safety line + "not legal advice"; unfinished = "Not completed yet."
- Parallel Parenting founder picture (`/images/sa-parallel-builder*.webp`, `PP_ART`) replaced PpBanner on Self Journey:
  3 main buttons → Steps 1–3, 4 small → new quick checks. PpBanner/PpHeader deleted.
- 4 PP quick checks (`checklists` in both ppContent.json + backend content): child_focus, safeguards, court_check
  (self-check, not legal advice note), professional_review. Saved as `checks` on plan (validated), in versions, summary, PDF.
  Flow: Step 6 → "Continue to Quick Checks" → checks 1–4 → summary.
- Full-screen option pages in Comm Builder / Court layout via `selfJourney/JourneyPage.jsx` (work left, picture with
  tap spots + remembered Guide chat right; phones picture → work → chat): Co-Parenting (`coparenting/CoparentingAssessmentView.jsx`,
  replaces deleted modal, Picture 1), Child Needs (`ChildNeedsView.jsx` tabs + bubbles switch inline form, auto-advance
  after save), Parallel Parenting (`ParallelParentingView.jsx`). New chats: `/api/journey-guide/{coparenting|child-needs}/chat`
  (+ `/new`), collections `coparenting_guide_chats`, `child_needs_guide_chats`.
- Testing agent iter110: backend 12/12, frontend pass; main agent self-verified 390px ordering/no overflow and
  celebration dialog (once only). parent1 restored to 4/5 + celebrated=false afterwards.


### 2026-06 — Iter111 · Child Needs reframe, privacy notices, help, signatures/notary, Court picture cards
- Educational / Medical / Psychological forms reframed from founder HTML: tabs, white card, purple header divider,
  rating matrix, header "SA CoParents Assessment Portal · Private to your account". New questions come first; old
  co-parenting questions sit under "Across both homes"; saved answers kept. Content JSON is the same in backend and frontend.
- Save Draft (drafts.<cat>, not completed) vs Submit (marks Completed ✓ + downloads the report).
- Confidentiality + Health Information Privacy notices (`childNeeds/ChildNeedsNotices.jsx`) at the top of each form.
  A one-time "I understand" step is required before the first save, remembered as `notice_ack_at` (422 without it).
  Both notices print in the Child Needs PDF and the Journey Summary PDF. No HIPAA-compliance claim.
- "Help me answer" per text field (`childNeeds/FieldHelp.jsx`, POST `/api/journey-guide/child-needs/suggest`; not
  offered on selects, ratings or help:false fields). Remembered Guide chat: right column on desktop, under the form on phones.
- Foundation Statement + Co-Parenting Agreement (renamed from Joint Alignment Report) PDFs: signature page (printed
  name / signature / date for both parents, optional typed /s/ e-signature via `components/ESignField.jsx`) plus a
  general US notary page per signer (`backend/pdf_sign_notary.py`). Legal note: signing or notarizing confirms who signed;
  it does not make the document a court order or binding without court approval. Not legal advice.
- Parallel Parenting Court-Order Notes PDF (POST `/api/parallel-parenting/court-notes/pdf`).
- Court page picture cards: `court-art-needs` + `court-art-parallel` with buttons that open each form or step.
- Testing agent iter111: backend 12/12, frontend all testids verified, no issues.
- Close-out (main agent): at 390px the Court "Tap the picture or the cards" hint is one line (15px tall); the page has no
  horizontal overflow (Court chat quick-prompt chips scroll sideways in their own overflow-x-auto row, by design).
- Pending: user acceptance testing of all Iter108–111 work.


### 2026-06 — Child Needs Guide starter questions
- `GuideChat` takes an optional `starters` prop ({label, items}). It shows an always-visible "Quick questions · <form>"
  row just above the message box, scrolling sideways. Tapping a chip sends it straight to the Guide; chips are disabled
  while the Guide is replying; the row resets when the tab changes. The empty-state suggestions row is hidden when empty.
- `ChildNeedsView` `STARTERS` holds 4 founder-approved questions each for Educational / Medical / Psychological,
  switched by the active tab. Testids: `cn-chat-starters`, `cn-chat-starters-label`, `cn-chat-starter-{0..3}`.
- Self-tested (screenshot): label + chips switch per tab; a tap sent the question and got a Guide reply; row stays after
  the chat starts; no page overflow at 390px.


### 2026-06 — Child Needs · Send to a provider
- Parents never type an address: recipients = professionals who ACCEPTED one of this parent's "Share with a Professional"
  invitations (`parent_professional_invitations`, accepted_at set, status accepted/access_expired; revoked excluded; deduped
  by email). None yet → empty state with a link to `/share/professional`.
- Backend `child_needs_share_routes.py`: GET `/api/child-needs/providers`, GET `/api/child-needs/shares`,
  POST `/api/child-needs/share {provider_id, categories}` (404 not an accepted provider; 422 unknown or not-completed form).
  Builds one PDF with only the ticked forms (`build_child_needs_pdf`) and emails it via
  `email_service.send_child_needs_report` (Resend, reply-to parent, `require_encrypted=True` so Virtru-forced setups fail
  closed). The share is saved in `child_needs_shares` only after a successful send. Form order: Educational → Medical → Psychological.
- Frontend: `childNeeds/SendToProvider.jsx` (button + dialog: pick provider → tick completed forms, current form ticked,
  "Select all (full report)" → confirm screen showing who gets what + "health details leave SA CoParents, can't be unsent"
  → Send now), `ShareProviderSteps.jsx`, `SentToList.jsx` ("Sent to" under each completed form), `useProviderShares.js`.
  Placed next to Submit (only when that form is Completed, signed-in parents) and beside the Journey Summary download
  on Self Journey (`door-self-send-provider`, shown when ≥1 child-needs form is completed).
- Test data: `seed_child_needs_provider.py` upserts accepted provider "Dana Reyes (test)" (delivered@resend.dev, Resend
  test inbox) for parent1.
- Self-tested: curl (providers/shares/share + 401/404/422) and screenshots (desktop + 390px dialog, real send, Sent-to
  list refresh, Journey button). Testing agent not run yet.


### 2026-06 — INTEGRATION_SHARED_SECRET rotated (preview)
- Founder supplied a new "sacoparents shared secret" (kept in Keeper). It's saved single-quoted in backend/.env (special
  characters: # $ etc.); the value never goes into docs. Verified: new key passes the gate (404 on a dummy code); old key → 401.
- Align side NOT switched yet → until it is, Align calls to this preview get 401 "Invalid integration key" and completion
  webhooks are signed with the new key. Legacy tests that hardcode the old hex key (e.g. tests/test_iter139_*) will fail; expected.


### 2026-06 — Two-key switchover + Individual Journey tidy-up
- Two-key switchover: `backend/integration_keys.py` `match_integration_key()` accepts INTEGRATION_SHARED_SECRET ("new") or
  INTEGRATION_SHARED_SECRET_PREVIOUS ("old", the prior hex key) on every Align-facing check (integration_routes,
  joint_alignment_routes, parent_professional_invitations). While PREVIOUS is set it logs `align integration key used=new|old|invalid`
  (key values never logged). Outbound completion webhooks are signed with the new key (ALIGN_COMPLETION_WEBHOOK_URL unset → none sent).
  END OF SWITCHOVER: when the founder confirms Align switched (logs show used=new only), delete the
  INTEGRATION_SHARED_SECRET_PREVIOUS line from backend/.env and restart the backend. Verified: new/old → pass, wrong/empty → 401 on
  link-code verify, joint-alignment case and report-permission routes. Legacy tests now strip quotes when reading the key (iter168: 19 passed).
- Individual Journey: removed the duplicate welcome picture (`door-self-welcome-image`); the main dashboard keeps it (`door-welcome-image`).
- Individual Journey: green arrow `selfJourney/FlowArrow.jsx` (`door-self-flow-arrow`, gentle nudge, reduced-motion safe)
  between the Self/Co-Parenting picture and the Child Needs picture.
- 2026-06: Green arrow enlarged ~5x per founder: 160px circle on phones / 220px on desktop, 80/110px icon, thicker ring, 10px nudge.
- 2026-06: Arrow reduced by 1/3 (107px phones / 147px desktop, 54/74px icon) + pulsing green glow (`sa-arrow-glow`, 2s; static glow when reduced motion). Still decorative (not tappable).
- 2026-06: Arrow ring changed to a solid 8px WHITE circle; the pulsing green glow is outside the white ring.
- 2026-06: Arrows are now tappable buttons (`FlowArrow({testid,to,label})`; smooth-scroll to the target testid with a 76px scroll margin for the sticky header). There are 5 on the Individual Journey: assess→needs (`door-self-flow-arrow`), needs→foundation (`-foundation`), foundation→parallel (`-parallel`), parallel→Communication Builder (`-biff`), and Communication Builder→finale rewards (`-rewards`, only when allThreeDone). Tests must click them with force=True (they bob).
- 2026-06: KEY SWITCH FINISHED. The founder confirmed Align uses the new key. INTEGRATION_SHARED_SECRET_PREVIOUS was removed from backend/.env and the backend restarted. Old key → 401, new key → accepted. The `integration_keys.py` helper stays; it logs nothing while no previous key is set. For a future switchover, add INTEGRATION_SHARED_SECRET_PREVIOUS again.
- 2026-06: Step badges on the arrows (`FlowArrow` `step` prop): a white pill on the circle's top-right showing "3 of 6", "4 of 6", "5 of 6", "6 of 6" and "Finish" (rewards). Testids: `<arrow-testid>-step`. Steps 1–2 = Self-Assessment and Co-Parenting; the Foundation card already shows 4.
- 2026-06: Finished-step badges. `FlowArrow` `done` prop turns the badge purple with a white check ("✓ 4 of 6"; data-done="true").
  The rules: 3 = all three Child Needs forms submitted; 4 = Foundation saved (`foundationBuilder.savedAt`); 5 = Parallel Parenting
  plan summary reached (`selfJourney/useParallelDone.js` → GET /api/parallel-parenting/me `completed_at`, re-checked when the builder
  closes); 6 = at least one message reworked (`biffAuthoredCount > 0`); "Finish" never changes.
- 2026-06: "6 of 6 finished". allStepsDone = all 5 assessments + Foundation saved + PP completed + ≥1 BIFF rewrite.
  `selfJourney/AllStepsBanner.jsx` (`door-self-all-steps-banner`) is a solid purple banner above the progress ring. While all steps
  stay done it shows every visit. The purple star sparkle (canvas-confetti, stars) plays ONCE per account: flag at
  GET/POST /api/journey-summary/steps-celebrated (collection `journey_step_celebrations`, separate from the 5-of-5 flag). The sparkle
  waits until the 5-of-5 dialog and any builders are closed. Test account journey6@test.com (seed_journey_six.py). Verified: sparkle on first
  visit, banner persists, no sparkle after reload, all badges ✓, no overflow at 390px.
- 2026-06: Founder chose to SKIP provider "Opened" receipts; reports stay as PDF attachments.


### 2026-06 — Continue button, certificate, Court arrows
- `selfJourney/ContinueStep.jsx` (`door-self-continue`): "Continue at Step N" at the top of the Individual Journey while any step is
  unfinished, with "<label> · X of 6 steps done". It scrolls to the first unfinished step (`scrollToTestId`, exported from FlowArrow.jsx).
  `journeySteps` in JourneyShell is the single source for step done-state (arrows, Continue, allStepsDone).
- Certificate: POST /api/journey-summary/certificate {name 1–80} → landscape Letter PDF (`journey_certificate_pdf.py`: logo, name,
  "Finished on <steps-celebrated date or today>", six steps with drawn ✓, the founder-approved "not a court-approved parenting course
  certificate and not legal advice" note). The server re-checks all 6 steps → 422 listing missing steps; blank name → 422.
  `selfJourney/CertificateButton.jsx` sits in the 6-of-6 banner (`door-self-certificate-btn` → dialog with editable name prefilled from the account).
- Court Ordered: half-size `FlowArrow size="sm"` (`.sa-arrow-sm` glow) between the 4 numbered step cards (`court-flow-arrow-{2..4}`,
  badges "N of 4", purple ✓ when that step's checklist status is done).
- Verified by screenshots + curl (parent1 Continue at Step 3 → scrolls to Child Needs top=76; journey6 certificate download; Court badges 2✓ 3 4✓).


### 2026-06 — Picture pages for Educational / Medical / Psychological + journey reorder (iter112 ✅)
- Founder pictures saved as /images/sa-needs-{educational,medical,psychological}(-640).webp. `childNeeds/needsPageArt.js`
  (NEEDS_PAGE_ART) holds the 4 icon tap spots per picture plus "start" (the round › button), each mapped to field ids.
  `ChildNeedsView` shows the active tab's picture. Tapping an icon scrolls to its questions and flashes them
  (`[data-field]` wrappers, `.cn-field-flash`); "start" scrolls to the first question.
- The Child Needs page has no Hero now: picture at the very top on phones, then portal bar, tabs, form, then `childNeeds/NeedsProgress.jsx`
  (`child-needs-progress`: N of 3 + bar + per-form status chips that switch tab + Sent-to list + report download + disclaimer), then chat.
  `JourneyPage` hero is optional.
- Content: medical has a new optional `med_preventive` ("Preventive Care: check-ups, vaccines, dental and vision"). edu_iep is relabelled
  "IEP, ARD, 504 Plan, or Learning Accommodation Status". The backend and frontend JSON are identical; test_child_needs expects [7,10,7].
  Psychological: no new questions (founder choice). Social→psy_household; Strengths→psych_therapy + psych_goal.
- Individual Journey reorder (founder): Continue button at the top, then the pictures, and accomplishments (`door-self-progress`: 6-of-6 banner,
  5-of-5 ring, Journey Summary, Send to a provider) at the END just before the badges. The "Finish" arrow now targets door-self-progress.
- Testing agent iter112: backend 7/7 + 5/5 regression, frontend 100%, no issues (tests/test_iter112_journey_cert_and_med_preventive.py).


### 2026-06 — Picture done ticks, certificate sharing, Court 2×2 form pictures
- Live purple ticks: `ChildNeedsForm` `onValuesChange` → ChildNeedsView `live` values. An icon gets a purple tick (`cn-art-done-<icon>`,
  `ArtPicture tickClass`) once ALL its mapped fields are non-empty on screen, and updates while the parent types.
- Certificate sharing (`backend/journey_certificate_routes.py`, prefix /api/journey-summary/certificate): GET /recipients (co-parent
  linked by court case code via court_compare `_case_key`/`_coparent`, hidden if EITHER parent `is_safety_flagged`; plus accepted
  professionals, deduped by email), POST /send {recipient_id, name} (same 6-step gate via `certificate_bytes`; Resend email
  `send_journey_certificate` with the PDF attached; reply-to parent), GET /shares. Collection `journey_certificate_shares`.
  Frontend `selfJourney/CertificateShare.jsx` (`door-self-certificate-share-btn` → tap a person → "Send to X (Role)?" → Send now).
  "Certificate sent to" list inside the 6-of-6 banner (`door-self-certificate-sent`). No typed addresses.
- Court page `court/CourtPictureCards.jsx`: 2×2 grid of the Educational / Medical / Psychological form pictures
  (`court-art-needs-<cat>`; tap the picture or `-btn` → open that form; tap an icon `-panel-<icon>` → open the form and jump to those
  questions via ChildNeedsView `initialJump`) + Parallel Parenting card.
- Self-tested (curl + screenshots); see the iter113 testing agent report.

- iter113 testing agent: 11/11 backend + all frontend checks passed, no action items.

### 2026-06 — PostHog removed
- Deleted the PostHog snippet (session recording on, host us.i.posthog.com) from `frontend/public/index.html`.
  The dev server only served the new copy after a frontend restart.
- `AppStorePrivacy.jsx`: removed the "Product-analytics events (PostHog, self-hosted)" row, PostHog from the
  service-provider list, and the "Turn off product analytics" bullet (no analytics remain).
- Verified: no "posthog" in the code; browser loads of /, /login and /legal/app-store-privacy made 0 PostHog requests and
  `window.posthog` is undefined. `assets.emergent.sh/scripts/emergent-main.js` has no PostHog references.
- Past recordings: support says to email support@emergent.sh (job ID + key prefix phc_xAvL…) about who owns the
  project and how to delete recordings. Production keeps sending data until the user deploys.


### 2026-06 — Privacy plan A–G (iter114: backend 9/9, frontend verified; PP fix re-checked by screenshot)
- A. Child record folders removed: `RECORDS_ENABLED=false` (portalStorage.js); RecordsDrawer returns null; PUT /portal/state forces
  align_records=[]; complete-report PDF + /portal/share never carry align_records (stored payload stripped). Startup purge in server.py
  ($set align_records=[] on portal_state, $unset payload.align_records on portal_pdf_shares) — purged 5 accounts + 3 share links in preview.
  Browser: SacoparentsPortal clears `sacoparents_align_records` and guided drafts for medical/educational/psychological. Forms kept.
  No upload feature exists or is planned (founder: no child documents stored).
- B. First-visit notice (LegalAcknowledgment) has a "Your privacy" box (components/privacy/PrivacyLinks: policy, /privacy#your-rights,
  /what-professionals-see, #by-assessment). Login has `LoginPrivacyBox`. `lib/useHashScroll` scrolls hash anchors (Privacy + new page).
- C. Public page /what-professionals-see (pages/WhatProfessionalsSee.jsx; all wording in lib/proVisibility.js, written from real code paths)
  with visible "Draft, pending attorney review" label + "Attorney review" tags (Align + court sections). `ProSeeLink` (new tab) on every
  sharing screen (Child Needs confirm, certificate share, Shared with professionals, Share with a professional, Foundation share modal,
  Pathway email, ReportShareControls, Summary email-mediator, Safety results + intro, Joint report/agreement, Child Needs notices).
  `SharingNotice` ("Who sees this") in Self-Assessment, Communication Builder, Parallel Parenting. Copy fixes: Summary email dialog and
  SendToProvider no longer say "attach"/"emailed".
- D. Self-Assessment tabs (`SaTabs`: My results | Progress over time). `ProgressOverTime`: one recharts line chart per area +
  `GoalTimeline` (set = completed_at, reached = new SAEntry.reached_at). POST /api/self-assessment/goal/reached {entry_id, reached}
  (404 unknown, 422 no goal). Picture spot "Track Your Progress" opens the Progress tab.
- E. JourneyPage: hero now sits inside the grid (phones: picture → pill → work → chat, like Communication Builder) + optional
  `banner` (BottomBanner). Child Needs hero: "<n> of <total> questions answered" (cn-step-pill/cn-answered-count). Parallel Parenting:
  BottomBanner + `PpActionButton` (new picture /images/sa-parallel-action(-640).webp): welcome → START/CONTINUE/VIEW plan; other
  screens → "SEE ALL STEPS AND QUICK CHECKS" (back to welcome, which shows the Who-sees-this notice).
- F. /legal/app-store-privacy: Google Play Data Safety section (GOOGLE_ROWS, not-collected list, why Shared=No, attorney note about
  Align), Apple answers corrected (no Usage Data/diagnostics; added voice notes + optional Gmail as ephemeral), delete URL from
  REACT_APP_PARENT_URL. Founder must copy these into App Store Connect + Play Console.
- (Gap closed in the next batch below.)

### 2026-06 — Align lock, mediator answer choice, attorney switch, goal celebration (iter115: backend 15/15, frontend 100%)
- Align lock: new `align_links` collection {user_id, email, context, linked_at, unlinked_at}. verify-link-code records the link;
  export-assessments + integrations/foundation-statement.pdf require an active link (else the same 404 'No linked parent found').
  Startup `migrate_verified_links` keeps parents whose link code was already 'verified' ($setOnInsert, never re-links; 32 in preview).
  Every Align read → `align_access_log` {user_id, endpoint, redacted, at}. Parent: GET/DELETE /api/integrations/align-link;
  Account page `AlignLinkCard` (status, last read, Unlink with AlertDialog). Relinking needs a new code.
- Safety firewall (founder's production plan): if `is_safety_flagged` (quick check flagged OR safety level ≤ 2) the export is
  `redacted_for_safety: true` (snapshot only completed_sections/updated_at; Foundation narratives null; special needs only
  rating_areas + generated_at) and the Foundation PDF returns 403.
- Mediator email: MediatorEmailBody.include_answers (default false) → Section 1 + 2 excluded unless ticked; recorded as
  mediator_emails[].included_answers. Dialog checkbox `mediator-include-answers`.
- `ATTORNEY_REVIEW_PENDING` in frontend/src/lib/proVisibility.js — flip to false when the attorney approves (hides draft label + tags).
- `GoalReachedBanner` (selfJourney): once per goal (localStorage `sac_goal_celebrated_<uid>`), confetti + banner on Self Journey.
- Founder's pasted plan (Vercel/Postgres/RLS migration) NOT actioned: this app runs on Emergent hosting + MongoDB; pending discussion.
- Known stale test: test_safety_assessment_mediator_email.py::test_metadata expects 10 section_1 questions (now 28).

### 2026-06 — Link From Account, Align Read History, attorney approval (iter116: backend 6/6, frontend 8/8)
- AlignLinkCard now has `AlignLinkCode` (POST /link-codes {context:'account'}; 15-min code, copy, timer, "type it on
  sacoparentsalign.com"; polls align-link every 8s and flips to Linked; safety-gate 403 shows message + safety screen link)
  and `AlignReadHistory` (last 5 reads from align_access_log: date/time, what, note when redacted/blocked).
- GET /api/integrations/align-link → recent_reads [{at, what, redacted, note}] (max 5, newest first).
- Attorney approved the professionals page wording: ATTORNEY_REVIEW_PENDING=false (label + tags hidden; flip back to show).
- Deploy requested by founder after this batch.

### 2026-06 — Self Journey step 6 picture card
- Purple Communication Builder hero card replaced by `selfJourney/CbJourneyCard` (full comm-builder-art picture, same width as the
  other step pictures + "OPEN COMMUNICATION BUILDER" button + "X messages built" count). Picture (testid door-self-card-biff) and
  button (door-self-card-biff-open) both open the full CommunicationBuilderView (onOpenCommBuilder), like the Court path.
  The quick BIFF Coach drawer is still on the bottom-nav "BIFF Tool". Self-tested by screenshot (390 + 1920). Not yet deployed.

### 2026-06 — Court-Ordered page: menu instead of arrows (iter117: backend 6/6, frontend 100%)
- StepCards (4 numbered cards + FlowArrows) and the 2×2 CourtPictureCards grid replaced by `court/CourtMenu.jsx`: 7 options
  (MENU in courtContent.js: coparent, self, educational, medical, psychological, foundation, parallel), any order, each with an
  "Asked by my professional" tick (`useCourtRequested`: GET/PUT /api/court-path/requested → collection court_requested;
  localStorage 'sac_court_requested' when signed out). Hero pill: "X of Y requested done" (or "N of 7 done" with no ticks).
- Court accept → opens first ticked unfinished option, else scrolls to the menu. All "Step N" wording on the Court page replaced by
  names (Foundation Statement, Co-Parenting Assessment...); court artwork keeps its printed numbers. Individual Journey keeps arrows.
- (Account deletion gap fixed in the next batch.)

### 2026-06 — Complete account deletion, professional ticks, requested checklist PDF (iter118: backend 9/9, frontend 100%)
- `backend/account_purge.py` `purge_account()` (called by DELETE /api/auth/account): walks every collection and deletes docs whose
  UID_FIELDS / EMAIL_FIELDS match (recipient `email` ignored for child_needs_shares + journey_certificate_shares); SKIP = global/config
  collections. COMPLIANCE (phi_access_log, legal_acknowledgments, hb300_acknowledgements, hb300_access_requests) are kept with ids →
  `deleted_<sha256[:16]>`, emails → null, name/ip/user_agent unset. Shared: joint_alignment_cases parent slot scrubbed
  (name "A parent deleted their account", email "", user_id/token null, account_deleted_at); professional fields scrubbed if the user
  was the professional; court_agreements $pull marked_by; deep-dive compare snapshots for their shares deleted; secure documents +
  GridFS files (bucket secure_doc_files) deleted; users.invited_by_user_id unset; record in `account_deletions` {anon_id, deleted_at}.
  POST /portal/share now stores user_id when signed in (older anonymous links can't be attributed). DeleteAccount page copy updated
  and it clears localStorage/sessionStorage (home page re-creates empty default keys — no data, cosmetic).
- Professional ticks: GET /api/court-path/requested runs `_sync_professional_requests` — once per source ("court:<case_id>",
  "case:<case_id>") adds keys to keys + pro_keys (+ pro_name). Sources: portal_court_keys.requested for the parent's court_key, and
  joint_alignment_cases (required assigned_steps; fallback primary type; CASE_STEP_TO_KEY). Response {keys, professional_keys,
  professional_name}. New Align endpoint POST /api/integrations/court-keys {key, case_id, mediator_name, expires_at?, requested[]}.
  CourtMenu `ProNote`: "Set by <name>" when ticked / "Your professional asked for this" when unticked.
- Checklist PDF: with ticks → case + safety + only ticked assessments (Edu/Med/Psych separate, Parallel Parenting Plan) + header note;
  no ticks → old full list. JSON checklist for the Court card unchanged.

### 2026-06 — Communication Builder trust fix, welcome, court page, privacy wording, sample history purge (iter137: backend 9/9 unit + 4/4 live, frontend 95% → crash fixed + self-verified). PREVIEW ONLY, NOT DEPLOYED.
- AI suggested wording (`backend/portal_ai.py`): `_KEEP_RULES` prompt (every date/time/number/question/boundary kept, no "...");
  `missing_facts()` checks numbers (exact), day/month words, question count, first-person boundaries ("I can't/won't/will stop…",
  "please don't") and ellipsis; one retry naming the gaps; still missing → `{status:"unavailable", biff:"", risk:null}`. OK →
  `{status:"ok", biff, flags, risk, missing:[]}`. Provider failure → 502 "Suggested wording isn't available right now."
- Frontend: no rule-based placeholder or tone label any more. `biffStatus` idle|loading|ai|unavailable in SacoparentsPortal;
  risk badge only when status "ai"; editing the draft clears the suggestion; BIFF drawer no longer auto-sends while typing
  (explicit `biff-suggest-btn`). Unavailable → `commBuilder/SuggestUnavailable.jsx` (Try again + fill-in template from
  `fillInTemplate.js`, copies the parent's question/date/time/boundary sentences verbatim, labelled "not checked by AI").
  `AiDraftNotice` directly above both draft boxes. Renamed to "Suggested wording" / "Copy with date stamp"; footer
  "Secure & Private analysis by Emergent AI" replaced. Self-Assessment progress + START button removed from the builder.
- Sample history: DEFAULT_MILESTONES / DEFAULT_BIFF_LOGS removed (history starts empty). `portal_routes.purge_sample_history`
  runs on boot ($pull of the exact sample objects from portal_state + portal_pdf_shares payloads; preview removed 20) and
  PUT /portal/state strips them (`without_samples`); frontend `withoutSamples` cleans localStorage. BiffMilestones guards
  milestones without `type`.
- Welcome: buttons (door-court, door-self, new door-comm "Not a separate path") above the artwork; artwork caption + "Tool for
  either path" badge; "Individual Journey" → "Self Journey" everywhere (incl. certificate PDF + email).
- Court page: `CourtMenu` = the one requested list (summary "X of Y done · Z remaining", requested rows then others);
  `CourtReports` = all PDFs (completion summary + send, court-ready, checklist, comparison); `CourtMoreTools` collapsed
  (case/communication tools, pillar tiles, court modules, checklist list). Mobile order: list → artwork → rest → chat.
- Privacy: `CASE_EXCEPTION` first on What Professionals See; case method + notices updated; `CaseVisibilityNotice` in the court
  accept dialog and Join invitation page; legal-ack modal + login privacy box mention the exception. Verified against code:
  professionals get status + dates only; joint-case bundle only at both_complete; no Self-Assessment answers path.
- Not changed: Privacy Policy legal text (Privacy.jsx §"does not share … unless you choose") — attorney-owned.


### 2026-10 — Privacy Notice consent, /privacy-notice, redirects (PREVIEW ONLY, NOT DEPLOYED; self-tested: pytest 11/11 + screenshots)
- `backend/privacy_consent.py`: PRIVACY_NOTICE_VERSION "2026-10-16-v1" (single source) + PRIVACY_NOTICE_TEXT_SHA256 of
  `frontend/src/pages/privacyNotice/PrivacyNoticeContent.jsx` (test fails if text changes without a bump). `consent_fields()`
  422s unless both boxes true; server sets consent_at. Enforced on /auth/register, /auth/signup-from-token, /auth/claim,
  /invites/coparent/accept/{token}. `log_consent` appends `privacy_consents` + upserts `legal_acknowledgments` v1.
  `POST /api/privacy-consent` (any signed-in user), `GET /api/privacy-consent/version`. UserPublic.consent_current.
- Frontend: `components/privacy/ConsentFields.jsx` (pop-up's two lines + 2 boxes) on Register, AccountSetup, InviteAccept
  (also fixed refresh→checkAuth bug), ClaimAccount; `ConsentGate.jsx` wraps <Routes> in App.js (replaces the app for signed-in
  users without current consent; open paths listed in the file). LegalAcknowledgment now only for signed-out visitors and
  skips account-creation pages. PrivacyLinks "Privacy Notice" (old policy/rights links removed). GlobalCopyright footer link
  on every page; AppFooter + Landing footer → /privacy-notice. /privacy, /privacy-policy, /confidentiality → /privacy-notice.
- tests/conftest.py ticks both boxes for older suites (requests only); tests/test_privacy_consent.py uses httpx.
- PENDING: user's exact Privacy Notice text (page is a labelled placeholder) and the AI-warning HTML/JS/CSS file.
  AI-warning scope agreed: Communication Builder/BIFF (/portal/biff-refine), all chats (3 Guides, Court, Parallel Parenting,
  AI Coach), summaries (pop-up on Generate + server refusal), auto demo session for signed-out AI use at "/".
- Admin consent counts: `GET /api/analytics/admin/consent-counts` (require_admin; counts only: current version, accounts
  consented/pending, demo sessions, by_version, current_version_by_source) + `/admin/consent` page (AdminConsentCounts.jsx),
  cross-linked with /admin/accounts. Self-tested: admin 200, non-admin 403, unauth 401, no "@" in output, 390px no overflow.
- Consent trend chart: built then REMOVED at user's request ("Don't build the consent chart").
- AI-warning work: NOT started (user: "Not yet"; approved privacy notice + AI warning instructions to come in separate messages).


### 2026-10-16 — AI privacy warning + Consent Trend + Privacy Notice v2 (PREVIEW ONLY, NOT DEPLOYED)
- AI notice: `backend/ai_notice.py` (AI_NOTICE_VERSION), `ai_notice_routes.py` (`/ack` needs current privacy consent → 409
  otherwise; `/send-anyway` logs user_id/at/version/feature/labels only), `require_ai_notice` (428) on every AI route.
  Frontend: `components/aiNotice/*` (Provider, Radix-based TrapModal so it stacks over Radix dialogs like Court chat,
  sticky checkbox/Continue footer, ack error message), `useAiGuard` lock on all AI inputs, `AiNoticeNeeded` for auto-AI
  (incl. Parallel Parenting step tips). Consent first: tapping an AI box on an open page (e.g. /legacy) shows
  "Before you continue" (ConsentGate + provider needConsent), then the AI pop-up opens by itself at the same scroll spot.
- Consent Trend: `/admin/consent-trend` (admin only, 403 otherwise), 12 UTC Monday weeks, real accounts, <5 sign-ups hides
  all 4 numbers; linked from /admin/consent and /admin/accounts.
- Privacy Notice: user's exact text in `PrivacyNoticeContent.jsx` (sections 1, 2, 7, 12 only; anchors #promise #collect #ai
  #contact); PRIVACY_NOTICE_VERSION 2026-10-16-v2 (everyone re-consents). Known text-vs-app conflicts reported to user, text unchanged.
- Tests: iteration_138 (HIGH court-chat pop-up + MEDIUM /legacy consent bugs), iteration_139 (both fixed; BIFF-drawer Escape
  regression → fixed with onEscapeKeyDown stopPropagation, self-verified). Backend 68 tests pass.
- Left as is (user choice): signed-out first-visit pop-up POST /legal/acknowledge → 401 (harmless).


### 2026-10-17 — Safety Gate + admin daily counts + whole-app mobile accessibility (PREVIEW ONLY; a deploy was started by the user, not by the agent)
- Safety Gate (case-level config from Align; screening happens in Align "Step 0" only):
  - Backend: `case_safety.py` (encrypted record per SA-XXXXXX case, SAFETY_ENC_KEY; resolved flags identical for both
    parents; audit log `safety_audit_log` for every read/write), `case_safety_routes.py` (`POST /api/internal/safety-status`
    HMAC-SHA256 `X-Align-Signature` with ALIGN_WEBHOOK_SECRET, 5-min timestamp window, version must increase, 401 + no change
    otherwise, 200 with no details, hidden from docs; `GET /api/case-settings`; support view mode only; admin CSV export
    (logged); `GET /api/admin/safety-audit-log/daily-counts` = last 30 UTC days applied/ignored/downloads, counts only, logged),
    `plan_options_routes.py` (parallel_parenting referral → protective options only), `help_routes.py` (admin-editable state
    services), `media_scrub.py` (EXIF/metadata removal helper only — app does NOT share photos, per user).
  - Frontend: CaseHomeNotices (banner + "View options" card on portal home), CaseSettingsBanner in Communication Builder and
    BIFF drawer, /case-settings, /plan-options, /help (no offline cache in SW sac-v3; native screenshot block via
    @capacitor/privacy-screen on next app build — browsers can't block), /calendar quick-exit (replace nav, Back can't return),
    /admin/audit-log (export + DailyCountsTable), /admin/help-services.
  - Old parent safety check-in OFF: no questions asked/saved/used, invite gate off, old answers kept but unused; old links → /help;
    Grey-rock = plain manual tone toggle (no reason, no advocate mode, milestones always normal). AI guardrail rule 7: tone checks
    flag only the sender's own aggressive/threatening words; never tell a parent to apologise/soften/reply.
  - User decisions: no Step 0 link in sacoparentsapp (Step 0 stays in Align). Answers on Align's Step 0 + notices given to user
    to paste to their other assistant (open items for Align: send screening_offered only when both parents completed/declined;
    "required step" vs skippable wording; reminders handled by Align).
  - Tests: backend tests/test_safety_gate.py (21) + test_safety_gate_external.py → 34 pass. iteration_140/141 frontend Safety Gate
    regression passed for two linked parents.
- Mobile accessibility (whole app, ~100 routes at 390px guest/parent/admin; scripts in /app/memory/a11y_scan.py + a11y_report.py,
  results /app/memory/a11y/scan5.json): axe WCAG 2.2 AA = 0 violations. Fixes: tertiary text #857E9C→#6E6787 + other low-contrast
  accents darkened, labels/ids on forms, login/register inline errors (role=alert, aria-invalid), <main>, single h1, 24px targets,
  focusable scroll regions, px→rem text (scales with text size), lib/useDialogFocus.js (dialog role, focus in/trap/Esc/return) on
  DrawerShell, GuidedJourneyModal, Communication Builder; reflow at 320px and 200% text (header/door cards/bottom nav wrap,
  body overflow-wrap:anywhere, sonner toaster kept on screen). Footer "Get help" link (not on /calendar).
  - iteration_142: 16/20 passed; the 4 remaining (portal home/CB at 390@200%, header brand, AiInsightPanel pill) fixed after and
    self-verified (scrollWidth 390 at 390@200%, 320 at 320px). Not possible here: real VoiceOver/TalkBack on a device.

### 2026-10-17 — Align Status Check + Spanish Get help + Quick exit calendar polish (PREVIEW ONLY; iteration_143: backend 9/9 new + 35/35 regression, frontend 100%)
- Align status: refused webhook calls (bad_signature / old_timestamp / invalid_body / replay) stored in `safety_webhook_rejects`
  with only at + reason (+ TTL `created`, 35 days; max 60 stored per minute so a flood can't grow it). `GET /api/admin/safety-audit-log/align-status`
  (admin, no-store, logged as view_align_status): last_update {at, applied|ignored}, last_applied_at, last_rejected, rejected_30d.
  Daily counts gained a `rejected` column. UI: `AlignStatusPanel.jsx` + "Refused" column on /admin/audit-log. Preview counters
  include test traffic.
- Get help in Spanish: `lib/helpCopy.js` (EN/ES strings), toggle `help-lang-toggle`, `<main lang>`, choice saved in localStorage
  `sac_lang` (user chose remember), auto-Spanish when browser language is es-*. Admin-typed local services shown as typed.
- Quick exit calendar: `lib/sampleCalendar.js` made-up weekly events, day buttons + agenda, Today + Close (→ "/"), tab title
  "Calendar" + plain calendar favicon (restored on leave), system font, GlobalCopyright hidden on /calendar.
- Global wrap rule changed to `overflow-wrap: break-word` (anywhere caused mid-word nav breaks on desktop); 200%/320px reflow re-verified.

### 2026-10-17 — Align silence warning (PREVIEW ONLY)
- `case_safety.silence_status()` (SILENCE_DAYS = 7): warns when no signed Align update (applied or ignored; refusals don't
  count) for 7+ days, or when none has ever arrived. Returned as `silence {threshold_days, days_since, warn}` in
  `GET /api/admin/safety-audit-log/align-status`. Panel shows gentle amber note `align-status-silence` (admin only, no email).
- Tests: test_align_silence_status_rule + align-status test assert silence (23/23 pass); UI checked at 390px for both the
  "N days" and "never" wording (mocked responses in screenshot).

### 2026-10-18 — Align test ping + "Check this side" (PREVIEW ONLY)
- Webhook accepts signed `{"test": true, "test_id", "timestamp"}` bodies: same signature/5-min/replay checks, recorded in
  `safety_webhook_tests` (TTL 35 d), audit action `test_received`, never touches a case or the update counts.
- `align_ping.py`: `POST /api/admin/safety-audit-log/self-test` (signs a test and posts it to PUBLIC_BACKEND_URL webhook),
  `POST .../align-ping` (POSTs `{test_id, timestamp, callback_url}` signed `X-SACO-Signature` to `ALIGN_PING_URL`, https only,
  15 s cooldown; `{"configured": false}` while unset), `GET .../test-status/{test_id}` (poll). align-status adds `last_test`.
- UI: `AlignTestButtons.jsx` in the Align panel ("Check this side", "Ask Align for a test", 30 s wait) + "Last link test" row.
- Spec for the Align builder: /app/memory/ALIGN_TEST_PING_SPEC.md. New env key `ALIGN_PING_URL` (empty until Align is ready).
- Tests: 48/48 (test_safety_gate.py incl. simulated-Align round trip, + external files). UI checked at 390px.

### 2026-10-18 — Webhook timestamp tolerance (PREVIEW ONLY)
- `_fresh()` now accepts Unix seconds or milliseconds (number or quoted digits) and ISO dates with timezone; 5-min window unchanged.
  Header (`X-Align-Signature`, optional `sha256=`), raw-body hashing and hex digests unchanged. Test added (27/27 pass).

### 2026-10-18 — Signature help on Align panel (PREVIEW ONLY)
- `SignatureHelp.jsx` (admin panel only): folded "How Align must sign updates" box (address, X-Align-Signature, hex HMAC-SHA256
  of raw body with optional sha256=, key name ALIGN_WEBHOOK_SECRET — never its value, timestamp rules) + "Copy for Align's
  builder"; opens automatically when wrong-signature refusals exist. "Too old" hint shown when old_timestamp refusals exist.
  Daily table made compact on phones. Verified by screenshot at 390px (copy text checked, no secret value).

### 2026-10-18 — ALIGN_WEBHOOK_SECRET burned and removed (PREVIEW ONLY, no deploy)
- Value was pasted in chat by mistake. Removed the key from backend/.env (left UNSET, no replacement generated), redacted the
  one copy in a local tool-output cache, restarted backend. Scan of /app (incl. git history), /var/log, /tmp, /etc, /root,
  /home and process environments: 0 occurrences (value never printed).
- Webhook is OFF while unset: POST /api/internal/safety-status → 503, records reject reason `webhook_off`, changes nothing.
  align-status returns `webhook_on: false`; admin panel shows a red "webhook is off" note. self-test → not_configured,
  align-ping → configured:false.
- Tests: signing suites skip when the secret is unset; new tests/test_webhook_off.py (2/2 pass).
- User must remove it from the Emergent Secrets tab themselves if it was ever added there (agent can't edit Secrets).

### 2026-10-19 — Secret paste guard + Align link health dot (PREVIEW ONLY; webhook still OFF, secret unset)
- `SecretPasteGuard.jsx` (PASTE_GUARD_TEXT) at top of /admin/audit-log and inside "How Align must sign updates" + its copied text.
- `GET /api/admin/safety-audit-log/link-health` (admin, no-store, not audit-logged): ok = webhook on AND signed update/test in
  last 7 days AND no refusals in last 24 h. `lib/useAlignLinkHealth.js` (60 s shared cache) + `LinkHealthDot.jsx` (green/amber,
  sr-only + title "Align link OK" / "Align link needs attention") on the AppShell "Admin" nav item (desktop + mobile) and a new
  "Updates from Align →" link on /admin. Tests: tests/test_webhook_off.py 3/3. Screens checked desktop + 390px.
- New secret: waiting for the user to add it (Keeper → both Secrets tabs, preview via backend/.env in the code editor) and say
  "secret set"; then check presence by length only, confirm webhook_on, re-run Safety Gate suites.

### 2026-10-19 — Fresh ALIGN_WEBHOOK_SECRET generated, webhook back ON, full Safety Gate re-run (PREVIEW ONLY, no deploy)
- At the user's request ("generate it"): a 64-hex random value was written into preview backend/.env only, never printed.
  Scan: 0 copies outside backend/.env (/app, /var/log, /tmp), 0 git commits. backend/.env is untracked by git.
  The user must copy it from the code editor into Keeper and Align's Secrets tab (and this app's Secrets tab before any future deploy).
- Bug fixed: case_safety.apply_update auto_red lock. From restricted/auto_red, only set_by=professional or an auto_red re-send that
  stays restricted can write. auto_red + standard/structured is now ignored ("locked"); before this fix it lifted the restriction.
- Outdated assertions updated in tests/test_align_status_external.py (webhook_on field, webhook_off reason).
- Tests: existing suites 60 passed / 1 expected skip (test_webhook_off). Testing agent iteration_144: 20/20 new live tests
  (tests/test_safety_gate_iter144_full.py) with two parents linked through the real professional-case + manual-code flow,
  plus frontend 100% (identical neutral banner for both parents, admin panel ON, Check this side OK, paste guard, 390px no overflow).
- Still pending: ALIGN_PING_URL (Align side not ready), a real cross-app test once Align has the secret, and native privacy-screen checks.
- Optional ideas from testing: return applied/ignored in the webhook response; drop the legacy safety_assessment router include.

### 2026-10-19 — Family check-in replaces A/B/C (option a) (PREVIEW ONLY, no deploy)
- User picked option (a): one neutral "Family check-in" card replaces the A/B/C reflection modules (Child Needs & Priorities,
  Co-Parenting Dynamics, Conflict Readiness). Hidden only: saved notes stay stored.
- `components/caseSettings/FamilyCheckinCard.jsx`: top of Court Ordered (court-family-checkin) and Self Journey
  (self-family-checkin, `stacked`). Opens REACT_APP_ALIGN_SITE_URL (sacoparentsalign.online) in a new tab. Status "Done" /
  "Not finished yet" from GET /api/case-settings `setup_complete` (= case screening_offered; identical for both parents in a case;
  a parent in several cases sees Done only when all are set up). The app never asks or saves check-in answers.
- Court checklist (JSON + PDF): Module A/B/C rows → one `family_checkin` row; `modules` no longer sent or read
  (court_checklist.py, court_path_ai.py, useCourtChecklist.js). Court AI prompt mentions the Family check-in, not modules.
  guided_draft_nudge: no nudges for the hidden foundation/safety guided topics. CourtModulesCard removed.
- SAFETY_STATUS_WEBHOOK is an Align-app setting (user checks Align Deploy → Secrets); nothing in this app uses it.
- Tests: iteration_145 backend 11/11 (tests/test_family_checkin_iter145.py) + UI 100%; Safety Gate suites 80 passed; checklist
  tests updated. 3 framing tests fail with 428 (AI notice), unrelated and already failing before this change.

### 2026-10-19 — Check-in direct link, one-time thanks note, Align links → .com (PREVIEW ONLY, no deploy)
- Probed from the pod: sacoparentsalign.online has NO DNS (all .online Align links were dead). sacoparentsalign.com is live
  (/api/health healthy, build 2026-09-26.1). Align's test-ping endpoint /api/internal/parents-test-ping returns 404 (not built yet).
- User chose .com for all Align links: frontend/.env REACT_APP_ALIGN_HOSTNAME / REACT_APP_ALIGN_URL → .com, new
  REACT_APP_ALIGN_SITE_URL=https://sacoparentsalign.com and
  REACT_APP_ALIGN_CHECKIN_URL=https://sacoparentsalign.com/joint/{case_id}/safety-screening (user explicitly accepted the case
  number and the path words in the address). JourneyShell fallback + Align.jsx text → .com.
- GET /api/family-checkin/link → {case_id} only when the parent is in exactly one case (else null → main Align site); no-store.
  lib/useCheckinLink.js fills {case_id} (validated ^SA-[A-Z0-9]{4,10}$).
- One-time note "Thanks, your check-in is done. There's nothing else you need to do for it." inside the card, per parent account:
  GET /api/family-checkin/thanks {show}, POST /api/family-checkin/thanks/seen (collection family_checkin_thanks {user_id, seen_at},
  covered by the generic account purge). lib/useCheckinThanks.js marks seen when shown; close button 44x44.
- ALIGN_PING_URL still unset: the user sent https://sacoparentsalign.com/api/health, but that is a status check and cannot do the
  signed round trip. Waiting on Align's builder for the spec endpoint.
- Heads-up (pre-existing): DomainGuard sends /admin and /align on the production parent host (sacoparentsapp.online) to
  REACT_APP_ALIGN_URL, so this app's admin pages (Updates from Align, audit log) can't be reached on that host as configured.
- Tests: iteration_146 backend 10/10 + UI 100% (desktop + 390px); Safety Gate suite incl. 3 new check-in tests passing.

### 2026-10-19 — Check-in reminder + /admin reachable on the parent host (PREVIEW ONLY, no deploy)
- Reminder in the Family check-in card: "Your Family check-in is still open. It only takes a few minutes, whenever you're ready."
  Shown when not done and 7+ days since the case was linked (case_safety.linked_at_for: latest parent accepted_at, else case
  created_at, so the same date for both parents). Closing it hides it for 7 days per account (collection family_checkin_reminder
  {user_id, dismissed_at}). GET /api/family-checkin/reminder, POST /api/family-checkin/reminder/dismiss (no-store, auth).
  No email/SMS/push. Notes live in components/caseSettings/FamilyCheckinNotes.jsx; hook lib/useCheckinReminder.js.
- App.js: /admin no longer wrapped in DomainGuard, so this app's admin pages open on sacoparentsapp.online (still admin-gated by the
  backend 403). /align still redirects to the real Align site.
- Still waiting on Align's builder: test-ping endpoint (POST /api/internal/parents-test-ping on sacoparentsalign.com returns 404
  as of 2026-10-19) and an optional neutral check-in page. Both are a one-setting change (ALIGN_PING_URL /
  REACT_APP_ALIGN_CHECKIN_URL).
- Tests: iteration_147 backend 10/10 + UI 100%; test_safety_gate.py incl. week-rule test; 72 passed across check-in/Safety Gate suites.

### 2026-10-19 — "Finished on" date + per-parent align_ref check-in link (PREVIEW ONLY, no deploy, webhook/secrets untouched)
- Finished-on date: case_safety doc gets plain `setup_completed_at` (set when an applied update turns screening_offered true,
  kept while true, cleared when reopened, newer date on re-complete; legacy done cases have none → just "Done").
  /api/case-settings adds `setup_completed_on` (UTC YYYY-MM-DD, case-level, identical for both parents). Card shows
  "Finished on October 19, 2026" under Done. User has NOT yet confirmed keep/remove (asked 2026-10-19).
- align_ref (user instruction): str(uuid.uuid4()) generated once, never changed. Stored on users docs (all 5 creation paths +
  seed; unique sparse index) AND on each joint_alignment_cases.parents[] entry (both creation paths + seed keeps per-slot value).
  backend/align_ref.py backfill_align_refs runs at startup (background task + error-logging callback): 6,429 accounts and 2,036
  case parent entries filled. GET /api/family-checkin/link → {align_ref} (account value) when linked to ≥1 case, else null;
  generates once if an account somehow lacks it. Never exposed elsewhere (auth/me, case-settings, admin, export all allow-lists).
- REACT_APP_ALIGN_CHECKIN_URL=https://sacoparentsalign.com/joint/{align_ref}/safety-screening; useCheckinLink validates uuid4 and
  keeps the button disabled until the lookup finishes.
- IMPORTANT: Align must know each parent's align_ref for the link to resolve; this app does not send it anywhere (webhook paused
  per user, no push). Case-entry align_refs are stored but unused.
- Open question to user: preview ALIGN_WEBHOOK_SECRET is still set (from "generate it"); user said the webhook "stays paused" —
  awaiting their decision whether to remove it from preview. Not changed.
- Tests: iteration_148 backend 10/10 (tests/test_align_ref_iter148.py) + UI 100%; 75 passed across Safety Gate / check-in suites.

### 2026-10-19 — Preview webhook PAUSED (PREVIEW ONLY, no deploy)
- User asked to pause: ALIGN_WEBHOOK_SECRET line removed from preview backend/.env (only that line; 46 other keys intact,
  SAFETY_ENC_KEY untouched), backend restarted. Verified: POST /api/internal/safety-status → 503 "Unavailable.", admin
  align-status webhook_on=false, self-test {"ok":false,"reason":"not_configured"}, secret absent from running backend env,
  tests/test_webhook_off.py 3 passed. Do NOT set/generate a new secret until the user says so.
- "Finished on" date kept (user replied "recommended").
- Still waiting on Align's builder + user approval: test address for the two-app test, and a neutral check-in page.
  Per user, the only Align endpoint we may call is GET https://sacoparentsalign.com/api/health (connectivity only).

### 2026-10-19 — Pre-deploy review answers; align_ref backfill made admin-run (PREVIEW ONLY, no deploy)
- Confirmed again: ALIGN_WEBHOOK_SECRET absent from preview backend/.env and running backend; webhook 503. Not regenerated.
- align_ref backfill NO LONGER runs at startup (server.py hook removed) and the link lookup no longer generates a missing one.
  Admin-only: GET /api/admin/align-refs (missing counts), POST /api/admin/align-refs/backfill (idempotent, never overwrites;
  creates the unique sparse users.align_ref index). UI: ParentIdsCard on /admin/audit-log with backup instructions
  (Republish → Database → Go to database → Dump DB), "I've taken a database backup" tick required, then "Add parent IDs".
  New accounts / new case entries still get align_ref at creation. On deploy, live data is NOT written by this app's startup
  except: case-safety indexes and the Get Help services seed (only if that collection is empty) — no parent records.
- CORRECTION: the old safety-assessment routes were ALREADY removed in an earlier session (safety_assessment_routes.py last line
  keeps only /problem-solving routes → everything else 404). The earlier "still saves" report was wrong; no change was needed.
  New test tests/test_parent_ids_and_retired_assessment.py (runs with webhook off). Legacy safety-assessment test files skipped.
- Leftover parent-facing wording found (not changed, awaiting user): /situation card "A private safety screen — …"
  (pages/Situation.jsx:81); footer note "Safety Screen data is never shared automatically" (DeepDiveCompareHub.jsx:261,
  SpecialNeedsV2Compare.jsx:272); dead safety-block banners (never trigger: backend _latest_safety_level returns None).
- Platform (support agent): normal redeploys don't change the DB; automated backups hourly/daily 7 days + 7-day PITR (restore via
  support); no automatic pre-deploy backup — manual Dump DB.
- Demo parents for screenshots: demo.checkin.a/b@example.com (case SA-DEMOCK), see test_credentials.md.
\n
### 2026-10-19 — Neutral wording (picker + comparison notes), new preview webhook secret (PREVIEW ONLY, no deploy)
- /situation: "Safety / Family Violence" card → neutral "Get Help" card ("Local services and crisis lines, any time.", /help,
  LifeBuoy icon, testid situation-topic-help).
- Comparison screens (DeepDiveCompareHub/View, SpecialNeedsV2Compare/View): dead "Comparison is paused for your safety… Review
  Safety Screen" banners + safetyBlocked state removed; footer now "This tool is neutral: neither parent is labeled as correct.
  Either parent can revoke at any time."
- Checked list of the rest: memory/SAFETY_WORDING_LIST.md (scan script memory/safety_wording_scan.py). Awaiting user decisions.
- User asked "please generate a new align webhook secret": new 64-hex ALIGN_WEBHOOK_SECRET written to preview backend/.env only
  (never printed; 0 copies elsewhere, 0 git commits). Webhook ON in preview, self-test OK (201 ms), unsigned POST 401.
  96 tests passed across Safety Gate / check-in / align_ref suites. User must copy it into Passwords + Align's Secrets tab
  (replaces the earlier value). Two-app test still NOT run (needs Align's test address + user "go").

## 2026-10-19 — Safety Gate correction + check-in link (PREVIEW ONLY, nothing deployed, no secrets touched)
- auto_red removed: Align `set_by=auto_red` refused + logged (`auto_red_refused`); unnamed professional refused (`no_professional_name`).
  Only a signed update with `set_by=professional` + name sets/lifts a limit; audit `write` row = actor_type `professional`, actor_id = name.
  Non-professional updates keep existing limits and change only the check-in status. New cases default `standard`.
  Older auto_red restrictions stay until a professional changes them. Webhook still OFF (ALIGN_WEBHOOK_SECRET unset).
- Admin-only `GET /api/admin/safety-audit-log/auto-restricted` -> `{count}`; card on /admin/audit-log "Cases restricted automatically: N". Preview: 1.
- Legacy Safety Assessment restored to its pre-10-16 behavior (routes, /safety-assessment, /safety CTA, portal SafetyScreen, grey-rock from flag,
  advocate review log, invite gating, comparison blocking, PDFs), keeping later a11y fixes.
  Kept on purpose: neutral picker/comparison wording, Get help page/nav, A/B/C hidden (so Module C "Conflict Readiness" entry stays hidden).
- Safety Gate hidden from families: /case-settings + /plan-options -> '/', no CaseHomeNotices / View options / CaseSettingsBanner. Enforcement unchanged.
- Family check-in link: `https://sacoparentsalign.com/check-in?case={case_id}` (shared SA- code, same for both parents; first unfinished case if several).
  Unlinked -> https://sacoparentsalign.com. align_ref no longer used in the link (data kept). `.online` Align comments fixed in code.
  Align confirmed: `.online` is not Align. Bridge field for the SA code is `case_id` (UUID is `report_id`).
- Tests: tests/test_safety_gate_correction.py (in-process, no secret), iter149 public suite; test_safety_gate.py updated (skips while webhook off).
- Next (user): step 4 — Professional Access Notice and "I'd rather not answer" option.

## 2026-10-19 — Step 4 (PREVIEW ONLY, not published)
- Professional Access Notice (Align wording v2026-10-19.1): full version replaces "What this professional will see" on JoinInvitation and CourtAcceptDialog, added to PreShareConsentDialog; hideable dashboard card; footer link → /who-can-see-my-information (Align "Who has looked" button appears when REACT_APP_ALIGN_ACCESS_LOG_URL with {case_id} is set — address pending from Align).
- Privacy Notice section 2 paragraph replaced; version 2026-10-19-v3 (all parents re-accept at next sign-in). Only sections 1, 2, 7, 12 exist (preview and live).
- "I'd rather not answer" (prefer_not) on every Safety Assessment question + quick Safety Screen. Full assessment: a skip never raises the level, except the SKIP_FLOOR list (danger / physical / sexual / child harm) → at least Level 2. Quick screen: skip = gentle support card (like "Not sure").
- Self Journey: "Safety Screen" link under the Family check-in card.
- Old vs new detail: memory/step4_old_vs_new.md. Tests: tests/test_step4_skip_scoring.py, tests/test_iter150_skip_answer_public.py.
- OPEN: older copy still says professionals never see answers (LegalAcknowledgment.jsx, LoginPrivacyBox.jsx, lib/proVisibility.js); notice promises this app doesn't deliver (view log, professional check-in on skip, reports without level).
- 2026-10-19 round 2: notice cut to the sentences true for this app (see step4_old_vs_new.md); Amber skip floor removed; skip = "Skipped", never flags (full + quick); Self Journey link "Quick check-in"; global footer link on every page; Privacy Notice v4. Untrue-for-this-app claims (professional access to answers, view log, court docs, professional check-in on skip) NOT built — awaiting user decision.

## 2026-10-20 — Align safety step replaces the old in-app Safety Assessment (PREVIEW ONLY, not published, no secrets)
- Q5 answer (from the 10-17 code, live not inspected): co-parent NO, public check page NO, share links NO. Exception: Safety
  Assessment PDFs emailed before 10-17 as "document waiting" links (recipient + one-time code, 7-day expiry) — now blocked in preview.
- Hidden from parents: /safety-assessment → /help, /next-steps/safety → /, all old assessment/screen API routes 404 (only /problem-solving kept),
  public court-report check API unmounted. Saved answers kept in DB + parent's own data export. Portal state never returns or writes
  safety_ack/safety_plan. Old safety share links not listed (/share/mine); old emailed safety PDFs (secure-docs) 404 + not listed.
- Egress: no lens/Finding 3/levels/flags in joint report (plumbing removed), Complete Report, court checklist, one-pager, readiness profile
  (prep.safety_assessment ignored), professional intro PDF, emails, AI prompts ("safety" coaching section removed). Docs carry only
  "Safety step: completed on SACOparentsAlign" / "Safety step: not started" (case_safety.safety_step_line; no "declined" exists).
- Kept internally: old level 1-2 / quick-check flag → invites + comparisons blocked with neutral NOT_AVAILABLE note + check-in link;
  reminders/nudges/weekly notes skipped; Align export held back with no flag. Grey-rock = parent toggle only.
- Notice (user-approved text): ProfessionalAccessNotice (WhoCanSee, PreShare, JoinInvitation, CourtAcceptDialog), short card,
  /privacy-notice §2 → PRIVACY_NOTICE_VERSION 2026-10-19-v6. "Who has looked" link OFF until Align gives the address (then linked parents only).
  /what-professionals-see (lib/proVisibility.js), /methodology §2, /accessibility no longer describe the old screen.
- Privacy Notice has only sections 1, 2, 7, 12 (never had 3-6, 8-11 in code history) — user will paste missing text; do NOT publish with gaps.
- Tests: tests/test_align_safety_step.py (23), tests/legacy_safety.py helper (old results written to Mongo), obsolete legacy tests
  deleted/replaced; iteration_152 (frontend 100%). Remaining suite failures are pre-existing (sign-in now required on guided/voice/BIFF
  routes, AI-notice 428, Resend 502 in preview, weekly-note html escape, daily-cap counters).

---
## 2026-10-20 — Part 3 privacy + Safety First banner (PREVIEW ONLY, not deployed)
- Safety-step wording is two states only: "Safety step: completed on SACOparentsAlign" (when Align confirms) or "Safety step: see SACOparentsAlign". "not started" is removed everywhere (case_safety.safety_step_text). The court checklist no longer lists the safety step under "What's left".
- Old-result hold (saved level 1-2) still blocks invites and comparisons with the neutral note only. A named professional's signed Align case settings (set_by=professional) lift it (safety_gate.is_blocked, now also used by the snc2 and deep-dive comparisons). set_by=default and auto_red can't lift it.
- Mediation Prep: the Issues safety box is replaced by the Family check-in card + Get help. New safety text is dropped; old saved text is kept and never shown, sent to AI or shared. Shared copies (share link, mediator email, joint agreement, Complete report) come from mediation_sharing.shared_view: no readiness, safety text, reflection or snapshots. Pre-update links return 410. Pre-update docs get an AI rewrite made without the sensitive inputs, or only goals + priorities. Pre-update secure-doc PDFs return 410. Align no longer gets reflection or readiness.
- Privacy Notice v7: sections 1-4, new safety-step wording. The REACT_APP_ALIGN_ACCESS_LOG_URL placeholder is empty, so the link stays hidden.
- Safety First banner (components/caseSettings/SafetyFirstBanner.jsx) sits on the parent home above the Court Ordered / Self Journey doors. It has an Open Family check-in link (case link, or the Align root), Quick exit, and the 911 + DV Hotline numbers. Once Align confirms the check-in, it becomes "Safety step: completed".
- Tests: the 27 old failures in the 50-file group are fixed (outdated tests updated; tests/ai_ready.py signs in and accepts the notices). tests/test_part3_privacy.py has 15 tests. Testing agent iteration_153: all pass.
- Open: 21 old failures in the second test group (same cause: AI tests don't sign in or accept the AI notice). Align has not yet answered the "Who has looked" URL question or the reflection/readiness deletion question. The first share of an older summary is slow (15-20s) while the AI rewrite runs.

## 2026-10-20 — Full backend test suite clean (PREVIEW ONLY, nothing deployed, no secrets touched)
- Full suite: baseline 46 failed → final **0 failed, 2203 passed, 26 skipped** (each skip has a one-line reason). Per-failure list: memory/test_cleanup_ledger.md.
- Real fixes found by tests: (1) guided_draft_nudge.py now skips parents with an old safety result (is_safety_flagged), like every other reminder;
  (2) pdf_provenance.py no longer splits "How this report was built" across near-blank pages (Medical Deep Dive was 10 pages, now normal).
- Test setup: conftest test_user + fresh-user fixtures accept the Privacy + AI notice (tests/ai_ready.py); retired-feature tests rewritten to assert the new rules.
- "Preparing a private copy" toast verified in the browser on a slow first share (Summary → Share via text).
- Skipped on purpose: 8 webhook modules (ALIGN_WEBHOOK_SECRET left unset by user), 4 retired v1 questionnaire modules, 14 retired old-safety-screen tests.
- Open (user): Align replies to (a) "Who has looked" addresses (linked + general) and (b) reflection/readiness question did not come through — defaults kept
  (link hidden; reflection/readiness not sent). Privacy Notice sections 3–6 / 8–11 stay out until the user sends text.

## 2026-10-20 — Held-back reminder count + supervised webhook run (PREVIEW ONLY)
- New held_emails.py: each reminder held for safety (reassess, weekly note, requested-steps, professional nudge, comparison alert,
  unfinished-draft) is recorded once per email as {kind, at} under a keyed hash — no name, email, user id or case code.
- Admin-only GET /api/admin/safety-audit-log/held-emails → last 30 days, by type; 1–4 shows "fewer than 5". Card on /admin/audit-log
  (components/caseSettings/HeldEmailsCount.jsx, testids held-emails-card/-total/-list/-{kind}). Preview numbers include test runs.
- Webhook run: temporary secret in preview only, 8 webhook files → 84 passed / 0 failed after 9 outdated tests were updated; secret removed,
  webhook back OFF (503). Tests: tests/test_held_emails.py (7).

## 2026-10-20 — User's 5-item spec (PREVIEW ONLY; don't deploy until Align's notice 2026-10-19.2 is ready, ship together)
1. "Who has looked at my information" (WhoCanSee page): shown ONLY to parents linked to Align (GET /api/integrations/align-link linked).
   frontend/.env REACT_APP_ALIGN_ACCESS_LOG_URL=https://sacoparentsalign.com/who-can-see?case={case_id},
   REACT_APP_ALIGN_ACCESS_LOG_GENERAL_URL=https://sacoparentsalign.com/who-can-see. Pure logic lib/accessLogHref.js (+ jest test, 5 passed):
   valid SA- code -> ?case=, otherwise plain page, never empty ?case=. Unlinked/signed-out -> hidden.
2. Reflection answers never sent to Align: export-assessments no longer has a foundation_statement block at all; test deep-scans keys/values
   (tests/test_align_share.py::test_no_reflection_field_is_ever_sent). foundation-statement.pdf stays 409.
3. Communication readiness = Communication Style page's 3 choices + sample message (4 answers). New backend/align_share.py:
   GET/PUT /api/integrations/align-share/communication-readiness {share: bool} -> choice yes|no|null (collection align_share_choices).
   Export adds top-level communication_readiness {answers:[{question, answer}×4 plain words], answered_at (comm_style.saved_at)} ONLY when
   choice == yes, answers exist and no old safety hold; otherwise the key is absent. Asked once after saving Comm Style
   (components/commStyle/CommShareCard.jsx: yes / no / skip); changed later via switch on Account Align card (components/account/CommShareSwitch.jsx).
   Align read history label shows "…and Communication Style answers" when included. Copy no longer says Align reads the Foundation Statement.
4. Admin held-back reminder card (see earlier entry). 5. Supervised webhook run (see earlier entry).
- Open: PrivacyNoticeContent.jsx (hashed, v7) doesn't describe the optional Communication Style sharing — needs user's wording + version bump.

## 2026-10-21 — Notice v8, linked-only sharing, reset on unlink (PREVIEW ONLY, do not publish)
- PrivacyNoticeContent.jsx section 2: new paragraph (testid privacy-notice-align-sharing) "Sharing with SACOparentsAlign. …" (user-approved text).
  PRIVACY_NOTICE_VERSION = "2026-10-20-v8", hash c4668edf9f430a6bb5927131f637016bb6ceef85fb5a2209419490f17e0c7175 → every account re-accepts once.
- Communication Style sharing question (after save) and Account switch only for parents linked to Align; PUT choice → 409 when not linked.
- DELETE /api/integrations/align-link resets the sharing choice (align_share.reset_share_choice) → re-linking never silently restarts sharing.
- Small fixes: NextSteps page scrolls to top on arrival; unlinked Account card labels old history "Earlier reads, before you unlinked".
- Tests: tests/test_align_share.py now 10; testing agent iteration_155 passed (no retest).
- Release: wait for Align's notice 2026-10-19.2 confirmation; ship both together. Paste-ready note for Align was given to the user.

## 2026-10-21 — Clear page for blocked Summary/Agreement share links (PREVIEW ONLY; wait for user's "deploy")
- backend/shared_link_page.py: GET /api/mediation/shared/{token} opened in a browser (Accept text/html) now returns a branded HTML page
  (testids shared-link-blocked-page/-title/-message), no-store + noindex. Scripts still get JSON {"detail": msg} with the same status.
  Messages: made before a privacy update (410), expired (404), not valid (404), switched off by the parent (404), no longer available (404).
- Tests: tests/test_shared_link_page.py (11) + test_part3_privacy.py → 26 passed. Mobile screenshot OK, no overflow.
- Sample communication_readiness payload generated from the real export path (fake parent, cleaned up) and given to the user.
  SACOparents has no Align-side ids; our ids are q1/q2/q3/free_text_sample (answer codes in align_share.QUESTIONS).
- Align secure connection (ALIGN_WEBHOOK_SECRET): user will create it on Align and paste the same value into the live site's settings;
  agent then checks presence only (never the value). Still unset in preview.

## 2026-10-21 — Preview DB backup (no changes made; nothing deployed; no secrets deleted yet)
- mongodump of PREVIEW DB to /root/backups/preview_<DB>_<UTC>.archive.gz (path in /root/backups/LATEST; chmod 600; outside /app so never in git).
  Verified with mongorestore --dryRun: all 163 collections present. Restore: mongorestore --uri=$MONGO_URL --gzip --archive=<file> --drop (only on request).
- Production DB is separate: only the user can export it (Manage Publishes → Database → Dump DB).
- Pending user go-ahead: delete SACOPARENTSALIGN_WEBHOOK_SECRET + INTEGRATION_SHARED_SECRET, then deploy.

## 2026-10-21 — DEPLOYED to https://sacoparentsapp.online (user said "Deploy now")
- Before deploy: removed SACOPARENTSALIGN_WEBHOOK_SECRET from preview backend/.env only (invite-accept webhook now 503). INTEGRATION_SHARED_SECRET
  kept everywhere (Align needs it). User removes ALIGN_WEBHOOK_SECRET + SACOPARENTSALIGN_WEBHOOK_SECRET from production Secrets themselves.
- Live checks after deploy: notice version 2026-10-20-v8 live (brief Cloudflare 520 during switchover), home 200, /api/ 200,
  login UI → 401 "Invalid email or password" shown for a wrong password; parent1@test.com does NOT exist in production (prod DB separate).
  Family check-in card (signed out) opens https://sacoparentsalign.com in a new tab (Align 200).
- Not verified on live: a successful sign-in with a real account (no production test account). backend/.env PUBLIC_APP_URL/PUBLIC_API_URL
  point at the preview domain — confirm production overrides them to sacoparentsapp.online (affects links in emails).

## 2026-10-21 ~03:05 UTC — Re-publish after user's production Secrets edits
- User set PUBLIC_APP_URL/PUBLIC_BACKEND_URL/PUBLIC_API_URL = https://sacoparentsapp.online and deleted ALIGN_WEBHOOK_SECRET + SACOPARENTSALIGN_WEBHOOK_SECRET
  in production Secrets (their report), kept INTEGRATION_SHARED_SECRET. Re-deploy job 6f8f7a2c… ran; 520 blip at 02:59:56.
- After: home 200, notice v8, password-reset request 200, export-assessments w/o key 401 — BUT both webhooks still answer 401 (= secrets still
  loaded; 503 expected when absent). Debug question queued to the deploy agent (presence of the two secrets + PUBLIC_* values, RCA). Unresolved.
- Align (via user): still reads export-assessments OK; stopped sending both webhooks; final notice 2026-10-20.1 live.
- Deployer RCA (run a971d13d, live since 02:59:58 UTC): ALIGN_WEBHOOK_SECRET + SACOPARENTSALIGN_WEBHOOK_SECRET still PRESENT in the running
  production env, carried forward from the production Secrets store (not the codebase .env). User's deletion did not persist. INTEGRATION_SHARED_SECRET
  present; PUBLIC_APP_URL/PUBLIC_BACKEND_URL/PUBLIC_API_URL = https://sacoparentsapp.online (correct). Fix (user): delete both again, confirm
  gone from list, re-deploy → both webhooks should return 503. RCA file: /app/deployer-agent-docs/RCA_a971d13d-02c3-4c53-be64-6517dc5408e4.MD

## 2026-10-21 ~12:00 UTC — Start with Safety banner + Co-Parenting Builder card (PREVIEW ONLY, not published)
- User zip installed at frontend/src/components/startWithSafety/ (StartWithSafetyBanner.jsx/.css, CoparentingBuilderReferral.jsx/.css, photo).
- Journey landing (JourneyShell door view) order: Quick Exit (journey-quick-exit) → StartWithSafetyBanner → existing SafetyFirstBanner
  (Family check-in link / completed chip / hotline) → CoparentingBuilderReferral → Pick your path.
- Card is unconditional: same wording for every parent, never depends on answers, skips, concern level or check-in status.
- Clash fixes vs user's files: eyebrow "This step is complete" → "What's next", check icon → arrow (untrue for parents not checked in);
  button opens in SAME tab (new tab would survive Quick Exit). Wording otherwise unchanged.
- builderUrl = /dashboard?open=parallel-builder (live: https://sacoparentsapp.online/dashboard?open=parallel-builder) opens the
  Parallel Parenting Option Builder; new deep link added next to ?open=self-assessment. Card click opens builder in-place.
- Self-tested at 390px: Quick Exit above banner, no overflow, card click + address both open builder. Awaiting user's "deploy".
- Open question for user: card says "Co-Parenting Builder" but the page is titled "Parallel Parenting Option Builder".

## 2026-10-21 ~12:30 UTC — Name change + progress badge done; path work HELD for secrets-only re-publish
- Card renamed to "Parallel Parenting Option Builder" (heading: "build your parallel parenting plan"); badge "Builder: In progress/Done"
  from /api/parallel-parenting/me (useParallelStatus in selfJourney/useParallelDone.js). All 3 states checked at 390px.
- Path work (user.journey_path, PUT /api/auth/journey-path, PathPicker popup, Account "Your path") built + picker smoke-tested,
  then SET ASIDE so the user's re-publish ships only banner/card/name/badge. Held at /app/memory/held/path_work/ (README has restore cmd;
  `git apply --check` OK). Restore after user says re-published.
- User-approved dashboard tags: check-in "You, your professional + a few admins"; Self-Assessment "Only you see your answers";
  Communication Builder "Only you, unless you share it"; Order step = Co-Parenting Agreement "Shared only if you both agree"
  (must link to Parallel Parenting Option Builder); Court checklist "You + your professional".
- ParentDashboard.jsx/.css + photo NOT received yet (4 attempts). Dashboard not started; start only after the re-publish.
- Test account created in preview: badgecheck+1792585401@test.com / TestPass123! (in-progress parallel plan, path self_journey).
