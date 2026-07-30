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

## Next step (blocked on user approval)

User provided the full spec for the new **Special Needs Coparenting Assessment** (13 sections, mixed question types, Likert 1–5 + N/A, new rating classification, comparison-not-competition report rules, Section 11 pass-through to Family Violence Assessment). Rebuild scope must be confirmed with user before coding begins.

### New spec summary
- Sections 1, 3, 4, 9, 13 are hybrid intake + scored
- Sections 2, 5, 7, 8, 10, 12 are pure Likert 1–5
- Section 6 uses a consistency scale (Consistent → Frequently inconsistent)
- Section 11 is safety-sensitive and does NOT produce a score; positive answers direct the user to the standalone Family Violence Assessment
- Rating classification: `4.25–5.00 Established strength · 3.50–4.24 Generally supported · 2.75–3.49 Coordination opportunity · 2.00–2.74 Significant inconsistency · 1.00–1.99 Priority concern`
- Comparison report never labels a parent correct

### Test credentials
See `/app/memory/test_credentials.md`.
