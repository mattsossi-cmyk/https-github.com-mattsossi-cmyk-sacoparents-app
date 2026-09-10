# Code Review Notes — accepted patterns in this codebase

Reference for automated/manual review cycles. These are deliberate; do not flag or "fix" them.

## `is None` / `is not None` comparisons
All `is` comparisons in this codebase target the `None` singleton (verified across 5 review
rounds — e.g. server.py, joint_engine.py, and test files). This is correct Python (PEP 8).
Do NOT convert them to `==` / `!=`: that would be a regression, not a fix.

## End-to-end style test flows
Tests under `backend/tests/` model real user journeys (register → invite → accept → respond →
report). Sequential multi-step tests are intentional; they are kept readable via shared helpers
in `tests/casekit.py` and per-file `_assert_*` / `_submit_*` helpers. Splitting a single user
journey into inter-dependent micro-tests adds fragility without value.

## Fixture/test accounts
Test accounts use throwaway emails (@example.com, @testmail.dev, @x.com) and the shared
`E2E_TEST_PASSWORD` env-overridable constant in `tests/casekit.py`. These are self-destructing
fixtures, not secrets. The email provider blocks @example.com delivery by design; delivery is
verified with real controlled inboxes instead.

## server.py size
Pure helpers are extracted to `auth_utils.py` (password/JWT) and `email_utils.py` (delivery +
content safety). Route handlers stay in server.py by design; a router-level split is deferred
until the file grows further.

## Round (2026-09-08)
- "is vs ==" findings (server.py, email_utils.py, joint_engine.py): all are `is None` / `is not None` identity checks — correct Python, left unchanged.
- "Undefined variable" findings (invite_expired `created`, _matter_state `key/label`): false positives (early return / all branches assign). Rewritten anyway for scanner clarity.
- Complexity: run_expiry_digests 18→~3, register 13→~5, build_case_pdf 11→~2, list_connections 12→~3. radon: no functions ≥ C remaining in server.py/pdf_report.py.

## Round (2026-09-08, later)
- send_email complexity 11 → split into _email_payload / _post_email / _post_with_retry / _send_failure (all ≤ B).
- "is vs ==": all 15 flagged lines are `is None` / `is not None` — correct, unchanged (third time flagged; scanner false positive).
- Type hints added: test_iteration_22.py, test_password_reset.py, conftest.py. Unused test imports removed (ruff F401).
- server.py module split deferred: routes already delegate to auth_utils / email_utils / pdf_report / joint_engine / report_engine; further splitting is a larger refactor with no user-visible value right now.

## Round (2026-09-08, #4)
- "is vs ==" (server.py ×13, joint_engine.py, email_utils.py ×3): re-verified — every flagged line is `is None` / `is not None`, which the report itself says is the correct use of `is`. Unchanged.
- Type hints: test_report_shape.py, test_pdf_report.py, backend_test.py, test_pro_share_updates.py — all def signatures now annotated (0 unannotated).
- server.py import count: deferred (see previous round).

## Round (2026-09-08, #5) — "is vs ==" (25 occurrences)
Every one of the 25 flagged lines verified by direct inspection (server.py ×13, email_utils.py ×3, joint_engine.py ×1, tests ×8):
all are `is None` (14) or `is not None` (11). PEP 8 mandates `is`/`is not` for None comparisons; `== None` would be the anti-pattern.
No code change made. Fifth consecutive false-positive report for this rule — the scanner appears to flag any `is` operator.

## 2026-09-09 — Code review round 5 ("is vs ==", 25 locations)
- Every flagged line (server.py ×13, joint_engine.py:406, email_utils.py 57/61/85, 8 test lines) is `is None` / `is not None`.
  Verified with grep: zero comparisons of `is` against string/number literals exist in the codebase.
  `is None` is the PEP 8-mandated form; converting to `== None` would be a regression (E711). No changes made.

## 2026-09-09 — Code review round 6
- Removed ad-hoc helper tests/_setup_compare_case.py (0% type hints; unused). Added full type hints to tests/test_access_log.py (7 tests pass).
- "is vs ==": same 17 production lines — all `is None`/`is not None` (the report itself says to keep these). Unchanged.
- server.py import count / module split: deliberate decision not to refactor a 2,600-line working route file without a product reason; auth/email helpers already live in auth_utils.py / email_utils.py.

## 2026-09-10 — Code review round 7
- refer_to_professional complexity 11 → split into _referral_matter_line() and _referral_html(); directory tests 3/3.
- "is vs ==" (server.py ×14, joint_engine.py, email_utils.py, 8 tests): `ruff --select F632` passes on the whole backend — all are `is None`/`is not None`. Unchanged (7th recurrence).
- server.py module split: deliberately deferred (see round 6).
