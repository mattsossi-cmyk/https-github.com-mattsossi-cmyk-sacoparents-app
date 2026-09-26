"""Iter-58: verify the new 7-section Legal Lens report shape.
- persistence of conflict_pathways (list), child_focus (dict), shared_concerns, pathway_rationale, professional_summary
- finalize gate on pathway_rationale (empty pathway_rationale + empty conflict_management_rationale + selected pathways -> 400)
- PDF headings for the 7 sections + [SELECTED] markers + child-focus notes + Report principle
- Court view surfaces pathways/child_focus/professional_summary in statement.legal_summary
- Public sample /api/joint/sample-legal-lens/pdf contains the 7 headings
"""
import io
import os
import uuid

import pymongo
import pytest
import requests
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from casekit import new_user, complete_both  # noqa: E402

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _pdf_text(b: bytes) -> str:
    r = PdfReader(io.BytesIO(b))
    return "\n".join(p.extract_text() or "" for p in r.pages)


def _judge():
    s = requests.Session()
    e = f"t_iter58j_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "Judge Iter58", "email": e, "password": "testpass123", "role": "judge",
        "agreements_accepted": True, "organization": "Test Court", "pro_role": "Judge"})
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


@pytest.fixture(scope="module")
def flow():
    judge = _judge()
    pro = new_user(API, "professional", "Iter58 Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"], "cause_number": f"2026-CI-{uuid.uuid4().hex[:5]}",
        "child_initials": "T.T.",
        "parent_a_name": "Alex", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
        "parent_b_name": "Blake", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com",
        "note": "iter58"}).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").status_code == 200
    d = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "communication", "child_name": "T.T.",
        "parent_a_name": "Alex", "parent_a_email": ref["parent_a_email"],
        "parent_b_name": "Blake", "parent_b_email": ref["parent_b_email"],
        "court_referral_id": ref["id"]}).json()
    complete_both(API, pro, d["id"], d["invitations"])
    return {"judge": judge, "pro": pro, "ref": ref, "rid": d["id"]}


# ----- Backend save: new fields persist via GET /professional-report -----
def test_save_draft_persists_new_fields(flow):
    pro, rid = flow["pro"], flow["rid"]
    # bootstrap
    assert pro.get(f"{API}/cases/{rid}/professional-report").status_code == 200
    # persist multi-select pathways + child_focus + shared_concerns + rationale + summary
    child_focus = {
        "educational": {"checked": True, "note": "Homework routine differs between homes."},
        "communication": {"checked": True, "note": "Reactive texts at handoffs."},
        "transitions": {"checked": False, "note": ""},
    }
    body = {"fields": {
        "conflict_pathways": ["coach", "facilitation", "consult"],
        "child_focus": child_focus,
        "shared_concerns": "Both parents want school stability.",
        "pathway_rationale": "Coach + facilitation address communication-driven disputes.",
        "professional_summary": "Communication-driven Level 4 dynamic; structured writing + facilitation.",
        "parent_a_rating": 5, "parent_b_rating": 6, "joint_rating": 5,
        "parent_a_growth": "Send BIFF messages.\nUse portal only.",
        "parent_b_growth": "Be on time.\nCheck portal daily.",
        "safety_takeaway": "No override needed.",
        "joint_notes": "Portal-first communication.",
    }}
    r = pro.put(f"{API}/cases/{rid}/professional-report", json=body)
    assert r.status_code == 200, r.text
    view = pro.get(f"{API}/cases/{rid}/professional-report").json()
    rep = view["report"]
    assert rep["conflict_pathways"] == ["coach", "facilitation", "consult"], rep.get("conflict_pathways")
    assert rep["shared_concerns"].startswith("Both parents")
    assert rep["pathway_rationale"].startswith("Coach")
    assert rep["professional_summary"].startswith("Communication")
    cf = rep.get("child_focus") or {}
    assert cf["educational"]["checked"] is True and "Homework" in cf["educational"]["note"]
    assert cf["communication"]["checked"] is True
    assert cf["transitions"]["checked"] is False


# ----- Finalize gate: pathways selected but empty rationale -> 400 -----
def test_finalize_requires_pathway_rationale(flow):
    pro, rid = flow["pro"], flow["rid"]
    # Clear both rationale fields
    pro.put(f"{API}/cases/{rid}/professional-report", json={"fields": {
        "pathway_rationale": "", "conflict_management_rationale": ""}})
    bad = pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {"signature_name": "QA Iter58", "professional_title": "Mediator"},
        "status": "final"})
    assert bad.status_code == 400, bad.text
    assert "conflict-resolution pathways" in bad.text or "pathway" in bad.text.lower()

    # Now add rationale -> 200
    ok = pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {"signature_name": "QA Iter58", "professional_title": "Mediator",
                   "pathway_rationale": "Communication-driven conflict."},
        "status": "final"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["report"]["status"] == "final"


# ----- PDF: 7 section headings + [SELECTED] marker + child-focus note + Report principle -----
def test_pdf_has_7_sections(flow):
    pro, rid = flow["pro"], flow["rid"]
    r = pro.get(f"{API}/cases/{rid}/professional-report/pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    text = _pdf_text(r.content)
    for h in ("Case & Assessment Overview", "Parent A Perspective", "Parent B Perspective",
              "Joint Co-Parenting Assessment", "Child-Focused Legal Issues",
              "Options & Resources", "Conflict Resolution Pathways",
              "Legal Conflict & Agreement-Building Analysis", "Professional Legal Statement & Roadmap", "Concise Court Summary"):
        assert h in text, f"missing PDF heading: {h!r}; head={text[:400]!r}"
    assert "SELECTED" in text, "no SELECTED marker in PDF"
    assert "Homework routine" in text, "child-focus note missing from PDF"
    assert "REPORT PRINCIPLE" in text.upper()


# ----- Court view: statement.legal_summary carries pathways/child_focus/professional_summary -----
def test_judge_sees_new_summary_fields(flow):
    pro, rid, judge, ref = flow["pro"], flow["rid"], flow["judge"], flow["ref"]
    # statement ready
    st = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={
        "role_basis": "Court-referred mediator.",
        "process_summary": "Independent reflections.",
        "observations": "Communication-driven.",
        "safety_considerations": "", "next_steps": "Two sessions.",
        "status": "ready"})
    assert st.status_code == 200, st.text
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court",
                   json={"attest": True, "include_legal_report": True})
    assert sub.status_code == 200, sub.text
    body = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    ls = (body.get("statement") or {}).get("legal_summary") or {}
    assert ls, "legal_summary missing"
    assert isinstance(ls.get("pathways"), list) and len(ls["pathways"]) >= 3, ls.get("pathways")
    assert ls.get("pathway_rationale")
    # child_focus is a list of {label,note} for checked items only
    cf = ls.get("child_focus") or []
    assert isinstance(cf, list) and any("Homework" in (x.get("note") or "") for x in cf), cf
    assert "communication" in " ".join(x.get("label", "").lower() for x in cf)
    assert ls.get("professional_summary", "").startswith("Communication")


# ----- Public sample: /api/joint/sample-legal-lens/pdf has 7 headings -----
def test_public_sample_pdf_7_headings():
    r = requests.get(f"{API}/joint/sample-legal-lens/pdf", timeout=30)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    text = _pdf_text(r.content)
    for h in ("Case & Assessment Overview", "Parent A Perspective", "Parent B Perspective",
              "Joint Co-Parenting Assessment", "Child-Focused Legal Issues",
              "Options & Resources", "Conflict Resolution Pathways",
              "Legal Conflict & Agreement-Building Analysis", "Professional Legal Statement & Roadmap", "Concise Court Summary"):
        assert h in text, f"sample PDF missing {h!r}"
    assert "SELECTED" in text
