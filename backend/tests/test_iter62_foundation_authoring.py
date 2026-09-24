"""Iter-62: Parent-authored Foundation Statement (GET/PUT /api/foundation/mine, PDF, share into joint case)."""
import os
import uuid

import pymupdf
import pytest
import requests

from casekit import new_user, TEST_PASSWORD

from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"


def _new_case():
    """Pro creates a joint case; register both parents. Returns (pro, pa, pb, rid)."""
    pro = new_user(API, "professional", "Pro")
    ea = f"TEST_fa_{uuid.uuid4().hex[:10]}@example.com"
    eb = f"TEST_fb_{uuid.uuid4().hex[:10]}@example.com"
    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "education", "custom_subject": "", "child_name": "TEST_Kid",
        "parent_a_name": "Alice", "parent_a_email": ea,
        "parent_b_name": "Bob", "parent_b_email": eb,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    rid = d["id"]
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    pa = new_user(API, "parent", "Alice", email=ea, invite=toks["a"])
    pb = new_user(API, "parent", "Bob", email=eb, invite=toks["b"])
    for s, tok in ((pa, toks["a"]), (pb, toks["b"])):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).status_code == 200
    return pro, pa, pb, rid


PARTIAL = {"child_name": "Sky", "vision": "Grows up feeling safe."}
COMPLETE = {
    "child_name": "Sky Rivera",
    "shared_purpose": "Sky deserves calm, love, and stability from both of us.",
    "vision": "I want Sky to grow up curious, confident, and safe.",
    "priorities": ["Protect Sky from adult conflict", "Consistent bedtimes"],
    "strengths": "Kind, curious, and resilient.",
    "needs": ["Calm transitions", "Predictable schedule"],
    "concerns": ["Occasional anxiety at handoffs"],
    "child_may_need": "Gentle scripts before transitions.",
    "commitments": ["Speak respectfully about the other parent", "Reply to messages within 24h"],
    "goals": ["Weekly check-in with co-parent"],
    "future": "Sky remembers this as a period we made her wellbeing the top priority.",
    "parent_commitment": "I commit to putting Sky's needs above my own feelings and to communicating respectfully.",
}


class TestFoundationAuthoring:
    def test_full_flow(self):
        pro, pa, pb, rid = _new_case()

        # Parent A: initially null
        r = pa.get(f"{API}/foundation/mine")
        assert r.status_code == 200
        j = r.json()
        assert j["statement"] is None
        assert isinstance(j.get("sections"), list) and len(j["sections"]) >= 5

        # PUT partial -> complete False
        r = pa.put(f"{API}/foundation/mine", json={"fields": PARTIAL})
        assert r.status_code == 200, r.text
        st = r.json()["statement"]
        assert st["complete"] is False
        assert st["fields"]["child_name"] == "Sky"
        assert st["fields"]["priorities"] == []  # list field defaults to empty

        # Share -> 400 (incomplete)
        r = pa.post(f"{API}/joint/reports/{rid}/foundation/share")
        assert r.status_code == 400, r.text

        # PUT complete
        r = pa.put(f"{API}/foundation/mine", json={"fields": COMPLETE})
        assert r.status_code == 200
        st = r.json()["statement"]
        assert st["complete"] is True
        assert st["fields"]["priorities"] == COMPLETE["priorities"]

        # GET my PDF
        r = pa.get(f"{API}/foundation/mine/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        text = "\n".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
        assert "Sky Rivera" in text or "Sky" in text

        # Share -> 200 side a
        r = pa.post(f"{API}/joint/reports/{rid}/foundation/share")
        assert r.status_code == 200, r.text
        assert r.json().get("side") == "a"
        assert r.json().get("ok") is True

        # Professional: sees foundation_statements
        r = pro.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        fs = r.json().get("foundation_statements")
        assert isinstance(fs, list) and len(fs) == 1
        assert fs[0]["side"] == "a"
        assert fs[0]["structured"] is True

        # Professional: side a PDF
        r = pro.get(f"{API}/joint/reports/{rid}/foundation/a/pdf")
        assert r.status_code == 200
        text = "\n".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
        assert "Child-Focused Foundation Statement" in text
        assert "Parenting Priorities" in text

        # Parent B: forbidden
        r = pb.get(f"{API}/joint/reports/{rid}/foundation/a/pdf")
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

        # Professional: cannot share (no side)
        r = pro.post(f"{API}/joint/reports/{rid}/foundation/share")
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_mine_pdf_404_when_none(self):
        pro, pa, pb, rid = _new_case()
        # Fresh parent B who never wrote a statement
        r = pb.get(f"{API}/foundation/mine/pdf")
        assert r.status_code == 404
