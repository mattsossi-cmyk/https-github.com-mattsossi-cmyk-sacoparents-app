"""API integration tests for Special Needs v3 with CP-matching vocabulary.

Targets the /api/special-needs-v3 surface after the 2026 family-violence /
Domain-10 subsystem was removed. Verifies schema shape (9 sections d1..d9,
54 questions, no 'safety' meta, no conflict_history intake), CP-vocabulary
ratings, full happy-path (intake + bulk answers + complete + report),
PDF rendering, share flow (public shared JSON + PDF), invite/comparison
two-parent flow, and legacy aliases (domains, find_domain).
"""
from __future__ import annotations

import os
import re
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

P1_EMAIL = "parent1@test.com"
P1_PASSWORD = "TestPass123!"

FORBIDDEN_STRINGS = [
    "Safety-Sensitive Review Recommended",
    "Safety-sensitive concern",
    "safety-sensitive alert",
    "Existing strength",
    "Existing Strength Overall",
    "Developing area",
    "Priority for planning",
    "Professional guidance recommended",
    "10 Principles",
    "10 principles",
    "10 Domains",
    "Domain 10",
    "conflict_history",
    "family violence",
    "Family Violence",
]


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def s():
    return requests.Session()


def _login_or_register(sess, email, password, name):
    r = sess.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        return r.json()["access_token"]
    r = sess.post(f"{API}/auth/register",
                  json={"email": email, "password": password, "name": name}, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    r = sess.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def p1_token(s):
    return _login_or_register(s, P1_EMAIL, P1_PASSWORD, "Sam Parent")


@pytest.fixture()
def p1_headers(p1_token):
    return {"Authorization": f"Bearer {p1_token}", "Content-Type": "application/json"}


def _all_answers(v: int = 3) -> dict:
    out = {}
    for d in range(1, 10):
        for q in range(1, 7):
            out[f"d{d}_q{q}"] = v
    return out


def _forbidden_scan(text: str, ctx: str):
    for bad in FORBIDDEN_STRINGS:
        assert bad.lower() not in text.lower(), f"Forbidden '{bad}' found in {ctx}"


# ---------- schema ----------

def test_schema_shape():
    r = requests.get(f"{API}/special-needs-v3/schema", timeout=30)
    assert r.status_code == 200
    d = r.json()

    assert d["total_questions"] == 54
    secs = d["sections"]
    assert len(secs) == 9
    assert [s["id"] for s in secs] == [f"d{i}" for i in range(1, 10)]
    for sec in secs:
        assert len(sec["questions"]) == 6

    # legacy alias present
    assert d.get("domains") == secs

    # scale labels
    labels = [x["label"] for x in d["response_scale"]]
    assert labels == [
        "Strongly disagree", "Disagree",
        "Unsure or insufficient information",
        "Agree", "Strongly agree",
    ]

    # meta flags: exactly 3, no safety
    keys = [m["key"] for m in d["meta_flags"]]
    assert set(keys) == {"na", "need_info", "want_help"}
    assert "safety" not in keys

    # intake groups & no conflict_history
    groups = {g["group"] for g in d["intake_profile"]}
    assert {"child", "family", "voice"}.issubset(groups)
    all_field_ids = [f["id"] for g in d["intake_profile"] for f in g["fields"]]
    assert "conflict_history" not in all_field_ids

    _forbidden_scan(r.text, "schema response")


# ---------- happy path ----------

def test_happy_path_report(s, p1_headers):
    # reset
    s.delete(f"{API}/special-needs-v3/me", headers=p1_headers, timeout=30)

    # intake
    r = s.post(f"{API}/special-needs-v3/intake",
               headers=p1_headers,
               json={"intake": {"child_age": 8, "diagnoses": "ADHD"}},
               timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["intake"]["child_age"] == 8

    # bulk answers
    r = s.post(f"{API}/special-needs-v3/answers/bulk",
               headers=p1_headers,
               json={"answers": _all_answers(3),
                     "meta": {"d1_q1": {"need_info": True}}},
               timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["answered"] == 54 and body["total"] == 54

    # complete
    r = s.post(f"{API}/special-needs-v3/complete", headers=p1_headers, timeout=30)
    assert r.status_code == 200, r.text
    scores = r.json()["scores"]
    assert scores["overall_rating"] in (
        "Excellent Progress", "Building Progress", "Early Progress", "Not enough data")
    for sec in scores["sections"]:
        assert sec["rating"] in ("Excellent", "Good", "Fair", "Needs Improvement", None)
    # legacy alias
    assert scores["domains"] == scores["sections"]
    _forbidden_scan(r.text, "complete response")

    # generate report
    r = s.post(f"{API}/special-needs-v3/report/generate", headers=p1_headers, timeout=60)
    assert r.status_code == 200, r.text
    doc = r.json()
    report = doc["report"]

    required = {"overall_rating", "overall_summary", "strengths", "growth_areas",
                "sections", "communication_toolkit", "show_communication_toolkit",
                "next_steps", "disclaimer", "intake", "framework"}
    assert required.issubset(report.keys()), f"missing keys: {required - report.keys()}"
    assert len(report["sections"]) == 9
    assert "9 sections" in report["framework"].lower() or "9 sections" in report["framework"]

    # rating vocabularies
    assert report["overall_rating"] in (
        "Excellent Progress", "Building Progress", "Early Progress", "Not enough data")
    for sec in report["sections"]:
        assert sec["rating"] in ("Excellent", "Good", "Fair", "Needs Improvement", None)

    _forbidden_scan(r.text, "report/generate")
    return doc["report_id"]


def test_pdf_download(s, p1_headers):
    # ensure a report exists
    r = s.get(f"{API}/special-needs-v3/report", headers=p1_headers, timeout=30)
    if r.status_code != 200 or not r.json().get("report"):
        # generate one
        s.delete(f"{API}/special-needs-v3/me", headers=p1_headers, timeout=30)
        s.post(f"{API}/special-needs-v3/answers/bulk",
               headers=p1_headers, json={"answers": _all_answers(3)}, timeout=30)
        s.post(f"{API}/special-needs-v3/complete", headers=p1_headers, timeout=30)
        s.post(f"{API}/special-needs-v3/report/generate", headers=p1_headers, timeout=60)

    r = s.get(f"{API}/special-needs-v3/report/pdf", headers=p1_headers, timeout=60)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert len(r.content) > 3000
    assert r.content[:4] == b"%PDF"

    # Extract PDF text via pdftotext for a meaningful string scan
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(r.content); path = f.name
    text = subprocess.check_output(["pdftotext", "-layout", path, "-"]).decode("utf-8", "ignore")
    assert "Section" in text, "PDF text should contain 'Section' headings"
    assert "Principle" not in text
    assert "Domain 10" not in text
    assert "Safety-Sensitive" not in text


# ---------- share flow ----------

def test_share_link(s, p1_headers):
    r = s.get(f"{API}/special-needs-v3/report", headers=p1_headers, timeout=30)
    report_id = r.json()["report_id"]

    r = s.post(f"{API}/special-needs-v3/report/{report_id}/share-link",
               headers=p1_headers, json={}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    token = body["token"]
    assert body["viewer_path"] == f"/shared/special-needs/{token}"

    # shared JSON (no auth)
    r = requests.get(f"{API}/special-needs-v3/report/shared/{token}?format=json", timeout=30)
    assert r.status_code == 200
    _forbidden_scan(r.text, "shared JSON")

    # shared PDF (no auth)
    r = requests.get(f"{API}/special-needs-v3/report/shared/{token}?format=pdf", timeout=60)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert len(r.content) > 3000
    raw = r.content.decode("latin-1", errors="ignore")
    # raw PDF is FlateDecoded; still filter known post-header strings
    for bad in ["Safety-Sensitive Review Recommended", "Existing Strength Overall",
                "10 Principles", "10 principles",
                "10 Domains", "Domain 10"]:
        assert bad not in raw, f"forbidden '{bad}' in shared PDF raw"

    # decoded text scan
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(r.content); path = f.name
    text = subprocess.check_output(["pdftotext", "-layout", path, "-"]).decode("utf-8", "ignore")
    for bad in ["Safety-Sensitive", "10 Principles", "10 Domains", "Domain 10",
                "Existing strength", "Existing Strength Overall"]:
        assert bad not in text, f"forbidden '{bad}' in decoded shared PDF"


# ---------- invite + comparison ----------

@pytest.fixture(scope="session")
def p2_creds(s):
    email = f"parent2_snv3_{uuid.uuid4().hex[:6]}@test.com"
    pw = "TestPass123!"
    tok = _login_or_register(s, email, pw, "Pat Coparent")
    return email, pw, tok


def test_invite_and_comparison(p2_creds):
    # p1 fresh session
    s1 = requests.Session()
    tok1 = _login_or_register(s1, P1_EMAIL, P1_PASSWORD, "Sam Parent")
    h1 = {"Authorization": f"Bearer {tok1}", "Content-Type": "application/json"}

    # reset & begin an in-progress doc so invite attaches
    s1.delete(f"{API}/special-needs-v3/me", headers=h1, timeout=30)
    s1.post(f"{API}/special-needs-v3/answer",
            headers=h1, json={"question_id": "d1_q1", "value": 3}, timeout=30)

    r = s1.post(f"{API}/special-needs-v3/invite", headers=h1, json={}, timeout=30)
    assert r.status_code == 200, r.text
    inv_token = r.json()["token"]
    viewer_path = r.json()["viewer_path"]
    assert viewer_path.startswith("/invites/special-needs/")

    # finish p1 answers + complete
    s1.post(f"{API}/special-needs-v3/answers/bulk",
            headers=h1, json={"answers": _all_answers(3)}, timeout=30)
    s1.post(f"{API}/special-needs-v3/complete", headers=h1, timeout=30)

    # p2 accepts
    _, _, tok2 = p2_creds
    s2 = requests.Session()
    h2 = {"Authorization": f"Bearer {tok2}", "Content-Type": "application/json"}
    s2.delete(f"{API}/special-needs-v3/me", headers=h2, timeout=30)
    r = s2.post(f"{API}/special-needs-v3/invite/{inv_token}/accept",
                headers=h2, json={}, timeout=30)
    assert r.status_code == 200, r.text

    # p2 completes with different values
    s2.post(f"{API}/special-needs-v3/answers/bulk",
            headers=h2, json={"answers": _all_answers(2)}, timeout=30)
    s2.post(f"{API}/special-needs-v3/complete", headers=h2, timeout=30)

    # comparison from p1
    r = s1.get(f"{API}/special-needs-v3/comparison", headers=h1, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "ready"
    assert len(d["sections"]) == 9
    for row in d["sections"]:
        assert row["id"].startswith("d")
        assert "inviter" in row and "acceptor" in row
        assert "rating" in row["inviter"]
        assert "rating" in row["acceptor"]
        assert "category" not in row
        assert "safety_flag" not in row
        assert row["inviter"]["rating"] in ("Excellent", "Good", "Fair", "Needs Improvement", None)

    assert "safety_triggered" not in str(d)
    _forbidden_scan(r.text, "comparison response")


# ---------- self-accept blocked ----------

def test_invite_self_accept_blocked(s, p1_headers):
    r = s.post(f"{API}/special-needs-v3/invite", headers=p1_headers, json={}, timeout=30)
    assert r.status_code == 200
    tok = r.json()["token"]
    r = s.post(f"{API}/special-needs-v3/invite/{tok}/accept",
               headers=p1_headers, json={}, timeout=30)
    assert r.status_code == 400


# ---------- legacy aliases ----------

def test_legacy_find_domain_alias():
    from sn_v3_questions import find_domain, find_section
    assert find_domain is find_section
    assert find_domain("d1")["number"] == 1
