"""Admin invites a judge by email; registering with that email activates the court account immediately."""
import os
import uuid

import pymongo
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _admin() -> requests.Session:
    s = requests.Session()
    email = f"t_adminfix_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={"name": "Fixture Admin", "email": email, "password": "testpass123", "role": "professional", "agreements_accepted": True}).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": email}, {"$set": {"role": "admin", "approved": True}})
    return s


def test_invited_judge_is_auto_approved() -> None:
    admin = _admin()
    email = f"t_invjudge_{uuid.uuid4().hex[:8]}@example.com"
    r = admin.post(f"{API}/admin/judges/invite", json={"name": "Judge Invited", "email": email, "court_name": "285th District Court"})
    assert r.status_code == 200, r.text
    assert "court=1" in r.json()["link"] and email.split("@")[0] in r.json()["link"]
    assert any(x["email"] == email and x["status"] == "sent" for x in admin.get(f"{API}/admin/judges/invites").json())
    judge = requests.Session()
    reg = judge.post(f"{API}/auth/register", json={"name": "Judge Invited", "email": email, "password": "testpass123", "role": "judge", "agreements_accepted": True})
    assert reg.status_code == 200, reg.text
    assert reg.json()["approved"] and reg.json()["role"] == "judge"
    assert judge.get(f"{API}/court-dashboard/packets").json()["approved"]
    assert any(x["email"] == email and x["status"] == "registered" for x in admin.get(f"{API}/admin/judges/invites").json())
    assert admin.post(f"{API}/admin/judges/invite", json={"name": "x", "email": email}).status_code == 400


def test_non_admin_cannot_invite() -> None:
    s = requests.Session()
    s.post(f"{API}/auth/register", json={"name": "P", "email": f"t_np_{uuid.uuid4().hex[:6]}@example.com", "password": "testpass123", "role": "professional", "agreements_accepted": True})
    assert s.post(f"{API}/admin/judges/invite", json={"name": "x", "email": "j@example.com"}).status_code == 403
