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
