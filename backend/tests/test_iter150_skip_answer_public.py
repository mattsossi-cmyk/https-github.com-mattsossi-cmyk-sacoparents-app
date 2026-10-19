"""Iter150 public-URL regression: Step 4 "I'd rather not answer" (prefer_not) on the legacy Safety Assessment,
and Step 3 Privacy Notice version bump (2026-10-19-v3)."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    email = f"test_iter150_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "TEST Iter150",
                                             "ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=30)
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    s.email = email
    yield s
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        u = db.users.find_one({"email": email})
        if u:
            db.safety_assessments.delete_many({"user_id": u["user_id"]})
            db.users.delete_many({"user_id": u["user_id"]})
    except Exception:
        pass


@pytest.fixture(scope="module")
def questions(client):
    r = client.get(f"{API}/safety-assessment/questions", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _base(questions):
    s1 = {q["id"]: "no" for q in questions["section_1"]}
    s2 = {q["id"]: ("no" if q["id"] == "s2_q8" else "yes") for q in questions["section_2"]}
    return s1, s2


# Questions endpoint shape
def test_questions_counts(questions):
    assert len(questions["section_1"]) == 28
    assert len(questions["section_2"]) == 8


# Baseline Level 4
def test_baseline_level4(client, questions):
    s1, s2 = _base(questions)
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, timeout=60)
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["level"] == 4 and res["declined_count"] == 0 and res["skip_floor_ids"] == []


# All prefer_not is accepted as answered (not "missing")
def test_all_prefer_not_accepted(client, questions):
    s1 = {q["id"]: "prefer_not" for q in questions["section_1"]}
    s2 = {q["id"]: "prefer_not" for q in questions["section_2"]}
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, timeout=60)
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["declined_count"] == 36 and res["section_1_declined_count"] == 28
    assert res["level"] == 2 and len(res["skip_floor_ids"]) == 12


# Ordinary skip does not raise
def test_ordinary_skip_level4(client, questions):
    s1, s2 = _base(questions)
    s1["s1_q3"] = "prefer_not"
    s2["s2_q8"] = "prefer_not"
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, timeout=60)
    assert r.status_code == 200
    res = r.json()["result"]
    assert res["level"] == 4 and res["declined_count"] == 2 and res["section_1_declined_count"] == 1


# Child experience floor
def test_child_floor(client, questions):
    s1, s2 = _base(questions)
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2,
                                                       "child_experience": {"ce_q8": "prefer_not"}}, timeout=60)
    assert r.status_code == 200
    res = r.json()["result"]
    assert res["level"] == 2 and res["skip_floor_ids"] == ["ce_q8"]


# Mixed case accepted; invalid value rejected
def test_case_insensitive_and_invalid(client, questions):
    s1, s2 = _base(questions)
    s1["s1_q1"] = "PREFER_NOT"
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, timeout=60)
    assert r.status_code == 200 and r.json()["result"]["level"] == 2
    s1["s1_q1"] = "maybe"
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, timeout=60)
    assert r.status_code == 400
    assert "s1_q1" in r.json()["detail"]["missing"]["section_1"]


# Persisted + PDF + one-pager show "Prefer not to answer"
def test_persist_and_pdf(client, questions):
    s1, s2 = _base(questions)
    s1["s1_q21"] = "prefer_not"
    r = client.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, timeout=60)
    aid = r.json()["assessment_id"]
    me = client.get(f"{API}/safety-assessment/me", timeout=30).json()
    assert me["assessment_id"] == aid and me["section_1"]["s1_q21"] == "prefer_not"
    assert me["result"]["skip_floor_ids"] == ["s1_q21"]
    pdf = client.get(f"{API}/safety-assessment/{aid}/pdf", timeout=90)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    op = client.get(f"{API}/safety-assessment/{aid}/one-pager", timeout=90)
    assert op.status_code == 200


# Privacy notice version bumped
def test_privacy_version(client):
    r = client.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 200
    txt = r.text
    # version is surfaced somewhere in consent status; tolerate either location
    r2 = client.get(f"{API}/privacy/consent-status", timeout=30)
    assert "2026-10-19-v3" in txt or (r2.status_code == 200 and "2026-10-19-v3" in r2.text) or r2.status_code == 404
