"""Iteration 170 — Portal Handshake Simulator CLI script.

Smoke tests the CLI at `/app/scripts/portal_handshake_simulator.py`:
  * `--help` prints and exits 0
  * missing `--integration-key` errors with exit 2
  * happy path against a live permission_id (from a freshly minted
    invite) — check_permission returns active + record_event
    increments the counters (exit 0)
  * curl output NEVER prints the raw integration key literally
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from typing import Tuple

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


SCRIPT = "/app/scripts/portal_handshake_simulator.py"

INTEGRATION_KEY = os.environ.get("INTEGRATION_SHARED_SECRET") or ""
if not INTEGRATION_KEY:
    try:
        with open("/app/backend/.env") as _f:
            for _line in _f:
                if _line.startswith("INTEGRATION_SHARED_SECRET="):
                    INTEGRATION_KEY = _line.split("=", 1)[1].strip()
                    break
    except OSError:
        pass


def _run(*args) -> Tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True, timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _register(prefix: str) -> Tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"S {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200
    return email, r.json()["access_token"]


def _seed_reflection(tok: str) -> None:
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "a", "own_part": "b", "best_outcome": "c", "coparent_feedback": "d"},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )


def _mint_permission(prefix: str) -> str:
    _e, tok = _register(prefix)
    _seed_reflection(tok)
    fid = requests.get(
        f"{BASE_URL}/api/parent/report-catalog",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    ).json()["reports"][0]["report_id"]
    inv = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json={
            "professional_first_name": "Sim", "professional_last_name": "Test",
            "professional_email": "sim@example.com", "professional_email_confirm": "sim@example.com",
            "professional_role": "mediator", "report_ids": [fid],
            "view_permission": True, "download_permission": True,
            "notify_on_view": True, "notify_on_download": True,
            "future_versions": False, "access_days": 30,
            "consent_authorised": True, "consent_relationship_acknowledged": True,
        },
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        timeout=30,
    ).json()
    inv_id = inv["invitation_id"]
    detail = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/{inv_id}",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    ).json()
    return detail["permissions"][0]["permission_id"]


# ------------------------------------------------------------------

def test_help_prints_and_exits_clean():
    code, out, err = _run("--help")
    assert code == 0
    assert "Portal Handshake Simulator" in out or "portal_handshake" in out
    assert "--permission-id" in out


def test_missing_integration_key_exits_2():
    code, out, err = _run(
        "--base-url", BASE_URL,
        "--integration-key", "",
        "--permission-id", "deadbeef1234abcd",
    )
    assert code == 2


def test_happy_path_active_permission():
    perm_id = _mint_permission("simhappy")
    code, out, err = _run(
        "--base-url", BASE_URL,
        "--integration-key", INTEGRATION_KEY,
        "--permission-id", perm_id,
        "--events", "view", "download",
    )
    assert code == 0, f"stdout:\n{out}\nstderr:\n{err}"
    # Permission-check active
    assert "Permission is ACTIVE" in out
    # Event confirmations
    assert "Event 'view' recorded" in out
    assert "Event 'download' recorded" in out


def test_curl_output_never_prints_raw_secret():
    """The reproducible curl snippet must reference the env var
    rather than embedding the raw key (a portal engineer might
    paste the output into Slack or a bug tracker)."""
    perm_id = _mint_permission("simredact")
    code, out, err = _run(
        "--base-url", BASE_URL,
        "--integration-key", INTEGRATION_KEY,
        "--permission-id", perm_id,
    )
    assert code == 0
    # Full key must never appear in a curl line.
    lines = [l for l in out.splitlines() if l.strip().startswith("-H 'X-Integration-Key")]
    assert lines, "no curl X-Integration-Key line rendered"
    for line in lines:
        assert INTEGRATION_KEY not in line, f"raw secret leaked in: {line}"
        assert "$INTEGRATION_SHARED_SECRET" in line


def test_unknown_permission_exits_1():
    code, out, err = _run(
        "--base-url", BASE_URL,
        "--integration-key", INTEGRATION_KEY,
        "--permission-id", "notaperm1234abcd",
        "--events", "view",
    )
    # Permission check returns 200 with {active:false, reason:"unknown"}
    # so that alone doesn't fail the exit code — but the event
    # attempt then 404s, so we expect exit 1.
    assert code == 1
    assert "INACTIVE" in out or "Unknown" in out or "404" in out
