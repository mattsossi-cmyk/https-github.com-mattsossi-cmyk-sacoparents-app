"""Tests for merging Foundation Statements into co-parenting agreements
(professional-initiated model)."""
import io
import os
import uuid
from pypdf import PdfReader

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
AREA_KEYS = ["foundation", "transitions", "communication", "education", "medical", "psychological", "activities", "wellness_tech", "decisions", "differences", "review"]


def _agreement(child="FS Kid"):
    pro = new_user(API, "professional", "Pro")
    ea = f"TEST_fsa_{uuid.uuid4().hex[:10]}@example.com"
    eb = f"TEST_fsb_{uuid.uuid4().hex[:10]}@example.com"
    r = pro.post(f"{API}/joint/agreements", json={
        "child_name": child,
        "parent_a_name": "A", "parent_a_email": ea,
        "parent_b_name": "B", "parent_b_email": eb,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    a = new_user(API, "parent", "A", email=ea, invite=toks["a"])
    b = new_user(API, "parent", "B", email=eb, invite=toks["b"])
    for s, tok in ((a, toks["a"]), (b, toks["b"])):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}).status_code == 200
        assert s.post(f"{API}/joint/reports/{d['id']}/safety-screening/decline").status_code == 200  # Start-with-Safety step
    return a, b, d["id"]


def _agreement_with_foundation():
    a, b, rid = _agreement()
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
    def test_agreement_report_includes_foundation(self) -> None:
        a, b, rid = _agreement_with_foundation()
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200, r.text
        fs = r.json().get("foundation_statements", [])
        assert len(fs) == 1
        assert fs[0]["title"] == "My Foundation Statement"
        assert "predictable handoffs" in fs[0]["content"]
        assert all(x["parent"] for x in fs)

    def test_agreement_pdf_includes_foundation(self) -> None:
        a, b, rid = _agreement_with_foundation()
        r = a.get(f"{API}/joint/reports/{rid}/pdf")
        assert r.status_code == 200, r.text
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
        assert "Foundation Statements" in text
        assert "predictable handoffs" in text

    def test_agreement_without_foundation_still_works(self) -> None:
        a, b, rid = _agreement("Plain Kid")
        answers = {k: "shared decisions and calm handoffs every week" for k in AREA_KEYS}
        a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        b.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers})
        r = a.get(f"{API}/joint/reports/{rid}/report")
        assert r.status_code == 200
        assert r.json().get("foundation_statements") == []

    def test_co_parent_sees_included_foundation_and_explicit_empty_removes_it(self) -> None:
        a, b, rid = _agreement_with_foundation()
        fs = b.get(f"{API}/joint/reports/{rid}/report").json().get("foundation_statements", [])
        assert len(fs) == 1 and "predictable handoffs" in fs[0]["content"]  # included = co-parent sees it
        answers = {k: "We share decisions with weekly check-ins and even holiday splits" for k in AREA_KEYS}
        assert a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers}).status_code == 200  # omitted → kept
        assert len(a.get(f"{API}/joint/reports/{rid}/report").json().get("foundation_statements", [])) == 1
        assert a.put(f"{API}/joint/reports/{rid}/responses", json={"answers": answers, "foundation": []}).status_code == 200  # unticked → removed
        assert b.get(f"{API}/joint/reports/{rid}/report").json().get("foundation_statements") == []
