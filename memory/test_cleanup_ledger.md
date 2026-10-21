# Backend test cleanup ledger (2026-10-20, PREVIEW ONLY)

Command: `cd /app/backend && REACT_APP_BACKEND_URL=<preview> python -m pytest tests -q -p no:cacheprovider`
(2218 tests, ~27 min, run in background; never `-n`, pytest-xdist is not installed).

| Run | Result |
|---|---|
| Baseline | 46 failed, 2151 passed, 32 skipped, 1 xfailed |
| Run 2 | 1 failed, 2197 passed, 32 skipped, 1 xfailed (the 1 = leftover users from my own first draft of a test; removed) |
| Run 3 (final) | **0 failed, 2203 passed, 26 skipped** (25m11s); report test_reports/pytest/full_run3.xml |

## The 46 failures and what was done

| Tests | Cause | Fix |
|---|---|---|
| test_coach (5), backend_test TestAI (3), test_email_mediator (1) | Signed-in test user never accepted the AI notice → 428 | conftest `test_user` accepts the Privacy Notice + AI notice after register (tests/ai_ready.py) |
| test_iter111 ChildNeedsSuggest (2), test_journey_summary_pp chat (1) | Same 428 | Their fresh-user fixtures accept the AI notice |
| test_iter130 (3), test_iter132 (6) | In-process fake user had `ai_notice_current=False` → 428 | Fake user sets `consent_current=True, ai_notice_current=True` |
| test_self_assessment_ai (9), test_court_path_ai (2) | AI routes now need sign-in → 401 | Tests sign in parent1 + accept the AI notice |
| backend_test test_issues_save | Old payload shape + expected the retired safety text back | Uses `items/other`; asserts new safety text is dropped and never returned |
| backend_test test_resources_listed | Expected 6 resources, app has 8 | Asserts at least 6 with unique ids |
| backend_test test_summary_and_pdf | Expected old `child_goals_summary` key | Expects current `executive_summary` |
| test_iter155 PDF author line | PDF redesign says "Completed by Sam Parent" | Assertion updated |
| test_iter194 analytics | Counted rows left by test_iter195 | Uses its own scratch database; test_iter195 now also cleans up after itself |
| test_iter223 nudge worker (2) | Seeded the hidden "foundation" topic (never nudged) on parent1 | Throwaway user + visible "coparenting" topic |
| test_med_deep page count | REAL BUG: the "How this report was built" block split across 6 near-blank pages | pdf_provenance.py breaks the page before a row that won't fit |
| test_password_reset (4) | Test helper treated a tuple as a database | Helper fixed |
| test_journey_summary_pp celebration | Child Needs save needs the notice tick | Sends `acknowledged: true` |
| test_iter94 (2) | One-off network timeout | Passed on re-run, no change |

## Real app issue found
- guided_draft_nudge.py: the unfinished-draft email still went to parents with an old safety result (every other reminder already
  skipped them). Now it uses `is_safety_flagged` (old result, lifted by a named professional = sends again). New test:
  `test_old_safety_result_holds_the_nudge`.

## Former run-time skips/xfail turned into real checks
- test_iter222 biff_refine: own client address instead of skipping on 429.
- test_iter43 Co-Parenting share label: used a removed `/reports` route; now `/coparenting/report`.
- test_journal prompt: xfail → asserts the daily prompt is public (generic text, no account data).
- test_journal weekly recap: user accepts the AI notice, so the AI recap really runs.
- test_snc2_iter38: asserts an old Level 1 result never feeds the SNC report.
- test_iter115 mediator-email (2): removed; the old safety email route is retired and its 404 is checked in test_align_safety_step.py.

## Skipped on purpose (one line each)
- 8 modules (test_safety_gate, _external, _live, _iter144_full, test_align_status_external, test_family_checkin_iter145/146/147):
  need ALIGN_WEBHOOK_SECRET, which you chose to leave unset in preview. The same rules are checked in-process by
  test_safety_gate_correction.py (no secret).
- 4 modules (test_edu_deep, test_edu_deep_live, test_psych_deep, test_psych_deep_api): v1 questionnaires retired; v2 is tested by
  test_iter67_edu_v2.py / test_iter70_psych_v2.py.
- test_iter144_safety_gate_on_invites (12) and test_iter149 (2): old in-app Safety Assessment retired; replaced by
  test_align_safety_step.py.

## Supervised webhook run (2026-10-20, preview only)
- A temporary ALIGN_WEBHOOK_SECRET was written to preview backend/.env (never shown), backend restarted, the 8 webhook files run, then the
  key was removed and the backend restarted. Afterwards: webhook POST -> 503, tests/test_webhook_off.py 3 passed, .env keys same as before.
- First pass: 64 passed, 9 failed, 44 skipped. The 9 were outdated tests (fixed): refusal counters now include no_professional_name /
  auto_red_refused; checklist PDF shows "Safety step: completed on SACOparentsAlign" once Align marks it done; audit write row is
  actor_type "professional"; check-in link returns the shared case_id (never align_ref); bad-signature check compares flags to before.
- Second pass: 84 passed, 0 failed, 44 skipped (auto_red tests, rule removed 2026-10-19; covered by test_safety_gate_correction.py).
- With the webhook off again these 8 files skip themselves (by design).

## Final full run after the 5-item spec (2026-10-20)
- 2230 tests: 2215 passed, 26 skipped, 1 failed. The failure was a 30 s network timeout through the preview proxy
  (test_iter161 bot/human opens); the file passed 11/11 on rerun. Earlier transient timeouts (test_align_safety_step x2) also pass on rerun.
- test_password_reset rate-limit test now uses one fixed client address (was flaky when proxy addresses varied).
- New: tests/test_align_share.py (7), tests/test_held_emails.py (7), frontend src/lib/accessLogHref.test.js (5).

## Final full run, 2026-10-21 (after notice v8 + linked-only sharing)
- 2245 tests: 2216 passed, 26 skipped, 3 failed. All 3 = ConnectTimeout (test machine could not reach the preview address):
  test_guest_autobootstrap::test_login_parent1, test_iter184::test_child_needs_consent_toggle..., test_iter_court_agreements::test_pdf_with_agreements.
  Re-run of those 3 files: 33 passed, 0 failed. Log: test_reports/pytest/full_run6.log / full_run6.xml.
