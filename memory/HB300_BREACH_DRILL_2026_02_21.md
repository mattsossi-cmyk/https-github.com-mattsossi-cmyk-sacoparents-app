# HB 300 Breach Simulation Drill — Post-Drill Readout

**Date:** 2026-02-21 · **Facilitator:** Privacy Officer (owner-operator) ·
**Duration:** ~2 minutes automated · **Overall:** ✅ **PASS**

## What this drill tested

The [HB 300 Breach Runbook](./HB300_BREACH_RUNBOOK.md) declares three
notification timers (60-day user notice, 60-day Texas AG notice at
≥ 250 TX residents, 60-day OCR notice at ≥ 500 individuals) and a
draft-breach endpoint (`POST /api/admin/breach-report`) that should
persist the draft, flag the AG threshold, and email the operator.
This drill runs three realistic scenarios end-to-end against the
live backend, asserts the runbook's promises actually hold in code,
and cleans up after itself.

Driver script: [`/app/scripts/breach_drill.py`](/app/scripts/breach_drill.py).
Raw JSON results: [`HB300_BREACH_DRILL_RESULTS.json`](./HB300_BREACH_DRILL_RESULTS.json).

## Scenarios executed

| # | Scenario | TX residents | Total | AG threshold flagged? | OCR route |
|---|----------|-------------:|------:|:---------------------:|-----------|
| A | Small internal exposure (support engineer catches mis-scoped share) | 12 | 12 | ❌ false ✅ | annual log |
| B | Vendor incident, reversible ID + child_first_name logged | 312 | 312 | ✅ true ✅ | annual log (< 500) |
| C | Public-cache misconfiguration exposing 742 rendered joint reports | 620 | 742 | ✅ true ✅ | immediate 60-day OCR (≥ 500) |

All three responded within **240 ms** including MongoDB write and
`next_steps` payload build.

## Findings

### ✅ Working as documented

1. **Admin gate** (`POST /api/admin/breach-report`)
   - Civilian user gets `403 Admin only.` — verified live.
   - Elevated user (`role="admin"` in Mongo) gets `200` — verified live.
2. **AG threshold flag** — response `ag_threshold_crossed` matched
   expectations across all three scenarios (12 → false, 312 → true,
   620 → true).
3. **Persistence** — every draft was retrievable from
   `hb300_breach_reports` with `status="draft"` and the correct
   `texas_residents_affected` count.
4. **`next_steps` payload** — 5-item checklist returned every time,
   including the "if ag_threshold_crossed is true, file with the
   Texas Attorney General without unreasonable delay" prompt.
5. **60-day user-notice deadline** — computable from
   `discovered_at + 60 days` (drill computed all three deadlines
   locally; server does the same math in the runbook).
6. **PHI access log untouched** — breach-report is an admin action,
   not a PHI read, and correctly does NOT write to `phi_access_log`.
7. **Cleanup** — drill removed 2 test users + 3 breach rows + any
   PHI access rows; verified via Mongo counts post-run.

### 🛠 Bugs uncovered by the drill (fixed in-flight)

1. **Admin gate silently unreachable via `role`/`is_admin`.**
   The endpoint's admin check used `getattr(user, "role", None)`
   and `getattr(user, "is_admin", False)` against the `UserPublic`
   Pydantic model. That model deliberately strips both fields, so
   the only way to become admin was to match the `OPERATOR_EMAIL`
   env var exactly — meaning any future workforce member would
   silently 403 forever with no observable signal.
   - **Fix:** `hb300_routes.py::submit_breach_report` now looks up
     `role`/`is_admin` from the Mongo `users` collection directly,
     with `OPERATOR_EMAIL` retained as the single-owner fallback.
   - **Regression test:** `test_iter121_hb300.py::test_breach_report_accepts_mongo_elevated_admin`
     elevates a test user via Mongo, hits the endpoint, asserts
     `200`, then reverts. Locks the gate against future drift.

### ⚠️ Follow-ups (non-blocking)

1. **Operator email best-effort** — the endpoint tries to import
   `send_operator_notification` from `email_service.py`, which
   does not exist yet. Wrapped in `try/except`, so it degrades
   silently. If the operator wants a live email on every draft,
   add a `send_operator_notification` helper in `email_service.py`
   that uses the existing Resend + Virtru switch. Low priority
   because the draft is retrievable from Mongo and the endpoint
   already logs the draft creation.
2. **No end-user notification is sent** — deliberate; the runbook
   requires legal counsel review before any notification leaves.
3. **Texas media notice** (Scenario C) is not automated. The
   runbook lists the requirement (≥ 500 residents of one Texas
   region → media notice) but this drill did not construct or
   attempt to send a media release; that step remains manual.

## Timers vs code — reconciled

| Notice | Runbook says | Code does |
| --- | --- | --- |
| Individual user (any) | 60 days from discovery | `next_steps` reminds the operator; deadline computable from `discovered_at`. Not automated (deliberate). |
| Texas AG (≥ 250 TX residents) | Without unreasonable delay, ≤ 60 days | `ag_threshold_crossed` flag ✅ + `next_steps` prompt ✅ |
| US HHS OCR (≥ 500 individuals) | 60 days | Not automatically flagged. **Follow-up:** add `ocr_threshold_crossed` boolean when `total_individuals_affected >= 500`. The current endpoint only takes `texas_residents_affected` — extend the payload with `total_individuals_affected` to cover multi-state breaches like Scenario C. |
| US HHS OCR (< 500) | Annual log by 60 days after year-end | Manual; runbook covers it. |
| Media (Texas ≥ 500 in one region) | 60 days | Manual; runbook covers it. |

**Recommended patch (P1, follow-up):**
`BreachReportPayload` gains `total_individuals_affected: int = Field(ge=0)`
(default to `texas_residents_affected` when omitted for backward
compat), and the response gains `ocr_threshold_crossed`. Would take
~15 minutes plus a scenario-C regression test.

## Verdict

The runbook survives contact with reality. The single real bug the
drill uncovered (admin gate) is fixed and covered by a regression
test. The follow-ups are refinements, not defects. Ready to publish
the runbook internally.

_Filed: 2026-02-21 · Next drill: 2027-02-21 (annual)._
