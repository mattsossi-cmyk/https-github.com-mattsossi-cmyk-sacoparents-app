"""Iteration 67: Perplexity provider fast-add (admin-only) + prose/JSON split."""
import os

import pytest
import requests

from casekit import new_user
from research import _split_providers
from test_legal_report import API


@pytest.fixture(scope="module")
def admin_session() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", "mattsossi@bsossi.com"), "password": os.environ.get("ADMIN_PASSWORD", "CoParents2026!")})
    if r.status_code != 200:
        pytest.skip("admin login unavailable")
    return s


def test_split_providers_parses_trailing_json() -> None:
    prose, provs = _split_providers('Two options exist [1].\nPROVIDERS_JSON: [{"name": "Family Service Assoc.", "phone": "210-555-0100", "website": "fsa.org", "services": "Supervised exchange"}, {"phone": "x"}]')
    assert prose == "Two options exist [1]." and len(provs) == 1 and provs[0]["name"] == "Family Service Assoc."
    assert _split_providers("plain answer") == ("plain answer", [])


def test_provider_add_requires_admin() -> None:
    pro = new_user(API, "professional")
    r = pro.post(f"{API}/research/providers/add", json={"name": "T_Provider X", "category": "dv_advocacy"})
    assert r.status_code == 403


def test_provider_add_by_admin(admin_session) -> None:
    import uuid
    name = f"T_Provider {uuid.uuid4().hex[:6]}"
    r = admin_session.post(f"{API}/research/providers/add", json={"name": name, "organization": "Test Org", "phone": "210-555-0199", "website": "example.org", "services": "Safety planning", "category": "dv_advocacy"})
    assert r.status_code == 200, r.text
    assert r.json()["specialty"].lower().startswith("domestic violence") and r.json()["source"] == "perplexity"
    assert admin_session.post(f"{API}/research/providers/add", json={"name": name, "category": "dv_advocacy"}).status_code == 409
    assert any(p["name"] == name for p in admin_session.get(f"{API}/admin/providers").json())
    pid = r.json()["id"]
    admin_session.delete(f"{API}/admin/providers/{pid}")
