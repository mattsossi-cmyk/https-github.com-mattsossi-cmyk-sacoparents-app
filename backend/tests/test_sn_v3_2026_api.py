"""Special Needs v3 2026 framework API regression tests.

Covers:
- schema (10 domains d1..d10 × 6 questions, response_scale 0..4, meta_flags, intake_profile)
- intake save
- answers/bulk with meta
- complete + report/generate + report GET
- report/{id}/share-link + shared JSON (public)
- invite lifecycle (create -> accept requires *different* user)
- comparison (waiting when only inviter completed; ready when both do)
- safety_triggered flow (Domain 10 Agree/Strongly agree -> safety-sensitive)
- DELETE /me
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

P1_EMAIL = "parent1@test.com"
P1_PASSWORD = "TestPass123!"
P1_NAME = "Sam Parent"
# A second parent to test invite/comparison
P2_EMAIL = f"parent2_snv3_{uuid.uuid4().hex[:6]}@test.com"
P2_PASSWORD = "TestPass123!"
P2_NAME = "Alex Parent"

TIMEOUT = 90


def _auth(email, password, name):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": password}, timeout=TIMEOUT)
    if r.status_code != 200:
        s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": password, "name": name}, timeout=TIMEOUT)
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": email, "password": password}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def p1():
    return _auth(P1_EMAIL, P1_PASSWORD, P1_NAME)


@pytest.fixture(scope="module")
def p2():
    return _auth(P2_EMAIL, P2_PASSWORD, P2_NAME)


@pytest.fixture(scope="module")
def schema(p1):
    r = p1.get(f"{BASE_URL}/api/special-needs-v3/schema", timeout=TIMEOUT)
    assert r.status_code == 200
    return r.json()


# --- Schema ---
def test_schema_new_2026_contract(schema):
    assert schema["total_questions"] == 60
    assert len(schema["domains"]) == 10
    ids = [d["id"] for d in schema["domains"]]
    assert ids == [f"d{i}" for i in range(1, 11)]
    for dom in schema["domains"]:
        assert len(dom["questions"]) == 6
    scale = schema["response_scale"]
    labels = [o["label"] for o in scale]
    assert labels == [
        "Strongly disagree", "Disagree",
        "Unsure or insufficient information",
        "Agree", "Strongly agree",
    ]
    meta_keys = {m["key"] for m in schema["meta_flags"]}
    assert {"na", "need_info", "want_help", "safety"} <= meta_keys
    assert isinstance(schema["intake_profile"], list) and len(schema["intake_profile"]) > 0
    # Domain 10 marked safety
    d10 = next(d for d in schema["domains"] if d["id"] == "d10")
    assert d10.get("safety_sensitive") is True


# --- Reset/me ---
def test_reset_and_me_empty(p1):
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    r = p1.get(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"exists": False}


# --- Intake ---
def test_intake_save_and_persist(p1):
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    body = {"intake": {"child_first_name": "Jamie", "child_age": "9"}}
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/intake", json=body, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    me = p1.get(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT).json()
    assert me["intake"]["child_first_name"] == "Jamie"


# --- Bulk answers + persist ---
def test_bulk_answers_with_meta(p1, schema):
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    payload = {
        "answers": {"d1_q1": 3, "d1_q2": 4, "d2_q1": 2},
        "meta": {"d1_q1": {"want_help": True}},
        "intake": {"child_first_name": "Jamie"},
    }
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["answered"] == 3 and d["total"] == 60
    me = p1.get(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT).json()
    assert me["answers"]["d1_q1"] == 3
    assert me["meta"]["d1_q1"]["want_help"] is True
    assert me["intake"]["child_first_name"] == "Jamie"


def _all_answers(schema, value=3, overrides=None):
    a = {}
    for dom in schema["domains"]:
        for q in dom["questions"]:
            a[q["id"]] = value
    if overrides:
        a.update(overrides)
    return a


# --- Complete + report + share ---
def test_full_flow_complete_report_share(p1, schema):
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    ans = _all_answers(schema, value=3)
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
                json={"answers": ans}, timeout=TIMEOUT)
    assert r.status_code == 200
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/complete", json={}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    scores = r.json()["scores"]
    assert "overall_rating" in scores
    valid_overalls = {
        "Existing Strength Overall", "Developing Overall",
        "Priority Focus Overall", "Safety-Sensitive Review Recommended",
    }
    assert scores["overall_rating"] in valid_overalls
    assert len(scores["domains"]) == 10
    # No old ratings
    old = {"Excellent", "Good", "Fair", "Needs Improvement"}
    assert scores["overall_rating"] not in old

    # Generate report
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/report/generate", json={}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    report_id = body["report_id"]
    assert body["report"]["overall_rating"] in valid_overalls

    # GET report
    r = p1.get(f"{BASE_URL}/api/special-needs-v3/report", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["report_id"] == report_id

    # share-link
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/report/{report_id}/share-link",
                json={"excluded": []}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    assert r.json()["viewer_path"] == f"/shared/special-needs/{tok}"

    # Public JSON view (no auth)
    r = requests.get(
        f"{BASE_URL}/api/special-needs-v3/report/shared/{tok}?format=json",
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    shared = r.json()
    assert shared["report"]["overall_rating"] in valid_overalls
    assert shared["shared_by"] == P1_NAME


# --- Safety-triggered ---
def test_safety_triggered_when_domain10_agree(p1, schema):
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    d10 = next(d for d in schema["domains"] if d["id"] == "d10")
    overrides = {q["id"]: 4 for q in d10["questions"]}  # Strongly agree on all d10 items (reverse-scored safety)
    ans = _all_answers(schema, value=3, overrides=overrides)
    p1.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
            json={"answers": ans}, timeout=TIMEOUT)
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/complete", json={}, timeout=TIMEOUT)
    assert r.status_code == 200
    scores = r.json()["scores"]
    assert scores.get("safety_triggered") is True
    assert scores["overall_rating"] == "Safety-Sensitive Review Recommended"
    rep = p1.post(f"{BASE_URL}/api/special-needs-v3/report/generate",
                  json={}, timeout=TIMEOUT).json()
    assert rep["report"].get("safety_triggered") is True


# --- Invite / comparison ---
def test_invite_create_and_self_accept_blocked(p1):
    r = p1.post(f"{BASE_URL}/api/special-needs-v3/invite", json={}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    assert r.json()["viewer_path"] == f"/invites/special-needs/{tok}"
    # inviter cannot accept own invite
    r2 = p1.post(f"{BASE_URL}/api/special-needs-v3/invite/{tok}/accept",
                 json={}, timeout=TIMEOUT)
    assert r2.status_code == 400


def test_comparison_waiting_then_ready(p1, p2, schema):
    # Reset both parents
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    p2.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)

    # p1 completes assessment first, then creates invite
    ans = _all_answers(schema, value=3)
    p1.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
            json={"answers": ans}, timeout=TIMEOUT)
    p1.post(f"{BASE_URL}/api/special-needs-v3/complete", json={}, timeout=TIMEOUT)

    # After complete, next invite call may not attach to existing completed
    # doc. To ensure invite_id ends up on the completed doc we must first
    # create an in-progress doc, then create the invite (which will attach
    # invite_id to that in-progress doc), then answer + complete.
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    # bootstrap an in-progress doc
    p1.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
            json={"answers": {"d1_q1": 3}}, timeout=TIMEOUT)
    inv = p1.post(f"{BASE_URL}/api/special-needs-v3/invite", json={}, timeout=TIMEOUT).json()
    tok = inv["token"]
    p1.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
            json={"answers": ans}, timeout=TIMEOUT)
    p1.post(f"{BASE_URL}/api/special-needs-v3/complete", json={}, timeout=TIMEOUT)

    # comparison waiting (acceptor hasn't finished)
    r = p1.get(f"{BASE_URL}/api/special-needs-v3/comparison", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "waiting"

    # p2 accepts and completes
    r = p2.post(f"{BASE_URL}/api/special-needs-v3/invite/{tok}/accept",
                json={}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    p2.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
            json={"answers": _all_answers(schema, value=2)}, timeout=TIMEOUT)
    p2.post(f"{BASE_URL}/api/special-needs-v3/complete", json={}, timeout=TIMEOUT)

    # comparison ready
    r = p1.get(f"{BASE_URL}/api/special-needs-v3/comparison", timeout=TIMEOUT)
    assert r.status_code == 200
    cmp_ = r.json()
    assert cmp_["status"] == "ready", cmp_
    assert len(cmp_["domains"]) == 10
    for d in cmp_["domains"]:
        assert "inviter" in d and "acceptor" in d
        assert "aligned" in d


# --- cleanup ---
def test_cleanup(p1, p2):
    p1.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
    p2.delete(f"{BASE_URL}/api/special-needs-v3/me", timeout=TIMEOUT)
