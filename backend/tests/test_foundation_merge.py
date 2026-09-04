"""Tests for merging Foundation Statements into co-parenting agreements."""
import io
import os
import uuid
import requests
from pypdf import PdfReader

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
AREA_KEYS = ["parenting_schedule", "holidays", "decision_making", "communication",
             "exchanges", "expenses", "information_sharing", "dispute_resolution"]


def _reg(prefix="fs"):
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": "parent",
    })
    assert r.status_code == 200, r.text
    return s, email


def _agreement_with_foundation():
    a, _ = _reg("fsa")
    b, b_email = _reg("fsb")
    inv = a.post(f"{API}/joint/agreements", json={
        "child_name": "FS Kid", "co_parent_name": "B", "co_parent_email": b_email,
    })
    assert inv.status_code in (200, 201), inv.text
    rid = inv.json()["id"]
    code = inv.json()["invitation"]["code"]
    assert b.post(f"{API}/joint/invitations/accept", json={"code": code}).status_code == 200
    answers = {k: "We share decisions with weekly check-ins and even holiday splits" for k in AREA_KEYS}
    ra = a.put(f"{API}/joint/reports/{rid}/responses", json={
        "answers": answers,
        "foundation": [{"title": "My Foundation Statement", "content": "Our daughter needs calm, predictable handoffs above all else."}],
    })
    assert ra.status_code == 200, ra.text
    rb = b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
    assert rb.status_code == 200, rb.text
    return a, b, rid


class TestFoundationMerge:
    def test_agreement_report_includes_foundation(self):
        a, b, rid = _agreement_with_foundation()
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200, r.text
        fs = r.json().get("foundation_statements", [])
        assert len(fs) == 1
        assert fs[0]["title"] == "My Foundation Statement"
        assert "predictable handoffs" in fs[0]["content"]
        # parent B did not include one — only A's appears
        assert all(x["parent"] for x in fs)

    def test_agreement_pdf_includes_foundation(self):
        a, b, rid = _agreement_with_foundation()
        r = a.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200, r.text
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
        assert "Foundation Statements" in text
        assert "predictable handoffs" in text

    def test_agreement_without_foundation_still_works(self):
        a, _ = _reg("noc1")
        b, b_email = _reg("noc2")
        inv = a.post(f"{API}/joint/agreements", json={
            "child_name": "Plain Kid", "co_parent_name": "B", "co_parent_email": b_email,
        })
        rid = inv.json()["id"]
        code = inv.json()["invitation"]["code"]
        b.post(f"{API}/joint/invitations/accept", json={"code": code})
        answers = {k: "shared decisions and calm handoffs every week" for k in AREA_KEYS}
        a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        assert r.json().get("foundation_statements") == []
