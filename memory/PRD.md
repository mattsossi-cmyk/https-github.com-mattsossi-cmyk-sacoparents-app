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





