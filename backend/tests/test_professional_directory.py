"""Professional directory + refer-a-case."""
import os

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_directory_lists_approved_pros_with_contact_fields() -> None:
    a = new_user(API, "professional", "Dir Pro A")
    b = new_user(API, "professional", "Dir Pro B")
    rows = a.get(f"{API}/professionals/directory").json()
    emails = {r["email"] for r in rows}
    assert a.email.lower() in emails and b.email.lower() in emails
    row = next(r for r in rows if r["email"] == b.email.lower())
    assert set(row) == {"id", "name", "email", "pro_role", "organization", "phone", "city", "state", "credentials_verified"}
    assert "password_hash" not in row


def test_parent_cannot_view_directory() -> None:
    _pro, pa, _pb, _d = new_case(API)
    assert pa.get(f"{API}/professionals/directory").status_code == 403


def test_refer_case_to_colleague_and_not_self() -> None:
    pro, _pa, _pb, d = new_case(API)
    colleague = new_user(API, "professional", "Dir Colleague")
    me = next(r for r in pro.get(f"{API}/professionals/directory").json() if r["email"] == pro.email.lower())
    them = next(r for r in pro.get(f"{API}/professionals/directory").json() if r["email"] == colleague.email.lower())
    assert pro.post(f"{API}/professionals/{me['id']}/refer", json={"message": "x"}).status_code == 400
    r = pro.post(f"{API}/professionals/{them['id']}/refer", json={"message": "Would you take this mediation?", "report_id": d["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["to"] == colleague.name
    assert pro.post(f"{API}/professionals/{them['id']}/refer", json={"report_id": "not-mine"}).status_code == 404
    assert pro.post(f"{API}/professionals/nope/refer", json={}).status_code == 404
