"""Professional approval gating: new professional accounts are pending until the
admin approves them. Parents (via invitation) are unaffected.
casekit.new_user auto-approves its fixtures, so these tests register raw pros."""
import os
import uuid
import requests
import pymongo
from dotenv import load_dotenv

from casekit import TEST_PASSWORD, new_case

load_dotenv("/app/backend/.env")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _raw_pro():
    """Register a professional the real way — starts unapproved."""
    s = requests.Session()
    email = f"t_pro_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "New Pro", "email": email, "password": TEST_PASSWORD, "role": "professional"})
    assert r.status_code == 200, r.text
    s.email = email
    return s


def _admin_session():
    s = _raw_pro()
    client = pymongo.MongoClient(MONGO_URL)
    client[DB_NAME].users.update_one({"email": s.email}, {"$set": {"role": "admin", "approved": True}})
    client.close()
    return s


class TestProfessionalApproval:
    def test_new_professional_is_pending(self):
        pro = _raw_pro()
        me = pro.get(f"{API}/auth/me").json()
        assert me["role"] == "professional"
        assert me["approved"] == False

    def test_unapproved_pro_cannot_create_case(self):
        pro = _raw_pro()
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_a_{uuid.uuid4().hex[:6]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 403
        assert "pending approval" in r.json()["detail"].lower()

    def test_unapproved_pro_cannot_prepare_or_create_agreement(self):
        pro = _raw_pro()
        r = pro.post(f"{API}/joint/agreements", json={
            "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_a_{uuid.uuid4().hex[:6]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 403
        assert "pending approval" in r.json()["detail"].lower()
        r = pro.post(f"{API}/joint/professional-requests/whatever/prepare")
        assert r.status_code == 403

    def test_admin_lists_and_approves(self):
        pro = _raw_pro()
        admin = _admin_session()
        pending = admin.get(f"{API}/admin/pending-professionals").json()
        match = [p for p in pending if p["email"] == pro.email]
        assert match, "new pro should appear in pending list"
        r = admin.post(f"{API}/admin/approve-professional/{match[0]['id']}")
        assert r.status_code == 200
        assert pro.get(f"{API}/auth/me").json()["approved"] == True
        # approved pro can now create a case
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "K",
            "parent_a_name": "A", "parent_a_email": f"t_a_{uuid.uuid4().hex[:6]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"t_b_{uuid.uuid4().hex[:6]}@example.com",
        })
        assert r.status_code == 200, r.text

    def test_non_admin_cannot_list_or_approve(self):
        seed_pro, pa, pb, d = new_case(API)  # approved professional fixture
        pro = _raw_pro()
        r = seed_pro.get(f"{API}/admin/pending-professionals")
        assert r.status_code == 403
        me = pro.get(f"{API}/auth/me").json()
        r = seed_pro.post(f"{API}/admin/approve-professional/{me['id']}")
        assert r.status_code == 403

    def test_approve_unknown_404(self):
        admin = _admin_session()
        r = admin.post(f"{API}/admin/approve-professional/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_parent_registration_unaffected(self):
        pro, pa, pb, d = new_case(API)
        me = pa.get(f"{API}/auth/me").json()
        assert me["role"] == "parent"
        assert me["approved"] == True
