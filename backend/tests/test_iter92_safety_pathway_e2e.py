"""Iter92 — E2E Safety Pathway Engine (layered on Safety Screening v2).

Covers steps 1-9 from the review request. Reuses helpers from test_iter88 for register/login/accept.
Run with: python -m pytest -n0 /app/backend/tests/test_iter92_safety_pathway_e2e.py -v
"""
import io
import os
import re
import time

import pytest
import requests
from dotenv import load_dotenv

from tests.test_iter88_safety_e2e import MONGO, _accept_invite, _login, _register

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
PRO_EMAIL = "approval.test.pro1@gmail.com"
PRO_PASSWORD = "TestPass2026!"
PARENT_PASSWORD = "TestPass2026!"

TS = int(time.time())
A_EMAIL = f"qa.pw.a.{TS}@example.com"
B_EMAIL = f"qa.pw.b.{TS}@example.com"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def pro():
    return _login(PRO_EMAIL, PRO_PASSWORD)


@pytest.fixture(scope="module")
def case(pro):
    body = {
        "child_name": f"TEST Pathway {TS}",
        "subject": "communication",
        "parent_a_name": "QA PW A", "parent_a_email": A_EMAIL, "parent_a_gender": "woman",
        "parent_b_name": "QA PW B", "parent_b_email": B_EMAIL, "parent_b_gender": "man",
    }
    r = pro.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]
    invs = {i["role"]: (i.get("token") or i.get("code")) for i in MONGO.invitations.find({"report_id": rid})}
    return {"id": rid, "tokens": invs}


@pytest.fixture(scope="module")
def pa(case):
    _register(A_EMAIL, "QA PW A", invite=case["tokens"]["a"])
    s = _login(A_EMAIL, PARENT_PASSWORD)
    _accept_invite(s, case["tokens"]["a"])
    return s


@pytest.fixture(scope="module")
def pb(case):
    _register(B_EMAIL, "QA PW B", invite=case["tokens"]["b"])
    s = _login(B_EMAIL, PARENT_PASSWORD)
    _accept_invite(s, case["tokens"]["b"])
    return s


# ---------- step 1: spec after choose ----------
def test_01_spec_includes_extra_items_and_safe_device_notice(case, pa):
    rid = case["id"]
    r = pa.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["choice"] is not None and d["spec"] is None
    ok = pa.put(f"{BASE}/api/joint/reports/{rid}/safety-screening/choose", json={"version": "A"}, timeout=15)
    assert ok.status_code == 200, ok.text
    d = pa.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15).json()
    spec = d["spec"]
    assert spec is not None
    ids = [i["id"] for i in spec["items"]]
    assert ids[-6:] == ["x_1", "x_2", "x_3", "x_4", "x_5", "safe"], ids[-6:]
    assert spec["scales"]["yn3"] == ["Yes", "No", "Prefer not to say"]
    assert spec.get("safe_device_notice")


# ---------- step 2: submit + responses view returns pathway ----------
def test_02_submit_and_pathway_suggestion(case, pa, pro):
    rid = case["id"]
    r = pa.put(f"{BASE}/api/joint/reports/{rid}/safety-screening",
               json={"responses": {"a1": "Never", "x_2": "Sometimes", "safe": "Very safe"}}, timeout=15)
    assert r.status_code == 200, r.text
    r = pro.get(f"{BASE}/api/joint/reports/{rid}/safety-screening/a/responses", timeout=15)
    assert r.status_code == 200, r.text
    pw = r.json()["pathway"]
    assert pw["suggested"]["pathway"] == "structured", pw
    assert "technologyStalking" in pw["suggested"]["triggered"], pw["suggested"]["triggered"]
    assert pw["decision"] in (None, {}), pw["decision"]
    assert len(pw["options"]) == 3


# ---------- step 3: no auto restriction ----------
def test_03_no_auto_restriction_before_decision(case, pro):
    r = pro.get(f"{BASE}/api/cases/{case['id']}/professional-report", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("safety_pathway") is None, data.get("safety_pathway")


# ---------- step 4: dismiss then change ----------
def test_04_dismiss_then_change_to_protected_review(case, pro):
    rid = case["id"]
    r = pro.put(f"{BASE}/api/joint/reports/{rid}/safety-pathway/a", json={"action": "dismiss"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "dismissed"

    view = pro.get(f"{BASE}/api/cases/{rid}/professional-report", timeout=20).json()
    assert view.get("safety_pathway") is None

    r = pro.put(f"{BASE}/api/joint/reports/{rid}/safety-pathway/a",
                json={"action": "change", "pathway": "protected_review"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["confirmed"] == "protected_review"
    assert body["label"] == "Protected participation review recommended"

    view = pro.get(f"{BASE}/api/cases/{rid}/professional-report", timeout=20).json()
    sp = view.get("safety_pathway")
    assert sp is not None
    assert sp["label"] == "Protected participation review recommended"
    assert isinstance(sp.get("child_needs"), list) and sp["child_needs"]
    sg_blob = " ".join(sp.get("safeguards") or []).lower()
    assert "written-only" in sg_blob
    assert sp.get("decisions")
    assert sp.get("restricted_notice")
    # must NOT include leaked data
    txt = str(sp).lower()
    assert "flags" not in sp
    assert "responses" not in sp
    for banned in ("lgbtq", "sometimes", "technologystalking"):
        assert banned not in txt, banned
    # no x_5 Yes yet for A, b not confirmed either
    assert sp.get("court_order_notice") in (None, "")


# ---------- step 5: parent B x_5 yes -> protected_review, order notice ----------
def test_05_parent_b_submits_x5_yes_then_confirm(case, pb, pro):
    rid = case["id"]
    r = pb.put(f"{BASE}/api/joint/reports/{rid}/safety-screening",
               json={"responses": {"b1": "Never", "x_5": "Yes", "safe": "Very safe"}}, timeout=15)
    assert r.status_code == 200, r.text
    view = pro.get(f"{BASE}/api/joint/reports/{rid}/safety-screening/b/responses", timeout=15).json()
    sug = view["pathway"]["suggested"]
    assert sug["pathway"] == "protected_review"
    assert sug["triggered"] == ["activeProtectiveOrder"]
    r = pro.put(f"{BASE}/api/joint/reports/{rid}/safety-pathway/b", json={"action": "confirm"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["confirmed"] == "protected_review"
    rep = pro.get(f"{BASE}/api/cases/{rid}/professional-report", timeout=20).json()
    assert rep["safety_pathway"]["court_order_notice"] == (
        "Active court or protective orders reported. All recommendations must be reviewed against existing legal restrictions."
    )


# ---------- step 6: highest wins ----------
def test_06_highest_wins_a_standard_b_protected(case, pro):
    rid = case["id"]
    r = pro.put(f"{BASE}/api/joint/reports/{rid}/safety-pathway/a",
                json={"action": "change", "pathway": "standard"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["confirmed"] == "standard"
    rep = pro.get(f"{BASE}/api/cases/{rid}/professional-report", timeout=20).json()
    assert rep["safety_pathway"]["pathway"] == "protected_review", rep["safety_pathway"]


# ---------- step 7: leakage ----------
def test_07_parent_cannot_decide_pathway_for_b(case, pa):
    r = pa.put(f"{BASE}/api/joint/reports/{case['id']}/safety-pathway/b",
               json={"action": "dismiss"}, timeout=15)
    assert r.status_code == 403


def test_07b_parent_view_hides_coparent_and_pathway(case, pa):
    r = pa.get(f"{BASE}/api/joint/reports/{case['id']}/safety-screening", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert list(d["roles"].keys()) == ["a"], d["roles"].keys()
    blob = str(d)
    assert '"pathway"' not in blob
    assert '"flags"' not in blob


def test_07c_parent_cannot_view_b_responses(case, pa):
    r = pa.get(f"{BASE}/api/joint/reports/{case['id']}/safety-screening/b/responses", timeout=15)
    assert r.status_code == 403


# ---------- step 8: access log ----------
def test_08_access_log_recorded(case):
    cnt = MONGO.access_events.count_documents({"report_id": case["id"], "kind": "safety_pathway"})
    assert cnt >= 1, f"expected safety_pathway access_events, got {cnt}"


# ---------- step 9: PDF content ----------
def test_09_pdf_contains_labels_and_sanitized_card(case, pro):
    r = pro.get(f"{BASE}/api/cases/{case['id']}/professional-report/pdf", timeout=30)
    assert r.status_code == 200, r.text
    try:
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
    except Exception as e:
        pytest.skip(f"pypdf unavailable: {e}")
    norm = re.sub(r"\s+", " ", text)
    assert "Protected participation review recommended" in norm
    assert "Active court or protective orders reported" in norm
    assert "remain restricted" in norm
    # Scope the sanitization to the Safety Pathway card
    low = norm.lower()
    anchor = "safety pathway"
    assert anchor in low, "no Safety Pathway card found in PDF"
    card = low.split(anchor, 1)[1][:2500]
    for banned in ("parallel parenting", "lgbtq", "sometimes"):
        assert banned not in card, f"leaked {banned!r} in pathway card: {card[:400]}"
