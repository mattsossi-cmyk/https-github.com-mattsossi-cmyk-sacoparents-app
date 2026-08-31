# Joint Alignment Report — Integration Guide

This document is written for the agent working in the **sacoparentsapp.online** Emergent project.
It describes how to port the Joint Assessment / Joint Alignment Report module from this repository
into that app. The module is intentionally self-contained.

## What This Module Is

A universal 10-page **Joint Alignment Report** system: two parents each complete the same structured
assessment (10 topics, 5-point concern scale), and a rule-based engine generates a 10-page report
(alignment, differences in perspective, child needs, options, conversation questions, professional
discussion map, action plan worksheet, alignment summary). Eight assessment types: General
Co-Parenting, Communication, High-Conflict, IPV/Family Violence (safety-first variant), Medical,
Educational, Psychological/Behavioral, Preparing for Court.

## Files to Port (copy these)

### Backend — copy verbatim, no changes needed
| File | Contents |
|---|---|
| `backend/assessment_data.py` | All 8 assessment type configs: topics, questions, scales, options, child needs, page titles, disclaimers, demo payloads. No dependencies. |
| `backend/report_engine.py` | `generate_report(case)` — pure rule-based function, takes a case dict, returns the full report JSON. Imports only from `assessment_data`. |

### Backend — port the routes, adapt auth
From `backend/server.py`, copy ONLY these route groups into the target app's router:
- `GET  /api/assessment-types` and `GET /api/assessment-types/{key}` — static config, no auth changes needed.
- `POST /api/cases`, `GET /api/cases`, `GET /api/cases/{id}`, `PUT /api/cases/{id}/responses/{a|b}`, `POST /api/cases/{id}/demo`, `GET /api/cases/{id}/report`, `DELETE /api/cases/{id}` — replace `get_current_user` with the target app's existing auth dependency, and `user["_id"]` with the target app's user id field. Cases are stored in a `cases` MongoDB collection with a string `id` (uuid), `user_id`, `type`, `child_name`, `parent_a_name`, `parent_b_name`, `responses: {a, b}`, `is_demo`, `created_at`.

**DO NOT copy** the auth routes (`/api/auth/*`), JWT helpers, bcrypt code, admin seeding, or CORS setup — the target app already has its own auth. Reuse it.

### Frontend — port and restyle
| File | Role |
|---|---|
| `frontend/src/pages/Wizard.jsx` | 4-step intake: choose type → case details → Parent A form → Parent B form. Includes `ParentForm` component (radio scale per topic, primary concern textarea, shared-goals checkboxes) and demo-data buttons. |
| `frontend/src/pages/ReportView.jsx` | Report viewer shell: page navigation (dots/prev/next), print button, print-only container rendering all 10 pages. |
| `frontend/src/components/report/Pages.jsx` | The 10 report page components (`REPORT_PAGES` array). Consumes the report JSON directly. |
| `frontend/src/components/report/Paper.jsx` | Paper shell, `Snapshot` donut chart (uses recharts), `PullQuote`, `StatusDot`, `SectionHeading`. |

**DO NOT copy** `Landing.jsx`, `Auth.jsx`, `AuthContext.jsx`, or `lib/api.js` verbatim — adapt API calls to the target app's existing API client/auth context. Skip this app's auth pages entirely.

## Frontend Dependencies to Check
- `recharts` (snapshot donut) — `yarn add recharts` if missing.
- `lucide-react`, `sonner`, shadcn `button/input/label/textarea/checkbox/radio-group` — already standard in Emergent templates.

## Styles to Port
From `frontend/src/index.css`: the `.report-paper`, `.report-page-enter`, `@keyframes pageFade`, `.worksheet-line`, `.print-only`, and the `@media print` block (critical for print/PDF output).
From `frontend/tailwind.config.js`: the `align` color tokens (`green #668B69`, `yellow #D4B46A`, `blue #6096BA`, `purple #9A8C98`) used for status colors (`text-align-green`, `bg-align-purple`, etc.). Adapt hex values if the target app's palette differs.

## Report JSON Contract
`GET /api/cases/{id}/report` returns everything `Pages.jsx` needs: `page_titles[10]`, `disclaimer`, `snapshot {total, aligned, different, info}`, `shared_goals[]`, `parent_a_concern`, `parent_b_concern`, `central_question`, `alignments[{topic, text}]`, `differences[{topic, parent_a, parent_b}]`, `child_needs[{title, text}]`, `options[]`, `conversation_questions[]`, `professional_map`, `action_plan[{issue, child_need, already_agree}]`, `summary {aligned, info, conversation, options, priority}`, `court_map` (court type only), `philosophy`, `is_demo`. If you change the backend shape, update the page components to match.

## Content Rules (important — preserve these when editing)
- Differences are "differences in perspective", never conflicts/failures/discrepancies.
- Options are "options for parents to explore", never recommendations.
- Psychological report: describe parental observations, never diagnose.
- IPV report: safety first — "Agreement between parents is not the measure of success where safety is a concern."
- Every report ends with: "We value the parenting system by how well it supports the child, not by how friendly the adults appear."

## Suggested Integration Order
1. Copy the two backend module files; add routes; wire to existing auth. Verify with curl (`demo` → `report`).
2. Add the frontend pages behind a route (e.g., `/joint-assessments`), adapt API calls, add nav link.
3. Restyle to the target app's design system.
4. Test end-to-end: create case → demo data → all 10 pages → print.

## Test Credentials in This Repo
See `/app/memory/test_credentials.md` (admin: mattsossi@bsossi.com). Not needed after the port — the target app's own users/auth apply.
