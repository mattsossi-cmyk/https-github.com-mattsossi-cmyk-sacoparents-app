"""Iteration 75: provider directory CSV export (admin only) with last-checked dates."""
import csv
import io
import os

import pytest
import requests

from test_legal_report import API


@pytest.fixture(scope="module")
def admin() -> requests.Session:
    s = requests.Session()
    if s.post(f"{API}/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", "mattsossi@bsossi.com"), "password": os.environ.get("ADMIN_PASSWORD", "CoParents2026!")}).status_code != 200:
        pytest.skip("admin login unavailable")
    return s


def test_export_csv(admin) -> None:
    r = admin.get(f"{API}/admin/providers/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text.lstrip("\ufeff"))))
    assert rows[0][:2] == ["Name", "Degrees"] and "Last checked (UTC)" in rows[0] and "Contact change applied (UTC)" in rows[0]
    names = {x[0] for x in rows[1:]}
    listed = {p["name"] for p in admin.get(f"{API}/admin/providers").json()}
    assert names == listed


def test_export_requires_admin() -> None:
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": "approval.test.pro1@gmail.com", "password": "TestPass2026!"})
    assert s.get(f"{API}/admin/providers/export.csv").status_code == 403
