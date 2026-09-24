"""Iter-61: Foundation Statements surfaced on joint case + per-side PDF,
extra sample email endpoints, BUILD_ID bump."""
import io
import os
import uuid

import pytest
import pymupdf
import requests

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
AREA_KEYS = ["foundation", "transitions", "communication", "education", "medical",
             "psychological", "activities", "decisions", "differences", "review"]


def _agreement_with_foundation(child="FS Kid"):
    """Professional creates an agreement case; parent A submits a Foundation Statement.
    Returns (pro_session, parent_a_session, parent_b_session, rid, stmt_title, parent_a_name)."""
    pro = new_user(API, "professional", "Pro")
    ea = f"TEST_fsa_{uuid.uuid4().hex[:10]}@example.com"
    eb = f"TEST_fsb_{uuid.uuid4().hex[:10]}@example.com"
    r = pro.post(f"{API}/joint/agreements", json={
        "child_name": child,
        "parent_a_name": "Alice", "parent_a_email": ea,
        "parent_b_name": "Bob", "parent_b_email": eb,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    rid = d["id"]
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    a = new_user(API, "parent", "Alice", email=ea, invite=toks["a"])
    b = new_user(API, "parent", "Bob", email=eb, invite=toks["b"])
    for s, tok in ((a, toks["a"]), (b, toks["b"])):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).status_code == 200
    answers = {k: "We share decisions with weekly check-ins and even holiday splits" for k in AREA_KEYS}
    stmt_title = "My Foundation Statement"
    ra = a.put(f"{API}/joint/reports/{rid}/responses", json={
        "answers": answers,
        "foundation": [{"title": stmt_title, "content": "Our daughter needs calm, predictable handoffs above all else."}],
    })
    assert ra.status_code == 200, ra.text
    rb = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
    assert rb.status_code == 200, rb.text
    return pro, a, b, rid, stmt_title


# ---- BUILD_ID ----
class TestHealthBuild:
    def test_health_build_id(self):
        r = requests.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        assert r.json().get("build") == "2026-09-24.1", r.json()


# ---- Foundation on joint report + PDF authorization ----
class TestFoundationStatementsOnJoint:
    def test_creator_sees_foundation_statements_in_report_detail(self):
        pro, a, b, rid, title = _agreement_with_foundation()
        r = pro.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200, r.text
        fs = r.json().get("foundation_statements")
        assert isinstance(fs, list) and len(fs) == 1
        item = fs[0]
        assert item["side"] == "a"
        assert item["parent"] == "Alice"
        assert item["title"] == title
        assert "predictable handoffs" in item["content"]

    def test_parent_b_does_not_see_foundation_statements_field(self):
        pro, a, b, rid, _ = _agreement_with_foundation()
        r = b.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        # foundation_statements is creator-only
        assert "foundation_statements" not in r.json()

    def test_creator_can_download_side_a_foundation_pdf(self):
        pro, a, b, rid, title = _agreement_with_foundation()
        r = pro.get(f"{API}/joint/reports/{rid}/foundation/a/pdf")
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        text = "\n".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
        assert title in text, f"Title '{title}' missing from PDF text"
        assert "Child-Focused Foundation Statement" in text
        assert "SA CoParents" in text

    def test_side_b_no_statement_returns_404(self):
        pro, a, b, rid, _ = _agreement_with_foundation()
        r = pro.get(f"{API}/joint/reports/{rid}/foundation/b/pdf")
        assert r.status_code == 404, f"Expected 404 got {r.status_code} {r.text[:200]}"

    def test_parent_b_requesting_side_a_returns_403(self):
        pro, a, b, rid, _ = _agreement_with_foundation()
        r = b.get(f"{API}/joint/reports/{rid}/foundation/a/pdf")
        assert r.status_code == 403, f"Expected 403 got {r.status_code} {r.text[:200]}"

    def test_parent_a_can_download_own_side(self):
        pro, a, b, rid, title = _agreement_with_foundation()
        r = a.get(f"{API}/joint/reports/{rid}/foundation/a/pdf")
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        text = "\n".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
        assert title in text


# ---- sample-extra email endpoints ----
class TestExtraSampleEmail:
    def test_foundation_statement_email_ok(self):
        r = requests.post(f"{API}/joint/sample-extra/foundation-statement/email",
                          json={"email": "t_fs_ok@example.com"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

    def test_coparenting_agreement_email_ok(self):
        r = requests.post(f"{API}/joint/sample-extra/coparenting-agreement/email",
                          json={"email": "t_cpa_ok@example.com"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

    def test_unknown_key_returns_404(self):
        r = requests.post(f"{API}/joint/sample-extra/not-a-key/email",
                          json={"email": "t_unknown@example.com"}, timeout=15)
        assert r.status_code == 404
