# Iter147: Family check-in in-card reminder (/api/family-checkin/reminder[/dismiss]) – 7-day rule, per-account dismiss, done hides.
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

from test_safety_gate_iter144_full import BASE_URL, DB, sign, register, PRO_NAME

URL = f"{BASE_URL}/api/family-checkin/reminder"
ST = {}


def send_update(case_id, version, offered):
    b = {"case_id": case_id, "safety_mode": "standard", "set_by": "professional", "professional_name": PRO_NAME,
         "referral": "none", "screening_offered": offered, "version": version, "timestamp": int(time.time())}
    raw = json.dumps(b).encode()
    r = requests.post(f"{BASE_URL}/api/internal/safety-status", data=raw,
                      headers={"Content-Type": "application/json", "X-Align-Signature": sign(raw)})
    assert r.status_code == 200, r.text


def new_case(pro, emails):
    r = pro.post(f"{BASE_URL}/api/professional/joint-alignment/cases", json={
        "assessment_type": "co-parenting", "parents": [{"email": e} for e in emails], "professional_name": PRO_NAME})
    assert r.status_code in (200, 201), r.text
    return r.json()["case_id"]


def age(case_id, days, as_string=False):
    when = datetime.now(timezone.utc) - timedelta(days=days)
    v = when.isoformat() if as_string else when
    DB.joint_alignment_cases.update_one({"case_id": case_id}, {"$set": {"created_at": v, "parents.$[].accepted_at": v}})


def show(s):
    r = s.get(URL)
    assert r.status_code == 200, r.text
    return r.json()["show"]


@pytest.fixture(scope="module", autouse=True)
def linked():
    pro, upro, epro = register("rmpro")
    a, ua, ea = register("rma")
    b, ub, eb = register("rmb")
    m, um, em = register("rmmulti")
    lone, ul, el = register("rmlone")
    c1 = new_case(pro, [ea, eb])
    for s in (a, b):
        assert s.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": c1}).status_code == 200
    c2 = new_case(pro, [em, "rmx_" + em])
    c3 = new_case(pro, [em, "rmy_" + em])
    for c in (c2, c3):
        assert m.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": c}).status_code == 200
    ST.update(c1=c1, c2=c2, c3=c3, a=a, b=b, m=m, lone=lone, ua=ua, ub=ub, um=um)
    yield
    for c in ("joint_alignment_cases", "case_safety", "safety_audit_log"):
        DB[c].delete_many({"case_id": {"$in": [c1, c2, c3]}})
    uids = [ua, ub, um, ul, upro]
    for c in ("plan_option_picks", "court_requested", "portal_state", "family_checkin_thanks", "family_checkin_reminder"):
        DB[c].delete_many({"user_id": {"$in": uids}})
    DB.users.delete_many({"email": {"$in": [ea, eb, em, el, epro]}})


class TestReminder:
    def test_unauth_401(self):
        assert requests.get(URL).status_code == 401
        assert requests.post(f"{URL}/dismiss").status_code == 401

    def test_unlinked_false_no_store(self):
        r = ST["lone"].get(URL)
        assert r.json() == {"show": False}
        assert "no-store" in r.headers.get("cache-control", "")

    def test_fresh_case_false(self):
        assert show(ST["a"]) is False and show(ST["b"]) is False

    def test_six_days_false_eight_days_true(self):
        age(ST["c1"], 6)
        assert show(ST["a"]) is False
        age(ST["c1"], 8)
        assert show(ST["a"]) is True and show(ST["b"]) is True

    def test_string_dates_parsed(self):
        age(ST["c1"], 8, as_string=True)
        assert show(ST["a"]) is True

    def test_dismiss_per_account(self):
        assert ST["a"].post(f"{URL}/dismiss").json() == {"ok": True}
        assert show(ST["a"]) is False and show(ST["b"]) is True
        docs = list(DB.family_checkin_reminder.find({"user_id": ST["ua"]}))
        assert len(docs) == 1 and set(docs[0]) <= {"_id", "user_id", "dismissed_at"}

    def test_dismiss_idempotent(self):
        ST["a"].post(f"{URL}/dismiss")
        assert DB.family_checkin_reminder.count_documents({"user_id": ST["ua"]}) == 1

    def test_dismiss_expires_after_week(self):
        DB.family_checkin_reminder.update_one({"user_id": ST["ua"]}, {"$set": {
            "dismissed_at": (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()}})
        assert show(ST["a"]) is False
        DB.family_checkin_reminder.update_one({"user_id": ST["ua"]}, {"$set": {
            "dismissed_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()}})
        assert show(ST["a"]) is True

    def test_done_hides_for_both(self):
        send_update(ST["c1"], 1, True)
        assert show(ST["a"]) is False and show(ST["b"]) is False
        send_update(ST["c1"], 2, False)
        assert show(ST["b"]) is True

    def test_multi_case_needs_all_done(self):
        age(ST["c2"], 10)
        age(ST["c3"], 10)
        assert show(ST["m"]) is True
        send_update(ST["c2"], 1, True)
        assert show(ST["m"]) is True
        send_update(ST["c3"], 1, True)
        assert show(ST["m"]) is False
