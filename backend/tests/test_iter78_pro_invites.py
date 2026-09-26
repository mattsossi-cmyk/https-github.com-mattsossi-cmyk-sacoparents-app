"""Iteration 78: admin invite → prefilled registration → credential upload → request → accept (approve + verify)."""
import io
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


def test_invite_register_credentials_accept(admin) -> None:
    email = f"t_inv_{uuid.uuid4().hex[:8]}@example.com"
    r = admin.post(f"{API}/admin/pro-invites", json={"name": "Invited Pro", "email": email, "zip": "78209", "profession": "Family Law Attorney"})
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["status"] == "invited" and "token" not in inv
    assert admin.post(f"{API}/admin/pro-invites", json={"name": "Invited Pro", "email": email, "zip": "78209"}).status_code == 409
    assert admin.post(f"{API}/admin/pro-invites/{inv['id']}/resend").status_code == 200
    import pymongo
    c = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    token = c.pro_invites.find_one({"id": inv["id"]})["token"]
    pre = requests.get(f"{API}/auth/pro-invite/{token}").json()
    assert pre["email"] == email and pre["zip"] == "78209" and pre["credential_types"]
    pro = requests.Session()
    r = pro.post(f"{API}/auth/register", json={"name": "Invited Pro", "email": email, "password": "TestPass2026!", "role": "professional", "agreements_accepted": True, "pro_invite": token,
                                              "license_number": "24011111", "credential_type": "Licensed Attorney (State Bar)", "organization": "Test Law", "zip": ""})
    assert r.status_code == 200, r.text
    assert r.json()["approved"] is False
    assert c.pro_invites.find_one({"id": inv["id"]})["status"] == "registered"
    u = c.users.find_one({"email": email})
    assert u["profile"]["zip"] == "78209" and u["profile"]["credential_type"].startswith("Licensed Attorney")
    assert requests.get(f"{API}/auth/pro-invite/{token}").status_code == 404
    # credentials
    assert admin.post(f"{API}/admin/professionals/{u['_id']}/request-credentials").status_code == 200
    up = pro.post(f"{API}/me/credentials", files={"file": ("bar-card.pdf", io.BytesIO(b"%PDF-1.4 bar"), "application/pdf")})
    assert up.status_code == 200, up.text
    fid = up.json()["id"]
    assert pro.get(f"{API}/me/credentials").json()["requested_at"]
    assert admin.get(f"{API}/admin/professionals/{u['_id']}/credentials").json()["files"][0]["id"] == fid
    assert admin.get(f"{API}/credential-files/{fid}").status_code == 200
    other = requests.Session(); other.post(f"{API}/auth/login", json={"email": "approval.test.pro1@gmail.com", "password": "TestPass2026!"})
    assert other.get(f"{API}/credential-files/{fid}").status_code == 404
    assert other.post(f"{API}/admin/pro-invites", json={"name": "x", "email": "y@example.com", "zip": "78209"}).status_code == 403
    # pending list shows them; accept = approve + verify
    assert any(p["id"] == u["_id"] for p in admin.get(f"{API}/admin/pending-professionals").json())
    acc = admin.post(f"{API}/admin/accept-professional/{u['_id']}")
    assert acc.status_code == 200 and acc.json()["approved"] is True
    u2 = c.users.find_one({"_id": u["_id"]})
    assert u2["verification_level"] == "credentials_verified" and u2["credentials_verified_at"]
    assert c.pro_invites.find_one({"id": inv["id"]})["status"] == "accepted"
    assert any(p["id"] == u["_id"] and p["profile"]["zip"] == "78209" for p in admin.get(f"{API}/admin/professionals").json())
    c.users.delete_one({"_id": u["_id"]}); c.pro_invites.delete_one({"id": inv["id"]}); c.credential_files.delete_many({"user_id": u["_id"]})
