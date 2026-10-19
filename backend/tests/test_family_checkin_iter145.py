# Iter145: Family check-in replaces A/B/C reflection modules.
# case-settings setup_complete, checklist family_checkin item, checklist PDF wording, court AI chat w/o modules.
# Webhook secret is loaded via dotenv only (inside test_safety_gate_iter144_full) and is never printed.
import io
import json
import time

import pytest
import requests
from pypdf import PdfReader

from test_safety_gate_iter144_full import BASE_URL, DB, sign, register, PRO_NAME

URL = f"{BASE_URL}/api/internal/safety-status"
BANNED = ["safety", "screening", "risk", "violence"]
ST = {}
EXPECTED_KEYS = ["case", "family_checkin", "card1", "card2", "card3", "card4", "biff"]


def send_update(version, screening_offered):
    b = {"case_id": ST["case_id"], "safety_mode": "standard", "set_by": "professional", "professional_name": PRO_NAME,
         "referral": "none", "screening_offered": screening_offered, "version": version, "timestamp": int(time.time())}
    raw = json.dumps(b).encode()
    return requests.post(URL, data=raw, headers={"Content-Type": "application/json", "X-Align-Signature": sign(raw)})


@pytest.fixture(scope="module", autouse=True)
def linked():
    pro, upro, epro = register("fcpro")
    a, ua, ea = register("fca")
    b, ub, eb = register("fcb")
    lone, ul, el = register("fclone")
    r = pro.post(f"{BASE_URL}/api/professional/joint-alignment/cases", json={
        "assessment_type": "co-parenting", "parents": [{"email": ea, "name": "TEST A"}, {"email": eb, "name": "TEST B"}],
        "professional_name": PRO_NAME})
    assert r.status_code in (200, 201), r.text
    case_id = r.json()["case_id"]
    for s in (a, b):
        assert s.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": case_id}).status_code == 200
    ST.update(case_id=case_id, a=a, b=b, lone=lone, ua=ua, ub=ub)
    yield
    for c in ("joint_alignment_cases", "case_safety", "safety_audit_log"):
        DB[c].delete_many({"case_id": case_id})
    uids = [ua, ub, ul, upro]
    for c in ("plan_option_picks", "court_requested", "court_path_chats", "portal_state"):
        DB[c].delete_many({"user_id": {"$in": uids}})
    DB.users.delete_many({"email": {"$in": [ea, eb, el, epro]}})


def cs(s):
    r = s.get(f"{BASE_URL}/api/case-settings")
    assert r.status_code == 200, r.text
    return r


def checklist(s, body=None):
    r = s.post(f"{BASE_URL}/api/court-path/checklist", json=body if body is not None else {})
    assert r.status_code == 200, r.text
    return r.json()


def pdf_text(s):
    r = s.post(f"{BASE_URL}/api/court-path/checklist/pdf", json={})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)


class TestCaseSettings:
    def test_unlinked_parent_false(self):
        d = cs(ST["lone"]).json()
        assert d["setup_complete"] is False

    def test_linked_no_update_false_and_identical(self):
        ra, rb = cs(ST["a"]), cs(ST["b"])
        assert ra.json()["setup_complete"] is False
        assert ra.content == rb.content

    def test_fields_and_no_banned_words(self):
        d = cs(ST["a"]).json()
        assert set(d.keys()) == {"banner", "set_by_label", "features", "template_categories", "settings",
                                 "plan_options", "setup_complete", "setup_completed_on"}
        low = json.dumps(d).lower()
        for w in BANNED:
            assert w not in low.replace("setup_complete", ""), w

    def test_update_true_then_false(self):
        r = send_update(1, True)
        assert r.status_code == 200, r.text
        ra, rb = cs(ST["a"]), cs(ST["b"])
        assert ra.json()["setup_complete"] is True
        assert ra.content == rb.content
        r = send_update(2, False)
        assert r.status_code == 200, r.text
        ra, rb = cs(ST["a"]), cs(ST["b"])
        assert ra.json()["setup_complete"] is False
        assert ra.content == rb.content


class TestChecklist:
    def test_items_todo(self):
        send_update(3, False)
        d = checklist(ST["a"])
        assert [i["key"] for i in d["items"]] == EXPECTED_KEYS
        fc = d["items"][1]
        assert fc["label"] == "Family check-in" and fc["status"] == "todo"
        low = json.dumps(d).lower()
        for w in BANNED + ["module"]:
            assert w not in low, w

    def test_items_done_both(self):
        assert send_update(4, True).status_code == 200
        for s in (ST["a"], ST["b"]):
            fc = checklist(s)["items"][1]
            assert fc["key"] == "family_checkin" and fc["status"] == "done"

    def test_extra_modules_ignored(self):
        d = checklist(ST["a"], {"modules": {"foundation": True, "safety": True}})
        assert [i["key"] for i in d["items"]] == EXPECTED_KEYS

    def test_unlinked_todo(self):
        fc = checklist(ST["lone"])["items"][1]
        assert fc["status"] == "todo"


class TestPdf:
    def test_pdf_full(self):
        t = pdf_text(ST["a"])
        assert "Family check-in" in t
        for w in ("Module A", "Module B", "Module C", "Child Needs & Priorities", "Co-Parenting Dynamics", "Conflict Readiness"):
            assert w not in t
        for w in BANNED:
            assert w not in t.lower(), w

    def test_pdf_requested_only(self):
        r = ST["a"].put(f"{BASE_URL}/api/court-path/requested", json={"keys": ["coparent", "self"]})
        assert r.status_code == 200, r.text
        t = " ".join(pdf_text(ST["a"]).split())
        assert "Showing your case, your Family check-in and the assessments your professional asked for." in t
        assert "Family check-in" in t


class TestCourtAiChat:
    def test_chat_without_modules(self):
        s = ST["b"]
        s.post(f"{BASE_URL}/api/ai-notice/ack")
        r = s.post(f"{BASE_URL}/api/court-path/ai/chat", json={"message": "What should I do next on my court path?"}, timeout=90)
        if r.status_code == 428:
            pytest.skip("AI notice not accepted")
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d, dict) and any(isinstance(v, str) and v for v in d.values())
        r2 = s.post(f"{BASE_URL}/api/court-path/ai/chat", json={"message": "hi", "modules": {"safety": True}}, timeout=90)
        assert r2.status_code in (200, 429), r2.text
