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

## Prioritized Backlog

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
