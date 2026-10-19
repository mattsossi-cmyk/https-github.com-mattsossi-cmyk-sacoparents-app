# Iter146: Family check-in case-code link (/api/family-checkin/link) + one-time thanks note (/api/family-checkin/thanks[/seen]).
import json
import time

import pytest
import requests

from test_safety_gate_iter144_full import BASE_URL, DB, sign, register, PRO_NAME

URL = f"{BASE_URL}/api/internal/safety-status"
ST = {}


def send_update(case_id, version, screening_offered):
    b = {"case_id": case_id, "safety_mode": "standard", "set_by": "professional", "professional_name": PRO_NAME,
         "referral": "none", "screening_offered": screening_offered, "version": version, "timestamp": int(time.time())}
    raw = json.dumps(b).encode()
    r = requests.post(URL, data=raw, headers={"Content-Type": "application/json", "X-Align-Signature": sign(raw)})
    assert r.status_code == 200, r.text


def new_case(pro, emails):
    r = pro.post(f"{BASE_URL}/api/professional/joint-alignment/cases", json={
        "assessment_type": "co-parenting", "parents": [{"email": e} for e in emails], "professional_name": PRO_NAME})
    assert r.status_code in (200, 201), r.text
    return r.json()["case_id"]


@pytest.fixture(scope="module", autouse=True)
def linked():
    pro, upro, epro = register("lkpro")
    a, ua, ea = register("lka")
    b, ub, eb = register("lkb")
    m, um, em = register("lkmulti")
    lone, ul, el = register("lklone")
    c1 = new_case(pro, [ea, eb])
    for s in (a, b):
        assert s.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": c1}).status_code == 200
    c2 = new_case(pro, [em, eb.replace("lkb", "lkx")])
    c3 = new_case(pro, [em, eb.replace("lkb", "lky")])
    for c in (c2, c3):
        assert m.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": c}).status_code == 200
    ST.update(c1=c1, c2=c2, c3=c3, a=a, b=b, m=m, lone=lone, ua=ua, ub=ub)
    yield
    for c in ("joint_alignment_cases", "case_safety", "safety_audit_log"):
        DB[c].delete_many({"case_id": {"$in": [c1, c2, c3]}})
    uids = [ua, ub, um, ul, upro]
    for c in ("plan_option_picks", "court_requested", "portal_state", "family_checkin_thanks"):
        DB[c].delete_many({"user_id": {"$in": uids}})
    DB.users.delete_many({"email": {"$in": [ea, eb, em, el, epro]}})


class TestLink:
    def test_unauth_401(self):
        assert requests.get(f"{BASE_URL}/api/family-checkin/link").status_code == 401

    def test_unlinked_null(self):
        r = ST["lone"].get(f"{BASE_URL}/api/family-checkin/link")
        assert r.status_code == 200 and r.json() == {"case_id": None}
        assert "no-store" in r.headers.get("cache-control", "")

    def test_single_case_both_parents_same_code(self):
        codes = [s.get(f"{BASE_URL}/api/family-checkin/link").json()["case_id"] for s in (ST["a"], ST["b"])]
        assert codes == [ST["c1"], ST["c1"]]

    def test_multi_case_gets_one_of_its_codes(self):
        assert ST["m"].get(f"{BASE_URL}/api/family-checkin/link").json()["case_id"] in (ST["c2"], ST["c3"])


class TestThanks:
    def test_unauth_401(self):
        assert requests.get(f"{BASE_URL}/api/family-checkin/thanks").status_code == 401
        assert requests.post(f"{BASE_URL}/api/family-checkin/thanks/seen").status_code == 401

    def test_not_done_false(self):
        for s in (ST["a"], ST["b"], ST["lone"]):
            assert s.get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": False}

    def test_done_shows_then_seen_once(self):
        send_update(ST["c1"], 1, True)
        assert ST["a"].get(f"{BASE_URL}/api/case-settings").json()["setup_complete"] is True
        for s in (ST["a"], ST["b"]):
            assert s.get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": True}
        assert ST["a"].post(f"{BASE_URL}/api/family-checkin/thanks/seen").json() == {"ok": True}
        assert ST["a"].get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": False}
        # per-account: parent B still sees it
        assert ST["b"].get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": True}

    def test_seen_idempotent_single_doc(self):
        ST["a"].post(f"{BASE_URL}/api/family-checkin/thanks/seen")
        docs = list(DB.family_checkin_thanks.find({"user_id": ST["ua"]}))
        assert len(docs) == 1 and set(docs[0]) <= {"_id", "user_id", "seen_at"}

    def test_stays_hidden_after_flip(self):
        send_update(ST["c1"], 2, False)
        send_update(ST["c1"], 3, True)
        assert ST["a"].get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": False}

    def test_multi_case_partial_not_shown(self):
        send_update(ST["c2"], 1, True)
        assert ST["m"].get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": False}
        send_update(ST["c3"], 1, True)
        assert ST["m"].get(f"{BASE_URL}/api/family-checkin/thanks").json() == {"show": True}
