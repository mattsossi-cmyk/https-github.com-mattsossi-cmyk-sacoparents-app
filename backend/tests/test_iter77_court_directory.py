"""Iteration 77: judge read-only provider directory with last-verified dates."""
from test_judicial_portal import _flow
from test_legal_report import API


def test_court_directory_read_only() -> None:
    judge, pro, ref, case = _flow()
    r = judge.get(f"{API}/court-dashboard/providers")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["providers"] and "endorsement" in body["note"]
    p = body["providers"][0]
    assert {"name", "specialty", "phone", "website", "last_verified_at", "contact_verified"} <= set(p)
    assert "verification" not in p and "source_note" not in p
    assert pro.get(f"{API}/court-dashboard/providers").status_code == 403
    assert judge.post(f"{API}/admin/providers", json={"name": "x"}).status_code == 403
