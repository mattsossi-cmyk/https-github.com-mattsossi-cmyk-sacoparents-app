"""Iter-63: 'Foundation Statement' pro assessment option -> case with kind='foundation',
code prefix SA-YY-FND-, /report returns kind='foundation' + foundation_statements,
/pdf returns 400, and share flips status to ready when both parents shared."""
import os
import uuid
import re

import pymupdf
import pytest
import requests

from casekit import new_user

from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"


COMPLETE = {
    "child_name": "Sky Rivera",
    "shared_purpose": "Sky deserves calm, love, and stability from both of us.",
    "vision": "I want Sky to grow up curious, confident, and safe.",
    "priorities": ["Protect Sky from adult conflict", "Consistent bedtimes"],
    "strengths": "Kind, curious, and resilient.",
    "needs": ["Calm transitions"],
    "concerns": ["Occasional anxiety at handoffs"],
    "child_may_need": "Gentle scripts before transitions.",
    "commitments": ["Speak respectfully about the other parent", "Reply within 24h"],
    "goals": ["Weekly check-in"],
    "future": "Sky remembers this as a period we made her wellbeing the top priority.",
    "parent_commitment": "I commit to putting Sky's needs above my own feelings.",
}


def _make_foundation_case():
    pro = new_user(API, "professional", "Pro")
    ea = f"TEST_fka_{uuid.uuid4().hex[:8]}@example.com"
    eb = f"TEST_fkb_{uuid.uuid4().hex[:8]}@example.com"
    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "foundation", "custom_subject": "", "child_name": "TEST_Sky",
        "parent_a_name": "Alice", "parent_a_email": ea,
        "parent_b_name": "Bob", "parent_b_email": eb,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    return pro, d, ea, eb


class TestFoundationKindCase:
    def test_case_creation_sets_kind_and_code(self):
        pro, d, ea, eb = _make_foundation_case()
        rid = d["id"]
        assert d.get("case_code", "").startswith("SA-") and "-FND-" in d["case_code"], d.get("case_code")
        # Detail
        r = pro.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        j = r.json()
        assert j.get("kind") == "foundation"

    def test_full_share_flow(self):
        pro, d, ea, eb = _make_foundation_case()
        rid = d["id"]
        toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
        pa = new_user(API, "parent", "Alice", email=ea, invite=toks["a"])
        pb = new_user(API, "parent", "Bob", email=eb, invite=toks["b"])
        for s, tok in ((pa, toks["a"]), (pb, toks["b"])):
            assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).status_code == 200

        # Parent A: complete + share
        assert pa.put(f"{API}/foundation/mine", json={"fields": COMPLETE, "safety": {"fear": False, "threats": False, "control": False}}).status_code == 200
        r = pa.post(f"{API}/joint/reports/{rid}/foundation/share")
        assert r.status_code == 200, r.text
        assert r.json()["side"] == "a"

        # Detail: A completed, status in_progress
        r = pro.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        j = r.json()
        parts = j.get("participants", {})
        assert parts.get("a", {}).get("completed") is True
        assert parts.get("b", {}).get("completed") is not True
        assert j.get("status") in ("in_progress", "invited")

        # /report before both -> 400
        r = pro.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 400

        # Parent B: complete + share
        assert pb.put(f"{API}/foundation/mine", json={"fields": {**COMPLETE, "child_name": "Sky (B)"}, "safety": {"fear": False, "threats": False, "control": False}}).status_code == 200
        r = pb.post(f"{API}/joint/reports/{rid}/foundation/share")
        assert r.status_code == 200, r.text
        assert r.json()["side"] == "b"

        # Detail: status ready
        r = pro.get(f"{API}/joint/reports/{rid}")
        assert r.status_code == 200
        j = r.json()
        assert j.get("status") == "ready", j.get("status")

        # /report -> kind foundation, 2 statements
        r = pro.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200, r.text
        rep = r.json()
        assert rep.get("kind") == "foundation"
        fs = rep.get("foundation_statements") or []
        assert len(fs) == 2, fs
        sides = sorted([x["side"] for x in fs])
        assert sides == ["a", "b"]

        # /pdf -> 400 for foundation-kind
        r = pro.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 400, r.status_code

        # per-parent PDFs
        for side in ("a", "b"):
            r = pro.get(f"{API}/joint/reports/{rid}/foundation/{side}/pdf")
            assert r.status_code == 200, f"{side}: {r.status_code} {r.text[:200]}"
            assert r.headers.get("content-type", "").startswith("application/pdf")
            text = "\n".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
            assert "Child-Focused Foundation Statement" in text
