"""Iter93 — Communication Readiness HTTP/E2E + import unit.

Covers the review-request matrix for /joint/reports/{rid}/communication-readiness,
including the professional responses endpoint and co-parent privacy.
"""
import os
import sys
import time
import pytest
import requests
import pymongo
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

sys.path.insert(0, "/app/backend")

TS = int(time.time())
PRO_EMAIL = "approval.test.pro1@gmail.com"
PRO_PASSWORD = "TestPass2026!"
PA_EMAIL = f"qa.cr.a.{TS}@example.com"
PB_EMAIL = f"qa.cr.b.{TS}@example.com"
PWD = "TestPass2026!"
CHILD_TEXT = "handoffs at school are tense"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return s


def _register(email, name, invite=""):
    payload = {"name": name, "email": email, "password": PWD, "role": "parent"}
    if invite:
        payload["invite"] = invite
    r = requests.post(f"{BASE}/api/auth/register", json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text


def _accept(session, token):
    r = session.post(f"{BASE}/api/joint/invitations/accept", json={"token": token}, timeout=15)
    if r.status_code not in (200, 201):
        r = session.post(f"{BASE}/api/joint/invitations/accept", json={"code": token}, timeout=15)
    assert r.status_code in (200, 201), r.text


@pytest.fixture(scope="module")
def pro_session():
    return _login(PRO_EMAIL, PRO_PASSWORD)


@pytest.fixture(scope="module")
def case_setup(pro_session):
    body = {
        "child_name": f"TEST CR {TS}",
        "subject": "communication",
        "parent_a_name": "QA CR Parent A",
        "parent_a_email": PA_EMAIL,
        "parent_b_name": "QA CR Parent B",
        "parent_b_email": PB_EMAIL,
        "parent_a_gender": "woman",
    }
    r = pro_session.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]
    invs = list(MONGO.invitations.find({"report_id": rid}))
    tokens = {i["role"]: i.get("token") or i.get("code") for i in invs}
    # Point invitations to our test emails
    for role, email in (("a", PA_EMAIL), ("b", PB_EMAIL)):
        MONGO.invitations.update_one({"report_id": rid, "role": role}, {"$set": {"invitee_email": email}})
    _register(PA_EMAIL, "QA CR A", invite=tokens["a"])
    _register(PB_EMAIL, "QA CR B", invite=tokens["b"])
    sa = _login(PA_EMAIL, PWD)
    sb = _login(PB_EMAIL, PWD)
    _accept(sa, tokens["a"])
    _accept(sb, tokens["b"])
    yield {"rid": rid, "pa": sa, "pb": sb}
    # Teardown
    MONGO.joint_reports.delete_one({"id": rid})
    MONGO.invitations.delete_many({"report_id": rid})
    MONGO.users.delete_many({"email": {"$in": [PA_EMAIL, PB_EMAIL]}})


class TestCommReadiness:
    def test_parent_a_get_initial(self, case_setup):
        rid, sa = case_setup["rid"], case_setup["pa"]
        r = sa.get(f"{BASE}/api/joint/reports/{rid}/communication-readiness", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert [i["id"] for i in d["items"]] == ["cr_conflict", "cr_direct", "cr_channel", "cr_child"]
        assert d["received"] is False

    def test_parent_a_put(self, case_setup):
        rid, sa = case_setup["rid"], case_setup["pa"]
        body = {"responses": {
            "cr_conflict": "High",
            "cr_direct": "Only in writing",
            "cr_channel": "Written-only through a logged platform",
            "cr_child": CHILD_TEXT,
        }}
        r = sa.put(f"{BASE}/api/joint/reports/{rid}/communication-readiness", json=body, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["received"] is True and d["answered_count"] == 4

    def test_professional_responses_contains_comm(self, case_setup, pro_session):
        rid = case_setup["rid"]
        before = MONGO.access_events.count_documents({"report_id": rid, "kind": "safety_screening"})
        r = pro_session.get(f"{BASE}/api/joint/reports/{rid}/safety-screening/a/responses", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        comm = d.get("communication") or {}
        assert comm.get("received") is True
        assert comm.get("flag_for_professional") is True
        answers = {it["id"]: it["answer"] for it in comm.get("items") or []}
        assert answers.get("cr_child") == CHILD_TEXT
        after = MONGO.access_events.count_documents({"report_id": rid, "kind": "safety_screening"})
        assert after == before + 1, "expected access_events to be inserted"

    def test_parent_b_forbidden_responses_and_own_cr_only(self, case_setup):
        rid, sb = case_setup["rid"], case_setup["pb"]
        r = sb.get(f"{BASE}/api/joint/reports/{rid}/safety-screening/a/responses", timeout=15)
        assert r.status_code == 403
        r2 = sb.get(f"{BASE}/api/joint/reports/{rid}/communication-readiness", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["received"] is False
        assert CHILD_TEXT not in r2.text
        # Joint public never contains CR data
        r3 = sb.get(f"{BASE}/api/joint/reports/{rid}", timeout=15)
        assert r3.status_code == 200
        assert CHILD_TEXT not in r3.text
        assert "communication_readiness" not in r3.text

    def test_professional_overview_shows_received_flags(self, case_setup, pro_session):
        rid = case_setup["rid"]
        r = pro_session.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15)
        assert r.status_code == 200, r.text
        roles = r.json()["roles"]
        assert roles["a"]["communication_received"] is True
        assert roles["b"]["communication_received"] is False

    def test_professional_cannot_put_comm(self, case_setup, pro_session):
        rid = case_setup["rid"]
        r = pro_session.put(f"{BASE}/api/joint/reports/{rid}/communication-readiness", json={"responses": {"cr_conflict": "Low"}}, timeout=15)
        assert r.status_code == 403


# Import branch unit coverage (integrations.py lines ~257-262)
def test_comm_record_import_from_parent_app_source():
    from safety_screening import comm_record
    payload = {"communication_readiness": {
        "completed_at": "2026-01-02T03:04:05+00:00",
        "responses": {
            "cr_conflict": "Moderate",
            "cr_direct": "Yes",
            "cr_channel": "Direct messaging",
            "cr_child": "note",
        },
    }}
    rec = comm_record(payload["communication_readiness"]["responses"],
                      source="sacoparentsapp.online",
                      completed_at=payload["communication_readiness"]["completed_at"])
    assert rec["source"] == "sacoparentsapp.online"
    assert rec["completed_at"] == "2026-01-02T03:04:05+00:00"
    assert rec["responses"]["cr_conflict"] == "Moderate"
    assert rec["responses"]["cr_child"] == "note"
    assert rec["answered_count"] == 4
    assert rec["flag_for_professional"] is False
