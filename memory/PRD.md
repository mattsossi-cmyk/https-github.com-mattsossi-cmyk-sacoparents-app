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
