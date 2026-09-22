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
