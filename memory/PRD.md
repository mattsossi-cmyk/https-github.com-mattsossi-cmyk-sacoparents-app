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
