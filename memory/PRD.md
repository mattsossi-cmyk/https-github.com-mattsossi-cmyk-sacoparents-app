# SA CoParents — Joint Alignment Report Platform

## Original Problem Statement
Build a universal 10-page Joint Alignment Report system for co-parents. Every report is visually familiar: Page 1 overview + Joint Alignment Snapshot, Page 2 child at the center, Page 3 alignment (green), Page 4 differences in perspective (table), Page 5 child needs, Page 6 options & resources (options, not recommendations), Page 7 questions for parent conversation (positions → questions), Page 8 professional conversation guide (6-step sequence), Page 9 parent action plan worksheet (top 3 issues), Page 10 alignment summary map + "Alignment Before Agreement" philosophy + the line "We value the parenting system by how well it supports the child, not by how friendly the adults appear." Eight assessment types: General Co-Parenting, Communication, High-Conflict, IPV/Family Violence (safety-first variant titled "JOINT COMMUNICATION & SAFETY CONSIDERATIONS REPORT" with distinct page titles and disclaimer), Medical, Educational, Psychological/Behavioral (observation language, no diagnosis), Preparing for Court/Parenting Structure (agreed/close/discussion/info buckets).

## User Choices
- Parents take structured assessments; demo/simulator pre-filled sample data available
- Rule-based template generation (no AI/LLM)
- All 8 assessment types in v1
- Printable/downloadable report (browser print → PDF, print CSS with page breaks)
- Simple JWT login (email/password, httpOnly cookies)

## Architecture
- Backend: FastAPI + MongoDB (motor). `/app/backend/server.py` (auth + cases + report API), `assessment_data.py` (8 type configs: topics, scales, options, needs, page titles, disclaimers, demo payloads), `report_engine.py` (rule-based report builder; per-topic status: aligned / close / different / info).
- Frontend: React + Tailwind + Shadcn UI. Pages: Landing, Auth, Dashboard, Wizard (4 steps), ReportView (10-page paper-style viewer + print). `src/components/report/Pages.jsx` (10 page components), `Paper.jsx` (paper shell, Snapshot donut via recharts).
- Auth: JWT access (30 min) + refresh (7 d) httpOnly cookies, bcrypt, brute-force lockout, admin seeded from env.
- Design: Organic & Earthy (Cormorant Garamond headings, Work Sans body, #344E41 primary, status colors green #668B69 / yellow #D4B46A / blue #6096BA / purple #9A8C98). Guidelines at /app/design_guidelines.json.

## User Personas
- Parent A / Parent B: complete identical assessments; receive the joint report.
- Professional (mediator, attorney, therapist, parenting coordinator): uses Page 8 discussion map and the full report as a session roadmap.
- Admin: platform owner (mattsossi@bsossi.com).

## Core Requirements (static)
1. Universal 10-page report structure across all assessment types.
2. Alignment snapshot: counts of aligned / different perspectives / need-more-information — "not scores, a roadmap for conversation."
3. Differences framed as "differences in perspective", never conflicts/failures.
4. Everything child-centered; options framed as "options to explore", not recommendations.
5. IPV variant prioritizes safety over agreement.
6. Print-ready output.

## Implemented (2026-08-31)
- JWT auth (register/login/logout/me/refresh), admin seeding, brute-force lockout
- All 8 assessment type configs with 10 topics each, type-specific options/needs/central questions
- Case creation, per-parent responses, demo data fill, report generation
- 10-page report viewer with paper aesthetic, snapshot donut, page navigation, print-to-PDF
- Dashboard with case list, completion status chips, demo badge, delete
- Landing page with 10-page architecture strip and 8-type grid
- Testing: backend 20/20 pytest, frontend critical flows verified (test report: /app/test_reports/iteration_1.json)

## Test Credentials
See /app/memory/test_credentials.md. Admin: mattsossi@bsossi.com / CoParents2026!

## Backlog
### P0
- None outstanding.

### P1
- Editable Page 9 action plan (fill fields in-app, persist, print filled version)
- Shareable read-only report link for professionals (token-based)
- Unicode font embedding for PDFs (non-Latin-1 names render as ?)
- Live end-to-end cross-app test once sacoparentsapp.online implements the integration spec

### P2
- Reassessment over time ("Reassess & adjust as the child grows") with comparison between report versions
- Workbook integration referenced in spec (Page 9 → SA CoParents workbook)
- Professional dashboard view across multiple families
- Email notifications (Resend) for invitations and report-ready events

## Next Tasks
1. Let the user review the 10-page report content/copy per type and adjust wording.
2. Implement P1 sharing/invite flow when user confirms priority.

## Implemented (2026-09-02) — Universal Joint Report Builder + Invitations
- Invite Co-Parent flow: 6-char codes + token links, email via managed Resend, accept by code or /join/{token} (invitee email must match account), resend/cancel/change-subject, family connections (separate accounts, connection cards on dashboard)
- Universal Joint Report Builder: 13 subjects (incl. custom), 3-step wizard (subject → child → invite), 6 free-text questions, rule-based report with keyword-overlap alignment heuristic (10 sections per spec), privacy enforced (partner answers never exposed; report gated until both complete)
- Professional tools: POST /api/joint/reports/professional invites both parents; parents can share completed reports with professional accounts by email
- Dashboard redesigned: Individual Tools + Joint Tools cards, "Already invited? Enter Invitation Code", connections, joint status cards
- Confidentiality notice (verbatim from sacoparentsapp.online) on register, private assessments, and joint assessments
- Auth supports ?next= redirect for invitation links
- Files: backend/joint_data.py, backend/joint_engine.py, joint endpoints in server.py; frontend pages JointNew/Join/JointAssessment/JointReport, Dashboard rewrite, components/ConfidentialityNotice.jsx
- Testing: see /app/test_reports/iteration_4.json

## Implemented (2026-09-02, later) — Agreements, Professional Requests, Privacy Policy, External Prefill
- Co-parenting agreements: POST /api/joint/agreements (kind="agreement", 8 AGREEMENT_AREAS), both parents propose terms privately, generate_agreement() (Likely aligned/Close/Needs discussion), agreement PDF (build_agreement_pdf). Dashboard "Invite Co-Parent to Joint Agreement" button; /joint/new?kind=agreement wizard; agreement-document view in JointReport.
- Contact-a-professional (family violence): GET /api/professionals, POST/GET /api/joint/professional-requests, POST .../prepare (professional creates all-safety-subjects report, invites BOTH parents; parents don't see it pre-accept; double-prepare 400; parent prepare 403). Dashboard red "Contact a Professional" card + pro inbox with Prepare.
- Safety styling (iteration-8 gaps FIXED): JointReport red title + jr-safety-notice banner; Wizard IPV card red border; Pages.jsx IPV report-title red.
- Privacy page: /privacy — full 32-section "Privacy, Confidentiality & Data Protection Policy" mirrored from sacoparentsapp.online, adapted to Align (rule-based, no AI; providers: Emergent/MongoDB Atlas/Resend) with formal Section 31 Notices provision. Linked from ConfidentialityNotice (all forms) and Landing footer.
- External prefill: GET /api/external/assessments (fetch_external_export helper shared with joint import); Wizard ParentForm "Load my saved answers" panel (linked accounts only) pre-fills primary concern + shows saved assessments/statements as reference.
- Tests: tests/test_agreements_and_pro_requests.py (5), tests/test_external_assessments.py (5). Suite: 87/87. QA: iteration_9.json (backend 82/82, frontend 100%).
- Email stays on Emergent managed proxy (delivers to any recipient on platform-verified domain); user-offered BYO Resend key declined per platform email guardrails (2026-09-02).

## BLOCKED — sacoparentsapp.online export endpoints
Probed 2026-09-02: /api/link-codes, /api/integrations/* on sacoparentsapp.online all return 404 — NOT implemented. User must open the other Emergent project and have its agent implement /app/SACOPARENTSAPP_ONLINE_INTEGRATION_SPEC.md (shared secret + 3 endpoints). Until then: link attempts 400, imports/prefill 502.

## Implemented (2026-09-02, final) — Poster circles + individual assessments moved to import-only
- Landing five pillars (REFLECT/ALIGN/COMMUNICATE/CO-PARENT/THRIVE) are now large filled colored circles matching the uploaded poster (bg-brand-purple/teal/green/orange/blue, white icon inside, label below). "Try the demo report" hero button removed.
- In-app individual assessments REMOVED per user decision: /new wizard route + Wizard.jsx deleted; Dashboard "Start a Private Assessment" card replaced with "Import from sacoparentsapp.online" card (link-code input + linked state + unlink); legacy cases section only renders when data exists ("Previous Private Assessments", view/delete only, no continue/demo); CompleteReport empty state now points to /joint/new.
- Imported sacoparentsapp.online data is used ONLY inside Joint Reports (user decision — no individual views).
- Backend case endpoints intentionally kept for legacy data; no new cases can be created via UI.
- QA: /app/test_reports/iteration_10.json — frontend 100% (6/6): circles render in brand colors, /new cleanly redirects to /, import card works with graceful 400 on bogus codes, legacy cases show view/delete only, hub + joint flows unaffected. Follow-up fixes: link code enforced to exactly 8 chars; duplicate empty-state button in CompleteReport removed.

## Deployment Readiness (2026-09-02)
- Deployment agent scan: PASS. Fixed 2 N+1 blockers (list_joint_reports batched invitation lookup via $in; list_connections batched user lookup via $in) — verified live (both endpoints 200 with correct data) and 87/87 pytest green.
- /health returns 200; all env vars in .env; no hardcoded secrets; CORS/admin seed/supervisor all OK.
- Added /app/.gitignore (keeps memory/test_credentials.md and env files out of git).

## Implemented (2026-09-03) — Scheduled completion notification emails
- Platform cron (.emergent/crons.yml, every 15 min) calls POST /api/cron/completion-nudge — Bearer-authed via WEBHOOK_CRON_SECRET (constant-time compare, 401 on fail), run_id idempotency in db.cron_runs, acks 2xx immediately and backgrounds the work (asyncio.create_task).
- run_completion_nudges(): (a) half-complete reports (>15 min, <48 h since completion) email the other parent "Your co-parent has completed their half" (once per side, nudges.{side} flag); (b) ready reports (<48 h) email BOTH parents "Your Joint Report is ready" with report link (per-side ready_notified map, set only on successful send). Emails use the managed proxy + fixed templates (guardrail-compliant).
- Verified: endpoint 401/401/200/duplicate-idempotent; unit run with stubbed send = correct recipients/flags, 2nd run no-op, stale(>48h) + fresh(<15min) correctly skipped. Backend suite 87/87.
- Data hygiene: deleted ~1k test users + 430 test joint_reports etc. from preview DB; unset 95 scalar ready_notified fields from the first (buggy) run; rewrote tests/test_pdf_report.py to be self-contained (no shared fixtures).

## Deployment (2026-09-03)
- Final deployment-agent scan: PASS, zero findings (cron endpoint, WEBHOOK_CRON_SECRET, crons.yml, .gitignore all verified; N+1 fixes confirmed). Live: /health 200, frontend 200, cron endpoint 401-guarded.
- User instructed to deploy via the Emergent Deploy button; crons.yml syncs the schedule automatically on deploy.

## Implemented (2026-09-03, later) — ALL reports now download as server-generated PDFs
- User reported blank printouts for family-violence demo reports. Root cause: the 10-page individual report (ReportView.jsx) and Complete Report (CompleteReport.jsx) still used browser window.print() (the old blank-print bug); only joint reports had server PDFs.
- Added build_case_pdf (10-page individual report incl. IPV/family violence) and build_complete_pdf (aggregated Complete Report) to backend/pdf_report.py.
- New endpoints: GET /api/cases/{id}/pdf (owner-only, 400 until both parents complete, filename alignment-report-<child>.pdf) and GET /api/reports/complete/pdf (400 when empty).
- Frontend: ReportView "Print / Save PDF" and CompleteReport "Print" buttons now download the server PDF (<a download>); JointReport/agreement PDF buttons unchanged (already server-side).
- Verified live: IPV demo case PDF 200 + %PDF magic + full text markers; Complete Report PDF 200 via browser fetch; safety joint PDF full 3-page content. tests/test_pdf_report.py extended (TestCasePdf + TestCompletePdf) — pdf suite 8/8, full suite 90 passed (3 test_report_shape.py setup errors were transient login-lockout 429s from repeated suite runs, not code).
- Answer to "can all demos be downloaded as PDF": YES — individual 8 types, joint/focused/customized, safety (family violence), co-parenting agreement, and Complete Report.

## Implemented (2026-09-03, final) — Badge-circle navigation (user's uploaded design)
- New reusable frontend/src/components/CircleNav.jsx: two large CSS-recreated badge circles — purple UNIFORM ASSESSMENT ("Understand. Align. Support Your Child.") and teal FAMILY VIOLENCE ASSESSMENT ("Prioritize Safety. Plan for Protection.") — ringed by 8 colored bubble buttons in an ellipse on desktop (grid fallback on mobile, circle-nav-mobile).
- Placement: Hub (/hub, fully rewritten — old cluster/multi-select UI removed) AND Dashboard (circle-nav-section as the main action area above the tools grid).
- Behavior: uniform circle → /joint/new?subjects=<all 7 non-safety> (full joint assessment); subject bubbles → /joint/new?subject=<key>; Complete Report bubble → /hub/complete; safety circle → parents: /dashboard?contact=professional (Dashboard auto-opens the contact-professional form via useSearchParams effect), professionals: /joint/new?subject=safety.
- Smoke-verified via browser: layouts on both pages, all three navigation flows, pro form auto-open. Testing agent iteration 11 for full frontend regression.
- QA iteration_11.json: frontend 100%, zero bugs; old hub testids confirmed removed; pro/parent branching + mobile fallback verified.
- Added connecting dashed ellipse ring (SVG, circle-nav-ring) behind the bubbles per user request — passes through all bubble centers; screenshot-verified.

## Deployment (2026-09-03, second scan)
- Deployment agent re-scan after badge-circle/PDF changes: PASS, zero findings (compilation clean, no Wizard.jsx references remain, env/CORS/supervisor/query limits all OK). Live: /health, /, /hub all 200.
- Suite green: 93/93. App is ready — deployment itself is user-triggered via the Emergent Deploy button.

## Deployment (2026-09-03, final scan)
- Third scan caught ONE blocker: my .env/.env.* gitignore entries — this platform TRACKS .env files in git and auto-updates them with production values at deploy time. Removed those lines (memory/test_credentials.md stays ignored). Re-scan: PASS, zero findings. Live probes: /health, /, /privacy all 200.
- CLEARED TO DEPLOY — user clicks the Deploy button.

## PRODUCTION LIVE (2026-09-03)
- Deployment confirmed live: https://align-report.emergent.host — /health 200, / 200. Deployment log scan: no /health 404s, no startup errors, no 5xx patterns (the old /health 404 issue is confirmed resolved in production).
- Production smoke test: 11/11 PASS — register ×2, joint report create, code accept, both parents submit, status ready, report content, PDF download (4164 bytes, full text, not blank).
- sacoparentsalign.com currently returns 301 (DNS propagation/final mapping pending).
- Completion-nudge cron ships with deploy; first prod fire within 15 min of qualifying activity.

## Bug Report Resolved (2026-09-03) — "circles not visible"
- User reported missing circle buttons. QA iteration_12.json (frontend 100%): circles render and route correctly on PRODUCTION (align-report.emergent.host) desktop + mobile; deployed bundle contains the code.
- ROOT CAUSE: environmental — sacoparentsalign.com (apex + www) is still a Squarespace "Coming Soon" parked page, NOT connected to the Emergent deployment. User was viewing the parked domain. NO code bug.
- Fix path: connect custom domain in Emergent (Settings/Deploy → Custom Domain) and update Squarespace DNS to point at the deployment; until then use https://align-report.emergent.host.

## Health Check (2026-09-03, latest)
- Deployment agent scan: PASS, zero findings (no code changed since last pass).
- Live probes: prod /health 200, prod frontend 200, prod cron endpoint correctly 401-guarded, preview /health 200.
- NOTE: public /health on the domain serves the SPA index.html (200) because ingress routes non-/api paths to the frontend; the platform's backend health probe hits the backend directly where /health returns the JSON. Not an issue.

## Implemented (2026-09-04) — Invite-per-button, email-to-professional, FV email-less flow, per-button confidentiality
- Confidentiality notices on every action button: badge microcopy (circle-uniform-notice / circle-safety-notice), shared ring line (circle-nav-confidentiality), full ConfidentialityNotice on the JointNew invite step (jointnew-confidentiality).
- Non-FV action buttons all lead to the co-parent invite flow (unchanged behavior, now explicit in copy).
- Share endpoint POST /api/joint/reports/{id}/share now also emails the professional a report link (guarded send); JointReport button relabeled "Email to professional".
- FV flow: parent contact-professional form no longer collects the other parent's email (ProRequestIn optional fields; pro-privacy-note copy); professionals enter both parents' emails at PREPARE time (PrepareIn body; pro-prepare-email-a/b inputs; 400 if missing). Legacy requests with co_parent_email still prepare without a body.
- Tests: tests/test_pro_share_updates.py (5 new). Suite: 98/98.
- QA iteration_13.json: backend 97/97 relevant + frontend 100% — all six flows verified. Fixed the one review note: Dashboard contact=professional effect now deps on [searchParams] and guards !showProForm, so clicking the teal safety circle from within the dashboard auto-opens the form without a refresh (screenshot-verified).

## Implemented (2026-09-04) — Third major circle (Co-Parenting Agreement) + 4-bubble ring + Foundation merge + Shared With Me
- CircleNav rewritten: THREE major circles — purple UNIFORM ASSESSMENT (all 15 non-safety subjects), GREEN CO-PARENTING AGREEMENT (circle-agreement → /joint/new?kind=agreement), teal FAMILY VIOLENCE ASSESSMENT. Bubble ring is now exactly 4 real subject keys: education (Educational), medical (Medical), psychological (Psychological), co_parenting (General Coparenting Assessment). Old bubbles removed (school/conflict were invalid keys); Complete Report moved to a text link (circle-nav-complete-link).
- Foundation Statements merge: JointAssessment agreement step has foundation-card ("Pull in my Foundation Statements" for linked accounts); PUT responses accepts foundation list (agreement kind only); generate_agreement returns foundation_statements; build_agreement_pdf renders a Foundation Statements section before Signatures. External source (sacoparentsapp.online) still pending its endpoints — pipeline testable via direct API PUT.
- Professional dashboard: "Shared With Me" section (joint_public.shared_with_me) listing reports parents emailed/shared to them.
- Tests: tests/test_foundation_merge.py (3 new). Targeted runs green (13/13).
- QA iteration_14.json: frontend 100%, backend 100/101 — one pre-existing bug found and FIXED: GET /api/professionals hard-capped at .to_list(100) while test accumulation left 110+ pro accounts, truncating new pros from the dropdown. Fixed (sorted by name, cap 500) + removed 133 test pro accounts from preview DB.
- CircleNav polish per user: every major badge now has an action pill (Start Assessment / Build Agreement / Request Professional) and the FAMILY VIOLENCE badge is RED (border-red-700/text-red-700, pill bg-red-700). Screenshot-verified.

## Implemented (2026-09-04, later) — Professional share links + brand tagline
- Professionals now get copyable per-parent share links after creating ANY joint report (POST /api/joint/reports/professional returns invitations[{role, code, link(/join/<token>), invitee_email}]); JointNew shows a "Parent Links Ready" card (pro-share-link-a/b, copy-link-a/b-btn) with ConfidentialityNotice instead of just a toast. Parent invite success card now also displays the invitation link (invitation-link-display + copy-invite-link-btn). Works for all subjects/buttons.
- Brand tagline updated: "Step 2 - Professional Corner - Joint Reports for Coparents" (italic dark green, landing header, data-testid brand-sub).
- Tests: tests/test_pro_share_links.py (3 new).

## Implemented (2026-09-04, final) — Professionals invitation section + QA iteration 15
- Landing: "An Invitation to Professionals" section (professionals-invite) above the footer — verbatim user copy, 4 report-content cards, "Your Role as a Professional", professional-community CTA (pro-join-btn → /auth), script motto line. Screenshot-verified.
- QA iteration_15.json: share links verified end-to-end. CRITICAL env bug found+fixed by testing agent: supervisord.conf baked a stale APP_URL (dead preview domain) which silently overrode backend/.env (dotenv override=False) — all /join/ share links pointed to an unreachable host. Fix: load_dotenv(override=True) in server.py. KEEP THIS. If APP_URL ever changes, verify pro share links use the right domain.
- Open minor item: Dashboard pro-select renders a <span> inside <option> (React hydration warning) — fix pending. (Later verified clean in source — stale bundle warning.)

## Production staleness finding (2026-09-04)
- Full prod smoke on align-report.emergent.host: core flows pass (register/joint/PDF/share), but prod runs the 2026-09-03 build — FAILS: pro share links (no invitations in response), foundation merge (no foundation_statements), FV request without co-parent email (422 — old ProRequestIn). Preview has all of these (tests green). USER MUST REDEPLOY (Deploy button) to ship the 09-04 rounds.
- Custom domain: sacoparentsalign.com A record resolves (104.18.14.241) but HTTP unreachable — domain still NOT linked in Emergent (Link domain/Entri step pending); www has no record yet.
- 2026-09-04 later: re-probed prod after user said they redeployed — STILL the old build (FV-no-email 422, no pro invitations, no foundation_statements). Deploy either not clicked, still building, or failed. Delayed probe scheduled → /app/prod_probe.log. Waiting on user confirmation that the deploy completed.

## Deploy blocker found & fixed (2026-09-04, final)
- Root cause of the "redeploy not landing": the iteration-15 fix used load_dotenv(override=True), which the deployment gate BLOCKS (would override K8s env vars). Deploy was failing on this blocker.
- Surgical fix (committed 8de5b20): plain load_dotenv() (K8s wins) + _APP_URL_FILE = dotenv_values(.../.env).get("APP_URL") used only by app_url() — keeps the preview stale-supervisor workaround without touching os.environ. WEBHOOK_CRON_SECRET quoted (WARN fix). Deployment re-scan: PASS, zero findings. Preview link-generation verified (invitation links use the correct host).

## PRODUCTION NEW BUILD VERIFIED (2026-09-04, iteration_16.json)
- User redeployed after the blocker fix; prod now runs the current build. Testing agent: 10/10 backend + 100% frontend smoke on https://align-report.emergent.host — share links (2 /join/ links, correct prod host, join page renders), foundation merge (report + PDF section), FV email-less flow (200 / 400 / 200), core cycle + non-blank PDF, share-to-pro, cron 401 guard, config, tagline, pillars, journey strip, professionals invite, 3 circles (safety red) + 4 bubbles.
- Prod verification suite: /app/backend/tests/test_prod_verification.py (run with REACT_APP_BACKEND_URL=https://align-report.emergent.host; needs browser-like User-Agent).
- Note for future: share endpoint body key is 'email' (FV request uses 'professional_email') — cosmetic inconsistency only.
- Custom domain: apex + www both resolve to 104.18.14.241 now; HTTP still unreachable until the Emergent "Link domain" registration completes (no vhost/SSL yet).
- Brand.jsx now supports an optional `sub` prop (renders italic dark-green text under the wordmark); Landing header uses `sub="Step Two"` per user request. Screenshot-verified (italic / rgb(22,101,52)).
- Landing hero swapped: poster image now LEFT, text RIGHT (md:order-first/last). Single hero image confirmed.
- Landing journey strip (journey-strip): Step One card → links to sacoparentsapp.online ("Complete your private assessments in the SA CoParents app"), Step Two card → "You are here" (Align). Screenshot-verified.

## Joint PDF re-verified (2026-09-04, user asked "can I have a PDF of the joint alignment report")
- Re-confirmed feature exists and works: GET /api/joint/reports/{rid}/pdf (fpdf2, server-side) + download button on report view in JointReport.jsx (line ~111, <a download>).
- Live curl E2E on production URL: registered 2 fresh parents → created joint report (subject "communication") → B accepted invite code → both submitted responses → status "ready" → PDF download HTTP 200, application/pdf, 4170 bytes, valid %PDF- header. Keyword grep on raw bytes fails because fpdf2 FlateDecode-compresses content streams (expected, not a defect).
- Auth note for curl testing: /api/auth/register + /login set httpOnly cookie `access_token` (no token in body) — use -c/-b cookie jars, not Bearer extraction.

## Sample Mediation Statement + Mediation Statement subject (2026-09-05)
- User request: sample mediation statement report in the Align app — BOTH a public sample preview AND the real generator, reusing joint report structure (alignment / differences in perspective / meeting child's needs / options & resources).
- Real generator: joint subject "mediation" relabeled "Mediation Issue" → "Mediation Statement" in backend/joint_data.py (flows through JointNew subject picker, report, PDF).
- Sample: joint_engine.sample_mediation_report() runs fictional parents (Jordan M./Casey M., child Avery) through generate_joint_report with subject "mediation"; overrides title="Sample Mediation Statement", is_sample=True, mediation-specific purpose. Public endpoints (no auth): GET /api/joint/sample/mediation (JSON), GET /api/joint/sample/mediation/pdf (filename sample-mediation-statement.pdf). build_joint_pdf renders "SAMPLE - fictional example data" line when is_sample.
- Frontend: new public page /sample-mediation (frontend/src/pages/SampleMediation.jsx, testids sample-mediation-*/sm-*) rendering Purpose, Alignment, Differences, Child's Needs, Options/Resources, Next Steps + Download Sample PDF btn + Get Started CTA; route added in App.js; Landing professionals-invite section gained "Preview a Sample Mediation Statement" outline button (data-testid=sample-mediation-btn).
- Verified: py_compile OK; sample report = 5 alignment stmts, 1 difference (Concerns), varied alignment map; both endpoints 200 public (PDF valid %PDF-, 4982 bytes); preview screenshots: sample page all sections PASS, landing button PASS. Production (align-report.emergent.host) still old build until user redeploys.

## Landing hero image replaced (2026-09-05)
- User uploaded new poster "SA CoParents ALIGN FOR PROFESSIONALS — Building on Different Perspectives, Creating a Shared Future" (800x800 PNG) and asked to replace the hero image.
- Saved to /app/frontend/public/align-pro-poster.png; Landing.jsx POSTER_IMG now "/align-pro-poster.png" (local public asset, was external artifact CDN URL); alt text updated to match new poster. Screenshot-verified on preview: natural 800x800, renders left of hero text. Old artifact URL no longer referenced.
- Same request batch: landing hero CTA button text changed "Start a Joint Assessment" → "Create Joint Report" (Landing.jsx line ~81, data-testid hero-cta-btn).

## Professional Alignment Case workflow + App→Align case integration (2026-09-05)
- User spec: professional creates Joint Alignment Case with Parent A email + Parent B email + report type + optional private case reference; Align auto-generates the Alignment Code (SA-XXX-NNNNNN, e.g. SA-EDU-482731) and emails each parent separately; token link is primary, case code is backup; pro dashboard shows per-parent status, Send Reminder per parent, Generate Report when both complete. Long-term model: parents complete assessments on sacoparentsapp.online, which pushes status/comparison data to Align via secure API (raw answers stay in the App DB).
- Backend (server.py): new_case_code() with SUBJECT_CODE_PREFIX map (AGR for agreements, ALN for multi); case_code stored on ALL joint docs (parent reports, pro reports, agreements, FV prepare). ProJointReportIn.case_reference (creator-only visibility in joint_public). create_invitation(code=, via_professional=): both pro invitations share the case code. send_invite_email rewritten to user's copy ("Invitation to Complete Your SA CoParents Assessment", participation code, Complete My Assessment button, privacy paragraph, do-not-forward note); link base env-gated: SACOPARENTS_APP_ASSESSMENT_URL (unset → Align /join/<token>; set → App /assessment?invite=<token>). Accept endpoint: token-first, then code+invitee_email match (shared-code email disambiguation), 403 if code belongs to another email. list/detail endpoints return pending_invitations[] for creators.
- New integration endpoints (X-Integration-Key = INTEGRATION_SHARED_SECRET): GET /api/integrations/case-invite/{token} (App resolves case→parent→assessment→professional), POST /api/integrations/case-update {token, status started|completed, assessment_id, responses} (completed stores responses.{role} imported + external.assessments for theme analysis; both complete → status ready + "Generate Joint Alignment Report" email to professional).
- Frontend: JointNew pro form + case-reference-input; created card shows Alignment Case + "Status: Waiting for both parents"; parent card label "Invitation code"→"Alignment Code". Dashboard: code input placeholder e.g. SA-EDU-482731 maxLength 12; joint cards show joint-case-code-<id> and joint-case-ref-<id> (private); per-parent "Send Reminder — name" buttons (joint-remind-btn-<id>-a/b); rows "Awaiting completion"; ready pro view button reads "Generate Report". JointReport page shows Alignment Case + private case ref.
- Spec updated: /app/SACOPARENTSAPP_ONLINE_INTEGRATION_SPEC.md "Case-based flow" section (App-side to-dos for the other project).
- Verified: /app/scripts/test_case_workflow.py — ALL CHECKS PASSED (E2E: SA-EDU-NNNNNN shared code, wrong-email 403, integration 401/200, started→in_progress→ready, pro sees case ref / parent doesn't, report+PDF from imported material, parent flow SA-COM code). Existing pytest pro/share/foundation files: 11/11 pass. Testing agent iteration_17: 100% frontend — all 5 flows pass. It found+fixed one HIGH bug: invitation-code-input maxLength was 12, truncating 13-char SA-XXX-NNNNNN codes (blocked all parents joining by code); raised to 13, then hardened to 16 by main agent per its recommendation.

## Deploy/domain/secret round (2026-09-05)
- INTEGRATION_SHARED_SECRET rotated in backend/.env (old value was exposed in chat; new value never printed). Backend restarted; full case-workflow E2E re-ran green against the new secret. Spec notes the rotation; the other project must copy the new value from protected env settings.
- deployment_agent scan: PASS, zero blockers (env config, CORS, compile, supervisor, no hardcoded secrets). Ready for user to click Deploy.
- Custom domain sacoparentsalign.com + www: still TLS-fail/409 — not linked on Emergent side. support_agent guidance: Deployment → Link domain → enter domain → click "Entri", REMOVE ALL A RECORDS at the DNS provider first (critical commonly-missed step), repeat for apex + www, SSL 5-15 min (up to 24h), then support@emergent.sh if unresolved.
- App-side implementation (token resolution screen, private assessment, case-update push, link-code/export endpoints) must be done in the SEPARATE sacoparentsapp.online project — cannot be edited from this workspace. Hand it /app/SACOPARENTSAPP_ONLINE_INTEGRATION_SPEC.md.

## Professional-only repositioning (2026-09-06, user directive)
- Align is now professional-exclusive: "App = parents reflect; Align = professionals align." Parents participate ONLY via secure invitation (token link primary, SA-XXX-NNNNNN case code backup).
- Backend gates (server.py): POST /auth/register — role defaults to professional; role=parent requires a pending invitation matching invite token/code + email, else 403. POST /joint/reports + /joint/agreements — professional-only (403 for parents); existing parent-created reports remain viewable. create_agreement rewritten: professional provides both parents' names/emails; both parents are participants, pro is case owner; two invitations share the SA-AGR-NNNNNN case code; response now returns invitations[] (was single invitation). create_pro_joint_report now sets is_safety (bug found by tests: pro-created safety cases weren't flagged).
- Frontend: index.html title "SA CoParents Align | Professional Joint Reports"; Landing.jsx fully rewritten (8 sections: professional hero w/ poster, two-platform table + 2 steps + parent-notice, 4 pro action cards + Sign-In-to-Create + flow steps, clarity bullets + 10-page chips, 8 subject cards w/ Who/Compares/Receives/Uses/View Sample + red safety note, applications + disclaimer, confidentiality/sharing, professional invitation + mantra; new nav); tagline "Professional Joint Reports for Co-Parenting Matters". Auth.jsx: no role picker; professional-only register; parent flow auto via ?next=/join/<token> (invite token passed to register); parent-notice box; ?mode=register deep link. Join.jsx: "Create your free parent account" register deep link. Hub.jsx: parents redirected to /dashboard. Dashboard.jsx: circle nav + joint-tools create + agreement card are pro-only; parents see parent-joint-note + case-code box. SampleMediation CTA → professional account. New /resources page (Resources.jsx): getting started, confidentiality/sharing, safety box, FAQ.
- Test suite rebuilt for the new model: tests/casekit.py (new_user/new_case/fill/completed_case — parents always created via real invitation); rewrote test_joint_reports.py, test_safety_reports.py (parent-initiation 403 + full safety cycle via pro prepare flow), test_hub_features.py, test_agreements_and_pro_requests.py, test_foundation_merge.py, test_pdf_report.py, test_pro_share_updates.py; patched test_pro_share_links.py, backend_test.py, test_password_reset.py, test_external_assessments.py (role=professional where role-agnostic). Decoupled 5 admin-fixture tests from the real admin account (self-contained fixture users) after finding the documented admin password no longer matches the stored hash (pre-existing; did NOT touch the real account). **Suite: 105/105 green.**
- Pending: test_prod_verification.py still assumes old prod behavior (parent registration) — will need the casekit treatment after deploy. Frontend E2E verification: testing_agent iteration_18 (100%, zero issues).

## Code-review quick wins applied (2026-09-06, user option a)
- tests/casekit.py: test password centralized to env-overridable `TEST_PASSWORD` (os.environ "E2E_TEST_PASSWORD", default testpass123; throwaway accounts only — scanner false positive resolved).
- `is` vs `==` review: all flagged lines (server.py 98/102/126/400/582 + test files) are CORRECT `is None`/`is not None`/`is True` identity checks — grep for genuine value-identity misuse found zero. No changes (documented false positives).
- InviteSpec @dataclass added (server.py): create_invitation 9 params → 1 spec; send_invite_email 8 params → (spec, token). All 7 call sites updated (parent report, pro report ×2, agreement ×2, FV prepare ×2, resend).
- Behavior-preserving; full suite re-run: 105/105 green. Deferred (user chose quick wins): complexity refactors of pdf_report builders / integration_case_update / save_joint_responses / joint_public, and type-hint rollout.

## Code-review complexity refactor + type hints (2026-09-06, scanner re-run / remaining items)
- pdf_report.py: extracted shared `_new_pdf()`, `_title_header()`, `_philosophy_block()` (header/philosophy were duplicated across all 4 builders) + per-section helpers `_joint_differences/_joint_alignment_map`, `_agreement_terms/_agreement_foundation/_agreement_signatures`, `_case_snapshot/_case_goals/_case_alignments/_case_differences/_case_action_plan`, `_complete_assessment_section/_complete_joint_section/_complete_section`. build_case_pdf 23→~8, build_complete_pdf 19→~6, build_joint_pdf 17→~7 complexity.
- server.py: joint_public → `_participants_public/_invitation_public/_pending_public`; create_joint_report → `_resolve_mediator/_notify_mediator`; save_joint_responses → `_validated_answers`; integration_case_update → `_compute_case_updates/_notify_case_ready`; prepare_pro_request → `_resolve_prepare_parties/_safety_case_doc`.
- GOTCHA (fixed immediately, caught by suite): inserting a helper between an @api route decorator and its endpoint re-decorates the helper (422 "Field required"). Always re-attach decorator directly above the endpoint.
- Type hints first pass: all of pdf_report.py; public functions of joint_engine (generate_joint_report/generate_agreement/sample_mediation_report), report_engine (generate_report), complete_engine (build_complete_report), joint_data (S, merged_subject_config), assessment_data (T, demo_payload); refactored server.py helpers. Note: joint_data/assessment_data are data modules — only 2 constructor functions each existed.
- `is` literal flags (server.py 99/103/127/401/583): re-verified — all correct `is None`/`is not None`; no changes.
- Verified: py_compile clean, decorators confirmed correctly placed, full suite 105/105 green after all refactors.
## Landing/auth polish round (2026-09-06, 5 user items)
1. Registration confidentiality text: ConfidentialityNotice.jsx gained `variant` prop — "professional" copy (user-provided: professional account/case info private by default...) used on Auth register (non-parent flow) + JointNew; parent copy kept for Join/JointAssessment. Privacy.jsx full provision untouched.
2. Ten-page vs sample reconciled by framing: landing chips block adds pages-sample-note ("preview is a condensed Sample Mediation Statement; full report follows the universal 10-page structure"); SampleMediation.jsx adds sample-condensed-note under the badge.
3. Subject-card buttons renamed "View Sample" → "View General Report Example" (all 8 still → /sample-mediation; per-subject samples are backlog).
4. Hero graphic simplified: generated minimal purple/teal poster (SA CoParents Align / For Professionals / Two parent perspectives / One child-focused report) via image tool → /app/frontend/public/align-hero-simple.jpg, POSTER_IMG swapped + alt updated; detailed poster kept as shareable flyer (FLYER_IMG) in professionals-invite section (data-testid pro-flyer).
5. New leadership-section on landing: "Created for the Professionals Who Guide Families" + user copy + trust bullets (who it's for, problem addressed, "authorized professional" definition, App relationship). Personal founder name/credentials/contact NOT invented — asked user to supply for personalization.

## Professional approval gating (2026-09-06, user: "Professional needs to be approved through mattsossi@bsossi.com")
- Backend (server.py): new professional registrations get approved:false + admin (ADMIN_EMAIL) is emailed a notice (guarded). require_approved_professional(user, detail) gates POST /joint/reports, /joint/reports/professional, /joint/agreements, /joint/professional-requests/{id}/prepare — unapproved pros get 403 "pending approval". Existing pros grandfathered via user.get("approved", True). public_user exposes "approved". New admin endpoints (role=admin only): GET /api/admin/pending-professionals, POST /api/admin/approve-professional/{user_id} (404 unknown, approval email to pro, guarded). /professionals list now only returns approved pros (approved != False; missing field = approved) and cap raised 500→5000 (cap cutoff was making tests flaky).
- Frontend (Dashboard.jsx): unapproved pros see approval-pending-banner (case creation still server-blocked); admin sees admin-approvals-section with pending list + approve-pro-btn-<id> per pro.
- Tests: casekit.new_user auto-approves professional fixtures via mongo (_approve lowercases email — GOTCHA: registration lowercases emails, so approval must too); new tests/test_professional_approval.py (7 tests: pending default, 403 gates ×3, admin list/approve flow, non-admin 403, unknown 404, parent unaffected). test_pro_share_links.py local _reg now approves pros. Suite: 112/112 green. UI verified: pending banner renders after fresh pro registration; admin section covered by API tests (admin UI not screenshot-verified — real admin login unavailable).
- GOTCHA (frontend): inserting hooks/state above `const { user } = useAuth()` → TDZ crash "Cannot access 'user' before initialization". Place after.

## Code-review round 3: cron refactor + complexity + hints (2026-09-06)
- run_completion_nudges (complexity 25, depth 5) split into `_parse_iso`, `_send_ready_notifications`, `_send_completion_nudge` + thin dispatcher loop; behavior identical.
- build_complete_report → `_assessment_section`/`_joint_section`; joint_engine `_theme_analysis` → `_theme_row`; generate_agreement → `_agreement_term`/`_foundation_entries`; build_joint_pdf → `_joint_notes`/`_joint_front_sections`/`_joint_back_sections`; report_engine generate_report → `_perspective_sections` (shared_goals now computed inside); server resolve_subjects → `_multi_label` + early returns; `_validated_answers` → `_foundation_payload`; `_resolve_prepare_parties` → `_first_email`.
- Type hints added to all refactored/new functions (engines + server helpers).
- Verified: py_compile clean; full suite 112/112 green after refactor.
- Terminology rename (user): Step One is now "Parent Individual Assessment" — Landing journey strip heading, platform-table purpose row, leadership parent-platform bullet.
- Terminology rename (user, 2026-09-06): Step Two is now "Professional Joint Report" (Landing.jsx journey strip). "Joint Alignment Case" → "Professional Alignment Case" in Dashboard.jsx (pending-approval banner + create button) and Resources.jsx. User framing: "SA CoParents Align = Professional Alignment — the professional brings the parents' perspectives together, identifies alignment and differences, and uses structured reports to facilitate the next conversation." Report product name "Joint Alignment Report" intentionally kept as-is (global rename offered but not chosen). Screenshot-verified: "Step Two — Professional Joint Report" renders on landing page.
- Real approval-flow validation (user, 2026-09-06): ROOT CAUSE of broken owner login = non-idempotent seed_admin (only inserted if missing; ADMIN_PASSWORD env changed after first seed, so stored hash matched neither env nor documented password). FIX: seed_admin now re-syncs bcrypt hash when env password doesn't verify and clears login_attempts for that admin (per integration_expert JWT playbook). Validated end-to-end with real owner account: admin login OK → /admin/pending-professionals OK → approve OK → approved pro (approval.test.pro1@gmail.com) logged in and created case SA-EDU-642310 (2 invitations). Admin notification email for new registrations: ACCEPTED (202) by provider once rate-limit window reset. Remaining caveat: Emergent email integration rate-limits (429) under heavy test-suite load — approval emails can be silently dropped during bursts (send_email raises, caught+logged; no retry). Cleanup pending: ~90 stale @example.com/test pending-professional accounts clutter the admin dashboard (awaiting user decision).
- Cleanup + domain + email validation (user-directed, 2026-09-06): (1) EMAIL — forgot-password deliverability test to real owner inbox returned provider 202 Accepted (owner to confirm inbox receipt); approval-notification send path verified accepted earlier. (2) CLEANUP — purged 94 pending + 3244 total fake-domain test users (@example.com/@testmail.com/@testmail.dev/@x.com); DB now holds only real accounts: admin, 2 validation pros, 1 parent (probe123@gmail.com). Admin pending list = 0. (3) CUSTOM DOMAIN LIVE — sacoparentsalign.com and www both serve the app (title verified), /api routes 200 through custom domain. No longer a blocker. (4) Sibling SA CoParents App implementation still pending in its own Emergent project (spec: /app/SACOPARENTSAPP_ONLINE_INTEGRATION_SPEC.md).
- Code-review round 4 (user, 2026-09-06): _send_ready_notifications split into _ready_window_open + _ready_email_html (complexity 12→10); _send_completion_nudge split into _nudge_target + _nudge_email_html (12→6). Production `is`-literal finding = FALSE POSITIVE (zero genuine cases; all are is None/isinstance — do not "fix"). Tests: batch-replaced `is True/False` → `== True/False` across tests/*.py; casekit new_case 8-arg → CaseSpec dataclass (+ type hints on all casekit helpers). Complex e2e test splitting deliberately skipped (sequential flows; splitting would duplicate setup). Found + fixed stale test_prod_verification.py (predated professional-only gates: direct parent registration + unapproved pro case creation now 403 by design) — rewritten to casekit invite flow; public checks (health/config/cron auth) stay on PROD, feature flows on preview (Secure cookies require HTTPS base URL). Prod suite 10/10 green. Full suite after all round-4 changes: 122/122 passed.
- Sibling App integration status (2026-09-06): sacoparentsapp.online endpoints NOW EXIST (link-codes 401 session-required, verify-link-code/export-assessments reachable, /?invite= 200) — the App project has been partially implemented since the last fork. Align side fully verified: case-invite returns 200 with rotated secret + real token (SA-EDU-642310), 401 with wrong secret. SECRET RESOLUTION (2026-09-06): App (feel-good-tracker) was configured with the ORIGINAL secret; owner directed Align to standardize on that value. Align backend/.env INTEGRATION_SHARED_SECRET reverted to match App (owner-confirmed correct). Verified after restart: env loads correctly, App verify-link-code returns 404 (authenticated) instead of 401. Rotation superseded — dead-end ledger item 5 no longer applies; both projects now share one standardized secret (still never print it in chat). Pending: production deploy must carry the same env value; then run full cross-platform E2E.
- Cross-platform E2E attempt (2026-09-06, preview Align + live App): S2S auth GREEN both directions (verify-link-code 404-auth'd, export-assessments 404-auth'd, case-invite 200 with real token SA-COM-744026). App registration works via API (Bearer JWT; test acct e2e.align.test1@gmail.com / E2ETest2026!). BLOCKERS ON APP SIDE: (1) link-code generation gated behind App's safety screen ("safety_screen_required", /safety) — submission endpoint is POST /api/safety-assessment (405 on GET), payload schema being probed; (2) App /?invite=<token> does NOT resolve invites — shows generic landing, no resolution screen (CONFIRMED: zero invite/case-invite/integrations refs in App JS bundle); (3) PROD NOT DEPLOYED: /api/joint/samples 404 on both prod hosts; prod admin login fails (prod DB separate — seed or env password differs there). Prod deploy + prod ADMIN_PASSWORD check still user actions.
- E2E COMPLETE on preview↔live-App (2026-09-06): safety screen POST /api/safety-assessment 200 (36 answers, dicts {s1_qN: no, s2_qN: yes}) → link code SA-267059 generated → Align external link VERIFIED: POST /api/external/link {code} → ok + external_email; GET status linked:true; GET /api/external/assessments → 200 {assessments:[],statements:[]} (empty = account has none, chain proven) → case-update receiver: "started"→in_progress 200, "completed" 200 (side A stored, case stays in_progress until both sides). FULL CHAIN GREEN except App-side UI gaps. Remaining App-side gaps for the App project agent: invite-resolution screen for ?invite= tokens; case-update push integration into App assessment completion.
- Per-subject sample reports feature (user-approved 2026-09-06): SAMPLE_SCENARIOS + sample_report()/sample_list() in joint_engine.py (co_parenting, communication, education, medical, psychological, safety-controlled [generic Parent A/B, SAFETY_PURPOSE + fictional-data note], plus mediation delegation). Public endpoints: GET /api/joint/samples, /api/joint/sample/{key}, /api/joint/sample/{key}/pdf (legacy /joint/sample/mediation* routes kept). Frontend: src/lib/samples.js (SAMPLE_REPORTS + samplePdfUrl), SampleReport.jsx (viewer, /samples/:key + fixedKey mediation at /sample-mediation), Samples.jsx (/samples grid), SampleMediation.jsx DELETED. Landing: new #samples section (7 cards, View+PDF), nav/hero/action/bottom CTAs -> /samples, subject cards map to per-subject sample via SAMPLE_KEY_BY_SLUG (high-conflict -> /samples). Verified: all 7 JSON+PDF endpoints 200/valid, bogus key 404, landing section screenshot clean. Testing agent iteration_19: 16/16 backend + 100% frontend passed; no issues. New test file: /app/backend/tests/test_samples.py. (Pre-existing minor: public pages log /api/auth/me 401 console noise — deferred.)
- Code-review round 5 (user, 2026-09-06): production `is` flags = FALSE POSITIVES again (all 12 server.py lines + joint_engine.py:406 are `is None`/`is not None` — scanner's own text admits these are correct; DO NOT convert). Applied: E712/F632 sweep across tests (== True→plain, == False→not, is True/False→same; one regex casualty backend_test.py:211 fixed); complex-test refactor via helpers: _submit_agreement/_assert_agreement_report/_assert_agreement_pdf/_pro_request/_assert_safety_listing (agreements file), _assert_full_report/_case_reference_visible_to_creator_only (joint_reports), _assert_safety_payload/_submit_side (safety_reports); `-> None` hints on all test functions. Full suite 138/138 passed (incl. test_samples.py from iteration_19).
- Email-this-sample feature (user, 2026-09-06): POST /api/joint/sample/{key}/email {email} (EmailStr-validated, 404 unknown key, emails view+PDF links via send_email — managed email API has no attachment support). Frontend: shared SampleCard.jsx component (View/PDF/Email inline form, sonner toasts) used by Landing #samples section and /samples page. Verified: 404/422 paths, email form renders+submits (screenshot), valid send reached provider. Isolation test proved provider-side rate limiting: known-good forgot-password path ALSO failed with 429 at the same time — not an endpoint bug. Note: my endpoint propagates send failure as 502 (honest error toast) vs other flows which swallow+warn; deliberate for a user-initiated send action. Retest delivery once provider rate window resets.
- Code-review round 6 (user, 2026-09-06): production `is` flags = FALSE POSITIVES 4th time (13 server.py lines + joint_engine 406 all `is None`/`is not None`; scanner text itself exempts None — permanent dead-end, stop re-flagging). Applied: report_engine.py fully type-hinted (7 fns); test complexity reduction round 2: test_full_flow split into _created_request + test_request_creation_and_listing + test_prepare_flow; _assert_agreement_report terms loop → _assert_agreement_terms; prod_verification: _pending_request split (test_prepare_empty_body_400 / test_prepare_with_emails_200) + _assert_two_invitations; pro_share_links _assert_two_parent_links; backend_test test_demo_and_report_for_all_types parametrized over TYPE_KEYS; report_shape _assert_snapshot_and_summary; samples safety specifics split into test_safety_sample_specifics; joint_reports _assert_stranger_404. server.py 28-import "split into modules" suggestion DEFERRED (behavior-neutral churn risk on working 1900-line app; revisit if server grows further). Full suite after round 6: 148/148 passed.
- Code-review round 7 (user, 2026-09-06): `is` flags = FALSE POSITIVES 5th time (all 21 lines verified `is None`/`is not None` incl. test files). God-object/import finding ADDRESSED via bounded extraction: auth_utils.py (JWT_ALGORITHM, jwt_secret, hash/verify_password, create access/refresh tokens) + email_utils.py (send_email, content-safety scanner, EMAIL_* env constants); server.py imports them; dropped bcrypt/ipaddress/HTMLParser/urlparse imports from server.py. Created /app/CODE_REVIEW_NOTES.md documenting accepted patterns (is None, e2e test flows, fixture accounts, server.py split policy) so future scanner rounds stop re-flagging. Same-batch F821 lint flags were edit-ordering artifacts — final state verified by py_compile. Full suite after round 7 extraction: 148/148 passed; /health 200; /api/joint/samples OK.
- Feature batch (user, 2026-09-06): (1) REMINDER PREVIEW MODAL — send_invite_email split into _invite_email_content builder + sender; new GET /api/joint/invitations/{iid}/reminder-preview (creator-only 403, 404 unknown) returns {to, subject, html}; shared ReminderPreview.jsx (Dialog + iframe srcDoc + Send confirm) wired into Dashboard reminder buttons and JointReport resend (old resend fn removed). (2) UNICODE PDFs — DejaVu Sans TTFs (regular/bold/oblique/bold-oblique) vendored to backend/fonts/ (sourced from matplotlib's mpl-data after GitHub 404s); registered as family "dejavu" (fpdf2 2.8.8 REFUSES overriding core name "helvetica" — UserWarning, does nothing); FONT constant switches all set_font calls; _s() passes Unicode through when fonts present, legacy latin-1 sanitizer as fallback. Verified: Jürgen Østberg / Sofía Núñez / em-dash / curly quotes / ✓ all render. (3) SAMPLE watermark — _JointPDF.watermark_text drawn rotated on every page footer; set for is_sample joint PDFs and is_demo case PDFs; case note text upgraded to "SAMPLE REPORT - demo data shown for illustration". Verified via pypdf extraction. (4) COPYRIGHT (user, 2026-09-07): global web footer in App.js (`© {year} SA CoParents Align · sacoparentsalign.com · All rights reserved`, data-testid="copyright-footer") renders on every screen incl. report views; PDF page footer (shared _JointPDF.footer → all 4 PDF types) now reads "SA CoParents Align - © {year} sacoparentsalign.com - Page N" on every page. Verified: web footer on /samples + /samples/education screenshot; pypdf confirms copyright line on every page.
- Prod deploy verification (2026-09-07): prod has PARTIAL build — samples + SampleCard email buttons + /api/joint/sample/{key}/email live (screenshot-verified on sacoparentsalign.com/samples), and prod admin login NOW WORKS (approved:true — ADMIN_PASSWORD set in prod env). Still missing on prod: reminder-preview endpoint (404), Unicode fonts, SAMPLE watermarks, © footers (PDF + web). Root cause: deploy happened before those commits; needs one more Deploy click. Retried after 45s — still old build.
- Full spec implementation wave (user pasted complete product spec, 2026-09-07): IMPLEMENTED — RegisterIn extended (phone/org/pro_role/city/state/license/website + agreements_accepted enforced for professionals, profile subdoc + verification_level="credentials_pending"); professional notes POST/GET /api/joint/reports/{rid}/notes (creator-only); GET /api/joint/reports/{rid}/activity (invitations + access_events); ProWorkspace.jsx (private notes + consent/activity sections on JointReport for creators); AcceptInvite.jsx (/accept-invite — accepts parent professional-requests via prepare flow); Dashboard 4 primary action cards; Landing hero per spec ("Turn Parent Reflection Into Child-Focused Alignment", 3 CTAs, "Parents Reflect. Professionals Align. Families Build Agreements."), professional-use disclaimer + philosophy line, spec footer language + 8 legal links; Legal.jsx generic pages (/legal/:page — terms, professional-use, methodology, data-retention, accessibility, safety-resources, contact). casekit + 6 test files patched with agreements_accepted. Suite: 148/148 passed. Bug found+fixed during verification: App.js route used nonexistent PrivateRoute (guard is Protected) — crashed whole SPA; fixed, all 3 screenshot checks passed (landing hero/footer/legal links, pro registration form w/ agreement gating, dashboard 4 action cards + /accept-invite). SPEC GAPS REMAINING (roadmap): 6-tab family-matter workspace UI, email verification + 2FA, verification-level admin workflow (credentials verified), consent grant/revoke flows, access-expiry automation, full audit logging on views/downloads, admin portal extensions, child-initials masking on dashboard cards, family_matter_id cross-platform key.

## 2026-09-08 — Admin approvals panel enrichment
- `GET /api/admin/pending-professionals` now returns `profile` (pro_role, organization, city/state, license_number, phone, website), `created_at`, `verification_level`.
- Dashboard admin panel shows Role / Organization (city, state) / License per pending professional, plus phone, website, registration date. data-testids: `pending-pro-role-{id}`, `pending-pro-org-{id}`, `pending-pro-license-{id}`.
- Cleaned 191 fixture (non-gmail/bsossi) unapproved test professionals from DB.
- Note: preview proxy showed "Preview Unavailable" during this session; frontend compiled OK and API verified via curl. Visual check pending.

## 2026-09-08 — Decline applicant + Family Matters page (tested: iteration_20, 148/148 backend)
- `POST /api/admin/decline-professional/{id}` {reason} (required, ≤500 chars) → sets declined flag/reason, emails applicant, removes from pending list. Dashboard: Decline button + inline reason form (`decline-pro-btn-{id}`, `decline-reason-input-{id}`, `decline-confirm-btn-{id}`).
- `PATCH /api/joint/reports/{rid}/archive` {archived} (creator/professional only); `archived` field added to joint_public.
- New page `/matters` (`FamilyMatters.jsx`): search, 6 status chips (all/awaiting_parents/awaiting_a/awaiting_b/ready/archived), child shown by initial only, Archive/Restore. Dashboard "My Family Matters" card → /matters; archived hidden from dashboard Joint Reports.
- Note: pytest suite re-creates unapproved fixture professionals (non-gmail domains) → they show in admin panel after test runs; clean with delete_many on non gmail/bsossi unapproved pros. Consider making pending list exclude fixtures or having tests clean up.
- Deploy still pending user click.

## 2026-09-08 — Expiring invitations + declined log (tested: iteration_21 frontend 100%, pytest 148/148)
- `_pending_public` now includes `created_at`, `expires_at` (created + 14 days; INVITE_EXPIRY_DAYS). No enforcement of expiry yet — display only.
- /matters: "Expiring Invitations" chip; matters with pending invites expiring ≤4 days show notice + Send Reminder (ReminderPreviewButton).
- Admin: `GET /api/admin/declined-professionals`, `POST /api/admin/reconsider-professional/{id}`; Dashboard collapsible declined log with reason + Reconsider.
- Test data: SA-EDU-642310 role-b invitation backdated 12 days to exercise expiring state.
- PRODUCTION: frontend 200 but ALL /api routes 404 on sacoparentsalign.com and align-report.emergent.host (incl. /api/health which was 200 before). Deployment agent static scan passes; runtime logs not obtained. Needs redeploy / platform check.

## 2026-09-08 — Matter Notes + invitation expiry enforcement (tested: iteration_22 100% both, pytest 152/152)
- `invite_expired()` (14 days from created_at) enforced in lookup (410), accept (410), resend (410), integration case-invite (410).
- `POST /api/joint/invitations/{iid}/reissue` (creator only): marks old invite `expired`, creates new invite (same code/email/role), emails parent, logs access_event.
- /matters: expired invite → red notice + "Reissue Invitation"; expiring-soon → Send Reminder + Reissue. Per-row "Notes" toggle → `MatterNotes.jsx` (reuses /joint/reports/{rid}/notes, professional-private).
- Production still: frontend 200, all /api 404 — awaiting user redeploy/platform check.

## 2026-09-08 — Credentials Verified badge (tested: iteration_23 frontend 100%, pytest 152/152)
- `public_user` exposes `verification_level`, `credentials_verified`. `GET /api/admin/professionals`, `POST /api/admin/verify-credentials/{id}` {verified}. Lookup endpoint returns `professional_verified`.
- UI: `AdminProfessionals.jsx` (Approved Professionals manage list), `VerifiedBadge.jsx`; badge in pro dashboard header and on /join invitation page.
- Cleaned 1110 @example.com fixture professionals. Test suite (test_iteration_22) no longer depends on a backdated invite.
- Production: still all /api 404 (frontend 200) as of this session — user must redeploy/check platform deploy logs.

## 2026-09-08 — Verified badge on Joint Report PDFs (pytest 152/152, rendered & visually checked)
- `_report_professional(doc)` in server.py looks up professional_id/created_by → {name, credentials_verified}; passed as `professional` into `build_joint_pdf`.
- `pdf_report._professional_line`: "Facilitating professional: <name>" + green "Credentials Verified" pill in the title header (only when verified). Samples unaffected (no professional key).
- Production: still all /api 404 as of this session (frontend 200). User must redeploy / inspect platform deploy logs.

## 2026-09-08 — Expiry digest cron + note edit/delete with revisions (pytest 152/152; iteration_24 frontend)
- `POST /api/cron/expiry-digest` (Bearer WEBHOOK_CRON_SECRET, idempotent by run_id via `_cron_accept`), background `run_expiry_digests()`: one email per professional/day listing pending invites expiring ≤4 days or expired (child by initial; link /matters?filter=expiring). Dedup via cron_runs {job:'expiry-digest-sent', pro_id, day}. Scheduled in .emergent/crons.yml daily 08:00 America/Chicago.
- Notes: `PUT/DELETE /api/joint/reports/{rid}/notes/{nid}`; edits push prior text to `revisions[]` and set `updated_at`. `MatterNotes.jsx` now has edit/delete/history UI; `ProWorkspace` reuses it (old pro-note-* testids removed).
- /matters honours `?filter=` query param.
- Production still all /api 404 (frontend 200).

## 2026-09-08 — Public verification page + note search (pytest 152/152; iteration_25 frontend)
- `GET /api/verify/{case_code}` (public): professional name/role/org, account_approved, credentials_verified, case_active. Never returns parent/child data. Page `/verify` (Verify.jsx), nav link on Landing, hint link on /join.
- `GET /api/notes/search?q=` (professional, own notes, min 2 chars, regex-escaped) with case_code/subject/child initial. `NoteSearch.jsx` at bottom of /matters with highlighted matches.
- Production still all /api 404 (frontend 200).

## 2026-09-08 — Digest preferences (pytest 152/152; iteration_26 frontend)
- `GET/PUT /api/me/preferences` {digest_frequency: daily|weekly|off} stored on user. `run_expiry_digests` skips "off" and sends "weekly" only on Mondays (UTC weekday 0). `DigestPreference.jsx` on /matters.
- Production still all /api 404 (frontend 200) — unchanged all session.

## 2026-09-08 — Weekly caseload summary (pytest 152/152; iteration_27 frontend)
- `POST /api/cron/weekly-summary` (Mon 08:00 America/Chicago in crons.yml; 3 crons total). `run_weekly_summaries`: per approved professional (skips @example.com fixtures, weekly_summary=false), one email per ISO week: counts (ready / awaiting one / awaiting both / notes added this week) + table of active matters (child by initial). Dedup cron_runs {job:'weekly-summary-sent', pro_id, week}.
- Preferences now {digest_frequency, weekly_summary}; `DigestPreference.jsx` has On/Off switch row.
- Purged 2088 @example.com fixture users + 390 reports + 4268 invites. Test suite recreates fixtures each run.
- Production still all /api 404.

## 2026-09-08 — Code review round + production probe correction
- CORRECTION: production backend is UP. Real probe paths: `/health` (root, 200 in prod), `/api/joint/samples` (200 in prod), `/api/joint/config` (200). `/api/health` and `/api/samples` never existed → earlier "all /api 404" conclusion was wrong; prod is merely STALE (today's routes /api/me/preferences, /api/verify 404 in prod, 200 in preview).
- Added `GET /api/health` → {"status","build": BUILD_ID} (BUILD_ID const near router). After user deploys, verify prod `/api/health` returns build "2026-09-08.3".
- Refactors: register() split into _validate_registration/_professional_profile/_notify_admin_new_professional; run_expiry_digests split into _expiring_rows_by_pro/_digest_due/_send_digest/_digest_html; build_case_pdf → _case_bullet_section/_case_professional_map; list_connections simplified; invite_expired uses _parse_iso; _matter_state uses dict lookup. Unused imports removed. Scanner "is vs ==" claims are all `is None` — false positives (do not change).
- NOTE: routes must be declared BEFORE `app.include_router(api)`.

## 2026-09-08 — Verification QR + test fixture cleanup (pytest 152/152)
- `GET /api/verify/{code}/qr.png` (public, cached 1d) → QR to /verify?code=. Invitation email now embeds QR + verify link; Joint Report PDFs show QR top-right ("Scan to verify" + case code) via `_verify_qr_block`, driven by `verify` key from `_verify_info(doc)`. Dependency: qrcode[pil] (requirements.txt updated).
- `tests/conftest.py`: `pytest_sessionfinish` (controller only under xdist) purges @example.com / @x.com fixture users + their reports/invites/notes/cases/connections/cron_runs. Suite now leaves DB clean (only panel.test.pro pending).
- Production still stale (no /api/health build id yet).

## 2026-09-08 — Forgot-password reliability (pytest 152/152; iteration_28)
- Root cause of "no passcode": Emergent email API 429 rate-limited (test suites burned quota) and forgot_password swallowed the failure. Fixes: send_email retries up to 3x on 429 (2s/4s backoff) then raises 503 with honest message; forgot_password surfaces 503/502 and deletes the stale reset record; fixture domains (@example.com/@x.com/@example.org) skip the provider entirely (FIXTURE_EMAIL_RE) incl. admin new-registration notifications. Auth.jsx toast updated.
- Verified: owner email reset request → provider 202 after one 429 retry.

## 2026-09-08 — Code review round 3 (pytest 152/152)
- send_email split into helpers; test type hints; unused test imports removed. "is None" findings remain false positives. Prod still stale.

## 2026-09-08 — PRODUCTION VERIFIED (build 2026-09-08.3 live)
- /api/health → build 2026-09-08.3; new frontend bundle main.8eb11ace.js; footer copyright present; hero + nav-verify present.
- Live & verified in prod: /verify page + /api/verify (404 for unknown code as designed), QR endpoint (200 image/png), /api/me/preferences (401 unauth / prefs for user), notes search, all 3 cron endpoints (401 unauth), reminder-preview (401 unauth), admin pending list w/ profile, decline → declined log → reconsider, admin/professionals list, sample PDFs (DejaVu fonts embedded, SAMPLE REPORT watermark, copyright footer), forgot-password fixture path.
- Prod fixture account prod.verify.pro@example.com left in DECLINED state (reason notes it is a test fixture) — safe to ignore/delete from declined log.
- Note: real prod case codes differ from preview (SA-EDU-642310 is preview-only).
- Test type hints round 4 done; pytest 152/152.

## 2026-09-08 — Resend code (pytest 152/152)
- forgot_password: 60s server cooldown per email (429). Auth.jsx reset screen: countdown `resend-code-countdown` then `resend-code-btn`; resend restarts 60s. Needs deploy to reach prod.

## 2026-09-08 — Admin-as-professional + seeded Joy Curbow (pytest 152/152; BUILD 2026-09-08.4)
- `is_pro()` = role in (professional, admin); frontend isPro likewise (Dashboard/Hub/JointNew). seed_admin sets ADMIN_PROFILE (Matt Sossi: Attorney, Family Law Mediator, Parent Facilitator & Amicus Attorney; 16607 Blanco #703 San Antonio TX 78232; 210-224-1667), approved + credentials_verified; no longer overwrites password if `password_reset_by_user` set (set by reset-password / change-password).
- `seed_professionals`: creates joy@bsossi.com (approved, verified, must_change_password) with password from env JOY_TEMP_PASSWORD (added to backend/.env). `POST /api/auth/change-password`; `ForcePasswordChange.jsx` modal on dashboard when must_change_password.
- Both take effect in PRODUCTION on next Deploy (seed runs at startup). Prod admin password: user reset it today; agent cannot log in to prod admin anymore.
- Dashboard header now shows name · email (`user-name` testid). iteration_30: 100% backend / 95% frontend (only note: header name, fixed).

## 2026-09-09 — Landing: workflow-first messaging (BUILD 2026-09-08.5)
- Hero subtext: "Invite parents to reflect separately. See where they agree. Identify where they differ. Build the conversation around their child's needs." Primary CTA "Invite Parents" (→ register), then Sign In, then Accept Invitation (ghost). Tagline `hero-journey`: "You invite. Parents reflect. Align compares. You guide."
- New `workflow-strip` (purple): Invite → Assess → Compare → Align → Guide + note that the professional connects the parents (no "send the other parent your code"). Step Two card copy updated. Architecture already professional-organized (professional-only invites) — no backend change.
- iteration_31: landing 100%. Mobile header overflow fixed (nav CTA shows "Get Started" on <sm). PROD build 2026-09-08.4 live: Joy's account present (approved, verified, must_change_password), new bundle main.80bdcc09.js. Landing messaging (build .5) still needs deploy.

## 2026-09-09 — Compare View (BUILD 2026-09-09.1)
- `CompareView.jsx`: professional-only (detail.is_creator) side-by-side of alignment_map + differences with Agree/Partly/Differ count filters, "Both parents identified" list, neutral footnote. JointReport tabs `view-tab-compare` (default) / `view-tab-report`; parents see only the report document. No backend change (uses existing generate_joint_report output).
- Preview ready fixture for pro1: report 4420edc0-a432-4eb8-b7f5-7ce2d2e7e8e6 (SA-EDU-934744). PROD build still 2026-09-08.4 (landing copy .5 and Compare .1 pending deploy).

## 2026-09-09 — Professional-hub "Invite Parents" flow (BUILD 2026-09-09.2; pytest 152/152)
- Landing top: H1 "Professional Tools for Child-Focused Alignment", user's subtext, CTAs INVITE PARENTS (→ /joint/new, protected) + PROFESSIONAL SIGN IN; journey line "Professional invites → Parents reflect → Align compares → Professional guides".
- /joint/new for pros (isPro && !agreement): panels order child(Create Case: case ref + child) → invite(Parent 1/2 name+email) → subject(Choose Assessment: Co-Parenting, Communication, Educational, Medical, Psychological, Mediation, Complete Alignment[multi 5 subjects]) → "Send Invitations". PRO_ASSESSMENTS const. Parents keep old order. JointReport header PDF button icon-only on mobile.
- Compare View iteration_32 passed (mobile overflow fixed here).


## 2026-09-09 — Landing simplification for conversion (BUILD 2026-09-09.3; iteration_34 69/69)
- Hero CTAs: primary "Create a Free Professional Account" (+ sub-line "Start a case and invite parents", → /auth?mode=register), "Professional Sign In", small link "Have an invitation? Accept Invitation". Removed Invite Parents/Accept trio. Journey line: "Create Case → Invite Parents → Compare Perspectives → Build Alignment → Work Toward Agreement".
- New purple `four-steps` centerpiece (step-create/invite/report/guide, user's exact copy) replaces the 5-stage workflow strip, platforms table, journey strip, pro-actions, clarity, applications, leadership and long invitation sections.
- New `AlignModel.jsx` signature graphic: THE CHILD at center; Reflection → Comparison → Alignment → Options → Agreement.
- 10-page report section promoted (numbered page-chip-0..9 + sample buttons). Samples trimmed to 3 cards; subjects collapsed to 8 compact links → sample pages; one short "Professional control. Parent privacy." section + parent notice; disclaimer + footer.
- Mobile: header Sign In hidden <sm, smaller brand subline, hero CTA wraps — zero horizontal overflow at 390px. Needs Deploy/Republish (prod last confirmed 2026-09-08.4).

## 2026-09-09 — Professional invitation acceptance + /methodology (BUILD 2026-09-09.4; pytest 159/159; iteration_35)
- `professional_requests` now carry `token_hash` (sha256 of opaque `secrets.token_urlsafe(32)`), `professional_email`, `expires_at` (+72h, `PRO_INVITE_TTL_HOURS`), `token_used_at`, `decided_at`, `events[]` audit (sent / info_requested / accepted / declined / conflict_reported). Email to pro links `/accept-invite?token=…` with minimal info (no parent emails pre-acceptance; do-not-forward notice).
- Endpoints: `GET /api/joint/professional-requests/lookup?token=` (404 invalid, 403 email mismatch, 410 expired/used, minimal payload); `POST …/{id}/decline` {reason}, `…/request-info` {reason required, stays pending}, `…/conflict` → `declined_conflict`; `prepare` (=accept) now consumes token, 410 when expired. List returns computed `expired` status + events. Parent notified by neutral email on decline/conflict/info.
- `AcceptInvite.jsx`: token mode + list mode, Accept / Request more information / Decline / Conflict of interest decision panels, expiry countdown, token error panel. Bug fixed post-test: request-info no longer removes card.
- `Methodology.jsx` at `/methodology` (public): AlignModel graphic, 4 steps, 10 pages, "what the model will not do", copy-link + print. Landing `model-methodology-btn` + footer link point to it (legal/methodology page kept).
- PROD at time of work: 2026-09-09.2 (Invite Parents wave live; simplified landing .3 and this .4 pending Deploy).

## 2026-09-09 — Parent request status + methodology PDF handout (BUILD 2026-09-09.5; pytest 160/160; iteration_36)
- `ParentRequestStatus.jsx` on parent dashboard (`!isPro`): "My Facilitation Requests" with status labels (pending/prepared/declined/declined_conflict/expired) and latest professional message from `events` (info_requested question or decline note; conflict notes stay private).
- `GET /api/methodology/pdf` (public, 1 page, `build_methodology_pdf` in pdf_report.py): stage row, 4 steps, 10 pages, principles, disclaimer, copyright footer. Methodology page: header "Download PDF" + "One-page handout (PDF)" buttons. Test `test_methodology_pdf.py`.
- fpdf2 gotcha: `multi_cell` defaults new_x=RIGHT — always pass `new_x="LMARGIN", new_y="NEXT"` before another full-width cell, else "Not enough horizontal space" 500.
- PROD still 2026-09-09.2 at time of work — user must Deploy.

## 2026-09-09 — Seeded Albert W. Smith, PhD (BUILD 2026-09-09.6)
- Added to `SEEDED_PROFESSIONALS`: dralsmith@gmail.com, "Albert W. Smith, PhD", Psychologist, same office address, phone 210-854-8964; approved + credentials_verified + must_change_password; temp password env `ALSMITH_TEMP_PASSWORD` (backend/.env). Matt Sossi already existed with the supplied details (admin + approved/verified professional) — no change needed.
- Preview login verified (must_change_password=true). Production: needs Deploy AND `ALSMITH_TEMP_PASSWORD` set in the production environment variables, else seed is skipped.

## 2026-09-09 — Report access log (BUILD 2026-09-09.7; test_access_log.py)
- `/joint/reports/{rid}/report` and `/pdf` now insert `access_events` with `kind` (view|download), `by`, `by_name`, `by_role` (Assigned professional / Parent 1 / Parent 2 / Shared professional). Activity endpoint returns `access_log`, `view_count`, `download_count`; legacy events stay in `access_events`.
- ProWorkspace "Consent & Activity" gained a "Report Access Log" list (View/PDF badge, actor, role, timestamp, counts, empty state, "downloaded copies cannot be recalled" note). Screenshot-verified in preview.

## 2026-09-09 — Verification-code delivery investigation (BUILD 2026-09-09.8)
- User (Matt, production) reported reset code never arrives. Findings: prod + preview `/api/auth/forgot-password` return 200; provider accepted direct test to mattsossi@bsossi.com (202, ids 167b0908…, 37256e9e…). Send failures already surface as 502/503, so a 200 means the provider accepted → likely spam/filtering at recipient domain, or stale code (each new request replaces the previous one; my curl tests also invalidated his code).
- Changes: reset code validity 10 → 15 min (server + Auth.jsx copy, "check spam", "new code replaces previous"); new admin-only `POST /api/admin/email-test` sends a delivery test to the admin's own inbox and returns provider id/build; button `admin-email-test-btn` in AdminProfessionals header. Code-review round: `is None` findings again false positives (unchanged); test_access_log.py split into fixture + parametrized tests (7 passing).

## 2026-09-09 — One-click password reset link (BUILD 2026-09-09.9; test_password_reset 12/12)
- forgot-password now also stores `link_hash` (sha256 of `secrets.token_urlsafe(32)`) in the same `password_resets` doc; email has a "Reset my password" button → `/auth?mode=reset&rt=<token>`. reset-password accepts `{token,new_password}` OR `{email,code,new_password}`; same 15-min expiry; both consumed on success (delete_many by email). Email optional in `ResetIn`.
- Auth.jsx: `rt` param → mode reset, shows `reset-link-info`, hides code input, posts token; navigates to /auth after success.

## 2026-09-09 — PRODUCTION VERIFIED build 2026-09-09.7 (bundle main.6eb4c859.js)
- Live: simplified landing (hero CTAs, four-steps, align-model, report-section, methodology button; no mobile overflow), /methodology + PDF (200), /accept-invite SPA, lookup endpoint auth-protected (401), sample PDF 200.
- Not yet live: .8 (admin email-test, 15-min codes) and .9 (one-click reset link — prod reset-password still requires email+code, 422 on token body). Albert login probe → 401 (can't distinguish "no account" vs wrong password without prod admin access; ALSMITH_TEMP_PASSWORD must exist in prod env).

## 2026-09-09 — Professional Directory + refer-a-case (BUILD 2026-09-09.10; test_professional_directory 3/3; iteration_37)
- `GET /api/professionals/directory` (approved pros/admins only; 403 otherwise): id, name, email, pro_role, organization, phone, city, state, credentials_verified. `POST /api/professionals/{id}/refer` {message, report_id?}: emails colleague (reply-to referrer) with referrer contact + optional case code/subject only — no parent data; logged in `referrals`; 400 self, 404 unknown pro / matter not created by me.
- `/professionals` page (Professionals.jsx: search, cards, VerifiedBadge, contact links, "Refer a case" dialog w/ matter select). Dashboard: `ProfessionalsPreview` section "Available Professionals" (4 compact cards + Full directory) for approved pros, plus 5th primary action card `action-professionals`. Mobile overflow fix: grid-cols-1 base, min-w-0/overflow-hidden card, break-all email.


## 2026-09-10 — PRODUCTION VERIFIED build 2026-09-09.9
- Live: one-click reset link endpoint (token body → 400 not 422), admin email-test (401 unauth), 15-min codes. NOT live: .10 directory (`/api/professionals/directory` 404). Albert login probe still 401 (indeterminate). Preview test account approval.test.pro1 does not log in on prod (separate DB) — use Matt's prod account for prod UI checks.


## 2026-09-10 — "Network error" on forgot-password (BUILD 2026-09-10.1)
- Prod endpoint itself returned 200 in ~2s from curl. Root cause candidate: worst-case email send path was 3 attempts × 30s timeout + backoff (~96s) → proxy drops connection → axios "Network Error". Fixes: EMAIL_TIMEOUT_S=12, EMAIL_ATTEMPTS=2, explicit 504 on provider timeout; axios timeout 45s; formatApiError gives a clear connection/timeout message instead of raw "Network Error". Also: each request replaces the code and 60s cooldown → 429 on rapid retries.









## 2026-09-10 — Revoke professional approval (BUILD 2026-09-10.2; test_admin_revoke 1/1)
- Owner: "Alamo Family Mediation" (panel.test.pro@gmail.com, a test fixture that had been approved) must not be an approved professional — approvals come only from SA CoParents. Preview DB: revoked (approved=false, declined, reason logged). Registration already defaults approved=false.
- New `POST /api/admin/revoke-professional/{id}` {reason} (admin only, not self, 404 if not approved) → approved=false, declined log entry, verification_level=declined; removed from directory; pro loses approved-only endpoints. AdminProfessionals list: red "Revoke approval" button per row (prompt for reason). Production has its own DB — Matt must revoke Alamo there via the button after deploying .2.

## 2026-09-10 — Case ID backbone (BUILD 2026-09-10.3; test_case_id 2/2; suite 177 green after assertion updates)
- Owner spec: master Case ID SA-YY-XXXXXX, two distinct parent tokens, statuses DRAFT→INVITED→ONE_COMPLETE→READY_FOR_ALIGNMENT→REPORT_GENERATED(→CLOSED), dashboard table Case ID|Subject|Parent A|Parent B|Joint Report. Owner choices: keep subject prefix → `SA-26-COP-K7M4Q2`; keep shared parent short code (links already carry distinct tokens); skip CLOSED action; child name stays required; table added above cards.
- Backend: `new_case_code` → `SA-{yy}-{PFX}-{6 unambiguous chars}`; `case_status(doc)` derived (no migration) and returned as `case_status` in joint_public; `report_generated_at` stamped on first report view/PDF via `_log_report_access`. Old `SA-EDU-123456` codes unchanged. Tests updated from `startswith("SA-EDU-")` to prefix-contains.
- Frontend: `CasesTable.jsx` on pro dashboard above the joint cards (`cases-table`, `case-row-*`, "Generate report →" when READY). JointNew case-reference helper copy updated.
- Doc: `/app/CASE_ID_ARCHITECTURE.md` — identifiers, collections mapping (CASES/INVITATIONS/ASSESSMENTS ↔ joint_reports/invitations/responses), App⇄Align handoff endpoints, privacy invariants.

## 2026-09-10 — Parent invitation links now route to sacoparentsapp.online (BUILD 2026-09-10.4)
- Root cause: `SACOPARENTS_APP_ASSESSMENT_URL` unset → email/dashboard links fell back to Align `/join/<token>`. Fix: `APP_ASSESSMENT_URL` defaults to `SACOPARENTS_APP_URL`; new `invite_link(token)` = `{APP}/?invite=<token>` (App rewrites /assessment to /, dropping the query — root keeps it) used for invitation emails and every `link` field in API responses (create, list, pending, reissue, FV prepare). `/join/<token>` on Align now redirects to the App (lookup returns `assessment_url`; Join.jsx `window.location.replace`). Tests updated to extract token via `split("invite=")`.

## 2026-09-10 — Invitation email preview (BUILD 2026-09-10.5; test_invitation_preview 2/2)
- `POST /api/joint/invitations/preview` (approved pros): renders both parent invitation emails via `_invite_email_content` with placeholder token/case code — nothing stored or sent. `InvitationPreview.jsx` "Preview emails" button beside Send Invitations on wizard step 3: dialog with Parent A/B tabs, subject, iframe body, "Send Invitations" from the dialog.
- PROD at check time: 2026-09-10.2 (revoke live; .3 Case IDs/.4 App links/.5 preview pending deploy). App-side ?invite= handling and custom sender domain: blocked on sibling project / owner answers.

## 2026-09-10 — Resend custom sender domain wiring (BUILD 2026-09-10.6)
- backend/.env: RESEND_API_KEY, RESEND_FROM_EMAIL=noreply@sacoparentsalign.com (owner-supplied). email_utils: `_post_resend()` tries Resend first (`from: "SA CoParents Align <noreply@…>"`, reply_to), falls back to Emergent sender on any non-2xx/exception; `send_email_detailed()` returns (id, provider). Admin email-test reports which sender was used.
- BLOCKER: supplied key `sk_…` → Resend 401 "API key is invalid" (real Resend keys start `re_`). Fallback verified working (provider=emergent). Also domain must be verified in Resend (SPF/DKIM DNS) or sends return 403 → fallback. Production env must also get RESEND_API_KEY/RESEND_FROM_EMAIL before deploy.

## 2026-09-10 — Close Case action (BUILD 2026-09-10.7; test_close_case 1/1)
- `PATCH /api/joint/reports/{rid}/close` {closed, note}: sets closed_at/closed_by/closed_note + archived (hidden from active Cases table & dashboard cards); closed=false reopens. `case_status` → CLOSED; joint_public exposes `closed_at`. UI: "Close" link in Cases table row + "Close case" button on /matters rows (prompt for optional note); closed matters show "Closed" badge with "Reopen".
- DNS check (dig): sacoparentsalign.com has NO SPF/DKIM/DMARC records yet; Resend key still invalid (sk_). Prod still 2026-09-10.2.

## 2026-09-10 — Close/reopen audit trail + closing summary PDF (BUILD 2026-09-10.8; test_closing_summary 1/1)
- Close/reopen now inserts `access_events` kind=lifecycle {action "Case closed"/"Case reopened", note, by, by_name, by_role}. Activity endpoint returns `lifecycle[]` (excluded from access_events). ProWorkspace "Case lifecycle" list under Consent & Activity.
- `GET /api/joint/reports/{rid}/closing-summary.pdf` (owner; 400 unless closed): one page — case ID/subject/professional, opened/closed/closed-by/reference/child, parent participation, report generated + view/download counts, closing note, timeline, disclaimer. "Closing summary" button on closed matters in /matters.
- Still blocked: valid Resend key (`re_`) not received; DNS records absent; prod on 2026-09-10.2.

## 2026-09-10 — Valid Resend key installed (BUILD 2026-09-10.8)
- RESEND_API_KEY replaced with owner's `re_…` key (send-only). Resend now returns **403 "domain is not verified"** (was 401). DNS check: sacoparentsalign.com has no DKIM (`resend._domainkey`), no `send.` MX/SPF, no `_dmarc`. Fallback (Emergent sender) delivered the live test (id 03de0927…). Once domain verified in Resend, no code change needed — sends switch automatically. Production env still needs RESEND_API_KEY/RESEND_FROM_EMAIL + Deploy.

## 2026-09-10 — Referral inbox + dashboard mobile polish (BUILD 2026-09-10.9; test_referral_inbox 1/1)
- referrals now store from_name/to_name/case_code/status(pending|accepted|declined)/responded_at/response_note. `GET /api/professionals/referrals` → {received, sent}; `POST /api/professionals/referrals/{id}/respond` {accept, note} (recipient only, once) emails referrer. `ReferralInbox.jsx` on pro dashboard (Received/Sent tabs, Accept/Decline with optional note prompt, "N new" badge; hidden when empty).
- Mobile: header px-4/gap tightened, verified badge hidden <sm, main overflow-x-hidden, tool cards min-w-0, long CTA buttons wrap, link-code row stacks.
- Resend: DNS records now present (DKIM/MX/DMARC) but Resend still reports domain not verified (403) → click Verify in Resend; fallback sender in use. Deploy instructions given via support (Republish → Manage Publishes → Secrets → add RESEND_API_KEY/RESEND_FROM_EMAIL → Re-publish; no API/CLI). Prod still .2.
- User asked about seed joint sample case / mini-quiz / ElevenLabs voice chips — clarification requested (latter two don't exist in Align; likely sibling App).

## 2026-06 Deployment readiness
- Deployment scan: PASS. Only finding was unquoted special-char TEMP_PASSWORD values in backend/.env (now quoted). Pasted deploy logs contained no errors (all /health 200).
- Production still requires manual Deploy/Republish; ensure RESEND_*, INTEGRATION_SHARED_SECRET, WEBHOOK_CRON_SECRET, SACOPARENTS_APP_URL set in Manage Publishes.

## 2026-06 Production verification
- Live build 2026-09-10.9 confirmed at sacoparentsalign.com; directory/referrals endpoints protected (401); /join, /accept-invite, /professionals, methodology PDF live.
- Authenticated prod checks blocked: preview test accounts do not exist in production DB (owner must verify or authorize a test pro account).
- Resend: still 403 domain-not-verified; DNS shows send.*, resend._domainkey, _dmarc records all NXDOMAIN (not published).

## 2026-06 Demo Sample Case (build 2026-09-10.10)
- POST /api/joint/reports/professional/sample (approved pros): creates fictional Communication case (Robin/Jamie), both sides complete, READY_FOR_ALIGNMENT, is_demo=true, idempotent (one open sample per pro). Dashboard "Load a sample case" button + SAMPLE badge in CasesTable. tests/test_sample_case.py 4 passed; browser verified.
- Prod live-check account align.livecheck still unapproved; Resend DNS: DKIM published, send.* SPF TXT + MX still missing.

## 2026-06 Sample Walkthrough
- components/SampleWalkthrough.jsx: 10-step guided tour on sample (is_demo) Joint Report page; banner + floating step card, scroll+highlight each jr-* section, localStorage dismissal. Desktop+mobile screenshot verified, no overflow.

## 2026-06 Session Prep Sheet (build 2026-09-10.11)
- GET /api/joint/reports/{rid}/session-prep.pdf (case pro / shared pro only, 403 for parents): one-page facilitator agenda (shared ground, top 3 differences w/ reframe, opening questions, options, next-step checkboxes). Logged as download in access log. Button "Session Prep Sheet" in JointReport header. tests/test_session_prep.py 3 passed; PDF visually verified single page.

## 2026-06 Post-Session Outcome (build 2026-09-10.12)
- PUT /api/joint/reports/{rid}/session-outcome {chosen_steps, summary} (creator only, both complete). Stored on joint_reports.session_outcome; lifecycle event logged; returned in detail for creator only. components/SessionOutcome.jsx in ProWorkspace (tick next steps + options, summary, save). tests/test_session_outcome.py 4 passed; browser verified.

## 2026-06 Outcome in Closing Summary (build 2026-09-10.13)
- Closing Summary PDF now has section 3 "Session outcome" (chosen steps, summary, recorded by/date); sections renumbered (closing note 4, timeline 5, capped at 6 events to stay one page). tests/test_closing_outcome.py + test_closing_summary.py 9 passed; PDF visually verified single page.

## 2026-06 Follow-Up Reminder (build 2026-09-10.14)
- session_outcome.follow_up_date (YYYY-MM-DD, validated). New cron follow-up-reminder (daily 8am Central, .emergent/crons.yml, 4 crons total) -> POST /api/cron/follow-up-reminder -> run_follow_up_reminders(): emails pro once per date (follow_up_reminder_sent flag, reset when date changes), logs lifecycle event, skips closed cases. Frontend date input in SessionOutcome. tests/test_follow_up_reminder.py + test_session_outcome.py 7 passed; browser verified persistence.

## 2026-06 Upcoming Check-Ins
- components/UpcomingCheckIns.jsx on Dashboard above CasesTable: lists creator cases with session_outcome.follow_up_date within 7 days (or overdue), Today/Tomorrow/weekday chips, link to case. Frontend-only (data already in /joint/reports). Desktop + mobile screenshot verified.

## 2026-06 Full regression
- Full backend suite: 207 passed. Testing agent iteration_38.json: 22/22 backend + all frontend criteria pass for sample case, walkthrough, prep sheet, outcome, follow-up cron, check-ins panel, closing summary. retest_needed=false. Preview build 2026-09-10.14 ready to publish.

## 2026-06 Court Packets phase 1 (build 2026-09-11.1)
- backend/court_packets.py (router mounted at /api): pro creates packet (judge name/email/court/cause, cover letter >=40 chars, extra own ready report_ids, include outcome/closing, attestation required) -> one-time link /court/<token> + separate 6-digit code emails; 30-day expiry; judge unlock (8 attempts) -> 4h access session (X-Court-Access header / ?access= for PDF); GET packet JSON, combined PDF (cover letter + report PDFs + closing summaries via pymupdf merge), respond acknowledged/clarification (emails pro); pro list/revoke/resend/pdf. All events logged to access_events kind=court.
- Frontend: pages/CourtPacket.jsx (/court/:token), components/CourtReportView.jsx, CourtPacketPanel.jsx (in ProWorkspace). tests/test_court_packets.py 6 passed; full suite 220 passed (after fixing hardcoded build string in test_iteration_38_review). Desktop+mobile verified.
- Phase 2 (not started): judge/court accounts with admin approval + Court Dashboard (user chose option c).

## 2026-06 PDF copyright
- All PDFs (via _JointPDF.footer) now stamp "© 2026 sacoparentsalign.com · SA CoParents Align. All rights reserved. · Page N" on every page; _new_pdf sets author/creator/subject metadata; merge_pdfs sets metadata on merged Court Packet. Verified across 7 PDF types; test_methodology_pdf updated. Build 2026-09-11.2.
- DNS incident: apex A + www records missing at Squarespace (Resend edit overwrote); user instructed to re-add Emergent A records + www CNAME, move Resend MX from @ to send, re-verify domain, republish.

## 2026-06 Judge accounts + transmittal (build 2026-09-11.3)
- role "judge": register via /auth?mode=register&court=1 (account-type tabs; court required), approved=false; admin endpoints GET /admin/judges, POST /admin/judges/{id}/approve|decline; AdminJudges panel on admin dashboard. Judge routes: GET /court-dashboard/packets (approved gate), GET/.../{pid}, /pdf, POST /respond (email match, logged). Protected route redirects role judge -> /court-dashboard (pages/CourtDashboard.jsx); PacketViewer.jsx shared with token flow. GET /court-packets/{pid}/transmittal.pdf one-page Certificate of Transmittal + button in CourtPacketPanel. tests/test_judge_accounts.py 6 + test_court_packets 6 passed; browser: judge register -> pending dashboard OK.

## PENDING SEND: court invite for Judge Nicole Garza <NICOLE.GARZA@bexar.org>, 37th District Court — send from Admin > Court Accounts (POST /api/admin/judges/invite) once production DNS is restored and republished.

## 2026-06 Court workflow (build 2026-09-11.6)
- backend/court_workflow.py: court_referrals (judge -> pro), accept/decline, case creation via court_referral_id (JointNew ?referral=), 7-stage court_stage in joint_public, Professional Statement (draft/ready, custody-language block, letterhead PDF), submit-to-court (frozen combined PDF in court_frozen_pdfs w/ SHA-256, versioned packets, superseded flag, lifecycle audit, judge email), judge referrals list w/ rule-based status summary (signature-based Outdated, refresh endpoint). Admin invite judge (court_invites -> auto-approved registration). Landing tagline "For Professionals"; sample-case PDF watermark SAMPLE REPORT.
- Tests: test_court_workflow 6, test_judge_invite 2, judge accounts 6, court packets 6 pass; testing agent iteration_39.json full E2E pass. Deployment scan PASS.
- STATUS: DNS restored (A 34.57.15.54, www CNAME), Resend domain VERIFIED (branded test send 200 to owner). Production still on 2026-09-10.9 -> user must Republish. Then send court invite to Judge Nicole Garza <NICOLE.GARZA@bexar.org>, 37th District Court via Admin > Court Accounts.

## 2026-06 Code-quality refactor (build 2026-09-11.7)
- court_packets.py: PacketService class + _pro_routes/_link_routes/_judge_routes (build_router complexity 106 -> trivial). court_workflow.py: _shared/_judge_routes/_pro_routes; build_status_summary -> HEADLINES table + line helpers; court_stage -> _stage_index guard clauses. pdf_report.py: _letterhead/_contact_line/_footnote shared. Tests: "is True/False" asserts -> truthiness; type hints added to test fns/fixtures; hardcoded build strings relaxed. Ruff F632/F821 clean. Full suite 249 passed; testing agent iteration_41 regression 24/24 + frontend smoke pass.

## 2026-09-13 — Navigation/hierarchy pass (iteration 42, all tests passed)
- Production confirmed LIVE at sacoparentsalign.com + www, build 2026-09-11.7 (same as preview at the time). New work below is NOT yet republished.
- Homepage: hero "Better Information. Stronger Decisions. Brighter Futures."; "Two ways a case begins" (Option 1 not court-ordered: pro invites parents; Option 2 court-ordered: court invites pro); 6-step journey; separate 8-step "For Courts" pathway (#for-courts); nav trimmed.
- Pro Dashboard: 4 primary tiles (Manage a Case | Invite Parents | Review Joint Reports | Court-Referred Cases) with live counts; Tools pill row; "Your Cases" (real only); Court-Referred Cases panel always visible; separate "Sample Reports" section; legacy tools (app link, joint agreement, FV contact, invite code) under collapsed "More tools". Circle diagram + Available Professionals removed from dashboard.
- Judge portal: Court Cases cards with labeled fields (Assigned Professional, Current Status, Hearing Date (editable), Joint Assessment Status, AI Status Summary, Final Reports & Statements, Communications & Audit).
- Hearing date: ReferralIn.hearing_date; PATCH /api/court-dashboard/referrals/{id}/hearing-date (judge only); shown in pro inbox; cron POST /api/cron/hearing-reminder (daily 8am CT, .emergent/crons.yml) emails pro + judge once, 7 days before, if not submitted. Tests: backend/tests/test_hearing_reminder.py.
- Judge Garza invite: NOT sent — requires production admin login (owner-reset password unknown to agent) and the judge's email is not in this context. Owner: live Admin → Judges → Invite Judge.
- Backlog: republish; live court check after publish; Communications / AI Case Summaries / Account-Org settings pages (linked tools currently omitted as they don't exist); C901 split of _pro_routes (optional).

## 2026-09-13 — Case Communications Log (iteration 43)
- email_utils.send_email(_detailed) accepts case_id/kind/to_role and calls a registered logger -> db.communications. All invitation, nudge, report-ready, follow-up, court referral/decline/submission, hearing, court packet/code/response emails are tagged.
- GET /api/joint/reports/{rid}/communications (case pro only); GET /api/court-dashboard/referrals/{id}/communications (owning judge; court-facing kinds only, never parent emails).
- UI: CommunicationsLog in ProWorkspace (/joint/{rid}); compact "Court-facing notices" in judge Court Case card. Tests: backend/tests/test_communications_log.py.
- Production still on 2026-09-11.7 at check time — user must Republish; Judge Garza invite still pending on user (needs live admin login).

## 2026-09-14 — Export, overdue alerts, judge-picked report types, tile rename
- Dashboard tiles: Manage a Case | Judge Referrals | Review Joint Reports | Submit to Court (red OVERDUE state).
- GET /api/joint/reports/{rid}/communications.pdf — Communications Log exhibit (copyright footer/metadata). UI export button in CommunicationsLog.
- referral.overdue (hearing ≤7 days, not submitted) — red flags on judge card, pro inbox, dashboard tile.
- Judge picks requested_reports (co_parenting, communication, education, medical, psychological, mediation, complete, agreement, family_violence) in ReferCaseForm; stored on referral; shown to pro (inbox chips, /joint/new banner, subjects preselected) and judge card. REPORT_TYPES in court_workflow.py.
- Tests: backend/tests/test_comms_export_overdue.py. Production still needs Republish; Judge Garza invite pending on user.

## 2026-09-14 — Redefined Co-Parenting Agreement (v2) + judge report-type trim
- joint_data.AGREEMENT_SECTIONS: 10 sections (Foundation, Transitions, Communication, Education, Medical, Psychological, Activities, Major Decisions, Managing Differences, Review) each with shared goal, main question, 3–5 follow-ups (keys section__fk), and role mapping (comm/decision/review).
- Parent form (JointAssessment) shows follow-ups after the main answer; only main answers required.
- generate_agreement → per section: Shared Goal, Current Alignment, Specific Agreements, Communication Method, Decision Process, Review Trigger, Issues Still Requiring Resolution; summary 3 groups; status labels. Rule-based drafting + AI (agreement_ai.py, gpt-5.4-mini via EMERGENT_LLM_KEY, item verdicts agreed/open, cached in doc.agreement_ai by answers signature; disputed items never become clauses).
- New PDF layout (At a Glance + numbered sections), AgreementDocument.jsx UI. Old 8-term agreements not supported (user OK).
- Court Refer form report types: co_parenting, education, medical, psychological, agreement, family_violence only.
- Tests: tests/test_agreement_v2.py; legacy test_agreements_and_pro_requests updated to 10 keys.

## 2026-09-14 — Three-layer architecture: Judicial Portal, court–professional communication, Case ID at referral
- Homepage: two portal doors (Professionals / Courts), model strip Parent Reflection → … → Court Review (when needed); header [Professional Sign In] [Judicial Portal].
- Judicial Dashboard = table (Case/ID, Professional, Parents n/2, Assessments, Joint Report, Prof. Statement, Hearing) + Review Case → /court/case/:refId (pages/CourtCase.jsx) with 5 sections: Case Status checklist, AI Court Summary (+counts, disclaimer), Joint Assessment Report (submitted only; Alignment/Difference/Child-Focused/Options), Professional Statement (frozen, role + materials), Court–Professional Communication.
- Backend: GET /api/court-dashboard/cases/{refId} (court_workflow.judge_case); court_messages.py: GET/POST judge + pro message endpoints, emails (kind court_message), AI communication_summary (gpt-5.4-mini, rule fallback) stored on referral.
- Case ID: referral gets case_code at creation (joint_data.new_case_code, moved from server.py); case creation from referral reuses it.
- Statement: role (STATEMENT_ROLES), materials_reviewed (STATEMENT_MATERIALS fixed list + Other), alignment_areas, further_attention, resources_considered, current_status; PDF updated. App.js judge redirect allows /court/case/*.
- Tests: tests/test_judicial_portal.py. CourtCaseCard.jsx now only exports HearingDate (card replaced by table).

## 2026-09-14 — Code-quality pass #2
- Report items "undefined variable" and 12× `is` misuse were false positives (ruff F821/F823 clean; all `is None`/`is not None`). Kept as-is.
- court_workflow.py: _judge_routes split into _judge_routes + _judge_case_routes; judge_case → pure helpers (judicial_case_payload, _case_checklist, _court_report_view, _submitted_material); _pro_routes split into _pro_routes + _pro_statement_routes; validated_statement / assert_submittable extracted. C901: 57→14, 39→12.
- court_messages.py: notify/load_ref/thread_view extracted; judge/pro registration split. 19→13.
- server.py module split (31 imports) deferred: high-risk, no functional gain; not requested by user beyond report.

## 2026-09-14 — Code-quality pass #3 + deployment readiness
- Ctx dataclass replaces 8-arg court route factories; _judge_case_routes decomposed (_judge_row, _load_judge_referral, _case_and_packets, _court_event, _email_hearing_set): 26→~8. court_packets _pro_routes split (case packet routes / packet admin routes) + _assert_packet_allowed. run_hearing_reminders restored after an accidental drop (import error caught, fixed, verified).
- "Undefined variable" + `is` findings: false positives again (ruff F821/F823/F811 clean; only `is None`). Remaining C901 12-13 on two factories is inherent to nested handlers.
- Focused court suites 26 passed; deployment_agent PASS. Awaiting user Republish (agent cannot deploy).

## 2026-09-14 — Judge Weekly Digest
- judge_digest.py: run_judge_digests(db, send_email, app_url, from_name, logger) → one email per approved judge with open referrals: table of Cause No./Case ID, professional, stage, hearing date (OVERDUE flag), unanswered court messages ("Unanswered since …"), procedural disclaimer. Kind judge_digest.
- POST /api/cron/judge-digest; .emergent/crons.yml "judge-digest" Monday 07:00 America/Chicago (6 crons total). Tests: tests/test_judge_digest.py.

## 2026-09-14 — Co-Parenting Dynamic Scale → professional-only Options/Resources/Techniques
- coparenting_tiers.py: 1–10 scale, 3 tiers (1-3 High Risk/IPV, 4-6 Moderate, 7-10 Collaborative) with framework, techniques (BIFF, cooling-off, third-party transfers…), tools (AppClose/OFW…), San Antonio resources; suggested_score(case) from Joint Report alignment ratio (safety cases capped at 3); framework_block(score, choices).
- StatementIn.dynamic_score + framework_choices → statement.framework; GET statement returns suggested_score + tiers. Statement PDF section "CO-PARENTING DYNAMIC SCALE & RECOMMENDED FRAMEWORK"; judicial case page shows it (court-statement-framework). Parent-facing Joint Report unchanged.
- UI: components/FrameworkPanel.jsx (slider, tier badge, safety alert, untick items) inside ProfessionalStatement. Test in tests/test_judicial_portal.py.

## 2026-09-17 — Professional Report = single legal deliverable (tested: iteration_47 backend+frontend, pytest 52/52)
- User decisions: options/resources/conflict techniques live ONLY in the Professional Report (professional + judge; never parents); Ability Level stays 1-10 (3 tiers); no AI drafting; Options section removed from parents' Joint Report for ALL cases incl. public samples; Professional Report available on every professional case (PDF for own file; court submission only for court-referred).
- Backend: coparenting_tiers.py → joint_findings() (alignment/differences-by-area/child_focused/alignment_map/subject_options), suggested_score() (alignment ratio, ≥4 differences −1, communication areas needing discussion −1, safety cap 3, neutral rationale), framework_block(score, choices, custom, subject_options). StatementIn gains framework_custom; statement persists dynamic_score/framework_choices/framework_custom (round-trip fix after iteration_47). GET professional-statement returns findings + subject_options. PDF build_professional_statement_pdf restructured: 1 Case & referral → role → 2 Materials → 3 Process → 4 Joint Assessment Findings → 5 Ability Level → 6 Options & Resources → 7 Conflict-Management Techniques → 8 Current status → 9 Observations (+alignment/attention/safety) → 10 Next steps → attestation. Joint PDF section 7 Options removed (renumbered 1-9); /joint/reports/{rid}/report and /joint/sample/* pop 'options'; _court_report_view drops options.
- Frontend: FrameworkPanel (slider, suggestion, per-group checklists incl. subject options, add-your-own with OWN badge/remove), ProfessionalStatement shows findings grid + "Professional Report" copy, CourtCase section 4 "Professional Report" w/ court-ability-level pill; JointReport/SampleReport options sections removed.
- Still pending from earlier: user-side admin login check, production republish + live E2E, Judge Garza invite, strict C901 on court_messages.build_router / _pro_statement_routes.

## 2026-09-17 (later) — Resource Library Editor + Level History (tested: iteration_48 frontend 100%, pytest judicial/court 12/12)
- GET/PUT /api/me/resource-library (approved pros; {resources, tools, techniques}, cleaned/deduped, stored users.resource_library). get_statement returns `library`; framework_block merges library into the tier pool (kept unless unticked). UI: ResourceLibrary.jsx inside FrameworkPanel (toggle, per-group add/remove), MY LIBRARY badge on checklist items.
- Level History: court_submissions entries store level_score/level_label; judicial_case_payload.level_history[] (oldest first, superseded flag); CourtCase.jsx timeline (court-level-history-{v}); ProfessionalStatement submission pills (submission-level-{v}); PDF section "ABILITY LEVEL HISTORY".
- BUILD_ID bumped to 2026-09-17.1. Deployment agent: PASS. Production still on 2026-09-11.7 → user must click Republish; then verify https://sacoparentsalign.com/api/health shows 2026-09-17.1 and run the live court walkthrough (judge referral → professional report → frozen submission) with controlled test accounts.

## 2026-09-17 (final) — Level Change Note + Organization library
- Level Change Note: StatementIn.level_change_note (≤300 chars, custody-phrase scan applies). validated_statement sets level_changed_from when dynamic_score ≠ last court_submissions[-1].level_score; marking ready without a note → 400. Submission stores level_change_note/level_changed_from; level_history rows carry note/changed_from; CourtCase shows court-level-note-{v}; PDF prints "Change since last submission" + history line suffix. UI: amber level-change-note-box in FrameworkPanel (lastSubmittedScore prop).
- Organization library: db.org_libraries keyed by lowercased profile.organization; PUT /api/org/resource-library (400 without organization); GET /api/me/resource-library now returns {…own, organization, org_library}; get_statement returns org_library/organization; effective_library (own ∪ org) feeds framework_block. UI: ResourceLibrary tabs (mine/org, ids resource-library-*/org-library-*), checklist badges MY LIBRARY / ORG.
- Tests: test_judicial_portal.py::test_level_change_note_and_org_library (7/7 file). Production still 2026-09-11.7 — awaiting user Republish.

## 2026-09-17 — Env-driven production recovery seeds (no HTTP backdoor)
- Approach 1 (direct prod Mongo) impossible: workspace only has preview MONGO_URL (localhost). Documented admin password no longer works on prod (user reset it) and the user cannot log into live Admin either.
- Added startup seeds in server.py: `AUTO_APPROVE_EMAILS` (comma list → professional/judge accounts set approved/credentials_verified, lockouts cleared; idempotent) and `ADMIN_PASSWORD_RESYNC=1` (forces admin hash back to ADMIN_PASSWORD env even if password_reset_by_user; unsets flag; clears lockout). Set in Emergent Deploy → Environment variables, then Republish; remove afterwards. Verified locally (2 fixture accounts approved, then deleted). Rejected the requested secret-token /api/admin/auto-approve endpoint as a standing backdoor.

## 2026-09-17 — Professional Report Section 6 "Parent Alignment — Based on Joint Report" (user's v8 HTML spec)
- New statement fields partial_alignment, alignment_summary (STATEMENT_FIELDS/StatementIn). Section 6 = alignment_areas ("Where the parents agree"), further_attention ("Where the parents do not agree"), partial_alignment, alignment_summary. PDF order: 1 Case & referral → 2 Materials → 3 Process → 4 Joint Assessment Findings → 5 Ability Level (+history) → 6 Parent Alignment → 7 Conflict Management (options/resources/techniques, resources considered, safety) → 8 Roadmap (status, next steps) → 9 Professional Summary (observations) → attestation. Editor groups fields under these headings (statement-group-{n}); CourtCase STMT labels updated. pytest test_judicial_portal 7/7.
- v8 template: /app/frontend/public/legal-lens-report-to-court-v8.html (9-section printable template served at /legal-lens-report-to-court-v8.html). StatementIn accepts camelCase aliases alignmentAgreements/alignmentDisagreements/partialAlignment/alignmentSummary (populate_by_name). Verified: PUT with camelCase → stored, 7/7 tests, template 200. Production deploy = user Republish (build 2026-09-17.1 pending).

## 2026-09-20 — Sample Professional Report (legal) on Sample Reports page
- backend/sample_professional_report.py: fictional fully written 9-section report (education scenario, Level 6, history v1=4→v2=6 with change note, custom resource, fictional pro/court). Endpoints GET /api/joint/sample-professional-report (+/pdf, SAMPLE watermark; build_professional_statement_pdf honours is_sample). Frontend: /samples/professional-report (SampleProfessionalReport.jsx, testids sample-pro-*) + highlighted card on /samples (sample-card-professional-report). Verified curl JSON/PDF (53 KB, contains 6. PARENT ALIGNMENT / 9. PROFESSIONAL SUMMARY / ABILITY LEVEL HISTORY).
- iteration_50 found mobile header overflow on /samples/professional-report → fixed (responsive header labels, logo hidden <sm); iteration_51 retest.
- PROD CHECK 2026-09-20: production republished to 2026-09-17.1 (Professional Report / Level History / Judicial Portal live; parent samples no longer expose options). NOT yet live: Level Change Note, org library, Section 6 Parent Alignment, Sample Professional Report (/api/joint/sample-professional-report 404), env seeds (admin login with documented password still fails → ADMIN_PASSWORD_RESYNC not applied). BUILD_ID bumped to 2026-09-20.1; user must Republish again (+ set AUTO_APPROVE_EMAILS / ADMIN_PASSWORD_RESYNC env vars first).

## 2026-09-20 — Sample Professional Report email + Judge Sample Preview
- POST /api/joint/sample-professional-report/email {email} (EmailStr; view+PDF links). SampleEmailForm.jsx reused on /samples card (sample-pro-email-*) and on the sample page (sample-pro-page-email-*).
- GET /api/court-dashboard/sample-case (public, fictional payload same shape as judicial case). Route /court/sample renders CourtCase with `sample` prop: banner, register CTA instead of logout, static hearing date, read-only AI summary (CourtStatusSummary readOnly), thread replaced by note, packet PDF → sample professional report PDF. Card sample-card-judicial-preview on /samples.
- Production still 2026-09-17.1 at this point; BUILD_ID is 2026-09-20.1 in preview — user must Republish with AUTO_APPROVE_EMAILS / ADMIN_PASSWORD_RESYNC env set.

## 2026-09-20 — Professional Legal Report (user's 18-point spec; choices 1a/2a/3a/4b)
- Same record as the Professional Report (joint_reports.professional_statement) + legal_status not_started/draft/professional_review/finalized, legal_draft (parent_a/b_summary labelled PARENT-REPORTED INFORMATION, joint, child_focused_summary, communication_summary, safety_notice), ai_generated_content (legal_ai.py: GPT-5.4-mini via Emergent key with user's system prompt, rule-based fallback; every lens field prefixed "AI-ASSISTED DRAFT — PROFESSIONAL REVIEW REQUIRED"), lens fields (observations/further_attention/alignment_areas/partial_alignment/procedural_considerations/professional_comments), options_resources/options_custom, conflict_resolution_paths/explanation, certification (checkbox+name+date required; title/bar/org/email/phone optional), legal_report_versions snapshots (v1, v2… never overwrite).
- Routes (legal_report.py router): GET /api/cases/{rid}/professional-legal-report, POST …/generate {regenerate}, PATCH /api/professional-legal-reports/{rid} {fields} (banned pejorative labels → 400), POST …/preview, POST …/finalize, GET …/pdf (DRAFT - REVIEW REQUIRED watermark until certified), GET /api/professional-legal-report/sample (+/pdf, Jordan Taylor J.D., SAMPLE-2026-001). Access: approved professional owning the case or admin; parents 403. Audit via access_events kind=lifecycle actions LEGAL_REPORT_{CREATED,GENERATED,VIEWED,EDITED,PREVIEWED,FINALIZED,EXPORTED}.
- Frontend: ProfessionalLegalReportCard (LEGAL LENS badge, status, Review Sample / Create|Continue) in ProWorkspace; /joint/:id/legal-report (LegalReport.jsx: availability checklist, generate, sections 1-7 generated, 8 lens editable w/ AI label, 9 options checklist + own, 10 paths multi-select + explanation, 11 safety, certification, actions Save/Preview/Regenerate/Finalize(confirm dialog)/Export PDF, versions); /joint/:id/legal-report/sample and public /samples/legal-report (LegalReportSample.jsx); shared LegalReportSections.jsx.
- Foundation Statement questionnaire: JointAssessment.jsx now has an optional in-app Foundation Statement textarea for joint_report cases (stored responses[role].foundation; server _validated_answers accepts it) → appears in Section 4 and availability.
- Tests: tests/test_legal_report.py.
- iteration_53 (frontend) all pass; only note: "Other Professional Comments" intentionally not AI-prefilled (professional's own words) — UI hint added. Production still 2026-09-17.1; preview build 2026-09-20.1 awaiting user Republish with AUTO_APPROVE_EMAILS / ADMIN_PASSWORD_RESYNC.

## 2026-09-20 — Legal Lens Review and Report to Court (user's /professional-report spec)
- Backend legal_lens.py (collection professional_reports, one per case): GET/PUT /api/cases/{rid}/professional-report (auto-created + prefilled from case: parent names, court, suggested joint rating, working_well→strengths, concerns→gaps, joint findings→alignment fields, FV receipt from safety subjects), GET …/readiness, GET …/pdf (build_legal_lens_pdf: lavender headings, DRAFT watermark until final, footer_meta tagline "SA CoParents — Starting With Alignment, Ending With Agreement" + case ID/pro/date + page numbers), GET /api/professional-report/cases. Bands: INDIVIDUAL_BANDS / JOINT_BANDS (mode + guidance) exactly per spec; resource lists per spec (no Joint Transition Protocol / focused assessments). Statuses draft/under_review/final/submitted_to_court; final requires signature_name. Parents 403.
- Frontend: /professional-report (ProfessionalReportHome: case picker w/ readiness), /cases/:id/professional-report (LegalLensReport.jsx: 13-step strip, sections 1-10, rating sliders w/ auto classification, provider sub-fields, guidance, notes, actions Save/Preview(PDF iframe)/Generate PDF/Finalize/status), LegalLensCard in ProWorkspace with readiness checkmarks + "Prepare Legal Lens Review & Report to Court". Backend flow verified by script (prefill, classes, finalize gate, PDF).
- Open: older "Professional Report" (statement) and "Professional Legal Report" (12-section) still exist alongside; user asked why report differed — root cause: v7 HTML never received. Consider consolidating once user confirms this new page is the source of truth.
- iteration_54 (frontend, Legal Lens builder): all pass. Note: fixture with fully aligned answers yields empty disagreement prefill (expected). Production still 2026-09-17.1 — Republish pending (preview 2026-09-20.1).

## 2026-09-20 — Consolidation: Legal Lens Review = the Professional Legal Report
- ProWorkspace shows only LegalLensCard ("Professional Legal Report · LEGAL LENS"); /joint/:id/legal-report(+/sample) → redirect to /cases/:id/professional-report; /samples/legal-report → /samples/professional-report; Samples card link removed. Old legal_report.py routes remain (unused by UI).
- Court attachment now uses Legal Lens: court_workflow.legal_pdf_bytes builds build_legal_lens_pdf when professional_reports.status ∈ {final, submitted_to_court} (else 400 "Finalize the Legal Lens…"), sets status submitted_to_court; get_statement returns legal_lens {status, signature_name}; ProfessionalStatement checkbox keyed on it; legal_version = submission version. test_legal_report.py 3/3.
- iteration_55 (consolidation + court attachment) all pass. Removed orphaned UI files (ProfessionalLegalReportCard, LegalReport, LegalReportSample, LegalReportDiff). Production still 2026-09-17.1 — Republish pending.

## 2026-06 — Sample Legal Lens Report (agent-tested, preview only)
- Public fictional finalized Legal Lens Review: GET /api/joint/sample-legal-lens (+ /pdf, POST /email); page /samples/legal-lens-report; card on /samples (data-testid sample-card-legal-lens).
- Files: backend/sample_legal_lens.py, frontend/src/pages/SampleLegalLensReport.jsx; reuses build_legal_lens_pdf.
- Verified: JSON + 5-page PDF (no DRAFT watermark), desktop/mobile render. Not user-confirmed, not republished to production.
- Guided spotlight tour on sample Legal Lens page: components/SampleLensTour.jsx (10 steps, auto-start once via localStorage key sa-lens-sample-tour-seen, "Start tour" replay, data-testids lens-tour-*). Screenshot-verified desktop+mobile.
- Gemini integration (2026-06): POST /api/cases/{id}/professional-report/ai-draft {model: gemini|openai, fields} -> Gemini 3.1 Pro (gemini-3.1-pro-preview, default) or GPT-5.4 Mini via EMERGENT_LLM_KEY, rule-based fallback; drafts joint_notes, alignment_summary, conflict_management_rationale, short/long_term_goals, professional_summary, all prefixed "AI-Assisted Draft — Professional Review Required". UI: model select + "AI-assist draft" in LegalLensReport toolbar (hidden when final/submitted), fills empty fields first. Code: legal_ai.py draft_lens_report, legal_lens.py ai_draft. Verified via curl (both models) + screenshot; not user-confirmed.
- Provider Directory (2026-06): backend/providers.py — collection providers seeded (Kelly Bernstein, Kassandra Levay, Brad Craig); admin CRUD /api/admin/providers, pro read /api/providers; legal_lens view() builds resource checklists from active providers (resource_lists) and exposes library.providers; frontend AdminProviders.jsx on admin Dashboard; ticking a provider in LegalLensReport auto-fills provider name/specialty/contact.
- Draft Comparison (2026-06): ai-draft stores report.ai_drafts{field:{text,model,at}}; finalize computes ai_review{edited} + audit event LEGAL_LENS_AI_DISCLOSURE; AiDraftComparison.jsx collapsible side-by-side; PDF "Appendix — AI-Assisted Drafting Disclosure" (_lens_ai_appendix). Verified via API + screenshots.
- Admin "Add professional" (2026-06): POST /api/admin/professionals {name,email,profession(dropdown: Mediator, Parenting Facilitator, Parenting Coordinator, Attorney, Counselor / Therapist, Custody Evaluator, Other),degrees,phone,organization} creates pre-approved professional (invite_pending) + 7-day set-password link reusing password_resets/reset-password flow; POST /api/admin/professionals/{id}/resend-invite. UI: AdminAddProfessional.jsx inside AdminProfessionals ("Manage professionals"), Invite pending badge + Resend. Provider Directory gained a degrees field. Verified via API + screenshot.
- 2026-06 code review pass: verified NO circular import (sample_professional_report -> legal_report is one-way lazy), NO undefined names (ruff F821 clean), all flagged "is" comparisons are `is None`/`is not None` (correct). Refactored legal_lens.py (sanitize_fields/apply_status/ai_disclosure_line/merge_drafts/case_summary; build_router C901 54->16) and legal_ai.rule_based_lens_report (_v helper). Deferred: court_workflow/joint_engine/court_messages complexity refactors (pre-existing, tested court code). Kelly Bernstein provider: MS, LCDC, LPC · (210) 265-1952 (seed + preview DB).
- 2026-06 code review round 2: legal_common.py holds shared Legal Report constants (legal_report + sample_professional_report both import from it; no cycle). court_workflow: validated_statement split (_framework_fields/_assert_statement_ready), _library_routes factory extracted, _legal_pdf_bytes/_frozen_packet/_submission_record/_submission_email_html module-level; joint_engine: _agreement_section/_agreement_summary; legal_lens: sanitize_fields via _CLEANERS dispatch. 27 backend tests pass. Remaining C901: _pro_statement_routes 15, legal_lens.build_router 16 (route-count only).
- 2026-06: Sample Professional Report now = Legal Lens sample (single card on /samples; old 12-section sample page removed, /samples/professional-report + /samples/legal-report redirect to /samples/legal-lens-report). Buttons: View (web), View PDF (inline, ?inline=1), Download PDF. Judicial sample case PDF points at Legal Lens sample. Old /api/joint/sample-professional-report JSON endpoints remain (unused by UI).
- 2026-06 REBUILD: Professional report now follows the user-supplied Gemini "Professional Evaluation Report" HTML: intro, 1 Safety First (FV receipt + 4-category IPV risk screening levels/notes + takeaway), 2 Individual Breakdown (A/B strengths, gaps, 3 growth areas; Joint Dynamic Summary w/ operating mode), 3 static 1-10 scale table w/ auto Case Placement, 4 Roadmap, 5 Resource table rows (category/resource/focus, quick-add from provider directory), 6 Reassessments (interval, up/down), 7 Conflict Resolution Pathways (auto-recommended by joint rating, override), Professional Certification. New fields: safety_takeaway, parent_x_growth, risk_screening, resource_rows, reassess_*, conflict_pathway. Files: legal_lens.py (SCALE_TABLE/RISK_*/PATHWAYS), pdf_report.build_legal_lens_pdf (fpdf2 tables), legal_ai LENS_REPORT_KEYS, LegalLensReport.jsx, components/LensScale.jsx, sample_legal_lens.py + SampleLegalLensReport.jsx (their sample content), SampleLensTour steps. Title: "SA CoParents Align Professional Evaluation Report". Old alignment fields kept in DB but no longer in the form.
- Tightened: recommended_pathway thresholds 1-2 court/3-4 facilitation/5-6 mediation/7-9 child-centered/10 direct; provider quick-add skips duplicates (toast); reassess fields default-filled in view().
- Growth Area Tracker (2026-06): report.growth_status {a|b: {line: bool}}; editor GrowthTracker checkboxes under Key Growth Areas; PDF marks [MET at reassessment]; court_summary() snapshot frozen on packet as legal_summary at submit; level_history rows carry growth {a,b:{met,total,items}}.
- Court View Alignment: CourtCase.jsx renders CourtLegalSummary (ratings, IPV risk screening, growth progress, pathway, goals, resources) from statement.legal_summary and hides old alignment statement fields when present; sample judicial case includes _sample_legal_summary. test_legal_report updated (3 pass).
- Gemini: already integrated (Gemini 3.1 Pro default AI-assist draft) — user re-requested; no change needed.
- Reassessment Reminder (2026-06): legal_lens.run_reassessment_reminders emails professional when next_review_date <= today (final/submitted reports), idempotent via reassess_reminder_for; wired into existing daily follow-up-reminder cron endpoint (platform cap 5 crons; crons.yml already lists 6 — judge-digest is the 6th and is NOT scheduled). tests/test_reassessment_reminder.py.
- Score Trend Chart: level_history rows carry ratings {parent_a,parent_b,joint}; ScoreTrendChart.jsx (recharts) on CourtCase and ProfessionalStatement (professional-statement GET now returns level_history). Sample judicial case has ratings/growth.
- Cron limit fix (2026-06): judge-digest merged into weekly-summary cron (Mon 8am Central runs run_weekly_summaries + run_judge_digests); crons.yml now exactly 5 entries. /api/cron/judge-digest endpoint kept (unscheduled).

## 2026-09-22 — Individual parent scale tables (preview, agent-tested)
- Section 3 of the Legal Lens report now renders three tables: Parent A individual, Parent B individual (Strengths / Challenges per band, placement column includes Key Growth Areas + MET status), then Joint table.
- Applied to: professional editor, sample report + tour tip, PDF (`_lens_individual_scale`), judge court view (`court_summary` now freezes `scale_table` + `placement`; `CourtLegalSummary` renders tables when present).
- Verified: sample PDF contains new headings; legal_report + court_workflow tests 9 passed; sample & /court/sample render all three tables. Not user-confirmed; not republished.
- 2026-09-22: Growth progress bars (`GrowthProgress` in CourtLegalSummary.jsx) added to judge growth block (`court-legal-growth-progress-{a,b}`) and professional GrowthTracker (`lens-growth-progress-{role}`). Verified on /court/sample: 1 of 3 (33%) / 2 of 3 (67%). Awaiting republish.
- 2026-09-22: PDF growth bar (`_growth_bar` in pdf_report.py) under each parent's Key Growth Areas; sample report now carries growth_status (A 1/3, B 2/3). Production confirmed on build 2026-09-21.1; /api/providers live (401 unauth).
- 2026-09-22 PREVIEW COURT WALKTHROUGH: iteration_56 — full referral→accept→case→parents→Legal Lens finalize (400 without signature)→growth met→statement ready→submit-to-court include_legal_report (400 before finalize, 200 after)→judge view (scale_table/placement/growth)→PDFs. 7/7 backend + Playwright public pages pass. Test file tests/test_iter56_court_walkthrough.py. PRODUCTION walkthrough still blocked: admin login 401 with documented password; no Wingman credentials received.
- 2026-09-22: BUILD_ID bumped to 2026-09-22.1 (scale tables + growth bars). Awaiting user Republish; verify https://sacoparentsalign.com/api/health shows 2026-09-22.1.
- 2026-09-22: PDF Section 3 pagination — page break before Section 3; Parent A + Parent B tables share one page (compact table style, wider placement column); Joint table starts on its own page. Verified on sample PDF (p4 A+B, p5 Joint).

## 2026-09-23 — Judicial Portal redesign + Professional Report 7-section reframe (preview, agent-tested pending)
- Code review pass 3 applied (server.py split into core/auth/joint_helpers/admin_routes/integrations/cron_jobs; court_workflow/legal_lens/court_messages/court_packets complexity refactors; lens_data.py). 276 pytest + iteration_57 live regression passed.
- Judicial Portal (/court-dashboard) rebuilt in two-column layout (components/JudgePortal.jsx): searchable case sidebar, Case Overview, Parent Assessment Status, Reports Available (deep links to /court/case/:id#reports|#statement|#summary|#thread), inline Professional Communication thread, Refer Case + legacy Court Packets kept, empty state = How it works + Refer form. CourtCase sections have ids + hash scroll.
- Professional Report reframed to user's 7 sections: 1 Case & Assessment Overview (intro, assessments completed, sources_considered, safety screening) · 2 Individual Parent Perspectives (+ Parent A/B scale tables) · 3 Joint Assessment Findings (alignment/partial/differing/shared_concerns/further attention + joint table) · 4 Child-Focused Issues (child_focus checklist of 9, prefilled from Joint Report) · 5 Options & Resources · 6 Conflict Resolution Pathways (12 pathways multi-select `conflict_pathways`, `pathway_rationale` required to finalize when pathways selected, CONFLICT_GUIDANCE helper) · 7 Professional Statement (professional_summary, goals, reassessment, growth tracker, principle, certification). Applied to editor, PDF, sample + tour, court_summary (pathways list, child_focus, professional_summary) and CourtLegalSummary. Old field names preserved.
- 2026-09-23 (later): User's "Professional Alignment Report" HTML applied. (a) /frontend/public/legal-lens-report-to-court-v8.html replaced with the static 8-section print template as-is. (b) Live report design: gradient ReportHeader, SourceTag (parent/system/professional/safety), AlignmentStatusGrid, SafetyPathwayCard, ReportDisclaimer + signature lines (components/LensSections.jsx); PATHWAYS reduced to 6 (direct, coach, child_centered, mediation, consult, facilitation) + SAFETY_PATHWAY; new field court_summary_text = section 8 "Concise Court / Referral Summary", frozen into court_summary as `court_summary` and shown to judges (court-legal-court-summary). PDF has section 8, source labels, safety pathway, disclaimer. Sample + tour updated (8 steps). iteration_58 passed before this change; targeted tests re-run after.
- 2026-09-23: Submission email to the judge now embeds the professional's Concise Court / Referral Summary (when the finalized report is included). BUILD_ID bumped to 2026-09-23.1 — awaiting user Republish. Wingman/admin production credentials still not provided; report sign-off feedback pending.
- 2026-09-23: ReassessmentCompare component (components/ReassessmentCompare.jsx) — previous vs current submission table (ability level, A/B/joint ratings, growth met %, deltas, professional's change note) on judge /court/case/:id and professional statement page. Preview admin password re-synced.
- 2026-09-23: iteration_59 — auth sign-in/forgot/reset verified (9/9). Fixed ReassessmentCompare rating keys (parent_a/parent_b). Login lockout identifier now prefers X-Forwarded-For so brute-force limiting works behind the ingress.
- 2026-09-23: Code review pass 4 applied (see CODE_REVIEW_NOTES.md): sample_fixtures.py breaks sample circular import; legal_report/legal_lens complexity refactors; test token no longer hardcoded.
- 2026-09-23: Frozen submission PDF (Professional Statement part) now includes "Reassessment comparison — previous vs. current submission" table (ability level, A/B/joint ratings, growth met, change, professional's note) when a prior frozen submission exists (`_compare_rows` in court_workflow.py, `_statement_compare` in pdf_report.py). Test added to test_iter59.
- 2026-09-23: Table color scheme unified (web: all report tables use bg-brand-purple/10 header + border-border, incl. ReassessmentCompare, JointReport, CompleteReport, CompareView, report Pages; PDF: all table headers use purple fill 243,238,250). `_legal_kv` label column now sized to the longest label (+4mm) so labels never run into inserted values.

## 2026-09-24 — Professional Alignment Report PDF (Stage 1) + new samples (preview, agent-tested iteration_60)
- PDF Stage 1 done: `pdf_lens.py` (brand header auto on every page via `_JointPDF.brand_header_fn`, cards, score boxes, pathway steps w/ SELECTED, gold Safety Override, Section 7 "Professional Observation & Action Plan" with 90-Day Action Plan + "How We Will Know Things Are Improving" (`success_indicators`, falls back to long_term_goals), Section 8 court card, principle, certification). 8 pages; Parent A+B tables on one page, Joint section on its own page. Static template `/legal-lens-report-to-court-v8.html` rewritten to the same 6-page look. `success_indicators` field added to editor (Section 7) + sample; REPORT_STEPS/Sec 7 title renamed. Pathways kept at 6 (displayed as numbered steps); page count allowed to flow.
- Auth UX: /auth shows persistent inline error (`auth-form-error`) + 8s toast. Production professional login issue reported by user ("page spins / network"); server-side prod API healthy (401 for bad creds, CORS OK). Awaiting user's exact message after republish.
- Co-Parenting Agreement: PDF restyled in `pdf_agreement.py` (brand header, At-a-Glance cards, status badges, section cards, signature cards); `pdf_report.build_agreement_pdf` delegates. Public sample: `sample_agreement.py`, GET /api/joint/sample-agreement[/pdf], page /samples/coparenting-agreement (`SampleAgreement.jsx`), card on /samples.
- Foundation Statement (user's HTML design, option b): `pdf_foundation.py` `build_foundation_pdf` (3 pages, purple banner, teal bullets, 10 sections, signature, footer contact + disclaimer), `sample_foundation.py`, GET /api/joint/sample-foundation-statement[/pdf], page /samples/foundation-statement (`SampleFoundationStatement.jsx`), card on /samples. Note: real Foundation Statements are authored in the sibling parent app; Align only has the sample + builder (imported statements still {title, content}).
- Tests: full suite 333 passed (2 transient 503s during hot reload re-run green); tests/test_iter60_samples_and_pdfs.py 7/7; iter58 headings updated to new section names.
- Pending: user visual sign-off on all three PDFs; Republish (prod still 2026-09-23.1); Stage 2 (apply mockup look to live web editor/sample/court view); prod login diagnosis.
- 2026-09-24: Foundation Statement + Co-Parenting Agreement added to the Sample Reports grid (lib/samples.js entries with `to`/`pdf`/`emailEndpoint`/`tag`; SampleCard honours overrides). Standalone cards removed from Samples.jsx. New POST /api/joint/sample-extra/{foundation-statement|coparenting-agreement}/email. Dashboard "Sample Reports" tool link already routes professionals/parents to /samples.
- 2026-09-24 (later): Foundation Statements in cases — `joint_public` returns `foundation_statements` to the creating professional; GET /api/joint/reports/{rid}/foundation/{a|b}/pdf (creator or that parent) renders imported {title,content} statements with the new Foundation design (`pdf_foundation.build_foundation_pdf` freeform branch); `FoundationStatements.jsx` card on /joint/:id. Web restyle: `ReportHeader` is the white brand header (mark, SA CoParents Align, tagline, pillars); `LensSec` purple heading bars shared by editor + sample; `CourtLegalSummary` blocks color-tinted. BUILD_ID 2026-09-24.1. iteration_61 testing agent run.
- 2026-09-24 (evening): Parent Foundation Statement authoring — `backend/foundation.py` (collection foundation_statements; GET/PUT /api/foundation/mine, GET /api/foundation/mine/pdf, POST /api/joint/reports/{rid}/foundation/share → responses.{side}.foundation=[{title,content,structured}]); professional's per-side PDF renders structured statements in full design. Frontend: /foundation editor (`FoundationEditor.jsx`), parent dashboard `foundation-card`, `ShareFoundation.jsx` on /joint/:id for parents. Generic `SampleTour.jsx` + tours on /samples/coparenting-agreement and /samples/foundation-statement. iteration_62 testing agent run. Production still 2026-09-23.1 — user has not republished.
- 2026-09-24 (night): Professional case creator: "Mediation" assessment option replaced by **Foundation Statement** (subject `foundation`, case code FND, doc.kind="foundation"). Parents on such a case are routed to /foundation?case={rid} (JointAssessment redirect, dashboard button "Write My Foundation Statement"); sharing sets responses.{side} completed + status ready when both shared; /report returns {kind:'foundation', foundation_statements}; joint PDF disabled for this kind (per-parent Foundation PDFs instead). Backend `mediation` subject kept for existing cases/sample.
- 2026-09-25: Co-Parenting Agreement → judges (user's 15-section HTML design). `agreement_model.py` maps agreement case + shared Foundation Statements into 15 sections (empty → "To be discussed"); `pdf_agreement.py` rewritten to purple-banner design (banner/heading/panel/bullets helpers shared from pdf_foundation). Court: SubmitIn.agreement_report_id (explicit, never automatic); `_agreement_pdf_bytes` validates same pro + same parent emails + status ready; frozen packet stores agreement_pdf + agreement_included/agreement_sha256/agreement_card; GET /api/court-dashboard/packets/{pid}/agreement.pdf; professional-statement payload has `agreement_options`. Frontend: ProfessionalStatement checkbox/select (submit-include-agreement, submit-agreement-select), CourtCase `court-agreement-card` + `court-agreement-pdf`. Fix: saving joint responses no longer wipes a previously shared Foundation Statement. Tests: test_iter64_agreement_to_court.py; iter60 sample headings updated.
- 2026-09-25 (cont.): Fixed regression from foundation_statements edit (invitation/pending_invitations had moved under `if role:` in joint_public). Imported freeform Foundation Statements now render in agreement PDF section 1. Tests updated: 21 subjects, new agreement headings. Full suite: 337 passed + all 13 prior failures re-run green. iteration_64 frontend passed. Production still 2026-09-23.1 — awaiting Republish.
- 2026-09-26: Safety gate (a+b+c). `safety_gate.py`: `safety_status(db, emails, pro_id)` flags when a Safety/FV case exists, Legal Lens risk_screening is Moderate-to-High/High, joint_process_appropriate starts "No", or a parent's private Foundation safety screen (fear/threats/control) is Yes. (a) Agreement PDF/judge card switch to **Parallel Parenting** variant (gold Safety Override panel; Sections 4/5/10/11 rewritten: app-only communication, neutral/staggered exchanges, no parent-to-parent step, safety-informed resources). (b) Submit-to-court: `agreement_safety` in professional-statement payload; red warning + confirm before attaching (submit-agreement-safety-warning); judge card shows override (court-agreement-safety-override). (c) Foundation editor 3-question safety screen (foundation-safety-*), stored `safety` on foundation_statements; share requires answers (400) and is blocked with 409 + safety-route note when flagged; case gets responses.{side}.safety_route → professional sees `foundation-safety-route-notice`. Tests: test_iter65_safety_gate.py; iter62/63/64 updated to send safety answers.
- 2026-09-26 (cont.): `WorkflowGuide.jsx` — collapsible numbered "before you start" step guides (persisted per kind in localStorage) on: Legal Lens editor (legal_lens), Professional Report/court submission box (professional_statement), case creator (case_create / agreement_create), Foundation editor (foundation). Judges: GET /api/court-dashboard/packets/{pid}/parallel-plan.pdf — one-page Parallel Parenting Order Summary (`pdf_parallel_plan.py`) only when the agreement card has safety_override (404 otherwise); gold button `court-parallel-plan-pdf` on CourtCase agreement card. Tests in test_iter65_safety_gate.py (3 pass).
- 2026-09-26 (late): Judge guide (`WorkflowGuide kind="judge"`, 6 steps) on /court-dashboard. Safety Case Auto-Start: POST /api/joint/reports/{rid}/safety-case (creator only) clones parents/child into a professional-mediated Safety + Risk + Safe Communication + Safeguards case, stores `safety_case_id` on the source case; `safety-case-start-btn` / `safety-case-open-link` inside the foundation safety-route notice. BUILD_ID 2026-09-26.1. Production observed at 2026-09-24.1 (user republished the 09-24 work; 09-25/26 work still needs a republish). Live sample PDFs 200.

## 2026-09-26 — AI & storage integrations (iteration_66: frontend 10/10, backend 7+3 new tests; full suite 361 green)
- **Claude Sonnet 4.6** (Emergent key): third selectable drafting model in the Professional Alignment Report (`legal_ai.MODELS`, `lens_data.AI_MODELS`; Gemini stays default) + `POST /api/cases/{rid}/parallel-summary-draft` "Parallel Parenting summary helper" (Section 7, review-gated, insert into Professional statement).
- **Jev (typesafe-sdk, `backend/jev.py`)**, all advisory: `POST .../professional-report/neutrality-check` (flags custody/diagnosis/credibility/legal-conclusion sentences; threshold 1−P(none) ≥ 0.6), `POST .../professional-report/child-focus-suggest` (accept/reject chips, Section 4), `POST /api/foundation/mine/blame-check` (parent concern-line nudge before save; "Save anyway" allowed), court-message `triage` {procedural|scheduling|urgent_safety} stored on each message + red badge in CourtThread, Foundation `safety_language` score on save (level high → extra reason in `safety_gate.safety_status`).
- **Object storage (`backend/storage.py`)**: parent attachments `POST/GET/DELETE /api/foundation/mine/attachments` (PDF/JPG/PNG/WebP, 10 MB, max 10, soft-delete), professional list `GET /api/joint/reports/{rid}/attachments` (only parents who shared a Foundation Statement into the case), `GET /api/files/{fid}?case=` owner or assigned pro. TTS audio also cached there.
- **Perplexity (`backend/research.py`)**: `GET /api/research/config`, `POST /api/research/ask`, `POST /api/research/local-resources` {category} using professional `profile.zip` (`PUT /api/me/profile/zip`; ZIP added to RegisterIn + Auth form). **NOT CONFIGURED** — `PERPLEXITY_API_KEY` empty in backend/.env → UI shows "not configured" notice; user must supply key (console.perplexity.ai) and set it in prod env too.
- **OpenAI TTS tts-1 voice "sage" (`backend/tts.py`)**: `POST /api/tts` (public, ≤4000 chars, sha-cached in db.tts_cache + object storage) → `GET /api/tts/{key}.mp3`. `ListenButton.jsx` on every WorkflowGuide, Foundation step headings, sample Legal Lens page.
- User artwork placed: `/alignment-report-preview.jpg` (sample Legal Lens page details), `/joint-report-poster.jpg` (/samples header), `/assessment-badges.png` (saved, not yet used). Image generation declined (no fitting use case); user mentioned other co-parenting scene images (graduation/school/doctor/certificate) that are NOT in this project — need re-upload.
- Frontend: `components/LensAiTools.jsx`, `ListenButton.jsx`, `FoundationAttachments.jsx` (+ CaseAttachments on JointReport for creators).
- Backlog: PERPLEXITY_API_KEY; TTS voice choice; chunked upload if >10 MB needed; judge-facing triage filter; add `assessment-badges.png` to CircleNav.
- 2026-09-26 (later) — **Directory Fast-Add**: `/research/local-resources` now asks Sonar to append `PROVIDERS_JSON` (parsed by `research._split_providers` → `providers[]` cards in ResearchPanel); `POST /api/research/providers/add` (admin-only, 409 on duplicate name, specialty from category, source="perplexity") → "Add to directory" button for admins; professionals get "Add to report" per provider. Tests: tests/test_iter67_provider_fast_add.py (3 pass). Still blocked on PERPLEXITY_API_KEY (user skipped) and scene-image re-upload (not in project).
- 2026-09-26 (later) — **Research Base (Perplexity Sonar) in Professional Alignment Report**: `research.research_insight(rep, user)` builds a context question (joint rating, ticked child-focus issues, chosen pathways, professional ZIP) → stored on `professional_reports.research_base` {text, citations[], model, zip, fetched_at}. Fetched automatically on `ai-draft` (non-fatal) and via `POST/DELETE /api/cases/{rid}/professional-report/research-insight` (503 when unconfigured; report generation never blocked). UI: `ResearchBase` aside in Section 5 (fetch/refresh/remove). PDF: teal "RESEARCH BASE" footer card under Section 5 with numbered sources (`pdf_lens._research_base`). Tests: tests/test_iter68_research_base.py (5 pass). `PERPLEXITY_API_KEY=` present but EMPTY in backend/.env — user sets real value in production env.
- 2026-09-26 (final) — **Perplexity LIVE in preview**: key set in backend/.env. Perplexity retired `/v1/sonar` (403 "migrate to Agent API"); `research._sonar_call` now uses **Agent API `POST https://api.perplexity.ai/v1/agent`** with `preset: "fast"`, `instructions`, `input`; sources parsed from the `search_results` output item, text from the `message` item (`_parse_agent_output`). Verified live: ZIP 78205 supervised-exchange → Guardian House + KidShare with phones, 10 citations; Research Base fetched + rendered in PDF; admin fast-add created "KidShare (Family Service Association)" in the directory. **User must set PERPLEXITY_API_KEY in production env before republish.**
- 2026-09-26 (iter 69) — (1) **Sample Research Base footer**: fictional `research_base` in `sample_legal_lens._REPORT` → aside on /samples/legal-lens-report (`sample-lens-research-base`) + sample PDF. (2) **Court Summary Sources**: `SubmitIn.include_research_sources` (only honoured with `include_legal_report`); `_legal_pdf_bytes(db, doc, include_sources)` adds `legal_summary.research_sources` {citations, note}; `professional-statement` payload exposes `legal_lens.has_research_base`; checkbox `submit-include-sources` in ProfessionalStatement.jsx; judge sees "Research Base — Sources" block (`court-legal-research-sources`) in CourtLegalSummary. Default OFF (explicit-inclusion rule). (3) **Provider Freshness Check** (admin): `POST /api/research/providers/{pid}/verify` (Perplexity lookup → checks.phone/website match|differs|not found, stored as `verification`/`last_verified_at`), `POST .../apply-verification` copies differing found values; AdminProviders.jsx refresh button + result panel + "Apply found values". Tests: tests/test_iter69_research_court_sources.py (3 pass, live). Scene images still NOT provided by user (not in job assets).
- 2026-09-26 (iter 70) — **Stale Provider Alerts** (AdminProviders.jsx: amber "never checked"/"stale check" badge when `last_verified_at` >90 days or missing; "Check all stale (n)" runs sequential freshness checks). **Judge Urgent Filter**: `GET /api/court-dashboard/urgent-messages` (professional messages triaged urgent_safety with no later Court reply) → red `judge-urgent-list` panel atop the Judicial Portal with "Open case thread"; test tests/test_iter70_urgent_list.py (1 pass). **Badge Artwork**: user's badge PNG split into `/badge-uniform.png` + `/badge-safety.png`; CircleNav `MainBadge img` prop renders artwork circles on /hub (pill below the circle so tagline stays visible); agreement badge stays CSS (no artwork supplied).
- 2026-09-26 (iter 71) — **Agreement badge artwork**: generated with Gemini Nano Banana (gemini-3.1-flash-image-preview, style-matched to user's uniform badge; script memory/gen_badge_agreement.py) → `/badge-agreement.png`; all three hub circles now use artwork. **Weekly provider freshness**: platform cap is 5 crons (already used) → folded into existing Monday 8am Central `weekly-summary` cron: `research.run_provider_freshness` re-verifies active providers stale >90 days via `verify_provider_record` (shared with the admin button) and emails admins (ADMIN_EMAIL + role=admin users) ONLY when a found phone/website differs (or a lookup failed); nothing auto-applied. Verified: direct run → 4 checked, emails composed to 2 admins; cron endpoint 200 with secret / 401 without.
- 2026-09-26 (iter 72) — **Urgent Email Alert**: `Threads.notify` sends an immediate "URGENT — safety concern raised - Cause No. …" email (red banner, kind `court_urgent_safety`) to the judge when a professional message is Jev-triaged urgent_safety; message stores `urgent_alert_sent_at` (shown as "judge emailed immediately" in CourtThread). Standard messages keep the normal notice. Test tests/test_iter72_urgent_email.py. **Parent Listen Mode**: "Read my statement aloud" panel (TTS over all filled Foundation sections, `foundation-listen-all`) above the Save button on /foundation; mobile-checked, no overflow.
- 2026-09-26 (iter 73) — **Moments that matter strip** on landing (`components/MomentsStrip.jsx`, `moments-section`, 4 cards: school, doctor, graduation, certificate) using Nano Banana-generated flat-vector scenes (`/moment-*.jpg`, script memory/gen_scene_images.py) because the user's original photos were never attached to this project. **Statement Voice Choice**: ListenButton accepts `voice` + `rate` (playbackRate); Foundation listen panel has Voice (Calm/Warm/Bright/Steady = sage/coral/nova/echo) and Speed (0.8/1/1.2×) selects persisted in localStorage (`foundation-voice-select`, `foundation-speed-select`), applied to all per-step Listen buttons too.
- 2026-09-26: doctor scene regenerated (parents together on the right, doctor on the left; memory/gen_doctor_v2.py)
- 2026-09-26: doctor scene v3 — father far left, doctor + child centre, mother far right (user-specified composition)
- 2026-09-26 (iter 74) — **Freshness History**: every verify (admin button, check-all, weekly cron) inserts `db.provider_checks` {provider_id, checked_at, by (user|system), checks, changed[], not_found[], applied_at, applied{}, applied_by}; apply-verification stamps the matching record. `GET /api/research/providers/{pid}/history` (admin) returns rows with by_name/applied_by_name ("Weekly cron" for system). UI: History button per provider → `ProviderHistory.jsx` table (Checked / By / Result / Applied). Tests tests/test_iter74_provider_history.py (2 pass).
- 2026-09-26 (iter 75) — **Directory Export**: GET /api/admin/providers/export.csv (admin; BOM+CSV: Name, Degrees, Specialty, Organization, Phone, Email, Website, Lists, Active, Last checked, Last check result, Contact change applied, Source); 'Export CSV' button in AdminProviders header (provider-export-csv-btn). Tests tests/test_iter75_provider_export.py (2 pass).
- 2026-09-26 (iter 76) — **Urgent SMS Option (Twilio, NOT CONFIGURED)**: `backend/sms.py` (twilio SDK, env TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER — all EMPTY in .env, user must supply). Judge settings `GET/PUT /api/court-dashboard/alert-settings` {mobile (E.164-normalised), sms_urgent_alerts}, `POST .../test-sms` (503 when unconfigured). `Threads._urgent_sms` texts the judge (cause no. + portal link only) alongside the urgent email; message stores `urgent_sms_sent_at` ("judge emailed + texted immediately" in thread). UI `UrgentSmsSettings.jsx` on Judicial Portal. Tests tests/test_iter76_urgent_sms.py (2 pass).
- 2026-09-26 (iter 77) — **Court Directory Page**: GET /api/court-dashboard/providers (approved court role only; active providers, public fields + organization/phone/email/website + last_verified_at + contact_verified; no verification internals) → CourtDirectory.jsx card on Judicial Portal (Browse toggle, search, grouped by specialty, verified/checked/not-yet badge, non-endorsement note). Test tests/test_iter77_court_directory.py.
- 2026-09-26 (iter 78) — **Invite Professional tab (admin)**: admin dashboard sections → shadcn Tabs (Invite Professional · Pending Credentials · Approved Professionals · Judges · Provider Directory). `backend/pro_invites.py`: POST/GET /admin/pro-invites, POST /admin/pro-invites/{id}/resend, public GET /auth/pro-invite/{token} (prefill name/email/zip/profession + CREDENTIAL_TYPES), `consume_invite` in register (RegisterIn.pro_invite, profile.credential_type; zip inherited from invite), POST /admin/professionals/{uid}/request-credentials (email), POST/GET /me/credentials (object storage `credentials/{uid}`), GET /admin/professionals/{uid}/credentials, GET /credential-files/{fid} (owner|admin), POST /admin/accept-professional/{uid} (approve + credentials_verified + email; invite→accepted). UI: InviteProfessional.jsx, PendingCredentialActions.jsx (in pending list), CredentialUpload.jsx (professional dashboard, #credentials), Auth.jsx `pi` prefill + credential-type-select, AdminProfessionals ZIP filter (admin-professionals-zip). Test tests/test_iter78_pro_invites.py (1 pass, full flow).
- 2026-09-26 (code review fixes) — test fixture passwords now env/random (`TEST_FIXTURE_PASSWORD` or random) in tests/_iter64/_iter65_ui_setup.py; dynamic `__import__` removed; unused var removed (legal_ai). Circular imports broken: new `pdf_common.py` (fonts/colours/_s/_new_pdf/_JointPDF) imported by pdf_agreement/pdf_foundation/pdf_parallel_plan; pdf_report imports pdf_agreement one-way (re-exports build_agreement_pdf); `consume_invite` moved into auth.py as `_consume_pro_invite` (pro_invites no longer imported by auth). Complexity: ai_tools.build_router → `_jev_routes` + `_attachment_routes`; foundation share logic → `_share_updates`; court_messages `_alert_routes` split from `_judge_routes` with module-level MobileIn/_alert_view. Deferred (business-critical, left unchanged): agreement_model._base_model, court_workflow._statement_payload/_submit_routes/submit_to_court. Full suite 373 passed.
- 2026-09-26 (court refactor pass) — `agreement_model._base_model` → `_identity/_needs/_practical/_conflict_and_commitments/_appendix` (same 32 keys, verified against sample doc). `court_workflow._statement_payload` → `_statement_block/_lens_block/_library_block/_findings_block/_court_block`; `submit_to_court` → `_build_bundle` (PDFs + merged packet) / `_build_submission` (hash-sealed Submission record) / `_log_submission` / `_notify_court`. LESSON: first attempt named the builder `_submission_record`, colliding with the existing helper of that name → 500 on every submission (caught by full regression; renamed). Full suite before 373 green, after 373 green.


## 2026-06 — Nearby Professional Picker (judge referral)
- `GET /api/court-dashboard/professionals?zip=` ranks approved professionals: exact ZIP (`match: nearby`) → same 3-digit area (`same_area`) → others; rows include zip/city/state.
- Referral form has a "Parties' ZIP" input (stored as `parties_zip` on the referral, echoed in referral_public). Badges: Nearby / Same area; "Location not listed" for pros without ZIP/city. Judge may still pick anyone.
- Tests: `tests/test_iter79_nearby_pros.py`; full suite 385 passed / 1 skipped.

- 2026-06 follow-up: radius matching (`?radius=` miles, offline `zipcodes` centroids via `backend/geo.py`, badge `within_radius` + `distance_miles`), `ProZipPrompt.jsx` on professional dashboard when `profile.zip` empty (PUT /me/profile/zip), hearing-date label wraps on mobile. Full suite 385 passed / 1 skipped.

## 2026-06 — Public "Find a Professional" listing (opt-in)
- `backend/public_listing.py`: `GET/PUT /api/me/public-listing` (approved professionals only; bio/phone/website/zip; listed toggle), `GET /api/public/professionals?zip=&q=` (no auth; only `public_listing.listed=true`; distance sort; no email exposed; non-endorsement note).
- Dashboard `PublicListingCard.jsx`: one-tap "List me on sacoparentsalign.com", edit details, un-list. Public page `/find-a-professional` (`FindProfessional.jsx`) + landing nav link.
- Tests: `tests/test_iter80_public_listing.py`; full suite 386 passed / 1 skipped.
- 2026-06 follow-up: `ListedProsTeaser.jsx` on landing (first 3 listed pros + Find a Professional button; hidden when none listed); shared `PublicProCard.jsx`; live "Preview — how your public card will look" inside `PublicListingCard.jsx` edit panel. Frontend-only; verified by screenshot.
- OPEN: user asked for Joint Report to be based on "old Gemini code we had provided" — no such spec exists in /app; awaiting user paste. Joint Report remains rule-based (`joint_engine.py`).

## 2026-06 — Gemini Joint Report (review-gated) + listing admin + referral distance + share link
- `backend/joint_ai.py`: Gemini 3.1 Pro (Emergent key, LlmChat) drafts narrative fields (alignment_statements, differences, child_needs, alignment_paragraph, conversation, questions, next_steps) from both parents' answers. Stored on case as `ai_joint_draft {status draft|approved, fields, model, reviewed_*}`. Endpoints (creator only): GET/POST/PUT `/api/joint/reports/{rid}/ai-joint-draft`, POST `.../approve`, `.../discard`. `effective_joint_report()` overlays approved fields (adds `ai_assisted`, `ai_model`, `ai_reviewed_by`) and now backs all joint-report consumers (screen, PDF, session prep, court view/packet, Legal Lens prefill). Rule-based engine remains default/fallback. UI: `JointAiDraft.jsx` on /joint/:id for creators; badge on published report.
- Admin "Public Listings" tab (`AdminListings.jsx`): GET `/api/admin/public-listings`, POST `/api/admin/public-listings/{id}/hide {hidden, reason}`; hidden listings excluded from public directory; professional sees hidden notice.
- Referral stores `professional_zip` + `professional_distance_miles`; shown in judge Case Overview and referral email.
- Share link: GET `/api/public/professionals/{id}`, route `/find-a-professional/:proId`, "Copy share link" button.
- Tests: `tests/test_iter81_ai_joint_listing_admin.py`; full suite 389 passed / 1 skipped (one transient reload 503 rerun green).
- 2026-06 Gemini spec swap: user pasted the "SACO ParentAlign Professional Evaluation Report" HTML spec. `joint_ai.SYSTEM` now has PART A (joint report fields) + PART B (professional evaluation: safety_status, parent_a/b_profile {strengths,gaps}, scale {parent_a,parent_b,joint,mode,rationale} on the spec's 5-band 1–10 matrix, short_term_goals, long_term_goals, resources from provider directory only). Approved evaluation is exposed as `professional_evaluation` to the case professional only (stripped for parents; court view never includes it). UI: `EvaluationEditor.jsx` (editable in draft panel, read-only after approval).
- 2026-06 Evaluation PDF: `backend/pdf_evaluation.py` `build_evaluation_pdf(ev, meta)` mirrors the HTML card (navy/teal header, meta block, amber safety callout, two profile cards, 5-band matrix with highlighted joint band + A/B/Joint placement, roadmap, resource table). `GET /api/joint/reports/{rid}/evaluation.pdf` (case professional only, requires approved draft; access event logged). UI: "Evaluation Report PDF" button in the approved Professional Evaluation section on /joint/:id.

## 2026-06 — REVERTED Gemini "Professional Evaluation" (user hated it) + Professional Alignment Report restyle
- Removed: PART B evaluation prompt, `pdf_evaluation.py`, `EvaluationEditor.jsx`, `JointAiDraft.jsx` panel (backend PART A joint-draft endpoints remain but have no UI), evaluation.pdf endpoint, lens prefill bridge, court `include_evaluation` checkbox (all uncommitted work discarded via git checkout).
- Professional Alignment Report PDF (`pdf_lens.py`) restyled to the user's mockup ("always like this"): gradient title band, numbered circle sections 1–11 (Case & Assessment Overview, Alignment Snapshot + Safety Screening, Parent A Perspective, Parent B Perspective, Joint Co-Parenting Assessment, Child-Focused Legal Issues (table), Options & Resources, Conflict Resolution Pathways, Legal Conflict & Agreement-Building Analysis, Professional Legal Statement & Roadmap, Concise Court Summary), solid purple/blue/teal score cards, Successes/Challenges/Growth cards per parent. Tests iter58/iter60 heading strings updated.
- Dashboard CasesTable: "Professional Report →" link per ready case (`case-row-pro-report-{id}`).
- DO NOT reintroduce the 5-section "SACO ParentAlign Professional Evaluation" HTML format.

## 2026-06 — Invitation email diagnostics
- Preview verified end-to-end: Resend custom-domain sender (sacoparentsalign.com) accepts sends (200) and admin invite path returns email_sent=true. Production failure ("not verified") is deployment-env specific.
- Added `POST /api/admin/email-health` (sends test email to the admin, reports Resend vs default sender, status/error, hints) + "Run email health check" panel in Admin → Invite Professional. Invite response now includes `email_error`; UI shows the real reason.
- Preview admin login with seeded ADMIN_PASSWORD returns 401 (user changed password / seed doesn't overwrite) — noted, not changed.
- 2026-06 Invite retry + sender badge: invites persist `email_sent/email_error/last_email_at`; `POST /admin/pro-invites/{id}/resend` returns `{ok, retry, email_sent, email_error}` (retry = original invite subject when the first send failed); red "Email failed" chip + "Retry send" button per invite. `GET /api/admin/email-status` (no send; config + last outcome + failed count → green/amber/red) powers `SenderStatusBadge.jsx` above the admin tabs. Verified via API in preview (green→red→retry→green).

## 2026-06 — Report walk-through + invite open tracking + undelivered digest
- `backend/lens_walkthrough.py` (11 sections: what/how/guardrail). `GET /api/cases/{rid}/professional-report/walkthrough` (own case). Editor: `LensWalkthrough.jsx` — overview with progress (fields per PDF section) + per-section "How to complete this section" (editor's 8 sections map to PDF sections 1–11). PDF: "How to Read This Report" page after the title band (`how_to_read_page` in pdf_lens.py).
- Invites: `first_opened_at` / `open_count` set when `/auth/pro-invite/{token}` is fetched (also flips email_sent true); shown in admin list ("Link opened …").
- `run_undelivered_invite_digest()` in cron_jobs.py, triggered by the daily `expiry-digest` cron: emails admins about invites with email_sent=false, unopened, >24h old.
- Tests: `tests/test_iter82_walkthrough_invites.py`.

## 2026-06 — Editor 1–11 match, guided step mode, judge reader guide, court packet preview
- `LegalLensReport.jsx`: sections array S(1..11) mirroring the PDF (Case; Alignment Snapshot & Safety [ratings + safety block]; Parent A; Parent B; Joint; Child-Focused Legal Issues; Options & Resources; Conflict Resolution Pathways; Legal Conflict & Agreement-Building [new text fields agreement_building_opportunities / issues_requiring_attention / existing_agreements / procedural_considerations added to lens_data.TEXT_FIELDS]; Professional Legal Statement & Roadmap; Concise Court Summary). `REPORT_STEPS` now 11. Guided step mode: `lens-step-mode-toggle`, one section at a time, sticky Back / Save & Next / progress bar.
- Judge: `GET /api/court-dashboard/report-guide` + `JudgeReportGuide.jsx` card in Judicial Portal case view.
- Court packet preview: `POST /api/joint/reports/{rid}/court-packet-preview` (same options as submit; returns merged PDF inline, header X-Packet-Preview, nothing persisted) + "Preview exact court packet (PDF)" button/iframe in ProfessionalStatement submit box.
- Tests: `tests/test_iter83_editor_guide_preview.py`.
- LESSON (repeat of ledger #7): never insert a route between an existing decorator and its handler — it silently rebinds the route (`/court-dashboard/professionals` briefly served the report guide). Insert new routes *before* the decorator line.

## 2026-06 — Sample page 1–11 + judge section jump
- `SampleLegalLensReport.jsx` restructured to the 11 numbered sections (new testids sample-lens-s2 = snapshot, s3 = Parent A, s4b = Parent B, s9-legal); `SampleLensTour.jsx` steps rewritten (11). `sample_legal_lens.py` gained section-9 fields.
- Judge: `GET /api/court-dashboard/packets/{pid}/legal-report-sections` → {pages: {n: page}, total_pages} by scanning the frozen PDF text after the "How to Read" page; `legal-report.pdf?inline=1` serves inline so `#page=N` works. `JudgeReportGuide` accepts `packetId` and renders p.N links; also embedded in `CourtCase.jsx` under the attached Professional Report block.
- Tests: extended `test_legal_report.py`.

## 2026-06 — Report §6/§7 table restyle
- Professional Report §6 Child-Focused Legal Issues and §7 Options & Resources tables now use light-tinted headers (teal/blue) with white rows across PDF, editor and sample page.
- Root cause of the solid-purple rows: fpdf2 tables inherit the current fill colour left by the heading badge; `_lens_table` (pdf_report.py) now resets fill to white and accepts `header=(fill, text)`.

## 2026-06 — Section colour pass + invite delivery test
- Report sections 1–11 tinted per SECTION_COLORS (pdf_lens.py) / SECTION_TINT (LensSections.jsx): 1 slate, 2–3 purple, 4 blue, 5–6 teal, 7 blue, 8 green, 9 orange, 10 blue, 11 gold. Applied to PDF heading badge/hairline, editor and sample page.
- Circular import removed: build_legal_lens_pdf + AI appendix now live in pdf_lens.py; importers (legal_lens, server, court_workflow, tests) updated.
- Preview invite delivery test: Email Health Check green (Resend 200 via noreply@sacoparentsalign.com); invite bc0e82eb sent to mattsossi+invite@bsossi.com, email_sent=true. Inbox receipt + first-open tracking pending owner confirmation. Admin password temporarily reset (see test_credentials.md).

## 2026-06 — Professional Dashboard restructure + Align Assistant
- /dashboard (pro/admin): ProTopNav (Case Lookup, Active Cases (n), + New Case), ProHero tagline + 3 CTA cards (Invite Parents, Review Joint Report, Create Prof. Report), PipelineStepper (5 steps for selected case, GET /api/assistant/case-brief/{id}). Old PrimaryTiles/SecondaryTools moved into More tools.
- Align Assistant (backend/assistant.py, frontend AlignAssistant.jsx): Gemini 3 Flash (gemini-3-flash-preview) via EMERGENT_LLM_KEY, SSE streaming POST /api/assistant/chat, history in db.assistant_messages per session_id, suggestion chips (invite/review/pathway/report) triggered by CTA hover/click. Advisory-only system prompt: no custody/credibility/diagnosis/legal conclusions, email-only invites, never files.
- Tested: iteration_68 all pass (backend + frontend).

## 2026-06 — Professional Report cover page (Page 1 Professional Contact)
- New PDF page 1 (pdf_lens.cover_page): title band, Professional Information (name/email/phone/office address from the professional profile via legal_lens.professional_contact; blank lines when missing), Purpose cards, ALIGN→FOCUS→RESOLVE→AGREE. Then How to Read, then sections 1–11 as before.
- ReportCover.jsx shown on the report editor (/cases/:id/professional-report) and sample page. Tests updated (Alignment Report title; fake db users).
- Invite test: mattsossi+invite@bsossi.com sent, not yet opened (first_opened_at null) — awaiting owner confirmation.

## 2026-06 — Profile contact fields + cover images
- backend/pro_profile.py: PUT /api/me/profile/contact (phone, organization, address, city, state, zip); POST/DELETE/GET /api/me/profile/image/{headshot|firm_logo} via Emergent Object Storage (≤2 MB jpg/png/webp), refs stored at users.profile.images.
- Cover: profile values auto-fill; per-report override fields cover_name/email/phone/address (TEXT_FIELDS) in the editor under the cover; images printed top-right of PDF cover (pdf_lens._cover_images) and shown on-screen.
- Dashboard: ProContactCard (Report Cover Contact) with edit form + image slots.

## 2026-06 — Signature image
- Third profile image slot `signature` (pro_profile SLOTS, ProContactCard). pdf_lens._signature_image prints it above the certification block only when report status is final/submitted_to_court. Auth.jsx sibling-app link moved to REACT_APP_SACOPARENTS_APP_URL (frontend/.env).

## 2026-06 — Signature on court packet
- pdf_report._signature_block prints the uploaded signature image + rule + name/role/attested date under PROFESSIONAL ATTESTATION on the court-packet cover letter; court_packets.pro_profile passes signature_path. Falls back to blank rule when no image.

## 2026-06 — Judge welcome chat box
- JudgeWelcomeChat.jsx shown on /auth when Judge/court staff is selected (or ?court=1): welcome message + "Enter Your Judges Portal" button that switches to court-account registration and focuses the name field.

## 2026-06 — Professional welcome chat + prod smoke check
- JudgeWelcomeChat now takes kind=judge|professional; professional copy shows on Create-account when Family professional is selected; judge copy on login+register when court selected.
- Live smoke (read-only): sacoparentsalign.com serves the new bundle (pro-hero, pipeline-stepper, assistant, sample cover) and /api/health healthy; sample PDF 200. Judge chat bundle not yet live (built after republish). Invite to mattsossi+invite@bsossi.com still unopened.

## 2026-06 — Judge first-review tour
- JUDGE_TOUR (SampleTour.jsx) auto-opens once per judge (localStorage judge-tour-{uid}) on /court-dashboard when approved; 5 steps (workflow guide, refer case, case list, packets heading, directory/alerts); restart via header judge-tour-start-btn. Republish requested via deployer.

## 2026-06 — Pro tour + parent welcome chat
- PRO_TOUR (SampleTour.jsx) auto-opens once per professional on /dashboard (localStorage pro-tour-{uid}); restart via pro-tour-start-btn. Steps: CTA bar, pipeline, contact card, assistant, cases.
- JudgeWelcomeChat kind=parent on Join.jsx invitation card (only when invite is not redirected to the sibling parent app) and on /auth when next=/join/... (parent flow).

## 2026-06 — Warmth touches
- JudgeWelcomeChat: personalized greeting "Welcome back, Judge {first}!" when session user present (name prop; strips Judge/Hon. titles); secondary "Take a 1-Minute Portal Tour" button (onTour). Shown on /auth (navigates to /court-dashboard?tour=1 or /dashboard?tour=1) and on Court Dashboard (dismissible, localStorage judge-greet-{uid}). ?tour=1 starts the tour on both dashboards.

## 2026-06 — Assistant draft insert
- System prompt asks Gemini to wrap report drafts in [[DRAFT section=key]]…[[/DRAFT]] (keys = DRAFT_SECTIONS in assistant.py). GET /api/assistant/draft-sections; POST /api/assistant/insert-draft {case_id, field, text} writes the field + ai_drafts[field] (model "Align Assistant (…)") via LensStore and logs LEGAL_LENS_AI_DRAFT. Admins may access any case brief.
- AlignAssistant.jsx renders DraftCard per marker block with "Insert into Professional Report for review" → link to editor #field.
- NOTE: preview admin mattsossi@bsossi.com password changed again by owner (AlignTemp2026! no longer valid); use qa.admin.preview@bsossi.com for tests.

## 2026-06 — Draft badge, hearing note, assistant on report page
- LegalLensReport: Field wrapper shows "AI draft — needs your review" badge (yellow ring) while a field equals its ai_drafts text and has no accepted_at; Accept → POST /api/assistant/accept-draft sets ai_drafts[field].accepted_at (logged). Editing clears the badge naturally.
- AlignAssistant embedded on the report editor (caseId=id, onInserted reloads report).
- CourtDashboard greeting shows next upcoming hearing note (days until, date, cause no.).

## 2026-06 — PDF readiness check (iteration_69)
- Full flow verified by testing agent: create case → both parents complete → Joint Report on screen + PDF (200, multi-page) → Professional Report editor → finalize → PDF with cover, 11 sections, certification, no DRAFT. Pre-completion: joint report 400 with clear message; professional report PDF available with DRAFT watermark. Dashboard pipeline reflects readiness. New regression test tests/test_iter69_prof_report_pdf_readiness.py.

## 2026-06 — Both-complete email + ZIP bundle
- server._notify_both_complete: when the second parent submits (status→ready), emails the case professional (professional_id or created_by) with links to /joint/{id} and /cases/{id}/professional-report; idempotent via joint_reports.both_complete_notified_at; skipped for demo cases.
- GET /api/cases/{rid}/professional-report/bundle.zip → ZIP with {code}-joint-report.pdf + {code}-professional-report.pdf (400 before both complete); "Download Both (ZIP)" button on the report editor (lens-bundle-btn). Tests: tests/test_iter85_bundle_notify.py (3 pass; run with REACT_APP_BACKEND_URL exported).

## 2026-06 — 3-minute demo video
- scripts/build_demo_video.py assembles /app/frontend/public/demo/sacoparentsalign-demo.mp4 (1280x720, 2:50, ~3.9 MB, captions burned via PIL, xfade via imageio-ffmpeg static ffmpeg — no drawtext filter in that build). Scenes: landing, judge welcome/portal/refer, pro dashboard/pipeline/invite, Joint Report, Professional Report editor + 2 PDF spreads (cover+guide, §6/7+certification), Align Assistant, finalize, court packets. Source frames were screenshot_tool outputs under /root/.emergent/automation_output.
- Landing: DemoVideoButton ("Watch the 3-minute demo") opens modal with player + Download MP4.

## 2026-06 — Demo read-along
- frontend/public/demo/captions.json (15 timed captions generated from build_demo_video SCENES). DemoVideoButton modal now has a Read-along panel (highlights current line on timeupdate; click to seek).

## 2026-06 — Safety sample reframed as self-assessment
- Sample card + API: "Safety / Family Violence" is described as a professional-mediated self-assessment (not a Joint Assessment); title "Sample Safety-Focused Self-Assessment Report (Controlled Preview)"; SampleReport condensed note swaps to safety wording when is_safety.

## 2026-06 — Code review pass
- assistant.case_brief split into _participants/_alignment_buckets/_state/_tick/_pathway_names/_steps (complexity 47→small helpers), behaviour unchanged (tests pass). ruff F821/F841/F811 clean. `is None/True/False` in tests is correct Python — left as is. Large court/foundation router refactors intentionally skipped (risk, no user-visible benefit).

## 2026-06 — Instagram cuts
- scripts/build_demo_instagram.py → frontend/public/demo/sacoparentsalign-demo-reels-9x16.mp4 (1080x1920) and -square-1x1.mp4 (1080x1080), ~82 s, 8 highlight scenes, big captions. Source frames: /tmp/demo (restore from /root/.emergent/automation_output/20260929_2230*/ if wiped; PDF spreads re-cut from main demo at 118s/129s).

## 2026-06 — Family-violence screening import surfaced
- backend/safety_import.py: extract_safety_screening(payload) finds a safety/FV assessment in the sacoparentsapp.online export (by title/question keywords, or structured family_violence_assessment/safety_screening if ever added) → {source,title,completed_at,items[{question,answer,concern}],item_count,concern_count}. Stored at joint_reports.responses.{role}.safety_screening (+safety_route when concerns) on /joint/reports/{rid}/import.
- legal_lens: readiness fv_a/fv_b done when screening imported → fv_*_received prefilled "Received"; _lens_view exposes safety_screening{a,b}. PDF §2 prints only a neutral receipt line (source, date, counts, "not findings") — never answer text. Editor §2 ImportedScreening.jsx shows the professional the items (collapsed) with concern highlighting. Tests: tests/test_iter86_safety_import.py.


## 2026-06 Code review (read-only, safety-import scope) — findings only, no fixes applied
- MEDIUM: `safety_import.py:47` / `ImportedScreening.jsx:8` assume `completed_at` is a string; non-string value from bridge would 500 PDF export and crash Section 2 UI. Fix: coerce to str at extraction + guard in UI.
- LOW: `ImportedScreening.jsx:12` `scr.items` without fallback; `build_demo_instagram.py` lacks mkdir/asset checks/nonzero exit; ruff lint nits.
- Open question: when one parent imports a screening on a non-safety case, other parent flips from "Not Applicable" to "Not Received" (`legal_lens.py:79-83`). Section 2 PDF uses stored snapshot vs Section 1 live readiness — can disagree.
- Verified OK: privacy gating, non-adjudicative wording, idempotent import, tz-aware datetimes, no ObjectId leaks.

## 2026-06 Fixes from code review (agent-tested: test_iter86 6 passed; related suites 15 passed)
- `safety_import._date()` coerces any bridge `completed_at` (str/epoch/datetime/dict/None) to safe YYYY-MM-DD; `screening_summary` uses `.get()` throughout → PDF/bundle never 500 on malformed dates.
- `ImportedScreening.jsx` guards non-string `completed_at` and missing `items`.
- Readiness: new `not_required` flag; `_prefill_header` sets "Not Required" (not "Not Received") for the other parent when only one screening is imported on a non-safety-subject case. RECEIPT options now include "Not Required". Flows through editor radios, PDF Section 2, court summary.
- Not yet redeployed — awaiting user go-ahead.

## 2026-10-06 Six-Questions framing + source labels + landing simplification (agent-tested, NOT deployed)
- `lens_walkthrough.py`: SIX_QUESTIONS, QUESTION_OF_SECTION, SOURCE_OF_SECTION, SOURCE_LEGEND, DISTINCTIONS, WORKFLOW. Walkthrough + judge report-guide endpoints expose question/source/legend/distinctions.
- Report editor + sample report: `ReportFraming.jsx` (SixQuestions, SourceLegend, Distinctions, StatementDivider); every LensSec shows question subtitle + SourceTag; green divider before §9.
- PDF: How-to-Read page has six questions, legend, four distinctions; headings print question + SOURCE; `statement_band()` before §9; `_ai_tag()` marks AI-drafted fields inline.
- Landing: hero mantra, 5-step INVITE→ASSESS→ALIGN→REVIEW→RESPOND, Four distinctions block, long journey + 8 court steps collapsed in <details>. Judge guide shows six questions/legend/distinctions.

## 2026-10-06 Private safety screenings Version A (women) / Version B (men) (agent-tested 16/16 E2E + 15 unit, NOT deployed)
- `backend/safety_screening.py`: VERSIONS, tiers (design guide), gender→version default, routes GET/PUT /joint/reports/{rid}/safety-screening, PUT …/assign (pro), GET …/{role}/responses (pro-only, access logged kind=safety_screening).
- Stored at top-level `joint_reports.safety_screenings.{role}` + `safety_flags.{role}` (NOT under responses — avoids marking a parent "complete"). Legal Lens view exposes `public_record()` only (no responses). PDF prints receipt/version/tier/date + "not a validated or diagnostic instrument" note.
- `safety_import.py` parses new structured bridge `safety_screening {version,tier,completed_at,answered_count,responses}`; legacy free-text still supported (version/tier None → "legacy format").
- JointNew: gender selects (parent-a-gender-select / co-parent-gender-select). JointReport: SafetyScreeningPanel. Pages: /joint/:id/safety-screening (parent), /joint/:id/safety-screening/:role (pro).
- TODOs in code: FVPS San Antonio 210-733-8810 unverified; Velonis 2021 HITS permission pending.
- Testing-agent fixes kept: joint_helpers.joint_public `.get("answers")`, coparenting_tiers._complete checks answers.
- Note: run E2E tests with `-n0` (xdist workers collide on timestamped fixture emails).
- DEPLOY PENDING user confirmation.

## 2026-10-06 Version C (LGBTQ+ relationship self-assessment) (agent-tested 36 passed incl. 16 E2E, NOT deployed)
- `safety_screening.py`: VERSIONS["C"] (16 items; tier3 = c_4,c_5,c_6,c_8,c_9), INTRO_C with Network/La Red 1-800-832-1901, LABEL_C.
- Neutral choice screen (11:28 clarification): GET overview returns `choice` {question, options:[default A/B if gender on file, else A+B, plus C]} until parent confirms; professional can override afterward via PUT …/safety-screening/choose (only default or C allowed). Stored: `safety_version.{role}` + `safety_version_confirmed.{role}` only — no orientation field.
- Labels: VERSION_LABEL (report/PDF/co-parent-safe) = "Version A/B/C"; VERSION_LABEL_PRO (full names) only in professional endpoints/screens. public_record() drops `title`.
- Import accepts version "C"; legacy fallback intact. Tests: tests/test_iter89_version_c.py. Frontend: choice screen in SafetyScreening.jsx (screening-choice-A/B/C), panel "Chosen by parent".
- DEPLOY PENDING user confirmation.

## 2026-10-06 Tier 3 alert (agent-tested, NOT deployed)
- `safety_screening._tier3_alert`: on a Tier 3 submission, emails the assigned professional (receipt, version letter, tier, pro-only link). No answers, no identity wording. Logged in `communications` kind=safety_tier3_alert. Never blocks the parent's submission. E2E asserts the comm record (17/17 pass).
- Resend rotation BLOCKED: `SA_COPARENTS_ALIGN_RESEND_KEY` not present in preview env as of 11:35 CDT. Nothing changed in .env. Deploy still pending user confirmation.

## 2026-10-06 Parent App Spec export (agent-tested, NOT deployed)
- `safety_screening.spec_export()`; server-to-server `GET /api/integrations/safety-screening-spec` (X-Integration-Key = INTEGRATION_SHARED_SECRET). Snapshot committed at `/app/docs/safety_screening_spec.json`. Test asserts tier3 ids match runtime.

## 2026-10-06 Screening reminders (agent-tested, NOT deployed)
- `safety_screening.run_screening_reminders()`: once per parent, 7+ days after invite acceptance, if no screening received; neutral email (no version/identity wording); marks `safety_reminded_at.{role}`; logged kind=safety_screening_reminder. Runs inside existing daily `follow-up-reminder` cron (8am Central) — cron cap of 5 already reached. Cron endpoint verified 401/200 in preview.
- Resend rotation still BLOCKED (secret absent at 11:50 CDT).

## 2026-10-06 Reminder dashboard (agent-tested, NOT deployed)
- Safety screening overview exposes `reminded_at` per role; SafetyScreeningPanel shows "Reminder sent <date> · no response yet" or "No reminder sent yet (automatic nudge 7 days after joining)" for unreceived screenings (testids safety-screening-{role}-reminded / -not-reminded).
- Resend rotation still BLOCKED (secret absent).

## 2026-10-06 ~12:05 CDT Release dispatched (job 84013524). Readiness check passed. Contents: six-questions framing, A/B/C screenings + choice screen, pro-only responses, Tier 3 alert, spec endpoint, 7-day reminders, reminder status. Production RESEND_API_KEY rotated by user in Secrets tab; preview rotation pending `SA_COPARENTS_ALIGN_RESEND_KEY` appearing in env (option c).

## 2026-10-08 Agreement LEGAL NOTICE & DISCLAIMER (agent-tested, NOT deployed — ships with Safety v2 / Resend republish)
- Verbatim notice constants `LEGAL_NOTICE_HEADING` / `DISCLAIMER` live in `joint_data.py` (imported by agreement_model.py & joint_engine.py). Old agreement disclaimer removed — single notice only.
- PDF (`pdf_agreement._legal_notice`) = last content block after signatures/contact footer; `_footer_contact` skips its side disclaimer when `disclaimer=False`. On-screen `AgreementDocument.jsx` renders it last (testid agreement-legal-notice). Not applicable to Legal Lens/Professional Report (no agreement section there); no Word export exists.
- Tests: tests/test_iter90_agreement_legal_notice.py (3) + test_agreement_v2 (3) pass.

## 2026-10-08 Safety Pathway Engine (agent-tested: 7 unit + 15 E2E via testing agent iter_71, NOT deployed)
- `backend/safety_pathway.py`: 9 flags (FLAG_MAP A/B/C + 5 EXTRA_ITEMS x_1..x_5, x_5 yn3), rules P1→"Protected participation review recommended", P2→"Structured communication recommended", else "Standard"; highest confirmed wins; `public_pathway()` sanitized block (label, child-need categories, safeguards, decision options, court-order notice, restricted notice). PUT /api/joint/reports/{rid}/safety-pathway/{role} {action: confirm|change|dismiss} pro-only, logged kind=safety_pathway. Suggestion stored in screening record `pathway_suggested`/`flags` (excluded from public_record).
- Import: `safety_flags` / `safety_pathway` honoured when present (top-level or inside safety_screening), else computed.
- UI: QuickExit.jsx (sticky bar, Escape×2, storage clear, location.replace weather.com, safe-device notice) on all screening screens; PathwayDecision.jsx on pro responses page; ImportedScreening shows confirmed pathway block; PDF card in §2. Plus Jakarta Sans + #3D1A78 for pathway/quick-exit UI.
- Note: pre-existing 1–11 scale level "Restricted Parallel Parenting" in lens_data remains (approved report scale); pathway engine never emits that phrase.

## 2026-10-08 Safety & Communication Assessment Hub (agent-tested: 10 backend + Playwright via testing agent iter_72; mobile overflow fixed, NOT deployed)
- Pages: /joint/:id/safety (SafetyHub.jsx: red Quick Exit bar "Confidential Assessment Area", header, inclusive banner, title, 3 cards, Begin button + privacy line, emergency strip), /joint/:id/communication-readiness (CommunicationReadiness.jsx, 4 items). Card 1 & 3 & Begin → /safety-screening (A/B/C choice screen). No AI widget; no third-party requests.
- Fonts bundled via @fontsource (plus-jakarta-sans, inter, montserrat, kaushan-script); Google Fonts link/import removed from index.html and index.css. Tailwind `font-jakarta`.
- Backend: COMM_ITEMS / comm_record / comm_items_view in safety_screening.py; GET/PUT /api/joint/reports/{rid}/communication-readiness (parents only); stored `communication_readiness.{role}`; shown on pro-only logged responses endpoint (`communication` key; endpoint also works when only comm exists). Import: `communication_readiness` from parent app export. Spec export includes contract. Panel shows comm received state.

## 2026-10-08 Privacy & Confidentiality Audit (READ-ONLY, no code changes). Verdict: CONDITIONAL PASS
- PASS: parent isolation/IDOR (joint, screening, pathway, comm readiness, Legal Lens pro-scoped, judge judge_id-scoped, packets 256-bit token + throttled code); co-parent/court outputs (only Received/Not Received, tier, neutral label); pro sensitive views access-logged; Perplexity sends ratings/category labels/ZIP only; fonts bundled.
- P1 SEC-001: static INTEGRATION_SHARED_SECRET (pasted in chat) can read parent email/child name and overwrite answers via /integrations/case-update → rotate, scope, alert on writes.
- P2 SEC-002: no account deletion / retention TTL for safety data. P2 SEC-003: joint report quotes co-parent's verbatim free-text answers (confirm intent).
- P3: CORS `*` with credentials; missing HSTS/CSP/XFO/XCTO (verified live); reset 6-digit code lacks attempt lockout; emails logged on failures; AUTO_APPROVE_EMAILS/seed_professionals run every boot; assistant.py sends child + parent names + case code to Gemini; index.html loads assets.emergent.sh script without SRI. Pending user decision on fixes.

## 2026-10-09 Hub banner copy (agent-tested, NOT deployed): heading "Designed for All Co-Parents"; line "Private, behavior-focused safety questions for every family structure, including non-binary and LGBTQ+ co-parents." Old "tailored… men, women" wording removed. Test added in test_iter93_comm_readiness.py.

## 2026-10-09 Audit fixes (agent-tested 20 passed incl. 3 new, NOT deployed)
- INTEGRATION_SHARED_SECRET rotated in backend/.env to the value supplied by the parent-app team ("SACOPARENTS SHARE CODE"); constant-time compare; every bridge write logged to access_events kind=integration_write (fields only, no answers) + admin email alert (ADMIN_EMAIL). NOTE: production env var must be updated to the same value before Republish.
- DELETE /api/auth/me (parents only; password + "DELETE"): cascades responses/safety_screenings/flags/pathway/comm-readiness/version/reminders, anonymises participant to "Former participant", deletes foundation statements, revokes invitations, redacts communications `to`, PII-free access_events record, clears cookies. UI: DeleteAccount.jsx button in Dashboard header for parents.
- Security headers middleware in server.py (HSTS, CSP, XFO DENY, XCTO, Referrer-Policy, Permissions-Policy) — applies to all FastAPI responses (/api). Frontend HTML is served by the platform static host; headers there depend on platform edge (meta CSP not added).
- 2026-10-09: meta CSP added to index.html (no console violations on landing). Removed startup `login_attempts.delete_many` from seed_auto_approvals/seed_admin (deployment blocker + audit P3). Release dispatch pending readiness re-check.
- 2026-10-09: readiness PASS; release dispatched (deploy queued). Verify production after green: /api/health headers, landing 5-step band, hub route, agreement notice.

## 2026-10-09 Privacy Notification (agent-tested 3 backend + browser flow, NOT deployed)
- `backend/privacy_notice.py`: PRIVACY_NOTICE_VERSION="2026-10-09.1" (also mirrored as PRIVACY_NOTICE_VERSION in frontend/src/App.js — keep in sync; test enforces), SUBHEAD pending-decision string, exact NOTICE text; GET /api/privacy-notice, POST /api/privacy-notice/accept (stores users.privacy_notice {version, accepted_at} + history). `public_user` exposes privacy_notice_version.
- Frontend: /privacy-notice page (PrivacyNotice.jsx, Plus Jakarta/#3D1A78, Quick Exit, BrandLogo + "Start with Safety", Continue disabled until checkbox); Protected route redirects any signed-in user (parents + professionals; judges too) whose accepted version ≠ current, then returns to the original path. Footer links intentionally absent (placeholder comment).

## 2026-10-09 — Privacy Notice follow-ups (deployed in release 84013524)
- Footer links on Privacy Notice now live: /privacy, /legal/confidentiality, /legal/sharing-consent (two new DRAFT pages in Legal.jsx, badge "Draft — pending owner review").
- Admin Acceptance Log tab (Dashboard → Acceptance Log): GET /api/admin/privacy-notice/acceptances (+ .csv export). Admin-only (403 otherwise).
- Tests: backend/tests/test_iter95_privacy_notice.py (4 passed), iter94 regression green; deployment readiness PASS; deploy queued (job 84013524…). Awaiting system deploy notification.
- PENDING: Professional-specific notice variant — user will supply exact wording. Owner review of Confidentiality / Sharing & Consent draft text.

## 2026-10-10 — Version B (CDC), Version C credit, draft policy pages (NOT DEPLOYED — awaiting user confirmation)
- Version B now CDC NISVS-adapted (ids b_1..b_15, tier3 b_5/b_10/b_11/b_12/b_13); Velonis/HITS kept in B_VARIANTS["velonis"], switched OFF via VERSION_B_SOURCE env ("cdc" default) / configure_version_b(). FLAG_MAP_B in safety_pathway. Import accepts source "cdc_nisvs_adapted"; legacy b1-b9 auto-detected. Records store b_source.
- Version C credit adds National LGBTQ Institute on IPV; RESOURCES_C adds The Network/La Red + external lgbtqipvinstitute.org link (new tab, noopener, "leaves the app" note). FVPS 210-733-8810 marked verified.
- Draft policy pages /privacy, /confidentiality, /sharing-consent (PolicyPage.jsx + content/policies.json, Version 1.0 draft, noindex, UNLINKED). Old approved policy moved to /privacy-policy (all existing links updated). Notice footer_links reverted to [] placeholder; /legal/confidentiality + sharing-consent drafts removed.
- backend/retention.py: RAW_SCREENING_RETENTION_DAYS=90, COURT_SUBMISSION_RETENTION_MONTHS=6 — constants only, no deletion job.
- Fixed tailwind duplicate fontFamily key: font-jakarta now works (Plus Jakarta Sans verified in browser).
- Tests: iter96 (Version B/C), iter97 (policy pages); 45 passed across safety/privacy suites. Audit structured report delivered in chat (GAP-01..19).
- PENDING: user confirms deploy; professional notice wording; Joint Report verbatim text decision; PostHog consent decision (GAP-05); CORS_ORIGINS prod value.

## 2026-10-10 07:xx — Owner pause & drafts (PREVIEW ONLY, nothing deployed after job 58042de)
- Draft policy routes (/privacy, /confidentiality, /sharing-consent) REMOVED from App.js; text preserved un-routed in content/policies.json + PolicyPage.jsx. Approved policy lives at /privacy-policy.
- Retention Engine PAUSED by owner: retention.py = constants only; no cron wiring, no purge, no judge reminder. Do not build until audit sign-off + owner design approval.
- New draft "Security & Privacy Practices" page content (policies.json key security-practices) — unrouted, publish only after GAP items addressed and owner approval.
- Full structured audit report v2 (GAP-01..GAP-20) delivered in chat 2026-10-10; not stored in app.
- RULE: no deploy of anything without explicit user "deploy".

## 2026-10-10 07:39 — Privacy Notification REDESIGN (preview only, NOT deployed)
- New layout per "Privacy Welcome Screen" mockup: lavender banner + logo, "Privacy & Confidentiality" / "Start with Safety. Build with Trust.", five icon cards, bordered legal notice, #3D1A78 button, Plus Jakarta. Subhead now "Private by default. Shared with your consent, or as the law requires."
- PRIVACY_NOTICE_VERSION bumped to 2026-10-10.1 (backend + App.js) → re-shown to all users. No policy links/buttons; hidden PLACEHOLDER kept; footer_links [].
- Tests iter95 5/5; browser verified desktop+390px, keyboard (Space toggles checkbox → button enables), Quick Exit present, acceptance → dashboard.
- 07:53 — Legal notice box now 4 sentences (adds "SA CoParents is a separate tool from the law practice of Matt Sossi." / "Access to or use of this app does not create an attorney-client relationship."). Reusable in privacy_notice.LEGAL_NOTICE_SENTENCES / LEGAL_NOTICE. Version bumped to 2026-10-10.2 (backend + App.js). iter95 5/5; browser verified re-show + exact text. PREVIEW ONLY.

## 2026-10-10 08:xx — Professional Dashboard redesign (PREVIEW ONLY, not deployed)
- ProHero now: one-message headline ("SA CoParents Align helps professionals understand each parent's perspective…"), five workflow action cards with live counts (Invite Parents · Review Assessments · Joint Report · Legal Lens Review · Court Report) + Judge Portal & Referrals card (pending referral count). Counts computed in Dashboard.jsx heroCounts from case_status. Tour step text updated. Old PrimaryTiles remain under "More tools".
- Deferred (owner skipped for now): hard "Approve for release" gate, Judge's Overview page 1, Safety-review badge on case rows.

## 2026-10-11 — Owner decisions implemented (PREVIEW ONLY, not deployed)
- Prod secrets check (names only): CORS_ORIGINS exact prod origin (GAP-09 closed), AUTO_APPROVE_EMAILS unset (GAP-16 closed), SACOPARENTS_APP_URL=https://sacoparentsapp.online. 10-10 deploys were owner Re-publish (GAP-21 closed).
- Retention Engine BUILT per owner: raw answers+flags purged 90d after case close (keep tier/version/receipt); frozen court submissions deleted entirely at 6 months (pdfs, packet, submission entry; referral→expired); judge reminder 30d before if unopened, once. Runs via follow-up-reminder daily cron. Admin GET /api/admin/retention/preview. Tests iter98.
- GAP-15: Joint Report free text kept; disclosed in invitation email + Sharing & Consent page; professional can redact per answer (PUT /joint/reports/{rid}/redactions, UI "Redact before release", access-logged kind=redaction).
- Policy pages APPROVED & ROUTED (/privacy, /confidentiality, /sharing-consent, /security-practices) but UNLINKED; robots.txt Disallow + meta noindex. Still show "Version 1.0 (draft)" badge — ask owner whether to flip status to "final" when linking.
- Pending: owner "deploy"; owner "link them"; professional notice wording.
- 2026-10-11 12:3x — Owner: Retention Engine PAUSED (code kept in retention.py; UN-WIRED from cron; crons.yml restored); deploy on hold pending owner's report; policy pages flipped to status "final" (badge shows "Version 1.0"), still UNLINKED + robots/noindex; 90-day rule keeps tier/version/receipt, purges answers+flags. Tests iter97/98 19 passed.
- 2026-10-11 14:50 — SWITCH OFF: Retention Engine behind RETENTION_ENGINE_ENABLED=false (every purge/reminder raises RetentionDisabled; not scheduled; admin route removed; tests prove it cannot run). Policy routes REMOVED again (content kept un-routed, status "final"); robots.txt removed; Sharing & Consent + invitation disclosure sentences removed. Redaction tool left as-is (pending owner decision). 25 tests green. Preview only.

## 2026-10-11 15:02–15:08 decisions implemented (PREVIEW ONLY, not deployed)
- Pause/Resume joint features: backend/joint_pause.py (PUT /joint/reports/{rid}/joint-pause, pro-only, note, access-logged kind=joint_pause, history). Blocks responses, report, PDF, invitation create/resend with 423 + NEUTRAL_MESSAGE; parents get only joint_blocked flag. No notifications. UI: components/JointPauseControl.jsx on JointReport.
- Safe contact channel: SubmitIn.safe_contact → safety_screenings.{role}.safe_contact (clean_safe_contact); pro-only on /responses screen; excluded from public_record/receipt/spec/PDF/email/import/bridge. UI: components/SafeContactStep.jsx (parent form), SafetyResponses view.
- Minimal-content notifications: MINIMAL_NOTIFICATIONS env (default on). Changed: invitation subject, report-ready + co-parent-completed (neutral body _neutral_email_html), screening reminder (subject+body), Tier3 pro subject, both-completed pro subject, FV facilitation subject.
- Redaction notice: joint_engine.REDACTION_NOTICE in invitation closing + report.redaction_notice (JointReport footer).
- Bridge requester context: integrations.BRIDGE_REQUESTER_CONTEXT (default false); headers X-Requester-{Professional-Id,Case-Id,Parent-Role,App} + body "requester" + query params; 401/403 → 403 DENIED_DETAIL. Contract provisional pending parent-app builder.
- NOT built (ambiguous): 3(c) separate individual perspective court reports — questions listed to owner.
- Tests: iter99 (16) + regression → 56 passed.

## 2026-10-12 — AI Privacy Warning + Individual Perspective Reports (PREVIEW ONLY)
- components/AiPrivacyWarning.jsx (exact owner text; full + one-liner). Placed above: AlignAssistant input (Gemini), LensAiTools research question (Perplexity), LegalLensReport top (fields→ai-draft/Jev/Claude), FoundationEditor top (Jev blame-check). Tests iter100.
- pdf_individual.py: one frozen packet, two per-parent sections (cover, receipt line, perspective areas provided/not provided, pro observations). court_workflow.SubmitIn.packet_mode; resolve_packet_mode (paused→individual default, joint→423); switch logged "Court packet format switched…"; packet_mode/packet_label stored; filename court-packet-*. Tests iter101.
- No "Communication Builder" UI exists in this app (name appears only in options library text).

## 2026-10-12 — Owner approvals + Legal Lens expert-report cover (PREVIEW ONLY, not deployed)
- Owner APPROVED the 7 neutral notification templates (MINIMAL_NOTIFICATIONS on) — keep as is.
- AI Privacy Warning: test_iter100 green (3/3); placements: AlignAssistant, LensAiTools Research Ask, LegalLensReport, FoundationEditor.
- Individual Perspective Reports: filename stays court-packet-{cause}.pdf; cover wording reported to owner; no packet-mode UI toggle (not requested).
- NEW: Legal Lens Professional Alignment Report cover page (pdf_lens.cover_page + ReportCover.jsx): Title / Bar Number / License Number rows, signature line (uploaded image on finalized reports), 'Date of submission', and word-count line 'Content origin: X% generated by AI (reviewed by the professional) · Y% written by the professional.' (legal_lens.content_origin; AI words = fields still identical to an AI draft). Report fields added: cover_title, cover_bar_number, cover_license_number, submission_date. Tests: tests/test_iter102_lens_cover.py (2 passed), iter58 regression 5 passed.
- Still pending owner: professional notice wording; stale /privacy-policy; Resend rotation; bridge requester contract; perspective-area summaries question (unanswered).

## 2026-10-12 — Four follow-ups built (PREVIEW ONLY, not deployed)
- Bar Number Profile: GET/PUT /api/me/profile/contact now carries pro_role (title), bar_number, license_number; ProfileContactForm.jsx on the Legal Lens cover ('My profile details') — cover auto-fills.
- Signature Capture: SignatureCapture.jsx (canvas draw + file upload -> POST /me/profile/image/signature; remove) on the Legal Lens cover; prints on finalized reports only.
- Topic Summaries: joint_reports.individual_summaries {a:{key:text},b:{}} via GET/PUT /api/joint/reports/{rid}/individual-summaries (240 chars, custody wording -> 400, event logged); IndividualSummaries.jsx under the Professional Report; pdf_individual prints the summary instead of 'Perspective provided'.
- Packet Mode Toggle: ProfessionalStatement.jsx radio Joint / Individual (packet-mode-joint|individual), sent as packet_mode in preview+submit; joint disabled while paused; GET professional-statement returns packet:{joint_paused,mode}; switch logged in access_events ('Court packet format switched from X to Y'). Verified end-to-end via API on a court case.
- Tests: tests/test_iter103_profile_summaries_toggle.py + tester's test_iter103_packet_mode_pause.py (6/6), iteration_73.json. Testing agent noted canvas-drawn signature occasionally did not persist under Playwright synthetic events; file upload path solid.

## 2026-10-13 — Owner decisions + Professional Notice (PREVIEW ONLY, not deployed)
- Owner: KEEP the four follow-ups (profile/bar, signature, topic summaries, packet switch). Secret rotation DEFERRED (old INTEGRATION_SHARED_SECRET/JWT_SECRET/WEBHOOK_CRON_SECRET/admin pw remain in git history commit 8de5b20; backend/.env untracked + .gitignore'd on 2026-10-13). Stale /privacy-policy stays as is.
- NEW Professional Notice (backend/professional_notice.py, pages/ProfessionalNotice.jsx, route /professional-notice, gate in App.js Protected for role=professional only, version 2026-10-13.1, user.professional_notice{version,accepted_at}+history, admin log GET /admin/professional-notice/acceptances). Text verbatim from owner. Tests test_iter104 3/3; UI verified.
- Signature hardening: pointer events + capture, ink check, white-background PNG, post-upload verification GET /me/profile/contact; drawn save verified end-to-end in browser.
- Resend: one authorized delivery test sent to mattsossi@bsossi.com via provider=resend (accepted, id returned). Delivery to inbox not yet confirmed by owner.
- Parent-app contract draft written to /app/PARENT_APP_REQUESTER_CONTEXT_CONTRACT.md for review; BRIDGE_REQUESTER_CONTEXT stays OFF.

## 2026-10-13 — Four more follow-ups (owner approved 'YES, A'; PREVIEW ONLY, not deployed)
- Notice Admin View: AdminAcceptanceLog.jsx parametrized; Dashboard Acceptance Log tab shows Privacy log + Professional Notice log (testid admin-pro-notice-log) with CSV at GET /api/admin/professional-notice/acceptances.csv.
- Court Submission Receipt: SubmissionReceipt.jsx shown after submit and via 'Receipt' link per version — date, packet format, version, court, submitted by, packet/report/statement SHA-256.
- Judge Packet Label: packet_label added to /court-dashboard/cases/{ref} submissions and /court-dashboard/packets; shown in CourtCaseCard + CourtDashboard rows ('Individual Perspective Reports' / 'Joint Report').
- Summary Neutrality Check: PUT individual-summaries runs jev.neutrality_check on every line; flags -> 400 'Neutrality check — please rephrase…' (blocking, per owner); Jev outage -> 503.
- BUG FIX (pre-existing): judges hit a redirect loop (blank page) at /privacy-notice because the judge guard did not allow that path; App.js guard now allows /privacy-notice.
- Tests: tests/test_iter105_neutrality_receipt.py 2/2; UI verified for receipt, judge label, admin log.

## 2026-10-14 — Owner: NO to all four suggestions (judge receipt PDF, notice banner, Gemini rewrite, receipt email). RULE: never build suggestion-chip items without explicit instruction in main chat.
- Parent-app link contract implemented behind PARENT_APP_LINK_CONTRACT (default false): backend/parent_app_contract.py (headers X-Integration-Key/X-Professional-Id/X-Case-Id, verify-link-code {code,professional_id,case_id}, export access_scope handling, safe-contact, screening/assign, aggregate, neutral refusal mapping), bridge_views.py (pro-only logged live views, 404 'Not available' when flag off), integrations.py (link accepts report_id; invite lookup returns professional_id), safety_screening assign → outbound assign when flag on. Old BRIDGE_REQUESTER_CONTEXT removed. UI: JointAssessment passes report_id; BridgeSafeContact.jsx on SafetyResponses page. Tests test_iter106 (29 total w/ iter99) green. Contract doc: /app/PARENT_APP_REQUESTER_CONTEXT_CONTRACT.md.
- Secrets: backend/.env untracked (removed in commit 06cae3b); old values remain in history commit 8de5b20 — cannot rewrite history from the pod; rotation deferred by owner.

## 2026-10-14 — Safety-first entry + Crisis Resources (owner-approved; PREVIEW ONLY, not deployed)
- Flow: sign in -> Privacy Notification -> /start-with-safety (StartWithSafety.jsx; Begin / Skip for now; once per session via sessionStorage align-start-with-safety-seen; auto-skips to dashboard when status completed/skipped) -> journey. PrivacyNotice sends parents to /start-with-safety.
- Banner: SafetyEntryBanner.jsx under the Dashboard header for role=parent; text in content/safetyEntry.js ('Start with Safety. A private check-in is available any time.'), Begin + Quick Exit; shrinks to small link when status != not_started. GET /me/safety-entry (status only, identical shape for all parents). POST /joint/reports/{rid}/safety-screening/skip records safety_skipped.{role}. _status gains entry_status/skipped_at.
- Crisis Resources: CrisisResources.jsx (shadcn Dialog, bundled icons) on StartWithSafety, SafetyHub, SafetyScreening (choice/questions/results), SafetyResponses (pro). GET /safety/crisis-resources?version= -> 911, NDVH, SA FVPS 24h, +VictimConnect (B), +Network/La Red + Trevor (C), Bexar County FJC LAST with hours (all versions). Refetches when version changes.
- Plus Jakarta Sans now bundled via @fontsource/plus-jakarta-sans (no CDN).
- Fixes: professional first-login redirect loop (privacy vs professional notice) in App.js Protected.
- NOT added: scoring, household questions, demographic menus. Tests: test_iter107 4/4; testing agent iteration_74 (issues fixed, re-verified by screenshot).

## 2026-10-14 — Option A: Start-with-Safety STEP required, ANSWERS not (owner decision 10:02; PREVIEW ONLY)
- Gate: PUT /joint/reports/{rid}/responses -> 403 'Please go through the Start with Safety step before answering the assessment.' until entry_status != not_started; /joint/reports/{rid} returns safety_step_satisfied for my_role; JointAssessment.jsx redirects to /start-with-safety when false.
- 'Skip for now' removed; POST /joint/reports/{rid}/safety-screening/decline ("I'd rather not answer these right now") records safety_declined.{role} date; statuses completed|declined|not_started; entry_label Received/Declined/Not started · date; receipt() -> 'Declined (parent chose not to answer at this time, DATE)' / 'Not started.' in professional panel, Individual Perspective Reports, Legal Lens PDF.
- Per-question skip unchanged; privacy notice unchanged; no auto restrictions; other parent never sees status (only own safety_step_satisfied flag). Banner text unchanged, no 'skip' wording. casekit.fill now declines the step before answering (tests). Tests test_iter108 2/2 + regressions 19 passed; UI verified (hub, bounce from /assess, decline -> link, assess opens).
- Pending (not built, text unapproved): invitation email wording for the required step; choice-screen text.
- 2026-10-15: Professional Access Notice on /start-with-safety above the decline button (exact owner text; PROFESSIONAL_ACCESS_NOTICE + STEP_NOTICE_VERSION=2026-10-15.1 in safety_screening.py, served via /me/safety-entry; ack via POST /me/safety-entry/ack-notice stored users.safety_step_notice). Step screen shows once more for every parent (needs_notice), then 'Continue'. Privacy Notification version/text untouched. Test in test_iter108.

## 2026-10-16 — Owner-approved edits (PREVIEW ONLY, not deployed)
- Invitation email: child name + subject label removed; professional name kept; new line after code: 'This invitation includes a private check-in before the assessment. Please complete it on a device only you can access.' (joint_helpers._invite_email_content).
- Choice screen: no gender default (GENDER_DEFAULT empty, default_version always None); same four options for everyone: Questions written for women (Version A) / men (Version B) / LGBTQ+ relationships (Version C) / Prefer not to say (I'll help you choose) with CHOICE_HELP_TEXT; switch note 'You can switch to a different set of questions later.' always shown; only version letter stored.
- Content note updated to '…your progress is saved so you can come back later.' and made TRUE: PUT /joint/reports/{rid}/safety-screening/draft stores safety_drafts.{role} (own account only, never to co-parent/professional, cleared on submit); GET returns my_draft; SafetyScreening.jsx autosaves (800ms) and restores.
- Tests: test_iter109 (3) + iter87/iter88 updated for no-default rule and xdist-safe fixtures; 36 passing; browser-verified choice screen + resume.

## 2026-10-16 — FAMILY VIOLENCE SAFETY MODULE (owner spec) — Phase 1 DONE (PREVIEW ONLY)
Owner rulings: 1 replace A/B/C with 8-domain set; 2 professional-decides (no auto restrict/pause; AUTO_RED webhook stays OFF); 3 Red/Amber/Green labels (pros only); 4 spec email templates (Phase 2); 5 keep Option A gate; 6 signed webhook behind own OFF flag (Phase 3); 7 build supervisor role + training ack + audit, DEFER separate encryption keys, break-glass, SPF/DKIM/DMARC (document DNS).
- Phase 1 built: backend/fv_screening.py (ITEMS 8 domains + gate/danger/free_text, TF scale, compute() fixed rules red/amber/green + triggered_rules, APP_TIER_LABEL green='No concerns reported', EMERGENCY, CLOSE_NOTE). safety_screening.py: VERSIONS['FV'], OFFERED_VERSION='FV' auto-assigned (choice screen bypassed), compute_tier/build_record FV branch (tier 3/2/1 = red/amber/green so Tier-3 alert + pathway + receipts keep working), _status app_tier/app_tier_label/triggered_rules (pro only), parent submit response has NO tier (close_note only). Frontend SafetyScreening.jsx: gate (Not now→dashboard, Quick exit), follow-up items (pv_worse/pv_medical) shown only after pv, inline emergency panel on danger=Yes, neutral result. A/B/C defs kept only for legacy records; obsolete tests skipped with reason.
- Tests: test_iter110_family_checkin.py 25 passed (each Red rule, each Amber rule, Green, flow/no-leak); suites 45 passed/6 skipped.
- NEXT: Phase 2 emails (two templates, single-use 7-day links, cadence, reply-to professional, one email per parent), Phase 3 webhook POST /api/internal/safety-status HMAC ALIGN_WEBHOOK_SECRET flag OFF, Phase 4 review two-column/pattern panel + provisions library + export scan/footer, Phase 5 supervisor sign-off/training gate/audit export + acceptance tests 1-12.

## 2026-10-16 — FV module Phases 2-4 DONE (PREVIEW ONLY). RESEND_API_KEY rotated by owner (new key in backend/.env, untracked).
- Phase 2 backend/safety_invites.py: professional_template (reply-to professional, 'reply to this email') + coparent_template; NEUTRAL_SUBJECT; PRIVATE_DEVICE_LINE 'works once and expires in 7 days'; INVITE_EXPIRY_DAYS 14→7 (core.py); send_invite_email + reminder-preview + /joint/invitations/preview use new templates (child/subject never in email); cadence DEFAULT {reminder_days:[3,6],max 2} per case GET/PUT /joint/reports/{rid}/invite-cadence (pro only, cap 2); run_invite_reminders() daily via existing follow-up-reminder cron (20h guard, skips expired/demo/paused).
- Phase 3 backend/safety_status_webhook.py: flag SAFETY_STATUS_WEBHOOK=false (.env), POST {SACOPARENTS_APP_URL}/api/internal/safety-status, X-Align-Signature sha256=HMAC(ALIGN_WEBHOOK_SECRET, body) (+X-Align-Timestamp/Version), allow-listed 8 keys only, retries 1/3/9s, admin email alert + db.webhook_deliveries on failure; fired from safety_pathway confirm; GET /admin/safety-status-webhook (admin). ALIGN_WEBHOOK_SECRET not set yet; parent-app builder confirmation still needed.
- Phase 4 backend/safety_review.py + frontend/src/pages/SafetyReview.jsx (/joint/:id/safety-review, link in SafetyScreeningPanel): two columns (entry status, Red/Amber/Green, pattern panel = rule labels grouped by domain, pathway), concern level none/green/amber/red + reasons (required for amber/red) + notes, 14 provisions in 6 groups + custom, PROVISIONS_FOOTER, GET .../safety-review/provisions.pdf scanned (scan_text/scan_pdf: question texts, time-frame answers, tier words) → 409 + export_scan_block log on leak. Stored doc.safety_review; never in parent payloads.
- Tests: test_iter111_safety_phases.py 9 passed; invitation/email/safety suites 67 passed/8 skipped; test_invitation_preview updated (no child name in email). Browser-verified review page.
- NEXT: Phase 5 supervisor sign-off for lowering Red, training acknowledgment gate, admin audit export; wire scan_pdf into Legal Lens / Individual / court packet exports (not yet hooked — only provisions PDF is scanned); DNS SPF/DKIM/DMARC records documentation.

## 2026-10-16 — FV module Phase 5 DONE (PREVIEW ONLY)
- backend/pro_training.py: TRAINING_VERSION 2026-10-16.1, 6 modules, GET /professional-training, POST /professional-training/acknowledge (users.safety_training + history); require_training() → 428 {code: training_required} on screening responses, safety-review GET/PUT/pdf, supervisor sign-off. auth/me exposes safety_training_version + is_supervisor. PATCH /admin/professionals/{uid}/supervisor. GET /admin/safety-audit(.csv) over access_events AUDIT_KINDS.
- Supervisor sign-off (safety_review.py): lowering concern level from red → stored doc.safety_review_pending_lower, returns requires_supervisor; POST /joint/reports/{rid}/safety-review/supervisor-signoff {approve, note} by admin or is_supervisor, never the requester; approve applies + supervisor_signoff record, decline keeps red; both logged kind supervisor_signoff.
- Export scan wired: safety_review.assert_export_clean() in legal_lens (pdf + bundle), court_workflow (_submission_pdfs Legal Lens, Individual Perspective Reports, combined packet), court_packets._pdf_response. 'Family check-in' (neutral version label in receipt line) removed from forbidden terms; rule labels added.
- Frontend: /professional-training (ProfessionalTraining.jsx), lib/trainingGate.js redirect on 428 from SafetyReview + SafetyResponses, pending-lower banner + sign-off controls in SafetyReview, AdminSafetyAudit on admin dashboard.
- EMAIL_DNS_SETUP.md: SPF/MX/DKIM/DMARC records for sacoparentsalign.com (DKIM value from Resend dashboard).
- Tests: test_iter112 4 passed; fixtures updated (_case acks training; iter88 pro_session acks; iter64 declines step). Suites 43+18 passed. Browser: 428 redirect → training page → review opens (390px).

## 2026-10-16 — Supervisor toggle, reminder dashboard, webhook live check DONE (PREVIEW ONLY)
- AdminProfessionals: is_supervisor in /admin/professionals; 'Make supervising professional' button → PATCH /admin/professionals/{id}/supervisor; Supervising badge.
- Reminder dashboard: GET /professional/invitations (pro's open cases, pending invites, next_reminder_at from cadence, expires_at, expired, can_reissue; no token). components/InviteReminderPanel.jsx on professional dashboard (under ProContactCard) with 'Send fresh link' → existing POST /joint/invitations/{iid}/reissue.
- Webhook live check: POST /admin/safety-status-webhook/test → deliver(test=True) single attempt, response_snippet (300 chars), case_id ALIGN-TEST-PING, works while flag OFF, no admin alert email on failure; components/AdminWebhookCheck.jsx on admin Acceptance Log tab (button disabled until ALIGN_WEBHOOK_SECRET set).
- Tests: test_iter113 3 passed (+iter111 9). Browser: admin toggle buttons + webhook card verified; reminder panel verified.

## 2026-10-16 — Training refresher + case reminder settings DONE (PREVIEW ONLY)
- pro_training.training_state(): current only if latest version AND acknowledged < REFRESH_DAYS(365); reason never|version|yearly; CHANGELOG changes_since; auth/me safety_training_due. Gate (428) also enforces yearly. components/TrainingRefresherBanner.jsx on pro dashboard; ProfessionalTraining shows yearly note / what changed.
- components/InviteCadenceSettings.jsx on JointReport (pro view, non-foundation): edit reminder days + max (0-2) via GET/PUT invite-cadence.
- Webhook secret: NOT set — needs owner/parent-app builder value (ALIGN_WEBHOOK_SECRET in backend/.env).
- Tests: test_iter114 3 passed (+iter112 4).

## 2026-10-17 — Owner decisions
- (c) ALIGN_WEBHOOK_SECRET stays UNSET; SAFETY_STATUS_WEBHOOK=false; never generate/print a secret. Webhook paused until owner decides.
- STOP building new features on this thread (owner instruction).
- Wrote /app/PARENT_APP_SAFETY_STATUS_WEBHOOK_CONTRACT.md (document only) for the parent-app builder.
- Owner asked about a 'Safety Gate message with Get Help line for the sacoparentsapp chat' — does NOT exist in this project; belongs to the other thread.

## 2026-10-17 — AI model update (owner: ChatGPT + Claude integrations; Q1 skipped → default a; models a = GPT-5.5 + Claude Sonnet 5.5)
- assistant.py MODEL → (openai, gpt-5.5) [Align Assistant; was gemini-3-flash-preview]. ai_tools._claude → claude-sonnet-5-5 (parallel-parenting summary / pro drafting). legal_ai.MODELS openai → gpt-5.5 'GPT-5.5', claude → claude-sonnet-5-5 'Claude Sonnet 5.5'; lens_data.AI_MODELS labels updated. joint_ai (Gemini 3.1 Pro) and Legal Lens default (gemini) unchanged. Perplexity, Jev, TTS unchanged. AI Privacy Warning unchanged (no uploads to AI).
- Google sign-in: asked owner (roles / new accounts / keep passwords) — NO ANSWER yet; not built.

## 2026-10-17 — Google sign-in, assistant model switch, model disclosure (PREVIEW ONLY)
- backend/google_auth.py: POST /auth/google/session {session_id} → Emergent session-data (backend only) → resolve_google_user(email): EXISTING professional/admin only (parents/judges/unknown → 403, unapproved pro → 403), sets same JWT cookies as password login; never creates accounts; GET /auth/google/config. Frontend: components/GoogleAuth.jsx (startGoogleSignIn redirect with window.location.origin — never hardcode; AuthCallback), App.js AppRoutes detects #session_id via useLocation, AuthContext skips /me during callback; Auth.jsx 'Continue with Google' (login mode, non-parent). auth_testing.md overwritten with this app's flow. Owner/admin: mattsossi@bsossi.com.
- assistant.py MODELS gpt→gpt-5.5 / claude→claude-sonnet-5-5; ChatIn.model + DraftInsertIn.model; session id suffixed per model; assistant_messages.model = actual model. AlignAssistant.jsx header toggle (assistant-model-gpt / assistant-model-claude).
- Disclosure: joint_ai rep.ai_disclosure; joint_engine agreement view ai_model + ai_disclosure (agreement_ai.MODEL_NAME); pdf_report agreement header prints ai_disclosure; JointReport jr-ai-disclosure; AgreementDocument agreement-ai-disclosure; LegalLensReport per-field hint 'Drafted with <model>'. Legal Lens PDF appendix already per-section.
- Perplexity: PERPLEXITY_API_KEY in backend/.env returns 401 (invalid) — owner must supply a valid key; not fixable in code.
- Tests: test_iter115 4 passed.

## 2026-10-17 — Google link badge + transmittal AI line (PREVIEW ONLY)
- auth/me google_linked_at; DELETE /auth/google/link (requires password_hash); ProContactCard shows 'Google linked' badge + Unlink.
- court_packets._ai_disclosure(doc): exact models from approved ai_joint_draft, agreement_ai, Legal Lens ai_drafts (or 'none'); printed in italics under Enclosures on the transmittal (pdf_report.build_transmittal_pdf ai_disclosure).
- Tests: test_iter116 2 passed; packet suites 11 passed.

## 2026-10-17 — Google for judges + AI line in receipt/court email (PREVIEW ONLY)
- google_auth GOOGLE_ROLES += judge; AuthCallback routes judge → /court-dashboard; Auth.jsx note updated.
- court_workflow: submission record sub.ai_disclosure (court_packets._ai_disclosure); SubmissionReceipt shows receipt-ai-disclosure; court notification email gets the italic AI line after the summary.
- Tests: test_iter117 2 passed.

## 2026-10-17 — Perplexity key replaced (owner-provided, untracked backend/.env). Direct chat/completions returns 403 for this key (sonar endpoint not enabled) but the app's /v1/agent path returns 200: Local Resources working (Bexar County FJC result). Two earlier pasted keys were invalid — advised owner to revoke them.

## 2026-10-17 — Deploy prep decision: (b) keep .env files git-ignored; owner enters production keys in the deployment Secrets tab. Readiness checker 'fail' on gitignore is by convention; all code checks passed. No deploy yet — owner must say 'deploy'.

## 2026-10-17 08:57 CDT — OWNER CORRECTIONS (final after follow-up)
- Screening: KEEP the 8-domain Family check-in as the single live screening; A/B/C four-option choice screen REMOVED (defs kept only to read legacy records; OFFERED_VERSION='FV'). A/B/C tests skipped with reason 'Owner 2026-10-17 (final)'. fv_screening.py = live.
- Invitation links back to 14 days (core.INVITE_EXPIRY_DAYS=14; email line '14 days').
- Training gate → PROMPT only (pro_training.require_training no-ops; banner/page remain; never blocks responses or review).
- Twilio/SMS removed: sms.py, UrgentSmsSettings.jsx, court_messages alert-settings/test-sms routes + _urgent_sms, test_iter76_urgent_sms.py deleted; twilio removed from requirements.txt and pip; TWILIO_* removed from backend/.env. Urgent-safety EMAIL alert to judges remains.
- SAFETY_STATUS_WEBHOOK=false; ALIGN_WEBHOOK_SECRET unset (unchanged).
- Tests: safety suites 66 passed / 5 skipped (A/B/C), iter88 13 passed/4 skipped; court/ai suites 21 passed.

## 2026-10-18 (18:54 CDT approval + addition) — PREVIEW ONLY, nothing deployed
- Owner chose (a): Family check-in stays the single live screening; A/B/C stays removed. No code change.
- ALIGN_WEBHOOK_SECRET: value pasted in chat by owner → burned. Removed from backend/.env; 0 occurrences in tree, git history, logs, DB. Left UNSET; no replacement generated; SAFETY_STATUS_WEBHOOK=false; admin test ping disabled. Parent app returned 401 to signed pings (acceptable while paused).
- Read-only UI pass iteration_74: professional, judge, parent flows OK; 14-day invite wording; no SMS card; Google button present.
- Production secrets table and EMAIL_DNS_SETUP.md (sacoparentsalign.com) delivered in chat.

## 2026-10-18 19:32–20:xx CDT — PRODUCTION LIVE (align-report.emergent.host, run 45d2385e, same code as preview)
- Owner said 'deploy' → first deploy via deployer; redeploy by owner after secrets edit; both Live. Static-check .gitignore '.env blocker' is a generic rule — owner keeps .env untracked and uses Deployment Secrets; deploy succeeded that way.
- Prod secrets (names): 17/19 required present; RETENTION_ENGINE_ENABLED and GOOGLE_SIGNIN absent (defaults off/on); ALIGN_WEBHOOK_SECRET absent; INTEGRATION_PROXY_URL platform-managed (ignore). Owner to add the two missing keys at next deploy.
- CORRECTION: seeded pro accounts joy@bsossi.com / dralsmith@gmail.com existed in prod since an earlier release (Sept activity), not created today. Joy already set own password (must_change_password cleared). Dr Smith: temp password never used to log in; owner chose option (iii): forgot-password email sent once from prod (15-min code); temp password NOT invalidated. Deployer agent is read-only for prod data; DB Manager one-liner documented in chat if owner wants hard invalidation later.
- Owner decision (a): Family check-in stays live; A/B/C removed. Webhook paused; no replacement secret.

## 2026-10-18 19:45 CDT — Dr Smith password: owner chose 3 (leave as-is)
- Deployer agent is READ-ONLY for prod data; main agent has no prod DB access. Sentinel '!disabled…' is WRONG (bcrypt raises ValueError → 500); correct invalidation = valid bcrypt hash of a discarded random value. Owner declined; temp password for dralsmith@gmail.com remains valid (must_change_password=true forces new password on first login). Joy untouched (password_reset_by_user=true).
- BACKLOG P1 (owner-approved for a future release, not now): admin 'Disable password & send reset link' endpoint + button.
- Prod flags: RETENTION_ENGINE_ENABLED absent→OFF; GOOGLE_SIGNIN absent→ON; SAFETY_STATUS_WEBHOOK present, value unreadable by agent (owner to eyeball = false); ALIGN_WEBHOOK_SECRET absent.

## 2026-10-18 19:55 CDT — preview-only edits (NOT deployed)
- Owner (a) confirmed: Family check-in live; A/B/C removed (code only in safety_screening.py for legacy reads).
- SMS leftovers removed: SampleTour tooltip now says email alert; CourtThread '+ texted' suffix dropped.
- Owner 'say so': Family check-in intro card now shows the Professional Access Notice (from content/safetyEntry.js, same text as Step 0) + 'Read the privacy notification' link → /privacy-notice (data-testid screening-access-notice / screening-privacy-notice-link). Verified in browser.
- Owner 'echo here too': Family check-in page now also has the "I'd rather not answer these right now" button (SAFETY_HUB_DECLINE, shared source) next to Submit privately → POST …/safety-screening/decline (status+date only, no notification) → dashboard. Verified in browser (390px, no overflow).

## 2026-10-18 20:04 CDT — Family check-in amendments (PREVIEW ONLY, not deployed)
- Parts 'Strangulation and threats' and 'Weapons' removed from live set → fv_screening.LEGACY_ITEMS (legacy reads only); parts renumbered 1–6; compute() drops strangulation/threat_kill/weapon_* rules; amber_cluster now requires recent separation only.
- Footer 'owner specification' label removed (SPEC.source=None; frontend shows scale_note only for legacy versions).
- Full crisis box on check-in = FV_RESOURCES (7 entries, hours labelled, FJC after 24-hour lines, 911 last). Hotline component shows hours.
- Mandatory-reporting sentence removed from intro → fv_screening.MANDATORY_REPORTING_NOTE (restore by appending to PRIVACY_NOTE).
- Tests edited: test_iter110 (red/amber params, new test_removed_parts_never_served_and_never_score), test_iter111 (stalk instead of strangle; 'Followed' signal), test_iter112 (stalk). Safety suites 62 passed / 7 skipped.
- 20:1x CDT: owner 'restore' → mandatory-reporting sentence back in PRIVACY_NOTE; owner 'deploy' → deployment dispatched.

## 2026-10-18 ~20:30 CDT — Code review fixes (PREVIEW ONLY, not deployed; owner approved 1a + 2)
- 1a: receipt() no longer prints a tier in court/co-parent output; export scan now blocks 'Tier 1/2/3 —' and 'Tier not available'.
- 2: parent branch of screening_overview strips app_tier/app_tier_label/triggered_rules/tier/tier_label; public FV spec strips per-question weight/tier3.
- Tests: new test_review_fixes_no_tier_in_receipt_scan_or_parent_overview (iter111); iter87 (2 asserts) and iter88 (PDF needle) flipped from 'Tier 3 present' to 'Tier absent'. Safety suites green.

## 2026-10-19 — Stable check-in alias (PREVIEW ONLY; owner asked). A deployment was initiated from the platform UI by the owner (system notif), not by the agent.
- GET /api/me/check-in[?case=SA-…] (parents only; resolves signed-in parent's case, optional shared code, to {report_id, case_code, path}); frontend /check-in → redirects to /joint/<id>/safety-screening; friendly 404 message otherwise.
- Test: test_iter111::test_check_in_alias_resolves_by_session_and_shared_code. Browser-verified both forms + bad code.

## 2026-10-19 — STANDING RULE (owner, emphatic): Claude is NEVER an option in Legal Lens, and the Align Assistant has NO second-opinion model switch (GPT-5.5 only). Claude Sonnet 5.5 stays ONLY in the professional drafting tools (ai_tools.py). Do not re-add.
- Removed: claude from assistant.MODELS, legal_ai.MODELS, lens_data.AI_MODELS; Assistant header toggle replaced by static GPT-5.5 label. Tests updated (iter66, iter115). PREVIEW ONLY until owner says deploy.

## 2026-10-19 — Owner LIFTED the webhook test-ping pause ('i lift that explicitly'). Still: no secret in chat; SAFETY_STATUS_WEBHOOK stays false until a successful ping and a separate owner go-live. Procedure given: parent-app side generates fresh ALIGN_WEBHOOK_SECRET → owner enters same value in Align Deploy → Secrets → owner clicks Admin → Webhook check → 'Send signed test ping' on production.
