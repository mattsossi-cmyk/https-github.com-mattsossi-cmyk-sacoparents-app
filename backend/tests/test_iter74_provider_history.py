"""Iteration 74: provider freshness history (per-check log with applied status)."""
import os
import uuid

import pytest
import requests

from test_legal_report import API


@pytest.fixture(scope="module")
def admin() -> requests.Session:
    s = requests.Session()
    if s.post(f"{API}/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", "mattsossi@bsossi.com"), "password": os.environ.get("ADMIN_PASSWORD", "CoParents2026!")}).status_code != 200:
        pytest.skip("admin login unavailable")
    return s


@pytest.mark.skipif(not os.environ.get("PERPLEXITY_API_KEY"), reason="live Perplexity required")
def test_history_records_check_and_apply(admin) -> None:
    name = f"T_KidShare Hist {uuid.uuid4().hex[:5]}"
    p = admin.post(f"{API}/research/providers/add", json={"name": name, "organization": "Family Service Association San Antonio KidShare", "phone": "210-000-0000", "website": "family-service.org/kidshare", "category": "supervised_exchange"}).json()
    assert admin.get(f"{API}/research/providers/{p['id']}/history").json()["history"] == []
    v = admin.post(f"{API}/research/providers/{p['id']}/verify", timeout=120)
    assert v.status_code == 200, v.text
    h = admin.get(f"{API}/research/providers/{p['id']}/history").json()["history"]
    assert len(h) == 1 and h[0]["applied_at"] is None and h[0]["by_name"] and set(h[0]["checks"]) == {"phone", "website"}
    a = admin.post(f"{API}/research/providers/{p['id']}/apply-verification").json()
    h2 = admin.get(f"{API}/research/providers/{p['id']}/history").json()["history"][0]
    if a["updated"]:
        assert h2["applied_at"] and h2["applied"] == a["updated"] and h2["applied_by_name"]
    else:
        assert h2["applied_at"] is None
    admin.delete(f"{API}/admin/providers/{p['id']}")


def test_history_requires_admin() -> None:
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": "approval.test.pro1@gmail.com", "password": "TestPass2026!"})
    assert s.get(f"{API}/research/providers/x/history").status_code == 403
