"""
Iter115 — Align lock + unlink + safety redaction + mediator email include_answers.

Covers the backend tasks of iteration 115:
  * GET/DELETE /api/integrations/align-link + auth gates
  * export-assessments / foundation-statement.pdf return 404 for unlinked
    parents (same body as unknown emails) and 200 for linked parents, with
    last_read_at updated via align_access_log inserts.
  * A parent with an older concerning result gets the same reply as one with
    nothing saved yet, with no safety flag (see test_align_safety_step.py).
  * Migration helper leaves an unlinked parent unlinked after restart.
  * Mediator email endpoint accepts include_answers and records it.
"""
import os
import re
import time
from pathlib import Path

import pytest
import requests

# --- env ------------------------------------------------------------------
def _read_frontend_env(key: str) -> str:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"{key} not in /app/frontend/.env")


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env("REACT_APP_BACKEND_URL")
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


def _read_env_val(key: str) -> str:
    for line in Path("/app/backend/.env").read_text().splitlines():
        if line.startswith(f"{key}="):
            v = line.split("=", 1)[1].strip()
            # strip wrapping quotes (double or single)
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            return v
    raise RuntimeError(f"{key} not in /app/backend/.env")


INTEGRATION_KEY = _read_env_val("INTEGRATION_SHARED_SECRET")
PARENT1 = "parent1@test.com"
PARENT2 = "parent2@test.com"
PASSWORD = "TestPass123!"


# --- fixtures -------------------------------------------------------------
@pytest.fixture(scope="session")
def s() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def _login(s: requests.Session, email: str) -> str:
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, (email, r.status_code, r.text[:200])
    return r.json().get("access_token") or r.json()["token"]


@pytest.fixture(scope="session")
def tok_p1(s):
    return _login(s, PARENT1)


@pytest.fixture(scope="session")
def tok_p2(s):
    return _login(s, PARENT2)


def _h(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _ik() -> dict:
    return {"X-Integration-Key": INTEGRATION_KEY, "Content-Type": "application/json"}


# --- helpers --------------------------------------------------------------
def _ensure_parent2_unlinked(s, tok_p2):
    r = s.delete(f"{API}/integrations/align-link", headers=_h(tok_p2), timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["linked"] is False


def _ensure_parent1_linked(s, tok_p1):
    # Mint and verify a code so parent1 is linked. Safe to re-run — _record_link upserts.
    r = s.post(f"{API}/link-codes", headers=_h(tok_p1), json={}, timeout=30)
    if r.status_code == 403:
        pytest.skip(f"parent1 not safety-cleared enough to mint link code: {r.text[:200]}")
    assert r.status_code == 200, r.text[:300]
    code = r.json()["code"]
    r2 = s.post(f"{API}/integrations/verify-link-code", headers=_ik(), json={"code": code}, timeout=30)
    assert r2.status_code == 200, r2.text[:300]


# --- Auth gating ----------------------------------------------------------
class TestAuthGating:
    def test_align_link_requires_auth(self, s):
        r = s.get(f"{API}/integrations/align-link", timeout=20)
        assert r.status_code in (401, 403)

    def test_align_unlink_requires_auth(self, s):
        r = s.delete(f"{API}/integrations/align-link", timeout=20)
        assert r.status_code in (401, 403)

    def test_export_requires_integration_key(self, s):
        r = s.get(f"{API}/integrations/export-assessments", params={"email": PARENT2}, timeout=20)
        assert r.status_code in (401, 403)


# --- Unlinked parent returns 404 (same body as unknown) -------------------
class TestUnlinkedReturns404:
    def test_setup_unlink_parent2(self, s, tok_p2):
        _ensure_parent2_unlinked(s, tok_p2)
        r = s.get(f"{API}/integrations/align-link", headers=_h(tok_p2), timeout=20)
        assert r.status_code == 200
        assert r.json()["linked"] is False

    def test_export_unlinked_parent_404(self, s):
        r = s.get(
            f"{API}/integrations/export-assessments",
            params={"email": PARENT2},
            headers=_ik(),
            timeout=20,
        )
        assert r.status_code == 404
        assert r.json().get("detail") == "No linked parent found"

    def test_export_unknown_email_same_body(self, s):
        r = s.get(
            f"{API}/integrations/export-assessments",
            params={"email": "nobody-xyz@example.invalid"},
            headers=_ik(),
            timeout=20,
        )
        assert r.status_code == 404
        assert r.json().get("detail") == "No linked parent found"

    def test_foundation_pdf_unlinked_404(self, s):
        r = s.get(
            f"{API}/integrations/foundation-statement.pdf",
            params={"email": PARENT2},
            headers={"X-Integration-Key": INTEGRATION_KEY},
            timeout=20,
        )
        assert r.status_code == 404


# --- Link flow + last_read_at updates ------------------------------------
class TestLinkFlowParent2:
    def test_mint_verify_and_export(self, s, tok_p2):
        _ensure_parent2_unlinked(s, tok_p2)
        r = s.post(f"{API}/link-codes", headers=_h(tok_p2), json={}, timeout=30)
        if r.status_code == 403:
            pytest.skip(f"parent2 safety screen not cleared: {r.text[:300]}")
        assert r.status_code == 200, r.text[:300]
        code = r.json()["code"]
        assert re.match(r"^SA-\d{6}$", code), code

        # Align verifies the code (server-to-server).
        r2 = s.post(f"{API}/integrations/verify-link-code", headers=_ik(), json={"code": code}, timeout=30)
        assert r2.status_code == 200, r2.text[:300]
        assert r2.json()["email"].lower() == PARENT2

        # Parent sees linked state.
        r3 = s.get(f"{API}/integrations/align-link", headers=_h(tok_p2), timeout=20)
        assert r3.status_code == 200
        body = r3.json()
        assert body["linked"] is True
        assert body["linked_at"] is not None

        # Export returns 200 and never carries a safety flag.
        r4 = s.get(
            f"{API}/integrations/export-assessments",
            params={"email": PARENT2},
            headers=_ik(),
            timeout=30,
        )
        assert r4.status_code == 200, r4.text[:300]
        exp = r4.json()
        assert "redacted_for_safety" not in exp
        assert exp["parent"]["email"].lower() == PARENT2

        # last_read_at should now be populated (align_access_log inserted on export).
        time.sleep(0.3)
        r5 = s.get(f"{API}/integrations/align-link", headers=_h(tok_p2), timeout=20)
        assert r5.status_code == 200
        after = r5.json()
        assert after["last_read_at"] is not None, after

    def test_unlink_then_404_again(self, s, tok_p2):
        r = s.delete(f"{API}/integrations/align-link", headers=_h(tok_p2), timeout=20)
        assert r.status_code == 200
        assert r.json()["linked"] is False

        r2 = s.get(
            f"{API}/integrations/export-assessments",
            params={"email": PARENT2},
            headers=_ik(),
            timeout=20,
        )
        assert r2.status_code == 404
        assert r2.json().get("detail") == "No linked parent found"


# --- Held back for an older concerning result: same as nothing saved, no flag ---
class TestSafetyRedaction:
    def test_parent1_linked_export_has_no_safety_flag(self, s, tok_p1):
        _ensure_parent1_linked(s, tok_p1)
        r = s.get(
            f"{API}/integrations/export-assessments",
            params={"email": PARENT1},
            headers=_ik(),
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        exp = r.json()
        assert "redacted_for_safety" not in exp
        assert "safety" not in r.text.lower()

    def test_parent1_foundation_pdf_never_says_why(self, s):
        r = s.get(
            f"{API}/integrations/foundation-statement.pdf",
            params={"email": PARENT1},
            headers={"X-Integration-Key": INTEGRATION_KEY},
            timeout=20,
        )
        assert r.status_code in (200, 409), (r.status_code, r.text[:200])
        if r.status_code == 409:
            assert "safety" not in r.text.lower() and "not available" not in r.text.lower()

    def test_parent1_stays_linked_at_end(self, s, tok_p1):
        # Explicitly do NOT unlink parent1. Just verify state is linked.
        r = s.get(f"{API}/integrations/align-link", headers=_h(tok_p1), timeout=20)
        assert r.status_code == 200
        assert r.json()["linked"] is True


# --- Mediator email include_answers --------------------------------------
class TestMediatorEmailIncludeAnswers:
    """Payload shape test: endpoint accepts include_answers and records
    `included_answers` on the mediator_emails entry. We don't require a
    real completed assessment id — if none exists, we skip."""

    def _find_assessment_id(self, s, tok) -> str | None:
        r = s.get(f"{API}/safety-assessment/me/history", headers=_h(tok), timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data if isinstance(data, list) else data.get("items") or data.get("history") or data.get("assessments") or []
        # Prefer completed ones.
        completed = [it for it in items if it.get("completed") or it.get("status") in ("completed", "complete", "done")]
        pool = completed or items
        for it in pool:
            aid = it.get("assessment_id") or it.get("id") or it.get("_id")
            if aid:
                return aid
        return None

    def test_endpoint_accepts_include_answers_field(self, s, tok_p1):
        aid = self._find_assessment_id(s, tok_p1)
        if not aid:
            pytest.skip("No safety-assessment id available for parent1")
        for include in (False, True):
            r = s.post(
                f"{API}/safety-assessment/{aid}/email-mediator",
                headers=_h(tok_p1),
                json={
                    "mediator_email": "delivered@resend.dev",
                    "mediator_name": "Test Mediator",
                    "include_answers": include,
                },
                timeout=30,
            )
            # The endpoint may 404 if the id isn't the parent's; accept 200/202 as success.
            assert r.status_code in (200, 202), f"include={include} -> {r.status_code} {r.text[:200]}"

    def test_endpoint_default_include_answers_false(self, s, tok_p1):
        aid = self._find_assessment_id(s, tok_p1)
        if not aid:
            pytest.skip("No safety-assessment id available for parent1")
        # Omit include_answers entirely — default must be False and request must succeed.
        r = s.post(
            f"{API}/safety-assessment/{aid}/email-mediator",
            headers=_h(tok_p1),
            json={"mediator_email": "delivered@resend.dev", "mediator_name": "Test Mediator"},
            timeout=30,
        )
        assert r.status_code in (200, 202), f"{r.status_code} {r.text[:200]}"


# --- Migration ($setOnInsert never re-links an unlinked parent) ----------
class TestMigrationDoesNotRelink:
    def test_restart_backend_keeps_parent2_unlinked(self, s, tok_p2):
        # Ensure parent2 is unlinked right now.
        _ensure_parent2_unlinked(s, tok_p2)
        # Restart backend.
        import subprocess
        subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=False, capture_output=True)
        # Wait for backend to come back up.
        deadline = time.time() + 45
        while time.time() < deadline:
            try:
                h = s.get(f"{API}/", timeout=5)
                if h.status_code < 500:
                    break
            except Exception:
                pass
            time.sleep(1.5)
        time.sleep(1.0)
        # Re-login (session cookies won't help since this is JWT in header; token itself is still valid).
        r = s.get(f"{API}/integrations/align-link", headers=_h(tok_p2), timeout=20)
        assert r.status_code == 200, r.text[:200]
        assert r.json()["linked"] is False, "Migration unexpectedly re-linked parent2 after restart"
        # Export should still 404.
        r2 = s.get(
            f"{API}/integrations/export-assessments",
            params={"email": PARENT2},
            headers=_ik(),
            timeout=20,
        )
        assert r2.status_code == 404
