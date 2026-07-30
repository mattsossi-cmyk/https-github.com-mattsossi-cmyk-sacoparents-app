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

## Next step (Phase A of the rebuild)

User provided the full spec for the new **Special Needs Coparenting Assessment** (13 sections) and the full **Individual Parent Report** structure (17 sections). Both specs are captured verbatim in `/app/memory/SPECIAL_NEEDS_REBUILD_SPEC.md`.

### Confirmed decisions
1. **Phase A only next session:** backend schema + deterministic scoring + deterministic report content builder + pytest coverage. No frontend, no PDF, no invite/comparison.
2. **Section 11 (Family Violence):** captured privately, excluded from every general score, included in the parent's own report, redacted by default in any shared/comparison view, positives surface the standalone Family Violence Assessment.
3. **Scoring rules:** Sections 1 and 13 are context. Section 11 is safety-only. All multi-select / intake fields in Sections 3, 4, 7, 8, 9, 10, 11 are context. **Scored categories = Sections 2, 3, 4, 5, 6, 7, 8, 9, 10, 12** (10 rows). Section 6 consistency scale maps Consistent 5 · Mostly consistent 4 · Sometimes inconsistent 3 · Frequently inconsistent 2 · Unknown/NA excluded.
4. **Fresh names:** files `snc_questions.py` / `snc_scoring.py` / `snc_report_content.py`; API prefix `/api/snc`; collections `snc_assessments` / `snc_reports` / `snc_invites`; Phase B frontend route `/special-needs`; Phase C shared viewer `/shared/snc/:token`; Phase D invite `/invites/snc/:token`. `snc` = Special Needs Co-parenting.

### Phase A deliverables
- `backend/snc_questions.py` — full 13-section framework, verbatim question wording, response scales, meta-flags.
- `backend/snc_scoring.py` — deterministic scoring: 10 category averages 1–5 (N/A excluded); classification map (4.25–5.00 Established strength · 3.50–4.24 Generally supported · 2.75–3.49 Coordination opportunity · 2.00–2.74 Significant inconsistency · 1.00–1.99 Priority concern); Section 6 consistency-scale numeric map; Section 11 safety captured but never scored.
- `backend/snc_report_content.py` — deterministic Individual Parent Report matching the 17-section blueprint, with each section following the `response → finding → child impact → suggested option → action step` pattern. Must accept `include_safety: bool` (default True for own view, False for shared) and produce a fully populated report.
- `backend/tests/test_snc_scoring.py` and `backend/tests/test_snc_report.py` — thorough unit coverage.

### Test credentials
See `/app/memory/test_credentials.md`.
