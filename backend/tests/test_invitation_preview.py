"""Invitation email preview before sending."""
import os

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

PAYLOAD = {"child_name": "Kai", "subject": "communication", "parent_a_name": "Ann", "parent_a_email": "ann@example.com",
           "parent_b_name": "Bo", "parent_b_email": "bo@example.com"}


def test_preview_returns_two_distinct_emails_without_sending() -> None:
    pro = new_user(API, "professional", "Preview Pro")
    r = pro.post(f"{API}/joint/invitations/preview", json=PAYLOAD)
    assert r.status_code == 200, r.text
    previews = r.json()["previews"]
    assert [p["role"] for p in previews] == ["a", "b"]
    assert previews[0]["to"] == "ann@example.com" and previews[1]["to"] == "bo@example.com"
    for p in previews:
        assert "Kai" in p["html"] and "Communication" in p["html"] and "Preview Pro" in p["html"]
        assert "sacoparentsapp.online/?invite=PREVIEW-TOKEN" in p["html"]
    assert "Ann" in previews[0]["html"] and "Bo" in previews[1]["html"]
    assert all(x["child_name"] != "Kai" for x in pro.get(f"{API}/joint/reports").json())


def test_preview_requires_professional() -> None:
    _pro, pa, _pb, _d = new_case(API)
    assert pa.post(f"{API}/joint/invitations/preview", json=PAYLOAD).status_code == 403
