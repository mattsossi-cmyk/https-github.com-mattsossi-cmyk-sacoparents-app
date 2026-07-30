# SA CoParents — PRD (post-demolition, pre-rebuild of Special Needs)

## Status snapshot (2026-07-30)

The Special Needs Co-Parenting Assessment and Report have been **completely removed** at user request. The Special Needs product is being reworked from scratch against a new 13-section framework the user has now provided.

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
- Family Report (now composes only CP + Safety)
- All auth, invites, gmail, coach, insights, admin, next-steps for the four remaining assessments

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
- Dashboard card + landing/methodology mentions restored (with new naming).

### Phase C deliverables (later)
- PDF renderer.
- Share link + public viewer at `/shared/snc/:token`.

### Phase D deliverables (later)
- Invite/accept flow at `/invites/snc/:token`.
- Comparison view (never labels a parent correct; Section 12 always redacted).

### Test credentials
See `/app/memory/test_credentials.md`.
