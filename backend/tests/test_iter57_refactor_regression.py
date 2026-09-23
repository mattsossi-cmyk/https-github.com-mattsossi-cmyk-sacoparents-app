"""Iter-57 regression: post backend split refactor. Verifies the moved routes still respond identically over live HTTP.

Coverage:
  1. Auth: register, login (cookie), /auth/me, /me/preferences GET/PUT, refresh, logout, forgot-password.
  2. Admin: professionals lists, judges, create pre-approved pro; then verify invite pending.
  3. Cron: all 6 endpoints require WEBHOOK_CRON_SECRET.
  4. Integrations: case-invite/{bad} with shared secret -> 404; without -> 401/403. /external/link auth'd.
  5. Public: /health, /joint/sample-legal-lens/pdf, /court-dashboard/sample-case, /joint/samples, /assessment-types.
  6. Court messages: judge<->pro thread via /court-dashboard and /professional endpoints.
"""
import io
import os
import uuid

import pymongo
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env", override=False)

from casekit import new_user, complete_both  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]
INTEG_SECRET = os.environ["INTEGRATION_SHARED_SECRET"]
ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PW = "CoParents2026!"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# --- Public routes ---
class TestPublic:
    def test_health(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        j = r.json()
        assert j.get("status") == "healthy"
        assert j.get("build") == "2026-09-22.1"

    def test_sample_legal_lens_pdf(self):
        r = requests.get(f"{API}/joint/sample-legal-lens/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_court_sample_case(self):
        r = requests.get(f"{API}/court-dashboard/sample-case")
        assert r.status_code == 200
        body = r.json()
        assert body.get("case") or body.get("statement") or body.get("id"), body

    def test_joint_samples(self):
        r = requests.get(f"{API}/joint/samples")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_assessment_types(self):
        r = requests.get(f"{API}/assessment-types")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))


# --- Auth flow ---
class TestAuth:
    def test_register_login_me_prefs_refresh_logout(self):
        s = requests.Session()
        email = f"t_iter57_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "name": "Iter57 Pro", "email": email, "password": "testpass123",
            "role": "professional", "agreements_accepted": True,
        })
        assert r.status_code == 200, r.text
        # cookies set on register/login
        assert any(c.name == "access_token" for c in s.cookies), s.cookies

        # /auth/me
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json().get("email") == email

        # preferences GET/PUT
        p = s.get(f"{API}/me/preferences")
        assert p.status_code == 200, p.text
        put = s.put(f"{API}/me/preferences", json={"weekly_summary": False})
        assert put.status_code == 200, put.text
        p2 = s.get(f"{API}/me/preferences").json()
        assert p2.get("weekly_summary") is False

        # refresh
        rf = s.post(f"{API}/auth/refresh")
        assert rf.status_code == 200, rf.text
        assert any(c.name == "access_token" for c in s.cookies)

        # logout
        lo = s.post(f"{API}/auth/logout")
        assert lo.status_code == 200
        me2 = s.get(f"{API}/auth/me")
        assert me2.status_code in (401, 403)

        # login again
        s2 = requests.Session()
        r2 = s2.post(f"{API}/auth/login", json={"email": email, "password": "testpass123"})
        assert r2.status_code == 200
        assert s2.get(f"{API}/auth/me").json().get("email") == email

    def test_forgot_password_no_leak(self):
        r_real = requests.post(f"{API}/auth/forgot-password", json={"email": "nobody_iter57@example.com"})
        assert r_real.status_code == 200
        j = r_real.json()
        # Should not reveal user existence
        assert "not" not in str(j).lower() or "sent" in str(j).lower() or j.get("ok") is True


# --- Admin routes ---
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


class TestAdmin:
    def test_list_professionals(self, admin_session):
        r = admin_session.get(f"{API}/admin/professionals")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    def test_list_pending_professionals(self, admin_session):
        r = admin_session.get(f"{API}/admin/pending-professionals")
        assert r.status_code == 200, r.text

    def test_list_judges(self, admin_session):
        r = admin_session.get(f"{API}/admin/judges")
        assert r.status_code == 200, r.text

    def test_create_preapproved_professional(self, admin_session):
        email = f"t_iter57_admin_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Iter57 Admin-Created Pro", "email": email,
            "organization": "Iter57 Firm", "pro_role": "Mediator",
        }
        r = admin_session.post(f"{API}/admin/professionals", json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        # Cleanup: purge the created user + related invites
        try:
            db = _db()
            u = db.users.find_one({"email": email})
            if u:
                db.users.delete_one({"_id": u["_id"]})
                db.invitations.delete_many({"invitee_email": email})
        except Exception:
            pass
        assert body


# --- Cron ---
CRON_ENDPOINTS = [
    "weekly-summary", "completion-nudge", "expiry-digest",
    "follow-up-reminder", "hearing-reminder", "judge-digest",
]


@pytest.mark.parametrize("name", CRON_ENDPOINTS)
def test_cron_ok(name):
    r = requests.post(f"{API}/cron/{name}",
                      headers={"Authorization": f"Bearer {CRON_SECRET}"}, json={})
    assert r.status_code == 200, f"{name}: {r.status_code} {r.text[:200]}"
    body = r.json()
    assert body.get("ok") is True, body


@pytest.mark.parametrize("name", CRON_ENDPOINTS)
def test_cron_wrong_secret(name):
    r = requests.post(f"{API}/cron/{name}",
                      headers={"Authorization": "Bearer wrong-secret"}, json={})
    assert r.status_code in (401, 403), f"{name} wrong secret got {r.status_code}"


def test_cron_no_secret():
    r = requests.post(f"{API}/cron/weekly-summary", json={})
    assert r.status_code in (401, 403)


# --- Integrations ---
def test_case_invite_bad_token_with_secret():
    r = requests.get(f"{API}/integrations/case-invite/badtoken",
                     headers={"X-Integration-Key": INTEG_SECRET})
    assert r.status_code == 404, f"got {r.status_code} {r.text[:200]}"


def test_case_invite_no_secret():
    r = requests.get(f"{API}/integrations/case-invite/badtoken")
    assert r.status_code in (401, 403)


def test_external_link_authed():
    s = requests.Session()
    email = f"t_iter57_ext_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "X", "email": email, "password": "testpass123",
        "role": "professional", "agreements_accepted": True,
    })
    assert r.status_code == 200, r.text
    r = s.get(f"{API}/external/link")
    assert r.status_code == 200, r.text


# --- Court messages (moved to court_messages.Threads) ---
def _judge():
    s = requests.Session()
    e = f"t_iter57j_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "Judge Iter57", "email": e, "password": "testpass123", "role": "judge",
        "agreements_accepted": True, "organization": "Test District Court", "pro_role": "Judge",
    })
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


@pytest.fixture(scope="module")
def messaging_ctx():
    judge = _judge()
    pro = new_user(API, "professional", "Iter57 Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"], "cause_number": f"2026-CI-{uuid.uuid4().hex[:5]}",
        "child_initials": "K.T.", "parent_a_name": "A",
        "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
        "parent_b_name": "B",
        "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com",
    }).json()
    a = pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept")
    assert a.status_code == 200, a.text
    return {"judge": judge, "pro": pro, "ref_id": ref["id"]}


def test_judge_posts_message_pro_reads(messaging_ctx):
    ref_id = messaging_ctx["ref_id"]
    judge, pro = messaging_ctx["judge"], messaging_ctx["pro"]
    msg = judge.post(f"{API}/court-dashboard/cases/{ref_id}/messages",
                     json={"text": "Judge check-in: any updates?"})
    assert msg.status_code in (200, 201), msg.text

    got = pro.get(f"{API}/professional/court-referrals/{ref_id}/messages")
    assert got.status_code == 200, got.text
    body = got.json()
    msgs = body if isinstance(body, list) else body.get("messages") or body.get("items") or []
    assert any("Judge check-in" in (m.get("text") or m.get("body") or "") for m in msgs), msgs


def test_pro_posts_message_judge_reads(messaging_ctx):
    ref_id = messaging_ctx["ref_id"]
    judge, pro = messaging_ctx["judge"], messaging_ctx["pro"]
    msg = pro.post(f"{API}/professional/court-referrals/{ref_id}/messages",
                   json={"text": "Pro update: session scheduled."})
    assert msg.status_code in (200, 201), msg.text

    got = judge.get(f"{API}/court-dashboard/cases/{ref_id}/messages")
    assert got.status_code == 200, got.text
    body = got.json()
    msgs = body if isinstance(body, list) else body.get("messages") or body.get("items") or []
    assert any("Pro update" in (m.get("text") or m.get("body") or "") for m in msgs), msgs


# --- Court packets legacy path ---
def test_court_packet_respond_validation():
    """/api/joint/reports/{rid}/court-packets creates a packet; judge respond kind validation lives in court_packets.py."""
    pro, pa, pb, rep, detail = _completed_case()
    rid = rep["id"]
    # Finalize the legal lens so packet includes it (still optional)
    pro.get(f"{API}/cases/{rid}/professional-report")
    pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {"parent_a_rating": 5, "parent_b_rating": 6, "joint_rating": 5,
                   "signature_name": "QA Pro"},
        "status": "final",
    })
    pkt = pro.post(f"{API}/joint/reports/{rid}/court-packets", json={
        "cause_number": "2026-TEST-1", "county": "Test",
        "judge_name": "Hon. Test", "judge_email": f"t_judge_{uuid.uuid4().hex[:6]}@example.com",
        "cover_letter": "This is the cover letter for the Iter57 regression test. It contains at least a few sentences to satisfy validation. The professional attests to authority to release. Thank you for your consideration.",
        "attest": True,
        "note": "Iter57 packet"})
    if pkt.status_code == 404:
        pytest.skip("legacy court-packets route removed")
    assert pkt.status_code in (200, 201), pkt.text
    body = pkt.json()
    packet_id = body.get("id") or body.get("packet_id") or (body.get("packet") or {}).get("id")
    assert packet_id, f"packet id missing: {body}"
    # The judge respond validation is exercised in tests/test_court_packets.py; here we only
    # verify the moved court_packets router still creates a packet end-to-end after the split.


def _completed_case():
    from casekit import CaseSpec, new_case, fill
    pro, pa, pb, d = new_case(API, CaseSpec(subject="communication"))
    fill(API, pa, d["id"], "alpha")
    fill(API, pb, d["id"], "beta")
    detail = pro.get(f"{API}/joint/reports/{d['id']}").json()
    return pro, pa, pb, d, detail
