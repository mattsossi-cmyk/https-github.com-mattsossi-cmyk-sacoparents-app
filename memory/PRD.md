# SA CoParents — PRD

## Status snapshot (2026-07-30 · v2 shipped)

- **Family Report:** fully removed at user request.
- **Special Needs Co-Parenting v1** (13-section flat product): fully deleted per user's "replace it" directive. Backend routes `/api/snc/*`, frontend `/special-needs*` pages, comparison + invite endpoints, associated tests, sample PDFs, and MongoDB collections `snc_assessments`, `snc_reports`, `snc_invites`, `snc_comparisons` all removed.
- **Special Needs Co-Parenting v2** shipped at `/special-needs-v2`. Category-gated (Medical / Educational / Psychological or Behavioural / Multiple) 8-step assessment. **Report reshaped (2026-07-30) to the 9-section polished framework**: Report Introduction · Family Situation · Areas of Need · Co-Parenting Strengths · Co-Parenting Challenges (4-part cards) · Child Impact Summary · Detailed Findings by Category (Strength / Developing / Needs Attention / Priority Concern / Professional Guidance Recommended status system) · Parent Alignment Summary · Recommended Co-Parenting Structure (Cooperative / Structured / Parallel or Professionally Supported — safety-aware).
- **Mobile UX**: assessment is fully phone-usable — 5-column numeric rating buttons, sticky bottom Prev/Save/Next nav, 44 px+ tap targets, high-contrast selected states.
- **Landing situation picker (2026-07-30)**: added new option "I have concerns for my child's educational, medical or psychological needs" that starts a guest session and routes directly to `/special-needs-v2` (icon: Baby; testid `situation-special-needs`; focus key `special-needs`).
- **SNC v2 Co-Parent Compare (2026-07-30)** shipped. New backend module `snc2_comparison.py` (neutral alignment builder), `snc2_comparison_pdf.py` (branded PDF), `snc2_comparison_routes.py` mounted at `/api/snc2/compare/*`. Consent-first: both parents must opt in; safety guardrail hard-blocks any consent or view when the requesting parent's latest Safety Assessment is level 1 or 2 (reads `result.level` from `safety_assessments`). Frontend pages `SpecialNeedsV2Compare.jsx` (hub) and `SpecialNeedsV2CompareView.jsx` (view + category filter + PDF download); entry buttons on the assessment page and the report page (testids `snc2-open-compare`, `snc2-report-open-compare`). New Mongo collection `snc2_shares`. Tests: `tests/test_snc2_comparison.py` (9) + `tests/test_snc2_compare_api.py` (18) — all passing after testing agent caught + fixed a critical nested-field bug in `_latest_safety_level` that had left all three safety guardrails fail-open.
- **SNC v2 Compare Highlights (2026-07-30)** shipped. Added a "5 things you already agree on" section to the top of the shared comparison — surfaces in the JSON payload (`comparison.highlights[]`), the branded PDF, and the frontend view (data-testid `snc2-compare-highlights` + `snc2-compare-highlight-{i}`). Neutral scoring rules: only items with real shared agreement (likert avg >=3 + gap <=1, multi-select with shared choices, matching single-selects, or both-parents-wrote-text) qualify; later workflow steps rank slightly higher.
- **SNC v2 Enhancements Bundle (2026-07-30)** — four enhancements shipped together:
  * **Sample buttons** on `/special-needs-v2` picker (testids `snc2-samples-block`, `snc2-sample-assessment`, `snc2-sample-report`, `snc2-sample-comparison`) linking to the 3 static sample PDFs.
  * **Safety Recommend guardrail** — `snc2_report_content._s9_recommended_structure(safety_level=...)` HARD-OVERRIDES recommendation to `parallel_or_supported` for Safety level 1 and to at least `structured` for level 2, regardless of score. `snc2_routes` reads the latest safety level per user and stores `safety_level_at_generation` on the cached report; `_is_stale` now considers a changed safety level so cache invalidates on new safety filings.
  * **Email My Report** — `POST /api/snc2/report/email` builds the PDF and sends it via new `email_service.send_snc_report_pdf` (Resend + attachment). Frontend button `snc2-report-email` on the report page.
  * **Growth Wins Dashboard card** — `GET /api/snc2/compare/dashboard/highlights` returns top-5 highlights from the parent's most-recent active ready comparison (safety-guardrail-aware). Frontend card `dashboard-snc-highlights` on `/dashboard` with a "See the full comparison" CTA linking to the compare view.
  * Tests: 11 new in `tests/test_snc2_enhancements.py` + 3 new safety-override unit tests in `test_snc2.py` — **61/61 SNC v2 tests passing** with iteration-36's `_latest_safety_level` fix intact.
- **Email delivery**: Resend `RESEND_FROM_EMAIL` switched to the verified `mattsossi@mattsossi.sacoparentsapp.online` subdomain — outbound email now delivering. Root `sacoparentsapp.online` domain still failed at Resend; add DKIM/SPF/MX records to verify it and switch the FROM back for cleaner branding.
- **Retained products**: Co-Parenting Assessment + Report (+ share links), Family Violence & Communication Safety Assessment + Report, auth, invites (general co-parent), gmail, coach, insights, admin, next-steps.

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

## Existing (retained) products & endpoints

- **Auth**: `/api/auth/*` (JWT + Emergent Google Auth)
- **Co-Parenting**: `/api/coparenting/*`
- **Safety**: `/api/safety-assessment/*`
- **Invites (general)**: `/api/invites/*`
- **Coach**: `/api/coach/*`
- **Insights / admin**: `/api/insights/*`

## Test credentials
See `/app/memory/test_credentials.md`.
