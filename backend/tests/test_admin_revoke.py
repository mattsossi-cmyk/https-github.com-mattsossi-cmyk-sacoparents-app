"""Admin can revoke an approved professional; revoked pros leave the directory."""
import os

import pymongo

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _make_admin(email: str) -> None:
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    client[os.environ["DB_NAME"]].users.update_one({"email": email.lower()}, {"$set": {"role": "admin"}})
    client.close()


def test_revoke_removes_from_directory_and_needs_reason() -> None:
    admin = new_user(API, "professional", "Temp Admin")
    _make_admin(admin.email)
    pro = new_user(API, "professional", "Revoke Me")
    other = new_user(API, "professional", "Watcher")
    pid = next(r["id"] for r in other.get(f"{API}/professionals/directory").json() if r["email"] == pro.email.lower())
    assert admin.post(f"{API}/admin/revoke-professional/{pid}", json={"reason": ""}).status_code == 400
    assert other.post(f"{API}/admin/revoke-professional/{pid}", json={"reason": "x"}).status_code == 403
    assert admin.post(f"{API}/admin/revoke-professional/{pid}", json={"reason": "Not approved by SA CoParents"}).status_code == 200
    assert pro.email.lower() not in {r["email"] for r in other.get(f"{API}/professionals/directory").json()}
    assert pro.get(f"{API}/professionals/directory").status_code == 403
    assert admin.post(f"{API}/admin/revoke-professional/{pid}", json={"reason": "again"}).status_code == 404
    declined = admin.get(f"{API}/admin/declined-professionals").json()
    assert any(d["email"] == pro.email.lower() for d in declined)
