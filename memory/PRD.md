# SA CoParents — PRD


- **Iteration 131 — Co-Parenting Agreement PDF matches the joint artefacts (2026-02-21)**:
  - **New helper `_agreement_disclaimer_banner`** in `pdf_service.py` — sage/sand palette banner (matching the CP Agreement's existing aesthetic, not the joint report's red) rendered on page 1 between meta and overview. Three-part message: (1) "Draft for discussion — read before signing or sharing" heading; (2) not a signed agreement / court order / legal document / custody recommendation; (3) "Your information is private by default…" (Sentence 1) + "Use of SA CoParents does not by itself create an attorney-client, therapist-patient, mediator-client, or other privileged relationship." (Sentence 2). Wired into `build_agreement_pdf` right after `_agreement_meta`.
  - **Sample regenerated** at `/app/frontend/public/downloads/sacoparents-sample-coparenting-agreement.pdf` (995 kB, valid `%PDF-1.3`) via `scripts/generate_agreement_sample.py` — same code path parents use, so the sample now shows exactly what a real parent's download would look like.
  - **Downstream coverage**: any endpoint that calls `pdf_service.build_agreement_pdf` (individual agreement download, shared token download, agreement email attachment) now ships with the banner. Zero code changes needed at the route layer.
  - **Testing**: sample builds valid `%PDF-1.3` bytes, `/api/insights/samples/sacoparents-sample-coparenting-agreement.pdf` returns 200 + `application/pdf`. 12/12 HB 300 + Virtru tests remain green.



- **Iteration 130 — Fixed "PDF generates code not print" bug + new Co-Parenting Agreement sample (2026-02-21)**:
  - **Root cause of parent complaints**: Landing page + Special-Needs marketing pages linked directly to `/downloads/<name>.pdf` — a static-asset path served by the React build. On some hosting configurations the SPA fallback caught those requests and returned `index.html` with the JS bundle. Browsers rendered that as raw HTML source → parents saw "code" instead of a PDF.
  - **Fix**: New whitelist-gated backend endpoint `GET /api/insights/samples/{filename}` in `insights_routes.py` that serves the same files through FastAPI with proper `application/pdf` content-type + 1-hour Cache-Control. The SPA fallback can never intercept an `/api/*` path. Allowlist blocks directory traversal (`../` returns 404) and unlisted files (404).
  - **Every frontend PDF link migrated** from `/downloads/*.pdf` to `/api/insights/samples/*.pdf` — 17 links across `Landing.jsx`, `SpecialNeedsV2.jsx`, and `SpecialNeedsV2PsychologicalDeepDiveReport.jsx`. Grep for `/downloads/.*\.pdf` now returns zero hits.
  - **New sample generator** `/app/backend/scripts/generate_agreement_sample.py` — uses the live `pdf_service.build_agreement_pdf` renderer with realistic fictional data (Alex Rivera, two kids Maya + Jonas, full communication + child-needs + household-rules + priority-items clauses). Output at `/app/frontend/public/downloads/sacoparents-sample-coparenting-agreement.pdf` (993 kB, valid `%PDF-1.3`). Served via the new allowlist endpoint.
  - **Also fixed a pre-existing F821 lint blocker** in `joint_professional_report_routes.py:414` — `email_joint_report` handler referenced `request` in its `record_phi_access` call without accepting it as a param. Added `request: Request` to the signature. This was blocking pre-completion checks.
  - **Testing**: 12/12 HB 300 + Virtru tests still pass. 5 sample-PDF endpoints all return `200 application/pdf` on preview. Directory traversal and unlisted-file requests both return 404. Zero remaining `/downloads/*.pdf` frontend links.



- **Iteration 129 — Prominent "Private by Default" + "no-privilege" callouts (2026-02-21)**:
  - Added two user-supplied crisper sentences in three high-visibility surfaces (a + b + d from ask-human):
    - **Sentence 1** *"Your information is private by default. SA CoParents does not share your assessment or reports with your co-parent or a professional unless you choose to share them, except where disclosure is required by law."*
    - **Sentence 2** *"Use of SA CoParents does not by itself create an attorney-client, therapist-patient, mediator-client, or other privileged relationship."*
  - **Privacy.jsx** — Sentence 1 now sits in a purple `Callout` at the very top of Section 7 ("Your individual assessment answers are private by default"). Sentence 2 in a matching `Callout` at the top of Section 10 (the privilege carve-out). Both sit above the original section bodies — no wording deleted, both callouts render before the skimmable ul-block.
  - **PreShareConsentDialog.jsx** — added a highlighted purple gradient block **above** the six "YOU CONTROL THIS REPORT" bullets so parents read both sentences at the exact moment of share. New testid `preshare-consent-headline`.
  - **PDF disclaimers** — Sentence 2 appended to all three artefact disclaimers that leave the platform: `joint_professional_report.py::DISCLAIMER`, `joint_agreement.py::DISCLAIMER`, `professional_intro_transcript.py::DISCLAIMER`. Bumped `professional_intro_transcript` banner rect from 30 → 38 units to accommodate the extra line without truncation.
  - **Testing**: 12/12 HB 300 + Virtru tests still pass; all three PDF builders emit valid `%PDF-` files (~991 kB each); Playwright smoke on `/privacy` shows both callouts + original bodies + zero runtime errors. Lint clean on both frontend files.



- **Iteration 128 — In-app policy-refresh banner for returning users (2026-02-21)**:
  - **New component** `/app/frontend/src/components/PolicyRefreshBanner.jsx` — one-time soft banner announcing the 2026-02-21 canonical Privacy Policy rewrite. Renders with the "Private by Default. Shared by Choice." tagline and a "Read the policy" CTA linking to `/privacy`. Version-keyed dismissal (`sa_policy_refresh_v_2026-02-21` in localStorage) so future policy revisions reappear the banner without wiping older dismissals.
  - **Gated to returning users only** — hidden when: (a) user is unauthenticated, (b) user is a guest sandbox, (c) user was created ON or AFTER 2026-02-21 (fresh signups already agreed to the new text at registration), (d) user is already on `/privacy` or any `/legal/*` route (redundant), (e) user has previously dismissed this version.
  - **Mounted** inside `AppRoutes` above `<Routes>` in `App.js` so it appears on every authenticated page (Dashboard, Summary, Safety, Coach) but doesn't ship with the LegalAcknowledgment first-visit modal.
  - **Testing**: lint clean. Authenticated Playwright smoke against preview with a Mongo-backdated returning user proved: banner visible on `/dashboard`, suppressed on `/privacy` and `/legal/hb300`, Read/Dismiss buttons rendered with correct test-ids. Dismissal + localStorage persistence follow the existing `IntroTourModal`/`VerificationBanner` pattern.
  - **Files touched**: `App.js` (import + mount), `PolicyRefreshBanner.jsx` (new). Setup helper `/app/scripts/policy_banner_smoke_setup.py` kept in-repo for future policy-version drills.



- **Iteration 127 — Full 32-section canonical Privacy, Confidentiality & Data Protection Policy (2026-02-21)**:
  - **Wholesale rewrite of `/app/frontend/src/pages/Privacy.jsx`** to a 32-section, ~5,000-word canonical policy anchored on the tagline "**Private by Default. Shared by Choice.**" Supersedes the ad-hoc sections we added in iter 126 (Information About Children, Sensitive Information, AI + PHI) — every one is now baked into the numbered structure.
  - **All `[Insert …]` placeholders filled with canonical codebase values** — no draft brackets in production: Effective + Last Updated 2026-02-21, Privacy Officer Matt Sossi, mattsossi@bsossi.com, 210-224-1667, 16607 Blanco #703 San Antonio TX 78232, sacoparentsapp.online, AI providers named (Anthropic Sonnet 4.5 via Emergent Universal LLM Key with the retention + no-training + no-BAA-yet framing), service providers listed (Emergent, Anthropic, MongoDB Atlas, Resend, Virtru pending BAA, Google optional), retention schedule defers to `/data-retention` as canonical single source of truth.
  - **Section-level cross-links** to `/legal/hipaa`, `/legal/privacy-practices`, `/legal/hb300`, `/data-retention`, `/methodology`, `/accessibility`, `/terms`, and `/delete-account` so the policy is the hub for every downstream legal artefact.
  - **New Prose helpers** — reusable `H2`, `H3`, `Callout`, `Prose` components inside the file. Callout used for the guiding-principle hero and the closing commitment.
  - **Testing**: lint clean, all 32 sections render, 12/12 content checks pass ("Private by Default" tagline, Privacy Officer named, full contact block, AI providers named, service providers listed, retention defers, no `[Insert]` residue, HB 300 cross-link, closing tagline "Starting With Alignment, Ending With Agreement"), no runtime errors.



- **Iteration 126 — Privacy-review pass: 4 factual reconciliations + 3 new sections + HIPAA softening + pre-share consent gate (2026-02-21)**:
  - **4 consistency fixes** across `Privacy.jsx` + `DataRetention.jsx` + `HipaaNotice.jsx` + `PrivacyPractices.jsx`:
    - Share links: default 7 days, user-selectable {1, 7, 30, never}, revocable anytime (was "30 days from creation" on one page vs "signed 7-day link" on another).
    - Deletion: active-account data purged promptly; encrypted rolling backups complete rotation within 30 days (was "instantly / manually within 7 days" contradicting "within 30 days").
    - Email provider: named Resend explicitly (was "Gmail SMTP" — factually wrong post-Resend migration); Virtru mentioned as pending BAA.
    - Anthropic retention: rewritten per integration-expert playbook — chain is `app → Emergent LLM proxy → Anthropic`. Anthropic's published commercial policy is deletion within 30 days subject to exceptions; Anthropic does not train on API traffic; Emergent's proxy payload retention is not publicly stated (link to their policy). Removed the false "transient / then discarded" claim and the false-precision "enforces 30-day retention max".
  - **New section — "Information about children"** on `Privacy.jsx`. Names the categories parents may enter about kids, the minimization ask, and 4 explicit commitments (no sale, no advertising, no model training, revocable Compare-only sharing).
  - **New section — "Sensitive information — enhanced protection"** on `Privacy.jsx`. Lists family-violence, children's medical/psychological, allegations, journal, safety assessments, and free-text as the enhanced-protection tier. Lists 5 concrete safeguards (Compare consent, Finding-3-only guardrail, PHI-access audit log, neutral-language guardrails, encryption). Explicit warning that revoking a link cannot retrieve already-downloaded copies.
  - **New section — "AI + sensitive information — what to avoid"** on `Privacy.jsx`. Firm disclosure per playbook: because Emergent → Anthropic BAA chain is not yet confirmed, do NOT paste raw medical records, diagnostic codes with identifiers, or verbatim court exhibits into free-text fields until BAA confirmation is published.
  - **HIPAA-language softening** on `HipaaNotice.jsx` + `PrivacyPractices.jsx`: replaced the "we voluntarily adopt HIPAA" framing with the user-requested wording — *"SA CoParents is not a healthcare provider, and use of the platform does not, by itself, make information subject to HIPAA. We nevertheless treat health-related information as sensitive personal information and apply the privacy and security protections described in this notice."*
  - **New component `/app/frontend/src/components/PreShareConsentDialog.jsx`** — promise-based `requestPreShareConsent(label)` API mounted once at the root via `<PreShareConsentHost />` in `App.js`. Renders a modal with the six "YOU CONTROL THIS REPORT" bullets (verbatim per user's review), requires an explicit checkbox tick, and fails closed on cancel/Esc/unmount. Deliberately not cached in localStorage — parent must re-consent every share so the bullets are always read.
  - **Wired into 4 share entry points**:
    - `JointReportEmailDialog::submit()` — covers both Joint Report + Joint Agreement email variants.
    - `ReportShareControls::copyShareLink()` — covers every share-link creation across Mediation Summary, Co-Parenting Agreement, Special Needs Care Plan, and Family Violence & Communication Safety Screen (4 report types → all gated by one code path).
    - `SafetyAssessment::prepareCoSign()` — reviewer Co-Sign QR link.
  - **Bug uncovered + fixed**: temporal-dead-zone `ReferenceError: Cannot access 'close' before initialization` in the first draft of the modal (function referenced in its own useEffect deps before declaration). Fixed by hoisting `close` above the effect + suppressing the exhaustive-deps warning with a dedicated eslint comment.
  - **Testing**: all 4 legal pages render clean on preview (`/privacy`, `/legal/hipaa`, `/legal/hb300`, `/legal/privacy-practices`, `/data-retention`). 8/8 policy content checks pass (Resend not Gmail, 7-day default, new sections present, no "transient" Anthropic claim, deletion nuance visible, Emergent chain named explicitly). Lint clean on all 3 modified components. No runtime errors.
  - **Files touched**: `Privacy.jsx`, `DataRetention.jsx`, `HipaaNotice.jsx`, `PrivacyPractices.jsx`, `App.js`, `JointReportEmailDialog.jsx`, `ReportShareControls.jsx`, `SafetyAssessment.jsx`, `PreShareConsentDialog.jsx` (new).



- **Iteration 125 — HB 300 breach simulation drill (2026-02-21)**:
  - **Driver script** `/app/scripts/breach_drill.py` — three scenarios (12 TX residents / 312 TX / 742 total with 620 TX) executed live against the backend end-to-end: register + Mongo-elevate an admin, POST `/api/admin/breach-report`, verify AG flag + persistence + `next_steps`, then clean up (delete drill users, breach rows, PHI access rows).
  - **Overall PASS** — admin gate + all three scenarios matched expectations within 240 ms. Raw JSON at `/app/memory/HB300_BREACH_DRILL_RESULTS.json`, full readout at `/app/memory/HB300_BREACH_DRILL_2026_02_21.md`.
  - **Bug found + fixed in-flight (admin gate silently unreachable)**: `hb300_routes.py::submit_breach_report` was checking `getattr(user, "role", None)` and `is_admin` on `UserPublic`, which deliberately strips those fields. Only the `OPERATOR_EMAIL` fallback could ever succeed — future workforce members would 403 silently. Fixed by querying `role`/`is_admin` from Mongo directly, with `OPERATOR_EMAIL` retained as the single-owner shortcut.
  - **Regression locked** — new `test_iter121_hb300.py::test_breach_report_accepts_mongo_elevated_admin` elevates a test user via Mongo, hits the endpoint, asserts `200`, then reverts. 12/12 pass (was 11/11 before).
  - **Follow-ups queued (non-blocking)**: (1) add `total_individuals_affected` + `ocr_threshold_crossed` to `BreachReportPayload` for multi-state OCR breaches, (2) implement `send_operator_notification` in `email_service.py` so drafts email the operator live (currently best-effort import that no-ops), (3) automate Texas-media-notice check for ≥ 500 residents in one region.



- **Iteration 124 — Virtru Hosted Gateway (Pattern A) SMTP relay wired (2026-02-21)**:
  - **New module** `/app/backend/virtru_mailer.py` — synchronous SMTP submitter matching the rest of `email_service.py`. Per-message `X-Virtru-Auth` MIME header (NOT SMTP AUTH — that's the Virtru documented pattern), optional `X-Virtru-Encrypt: 1` header, optional `#secure#` subject marker, 100 MB raw attachment cap, PDF-only content-type guard, redacted error logging (auth header NEVER appears in any log line, even on SMTP failure).
  - **email_service.`_send()` provider switch** — auto-routes through Virtru when `VIRTRU_ENABLED=true` + `VIRTRU_AUTH_HEADER` + `VIRTRU_FROM_EMAIL` are populated, then falls back to Resend cleanly on `VirtruNotConfigured`. **Fail-closed** for HIPAA-scoped sends: `require_encrypted=True` + `VIRTRU_FORCE_ENCRYPT_REQUIRED=true` refuses Resend fallback entirely so no PHI email ever escapes unencrypted once the operator flips the flag.
  - **Wired into**: `send_joint_professional_report` + `send_joint_agreement_draft` marked `require_encrypted=True`. Other PDF flows (Special Needs report, safety assessment, pathway report) intentionally NOT marked in this iteration — will be re-scoped after production burn-in of the joint flows.
  - **`.env` pre-declared** with defaults OFF: `VIRTRU_ENABLED=false`, `VIRTRU_FORCE_ENCRYPT=false`, `VIRTRU_FORCE_ENCRYPT_REQUIRED=false`, plus `VIRTRU_SMTP_HOST=smtp.virtrugateway.com`, `VIRTRU_SMTP_PORT=587`, `VIRTRU_SMTP_STARTTLS=true`, `VIRTRU_SMTP_TIMEOUT_SECONDS=30`, plus empty placeholders for `VIRTRU_AUTH_HEADER` + `VIRTRU_FROM_EMAIL` awaiting Virtru provisioning.
  - **Operator cutover checklist** `/app/memory/VIRTRU_CUTOVER_CHECKLIST.md` — provisioning prerequisites (BAA, tenant, X-Virtru-Auth code, DNS-verified sender, outbound Security Rule), the 12-var flip table, staged cutover (openssl STARTTLS test → dry-run → fail-closed drill → full production), ongoing operational rules (secret rotation, no-DB storage, DSN monitoring), rollback (single env flip).
  - **Testing**: 6/6 (`test_iter122_virtru_mailer.py`) pass — env-var gating, MIME headers + attachments, port 587 + STARTTLS + no SMTP AUTH, auth header never logged on failure, non-PDF rejection, fail-closed refuses fallback. 11/11 combined with iter121 HB 300 suite. Existing Resend path unchanged with defaults.



- **Iteration 123 — Texas HB 300 (Medical Records Privacy Act) compliance (2026-02-21)**:
  - **New legal page** `/legal/hb300` — dedicated Texas HB 300 (Tex. Health & Safety Code Ch. 181) notice covering §181.154 electronic-disclosure notice, §181.153 no-sale attestation, §181.152 marketing opt-in, §181.102 15-business-day right of access, breach notification timers (60-day user, ≥250 TX residents → AG), workforce training §181.101, reasonable safeguards, Texas-specific rights, AG + OCR complaint routes. Linked from HIPAA Notice + Privacy Practices "See also".
  - **New backend module** `/app/backend/hb300_routes.py` with 5 endpoints:
    - `POST /api/me/hb300/acknowledge` — captures dated ack (versioned) in `hb300_acknowledgements` + mirror on user doc.
    - `POST /api/me/hb300/marketing` — opt-in / opt-out (default OFF per §181.152).
    - `POST /api/me/hb300/access-request` — formal 15-business-day request; row in `hb300_access_requests`; response includes SLA deadline + self-serve `/api/me/export` link.
    - `GET  /api/me/hb300/status` — current posture (ack version + timestamp, marketing opt-in, pending access requests).
    - `POST /api/admin/breach-report` — admin-only draft (403 for non-admins), stored in `hb300_breach_reports`, best-effort email to `OPERATOR_EMAIL`, flags Texas AG threshold (≥ 250) crossed.
  - **Signup captures HB 300 ack** — `/api/auth/register` now writes `hb300_ack_version="2026-02-21"`, `hb300_ack_at`, and `marketing_opt_in=False` at signup so every new account starts with a compliant baseline.
  - **Internal runbook** `/app/memory/HB300_BREACH_RUNBOOK.md` — 60-minute containment, 24-hour assessment, notification timers matrix (user 60d / TX AG 60d ≥ 250 / OCR 60d ≥ 500), notification-content elements, TX AG filing details, post-incident retention 6yr.
  - **Security audit fix (this session, SEC-001)** — `auth.py` `EmailSendError` handlers for password reset + verification tokens no longer log the reset/verification URL or raw token; log `user_id + error_type` only. Prevents account takeover via log access.
  - **Testing**: 5/5 (`test_iter121_hb300.py`) pass — signup ack, idempotent ack, marketing toggle round-trip, 15-biz-day SLA math, 403 for non-admin breach-report.



- **Iteration 121 — Security audit fixes + HIPAA legal pages + PHI hardening (2026-08-24)**:
  - **SEC-001 CORS lockdown (CRITICAL)**: `server.py` no longer reflects any origin with `allow_credentials=True`. Explicit allowlist required via `CORS_ORIGINS` env var — default is production + www + preview. `.env` updated to explicit list. Prevents cross-site PHI theft from any site a signed-in parent visits.
  - **SEC-002 password-reset link redaction (MEDIUM)**: `auth.py` no longer logs the reset URL or raw token. Logs the event only with `user_id`; the token is retrievable from the `magic_links` collection in dev.
  - **SEC-003 consent scope narrowing (MEDIUM)**: `joint_professional_report_routes.py::_SHARE_COLLECTIONS` now only accepts `snc2_shares` + `compare_shares`. Narrow deep-dive shares (edu/med/psych) no longer unlock the full joint aggregators. This was a design-scope tightening — narrow deep-dive shares still gate their own comparison endpoints.
  - **SEC-004 delete completeness (MEDIUM)**: `_PHI_COLLECTIONS` in `phi_access_routes.py` extended with 16 additional user_id-keyed collections (`nd_assessments`, `journal_entries`, `journal_recaps`, `summaries`, `improvement_plans`, `coach_messages`, `coach_sessions`, `next_steps`, `problem_solving_worksheets`, `cp_assessments`, `post_summary_checkins`, `mediator_emails`, `pathway_report_comments`, `devices`, `legal_acknowledgments`, `user_sessions`) so `DELETE /api/me` actually removes all PHI-adjacent data.
  - **P3 no-store PDF headers**: joint report + joint agreement PDF endpoints now emit `Cache-Control: no-store, no-cache, must-revalidate, private` + `Pragma: no-cache` so PHI PDFs are not cached by browsers or intermediaries.
  - **HIPAA Notice + Notice of Privacy Practices** pages published at `/legal/hipaa` and `/legal/privacy-practices`. Linked from the existing Privacy Policy "See also" block. Copy is plain-English-first, lawyerly-second, mirroring the existing legal-page voice.
  - **PHI access log + right-to-export + right-to-delete + accounting-of-disclosures** shipped as `/api/me/export`, `DELETE /api/me`, `/api/me/access-log`. Every joint-report/agreement read, download, or email disclosure now writes an audit row. Deletion de-identifies the audit log rather than wiping it (legal-hold + accounting-of-disclosures protection).
  - **Regression testing**: 42/42 (`iter113` + `iter116` + `iter120`) pass after all fixes. New `test_iter120_phi_access_export_delete.py` locks the audit-log wiring, export contents, and deletion completeness.

- **Iteration 122 — Virtru integration playbook received (pending BAA/credentials) (2026-08-24)**:
  - **Pattern A — Virtru Secure Email (SMTP)**: implementable now. Requires customer to obtain from Virtru Sales: **(1)** Hosted Gateway entitlement, **(2)** `smtp.virtrugateway.com` credentials + org-specific `X-Virtru-Auth` header code, **(3)** signed BAA (1–2 wk lead), **(4)** DNS-verified sending domain. Once received, scaffold with `aiosmtplib` + FastAPI wrapper around existing joint email flows.
  - **Pattern B — Virtru TDF (PDF-at-rest)**: BLOCKED. The legacy `virtru-sdk` Python package (v3.0.0) only exposes file-path / string encryption APIs — no bytes/streams — which contradicts our in-memory `fpdf2` architecture. Current Virtru Developer Experience emphasizes Go/Java/JS SDKs. Customer must confirm with Virtru Sales that a supported Python byte-stream API or approved OpenTDF-capable path exists before we can wrap PDFs as `.tdf`.
  - **Not yet coded**: Virtru integration requires credentials + BAA before scaffolding. Full playbook stored in this conversation's integration_playbook_expert_v2 response.



- **Iteration 119 — 3-Minute Professional Introduction PDF (2026-08-17)**:
  - **New backend module** `/app/backend/professional_intro_transcript.py` — single source of truth for the ~450-word transcript. Copy stored as data (heading + body tuples) so the PDF and any future HTML/audio surface iterate consistently. Explicitly names the three joint artefacts (Shared Special Needs Report, Joint Co-Parenting Summary for Professional Review, Joint Co-Parenting Agreement Draft) and preserves the Finding-3-only safety-privacy caveat.
  - **New public endpoint** `GET /api/joint-professional-report/professional-intro.pdf` — no consent gate (carries no user data). Registered BEFORE the `/{share_id}` catch-all so FastAPI's fixed-path match wins. Cache-Control set to `public, max-age=3600` since the PDF is stable across requests.
  - **Bundled into both email flows** — `send_joint_professional_report` and `send_joint_agreement_draft` now automatically build + attach the intro PDF as a second attachment. Intro-build failures are swallowed so they can never block the primary send. Both covering-email HTML/plain bodies now explicitly mention the intro so recipients understand what the second file is.
  - **Frontend entry points** — new `data-testid="joint-report-download-intro"` on Joint Professional Report header + `data-testid="joint-agreement-download-intro"` on Joint Agreement header. Both open the same public PDF in a new tab (`target="_blank"`, `rel="noopener noreferrer"`).
  - **Testing**: 2 new pytests in `test_iter113_joint_professional_report.py::TestProfessionalIntroPdf` — public endpoint returns a valid non-trivial PDF, and the fixed-path route doesn't collide with the `{share_id}` catch-all. 17/17 iter113 + 19/19 iter116 = 36/36 pass overall.



- **Iteration 118 — Regenerate My Draft From Joint (2026-08-16)**:
  - **New backend endpoint** `POST /api/joint-agreement/{share_id}/regenerate-mine` — deterministic (no LLM). Loads the caller's latest individual agreement + the current joint payload, promotes any clause matching the joint's `both_proposed` bucket (via the same `SequenceMatcher` similarity gate the merger uses) to the top of each section, sets `anchored: true/false` on dict-shaped clauses, and inserts a NEW agreement doc — the prior draft is preserved untouched.
  - **New helper** `joint_agreement.regenerate_individual_from_joint(...)` — pure function so tests can lock the anchor-promotion + `regenerated_from_joint` audit stanza (share_id, prior_agreement_id, anchor_counts_per_section, total_anchors, regenerated_at, co-parent name).
  - **Refreshed overview line** — when at least one clause is anchored, the new doc's `overview` is rewritten as *"Refreshed draft — anchored around the {N} clause(s) that {co-parent first name} and I have both proposed. Those clauses appear at the top of each section and are marked as anchored."*
  - **Frontend button** on `JointAgreement.jsx` header (`joint-agreement-regenerate-mine-open`) — only shown when `summary.both_proposed > 0`. Opens a green-branded confirm dialog explaining the promotion + preservation semantics, then hits the endpoint and shows a toast with the anchor count. Prior draft stays in the parent's Summary → Agreement history.
  - **Testing**: `test_iter116_joint_agreement.py::TestRegenerateMine` — 5 new pytests: auth required, non-participant 403, happy path inserts a new doc + preserves the prior id, anchored clauses promoted to the top with correct `anchored` flag, prior agreement doc untouched. 19/19 pass; iter113 suite still 15/15 (no regressions).



- **Iteration 117 — Email Joint Agreement Draft (2026-08-15)**:
  - **New backend route** `POST /api/joint-agreement/{share_id}/email` — assembles the Joint Agreement PDF and sends it directly to a mediator, attorney, court, therapist, or PFAL. Same consent gate as the Joint Agreement JSON/PDF endpoints. Reply-to is set to the sending parent so the recipient can respond directly. Audit log written to `joint_agreement_emails`.
  - **New email helper** `email_service.send_joint_agreement_draft(...)` — mirrors `send_joint_professional_report`'s structure but reframed as a DRAFT for discussion (yellow strip, never a signed agreement / never a custody recommendation). At-a-glance strip shows both-proposed / one-only counts + convergence %.
  - **Dialog generalisation, not duplication**: `/app/frontend/src/components/JointReportEmailDialog.jsx` now accepts a `variant` prop (`"report"` or `"agreement"`) and a `testIdPrefix`. Two internal `VARIANTS` objects swap the eyebrow, disclaimer tone (red vs yellow), scope card blurb, intro text, message-placeholder, italic-hint, and Send-button label. Defaults keep the existing test-ids intact so iter113 tests still pass.
  - **Wired into JointAgreement page** — new `Email to professional` button (`data-testid="joint-agreement-email-open"`) sits beside `Download PDF`. Handles both 200 (success toast) and 503 (mail-not-configured toast) paths cleanly.
  - **Testing**: `test_iter116_joint_agreement.py::TestEmailEndpoint` — 5 new pytests (auth, non-participant, invalid email, demo email, happy-or-503). 29/29 pass across iter113+iter116 combined; no regressions from the dialog refactor.



- **Iteration 116 — Joint Co-Parenting Agreement Draft (merged from both parents) (2026-08-15)**:
  - **New backend module** `/app/backend/joint_agreement.py` — deterministic merger (no LLM). Reads both parents' latest documents from `agreements`, matches clauses using `difflib.SequenceMatcher` at a 0.60 similarity threshold, and buckets each clause into `both_proposed` / `parent_a_only` / `parent_b_only`. Sections merged: shared_goals, communication, child_needs, household_rules, priority_items, open_for_discussion. Also computes a convergence % for the summary strip.
  - **New route** `/app/backend/joint_agreement_routes.py` — `GET /api/joint-agreement/{share_id}` (JSON) + `/pdf`. Reuses `_find_active_share` + `_load_user_display_name` from `joint_professional_report_routes` so the consent gate is identical (active Compare share = mutual consent). Returns 409 when either parent hasn't generated their individual agreement yet — with a clear instruction pointing to Summary → Co-Parenting Agreement Draft.
  - **New PDF** `/app/backend/joint_agreement_pdf.py` — branded cover with a yellow "This is a draft for discussion" banner + convergence stats, then each of the 6 sections with three colour-coded buckets (green Both / purple Parent A only / warm Parent B only). Footer marks every page as *"Draft for discussion - Not a signed agreement or court order"*.
  - **New frontend page** `/app/frontend/src/pages/JointAgreement.jsx` at route `/joint-agreement?share=<id>` — three colour-coded buckets per section, side-by-side Parent A / Parent B strips in the Both bucket, at-a-glance convergence percentage, closing-notes side-by-side card, next-step callout, PDF download.
  - **Access points wired** on all three surfaces per the earlier pattern:
     * Dashboard "Where you already agree" card gets a second inline CTA `dashboard-joint-agreement-link` alongside the Joint Report link.
     * `JointProfessionalReport.jsx` header gets `joint-report-open-agreement` button so professionals reading the summary can jump straight to the joint draft.
     * (Not repeated on the SNC2 compare page — user hits it via the dashboard / joint report entry points.)
  - **Testing**: `test_iter116_joint_agreement.py` — 9 pytests: auth required, unknown share 404, non-participant 403, expected 6 section keys, bucketing correctness with real overlap seeds, disclaimer language, convergence math, missing-agreement 409, PDF is a valid non-trivial PDF. All 9 pass; regression run with iter113 shows 24/24 pass overall.



- **Iteration 115 — Joint Report Email (2026-08-15)**:
  - **New backend route** `POST /api/joint-professional-report/{share_id}/email` — assembles the Joint Report PDF and sends it directly to a mediator, attorney, court, therapist, or parent facilitator ad litem. Same consent gate as the JSON/PDF endpoints (active Compare share required). Reply-to is set to the sending parent's email so the recipient can respond directly. Audit log written to `joint_report_emails`.
  - **New email helper** `email_service.send_joint_professional_report(...)` — branded HTML + plain-text covering letter with an at-a-glance count (aligned items / different views / issues for discussion), a red NOT-A-CUSTODY-EVALUATION strip, and the Finding-3-only safety-privacy note. PDF attaches as `joint-professional-report-<share>.pdf`.
  - **New frontend dialog** `/app/frontend/src/components/JointReportEmailDialog.jsx` — mirrors PathwayEmailDialog UX with role chips (mediator / parent facilitator ad litem / trial court / attorney / therapist / other), recipient email + name, and an optional 1200-char parent note. Prominent "This is not a custody evaluation" strip inside the dialog itself.
  - **Wired into JointProfessionalReport page** — new `Email to professional` button (`data-testid="joint-report-email-open"`) sits beside `Download PDF`. Handles both success (toast: "Joint report emailed to …") and the "email not configured" 503 case (toast surfaces the backend's message unchanged).
  - **Testing**: `test_iter113_joint_professional_report.py::TestEmailEndpoint` — 5 new tests: auth required, non-participant 403, invalid-email rejection, demo-email rejection, happy-path OR 503-when-mail-transport-disabled. All 15 tests pass.



- **Iteration 114 — Joint Co-Parenting Summary for Professional Review (2026-08-15)**:
  - **New backend module** `/app/backend/joint_professional_report.py` — pure aggregator that turns both parents' SNC v2 comparison + mediation prep + Dimension Companion tiers + TISFL Finding 3 (safe to share) into 9 neutral sections: Shared child-centered priorities, Medical needs, Educational / IEP / 504, Psychological & emotional, Consistency between households, Communication & decision-making concerns, Areas of agreement, Areas where perceptions differ, Issues for professional discussion. Every row carries `topic / parent_a / parent_b / alignment / childs_need / issue_for_discussion` and rows are sorted divergent-first inside each section.
  - **New route** `/app/backend/joint_professional_report_routes.py` — `GET /api/joint-professional-report/{share_id}` (JSON) + `/pdf`. Consent gate reuses the Compare-share model — an active share (SNC v2 or Compare-family) IS mutual consent. Non-participants get 403, unknown share 404, un-consented share 409. Loads Finding 3 via `trauma_lens.redact_for_compare` so Findings 1 & 2 never leak. Registered in `server.py`.
  - **New PDF** `/app/backend/joint_professional_report_pdf.py` — branded cover page with a red "This is not a custody evaluation" banner, per-section pages with two-column Parent A / Parent B strips + alignment pills + Child's-need + For-discussion callouts. Every page footer marks it as a "Preparation resource - Not a custody evaluation, diagnosis, or recommendation to any court".
  - **New frontend page** `/app/frontend/src/pages/JointProfessionalReport.jsx` at route `/joint-professional-report?share=<id>` — professional-facing side-by-side layout with prominent NOT-A-CUSTODY-EVALUATION disclaimer, neutral-language + safety-privacy caveat cards, 9 sections rendered as row cards, Download PDF action.
  - **Access points wired on all three surfaces** (per user's ask):
     * Dashboard "Where you already agree" card gets a new `data-testid="dashboard-joint-professional-report-link"` secondary CTA. Nested-`<Link>` violation avoided by splitting the outer clickable card.
     * `PathwayReport.jsx` header gets `data-testid="pathway-report-joint-report"` (only when a `?share=` param is present so single-parent previews don't offer it).
     * `SpecialNeedsV2CompareView.jsx` action bar gets `data-testid="snc2-compare-joint-professional-report"`.
  - **Neutral-language guardrail**: `test_iter113_joint_professional_report.py::TestPayloadShape::test_neutral_phrasing_in_issues` scans every `issue_for_discussion` / summary / childs_need string for banned adjudicative language (`mother is correct`, `should have custody`, `primary custody`, `sole custody`, `possession`, `access schedule`, etc.). Any regression re-introducing that language will fail the test.
  - **Testing**: `test_iter113_joint_professional_report.py` — 10 pytests: auth required, unknown share 404, non-participant 403, all 9 sections present, disclaimer / neutral-language / safety-privacy fields, medical section rows exist after seeding, banned-language regex sweep, PDF returns valid bytes, PDF still enforces consent gate. All 10 pass.



- **Iteration 113 — Foundation Statement + Co-Parenting Agreement shortcuts (2026-08-12)**:
  - **Dashboard shortcuts**: Added two dedicated buttons in the "Next up" card of `/app/frontend/src/pages/Dashboard.jsx` — `dashboard-foundation-statement-button` (→ `/reflection`) and `dashboard-coparenting-agreement-button` (→ `/summary?tab=agreement`).
  - **PREP_MODULES fix**: The "Declaration Statement" tile was mislabeled and mis-routed to `/summary`. Renamed to **Foundation Statement** and re-routed to `/reflection` to match the rest of the app (Landing, MyPlan, PersonalizedRecommendations, NextStepJourney all use "Foundation Statement" → `/reflection`).
  - **Summary deep-link support**: `/app/frontend/src/pages/Summary.jsx` now honours `?tab=summary|agreement|improve` via `useSearchParams`, so shortcuts open directly on the requested tab.
  - **PathwayReport shared entry point**: Added `data-testid="pathway-report-draft-agreement"` button (link to `/summary?tab=agreement`) in the header of `/app/frontend/src/pages/PathwayReport.jsx`, giving parents a one-tap way to jump from their dispute-resolution pathway into drafting the Co-Parenting Agreement.
  - **Bug fix (defensive)**: `/app/frontend/src/pages/Reflection.jsx` crashed with `(v || "").trim is not a function` when the persisted reflection dict included a boolean flag (e.g. `private: true`). Now filters to string values only in both `hasContent` and `safetyLevel` computations.



- **Iteration 112 — Reviewer Co-Sign Portal for the Court Report (2026-08-12)**:
  - **New backend module** `/app/backend/court_report_verify_routes.py` — mirrors the pathway-verify pattern. Owner-side endpoint `POST /api/safety-assessment/{assessment_id}/prepare-cosign` writes a `court_report_signatures` row keyed by `sig_id` (16-char uuid4 hex) and returns `{sig_id, verify_url, qr_png_data_url}` (base64 PNG QR). Public endpoints under `/api/verify/court-report/{sig_id}` — `GET` returns issued flag + parent name + issue date + `findings_headlines` (headlines only, never raw behavioural language); `POST /cosign` records reviewer name + role + optional notes with a 409 on second-attempt to prevent anonymous overwrites; `GET /pdf` re-downloads the court report with the reviewer's printed name + role baked into the signature block (via `build_court_report_pdf(reviewer_name=...)`), no regeneration required.
  - **New frontend page** `/app/frontend/src/pages/VerifyCourtReport.jsx` (route `/verify/court-report/:sig_id`) — public reviewer-facing page with (a) the universal self-reflection disclaimer at top ("co-signing acknowledges you have discussed the findings with the parent, not that you endorse them as an evaluation"), (b) parent name + issued date, (c) findings headlines, (d) a co-sign form (printed name, role, notes) OR a "co-signed" panel showing who signed and when, (e) a download-the-(co-signed)-court-report button.
  - **Parent-side modal** on the Safety Assessment results card — new "Get reviewer co-sign QR" button opens a modal with the QR image, the verify URL, and a "Copy link" button (`data-testid` values for `cosign-modal`, `cosign-modal-qr`, `cosign-modal-url`, `cosign-modal-copy`, `cosign-modal-close`).
  - **Privacy stance**: sig_id is unguessable; `findings_headlines` is the maximum leak surface (never raw Section-1 answers); malformed sig_ids return `issued:false` without disclosing which are real; second co-sign returns 409 so the audit trail can't be overwritten anonymously.
  - **Testing**: `test_iter112_court_report_cosign_portal.py` — 7 pytests locking prepare-cosign auth + shape, verify returns headlines-only, verify handles unknown/malformed sig_ids gracefully, cosign records and 2nd attempt 409s, cosigned PDF is valid + roundtrips through the JSON verify endpoint. All 7 pass.


- **Iteration 111 — Wall Cheer Digest in weekly email + "For your professional" one-pager (2026-08-12)**:
  - **Wall Cheer Digest**: New helper `wall_utils.get_weekly_cheer_digest(db, user_id, since_iso)` aggregates per-parent cheer counts + top-badge rollups (badge_type, human label, count) from the last 7 days, excluding self-cheers. Wired into `email_service.send_weekly_compliance_reminder()` via a new optional `wall_cheer_digest` kwarg — the Monday email now renders a purple→teal "Cheers you got this week" ribbon above the pending-items list when the digest is non-empty, listing the top 3 most-cheered badge types. Plain-text form gets the same info. Section is silently omitted when the parent received 0 cheers so the email stays warm, not empty.
  - **For Your Professional one-pager**: New endpoint `GET /api/safety-assessment/{assessment_id}/one-pager` and PDF module `/app/backend/safety_one_pager_pdf.py`. The one-pager is a very short branded handoff a parent can give to their lawyer, DV advocate, or family counsellor. Contents in order: (1) universal `SELF_REFLECTION_DISCLAIMER` at the top, (2) a "how to use this handoff" note framing the TISFL, (3) parent name + level, (4) headlines-only findings summary (never raw Section-1 behavioural text) plus the feasibility tier under Finding 3, (5) 10 targeted questions drawn from a domain-keyed bank (`pattern` / `trauma` / `plan` / `child` / `general`) — populated based on which findings actually surfaced, (6) an explicit "what this tool is NOT" section. Every page footer marks it as non-forensic with the assessment_id + date.
  - **Frontend**: New white-pill "For your professional (1 page)" button next to the black-pill Court Report button in the results card, with a `data-testid="results-download-one-pager"` and tooltip explaining what the handoff contains.
  - **Testing**: `test_iter111_wall_digest_and_one_pager.py` — 8 tests locking (a) self-cheers excluded from digest, (b) empty digest for parents with no events, (c) email HTML renders the digest with correct counts and badges, (d) email omits digest when count is zero, (e) one-pager endpoint returns a valid PDF, (f) auth required, (g) 404 for unknown assessment, (h) source-check that the module references the universal disclaimer + all five question banks. All 8 pass.


- **Iteration 110 — Coparenting Feasibility Spectrum (Phase 2) (2026-08-12)**:
  - New module `/app/backend/feasibility_spectrum.py` exposes `recommend_tier()` — a deterministic 6-tier ladder wired to Finding 3 of the Trauma-Informed Safety and Functioning Lens.
  - **Tiers (most restrictive → least)**: `suspended_contact` → `supervised_contact` → `supervised_exchanges` → `parallel_parenting` → `structured_coparenting` → `cooperative_coparenting`. Each tier carries its own narrative, `structure_words`, order (1-6), and review-point cadence (30 / 60 / 90 / 180 / 180 / 365 days).
  - **Explicit thresholds**:
    * *Suspended contact* triggers: `ce_q1` (child directly harmed), `s1_q25` (distinct homicide threat), `s1_q13` (any strangulation).
    * *Supervised contact* triggers: `s1_q19` (strangulation pattern), `s1_q14` (forced sexual activity), `s1_q2` (physical restraint/harm), `ce_q2` (children exposed).
    * *Supervised exchanges* triggers: `s1_q4` (stalking), `s1_q22` (digital surveillance), `s1_q20` (firearms access), `s1_q26` (suicide threat), `s1_q11` (violence escalating).
    * *Pattern-typology floors*: `coercive_controlling` → at least parallel; `violent_resistance` → at least parallel (shaped by the underlying coercive pattern the answering parent is being protected FROM, not by their defensive conduct — this is explicitly explained in the tier's caveat); `situational` / `separation_instigated` → structured; `unclear` → cooperative.
    * Base-level baseline: level 4 → cooperative; level 3 → structured; level 2 → parallel; level 1 → supervised_contact.
  - Wired into `trauma_lens.build_findings(section_1_answers=…)` so the submit endpoint threads Section-1 raw answers + typology + child_experience_raw into `recommend_tier()`, and the resulting `feasibility_tier` block is attached to Finding 3 (which is the ONE finding the co-parent's Compare view can see).
  - Court-report PDF renders the tier under Finding 3 with the tier label, structure words, review-point days, and caveats (violent-resistance note included when applicable).
  - Frontend results card gets a new `data-testid="finding-feasibility-tier-{tier}"` card under Finding 3 with the tier label, "Tier N of 6" designation, narrative, escalation-triggers list, and caveats.
  - Locked with 18 tests: `test_iter110_feasibility_spectrum.py` (13 pure-function tests) + `test_iter110b_feasibility_http.py` (5 HTTP integration tests).


- **Iteration 109 — Universal self-reflection disclaimer (2026-08-12)**:
  - Added a shared constant `trauma_lens.SELF_REFLECTION_DISCLAIMER` with the exact language: *"This assessment is a guided self-reflection and preparation resource. It is not a clinical, forensic, legal, or professional evaluation. Its results are intended to help you identify concerns, organize your thinking, and prepare questions for an appropriate professional."*
  - Surfaced this disclaimer prominently on: (a) the Safety Assessment intake page as a purple call-out above the safety notice, (b) the top of the results card via `data-testid="results-self-reflection-disclaimer"`, (c) the standard Safety Assessment PDF's "Important — read this first" section, (d) the Court Report cover's "Limits of use" (now leads with this framing), (e) the Mediation-Readiness disclaimer.
  - Locked with `test_iter109_universal_disclaimer.py` — 6 tests keep the language identical across every surface.


- **Iteration 108 — Mediation-Readiness profile-first output (2026-08-12)**:
  - Refactored `readiness_scoring.compute_readiness()` to lead with a per-domain **profile** (level `emerging`/`developing`/`solid` + headline + narrative + strengths + growth-areas + specific preparation recommendations) rather than a single overall number. Legacy `overall`/`label`/`dimensions` fields preserved unchanged for backwards compatibility.
  - Added `readiness_disclaimer` at the top of the payload naming the *completeness vs readiness* distinction, and `caveats` that fire when the profile could mislead (safety concerns present, or polished-communication + high-conflict combo — the exact failure mode the user flagged).
  - Trust-domain recommendations at the `emerging` level explicitly route the parent to Finding 3 of the Trauma-Informed Safety and Functioning Lens rather than joint mediation.
  - `ReadinessDashboard.jsx` rebuilt to lead with the four-domain descriptive profile (level pill + strengths + growth areas + numbered preparation recommendations); the overall number is now a secondary indicator card below the profile.
  - Locked with `test_iter108_readiness_profile.py` — 6 tests including the polished-communication-plus-high-conflict-load case.


- **Iteration 107 — Phase 3/4/5 lens extensions HTTP integration (2026-08-12)**:
  - `POST /api/safety-assessment` accepts optional `pattern_context`, `trauma_impact`, `child_experience` sections. When >=3 items are answered in a section: Finding 1 gets `pattern_typology` (coercive_controlling / violent_resistance / situational / separation_instigated / unclear), Finding 2 gets per-domain `domain_signals` (hypervigilance / avoidance / dissociation / sleep / fear_communication), and a NEW Finding 4 (`child_experience`) appears with concern-domains and a protective-relationships resilience flag.
  - `GET /api/safety-assessment/questions` exposes all three extension banks.
  - Locked with `test_iter107_lens_extensions_http.py` — 7 tests covering empty-is-valid, coercive typology, violent-resistance typology, trauma domain aggregation, Finding 4 emergence with high-concern flag, and the below-threshold no-Finding-4 case.


- **Iteration 106 — Safety-screen gap closure (2026-08-12)**:
  - Added 10 structured items to Section 1 (`s1_q19` through `s1_q28`) closing gaps the user identified: strangulation pattern (`s1_q19`), firearms access (`s1_q20`), sexual coercion — non-force (`s1_q21`), digital surveillance / spyware / GPS trackers (`s1_q22`), financial abuse — sabotage / debt in name / employment interference (`s1_q23`), substance use *during* incidents (`s1_q24`), distinct homicide threat (`s1_q25`), distinct suicide threat (`s1_q26`), currently-in-force protective order (`s1_q27`), and history of being advised to seek a protective order (`s1_q28`).
  - The 8 high-severity items carry `high_concern=True` and `da_domain=True` where appropriate — a yes on any of them escalates the score to level ≤ 2 (never soft-pedalled). The 2 protective-order items are informational (do NOT shift the level by themselves so declining to pursue an order isn't punished by the score).
  - Each new item carries a `gap_domain` tag for court-report audit trails.
  - Locked with `test_iter106_safety_gap_closure.py` — 3 tests covering exposure via /questions, high-concern escalation for all 8 high-severity items, and informational-only behaviour of the protective-order items.
  - Ported all downstream test helpers (`test_iter42-48`, `test_snc2_*`, `test_iter103`, `test_iter105`, `test_safety_assessment_mediator_email`) from `range(1, 19)` to `range(1, 29)`.


- **Iteration 105 — Trauma-Informed Safety and Functioning Lens (TISFL) — Phase 1 (2026-08-12)**:
  - **Framework module** `/app/backend/trauma_lens.py` — defines `LENS_NAME`, two `INTERPRETATION_RULES`, five `PROCEDURAL_SAFEGUARDS`, and `build_findings(result)` which derives three separate findings from any scored assessment (level 1-4 aware). Never mutualises abuse. Never diagnoses. Level-1 pattern language uses serious-danger framing; level-2 uses coercive-control framing; level-4 explicitly says no pattern indicated at this time.
  - **Three findings** (rendered separately in the UI and PDFs so they aren't collapsed into one score): (1) Family-Violence Pattern — *confidential*, (2) Trauma Impact — *confidential*, non-diagnostic, (3) Parenting-Plan Implications — *shareable*, includes an arrangement spectrum (cooperative → structured → parallel → supervised). `redact_for_compare()` helper strips findings 1 & 2 so the co-parent's Compare view only ever sees Finding 3.
  - **Two interpretation rules** surfaced on the intake page, results card, standard PDF and court report: "Trauma symptoms are not evidence that a parent is unreliable, unfit, or responsible for the violence." + "A history of trauma does not excuse coercion, intimidation, child maltreatment, or other harmful parenting behavior."
  - **Procedural safeguards banner** on the intake page: separate completion, pause-any-time, non-diagnostic, safety-walled from Compare, DV-hotline escape line.
  - **New court-facing PDF endpoint** `GET /api/safety-assessment/{assessment_id}/court-report` (owner-only, requires saved account) — `safety_court_report_pdf.py` produces a professional multi-page document: cover page with the two rules + methodology + limits-of-use statement, one page per finding, procedural-safeguards attestation page, and a signature block (parent + optional reviewer co-signature). Deliberately excludes raw Section-1 behavioural answers so the filing is safe. Footer includes assessment_id + generated date + "not a forensic evaluation" on every page.
  - **AI prompt hardening** (`safety_ai_summary.py::_system_message`) — added lens-aligned rules to Claude Sonnet 4.5: non-diagnostic (banned terms: PTSD, NPD, BPD, bipolar…); never mutualise abuse; trauma responses are protective adaptations, not character flaws; trauma history never excuses coercion.
  - **Frontend** (`SafetyAssessment.jsx`) — renamed the page hero to "Trauma-Informed Safety and Functioning Lens · TISFL"; added the procedural-safeguards banner + inline interpretation rules on the intake page; results card now renders the three findings in colour-coded stacked cards (red-l pattern, amber-l trauma, purple-l plan) with per-finding core question, headline, summary, non-diagnostic note, and arrangement spectrum; new "Download court report" black-pill button next to the standard PDF button. Dashboard tile relabelled with the lens name and short blurb.
  - **Testing**: `test_iter105_trauma_lens.py` — 7 pytests locking (a) pure-function shape at every level, (b) redact-for-compare removes findings 1&2, (c) submit attaches lens to result, (d) court-report endpoint returns real multi-page PDF (>10KB with PDF magic bytes), (e) court-report requires auth, (f) 404 for unknown assessment_id, (g) level-1 pattern language uses serious-danger framing. All 7 pass. Iter102-104 remain green (22/22). Broader test corpus (`test_safety_assessment.py`, `test_iter42-48`) still 95/97 pass (the 2 residual fails are the pre-existing stale metadata assertions unrelated to this change).


- **Iteration 104 — "Answer every question" guard on Family Violence submission (2026-08-12)**:
  - **Backend**: New `_validate_all_answered()` helper rejects `POST /api/safety-assessment` submissions that don't cover every s1_q1..s1_q18 and s2_q1..s2_q8. Returns HTTP 400 with a machine-readable payload `{ "message": "…", "missing": { "section_1": [...], "section_2": [...] } }` so the UI can highlight the exact rows to answer. Accepted answers are Yes/No/Unsure (case-insensitive) — anything else (empty, "maybe", etc.) is treated as missing.
  - **Frontend**: New `ProgressStrip` component sits above each section showing "X / Y answered" with a filled progress bar that transitions to a purple→teal gradient on completion. `QuestionRow` renders a red ring + "Please answer this one" badge for any row that came back in the server's `missing` payload. The submit handler parses the 400 response, jumps the wizard back to the earliest section with missing items, and clears the flag on each row as the parent answers it. A scripted client can no longer slip an incomplete assessment past.
  - **Testing**: `test_iter104_safety_all_answered_guard.py` — 5 live-server pytests: (a) empty submission → 400 with all ids missing, (b) partial submission → 400 flagging only the unanswered ids, (c) unknown values ("maybe", "") treated as missing, (d) fully-answered submission → 200 with real result payload, (e) mixed-case answers accepted. Updated helpers in `test_safety_assessment.py`, `test_iter42-48`, `test_snc2_compare_api`, `test_snc2_enhancements`, `test_safety_assessment_mediator_email` to send complete section 1 (18 items) + section 2 (8 items) payloads with a `_CLEAN_S2` / autofill baseline so callers only need to override items driving the target level. All 143 impacted tests pass.


- **Iteration 103 — Regenerate AI Summaries button (Family Violence Report, 2026-08-11)**:
  - **New endpoint** `POST /api/safety-assessment/{assessment_id}/regenerate-summaries` clears the cached `ai_summaries` on the assessment doc and re-invokes Claude Sonnet 4.5 for all four narrative components (`overall`, `pathway`, `section_1`, `section_2`). Returns the fresh summaries + a `ai_summaries_generated_at` ISO timestamp.
  - **Access**: assessment owner OR ADMIN_EMAILS operator. Admin can regenerate any parent's assessment (returns `forced_by_admin: true` when the caller isn't the owner).
  - **Cooldown**: 1 regen per `SAFETY_SUMMARY_REGEN_COOLDOWN_SEC` (default 600s = 10 minutes) per assessment, enforced from the doc's `ai_summaries_generated_at`. Admins bypass the cooldown so ops can force-refresh support cases without waiting.
  - **Frontend**: new "Regenerate AI summaries" button in `SafetyAssessment.jsx`'s `ResultsCard`, sitting alongside Download / Email / Email Mediator / Problem-Solving actions. Shows a spinning `RefreshCw` icon while regenerating. Admins see the button re-labelled "Regenerate AI summaries (admin)" with a tooltip flagging the no-cooldown bypass. On 429, the button shows the exact "wait Xm Ys" copy from the backend so parents know when they can retry.
  - **Testing**: `test_iter103_safety_regenerate_summaries.py` — 4 live-server pytests: (a) 401 without auth, (b) 404 for unknown assessment_id, (c) happy-path parent regen + immediate 429 on second call inside cooldown, (d) admin bypass of cooldown on another parent's assessment. All 4 tests pass against real Claude Sonnet 4.5 (72s run — includes actual LLM latency).


- **Iteration 92 — Pathway Report PDF Export (2026-02-27)**:
  - **New PDF builder** `pathway_report_pdf.py` — professional layout mirroring the 4-Dim Briefing visual system (brand purple/teal, `_safe` sanitiser, `_section_break`). Cover with generation metadata, primary pathway card (red-bordered when safety hard-lock fires + prominent "Safety trigger applied" panel), factors, goals, per-pathway suitability table with coloured chips, considerations, data-inputs-used table, legal disclaimer footer.
  - **Two new endpoints**: `GET /pathway-report/preview/pdf` (single-parent) + `GET /pathway-report/dual/{share_id}/pdf` (dual, same consent gate via `_find_active_share`). Both return `Content-Disposition: attachment` with sensible filenames (`pathway-report-preview.pdf`, `pathway-report-{share_id}.pdf`).
  - **Language guardrails preserved**: PDF never says "you should"; hard-lock panel copy explicitly disrecommends mediation with survivor-safe language.
  - **Privacy**: dual PDF never leaks per-input state for the OTHER parent — the "Data inputs used" block only lists the caller's own presence flags.
  - **Frontend**: `PathwayReport.jsx` gains a top-right "Download PDF" button with a spinner while streaming (testid `pathway-report-download-pdf`). Works from both preview and dual views.
  - **Testing**: 4 new pytests — `test_pdf_builder_renders_valid_pdf_for_neutral_case` (renders + PDF magic header), `test_pdf_builder_stamps_hard_lock_when_present` (semantic assertion — locked payload has `hard_locked_by` + primary = litigation; PDF still renders), `test_route_preview_pdf_returns_pdf` (live route + content-type + disposition header), `test_route_dual_pdf_returns_pdf_for_active_share` (seeds real `edu_deep_shares` row, calls dual endpoint, asserts PDF + filename echoes share_id). **22/22 iter91 tests pass** (up from 18), **61/61 across iter 87-91**. Live curl E2E: preview PDF 4041 bytes with `%PDF-1.3` header; dual PDF 3299 bytes against real seeded share. Live screenshot confirms the button renders correctly on the page.
  - **Deferred**: mediator email + QR-verify (iter 93 add-on) — same follow-up pattern as the 4-Dim Briefing.



- **Iteration 94 — Code Review Fixes: Pathway Report Data Layer + Alert Dedupe (2026-02-27)**:
  - **HIGH #1 fixed** (`pathway_report_routes.py`): `_load_party_context` was reading `dimension_companion` (empty legacy collection, 0 rows) instead of `dimension_companion_assessments` (real collection, 9 rows) — companion dimension signals were silently dropped from every recommendation. Also updated tier vocabulary in `pathway_report.py::_tier_score` — the real vocab is `strong/steady/stretched/strained` (4 tiers), not `aligned/stretch/strained` (3 tiers I invented). New scale: `strong=3, steady=2, stretched=1, strained=0`. Classification thresholds shifted from `>=2/>=1` to `>=3/>=2` on the strict paths (`worst_comm >= 3` now requires "strong" for mediation-high) to preserve semantic meaning.
  - **HIGH #2 fixed** (`pathway_report_routes.py::_find_active_share`): was querying snapshot tables (`deep_dive_compare_snapshots`, `compare_shares`, `snc2_compare_shares`) which don't carry `status`/`user_pair`. Real shares live in `edu_deep_shares` (475 rows), `med_deep_shares` (211), `psych_deep_shares` (214), `snc2_shares` (124) — the entire two-parent Pathway Report was unreachable for every real share before this fix.
  - **LOW #1 fixed** (`nd_coordinator_alerts._should_fire`): when a parent's tier oscillates (e.g. `critical → high → critical`), a downgrade previously returned `"hit"` bypassing the 24h dedupe window and generating repeat operator emails. Downgrades now respect the same-tier window.
  - **LOW #2 fixed** (`reviewer_panel_routes._load`): backfilled ids on legacy entries are now persisted immediately (self-healing migration on first load). Previously each GET generated fresh random ids, so PATCH/DELETE using a previously-returned id would 404. Not reachable today (file has 0 legacy entries) but latent.
  - **Test coverage gap closed**: `test_iter91_pathway_report.py` now includes 3 route-integration tests that go through real Mongo shape — one seeds a live share in `edu_deep_shares` and asserts the dual endpoint returns 200 with proper envelope, one asserts 409 on pending share, one asserts preview reads the real companion collection. These would have caught both HIGH defects.
  - **Testing**: 18/18 iter91 tests pass (up from 15). 57/57 tests pass across iter 87-91. Live end-to-end proves: preview now reports `dimension_companion: True`, dual endpoint returns 200 + `is_dual_party: True` against a seeded real share row.
  - **Review outcome**: all HIGH findings addressed with regression tests. All LOW findings fixed. Coverage gap flagged by reviewer (missing route-integration tests) closed.



- **Iteration 93 — Pathway Report Unlock Hint on Compare Empty State (2026-02-27)**:
  - **New component** `PathwayReportUnlockHint.jsx` — dashed-border card shown at the TOP of a Compare hub, before the "Start a new comparison" form. Copy names the concrete downstream reward: "Both of you also unlock the two-parent Dispute Resolution Pathway Report", enumerates the four pathway options, and reiterates the safety-trigger guardrail so it doesn't oversell mediation.
  - **Auto-hide logic**: `anyActive = shares.some(s => s.ready_to_view || s.status === "active")`. If true, hint returns null — at that point the compare *view* page's CTA card (iter 92) is the right surface, not the hub.
  - **Wired on**: `DeepDiveCompareHub.jsx` (covers all 4 deep-dive compare pathways) + `SpecialNeedsV2Compare.jsx`.
  - **Solo-preview link**: hint includes a small "See a solo preview against your own data →" link to `/pathway-report` so curious parents can view the single-parent preview before inviting.
  - **Testids**: `{prefix}-pathway-unlock-hint`, `{prefix}-pathway-unlock-preview`.
  - **Testing**: 5-case visibility probe passed (empty / only-revoked / pending-consent / one-ready-to-view / one-active). Live smoke-tested against parent1's account: they already had a ready-to-view share, hint correctly auto-hid (confirming the anyActive branch works in production). Zero backend changes needed.



- **Iteration 92 — Pathway Report Deep Link on Compare Views (2026-02-27)**:
  - **New component** `PathwayReportPrompt.jsx` — compact CTA card ("Both parents have consented — generate the two-parent pathway report") that deep-links to `/pathway-report?share={shareId}`. Copy stays inside the same language guardrails ("for professional consideration", never "your recommended pathway").
  - **Wired on**: (1) `DeepDiveCompareView.jsx` — the reusable component behind every deep-dive compare pathway (mediation, educational, psychological, medical). (2) `SpecialNeedsV2CompareView.jsx` — the SNC2 compare page. Card sits just below the alignment summary bar and the milestone celebration, above the highlights section.
  - **Gating** stays server-side (from iter 91): `/api/pathway-report/dual/{share_id}` returns 409 if the share isn't fully consented, 403 if the caller isn't a participant, 404 if the share doesn't exist. So the CTA is safe to render anywhere a compare view successfully loaded.
  - **Testids**: `{prefix}-pathway-report-prompt` and `{prefix}-pathway-report-open`, where `{prefix}` is either the deep-dive pathway prefix or `snc2-compare`.
  - **No new backend code**. Frontend lint clean.



- **Iteration 91 — Dispute Resolution Pathway Report (2026-02-27)**:
  - **Backend scoring engine** (`pathway_report.py`): deterministic rules that fuse 5 inputs (Safety Screen, ND Risk, Dimension Companion, Compare alignment %, Compliance streak) into one of four pathways — Mediation / Child-Centered Relational Mediation / Collaborative Family Law / Litigation. Includes per-pathway suitability rating (High / Moderate / Low / Not indicated). No LLM — every branch is transparent and comment-explained.
  - **Safety hard-lock (ethical anchor)**: if EITHER parent's Safety Screen shows level 1 (court-required pathway), a coercive-control trigger, OR a physical-safety trigger, the algorithm forces Litigation as the ONLY primary — mediation → `not_indicated`, other consensual paths → `low`. Reasoning is surfaced under `hard_locked_by`. Never mutualises abuse.
  - **Language guardrails**: never says "you should"; always "the combined assessment data indicates". Every pathway comes with `factors_supporting_primary`, `considerations`, `goals_before_or_during`. Tie-breaker always picks the LEAST adversarial option.
  - **API** (`pathway_report_routes.py`):
    - `GET /pathway-report/preview` — single-parent preview (caller's own data). Result flags itself as a preview + nudges parent to invite co-parent.
    - `GET /pathway-report/dual/{share_id}` — full 2-parent report. Gated behind an ACTIVE `deep_dive_compare` share (reuses the existing mutual-consent flow — no new consent UI needed). Reads both parents' Safety + Companion + ND Risk + Compliance from Mongo using the share's user_pair. Returns 409 if the share isn't fully consented and 403 if the caller isn't a participant.
  - **Frontend**: new page `/pathway-report` (`PathwayReport.jsx`). Renders primary pathway card, hard-lock trigger panel (red) when applicable, factors list, goals list, suitability profile with per-pathway coloured chips, considerations block, "not legal advice" footer. Testids: `pathway-report-{root,loading,error,primary,primary-label,hard-lock,factors,goals,suitability,considerations,preview-banner}` + `pathway-suitability-{key}`.
  - **Testing**: `test_iter91_pathway_report.py` — 15/15 pass. Priority tests are the ethical anchors: coercive-control from EITHER side hard-locks to litigation, physical-safety trigger hard-locks, safety level 1 hard-locks, and the "no prescriptive language" sweep test that scans every string field for banned phrases like "you should". Also covers happy paths for all four pathways, tie-break policy (least adversarial wins), and no-data no-crash behaviour. Live curl E2E: parent1 with critical ND-risk correctly routed to Litigation as a *soft signal* (not hard-locked) with full suitability profile shown.
  - **Deferred**: professional PDF export + mediator email (planned as iter 92 — reuses the 4-Dim Briefing PDF + QR-verify pattern).



- **Iteration 90 — Weekly Compliance Reminder (Monday nudge email) (2026-02-27)**:
  - **Backend**: new `weekly_compliance_reminder.py` — `send_weekly_compliance_reminders(db, dry_run, now, force_window)` pure sweeper + `weekly_compliance_reminder_loop(app)` background task (registered in `server.py` alongside the other schedulers). Sweep runs only during Monday 08:00-22:00 UTC (env-configurable `WEEKLY_COMPLIANCE_REMINDER_START_HOUR_UTC` / `_END_HOUR_UTC`). Loop is gated behind `WEEKLY_COMPLIANCE_REMINDER_ENABLED=1` — off by default; operator flips the env var + restarts backend when ready to go live.
  - **Suppression matrix**: opt-out row, no email, `@demo.local`, `>60 days` inactive on compliance, `≥80%` already ticked this week (STREAK_THRESHOLD_PCT), or already sent to this user this ISO week. Sends collection `weekly_compliance_reminder_sends` records every send + failure (mirrors the coordinator alerts audit pattern — a broken Resend never causes a re-attempt storm).
  - **Email**: new `email_service.send_weekly_compliance_reminder` — warm, streak-aware copy (`"You're on a K-week streak. Nice work — keep the momentum this week."`), top-5 pending items list with "+ N more" overflow, current-week percentage, CTA button back to `/compliance`, footer "Turn it off" link. Subject: `Monday check-in · N intervention(s) still open`.
  - **Endpoints on `intervention_compliance_routes.py`**:
    - `GET/PUT /interventions/reminder-preferences` — parent-facing opt-in/out (default opt-in = True when no row exists)
    - `POST /interventions/weekly-reminder/admin/send-me-preview` — operator-only, fires a real email to the operator's inbox using their real data
    - `POST /interventions/weekly-reminder/admin/sweep?dry_run=true&force_window=true` — operator-only manual trigger; dry-run defaults true so operator can see who WOULD get a reminder before flipping any switches
  - **Frontend**: `ReminderPreferencesCard` component on `InterventionCompliance.jsx` between the streak panel and the checklist — clean toggle switch, hint copy "A short email early each Monday listing the interventions you haven't ticked yet, so your streak stays alive". Testids: `reminder-preferences-card`, `reminder-preferences-toggle`.
  - **Testing**: `test_iter90_weekly_reminder.py` — **15/15 pass** covering: (1) Monday send-window bounds, (2) Tuesday short-circuit, (3) opted-in default, (4) opt-out persistence, (5) happy-path dispatch + audit row, (6) dry-run never sends, (7) opted-out suppression, (8) inactive-user suppression, (9) high-enough-pct suppression, (10) same-week dedupe, (11) demo-email skip, (12) email-provider failure still writes audit row. Live curl E2E: operator preferences round-trip, dry-run sweep found parent1 with 21 pending items, non-operator got 403, real preview email fired to operator inbox (Resend 200). Fixed one bug during E2E — `distinct()` in Motor is a coroutine, not an async cursor; production code updated.



- **Iteration 89 — Coordinator Alerts for High / Critical ND Risk Assessments (2026-02-27)**:
  - **Backend**: new `nd_coordinator_alerts.py` with `maybe_fire_coordinator_alert()` — writes to `nd_coordinator_alerts` collection and dispatches an operator email via new `email_service.send_coordinator_nd_alert`. Dedupe rules: (1) `low`/`medium` never alert; (2) first-time `high`/`critical` → alert reason `hit`; (3) same tier within 24h → suppressed; (4) same tier after 24h → alert reason `re_hit`; (5) tier escalation (e.g. `high` → `critical`) always fires immediately with reason `escalated`; (6) rows are recorded even on email-provider failure so a downed Resend doesn't cause every submit to re-attempt a broken send.
  - **Hook site**: `nd_risk_routes.submit_assessment` fires the alert AFTER Mongo insert, wrapped in try/except so a broken email never blocks the parent's submission.
  - **Email payload**: goes to `OPERATOR_EMAIL` — headline like "ND Risk hit Critical", tier + score/16, target parent name, coparent name, assessment_id, submitted-at (UTC), curl-ready `GET /api/nd-risk/assessment/{id}` hint. Copy is deliberately terse for phone lock-screen legibility.
  - **Testing**: `test_iter89_nd_coordinator_alerts.py` — 15 tests pass covering all six dedupe branches + email-provider-down persistence guarantee + full happy-path monkeypatch capture. Live end-to-end curl against preview: parent1 submitted a critical-tier assessment → Resend returned 200 → audit row shows `email_ok: true`, `score: 16`, `reason: hit`. Second submit inside 24h correctly suppressed (count stayed at 1). Total score bug (`scored["total"]` → `scored["total_score"]`) caught + fixed in the same session.



- **Iteration 88 — Reviewer Admin Page (operator-only CRUD for reviewer_panel.json) (2026-02-27)**:
  - **Backend** (`reviewer_panel_routes.py`): added `_save()` helper (atomic tmp-file + rename, auto-bumps `last_updated` on every write); `_load()` back-fills stable `id` (uuid4 hex[:12]) on any legacy entries. New operator-gated endpoints — `POST /reviewer-panel/reviewers`, `PATCH /reviewer-panel/reviewers/{id}`, `DELETE /reviewer-panel/reviewers/{id}`. Public helper `GET /reviewer-panel/reviewers/roles` for the admin form's role dropdown. Server-side validation: role must be one of the 5 known keys, `review_date` must parse as `YYYY-MM-DD`, name min 2 chars.
  - **Frontend**: new `AdminReviewers.jsx` at `/admin/reviewers` — inline form (name, role dropdown, org, review_date native picker, review_scope, attestation) with Add / Edit / Cancel / Save + Remove buttons; empty-state card when no reviewers; non-operator gate shows "Operator only" placeholder with a link back to public methodology. Testids: `admin-reviewers-{root,not-operator,loading,empty,list,add-btn}` + `admin-reviewers-form-{name,role,date,org,scope,attestation,save,cancel}` + `admin-reviewer-{item,edit,delete}-{id}`.
  - **Discoverability**: `ReviewerPanelCard.jsx` now shows a "Manage reviewers" link (testid `reviewer-panel-manage-link`) next to the "Send packet" button — visible only to the operator.
  - **Testing**: `test_iter88_reviewer_admin.py` — 4 tests pass: public roles endpoint, non-operator 403 on add, full add→PATCH→DELETE round-trip (with 404 on second delete + 400 on bad role/date via PATCH), add rejects bad role/date via POST. Cleanup fixture keeps `reviewer_panel.json` clean across runs. Frontend smoke-tested against preview URL — operator sees full form with the sample entry filled in, parent1 sees the "Operator only" gate.



- **Iteration 87 — Signed Briefing Verify (QR-scan issuance check) (2026-02-27)**:
  - **Backend**: New `briefing_verify_routes.py` with helper `record_briefing_signature(db, user_id, parent_name, audience, snapshot) -> {sig_id, verify_url}` (uuid4 hex[:16] id, writes `briefing_signatures` row with `issued_on` UTC calendar date + internal-only snapshot of scores) and public endpoint `GET /api/verify/briefing/{sig_id}` returning `{issued, issued_on, sig_id}` only — no snapshot ever leaks.
  - **PDF builder**: `four_dimension_briefing_pdf.py` accepts new kwargs `briefing_sig_id` / `briefing_verify_url`; footer of every page stamps a 12×12mm QR at bottom-LEFT (out of the way of the optional signature QR at bottom-right) via new `_stamp_briefing_verify_qr`; cover shows a "Briefing ID" line for at-a-glance eyeballing.
  - **Wiring**: Both briefing-generation endpoints (`GET /dimension-companion/four-dimension-briefing/pdf` and `POST /dimension-companion/four-dimension-briefing/email`) now call `record_briefing_signature` before building the PDF; new helper `_briefing_snapshot` extracts internal-audit fields (safety level + pathway_title, per-dim tier+score, follow-through %).
  - **Frontend**: New page `/verify/briefing/:sig_id` (`VerifyBriefing.jsx`) with minimal privacy-first UI — green "Yes — issued by SA CoParents on {UTC date}" or red "Not recognised". No scores, tiers, names, or audience shown per product decision. Route ordered above generic `/verify/:sig_id` in `App.js`. Testids: `verify-briefing-{root,ok,not-issued,error,loading,date,id,back}`.
  - **Privacy**: Public verify response intentionally minimal — protects survivors if QR image escapes and avoids mutualising abuse via score exposure. Snapshot stored server-side for operator-only reconstruction of disputed briefings.
  - **Revocation**: Not implemented — each generation stands on its own (per product decision).
  - **Testing**: `test_iter87_briefing_verify.py` — 5 tests pass: PDF-with-sig is larger than without, `record_briefing_signature` shape + row insertion, unknown id returns issued=false, malformed id returns issued=false (no 500), full download → DB row → verify round-trip. All 16 pre-existing briefing/compliance tests still pass (no regressions). Live screenshots taken of both `issued=true` (August 6, 2026) and `Not recognised` states.



- **Iteration 84 — Neurodivergent Coparenting Risk Assessment (2026-02-06)**:
  - **Backend**: New `nd_risk_routes.py` — profile CRUD, POST assessment (auto-scores + tiers to Low / Medium / High / Critical using `threat × vulnerability`, each axis = max of 3 sub-dimensions for safety-conservative scoring), coordinator summary with per-user 4×4 heatmap + tier counts, admin-gated multi-case view. New `nd_risk_pdf.py` — court-ready PDF with formal cover, methodology brief, score card, marked 4×4 heatmap, interventions checklist, disclaimer footer, and existing tamper-evident signature QR from iter72.
  - **Frontend**: `/nd-risk-assessment` intake (2 axes × 3 items, 1-4 rating) + `/nd-risk-assessment/result/:aid` result view (tier pill, marked 4×4 grid, interventions checklist, one-click court-ready PDF download).
  - **Dashboard tile** added under the existing "Family Violence Assessments" category (iter83). **Cross-link** ("Recommended next: Neurodivergent Risk Assessment") added on the Safety Assessment result page.
  - Coordinator dashboard is admin-only per iter84 design decision — regular parents see their own case on a clean personal result page instead of a fake multi-case grid.
  - 11/11 pytest module `test_iter84_nd_risk.py` pass (scoring boundary tests + full API round-trip + PDF response shape + access-control 404 + coordinator response shape). Live smoke-test confirmed: 3+3 → tier High, cell (3,3) marked, 5 interventions populated.



- **Iteration 83 — Preparation Modules regrouped into 4 named categories (2026-02-06)**:
  - Restored the parent's four-group menu on the Dashboard: **Co-Parenting Assessments**, **Foundation Statements**, **Family Violence Assessments**, **Special Needs Assessments** (medical + educational + psychological). Each group has its own header row with a one-line hint.
  - Added `category` field to `PREP_MODULES` + new `PREP_MODULE_CATEGORIES` list defining the four groups with intentional ordering (foundation → co-parenting → safety → special-needs). Grouped rendering with `dashboard-prep-category-{coparenting|foundation|safety|special-needs}` testids; existing per-module + recommended-badge testids preserved.
  - Live-tested logged in as parent1 — all four category headers render with the correct child modules in each.



- **Iteration 82 — Homepage FAQ + broken-link cleanup (2026-02-06)**:
  - **HomepageFAQ** — compact 4-question strip inserted between TrustSignals and FinalCTA, using native `<details>`/`<summary>` (no JS state) with a rotating `+` icon on open. Questions target the last trust doubts hesitant parents carry: solo-usable, privacy, professional boundaries, and safety. Testids: `homepage-faq`, `homepage-faq-{solo,privacy,professional,safety}` + `-summary` and `-answer`.
  - **Broken link removed**: FinalCTA's secondary "Learn More About Child-Focused Mediation" button scrolled to `#child-focused-mediation` — a section retired in iter80. Removed the secondary CTA entirely so FinalCTA now has a single primary action (matches iter81's "one recommendation, one next action" principle). Retired the now-unused `SecondaryCTA` helper.
  - Landing.jsx lints clean; live smoke-test confirms FAQ renders and expands.



- **Iteration 81 — Hero copy + Gmail prominence (2026-02-06)**:
  - **Hero copy rewritten** per user brief: H1 "Prepare for better co-parenting conversations." · Sub-head "Choose what your family is facing and receive a personalized starting point, practical communication tools, and reports you can bring to mediation or professional support." · Supporting reassurance: "Private guest access · No payment required to begin · About 10 minutes". The situation picker is now the single primary action; "Watch how it works" and "Or explore as a guest →" demoted to inline text links; the old 4-item trust-indicator grid removed (its ideas already live in TrustSignals further down).
  - **Gmail Mini Inbox removed from Dashboard**: connecting an inbox is a major trust request and was appearing directly beneath the Situation Picker. It now lives only on the dedicated `/gmail` page, reached through app-shell navigation.
  - **Plain-language disclosure block** added to the `/gmail` connect state (`data-testid="gmail-disclosure"`) with a 4-row Read / Store / Retain / Send breakdown, plus a direct deep-link to Google Account permissions for revoking access. Framed explicitly as an "optional advanced tool".
  - Removed unused `TertiaryCTA` helper and `CheckCircle2` import. Landing.jsx lints clean; live smoke-test confirms H1, sub-head, and reassurance strings render exactly as brief.



- **Iteration 80 — Homepage tightened per user brief (2026-02-06)**:
  - **Length**: `Landing.jsx` went from 1192 → 897 lines (**~25% shorter**, right in the requested 20–30% range).
  - **New section order**: (1) Promise + situation picker (Hero — picker embeds the recommended pathway inline once a parent selects a situation), (2) What you receive (ThreeReportsStrip — each card still carries a "See sample" link), (3) How it works, (4) Trust, privacy, professional boundaries, (5) Final CTA.
  - **Removed as duplicative** (their key ideas already live inside Hero + Situation Picker + ThreeReports): `TheProblem` (~55 lines), `ChildFocusedMediation` (~55 lines), `SampleReports` + `SampleMediation/Safety/Progress` + `ReportPageFrame/SampleStat/SampleSection` (~185 lines). No external links reference the retired anchor IDs (`#sample-reports`, `#child-focused-mediation`) — nav/footer clean.
  - Removed 4 now-unused lucide-react imports (`Quote`, `ChevronRight`, `BarChart3`, `Award`). Landing.jsx lints clean.
  - Smoke-tested against preview URL — hero + picker + reports strip render correctly, all three deleted section titles verified absent.



- **Iteration 79 — Code Review Fixes v3 (2026-02-06)**:
  - **Reviewer's circular-import claim confirmed stale**: Verified via fresh module load that `deep_dive_narrative` imports only `pdf_base` (no back-reference to `edu_deep_report`). Cycle was broken in iteration 78 via the new `pdf_base.py` leaf module.
  - **Array index keys**: Fixed the one new file the reviewer flagged this round — `WeeklyEmailPreview.jsx:301` (milestones-this-week list) now uses a stable content-composite key.
  - **All other items are repeats from iter77/78** and were already dismissed with recorded rationale (`is None` PEP 8 idioms, test-only creds, non-sensitive localStorage keys like orientation-seen / verification-banner-dismissed, 149-count hook-deps blitz where the specifically-flagged files including `VerifySignature.jsx:24` and `AuthContext.jsx:91` all lint clean under `exhaustive-deps`, complexity/large-component refactors deferred to a future sprint per user approval option `a`).



- **Iteration 78 — Code Review Fixes v2 (2026-02-06)**:
  - **Circular import — fully broken** (real fix, not lazy-import workaround): New leaf module `pdf_base.py` holds `_safe`, `_section_break`, `LOGO_PATH`. `deep_dive_narrative`, `edu_deep_report`, and `journey_pdf` now all import from `pdf_base` at module top-level. `edu_deep_report` also imports `render_parts_narrative` from `deep_dive_narrative` (one-way). Verified via a clean-modules test: loading `deep_dive_narrative` only pulls in `pdf_base` — no back-reference to `edu_deep_report`.
  - **Array index keys** in 6 more files (this round's list): `SpecialNeedsV2CompareView.jsx:55` (list bullets), `LearningArticle.jsx:163/182/264` (paragraphs, takeaways, coach paragraphs), `Dashboard.jsx:1095` (snc highlights — now keyed by `section_id-item_id` when available), `SectionCoachCard.jsx:243` (bullet lines), `GrowthTracker.jsx:163` (insights — keyed by `ins.kind` when available).
  - **False positives skipped (documented rationale)**: `is None` (PEP 8 idiom), 149-count hook-deps blitz (lint-clean under `exhaustive-deps` on the flagged specific files including new `VerifySignature.jsx`), test-only creds, situation/celebration localStorage keys (non-sensitive), complexity/large-component refactors (categorised as future sprint).
  - 129/129 backend regression tests pass; all touched frontend files lint clean.



- **Iteration 77 — Code Review Fixes (2026-02-06)**:
  - **Circular import resolved**: Moved `render_parts_narrative` from `journey_pdf.py` to `deep_dive_narrative.py`. `edu_deep_report.py` and `journey_pdf.py` now both import it from a single downstream module — no more `edu_deep_report ↔ journey_pdf` back-reference. Verified with fresh module load; 96/96 regression tests pass.
  - **Empty catch blocks**: Added `logError` calls in `SpecialNeedsV2.jsx` (deep-dive dismiss read/write) and `Orientation.jsx` (orientation-seen flag) so storage failures show up in debug logs instead of failing silently.
  - **Array index keys**: Replaced `key={i}` with stable content-composite keys in 5 spots: `SharedCoParentingReport.jsx` (toolkit tips, findings, recommendations, next-steps), `SafetyAssessment.jsx` (recommendations list), `DeepDiveCompareView.jsx` (timeline bars), `GmailComposer.jsx` (tone notes).
  - **False positives noted**: `is None` in `wall_utils.py:188` / `wall_routes.py:181` is idiomatic Python (PEP 8) — skipped. `AuthContext.jsx:91` + `ReportShareControls.jsx:148` hook-deps already lint clean under `exhaustive-deps` — skipped. Hardcoded `TestPass123!` in test files is shared test-only cred — skipped per user approval (option `a`).



- **Iteration 76 — Gmail Unread Badge (2026-02-06)**:
  - New backend endpoint `GET /api/gmail/unread-count` — O(1) via the Gmail Labels API (INBOX label's `messagesUnread` / `threadsUnread`). Returns `{connected, unread_messages, unread_threads}`; gracefully degrades to `connected:false` on any Gmail/token error so the dashboard never sees a 5xx.
  - Frontend `GmailMiniInbox.jsx` fetches messages + unread count in parallel and renders a small red pill next to the "Recent messages" heading (`data-testid="gmail-mini-unread-badge"`, caps at "99+"). Hidden when count is 0.
  - 2/2 backend regression tests pass (`test_iter76_gmail_unread.py`).



- **Iteration 75 — Gmail Mini Inbox (2026-02-06)**:
  - New dashboard card `GmailMiniInbox.jsx` slotted right below the Situation Picker. Shows the 5 most-recent Gmail inbox messages when connected, or a compact "Connect Gmail" CTA when not. Tapping a row expands the full body inline (calls `GET /api/gmail/messages/{msg_id}`); tapping Reply opens the shared composer with the Coach-drafted reply flow available and pre-quotes the original message.
  - Refactor: extracted the modal composer from `pages/Gmail.jsx` into a shared `components/gmail/GmailComposer.jsx` so both the full page and the mini inbox reuse it.
  - 30-second auto-refresh + manual refresh button. Handles token-revoked (401) gracefully by flipping back to the connect prompt.
  - No backend changes — existing Gmail routes (`/api/gmail/status`, `/api/gmail/messages`, `/api/gmail/send`, `/api/gmail/draft-reply`) power the flow.
  - Smoke-tested logged-in as parent1 (disconnected state — CTA + href verified).



- **Iteration 74 — Milestone Confetti (2026-02-06)**:
  - **Milestone Confetti (P0)**: Fired a two-burst confetti + celebration toast the first time a parent's dashboard streak reaches **30** or **100** consecutive days. Uses `canvas-confetti@1.9.4` (yarn add), imported lazily so the bundle only pays the cost when the celebration actually fires. Respects `prefers-reduced-motion` via `disableForReducedMotion: true`. Once-per-device via `localStorage['sacop_celebrated_streaks_v1']` so the same threshold never celebrates twice. Wired into `ProgressDashboardCard` (which already fetches `/api/dashboard/progress` including `streak_days`).
  - New hook: `/app/frontend/src/hooks/useStreakCelebration.js` + 6 unit tests (`useStreakCelebration.test.js` — all pass).
  - No backend changes.



- **Iteration 73 — Wall Milestones Feed filter + Verify page polish (2026-02-06)**:
  - **Wall Milestones Feed (P0)**: Added category filter chip row on the Community Wall (`PublicMilestoneWall.jsx`). Chips: All, Streaks & badges (union), Streaks (week/month/hundred_day), Foundations (foundation_ready/first_compare/communication_master), Alignment (high_alignment_90). Each chip shows a live count. Backend `GET /api/wall/feed` accepts `?category=` and echoes the resolved category + `category_counts` dict. Unknown values fall back to "all". `CATEGORY_BADGES` lives in `wall_utils.py` as the single source of truth. Post-opt-in the frontend force-resets the filter to "all" so backfilled badges never hide under a stale chip. Cheer button (existing) confirmed to work under a filtered view.
  - **Verify Landing Polish (P0)**: Added `/verify/` to the LegalAcknowledgment exempt paths so QR scanners land directly on the Untampered ✓ card. Modal is already skipped on `/shared/` for the same reason — verify page carries its own disclaimer footer.
  - Regression tests: `/app/backend/tests/test_iter73_wall_filter.py` (6 tests) + `/app/backend/tests/test_iter73_wall_filter_live.py` (7 live tests via testing agent). Iteration 52 testing report: 100% pass rate, no critical or minor issues.



- **Iteration 72 — Narrative Rebuild, Long-Streak Badges, Signature QR (2026-02-06)**:
  - **Narrative Rebuild (P0)**: Both v2 Educational and Psychological Deep Dive reports now return `parts_narrative` (5 items — one per part), `opening_story`, and `closing_story`. Each per-part item includes score/band/band_headline, band-driven prose, up to 2 concrete strengths (items scored 3-4), up to 2 growth items (items scored 0-1), and a child-focused reflection line. Shared helper: `deep_dive_narrative.py`. PDF export via `journey_pdf.render_parts_narrative`. Frontend component: `DeepDivePartsNarrative.jsx` — the retired v2 "coming next iteration" banners are gone on both report pages.
  - **Long-Streak Badges (P0)**: Added `month_streak_30` (30-day) and `hundred_day_streak` (100-day) wall badges — both lifetime-deduped. Wired into `progress_dashboard_routes.mark_visit` alongside the existing `week_streak_7`. Shown in the wall feed and included in the weekly Cheer Digest via `BADGE_LABELS`. Helpers: `maybe_log_month_streak`, `maybe_log_hundred_day_streak` in `wall_utils.py`.
  - **Signature QR (P0)**: Every signed PDF now stamps a 12x12mm QR (with "Scan to verify" micro-label) beside the signature line. The QR resolves to `/verify/{sig_id}?n=<name>&t=<ts>&note=<note>` where `sig_id = sha256("SIGNATURE_VERIFY_SECRET|name|ts|note")[:16]`. Any tampering with the URL params breaks the hash. New `GET /api/verify/{sig_id}` endpoint (in `signature_verify_routes.py`) re-hashes and returns `{untampered: bool, signed_by, signed_at, signed_note}`. New public React page `/verify/:sig_id` displays a green "Untampered ✓" card or a red "Could not verify" card. QR generation via `qrcode[pil]==8.2` — added to `requirements.txt`.
  - Regression suite `/app/backend/tests/test_iter72_narrative_streak_qr.py` — 16 tests, all pass. Testing agent iteration 51 also passed 23/23 live-API + full frontend flow.



- **Iteration 71 — Compare Matrix, Framework PDF link, Situation dual highlight (2026-02-06)**:
  - **Compare Matrix (P0)**: Added a compact 25-question side-by-side matrix on the Educational + Psychological Deep Dive compare views (opt-in via `pathway.showMatrix`). Rendered above the per-section detail cards, grouped by the 5 parts, with columns: #, Question, Parent A score, Parent B score, Gap pill (0-1 green / 2 purple / 3-4 red) and a legend. Only numeric (`alignment`/`likert`) items render; sections without numeric items are skipped. Medical compare intentionally opts out.
  - Component lives inline in `/app/frontend/src/components/deepdive/DeepDiveCompareView.jsx` (`AlignmentMatrix` + `GapCell`). Testids: `edu-deep-compare-matrix`, `psych-deep-compare-matrix`, `-matrix-legend`, `-matrix-section-<id>`, `-matrix-row/-a/-b/-gap-<section>-<item>`.
  - **Framework PDF Link (P0)**: Added a highlighted callout on `/special-needs-v2/psychological-deep-dive/report` linking directly to `/downloads/coparenting_psychological_alignment_framework.pdf` (target `_blank`). Rendered both on the report body AND the "No report available yet." empty state, so parents can always print/share the framework. Testid `psych-report-framework-pdf-link`.
  - **Situation → Psych Mapping (P0)**: `SITUATION_TO_RECOMMENDED_MODULE` renamed to `SITUATION_TO_RECOMMENDED_MODULES` (array-of-strings map). Selecting "special-needs" on the Dashboard Step 1 hero now highlights BOTH the Educational Assessment AND Psychological Assessment prep-module tiles (previously only Educational). Other situations keep single-module highlight. Dashboard render uses `recommendedModules.includes(m.key)` so adding future multi-highlights is a one-line schema change.
  - Frontend-only iteration. Testing agent iteration 50 verified all three items (dual-highlight badges via localStorage, PDF HEAD 200, compare pages render without JS errors + Medical opts out).


## Status snapshot (2026-07-30 · v2 shipped)

- **Iteration 70 — Psychological Deep Dive rebuilt as Co-Parenting Psychological Alignment Framework (2026-02-05)**:
  - Retired v1 11-section 60-item schema. New `psych-deep-2.0.0` schema: 5 parts × 5 items × 0-4 alignment likert with N/A pro-rating. Total /100 + three bands (High 81-100, Moderate 51-80, Low 0-50). Parts: (1) Emotional Regulation Between Parents, (2) The Child's Emotional Environment, (3) Therapy & Mental-Health Coordination, (4) Trauma, Grief & Attachment, (5) Modelling Emotional Health for the Child.
  - Backend rewritten: `psych_deep_questions.py` (v2 schema + `is_v2_key`), `psych_deep_scoring.py` (score card with band summary + next-steps), `psych_deep_journey.py` (score-card journey with rating areas + action plan + foundation statement), `psych_deep_report.py::build_deep_dive_report` returns v2 shape.
  - `psych_deep_routes.py::/me` silently strips legacy v1 keys and marks `completed=false` on first load.
  - Frontend `SpecialNeedsV2PsychologicalDeepDive.jsx` supports the 0-4 scale from `item.scale` with the same yellow scale-legend callout as the Educational v2 page. `SpecialNeedsV2PsychologicalDeepDiveReport.jsx` shows a first-fold Score Card (total /100, band pill, per-part progress bars, next-steps + v2 rollout banner).
  - Standalone fillable PDF at `/downloads/coparenting_psychological_alignment_framework.pdf` (8 pages, 193 real AcroForm widgets — 40 text + 153 checkboxes covering the 25 items, results table, band selector, and signatures). Built by `/app/scripts/build_psychological_alignment_framework.py`.
  - Retired `test_psych_deep.py` + `test_psych_deep_api.py` with a pointer to the new suite. `test_iter70_psych_v2.py` adds 27 dedicated tests (schema, validate, banding boundaries, N/A pro-rating, backwards-compat shape, legacy wipe, journey shape).
  - 264 passed / 7 skipped across iter42-70 + psych/edu/wall/analytics. Frontend smoke test on `/special-needs-v2/psychological-deep-dive` confirmed the new page renders with the scale legend, 0-4 buttons, N/A, and 5-part navigation.



- **Iteration 69 — Situation Memory + ADHD Addendum PDF (2026-02-05)**:
  - **Situation Memory**: The Step 1 hero on `/dashboard` now remembers the parent's picked situation in `localStorage['sacoparents_situation_choice_v1']`. On return visits the hero collapses into a "You chose: {label}" chip + a "Change my answer" reset button instead of re-showing the six-choice grid. The matching prep module in the Preparation Modules card is highlighted with a bold purple border + a "Recommended for you" badge (mapping: cooperate/difficult/mediation → Mediation Summary · high-conflict/safety → Family Violence & Safety · special-needs → Educational Assessment).
  - **ADHD Addendum PDF**: New standalone fillable PDF (`/downloads/coparent-adhd-addendum.pdf`) at `/app/scripts/build_adhd_addendum_template.py`. 7 pages, 85 real interactive AcroForm widgets (41 text fields + 44 checkboxes). Six sections: IEP & ARD Management, Accommodations Held in Both Homes, ADHD Medication Coordination, Transitions & Executive-Function Support, Communication Between Us, Review & Signatures. AI-rated 10/10 per page for print + fillability. Reuses the layout primitives from the Commitment Agreement template.
  - No backend changes; lint clean.



- **Iteration 68 — Dashboard "Step 1" situation opener + Preparation Modules jump-menu (2026-02-05)**:
  - Replaced the generic time-of-day greeting ("Good morning demo") with a dedicated hero card labelled **Step 1** — "What best describes your situation, {name}?" — surfaced as the first thing above the fold on `/dashboard`. Mirrors the Landing-page opener exactly (six choices: We generally cooperate · Communication is difficult · Ongoing high conflict · Safety/family-violence concerns · Special-needs child · Preparing for mediation).
  - Three of the six choices navigate directly (`/safety-assessment`, `/special-needs-v2`); the other three route to `#next-step` (the NextStepJourney anchor lower on the same page).
  - Added a new **Preparation Modules** jump-menu card below NextStepJourney listing the six documents the app can build a PDF for — Declaration Statement, Mediation Summary, Family Violence & Safety Assessment, Educational Assessment, Medical Assessment, Psychological Assessment — each a one-tap deep link.
  - The old "Your space" hero card (day-of-prep chip + progress bar + step checklist) stays inside the "Explore more tools" collapsible with the plain time-of-day greeting restored (test-id `dashboard-greeting-secondary`).
  - No backend changes; 54/6 pytest across iter51-67 still green.



- **Iteration 67 — Educational Deep Dive rebuilt as Special-Ed / ADHD Alignment Assessment (2026-02-05)**:
  - Retired the v1 12-section 60-item diagnostic. Replaced with a 5-part 25-item 0-4 likert alignment scorer, total /100 with three bands (High 81-100, Moderate 51-80, Low 0-50). Focus areas: Emotional Well-being, Communication, IEP/ARD, ADHD Routines, Logistics.
  - Backend files rewritten: `edu_deep_questions.py` (schema `edu-deep-2.0.0` + `is_v2_key`/`validate_answer`), `edu_deep_scoring.py` (`score_deep_dive` returns total/percent/band/next_steps/sections + backwards-compat `totals`/`is_texas`), `edu_deep_journey.py` (v2 score-card journey with rating areas, action plan, foundation statement), `edu_deep_report.py::build_deep_dive_report` now consumes v2 shape.
  - `edu_deep_routes.py::/me` silently strips legacy v1 answers and marks `completed=false` on first load so nothing crashes.
  - `deep_dive_comparison_core.py` treats the new `alignment` item type as numeric (equivalent to v1 `likert`) via `_is_numeric_type` helper — so compare / snapshot / preview / milestones all keep working.
  - Frontend `SpecialNeedsV2EducationalDeepDive.jsx` renders a 0-4 alignment scale (from `item.scale`) with a soft yellow scale-legend callout. `SpecialNeedsV2EducationalDeepDiveReport.jsx` adds a first-fold Score Card (total, band pill, per-part progress bars, next-steps card + a "new format, full narrative coming next iteration" banner).
  - Retired tests: `test_edu_deep.py`, `test_edu_deep_live.py` skip with a pointer to the new suite. `test_iter67_edu_v2.py` adds 34 new tests (schema, validate_answer, banding boundaries, N/A pro-rating, backwards-compat shape, legacy wipe, journey shape). Test fixtures in iter45/46/48/50/52 patched to accept both `likert` and `alignment` item types with `max(scale)`.
  - Verified via `python -m pytest`: 288 passed, 7 skipped across iter42-67 + growth/analytics/shared-cp/snc2-compare/wall_utils. Frontend smoke test on `/special-needs-v2/educational-deep-dive` confirmed the new page renders with the scale legend, 0-4 buttons, N/A, and 5-part navigation.
  - Backlog for next iteration: rebuild the rich narrative journey to fit the 25-item shape; add the compare-view 25-question matrix; add the "Special Education & ADHD Addendum" companion PDF.



- **Iteration 66b — Wall Cheer Digest (2026-02-02)**:
  - Added an anonymised community cheer block to the existing Sunday weekly email (kept as one email per week — no new outbound). Two data streams:
    * `cheers_received` — for opted-in parents only. Counts hearts landed on their own badges in the last 30 days that got cheered *this week*. Cheerer identity is NEVER exposed.
    * `community_pulse` — up to three most-cheered anonymous badges earned by *other* parents this week. Shown to opted-in AND opted-out parents so opted-out folks still feel the momentum.
  - Backend: new `wall_utils.build_weekly_cheer_digest(db, user_id, week_start)` returns `{opted_in, cheers_received, community_pulse, week_start}`. `_build_weekly_email_context` merges the digest into the preview + send payloads (`wall_opted_in`, `cheers_received`, `cheers_received_total`, `community_pulse`). `send_weekly_progress_summary` in `email_service.py` renders a pink "Community cheers" / "From the community" card in both HTML and plain-text — silently omitted when both lists are empty.
  - Frontend: `WeeklyEmailPreview.jsx` renders the same block below the milestones list. Header switches to "From the community" for opted-out users. Test IDs: `weekly-email-preview-cheers`, `weekly-email-preview-cheers-received`, `weekly-email-preview-community-pulse`.
  - Regression: `test_iter66_cheer_digest.py` — 11 new tests (5 helper-unit, 2 preview-endpoint, 1 send-endpoint, 3 email-service render). All pass; 50/50 pass across iter54/55/56/57/66 + wall_utils_regression combined.


- **Iteration 66 — Code Quality Report fixes (2026-02-02)**:
  - Resolved the circular import between `wall_routes.py` ↔ `progress_dashboard_routes.py`. Extracted anon hashing, log-event-once machinery, `BADGE_LABELS` constants, and the five `maybe_log_*` helpers into a new `wall_utils.py`. `wall_routes` now imports from `wall_utils` and lazy-imports `compute_progress` inside the `/wall/opt-in` endpoint only. `progress_dashboard_routes` and `deep_dive_compare_router_factory` import from `wall_utils` at load time. `wall_routes.__all__` re-exports the helpers for backwards compat.
  - Frontend: removed 9 dead `eslint-disable-next-line react-hooks/exhaustive-deps` / `no-console` directives across `Summary.jsx`, `Reflection.jsx`, `ReadinessCheck.jsx`, `InviteCoparentCard.jsx`, `AdminInsights.jsx`, `PriorityRanking.jsx`, `VerifyEmail.jsx`, `index.js`, `lib/logger.js`. Filled the one empty `catch {}` in `AlignmentMilestoneCelebration.jsx` with an explanatory comment.
  - Verified via `testing_agent_v3_fork` (iteration_49.json): 12 new regression tests in `test_wall_utils_regression.py` all pass, iter54/55/56 (20 tests) still pass, `/dashboard` renders the three-block layout cleanly (dashboard-greeting, progress-bar, continue-button etc.), zero console/pageerrors, all wall/progress/weekly-email endpoints return 200.
  - Noted as false positives in the report and skipped (not real issues): `is None` in `wall_routes.py:166,311` is correct Python idiom; `TestPass123!` in `tests/*.py` is a fixture, not a leaked secret; `personal_analytics` and the `ai_service.py` prompt builders are readable single-responsibility functions where a "complexity refactor" would just move code into helpers that are called once — violates DRY-vs-YAGNI.



- **Iteration 65 — Sign With Notes (2026-02-02)**:
  - Extended the "Sign & timestamp this download" flow so parents can also add a **one-line signing note** (e.g. *"Prepared for our 12 Feb mediation session"*) that prints in italics just above the bold signature line on every content page of the PDF.
  - Frontend: `SignDownloadToggle.jsx` now renders an inline text input the moment the sign checkbox is ticked, capped at 120 chars with a live "N chars left · appears above your signature on every page" counter. Backwards-compatible: callers passing only `{ checked, onChange }` keep old behaviour; new `note` + `onNoteChange` unlock the note field. Wired into all 8 report/compare surfaces (SNC, 3 deep-dives, Mediation Summary, Agreement, SNC Compare, Deep-Dive Compares).
  - Backend: `pdf_signing.sign_kwargs(sign, name, note)` now returns `signed_note` when the note is non-empty; silently trims + clamps to 120 chars. `pdf_watermark.stamp_signature_line(pdf)` reads `pdf._signed_note` and renders an italic note line above the signature, with its own thin grey rule; layout uses a two-line stack when a note is present and stays single-line otherwise. Every builder (`build_summary_pdf`, `build_agreement_pdf`, `build_snc2_pdf`, `edu/psych/med build_deep_dive_pdf`, `build_journey_pdf`, both `build_comparison_pdf`) now accepts the `signed_note` kwarg. Every download endpoint now accepts `?sign=true&note=...`.
  - Regression: `test_iter65_signing_notes.py` — 14 new tests covering `sign_kwargs` semantics (whitespace-only rejection, 500-char clamp to 120, no-sign zero-out, note-alone absence), plus note-in-PDF end-to-end for all 8 builders. **78/78 backend tests pass** across iter56/57/58/63/64/65 + SNC v2 suites. Gemini-verified visual: both italic note + bold signature lines render, correctly stacked, no collision with page number, watermark still visible.

- **Iteration 64 — Signed PDF Downloads (2026-02-02)**:
  - New opt-in **"Sign & timestamp this download"** checkbox next to every Download PDF button. When toggled, the backend adds a small `Signed by <Parent Name>  |  <UTC timestamp>` line just above the standard page-number footer on every content page — right under the diagonal "REVIEW BEFORE SHARING" watermark so a shared PDF carries clear provenance without a separate cover sheet.
  - Backend:
    - `pdf_watermark.stamp_signature_line(pdf)` — new helper. Reads `pdf._signed_by` + `pdf._signed_at`; renders a thin grey rule + centred bold-purple signature line at `y = pdf.h - 6.0`. Latin-1 safe, restores font/colour state.
    - `pdf_signing.sign_kwargs(sign, name)` — one-liner helper: returns `{"signed_by": name, "signed_at": UTC ISO}` when both `sign=true` and a name are present, `{}` otherwise. Timestamp is captured at download time.
    - Every builder (`pdf_service.build_summary_pdf`/`build_agreement_pdf`, `snc2_report_pdf.build_snc2_pdf`, `edu_deep_report.build_deep_dive_pdf`, `journey_pdf.build_journey_pdf` — which serves both psych + med, `snc2_comparison_pdf.build_comparison_pdf`, `edu_deep_comparison_pdf.build_comparison_pdf`) now accepts `signed_by` + `signed_at` kwargs and stashes them on the PDF instance before the first `add_page()` so headers/footers pick them up.
    - Every download endpoint accepts `?sign=true`: `/api/mediation/summary/{id}/pdf`, `/api/mediation/agreement/{id}/pdf`, `/api/snc2/report/pdf`, `/api/edu-deep/report/pdf`, `/api/psych-deep/report/pdf`, `/api/med-deep/report/pdf`, `/api/snc2/compare/{share}/pdf`, and all three deep-dive compare `{share}/pdf` endpoints via the shared router factory.
  - Frontend:
    - New shared `SignDownloadToggle.jsx` component — a tiny checkbox with a `PenTool` icon and native `title` tooltip explaining what signing does. Zero API coupling; consumers own the state.
    - Wired into 8 report/compare surfaces: `SpecialNeedsV2Report`, `SpecialNeedsV2EducationalDeepDiveReport`, `SpecialNeedsV2PsychologicalDeepDiveReport`, `SpecialNeedsV2MedicalDeepDiveReport`, `Summary` (Mediation Summary + Agreement tabs), `SpecialNeedsV2CompareView`, and the shared `DeepDiveCompareView`. Toggle sits below the Download button on each. Test IDs: `<pathway>-sign-toggle`, `<pathway>-sign-toggle-checkbox`.
    - Every `download*` handler now appends `?sign=true` (or the axios `params: { sign: true }` variant) when the toggle is checked and toasts "Signed & downloaded." on success.
  - Regression: `test_iter64_signed_pdfs.py` — 11 new tests covering signed+unsigned parity across all 7 PDF surfaces (byte-level and zlib-stream inspection). **All 64/64 backend tests pass** across iter56/57/58/63/64 + SNC v2 suites. Gemini-verified visual: signature line visible on every content page, correct format (`Sam Nkosi | 02 Aug 2026, 16:52 UTC`), does not clash with page number, watermark still renders correctly, cover pages remain clean.

- **Iteration 63 — PDF "REVIEW BEFORE SHARING" Watermark (2026-02-02)**:
  - New `pdf_watermark.py` shared helper `stamp_watermark(pdf)` that draws a subtle diagonal `REVIEW BEFORE SHARING` watermark behind every content page across every PDF the app generates. Rendered via `fpdf2.rotation(angle=30, x=cx, y=cy)` + `pdf.text()` at ~48pt in light grey (RGB 215/210/220) so body text stays fully readable on top.
  - Wired into six FPDF subclasses' `header()`:
    * `PrepSummaryPDF` (mediation summary) — respects the existing `_chromeless` flag so poster cover pages remain watermark-free
    * `AgreementPDF` (neutral draft agreement)
    * `_PDF` in `snc2_report_pdf.py` (Special Needs report)
    * `_PDF` in `edu_deep_report.py` (Educational deep dive)
    * `_JourneyPDF` in `journey_pdf.py` (Psychological + Medical deep dives — one wire-in serves both)
    * `_PDF` in `snc2_comparison_pdf.py` (SNC compare)
    * `_PDF` in `edu_deep_comparison_pdf.py` (all three deep-dive compares)
  - Header state is snapshotted + restored (font family/style/size, XY, text color) so no downstream layout ever shifts.
  - Regression: `test_iter63_pdf_watermark.py` — 7 watermark presence tests (one per PDF surface) + 1 sanity check that iter62's provenance footer still renders after the watermark was layered under it. Detection uses raw PDF byte-search for uncompressed streams and `/FlateDecode` decompression + substring search for compressed ones. **53/53 backend tests pass** (previous 45 + new 8). Gemini-verified visual: watermark clearly visible but subtle, correct diagonal orientation, body text fully readable, NOT rendered on poster cover pages, no rendering glitches.

- **Iteration 62 — PDF Provenance (2026-02-02)**:
  - Mirrored the on-screen `ReportProvenanceFooter` inside every downloadable PDF so recipients (mediators, therapists, attorneys) see the same "How this report was built" breakdown.
  - New shared `pdf_provenance.py` with `render_provenance_footer(pdf, variant=…)` — accepts any FPDF-compatible subclass, latin-1 safe, four variants (`mediation` | `snc` | `deepdive` | `comparison`), colour-coded pills (green **RULE-BASED**, gold **GENERATIVE**), with the same explainer paragraph as the React footer.
  - Wired into six PDF surfaces:
    * `pdf_service.build_summary_pdf` (Mediation Summary — added on its own page before the closing poster)
    * `pdf_service.build_agreement_pdf` (Neutral Draft Agreement)
    * `snc2_report_pdf.build_snc2_pdf` (Special Needs Report)
    * `edu_deep_report.build_deep_dive_pdf` (Educational Deep Dive)
    * `journey_pdf.build_journey_pdf` (Psychological + Medical Deep Dives — one wire-in serves both)
    * `snc2_comparison_pdf.build_comparison_pdf` (SNC v2 co-parent compare)
    * `edu_deep_comparison_pdf.build_comparison_pdf` (all three deep-dive compare PDFs)
  - Verified via unit builds of all 6 generators (each produces valid `%PDF` bytes) + a Gemini-based content check of the SNC v2 sample: eyebrow present, 3+3 counts correct, all 6 rows show the right colour pill and text, explainer paragraph verbatim.
  - Regression: **45/45 backend tests pass** across iter56/57/58 + the entire SNC v2 + comparison suite (the SNC PDF regression touches the new code path and still passes).

- **Iteration 61 — Dashboard IA Restructure + Report Provenance (2026-02-02)**:
  - **New three-block above-the-fold Dashboard** per user's audit item #1: `Do This Next` (NextStepJourney) → `Your Progress` (ProgressDashboardCard with 5 milestones + streak) → `Your Reports` (new). Everything else lives inside a single collapsible "Explore more tools — community, weekly email, learning center, and more" pill toggle (`dashboard-explore-more-tools`) — kept, not removed, so a stressed parent's first fold stays focused.
  - **`YourReportsCard.jsx`** — new compact launcher (`your-reports-card` testid) with one row per report:
    * Mediation Summary (always visible; Ready / Not started)
    * Special Needs Report (only when SNC assessment exists; Ready / In progress)
    * Educational / Psychological / Medical deep-dive reports (each surfaces only when the corresponding deep dive has been started; Ready / In progress with `N answered` count)
    * Co-Parent Comparison (only when a share is active or ready-to-view)
    Each row has a state pill (Ready/In progress/Not started), colour-coded, plus `Open/Continue/Start` CTA. Wired to the actual live data shapes from `/snc2/report/status`, `/deep-dives/status`, `/deep-dives/compare-status`.
  - **`ReportProvenanceFooter.jsx`** — new "How this report was built" collapsed footer added to every report page (Mediation Summary, SNC Report, Educational/Psychological/Medical Deep-Dive Reports, SNC Compare View, and the shared DeepDiveCompareView). Four variants (`mediation` / `snc` / `deepdive` / `comparison`) each list which sections are Rule-based (deterministic, colour-coded green) vs Generative (technology-assisted via Claude, colour-coded gold), with a friendly explanation that parents remain responsible for reviewing every part. Test IDs: `report-provenance-footer`, `report-provenance-toggle`, `report-provenance-body`, `report-provenance-row-rule`, `report-provenance-row-generative`.
  - Regression: 24/24 backend tests still green; frontend lint clean; verified live via preview screenshots of the new dashboard first-fold + the expanded "Explore more tools" section + the Educational Deep Dive report provenance footer (rule-based + generative rows rendering with correct colour pills).

- **Iteration 60 — Copy + Trust Polish (2026-02-02)**:
  - **Homepage "Three Reports" strip** (`Landing.jsx`) rewritten as "Three core reports — plus specialized reports based on your family's needs" with an explanatory sub-paragraph, so the homepage no longer contradicts the Special Needs pathway's additional reports.
  - **Deep-dives optional banner** — a prominent green-bordered notice added above the deep-dive CTAs on `/special-needs-v2` picker (`snc2-deep-dives-optional-banner`): "Your core Special Needs Assessment is enough on its own… the three deep dives are OPTIONAL."
  - **AI language sanitised**. "AI-synthesized, mediator-ready, downloadable PDF" and "Three AI-synthesized views" on the Dashboard/Summary swapped for the safer, professionally-worded "structured, child-focused report with technology-assisted drafting… You remain responsible for reviewing…"
  - **`ReportReviewNotice` component** shipped as a shared warm-gold callout with two variants:
    - `individual`: *"Review this report carefully before sharing it. It reflects one parent's responses and has not been independently verified."*
    - `comparison`: *"This report organizes both parents' reported perspectives side-by-side. It does not determine which account is correct."*
    Wired into: `Summary.jsx`, `SpecialNeedsV2Report.jsx`, `SpecialNeedsV2EducationalDeepDiveReport.jsx`, `SpecialNeedsV2PsychologicalDeepDiveReport.jsx`, `SpecialNeedsV2MedicalDeepDiveReport.jsx` (individual), plus `SpecialNeedsV2CompareView.jsx` and the shared `DeepDiveCompareView.jsx` (comparison). Test IDs: `report-review-notice-individual` / `report-review-notice-comparison`.
  - **"Child-focused" brand sweep** across all `.jsx`/`.js` (~35 replacements): child-centered / child-centred / Child-Centered / etc. globally standardised to child-focused / Child-Focused. Includes module labels ("Child-Focused Goals"), section headings ("Section B — Child-Focus" in Readiness Check), copy across Landing, Dashboard, Summary, Methodology, Terms, Privacy, Delete Account, Learning Center, Watch, Orientation, Progress, InviteAccept, MediatorBadge, ProblemSolvingWorksheet, ReadinessCheck, FivePillarJourney, NextStepJourney, BadgeShelf, SharedCoParentingReport, and every Special-Needs deep-dive report.
  - **Production build hardening**: `GENERATE_SOURCEMAP=false` added to `frontend/.env` so React source maps are no longer publicly exposed on production once redeployed.
  - **Structured data correction**: `public/index.html` schema.org `WebApplication.operatingSystem` changed from misleading "Web, iOS, Android" to "Web (progressive web app installable on supported iOS and Android devices)".
  - Regression: 24/24 tests still pass across iter56 + iter57 + iter58; no backend behaviour touched. Frontend lint clean on all new/modified files.

- **Iteration 59 — Learning Center (2026-02-02)**:
  - New `/learning` route + full library of 15 hand-authored short reads (~2-3 min each) grouped into three hubs matching the assessment structure: **Child-centred communication**, **Healthy boundaries**, and **Mediation prep** (5 articles per hub). Every article has: hero summary, 300-500 word body, 3 "things to try this week" takeaways.
  - Backend: new module `learning_content.py` holds the static seed (swap-out later to Mongo without touching routes), and `learning_routes.py` exposes:
    * `GET /api/learning/hubs` — full index + per-user read state
    * `GET /api/learning/hub/{hub}/article/{slug}` — full body + per-user read + cached AI expansion state
    * `POST /api/learning/hub/.../read` and `DELETE .../read` — mark/undo with idempotent hub progress in the response
    * `GET /api/learning/progress` — compact per-hub summary for the dashboard entry card
    * `GET /api/learning/search?q=...` — keyword match across titles/summaries/bodies
    * `POST /api/learning/hub/.../coach {force}` — **AI depth expansion via Claude Sonnet 4.5** (uses the Emergent LLM key). Returns exactly three paragraphs (example / common pitfall / one weekly practice). Cached per user per article forever unless `force=true` since seed content is static; failure returns 503 with a friendly toast so the article still stands on its own.
  - Frontend:
    * `LearningCenterCard.jsx` mounted on `/dashboard` under the Weekly Email Preview — book-icon eyebrow, per-hub 3-column mini-grid with accent dots, running "N/15 read" progress bar, Explore/Continue CTA (`data-testid="learning-card"`).
    * `LearningCenter.jsx` at `/learning` — three hub sections with tagline pills, per-article rows (Circle/CheckCircle read state + 2-min clock + hover-to-arrow).
    * `LearningArticle.jsx` at `/learning/:hubSlug/:articleSlug` — clean prose layout, "Mark as read" toggle with toast, purple "3 things to try this week" panel, gold "Ask the coach for more depth" panel with Ask/Loading/Error/Body/Regenerate states, Back links top + bottom.
  - Milestone-neutral by design (per user choice) — no dashboard pill impact, no wall badges, no confetti. Learning Center is its own space.
  - New Mongo collections: `learning_reads`, `learning_ai_expansions`.
  - Tests: `test_iter58_learning_center.py` — 8/8 pass (hubs index shape, per-user progress, article fetch + 404s, mark/unmark round-trip + idempotency, cross-hub aggregation, keyword search, empty search). AI expansion smoke-tested via curl (returns 3 Claude-authored paragraphs, cached on second call). All 16 iter56 + iter57 regressions remain green.

- **Iteration 58 — Preview Custom Message / Handwritten Weekly Note (2026-02-02)**:
  - Parents can now attach a short handwritten note (max 280 chars, tweet-sized) to the upcoming Sunday weekly email. Note is ISO-week scoped and auto-clears once the Sunday email fires, so each week starts fresh.
  - New backend endpoints on `progress_dashboard_routes.py`: `GET /api/dashboard/weekly-email/note` returns `{note, updated_at, week_key, max_chars}`; `POST /api/dashboard/weekly-email/note {note}` saves/clears (empty or whitespace clears; oversize silently truncated). New Mongo collection `weekly_progress_email_notes` (composite key: `user_id + week_key`).
  - Weekly email context now carries `personal_note` + `personal_note_updated_at`; `_build_weekly_email_context` reuses `_fetch_weekly_note` so preview + send stay in sync.
  - `email_service.send_weekly_progress_summary` accepts `personal_note`, escapes it, and renders it in a warm cream/gold "A note from you" card using a cursive stack (Caveat / Bradley Hand) above the milestone block. Plain-text alternate wraps the note in curly quotes for parity.
  - After a successful send, the note doc for that week is deleted (auto-reset). Send response now includes `personal_note_included: bool`.
  - Frontend `WeeklyEmailPreview.jsx`: new Post-it style composer inside the expanded preview card — cursive textarea (280 char cap with live counter, "N chars left" turns red over limit), disabled `Save note` button until dirty, "Saved" flash + toast on save, dashed-border preview line rendering the saved note in the same cursive as the email. Clears cleanly with an empty submit.
  - Tests: new `test_iter57_weekly_note.py` (7 cases: empty default, save/read round-trip, whitespace-clears, oversize truncation, preview surfaces note, send includes + clears note, send-without-note flag). All 7 pass. Regression `test_iter56_features.py` remains 9/9 green.

- **Family Report:** fully removed at user request.
- **Special Needs Co-Parenting v1** (13-section flat product): fully deleted per user's "replace it" directive. Backend routes `/api/snc/*`, frontend `/special-needs*` pages, comparison + invite endpoints, associated tests, sample PDFs, and MongoDB collections `snc_assessments`, `snc_reports`, `snc_invites`, `snc_comparisons` all removed.
- **Special Needs Co-Parenting v2** shipped at `/special-needs-v2`. Category-gated (Medical / Educational / Psychological or Behavioural / Multiple) 8-step assessment. **Report reshaped (2026-07-30) to the 9-section polished framework**: Report Introduction · Family Situation · Areas of Need · Co-Parenting Strengths · Co-Parenting Challenges (4-part cards) · Child Impact Summary · Detailed Findings by Category (Strength / Developing / Needs Attention / Priority Concern / Professional Guidance Recommended status system) · Parent Alignment Summary · Recommended Co-Parenting Structure (Cooperative / Structured / Parallel or Professionally Supported — safety-aware).
- **Mobile UX**: assessment is fully phone-usable — 5-column numeric rating buttons, sticky bottom Prev/Save/Next nav, 44 px+ tap targets, high-contrast selected states.
- **Landing situation picker (2026-07-30)**: added new option "I have concerns for my child's educational, medical or psychological needs" that starts a guest session and routes directly to `/special-needs-v2` (icon: Baby; testid `situation-special-needs`; focus key `special-needs`).
- **SNC v2 Co-Parent Compare (2026-07-30)** shipped. New backend module `snc2_comparison.py` (neutral alignment builder), `snc2_comparison_pdf.py` (branded PDF), `snc2_comparison_routes.py` mounted at `/api/snc2/compare/*`. Consent-first: both parents must opt in; safety guardrail hard-blocks any consent or view when the requesting parent's latest Safety Assessment is level 1 or 2 (reads `result.level` from `safety_assessments`). Frontend pages `SpecialNeedsV2Compare.jsx` (hub) and `SpecialNeedsV2CompareView.jsx` (view + category filter + PDF download); entry buttons on the assessment page and the report page (testids `snc2-open-compare`, `snc2-report-open-compare`). New Mongo collection `snc2_shares`. Tests: `tests/test_snc2_comparison.py` (9) + `tests/test_snc2_compare_api.py` (18) — all passing after testing agent caught + fixed a critical nested-field bug in `_latest_safety_level` that had left all three safety guardrails fail-open.
- **SNC v2 Compare Highlights (2026-07-30)** shipped. Added a "5 things you already agree on" section to the top of the shared comparison — surfaces in the JSON payload (`comparison.highlights[]`), the branded PDF, and the frontend view (data-testid `snc2-compare-highlights` + `snc2-compare-highlight-{i}`). Neutral scoring rules: only items with real shared agreement (likert avg >=3 + gap <=1, multi-select with shared choices, matching single-selects, or both-parents-wrote-text) qualify; later workflow steps rank slightly higher.
- **Educational Needs Deep Dive (2026-07-30)** — new optional 12-section companion product at `/special-needs-v2/educational-deep-dive`. Backend: `edu_deep_questions.py` (12-section schema with Texas-gated ARD Section 3 and IEP/504/counsellor gates for Sections 4/5/6), `edu_deep_scoring.py` (rule-based concern detection using likert averages, decision-topic Rarely/Never Agree counts, and gate visibility), `edu_deep_report.py` (report builder that only surfaces flagged + strength sections + branded Letter PDF), `edu_deep_routes.py` at `/api/edu-deep/*`. Frontend: `SpecialNeedsV2EducationalDeepDive.jsx` (12-section UI with progress dots, sticky nav, per-item option chips) and `SpecialNeedsV2EducationalDeepDiveReport.jsx` (polished report + PDF download). Entry via CTA card `snc2-edu-deep-dive-cta` on `/special-needs-v2`. Mongo collections: `edu_deep_assessments`, `edu_deep_reports`. Tests: `tests/test_edu_deep.py` (16 unit) + 9 live E2E from testing agent = 25 passing, plus SNC v2 regression suite (79 passed) intact.
- **Psychological / Behavioural Deep Dive (2026-07-30)** — mirroring the Educational Deep Dive architecture. New optional 11-section companion product at `/special-needs-v2/psychological-deep-dive`. Backend: `psych_deep_questions.py` (11 sections with medication gate on s4 and therapy gate on s6), `psych_deep_scoring.py` (frequency/confidence/consistency maps convert answer labels to likert-equivalent scores; s10 counts Rarely/Never Agree decisions), `psych_deep_report.py` (report builder + subclassed `_PsychPDF` with psychological-specific header), `psych_deep_routes.py` at `/api/psych-deep/*`. Frontend: `SpecialNeedsV2PsychologicalDeepDive.jsx` (11-section UI cloned from Edu with Texas gate removed) and `SpecialNeedsV2PsychologicalDeepDiveReport.jsx` (report with diagnoses + providers as chips). Entry via new dual-CTA grid on `/special-needs-v2` (`snc2-edu-deep-dive-cta` + `snc2-psych-deep-dive-cta`) and top-toolbar link `snc2-open-psych-deep-dive`. Mongo collections: `psych_deep_assessments`, `psych_deep_reports`. Tests: `tests/test_psych_deep.py` (10 unit) + 11 live E2E from testing agent = 21 passing. Total SNC v2 family regression at 87 green.
- **Medical · Prescription & Medication Coordination Deep Dive (2026-07-30, iteration 41)** — third deep dive shipped as a standalone Medical Needs product at `/special-needs-v2/medical-deep-dive`. Ten sections: (1) Prescription Information Sharing, (2) Prescription Pick-Up, (3) Medication Supply Between Homes, (4) Medication Administration, (5) Parent-to-Parent Communication, (6) Pharmacy Coordination, (7) Financial & Insurance Barriers, (8) Controlled Medication Accountability (gated by `has_controlled=Yes`), (9) School Medication Coordination (gated by `school_meds=Yes`), (10) Medication Decisions & Disagreements. Option-based questions throughout with a single optional free-text notes field in Section 1. Safety-aware scoring produces `risk_signals` for emergency-med availability gaps, missed-dose frequency, running-out incidents, controlled-substance safeguards, missing school authorisation, and high-stakes disagreement — surfaced as a distinct card in the report UI and PDF. Backend: `med_deep_questions.py`, `med_deep_scoring.py`, `med_deep_report.py` (subclassed `_MedPDF` header), `med_deep_routes.py` at `/api/med-deep/*`. Frontend: `SpecialNeedsV2MedicalDeepDive.jsx` and `SpecialNeedsV2MedicalDeepDiveReport.jsx`. Entry via new CTA card `snc2-med-deep-dive-cta` on `/special-needs-v2` and toolbar link `snc2-open-med-deep-dive`. Mongo collections: `med_deep_assessments`, `med_deep_reports`. Tests: `tests/test_med_deep.py` (14 unit) + `tests/test_med_deep_api.py` (13 live E2E) + 38 regression on psych/edu/snc2 = 65 passing. Non-diagnostic, non-adjudicative disclaimer; PDF <=8 pages Letter size.
- **Optional-first Deep Dive UX + Preview Samples + Dashboard Progress (2026-07-31)** — three-part enhancement bundle:
  * **Optional-first entry UX**: Wrapped the three deep-dive cards in a titled section "Optional companion deep dives — pick any, all, or none" with explanatory copy that the main assessment is enough on its own. Each card gets a corner X-dismiss + "Not applicable to us" link (state persisted in `localStorage['snc2.deepDiveDismissed']`) and a "Bring back" restore button. Toolbar chips inside the assessment view carry an "(optional)" hint.
  * **Deep-dive sample PDFs**: `scripts/generate_snc2_samples.py` extended with `build_edu_deep_sample`, `build_psych_deep_sample`, `build_med_deep_sample` producing `snc-sample-educational-deep-dive.pdf`, `snc-sample-psychological-deep-dive.pdf`, `snc-sample-medical-deep-dive.pdf` served from `/downloads/`. New tri-card row on the SNC v2 samples block with testids `snc2-sample-deep-dives`, `snc2-sample-deep-dive-{educational|psychological|medical}`.
  * **Dashboard "Optional deep dives" progress card**: New backend aggregator `/api/deep-dives/status` (`deep_dives_routes.py`) returns per-user status (has_assessment, completed, answered_count, has_report, report_stale, updated_at, generated_at) for the three products. Dashboard renders a card (`dashboard-deep-dives-card`) with per-deep-dive rows showing status pill (Not started / In progress · N answered / Completed) and links to the report or assessment. Only surfaces once at least one deep dive has been started.
- **SNC v2 Enhancements Bundle (2026-07-30)** — four enhancements shipped together:
  * **Sample buttons** on `/special-needs-v2` picker (testids `snc2-samples-block`, `snc2-sample-assessment`, `snc2-sample-report`, `snc2-sample-comparison`) linking to the 3 static sample PDFs.
  * **Safety Recommend guardrail** — `snc2_report_content._s9_recommended_structure(safety_level=...)` HARD-OVERRIDES recommendation to `parallel_or_supported` for Safety level 1 and to at least `structured` for level 2, regardless of score. `snc2_routes` reads the latest safety level per user and stores `safety_level_at_generation` on the cached report; `_is_stale` now considers a changed safety level so cache invalidates on new safety filings.
  * **Email My Report** — `POST /api/snc2/report/email` builds the PDF and sends it via new `email_service.send_snc_report_pdf` (Resend + attachment). Frontend button `snc2-report-email` on the report page.
  * **Growth Wins Dashboard card** — `GET /api/snc2/compare/dashboard/highlights` returns top-5 highlights from the parent's most-recent active ready comparison (safety-guardrail-aware). Frontend card `dashboard-snc-highlights` on `/dashboard` with a "See the full comparison" CTA linking to the compare view.
  * Tests: 11 new in `tests/test_snc2_enhancements.py` + 3 new safety-override unit tests in `test_snc2.py` — **61/61 SNC v2 tests passing** with iteration-36's `_latest_safety_level` fix intact.
- **Email delivery**: Resend `RESEND_FROM_EMAIL` switched to the verified `mattsossi@mattsossi.sacoparentsapp.online` subdomain — outbound email now delivering. Root `sacoparentsapp.online` domain still failed at Resend; add DKIM/SPF/MX records to verify it and switch the FROM back for cleaner branding.
- **Iteration 57 — Weekly Email Recap Preview (2026-02-XX)**:
  - Extracted `_build_weekly_email_context(db, user)` out of the send endpoint so preview + send share exactly the same numbers (regression-tested — the preview cannot lie about what the email will contain).
  - New endpoint `GET /api/dashboard/weekly-email/preview` returns `{week_key, sent_this_week, sent_at, is_sunday_utc, weekday_utc, preview: {user_name, user_email, completed_count, total, streak_days, milestones_this_week[], alignment_pct, dashboard_url}}`.
  - New `WeeklyEmailPreview.jsx` mounted on `/dashboard` below the Public Milestone Wall. Collapsed by default with a friendly headline that adapts to the day of the week ("Your snapshot goes out tomorrow (Sunday)" / "Today is Sunday — your snapshot fires next" / "Your snapshot goes out in N days"). Expanded body pixel-mirrors the email: subject line, purple pill card with the exact `N of 5 milestones lit.` + streak + alignment lines, and a bullet list of this-week milestones. Two action buttons: "Send it to me now" (force-sends via `POST /weekly-email/send`) and "Refresh preview" (reloads the endpoint after recent activity). If `sent_this_week` is true, an "Already sent this week" green pill appears next to the actions.
  - Tests: extended `/app/backend/tests/test_iter56_features.py` — 9/9 pass (adds `TestWeeklyEmailPreviewEndpoint` with shape validation + preview/send-payload equality check). Regression 74/74 across iter-48/50/51/52/53/54/55/56/57.

- **Iteration 56 — Streak Days Badge + Top Cheered Spotlight + Weekly Progress Email (2026-02-XX)**:
  - **Streak Days**. `_current_streak_days(db, user_id)` helper counts consecutive UTC calendar days a parent has hit the dashboard (backed by the existing `progress_daily_history` collection). Exposed on `/api/dashboard/progress` as `streak_days`. When the streak reaches 7, `maybe_log_week_streak` fires a new `week_streak_7` wall badge (24-hour de-dupe so re-earning is possible). New sparkline row field `visited` tells the frontend which days were actual visits vs backfilled.
  - Frontend: new gold-tinted "🔥 Nd" streak pill in `ProgressDashboardCard.jsx` next to the sparkline (`dashboard-progress-streak` testid). Only rendered when `streak_days > 0`.
  - **Top Cheered This Week**. `top_cheered_since(db, days=7, limit=3, viewer_id)` helper aggregates `wall_cheers` in the last 7 days, joins back to events, and returns anonymised rows in sorted-desc order with `cheer_count` + `i_cheered`. Exposed as `top_cheered` array on `/api/wall/feed`.
  - Frontend: new gold-bordered "MOST CHEERED THIS WEEK" spotlight card above the main wall feed in `PublicMilestoneWall.jsx` — badge icon + tinted avatar + `cheer_count` pill per row. Only rendered when there are cheered events. Testids `wall-top-cheered`, `wall-top-cheered-item-{event_id}`, `wall-top-cheered-count-{event_id}`.
  - **Weekly Progress Email**. New `send_weekly_progress_summary` email helper (branded HTML + plain-text alternate) that renders the parent's `N/5` progress, streak line, this-week milestones, and alignment %. Two new endpoints:
    - `POST /api/dashboard/weekly-email/send` `{force?: bool}` — sends the email, upserts a `weekly_progress_email_log` row keyed by `(user_id, week_key=YYYY-Wnn)`. Idempotent per ISO week; second call returns `already_sent: True` unless `force=True`.
    - `GET /api/dashboard/weekly-email/status` — returns `{week_key, sent_this_week, sent_at, is_sunday_utc, weekday_utc}` so the frontend can auto-fire the email on Sundays.
  - Frontend: new lazy `useEffect` in `Dashboard.jsx` checks `/weekly-email/status` on load, and if `is_sunday_utc && !sent_this_week` fires `POST /weekly-email/send`. Multi-tab safe (backend enforces idempotency). Silent on failure — the email is best-effort momentum, never blocks the dashboard.
  - Tests: `/app/backend/tests/test_iter56_features.py` — 7/7 pass (streak_days present and ≥1 after visiting, seeding 6 historical days + hitting /progress today produces streak=7 AND logs `week_streak_7` badge on the wall, `top_cheered` field present + populates in sorted desc order + `i_cheered` correctly reflects the caller, weekly-email status shape, send is idempotent per ISO week, force=True bypasses idempotency). Regression 72/72 across iter-48/50/51/52/53/54/55/56. Live-verified on preview URL — all 5 new testids render + 2 top-cheered items appear above the main feed.

- **Iteration 55 — Cheer Reactions + More Badge Types on the Wall (2026-02-XX)**:
  - **More badge types**. Extended `wall_routes.py` with three new badges alongside the existing `foundation_ready`:
    - `first_compare` (lifetime badge) — logged when a compare share transitions to `status == "active"` (both parents consented) via a hook inside `deep_dive_compare_router_factory.consent()`.
    - `high_alignment_90` (24-hour dedupe) — logged when a compare snapshot is persisted with `aligned_pct >= 90` via a hook inside the snapshot-persistence branch of the same factory.
    - `communication_master` (lifetime badge) — logged when a parent has saved all 6 mediation-prep sections (child_goals, issues, priority, comm_style, readiness, reflection) via a hook inside `progress_dashboard_routes.get_progress`.
    Refactored `_log_event_once` with an `_LIFETIME_BADGES` frozenset so lifetime badges never re-log while the others still use the 24-hour flicker guard. Feed labels populated for every new type.
  - **Cheer Reactions**. New `wall_cheers` collection with (event_id, user_id) rows. `POST /api/wall/cheer/{event_id}` is a toggle — first call inserts, second removes. Returns `{ok, cheered, cheer_count}`. Requires the caller to be opted-in (403 otherwise — symmetric mutual-consent contract), blocks self-cheering with 400, and 404s an unknown event. `/api/wall/feed` now returns `cheer_count` + `i_cheered` on every event via a Mongo aggregate pipeline. Cheerer's identity is never exposed on the feed — only their opt-in status enables the interaction.
  - Frontend: `PublicMilestoneWall.jsx` extended with a `BADGE_META` map (icon + tint per badge type — green Foundation, purple First Compare, amber 90% Alignment, blue Communication Master) and a small heart-shaped cheer button per event. Button shows a live `cheer_count`, animates to filled-red on cheered, is disabled + faded when the caller is opted-out (with a friendly title), and toggles optimistically via the wall/cheer endpoint. Testids `wall-cheer-{event_id}` (with `data-cheered="0|1"`) and `wall-cheer-{event_id}-count`.
  - Tests: `/app/backend/tests/test_iter55_features.py` — 6/6 pass (all 4 badge types appear on the wall after a full 5/5 run, `first_compare` is a lifetime badge so revoke + re-consent does not re-log, opted-out parent can't cheer → 403, self-cheer blocked → 400, cheer toggles `cheered` + `cheer_count` correctly, unknown event → 404). Regression 65/65 across iter-48/50/51/52/53/54/55. Live-verified on preview URL: 6 wall events rendered with 4 distinct badge types, 12 cheer buttons rendered, one in cheered=1 state.

- **Iteration 54 — Public Milestone Wall (2026-02-XX)**:
  - New backend module `wall_routes.py` — opt-in, anonymised community feed of badges other parents have earned in the last 30 days. Two Mongo collections: `wall_opt_in` (per-user preference) and `wall_events` (raw badge events with a stable SHA-256 hash of `user_id` combined with a salt from `WALL_ANON_SALT` env var — falls back to a dev salt for local runs). Only 3 endpoints: `GET /api/wall/status` → `{opt_in, my_events_this_month}`, `POST /api/wall/opt-in` `{opt_in}` — flips the pref AND backfills a Foundation-Ready event immediately when the parent already holds the badge, `GET /api/wall/feed?days=30&limit=50` → `{events: [{event_id, user_hash, badge_type, badge_label, created_at, when_human}...], total, days}`. Feed rows expose ONLY safe fields — never user_id, name, email, or numeric stats. Wall event logging is silently hooked into `/api/dashboard/progress` — safe no-op unless opted in. De-duped in a 24-hour window so a 4↔5 flicker can't spam the wall.
  - Frontend: new `PublicMilestoneWall.jsx` mounted under the ProgressDashboardCard on `/dashboard`. Renders a headline count, a big pill toggle (green filled when opted-in / purple outlined when off), and up to 25 anonymised events with a deterministic two-tone HSL avatar generated from the `user_hash` so parents can spot repeat events from the same anon parent without knowing who they are. Empty state and privacy note ("You're currently invisible to the wall") when opted out.
  - Tests: `/app/backend/tests/test_iter54_features.py` — 5/5 pass (default opt-out never produces events even with 5/5 lit, opt-in backfills an event when the parent already holds the badge, feed rows expose only safe fields with 16-char user_hash, hitting `/progress` multiple times within 24h never double-logs, opt-out stops future events but keeps past ones). Regression 59/59 across iter-48/50/51/52/53/54. Live-verified on preview URL: all `wall`, `wall-headline`, `wall-toggle` (data-opted-in=1), `wall-feed`, and `wall-event-*` testids render, showing the backfilled Foundation Ready event with a pink two-tone avatar and "just now" timestamp.

- **Iteration 53 — Foundation Ready On Certificate + Progress Sparkline (2026-02-XX)**:
  - **Foundation Ready ribbon on the Certificate**. `certificate_service.build_certificate_png/pdf` now take a `foundation_ready: bool` param; when true, a gold-bordered deep-green "FOUNDATION READY" pill is stamped in the top-right corner of the certificate template. Extracted `compute_progress(db, user)` helper out of `progress_dashboard_routes.py` so `mediation_routes.py::preview_certificate` and `download_certificate` can compute the flag at generation time — no double DB lookup. Preview responds with `X-Foundation-Ready: 1|0` header so the frontend can label the download link. Best-effort — a progress-lookup hiccup never fails certificate generation.
  - **Progress Sparkline (30-day)**. New `progress_daily_history` collection keyed by (user_id, date=YYYY-MM-DD). `GET /api/dashboard/progress` upserts today's `{completed_count, total, ready}` row on every call (idempotent — one row per user per UTC day) and returns a dense `history: [{date, done, total, ready}, ...]` array covering the last 30 days plus `history_days: 30`. Missing days are backfilled with the last known value so the sparkline stays continuous. Frontend: new `ProgressSparkline.jsx` SVG component (gradient fill + path + endpoint dot that turns gold on ready-days) mounted inside the progress-count row next to the `N/5` count and Foundation Ready badge. Data-testid `progress-sparkline` carries `data-trend="up|down|flat"` for the last 30 days.
  - Tests: `/app/backend/tests/test_iter53_features.py` — 7/7 pass (PNG + PDF ribbon changes output bytes, `X-Foundation-Ready` header is 0/1 correctly before + after 5/5, `/progress` returns exactly 30 dense history rows with the expected shape, today's row updates idempotently on repeat calls, `foundation_ready` bubbles up alongside `history[-1].ready`). Regression 54/54 across iter-48/50/51/52/53. Live-verified on preview URL: certificate PNG shows the ribbon in the top-right corner; dashboard renders `progress-sparkline` with `data-trend="up"` next to the count.

- **Iteration 52 — Section Coach on the Report + Foundation Ready Celebration (2026-02-XX)**:
  - **Section Coach on the Report** — new `ReportSectionCoachStrip.jsx` in `/app/frontend/src/components/deepdive/` fetches the pathway schema and renders one collapsed `SectionCoachCard` per section on the Deep Dive report pages (`SpecialNeedsV2{Educational,Psychological,Medical}DeepDiveReport.jsx`), below the final child-focused summary. Texas-only sections are dropped when the parent isn't in TX. Each card lazy-loads on tap and hits the existing `POST /api/{prefix}/section/{section_id}/coach` — cached cards from the assessment flow return instantly (`cached: True`), so revisiting the report is free. Testids: `{prefix}-report-section-coach-strip` and `{prefix}-report-{sectionId}-section-coach` (plus all the inherited coach card testids).
  - **Foundation Ready Celebration** — new `FoundationReadyCelebration.jsx` component (+ `FoundationReadyBadge` export) plugged into `ProgressDashboardCard.jsx`. When `GET /api/dashboard/progress` returns `completed_count === total` (all 5 pills lit), the card renders a 36-particle CSS confetti burst plus a "BADGE UNLOCKED · Your Foundation Is Ready." card with "Copy a share line" and dismiss actions, and a persistent "Foundation Ready" gradient pill next to the `N/5` count on the progress card header. LocalStorage keys `sacop.foundation_ready_celebrated.v1` (one-time dismissal) and `sacop.foundation_ready_streak.v1` (streak tracker that resets so a lost-then-re-earned badge replays the confetti). Colours pull the app's purple / green / amber palette to celebrate all five pill tints at once.
  - Tests: `/app/backend/tests/test_iter52_features.py` — 5/5 pass (schema returns sections with the fields the strip reads for all three pathways, cached coach card survives a repeat call so the report doesn't re-hit the LLM, `completed_count == total` transitions from < total to == total after a consented high-alignment compare snapshot). Regression 47/47 across iter-48/50/51/52. Live-verified on the preview URL: all 9 celebration + badge + confetti testids render when the parent hits 5/5.

- **Iteration 51 — AI Personal Coach + Progress Dashboard (2026-02-XX)**:
  - **AI Personal Coach** for Deep Dive sections. New backend module `deep_dive_section_coach.py` — pattern mirrors `ai_summary.py` (Claude Sonnet 4.5 via Emergent LLM key) — produces a strict-JSON 4-list coach card (`doing_well`, `coordination_gaps`, `next_steps`, `resources`, each 0-3 short bullets). System prompt enforces neutral / non-diagnostic / non-adjudicative tone and frames gaps as coordination opportunities. Cache collection `deep_dive_section_coach_cards` keyed by (user_id, pathway_id, section_id) with a 16-char answer hash so revisiting a section with unchanged answers is free. New pathway endpoint `POST /api/{edu,psych,med}-deep/section/{section_id}/coach` — body `{force?: bool}`; returns `{ok, section_id, coach, cached, answer_hash, generated_at, no_answers}`. LLM failures serve a 503 without breaking the assessment flow. Frontend: new `SectionCoachCard.jsx` in `/app/frontend/src/components/deepdive/`, wired into all three deep-dive assessment pages (`SpecialNeedsV2{Educational,Psychological,Medical}DeepDive.jsx`). Card is collapsed by default, opens on tap, shows Loading → 4 tint-coded cards (green Strengths / purple Coordination / amber Next steps / blue Resources) with a Refresh button that force-regenerates. Reset state on section change so parents never see a stale card.
  - **Progress Dashboard**. New backend module `progress_dashboard_routes.py` — `GET /api/dashboard/progress` returns five ✓ pills: `foundation_completed` (safety assessment saved + user has a name), `child_needs_identified` (any deep-dive completed OR SNC v2 report), `communication_readiness` (`prep_data.comm_style` saved), `mediation_readiness` (3+ mediation-prep sections saved out of child_goals / issues / priority / comm_style / readiness / reflection), and `conflict_reduced` (most-recent compare snapshot across any pathway has aligned_pct ≥ 60). Each pill returns a `done` bool + a helpful `detail` line. Also exposes `completed_count`, `total`, `alignment_pct`, `alignment_pathway`, `alignment_threshold` for a headline count. Frontend: new `ProgressDashboardCard.jsx` mounted just below `NextStepJourney` on `/dashboard` — headline "N of 5 milestones lit", gradient progress bar, and a 2-column grid of the five tint-coded pills with icons that swap Circle → CheckCircle2 when done.
  - Tests: `/app/backend/tests/test_iter51_features.py` — 9/9 pass (Progress Dashboard shape, `foundation_completed` + `mediation_readiness` light after seeding safety + 3 prep sections, `conflict_reduced` flips after a consented compare snapshot at ≥60%, coach returns four lists for all three pathways, cache hit on repeat call, `force=True` bypasses cache, unknown section returns 404). Regression 42/42 across iter-48/50/51. Live-verified on the preview URL: all 5 dashboard-progress testids render.

- **Iteration 50 — Psych & Med Compare Rename + Alignment Preview in Invite Email (2026-02-XX)**:
  - Renamed the Psychological Compare product from "Psychological Deep Dive · Co-Parent Comparison" → **"Checkin - Psychological Needs Report"** across frontend hub/view eyebrows and backend PDF filename stem/header/product-title. New PDF filename prefix: `Checkin_Psychological_Needs_Report_...pdf`. `product_label` used in Compare-Invite emails now reads "Checkin - Psychological Needs".
  - Renamed the Medical Compare product from "Medical Deep Dive · Co-Parent Comparison" → **"Checkin - Medical Needs Report"** analogously. New PDF filename prefix: `Checkin_Medical_Needs_Report_...pdf`. `product_label` in emails now reads "Checkin - Medical Needs".
  - Updated `tests/test_iter48_features.py::TestEducationalPDFRename` to reflect the new prefixes for all three pathways (Edu, Psych, Med) — 16/16 iter-48 tests pass.
  - **Three alignment lists (Shared Priorities / Points for Discussion / Questions for Mediation) confirmed live on Psych + Med** — no code changes needed because psych/med delegate to the shared `deep_dive_comparison_core.build_comparison_from_spec` (payload), the shared `DeepDiveCompareView.jsx` renders the three-card `AlignmentList` grid using dynamic `testidPrefix`, and the shared `edu_deep_comparison_pdf.build_comparison_pdf` renders the three sections in the PDF.
  - **Alignment Preview + Trend in Compare-Invite email**: `link_partner` now computes `aligned_pct` at invite time (only when BOTH parents have completed their assessments) and passes it to `send_compare_invite(aligned_pct=...)`. In addition, it looks up the most recent compare snapshot for this user pair on this pathway (across any prior share, revoked or not) and passes its aligned_pct as `previous_aligned_pct=...`. The email renders a green "A quick preview — You already agree on about NN% of your answers." card in HTML + a matching line in plain text, followed by a small colour-coded trend line ("↑ up 9 points since your last check-in (was 62%)" / "↓ down 14 points…" / "→ no change since your last check-in") whenever a prior snapshot exists. Ends with "This is a summary only — no items are shared until you consent." Falls back cleanly: missing current or missing previous ⇒ no fabricated numbers leak. All numeric inputs are clamped to [0, 100] and floats are coerced to int for safety.
  - Tests: `/app/backend/tests/test_iter50_compare_invite_preview.py` — 17/17 pass (email rendering with/without pct + trend up/down/flat + missing current + missing previous + clamping + float coercion + `build_comparison` returns a well-formed `summary.aligned_pct` integer for all three pathways). iter-48 regression 16/16.

- **Iteration 49 — Rename + Compare-Invite Email (2026-08-02)**:
  - Rename (Educational only): "Educational Assessment Alignment Report" → **"Coparenting Education Check In Summary"** across the frontend hub eyebrow + description, the compare-view eyebrow + hub-label + download filename, and the backend PDF (`Coparenting_Education_CheckIn_Summary_<parentA>_and_<parentB>.pdf` + matching header/title). The `product_label` value passed to Compare-Invite emails now reads "Coparenting Education Check In" so email copy stays consistent. Psychological & Medical Compare untouched.
  - Compare-Invite email: `email_service.send_compare_invite(to_email, link_url, inviter_name, product_label)` sends a neutral Resend email with subject "{inviter} invited you to compare {product_label} answers on SA CoParenting App" and a CTA link to the pathway hub. Fired from `deep_dive_compare_router_factory.link_partner` after inserting a new share (fire-and-forget: Resend hiccups are logged but never block the state machine). Factory now takes a `frontend_hub_path` param and each of the three pathway wrappers passes their hub route.
  - Verified end-to-end: creating a fresh Educational share returned a 200 response with the new share_id; PDF endpoint now returns `Content-Disposition: attachment; filename="Coparenting_Education_CheckIn_Summary_..."`.

- **Iteration 48 — Educational Assessment Alignment Report (2026-08-01)**:
  - Rename (Educational only): product now branded as "Educational Assessment Alignment Report". Hub + view eyebrow, PDF filename (`Educational_Assessment_Alignment_Report_...pdf`), PDF header/title, and the Educational Report page entry link ("Compare Our Educational Priorities" at testid `edu-deep-report-open-compare`) all updated. Psych + med copy untouched.
  - Three new mediation-ready sections in the comparison payload (all pathways share the same schema shape so psych + med get them for free): `shared_priorities` (both parents scored likert ≥4 or picked ≥2 overlapping multi options), `discussion_points` (close-alignment items + one-only responses), `mediation_questions` (divergent items neutralized as questions — "How will we align on: {prompt}", "You chose different answers to: {prompt}", "Which of these options do we both commit to on: {prompt}"). Each list capped at 8 rows.
  - Frontend: new `AlignmentList` presentational component in `DeepDiveCompareView` rendering the three cards side-by-side (`{prefix}-alignment-lists` grid → `-shared-priorities`, `-discussion-points`, `-mediation-questions`) with per-card count/list/empty testids. PDF renders the three lists after the existing "5 things you already agree on" block.
  - Topic coverage audit: IEP, ARD, tutoring, attendance, performance, accommodations, educator comms all already present in `edu_deep_questions.py` — no gap.
  - Tests: `/app/backend/tests/test_iter48_features.py` — 16/16 pass; iter-42 through iter-47 regression 76/77 (1 pre-existing skip). Testing agent report `/app/test_reports/iteration_48.json` — no bugs. Optional refinements (highlight-scored top-8 selection, `md:grid-cols-2` tablet break) deferred.

- **Iteration 47 — Milestone History Ribbon (2026-08-01)**:
  - Backend: `deep_dives_routes._compare_counts` now unions every non-empty `milestones_crossed` list across snapshots for each pathway's non-revoked shares (whitelisted to {50, 75, 90} so rogue values can't surface an untinted pill). `/api/deep-dives/compare-status` now returns `pathways[i].milestones` and top-level `total_milestones_unlocked`.
  - Frontend: Dashboard compare tile shows a gold `dashboard-compare-milestones-total` pill in the header when the aggregate is > 0, and each pathway row gets a `dashboard-compare-pathway-{id}-trophies` strip with tier-tinted trophy pills (`trophy-50/75/90` = purple/green/gold). Trophy strip is only rendered when a pathway has ≥ 1 milestone.
  - Tests: `/app/backend/tests/test_iter47_features.py` — 8/8 pass; iter-42/43/44/45/46 regression 68/69 (1 pre-existing skip). Testing agent report `/app/test_reports/iteration_47.json` — no bugs, applied the "whitelist tiers" belt-and-suspenders code-review note.

- **Iteration 46 — Alignment Milestones (2026-08-01)**:
  - Backend: `_load_comparison` now computes `milestones_crossed` for each new snapshot (thresholds 50/75/90 aligned_pct, upward-only). Field stored on the snapshot row. Timeline endpoint exposes `latest_snapshot_id` + `latest_milestones`. Server startup creates a unique index on `(share_id, snapshot_key)` for the snapshot collection so concurrent view races can't stamp duplicate milestones — insert now catches `DuplicateKeyError`.
  - Frontend: new `AlignmentMilestoneCelebration` component (`components/deepdive/`) renders a tinted card + 24-particle pure-CSS confetti burst when a milestone fires. Copy scales by tier: 50 → "You've agreed on half of your answers.", 75 → "You've agreed on more than 3 in 4 questions." (the primary user-requested milestone), 90 → "You've reached 9-in-10 alignment." Includes a "Copy this line" button that lifts the shareable sentence to the clipboard and a "Dismiss" that persists under `sacop.milestone_dismissed.{snapshot_id}` so parents don't see the same celebration twice. DeepDiveCompareView renders the highest crossed milestone via `Math.max(...timeline.latest_milestones)`.
  - Tests: `/app/backend/tests/test_iter46_features.py` — 17/17 pass; iter-42/43/44/45 regression 51/52 (1 pre-existing skip). Testing agent report: `/app/test_reports/iteration_46.json` — 100% frontend end-to-end verified with a seeded 98% share.

- **Iteration 45 — Compare Timeline (2026-08-01)**:
  - Backend: `deep_dive_compare_router_factory._load_comparison` now writes a lightweight row to a new `deep_dive_compare_snapshots` Mongo collection every time it computes a comparison. Dedupe key = `(creator_assessment.updated_at, partner_assessment.updated_at)` so re-runs of either assessment produce a fresh snapshot on the next view, but repeat opens do not. Insert is wrapped in try/except so a Mongo blip never blocks the parent from seeing their comparison.
  - Backend: new `GET /api/{edu,psych,med}-deep/compare/{share_id}/timeline` returns `{snapshots, series, count, first_aligned_pct, latest_aligned_pct, delta_aligned_pct}` ordered ASC. Returns 200 with count=0 when nothing has been captured yet.
  - Frontend: `DeepDiveCompareView` fetches the timeline after the main comparison and renders an "Alignment over time" section only when `count > 1`. Headline shows the latest aligned %, a ▲/▼ delta pill vs. the first snapshot, a compact bar-sparkline (latest = deep purple), and a scrollable list of every snapshot with date + aligned/divergent counts.
  - Tests: `/app/backend/tests/test_iter45_features.py` — 8/8 pass; iter-42/43/44 regression 43/44 (1 pre-existing skip). Testing agent report at `/app/test_reports/iteration_45.json` — no bugs, one optional UX polish (add date ticks under sparkline) deferred.
- **Iteration 44 — Compare Dashboard Widget (2026-08-01)**:
  - Backend: new `GET /api/deep-dives/compare-status` in `deep_dives_routes.py` returns `{pathways: [{id, name, compare_route, active, ready_to_view}], total_active, total_ready_to_view}` counting non-revoked shares in each of the 3 pathway shares collections; `ready_to_view` additionally requires mutual consent + completed assessments on both sides. `DEEP_DIVES` config extended with `shares_collection` and `compare_route`.
  - Frontend: Dashboard fetches `/deep-dives/compare-status` non-blocking and renders a `dashboard-compare-card` tile (headline `dashboard-compare-headline`) only when `total_active > 0`. Three per-pathway rows link straight to each compare hub with a colored status pill (green = ready, orange = pending, grey = none yet).
  - Tests: `/app/backend/tests/test_iter44_features.py` — 6/6 pass; iter-42 (20/20) and iter-43 (17/17) still green. Playwright verified the tile renders, headline reads correctly, per-pathway rows navigate to the right hubs, and the tile hides when all shares are revoked. See `/app/test_reports/iteration_44.json`.
- **Iteration 43 — Compare parity + Nickname (2026-08-01)**:
  - **Psychological Compare + Medical Compare**: Extracted the iteration-42 Educational Compare into a shared core. New modules `deep_dive_comparison_core.py` (pathway-agnostic alignment logic via `build_comparison_from_spec`) and `deep_dive_compare_router_factory.py` (state-machine + safety guardrail factory). Educational, Psychological, and Medical each now sit on top of these as ~15-line wrappers, exposing `/api/{edu,psych,med}-deep/compare/*`. Frontend gets shared `DeepDiveCompareHub.jsx` + `DeepDiveCompareView.jsx` under `components/deepdive/`; the six pathway pages are ~20-line wrappers passing a pathway prop. Entry links `psych-deep-report-open-compare` and `med-deep-report-open-compare` added to the psych + med report pages.
  - **Share Link Nickname**: `ReportShareControls` gains an optional 60-char nickname input (testid `{prefix}-nickname-input`); label is sent as `{label}` in the share-link POST body (already accepted by all 4 endpoints in iter-42), persisted in `share_tokens`, and rendered in the active-links list (`{prefix}-row-label-{jti}`) with an italic "Untitled link" fallback.
  - **Refactor bug caught + fixed**: initial factory version defined `LinkIn`/`ConsentIn` as inner classes and FastAPI treated the body as a query param → 422s. Fixed by promoting them to module scope in `deep_dive_compare_router_factory.py` (lines 54/58).
  - Tests: `/app/backend/tests/test_iter43_features.py` — 17/17 executed pass; iter-42 regression `test_iter42_features.py` — 20/20 still pass. Frontend testing agent verified both compare hubs load and the nickname round-trips via `/summary` share.

- **Retained products**: Co-Parenting Assessment + Report (+ share links), Family Violence & Communication Safety Assessment + Report, auth, invites (general co-parent), gmail, coach, insights, admin, next-steps.
- **Iteration 42 — Three-feature batch (2026-08-01)**:
  - **Summary Length Toggle**: `ai_summary.generate_executive_summary(..., length='short'|'standard'|'long')` — short ~60-100 words, standard ~180-220, long ~320-380. `POST /api/{edu,psych,med}-deep/report/regen-summary` accepts optional `{length}` body (backwards compatible with empty body); response stores `ai_summary_length`. Frontend adds a Short/Standard/Long pill toggle inline with the Regenerate button on all 3 deep-dive report pages.
  - **Expiring Share Links** — user-selectable window + revocation. `auth.create_share_token` now accepts `expire_days` (1/7/30/None) and always emits a unique `jti`. New collection `share_tokens` records each mint. New endpoints `GET /api/share/mine` and `POST /api/share/revoke {jti}`. All 4 existing share-link endpoints (cp_report, mediation summary, mediation agreement, safety assessment) accept `{expire_days, label}` and return `{token, jti, expires_at}`. Every `/shared/{token}` GET consults `is_share_token_revoked`. Frontend `ReportShareControls` shows a 24h/7d/30d/Never pill selector plus a collapsible "Your active share links" list with per-row Revoke buttons.
  - **Compare Deep Dives (Educational only)** — new backend modules `edu_deep_comparison.py`, `edu_deep_comparison_routes.py`, `edu_deep_comparison_pdf.py` mounted at `/api/edu-deep/compare` (mirrors `/api/snc2/compare` state machine + safety guardrail: levels 1–2 block). New pages `SpecialNeedsV2EducationalDeepDiveCompare.jsx` (hub) and `SpecialNeedsV2EducationalDeepDiveCompareView.jsx` (view), routed at `/special-needs-v2/educational-deep-dive/compare[/:share_id]`. Entry link (`edu-deep-report-open-compare`) added to the Educational Deep Dive report page. Compare view includes a "N things you already agree on" highlights section + branded PDF download.
  - Testing agent report: `/app/test_reports/iteration_42.json` — 20/20 iter-42 tests pass. Applied testing agent's recommended defense-in-depth safety re-check to `/link` even when returning an existing share.

---

## v2 Implementation summary

### Backend
- `backend/snc2_questions.py` — 4 pathways, 8-step template, parametric per-pathway prompts + options; `build_schema()` compiles per-selection schemas.
- `backend/snc2_scoring.py` — Per-pathway composite `understanding` + `coordination` scores plus a reported-impact banding.
- `backend/snc2_report_content.py` — Structured report matching the 8-step workflow with the response → finding → child impact → suggested → action step pattern.
- `backend/snc2_report_pdf.py` — SA CoParents-branded PDF renderer (sand header band + logo + purple accents).
- `backend/snc2_routes.py` — `/api/snc2/*` API (pathways, schema, me, select, answer, answers/bulk, complete, scores, delete, report/status, report/generate, report/regenerate, report, report/pdf).
- MongoDB collections `snc2_assessments`, `snc2_reports`.

### Frontend
- `frontend/src/pages/SpecialNeedsV2.jsx` — category picker → 8-step assessment (autosave, progress bar, step tabs, Save-and-come-back, Complete).
- `frontend/src/pages/SpecialNeedsV2Report.jsx` — At-a-glance, pathway scores, 8 step blocks, cache bar with Download PDF + Regenerate.
- `App.js` routes `/special-needs-v2`, `/special-needs-v2/report`.
- `Dashboard.jsx` card `[data-testid=dashboard-snc-card]` deep-links to v2 URLs.

### Tests
- `tests/test_snc2.py` — 9 unit tests (schema resolve/build, validation, scoring bands, report structure, PDF signature + guardrails, catalog).
- `tests/test_snc2_api.py` — 11 API integration tests (added by testing agent).
- Testing agent iteration 35 — zero critical/minor issues. Guardrails verified: no `correct parent`, `wrong parent`, `winner`, `right parent`, `incorrect parent` in payload or PDF bytes.

### Public samples
- `frontend/public/downloads/snc-sample-individual-report.pdf` — filled with rich fictitious "Multiple pathways" data (ADHD + IEP + emotional regulation).
- `frontend/public/downloads/snc-sample-assessment.pdf` — blank 8-step workbook printout with all three pathways.

---

## Backlog / Next work

### P1
- **Report email attachment** for v2 (mirror the v1 `POST /api/snc2/report/email` we shipped earlier — SA CoParents-branded email with the PDF attached).

### P2
- **Reintroduce a Family Report** that stitches CP + Safety + SNC v2 into a single PDF, if user wants it.
- **AI narrative** (through `integration_playbook_expert_v2`) that turns the 8-step report into a plain-language executive summary.
- **Comparison PDF** for the new v2 side-by-side once the invite + comparison lands.
- **Verify Resend sender domain** so all outbound email (survey reminders, SNC report emails, invitations) actually delivers.
- Split `PRD.md` into PRD / CHANGELOG / ROADMAP if it grows past ~700 lines.

---

## Recent additions (Feb 2026)

### ND Risk Assessment Timeline (Feb 2026)
- Added Timeline component on `/nd-risk-assessment/result/:aid` — Recharts line chart with tier bands (Low/Medium/High/Critical), header stats (latest tier, lifetime delta, re-assess CTA), and delta cards between consecutive assessments.
- Added compact `NDRiskTimelineCard` on Dashboard — self-hides for parents with 0 assessments; shows a stepped list of last 3 assessments with tier chips and a trend badge.
- Reuses existing `GET /api/nd-risk/assessments/me` endpoint (no backend changes).
- Files: `/app/frontend/src/components/NDRiskTimeline.jsx`, `NDRiskTimelineCard.jsx`, updates to `Dashboard.jsx` and `NDRiskAssessmentResult.jsx`.

### Contemporaneous wording (Feb 2026)
- Updated High-tier intervention copy in `nd_risk_routes.py`: "Asynchronous / synchronous" → "Non-Contemporaneous / contemporaneous". Backfilled 2 existing High-tier assessments in Mongo.

### Login → Demo-first (Feb 2026)
- Simplified `Login.jsx` — primary CTA is now "Enter demo mode" (gradient button); email/password sign-in is collapsed behind a small toggle link for admin/returning users.

### Dimension Companion Assessment — Dim 2/3/4 (Feb 2026)
- New backend router `dimension_companion_routes.py`:
  - `GET  /api/dimension-companion/questions` — 15 Likert questions (5 per dimension)
  - `POST /api/dimension-companion` — submits + scores, returns per-dimension tier + interventions + worst-dimension focus note
  - `GET  /api/dimension-companion/me` — latest for the caller
- New frontend page `/companion-assessment` (`DimensionCompanion.jsx`) — 4-step flow (intro → Dim 2 → Dim 3 → Dim 4 → combined result).
- CTA added on Safety Assessment result page: appears ONLY when safety level ≥ 3 (cleared). Levels 1 & 2 do NOT see the companion CTA to preserve the safety firewall.
- Tiers: Strong / Steady / Stretched / Strained. Overall pathway derived from worst dimension (conservative).
- Storage: `dimension_companion_assessments` Mongo collection.

### Combined 4-Dimension Briefing PDF (Feb 2026)
- New endpoint `GET /api/dimension-companion/four-dimension-briefing/pdf` — assembles the caller's most recent Safety + Companion records into a single 4-page court-ready PDF (cover + executive summary → Dim 1 detail → Dim 2/3/4 detail → advisory).
- Accepts `audience` query param (e.g. "Mediator / Parent Facilitator Ad Litem / Trial Court") and optional `sign=true` for the tamper-evident signature line + QR.
- Gracefully renders "Not yet completed" blocks when either the Safety or Companion doc is absent — the parent can hand in an interim briefing at any completeness level.
- Frontend: download button on both the Companion result page (`companion-briefing-pdf-button`) and the Safety Assessment result page when level ≥ 3 (`safety-briefing-pdf-button`).
- Pytest coverage: `/app/backend/tests/test_iter85_four_dim_briefing.py` (6 tests: scoring + PDF magic bytes + live HTTP round-trip).

### Email the Briefing (Feb 2026)
- New endpoint `POST /api/dimension-companion/four-dimension-briefing/email` — generates the 4-Dim briefing PDF and emails it via Resend directly to the parent's mediator, parent facilitator ad litem, trial court, attorney, or therapist.
- Reply-to is set to the parent's email so the recipient can respond directly.
- Body accepts `recipient_email` (required), optional `recipient_name`, `recipient_role` (one of `mediator` / `parent_facilitator_ad_litem` / `trial_court` / `attorney` / `therapist` / `other`), and `parent_message`.
- Rejects invalid or `@demo.local` addresses with a 400; missing Resend keys return 503 with a friendly toast.
- Audit log stored in `four_dimension_briefing_emails` Mongo collection (user_id, to_email, recipient_role, audience, sent_at).
- Email helper `send_four_dimension_briefing()` in `email_service.py` with branded HTML template.
- Frontend: new reusable `BriefingEmailDialog.jsx` (email + name + role radio-chips + short message). Mounted on both the Companion result page (`companion-briefing-email-button`) and the Safety Assessment result page (`safety-briefing-email-button`).
- Pytest coverage extended in `test_iter85_four_dim_briefing.py` (7 tests total) — includes rejection of invalid emails/demo.local and a successful send to Resend's sandbox address.

### Intervention Compliance Log (Feb 2026)
- New backend router `intervention_compliance_routes.py`:
  - `GET  /api/interventions/log` — aggregates enforced interventions from the parent's LATEST Safety + ND Risk + Companion assessments, merged with this week's tick state and per-item notes. Returns summary (`total`, `followed`, `compliance_pct`).
  - `POST /api/interventions/log` — idempotent upsert of a single item (intervention_key, followed, notes).
  - `GET  /api/interventions/log/history?weeks=N` — weekly compliance % for the last N weeks (chronological, gaps filled with `null` for empty weeks).
- Storage: `intervention_compliance` Mongo collection, one document per (user_id, week_start, intervention_key). Week starts Monday UTC.
- Stable intervention key = `md5(source|text)[:16]` so ticks persist across re-assessments as long as wording stays the same.
- New frontend page `/interventions` (`InterventionCompliance.jsx`) — weekly compliance gauge, 8-week history bar strip, grouped-by-source checklist with tick toggles + optional per-item notes.
- New Dashboard card `InterventionComplianceCard.jsx` — self-hides for parents with 0 interventions on file; shows current week's % and follow count with a gradient progress bar.
- Pytest: `/app/backend/tests/test_iter86_intervention_compliance.py` (4 tests: week-start math, intervention-key stability, HTTP tick lifecycle, history endpoint shape).

### Streak Rewards for Compliance (Feb 2026)
- New endpoint `GET /api/interventions/streak` returning `current_streak`, `longest_streak`, `badges[]` (with `earned` bool), and `next_badge` with weeks-to-go + progress %.
- Three tiered badges: 4-Week Compliance Champion, 8-Week Consistency Anchor, Quarter-Year Habit.
- Streak rule: consecutive weeks with `compliance_pct >= 80%`. Silence weeks (no ticks) break the streak — this mirrors the UX language "silence isn't credit".
- New frontend component `ComplianceStreakPanel.jsx` mounted on the compliance page — shows current streak flame, longest streak, next-badge progress bar, and an "Earned" pill shelf.
- One-shot confetti + toast celebration when a new badge is detected on the device (keyed by badge key in localStorage so it never repeats).
- Dashboard card enhanced to show streak chip + earned-badge count + next-badge line.
- Pytest coverage extended (8 tests total) — includes streak boundary math (80% cutoff), null-week break semantics, and live endpoint shape checks.

### Follow-Through in the 4-Dim Briefing PDF (Feb 2026)
- The 4-Dimension Briefing PDF now includes a dedicated "How this parent is following through" page (5 total pages) showing: current-week compliance %, count followed / total, current streak + longest streak, earned badges list, and next-badge progress.
- Executive summary on the cover page gained a "Follow-through" row with the tier-style badge (on track / partial / lagging).
- New helper `build_compliance_snapshot(db, user_id)` in `intervention_compliance_routes.py` returns the compact `{current_week, streak}` shape reused by both PDF and email endpoints.
- Extended `test_iter85_four_dim_briefing.py` with `test_briefing_pdf_with_compliance_snapshot` asserting the compliance-enriched PDF is strictly bigger than the no-compliance variant. All 16 tests across iter85 + iter86 pass.

### Safety-Screen Guardrails & Terminology Reform (Feb 2026)
Applied in response to a professional review of the Safety Assessment (Danger Assessment, HITS, and MASIC-S limitations).
- **Renamed** "Family Violence & Communication Safety Assessment" → "**Family Violence and Communication Safety Screen**" across frontend pages (Landing, Dashboard, Safety, Methodology, SafetyAssessment, DimensionCompanion, InterventionCompliance, ProblemSolvingWorksheet, SpecialNeedsV2*, DeepDiveCompare*, PickerChoicePill, FivePillarJourney, PersonalizedRecommendations, methodology.js) and backend surfaces (email_service.py, safety_assessment_pdf.py cover, deep_dive_compare_router_factory.py). All `data-testid`s and route/API paths preserved.
- **Removed "court-ready"** from every user-visible surface. PDFs headers now read "Professional Informational Report" / "Professional Informational Briefing". Button labels changed to "Download PDF report".
- **New `DeviceSafetyBanner` component** (dismissible) shown at the top of the Safety Screen intro — warns about device monitoring, shared accounts, browser history, and unsafe PDF storage. Includes a **Quick Exit** button that `location.replace()` to `weather.com` and `history.replaceState` so the current page is removed from history.
- **New `ScreenGuardrailPanel` component** rendered on every safety result page:
  - Always shows a "What this screen decides — and what it does not" block naming the human roles required (family-law attorney, licensed clinician / forensic evaluator, DV advocate).
  - For Level 1 & 2 (highest-concern) results, an additional **anti-mutualization** block explains why communication coaching is not the right first step and points to the National DV Hotline.
- **AI communication coaching (`SectionCoaching`) is suppressed for Level 1 & 2** results so a survivor is never coached to communicate "better" with a coercive co-parent.
- **Methodology page transparency** — added explicit statement that this screen is not the Danger Assessment, MASIC-S, or HITS, and has not been independently validated in custody or mediation populations; scoring is heuristic; it recommends a communication *structure*, not clinical or legal outcomes.
- Survivor-visibility hardening confirmed: the Deep-Dive Compare and SNC v2 compare routers already gate on Safety Screen level and never join safety-screen answers into a shared payload.

### MASIC-S Coverage Transparency Sidebar (Feb 2026)
- New `MasicComparison.jsx` component mounted on the Methodology page (`/methodology`) — publishes an honest side-by-side of MASIC-S domains vs. this screen's actual coverage.
- Each of the 18 MASIC-S domains is tagged Covered / Partial / Gap / Reviewer pending with a short note. Legend + counts shown above the table.
- Domains currently flagged as **Gap** for reviewer input: strangulation, weapons in the home, sexual coercion, digital surveillance, financial control, substance abuse during incidents, mental-health safety concerns.
- Explicit "does NOT claim equivalence to MASIC-S" note; rows only move to Covered after reviewer panel approval with names + review date printed on the page.

### Expert Reviewer Panel Scaffolding (Feb 2026)
- New backend module `reviewer_panel_routes.py` + editable JSON file `reviewer_panel.json`:
  - `GET  /api/reviewer-panel` — returns the current list of reviewers, review scope, and status (`reviewed` / `pending`). Empty list initially.
  - `GET  /api/reviewer-panel/is-operator` — returns whether the caller is the site operator (used by the frontend to gate the send dialog).
  - `GET  /api/reviewer-panel/packet` — generates a 6-page PDF reviewer packet: cover, how the screen works, Section 1 questions (with high-concern flags), Section 2 questions, review checklist, MASIC-S gaps to address, and a sign-off page.
  - `POST /api/reviewer-panel/send` — **operator only** (gated on `OPERATOR_EMAIL` env var). Emails the packet via Resend to a candidate reviewer with a branded cover letter; reply-to is the operator's email. Logs the send in `reviewer_packet_sends`.
  - `GET  /api/reviewer-panel/sends` — operator-only audit log of previous sends.
- New env var: `OPERATOR_EMAIL` in `/app/backend/.env` (currently `mattsossi@bsossi.com`) — the site operator's email; only this account can send reviewer invitations.
- New email helper `send_reviewer_packet()` in `email_service.py` with a professional invitation template.
- New frontend `ReviewerPanelCard.jsx` on the Methodology page — lists each reviewer or shows a transparent "Independent expert review is pending" empty state. When the caller is the operator, additionally shows a **"Send packet to a reviewer"** button and a recent-sends audit log.
- New frontend `ReviewerSendDialog.jsx` — role radio-chips (DV advocate / forensic psychologist / Texas family-law attorney / clinician / other), email + name + personal note fields.
- New frontend `ReviewerStatusChip.jsx` mounted on the Safety Screen intro — pill users see immediately linking to methodology.
- Verified: non-operator/anon users see the download link but NOT the send button; backend correctly returns 403 for non-operator send attempts.
- The operator adds reviewer entries by appending to `reviewer_panel.json` after a reviewer signs the packet and agrees to be listed publicly.

### Pathway Report Email + QR Verify (Feb 2026 · iter92)
- Parents can now email the Dispute Resolution Pathway Report PDF directly to a mediator, PFAL, attorney, court, or therapist — mirrors the 4-Dim Briefing email pattern.
- New backend endpoint `POST /api/pathway-report/email` accepts `{recipient_email, recipient_name?, recipient_role, parent_message?, share_id?}`. When `share_id` is set the endpoint re-enforces the Compare-share consent gate before sending the two-parent version. Otherwise it sends the single-parent preview.
- New backend router `pathway_verify_routes.py` — writes `pathway_signatures` rows and exposes `GET /api/verify/pathway/{sig_id}`. Same minimal-response privacy stance as the briefing verify (issued yes/no + date + single/dual scope, never the recommendation or hard-lock reasons).
- Pathway PDF footer now stamps a 12x12mm QR pointing at `/verify/pathway/{sig_id}` alongside the existing "Not legal advice" line.
- New frontend `PathwayEmailDialog.jsx` (mirrors `BriefingEmailDialog`) + new public `VerifyPathway.jsx` page. `PathwayReport.jsx` gains an "Email to mediator" button that opens the dialog and forwards the current `share` query param so a dual-party report can be emailed directly from the same view.
- New email template `send_pathway_report()` in `email_service.py` — surfaces the primary pathway label + scope + a red "safety trigger applied" callout in the covering email when the algorithm hard-locked.
- Signature is recorded BEFORE the PDF is built for all three entrypoints (preview PDF, dual PDF, email) so the QR is guaranteed to resolve.
- Tests: `/app/backend/tests/test_iter92_pathway_email_verify.py` — 9/9 green (PDF-with-QR-larger, signature shape, unknown/malformed id, live round-trip, auth challenge, bad-email/@demo.local rejection, bogus-share-id consent gate).

### Admin ND Risk Coordinator Dashboard (Feb 2026 · iter93)
- New admin-only page at `/admin/nd-coordinator` shows every parent's latest ND Risk Assessment as a 4×4 threat×vulnerability heat map with per-cell counts, plus an "active cases" list of high/critical parents ordered by severity.
- Backend router `admin_nd_coordinator_routes.py` exposes `GET /api/admin/nd-risk-coordinator` gated by `analytics_routes.require_admin`. Response includes: `total_parents`, `tier_counts`, `active_case_count`, `heatmap` (4×4 grid with `{threat, vulnerability, tier, count, total_score}` per cell), `active_cases`, and `coordinator_alerts` audit counters (total, emailed).
- Reducer takes the newest assessment per `target_user_id` so a parent who re-assessed doesn't double-count.
- KPI strip (parents assessed / active / critical / coordinator emails), tier legend with per-tier totals, and case rows include target name, co-parent name, tier chip, scores, and date.
- Frontend `AdminNDCoordinator.jsx` handles 401/403 gracefully with an "admin-only" placeholder — never crashes.
- Tests: `/app/backend/tests/test_iter93_admin_nd_coordinator.py` — 6/6 green (tier-boundary corners, 4×4 heatmap counting with garbage-input tolerance, tier summariser, auth requirement, non-admin refusal, admin shape validation with live endpoint).

### Admin ND Coordinator Case Drilldown (Feb 2026 · iter94)
- Every active-case row on the coordinator dashboard is now a keyboard-accessible button that opens a right-side drawer without leaving the page.
- New backend endpoint `GET /api/admin/nd-risk-coordinator/case/{target_user_id}` returns the parent's full assessment history newest-first (`assessment_id`, `created_at`, `status`, `coparent_name`, `tier` / `tier_label`, `threat_score` / `vulnerability_score` / `total_score`, `sub_scores`, `notes`) plus the coordinator email-alert audit trail for that parent. Raw matrix answers are NOT included in the row payload — only derived scoring — so the panel is safe to leave open on a shared operator screen.
- Missing target returns `404` (clean "no history" signal) rather than empty rows; the panel surfaces the same friendly copy.
- Drawer UI (`CaseDrilldown` component inside `AdminNDCoordinator.jsx`) shows: parent name header + assessment/alert counters, coordinator alert audit list with delivered / failed indicators, and the full assessment stack. The most recent assessment is highlighted with its tier tint and a "Latest" badge; each row surfaces threat + vulnerability sub-scores side-by-side and any free-text notes the parent recorded. `Escape` closes the drawer; clicking the backdrop closes too.
- Tests: `/app/backend/tests/test_iter94_admin_nd_case_drilldown.py` — 4/4 green (unauthenticated → 401, non-admin parent → 403, unknown target → 404, admin-ok shape + newest-first ordering + no-matrix-leak).

### Heatmap Time Window Filter (Feb 2026 · iter95)
- The coordinator dashboard now accepts a `window_days` query param (allowed: 30, 60, 90, 180; omit for full history). Both the parent/case aggregation AND the coordinator-alert audit counters are clipped to the trailing window so the KPI strip stays internally consistent.
- Invalid values return `400` with a helpful message listing the allowed set — no silent fallbacks.
- Response now echoes `window_days` back so the UI can confirm what it's showing.
- Frontend: new pill-chip strip (All history / 30 / 60 / 90 / 180 days) with `data-testid="admin-nd-window-{value}"`. Chips are disabled during refetch and show an inline spinner in the section eyebrow. Empty-state copy is contextual ("No parents in the last 30 days" vs. "No parents have completed an ND Risk Assessment yet"). Initial full-page loader only shows on the first fetch — subsequent filter changes update in place.
- Tests: `/app/backend/tests/test_iter95_admin_nd_window_filter.py` — 7/7 green (cutoff helper accepts/rejects, endpoint gating, invalid-value 400, echoes window, filter shrinks counters, every allowed value returns 200).

### Dashboard Pathway Card (Feb 2026 · iter96)
- New `PathwayReportCard.jsx` mounts on the Dashboard right after the Intervention Compliance card. Reads `/pathway-report/preview` and self-hides for parents who have no Safety / Companion / ND Risk / Compliance data on file yet — so the dashboard is not cluttered for first-time visitors.
- Card surfaces: primary pathway label (from the deterministic rule engine), a "Preview" vs "Two-parent" scope chip, the primary summary (2-line clamp), a red "Safety trigger applied" pill when the algorithm hard-locked, and a "View full report →" CTA that deep-links to `/pathway-report`. When hard-locked, the whole card switches to the danger palette so parents cannot miss it.
- Language matches the report page itself: never says "you should", always frames as "the assessment data indicates". The single-parent-preview state includes a friendly nudge to invite the co-parent via Compare Share.
- Tests: `/app/backend/tests/test_iter96_dashboard_pathway_card.py` — 2/2 green (auth-required, full response contract locked so `data_inputs_present` cannot silently drop the four keys the card's self-hide logic checks). Backend `data_inputs_present` shape confirmed live for the seeded parent1 account (safety_screen + dimension_companion + nd_risk all True, primary_label = "Litigation / Court Intervention").

### Pathway Report — Direct Negotiation Row + Enriched Factor Language (Feb 2026 · iter97)
- The suitability profile now includes a fifth row for **"Direct negotiation"** (no mediator in the room). Its rating is derived by demoting the Mediation rating by exactly one notch (`high → moderate → low → not_indicated`), so a professional reading the report sees at a glance that unsupported negotiation is always more fragile than supported mediation.
- Direct negotiation is deliberately **excluded from the primary-pick pool** — the app never recommends a family negotiate with no professional present. Locked with a test.
- **Enriched factor bullets** now use the clinical language from the product brief — e.g. *"Significant communication breakdown is present between the parents"*, *"Emotional reactivity appears to interfere with negotiation"*, *"disagree substantially about the child's needs"*, *"an interdisciplinary team rather than a single mediator"*.
- **Bug fix (found by iter97 test suite)**: the classifier previously defaulted single-parent Compare alignment to 60% which was inadvertently boosting CCRM into "high" for perfectly aligned single parents. Now the classifier tracks `align_missing` and only applies alignment-based branches when we actually have dual-party data.
- Downstream propagation: frontend `PathwayReport.jsx`, PDF export (`pathway_report_pdf.py`), mediator email (`send_pathway_report`), QR verify snapshot, and the Dashboard card all iterate `suitability_profile` and `factors_supporting_primary` as lists — they picked up the new row + copy without any UI changes.
- Tests: `/app/backend/tests/test_iter97_pathway_expanded.py` — 9/9 green (PATHWAY_ORDER, 5-row profile, direct-negotiation-one-below-mediation invariant across 3 scenarios, direct-negotiation never becomes primary, hard-lock marks it not_indicated, CCRM enriched phrasing, mediation safety-screen + child-involvement lines, collaborative interdisciplinary-team line, hard-lock branch does not leak soft-signal copy). All prior pathway tests (iter91/92/96) still green — 42/42 total.

### Pathway Report Reviewer Comments — closed-loop feedback (Feb 2026 · iter98)
- A mediator, PFAL, attorney, court, or therapist who scans the QR from an emailed pathway PDF now lands on `/verify/pathway/{sig_id}` and can **leave a signed comment** for the parent. Comments show back on the parent's dashboard on next login. Closes the loop between the SA CoParents tool and the professional who received the report.
- New public endpoints (no login required — the QR IS the ticket):
  - `POST /api/verify/pathway/{sig_id}/comments` — validates body via Pydantic (name required, comment text ≥ 4 chars), rate-limits by salted IP hash (max 30 comments per hash per sig_id per 24h), 404s on unknown sig_id.
  - `GET /api/verify/pathway/{sig_id}/comments` — public list of comments on this signature, newest-first. Never leaks `ip_hash` or `parent_user_id`.
- New authed endpoint `GET /api/pathway-report/comments/mine` — returns comments left on any pathway report the caller has issued, capped at 50 rows. Isolation locked with a two-parent Mongo test proving Parent A never sees B's row.
- New comments collection `pathway_report_comments` fields: `comment_id`, `sig_id`, `parent_user_id`, `reviewer_name`, `reviewer_role`, `reviewer_org?`, `comment_text`, `ip_hash` (internal only), `created_at`. Comments are immutable — the audit trail is court-defensible.
- Frontend:
  - `VerifyPathway.jsx` now shows a "Reviewer comments" section under a successful verification. Existing comments appear as a card list; a collapsed "Add a professional comment" form opens on click and collects role (pill selector), name, optional organisation, and comment text (4000 char max). Immutable-warning copy included.
  - New `PathwayReviewerCommentsCard.jsx` mounts on the Dashboard right after `PathwayReportCard`. Self-hides when no comments exist; otherwise shows up to 3 newest comments inline with reviewer name / role / org / date + a `X new` chip + a CTA to the full pathway report. Older comments accessible from the report page.
- Tests: `/app/backend/tests/test_iter98_pathway_reviewer_comments.py` — 6/6 green (user-isolation with real Mongo insert + cleanup, unknown-sig-id 404, body validation 422, unknown-sig-id public GET returns empty list, authed feed requires auth, full end-to-end loop: preview PDF → public POST → public GET → parent-authed feed all show the same row and never leak `ip_hash`). 80/80 tests across iter90–iter98 still green — zero regressions.

### Admin Drilldown PDF Export — court-ready case history (Feb 2026 · iter99)
- Admins can now download a full ND Risk case history as a court-ready PDF straight from the drilldown drawer they use to inspect an active case. Mirrors the visual system of the existing per-assessment `nd_risk_pdf.py` (same tier colours, cover, informational-only disclaimer) but iterates every assessment newest-first plus the coordinator alert audit trail.
- New backend endpoint `GET /api/admin/nd-risk-coordinator/case/{target_user_id}/pdf` — admin-gated via `require_admin`, 404 on unknown target, returns a proper `application/pdf` blob with `Content-Disposition: attachment; filename="nd-case-history-{id}.pdf"`.
- Refactored `admin_case_history` to share `_build_case_payload()` with the new PDF endpoint so JSON and PDF stay in lockstep — a change to the drilldown payload can never silently drift the PDF.
- PDF sections: cover page (parent name, id, assessment count, latest date, generated-by admin), case summary strip (most-recent tier pill + tier distribution), coordinator alert audit trail (delivered / failed rows), assessment history newest-first with "LATEST" badge + tier pill + sub-scores (two-column threat vs vulnerability) + free-text notes. Never leaks raw matrix answers, IP hashes, or account metadata — only derived scoring already exposed via the drilldown JSON.
- Frontend: `CaseDrilldown` drawer header gains a "Court-ready PDF" gradient button next to the close button, only shown when the case has ≥1 assessment on file. Downloads as a Blob with the parent's target_user_id in the filename. Toast confirms success; spinner state while building.
- Tests: `/app/backend/tests/test_iter99_admin_drilldown_pdf.py` — 6/6 green (builder handles empty-history + full-multi-row scenarios producing valid `%PDF-` bytes, endpoint requires auth 401, refuses non-admin parent 403, 404 on unknown target, admin gets `application/pdf` blob with `Content-Disposition: attachment` and target_id embedded in filename and multi-KB payload). 23/23 across every admin ND suite (iter93–99) still green.

### Compare Invite Nudge Reminder — weekly cron (Feb 2026 · iter100)
- Parents who send a Compare Share request that stays in `awaiting_partner_consent` for more than 7 days now receive a warm, no-blame reminder email once every 7 days. Drives Compare adoption which unlocks the two-parent Pathway Report for actual mediator hand-off.
- New backend module `compare_invite_nudge.py` — sweeps every share collection (`edu_deep_shares`, `psych_deep_shares`, `med_deep_shares`, `snc2_shares`), filters to stale awaiting-consent rows, and dispatches via a new email template. Dedupe collection `compare_invite_nudge_sends` prevents double-sends within a rolling 7-day window per share_id.
- Suppression rules locked with tests: fresh share (<7d) skipped, already-consented share skipped, `@demo.local` / `@guest.local` / missing creator email skipped, outside Monday 08–22 UTC send window short-circuits (unless `force_window=True` for operator preview), feature flag `COMPARE_INVITE_NUDGE_ENABLED` defaults off to prevent accidental prod send on rollout.
- New email template `send_compare_invite_nudge()` in `email_service.py` — warm framing ("A quick friendly note — your request is still waiting"), three-option list (message the co-parent outside the app / resend or cancel in Compare Hub / do nothing), computes and shows the request age in days, "no pressure" copy prevents dunning tone.
- Long-running loop `compare_invite_nudge_loop(app)` registered in `server.py`; hourly sweep window Mon 08-22 UTC same as compliance reminder (staggered 30s so both don't hit DB simultaneously). Backend boot confirmed clean — loop currently idle awaiting the ops flag flip.
- Tests: `/app/backend/tests/test_iter100_compare_invite_nudge.py` — 9/9 green (real-email guard, Monday 08-22 UTC window, feature flag defaults off, outside-window short-circuit, stale-share dispatch + dedupe on 2nd sweep, fresh-share skip, already-consented skip, `@demo.local` skip with clean dedupe collection, all 4 share collections iterated on the same sweep).

### Trend Sparkline — coordinator escalation arc (Feb 2026 · iter101)
- The admin drilldown drawer now shows a pure-SVG sparkline of the parent's `total_score` (0-16) across every assessment on file, above the assessment list. Points are coloured by tier, connecting line is neutral indigo, and shaded tier bands sit behind so the reader instinctively reads "how deep did they get into the critical zone".
- Renders only when the parent has ≥2 assessments — a single point on a chart says nothing about escalation.
- Header shows the score delta with tone-coded arrow: red ↑ for worsened, green ↓ for improved, grey → for unchanged. Delta is computed vs the OLDEST assessment on file, not vs the second-newest, so the coordinator sees the full arc.
- Hover title on each dot shows tier label, score, and `created_at` — legible without a chart library and works with browser accessibility tools out of the box.
- Deliberately no chart library — keeps the drilldown drawer light so an admin scanning through active cases doesn't wait on chart bundle chunks between clicks.
- No new backend endpoint needed — reuses the existing drilldown JSON payload's `history` field which already returns `total_score`, `tier`, `tier_label`, and `created_at` per row. All 32 tests across admin ND suites (iter93-100) still green — zero backend regressions.

### Safety Assessment · Four AI-Summary Components (Feb 2026 · iter102)
- The Family Violence & Communication Safety Assessment PDF now includes **four AI-generated narratives** on top of the existing structured content, produced from the parent's actual answers by Claude Sonnet 4.5 via the Emergent LLM key:
  1. **Executive summary** at the top of the report (~180 words, mediator/professional audience) — one-sentence framing, safety signals at a glance, communication readiness at a glance, whether the recommended pathway is a fit, one child-focused closing line.
  2. **Pathway summary** (2-3 sentences) inside the Recommended pathway block explaining WHY that specific level's pathway is a fit given the answers.
  3. **Section 1 · Immediate safety screen summary** (~90 words) — plain-language narrative of the safety indicators the parent surfaced.
  4. **Section 2 · Communication readiness summary** (~90 words) — strengths and areas that would need structured support before consensual co-parent communication is likely to hold.
- New module `safety_ai_summary.py` — mirrors `ai_summary.py` (deep-dive executive summary) but produces the four-key dict shape. Same strict guardrails: neutral parent-attributed tone, non-diagnostic, non-adjudicative, no legal/medical advice, NEVER minimise a concrete safety indicator, no jargon, no fabrication.
- Summaries are cached on the assessment doc under `ai_summaries` after first successful generation so subsequent PDF downloads are instant. Failed / partial generation is retried on next download rather than locked in (prevents "sad empty state" from an intermittent LLM outage).
- Renderer is fully graceful — a missing `EMERGENT_LLM_KEY` or a partial `ai_summaries` dict still produces a valid PDF with the AI blocks silently omitted.
- Live curl verified: parent1's 995 KB PDF renders end-to-end via `GET /api/safety-assessment/{id}/pdf` with `%PDF-1.3` header intact.
- Tests: `/app/backend/tests/test_iter102_safety_ai_summaries.py` — 6/6 green (builder accepts new kwarg + renders valid PDF; builder still works without kwarg; partial/empty keys handled cleanly; long AI copy materially increases PDF size — proving the copy actually lands on the page; generator returns the four-key dict shape even without an LLM key; empty sections short-circuit without wasting an LLM call).

---



- **Auth**: `/api/auth/*` (JWT + Emergent Google Auth)
- **Co-Parenting**: `/api/coparenting/*`
- **Safety**: `/api/safety-assessment/*`
- **Invites (general)**: `/api/invites/*`
- **Coach**: `/api/coach/*`
- **Insights / admin**: `/api/insights/*`

## Test credentials
See `/app/memory/test_credentials.md`.
