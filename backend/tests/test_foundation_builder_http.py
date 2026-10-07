"""HTTP tests for Card 4 Foundation Builder endpoints (iteration 94)."""
import os
import re
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


# GET /me unauthorized
def test_get_me_requires_auth():
    r = requests.get(f"{BASE_URL}/api/foundation-builder/me", timeout=20)
    assert r.status_code in (401, 403)


# GET /me authorized returns schema
def test_get_me_authed(client):
    r = client.get(f"{BASE_URL}/api/foundation-builder/me", timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert "fields" in body and "updated_at" in body
    assert isinstance(body["fields"], dict)


# PUT /me overwrites, drops unknown keys and caps 3000
def test_put_me_overwrites_and_caps(client):
    payload = {
        "fields": {
            "parent_names": "TEST_Sarah & Mark",
            "child_info": "TEST_Emma (8)",
            "core_goals": "x" * 5000,
            "bogus": "ignored",
            "commitments": "Pause first.",
        }
    }
    r = client.put(f"{BASE_URL}/api/foundation-builder/me", json=payload, timeout=20)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert "bogus" not in body["fields"]
    assert len(body["fields"]["core_goals"]) == 3000
    assert body["fields"]["parent_names"].startswith("TEST_Sarah")
    assert body["updated_at"]

    # GET verifies persistence
    r2 = client.get(f"{BASE_URL}/api/foundation-builder/me", timeout=20)
    assert r2.status_code == 200
    got = r2.json()
    assert got["fields"].get("commitments") == "Pause first."
    assert "bogus" not in got["fields"]


# PUT /me overwrite replaces (only kept keys persist)
def test_put_me_overwrite_replaces(client):
    # Save only core_goals
    r = client.put(
        f"{BASE_URL}/api/foundation-builder/me",
        json={"fields": {"core_goals": "TEST_only_this"}},
        timeout=20,
    )
    assert r.status_code == 200
    r2 = client.get(f"{BASE_URL}/api/foundation-builder/me", timeout=20).json()
    # Overwrite semantics: previous keys should be gone
    assert r2["fields"] == {"core_goals": "TEST_only_this"}


# POST /pdf empty -> 400
def test_pdf_empty_400():
    r = requests.post(
        f"{BASE_URL}/api/foundation-builder/pdf", json={"fields": {"core_goals": "   "}}, timeout=20
    )
    assert r.status_code == 400


# POST /pdf valid -> application/pdf + Content-Disposition
def test_pdf_valid_public():
    payload = {
        "fields": {
            "parent_names": "Sarah & Mark",
            "child_info": "Emma (8)",
            "core_goals": "Emma feels safe — always.",
            "commitments": "Pause before replying.",
        }
    }
    r = requests.post(f"{BASE_URL}/api/foundation-builder/pdf", json=payload, timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.headers.get("content-type", "").startswith("application/pdf")
    cd = r.headers.get("content-disposition", "")
    assert "SA_CoParents_Foundation_Statement_" in cd
    assert r.content[:4] == b"%PDF"

    # Decompress FlateDecode streams to verify text content
    import zlib, re as _re
    raw = r.content
    text_blob = b""
    for m in _re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, _re.DOTALL):
        try:
            text_blob += zlib.decompress(m.group(1))
        except Exception:
            pass
    for needle in [b"Foundation Statement", b"Parent signature", b"Date", b"Brighter Future"]:
        assert needle in text_blob, f"missing {needle!r} in PDF text"
    # Numbered labels
    for n in [b"1.", b"2.", b"3.", b"4."]:
        assert n in text_blob


# Regression: legacy foundation statement endpoint still responds
def test_legacy_foundation_statement_still_responds(client):
    # Try mediation first, then insights
    r = client.get(f"{BASE_URL}/api/mediation/foundation-statement.pdf", timeout=30)
    if r.status_code == 404:
        r = client.get(f"{BASE_URL}/api/insights/foundation-statement.pdf", timeout=30)
    # Accept any non-5xx (may 400/404 if no reflection yet, but must not crash)
    assert r.status_code < 500, f"legacy endpoint 5xx: {r.status_code}"
