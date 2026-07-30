# SA CoParents — PRD (SNC Phase B/C shipped)

## Status snapshot (2026-07-30 · updated)

- **Family Report:** fully removed at user request (this session).
- **Special Needs Co-Parenting (SNC):** Phase A + Phase C shipped previously; Phase B (persistence, routes, cached report, save-and-resume) + frontend (assessment, report, dashboard card, PDF download, regenerate) now shipped in this session. Testing agent iteration 33 — backend 19/19 API tests pass, frontend flows verified.

### Files added (backend) — SNC Phase B 2026-07-30
- `backend/snc_routes.py` — full `/api/snc` router (schema, me, answer, answers/bulk, complete, scores, report/status, report/generate, report/regenerate, report, report/pdf, report/email, DELETE /me)
- `backend/tests/test_snc_api.py` — 19 API tests, all pass
- Registered `snc_router` in `server.py`; MongoDB collections `snc_assessments` and `snc_reports` (indexed by `user_id`)
- Updated `snc_report_pdf.py` header to include the shared SA CoParents branded logo band (matches co-parenting / safety PDFs)
- Extended `email_service.py` with `send_snc_report_ready()` — SA CoParents branded email with the PDF attached; one-time send on first successful report generation, and a manual "Email me the PDF" endpoint (`POST /api/snc/report/email`)
- Report cache now tracks `notified_at`; the "your report is ready" email is only sent the first time a cached report is created for a parent (regenerate does NOT re-notify)
- **Known deployment blocker (not code):** Resend send fails with `The sacoparentsapp.online domain is not verified` — same root cause affects the existing survey-reminder emails. `POST /api/snc/report/email` returns `{"sent": false, "reason": "…"}` cleanly and the UI surfaces that as a toast. Fix: verify the sender domain in Resend at https://resend.com/domains.

### Files added (frontend) — SNC Phase B 2026-07-30
- `frontend/src/pages/SpecialNeedsCoParenting.jsx` — 13-section assessment, autosave, progress bar, section navigator, Save-and-come-back button, Complete + auto-generate
- `frontend/src/pages/SpecialNeedsReport.jsx` — 17-section report render, "Last generated · Regenerate", "Download PDF", "Email me the PDF" (uses the new report/email endpoint), safety block with automatic referral to the full Safety Assessment
- `App.js` — routes `/special-needs` and `/special-needs/report` (both `ProtectedRoute`)
- `Dashboard.jsx` — new `[data-testid=dashboard-snc-card]` with cached-report status, links to assessment or report based on state

### Files removed (backend) — Family Report demolition 2026-07-30
- `backend/family_report_content.py`, `family_report_pdf.py`, `family_report_routes.py`
- `backend/tests/test_family_report.py`
- Removed `/api/insights/family-report-dynamic-sample.{pdf,png}` (+ thumb) endpoints
- Unregistered `family_report_router` from `server.py`
- MongoDB collection `family_reports` dropped

### Files removed (frontend) — Family Report demolition 2026-07-30
- `frontend/src/pages/FamilyReport.jsx`, `SharedFamilyReport.jsx`
- `frontend/src/components/FamilyReportBody.jsx`
- Removed `/family-report` and `/shared/family/:token` routes from `App.js`
- Removed the "Family Report" dashboard card + `FileHeart` icon import from `Dashboard.jsx`
- Removed `public/downloads/sacoparents-family-report-*` samples (PDF, PNG, JPG, thumbs)

### What remains untouched after Family Report removal
- Co-Parenting Assessment + Report (+ its own share links + dynamic sample)
- Family Violence & Communication Safety Assessment + Report
- SNC Phase A + Phase C core (questions, scoring, report content, PDF renderer, sample PDF)
- Auth, invites, gmail, coach, insights, admin, next-steps

---

## Prior demolition record — Special Needs (retained for history)

### Files removed (backend)
- `sn_v3_questions.py`, `sn_v3_scoring.py`, `sn_v3_routes.py`, `sn_v3_report_content.py`, `sn_v3_report_pdf.py`, `sn_report_pdf.py`
- `special_needs_questions.py`, `special_needs_scoring.py`
- `neurodivergent_routes.py`, `sn_pathway.py`
- `scripts/regen_sn_sample.py`
- `tests/test_sn_v3_*.py`, `tests/test_sn_pathway*.py`, `tests/test_phase2_share_endpoints.py`

### Files removed (frontend)
- `pages/SpecialNeedsV3.jsx`, `pages/SharedSpecialNeedsReport.jsx`, `pages/SpecialNeedsInviteAccept.jsx`
- `pages/Neurodivergent.jsx`, `pages/NeurodivergentReports.jsx`
- `components/SpecialNeedsScoreDashboard.jsx`
- `public/special-needs-report.html`
- `public/downloads/sacoparents-special-needs*.pdf/.png`, `parent1-special-needs-report.pdf`

### Files updated (wiring cleaned)
- `backend/server.py` — SN routers unregistered
- `backend/family_report_content.py`, `family_report_pdf.py`, `family_report_routes.py` — Family Report composes CP + Safety only
- `backend/next_steps_routes.py` — `special_needs` handler stubbed out
- `backend/insights_routes.py` — sample endpoints removed
- `backend/report_visibility.py` — `sn_v3_report` entry removed
- `backend/tests/test_family_report.py` — CP + Safety only
- `frontend/src/App.js` — SN routes/imports removed
- `frontend/src/pages/Dashboard.jsx` — SN cards + neurodivergent data fetching removed
- `frontend/src/components/FamilyReportBody.jsx`, `FivePillarJourney.jsx`, `NextStepJourney.jsx`, `PickerChoicePill.jsx` — SN entries removed
- `frontend/src/pages/Landing.jsx`, `Methodology.jsx`, `NextSteps.jsx`, `SafetyAssessment.jsx` — SN mentions removed
- `frontend/src/lib/methodology.js` — special_needs entry removed

### MongoDB collections dropped
- `sn_v3_assessments`, `sn_v3_reports`, `sn_v3_invites`, `nd_prep`, `nd_reports`, `sn_v2_reports`

### What remains untouched
- Co-Parenting Assessment + Report (backend, dynamic report, PDF, share links)
- Family Violence & Communication Safety Assessment + Report
- All auth, invites, gmail, coach, insights, admin, next-steps for the remaining assessments

### Tests still passing
- 26/26 relevant backend tests (family_report, cp_report, coparenting_scoring, report_visibility).
- Backend running clean, `/api/health` = 200.

## Next step (Phase B of the rebuild)

Phase A landed on 2026-07-30. The next session picks up with the React assessment flow at `/special-needs`.

### Phase A delivered
- `backend/snc_questions.py` — 13-section framework, verbatim question wording, response scales, meta-flags. Assertion in module guarantees `SCORED_CATEGORY_IDS == (s2..s10, s12)`.
- `backend/snc_scoring.py` — deterministic 1–5 averaging, classification tiers 4.25/3.50/2.75/2.00, Section 6 consistency mapping 5→2 (Unknown/NA excluded), Section 11 safety captured separately with levels {unanswered, clear, declined, concerns}.
- `backend/snc_report_content.py` — 17-section Individual Parent Report with the required `response → finding → child impact → suggested option → action step` pattern for every scored section, auto-derived Section 16 "Questions for the Other Parent", 30-day step list, Section 15 Action Plan sourced from the lowest-scoring categories, closing summary. `include_safety=False` fully redacts Report Section 12.
- `backend/tests/test_snc_scoring.py` and `backend/tests/test_snc_report.py` — 25 tests, all passing.

**Total scored items**: 92 (Sections 2 8 + 3 9 + 4 10 + 5 10 + 6 12 + 7 8 + 8 8 + 9 10 + 10 7 + 12 10).

### Phase B deliverables
- FastAPI routes at `/api/snc` (schema, answers, complete, generate report, etc.).
- MongoDB collections: `snc_assessments`, `snc_reports`.
- React assessment page at `/special-needs` (intake → 13 sections → completion → individual report).
- **Save-and-resume from day one (user-approved 2026-07-30):**
  - Server-side autosave every time a field changes (debounced, batched by section).
  - Resumable progress meter that shows overall progress AND per-section progress.
  - Explicit "Save & come back later" checkpoints at the end of each section (13 checkpoints).
  - On return, the flow jumps to the first unfinished section (not the beginning).
  - Optional weekly reminder email if the user hasn't finished within 7 days (opt-in, off by default).
- Dashboard card + landing/methodology mentions restored (with new naming).

### Phase C partial — PDF renderer landed
- `backend/snc_report_pdf.py` — full 17-section Individual Parent Report renderer built on FPDF. Uses `pdf.epw` explicit widths and `set_x(l_margin)` before every multi_cell to stay resilient to prior cursor positions. Sample profile renders to ~41KB / multi-page.
- Safety redaction verified end-to-end: the same `include_safety` flag threaded through `build_individual_report()` produces PDFs that strictly omit Section 12 flag/safeguard text in the shared view.
- `backend/tests/test_snc_report_pdf.py` — **6 tests** covering signature/size, empty-answers rendering, safety redaction (both directions), absence of old vocabulary, presence of all 17 report section markers, and no judgemental phrases (`is wrong`, `better parent`, etc.).
- Sample PDF at `/app/frontend/public/downloads/snc-sample-individual-report.pdf` (accessible via the preview URL) uses a curated mixed profile so every classification tier appears.

### Phase C remaining (share link + public viewer) — next session
- FastAPI routes under `/api/snc` for share-link generation and shared-report fetch (JSON + PDF).
- Signed share tokens with visibility exclusion controls (mirror `report_visibility.py` pattern).
- React public viewer at `/shared/snc/:token`.
- Register SNC in `report_visibility.py` REPORT_SECTIONS with the correct section keys (`at_a_glance`, `category_summary`, `sections`, `action_plan`, etc.).

### Phase D deliverables (later)
- Invite/accept flow at `/invites/snc/:token`.
- Comparison view (never labels a parent correct; Section 12 always redacted).

### Test credentials
See `/app/memory/test_credentials.md`.
