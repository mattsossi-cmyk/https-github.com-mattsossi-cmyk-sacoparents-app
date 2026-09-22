"""Iter-56: full court walkthrough — referral → accept → case → both parents → Legal Lens finalize (with Section 3 scale tables +
growth) → statement ready → submit-to-court with include_legal_report → judge sees frozen submission summary + PDFs."""
import os
import uuid

import pymongo
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

from casekit import new_user, complete_both

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_iter56j_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "Judge Iter56", "email": e, "password": "testpass123", "role": "judge",
        "agreements_accepted": True, "organization": "285th District Court", "pro_role": "Judge",
    })
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


@pytest.fixture(scope="module")
def flow():
    judge = _judge()
    pro = new_user(API, "professional", "Iter56 Pro")
    me = pro.get(f"{API}/auth/me").json()
    # Judge referral
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"], "cause_number": f"2026-CI-{uuid.uuid4().hex[:5]}",
        "child_initials": "E.T.",
        "parent_a_name": "Robin", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
        "parent_b_name": "Jamie", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com",
        "note": "Iter56 walkthrough",
    }).json()
    # Pro accepts
    acc = pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept")
    assert acc.status_code == 200, acc.text
    # Pro creates the case attached to the referral
    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "communication", "child_name": "E.T.",
        "parent_a_name": "Robin", "parent_a_email": ref["parent_a_email"],
        "parent_b_name": "Jamie", "parent_b_email": ref["parent_b_email"],
        "court_referral_id": ref["id"],
    })
    assert r.status_code == 200, r.text
    d = r.json()
    complete_both(API, pro, d["id"], d["invitations"])
    return {"judge": judge, "pro": pro, "ref": ref, "rid": d["id"], "case_code": d.get("case_code")}


def test_legal_lens_finalize_requires_signature(flow):
    pro, rid = flow["pro"], flow["rid"]
    # bootstrap the report
    r0 = pro.get(f"{API}/cases/{rid}/professional-report")
    assert r0.status_code == 200, r0.text
    # ratings + narrative but no signature -> 400
    bad = pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {
            "parent_a_rating": 5, "parent_b_rating": 7, "joint_rating": 6,
            "parent_a_strengths": "Consistent routines.", "parent_a_gaps": "Reactive texts.",
            "parent_a_growth": "Use BIFF messages.\nUpdate the portal weekly.\nRoute schedule swaps 48h ahead.",
            "parent_b_strengths": "Task-focused.", "parent_b_gaps": "Occasional lateness.",
            "parent_b_growth": "Arrive on time.\nCheck portal daily.\nShare medical updates.",
            "joint_strengths": "Portal-first.", "joint_gaps": "Sudden shifts.",
            "short_term_goals": "Adopt BIFF.\nUse portal only.",
            "long_term_goals": "Coordinate school activities.",
            "conflict_pathway": "mediation", "conflict_management_rationale": "Level 6 - traditional mediation.",
        },
        "status": "final",
    })
    assert bad.status_code == 400 and "Signature" in bad.text


def test_finalize_report_and_growth(flow):
    pro, rid = flow["pro"], flow["rid"]
    # Persist ratings + narrative first (previous test raised before save)
    prep = pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {
            "parent_a_rating": 5, "parent_b_rating": 7, "joint_rating": 6,
            "parent_a_growth": "Use BIFF messages.\nUpdate the portal weekly.\nRoute schedule swaps 48h ahead.",
            "parent_b_growth": "Arrive on time.\nCheck portal daily.\nShare medical updates.",
            "conflict_pathway": "mediation",
        }})
    assert prep.status_code == 200, prep.text
    # Finalize with signature
    ok = pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {"signature_name": "QA Court Pro", "professional_title": "Mediator",
                   "professional_summary": "Neutral facilitation observations."},
        "status": "final",
    })
    assert ok.status_code == 200, ok.text
    rep = ok.json()["report"]
    assert rep["status"] == "final" and rep.get("finalized_at")
    # Mark first Parent A growth line met via growth_status dict
    growth_a_line = "Use BIFF messages."
    upd = pro.put(f"{API}/cases/{rid}/professional-report", json={
        "fields": {"growth_status": {"a": {growth_a_line: True}}},
    })
    assert upd.status_code == 200, upd.text
    saved = upd.json()["report"]
    assert saved.get("growth_status", {}).get("a", {}).get(growth_a_line) is True


def test_submit_without_finalize_first_then_with(flow):
    """include_legal_report=True BEFORE the pro re-finalizes should fail if the report status is no longer final,
    but in our flow it stays final, so this really tests: the include_legal_report path 400s when the report was never
    finalized. We already finalized, so instead assert the professional statement is required first."""
    pro, rid = flow["pro"], flow["rid"]
    # Attempt submit without a ready statement
    bad = pro.post(f"{API}/joint/reports/{rid}/submit-to-court",
                   json={"attest": True, "include_legal_report": True})
    assert bad.status_code == 400 and "Professional Statement" in bad.text


def test_statement_ready_then_submit_with_legal(flow):
    pro, rid = flow["pro"], flow["rid"]
    stmt = {"role_basis": "Court-referred mediator.",
            "process_summary": "Both parents completed independent reflections.",
            "observations": "Parents align on schedule; differ on communication channel.",
            "safety_considerations": "", "next_steps": "Two facilitated sessions.",
            "status": "ready"}
    r = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=stmt)
    assert r.status_code == 200, r.text
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court",
                   json={"attest": True, "include_legal_report": True})
    assert sub.status_code == 200, sub.text
    s = sub.json()["submission"]
    assert s.get("legal_report_included") is True
    assert s.get("legal_sha256") and len(s["legal_sha256"]) == 64
    flow["packet_id"] = s["packet_id"]


def test_judge_sees_scale_and_growth(flow):
    judge, ref = flow["judge"], flow["ref"]
    view = judge.get(f"{API}/court-dashboard/cases/{ref['id']}")
    assert view.status_code == 200, view.text
    body = view.json()
    stmt = body.get("statement") or {}
    assert stmt.get("legal_report_included") is True
    ls = stmt.get("legal_summary") or {}
    assert ls, "legal_summary missing"
    assert isinstance(ls.get("scale_table"), list) and len(ls["scale_table"]) == 5
    placement = ls.get("placement") or {}
    # Ratings: A=5 -> row 2 (5-6), B=7 -> row 3 (7-8), joint=6 -> row 2 (5-6)
    assert placement.get("a") == 2, placement
    assert placement.get("b") == 3, placement
    assert placement.get("joint") == 2, placement
    # Growth A first line met
    a_growth = (ls.get("growth") or {}).get("a") or []
    assert any(g.get("met") for g in a_growth), a_growth


def _pdf_text(b: bytes) -> str:
    import io
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(b))
    return "\n".join(p.extract_text() or "" for p in r.pages)


def test_legal_pdf_and_sample_pdf(flow):
    pro, rid = flow["pro"], flow["rid"]
    pdf = pro.get(f"{API}/cases/{rid}/professional-report/pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf")
    text = _pdf_text(pdf.content)
    for needle in ("Individual Challenges & Growth", "Joint Co-Parenting Dynamic", "growth areas met ("):
        assert needle in text, f"missing {needle!r} in legal-lens PDF; got head={text[:400]!r}"
    # public sample PDF
    sp = requests.get(f"{API}/joint/sample-legal-lens/pdf")
    assert sp.status_code == 200 and sp.headers["content-type"].startswith("application/pdf")
    stext = _pdf_text(sp.content)
    assert "1 of 3 growth areas met (33%)" in stext, "sample PDF missing 33% caption"
    assert "2 of 3 growth areas met (67%)" in stext, "sample PDF missing 67% caption"


def test_submit_before_finalize_400(flow):
    """Fresh referral+case: try include_legal_report=True while Legal Lens is not finalized -> 400."""
    judge = flow["judge"]
    pro = new_user(API, "professional", "Iter56 Pro 2")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"], "cause_number": f"2026-CI-{uuid.uuid4().hex[:5]}",
        "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
        "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com"}).json()
    pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept")
    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "communication", "child_name": "K",
        "parent_a_name": "A", "parent_a_email": ref["parent_a_email"],
        "parent_b_name": "B", "parent_b_email": ref["parent_b_email"],
        "court_referral_id": ref["id"]}).json()
    rid = r["id"]
    complete_both(API, pro, rid, r["invitations"])
    # statement ready
    ok = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={
        "role_basis": "Mediator.", "process_summary": "Independent reflections.",
        "observations": "Aligned on schedule.", "next_steps": "Two sessions.",
        "safety_considerations": "", "status": "ready"})
    assert ok.status_code == 200
    # bootstrap the report but DO NOT finalize
    pro.get(f"{API}/cases/{rid}/professional-report")
    bad = pro.post(f"{API}/joint/reports/{rid}/submit-to-court",
                   json={"attest": True, "include_legal_report": True})
    assert bad.status_code == 400, bad.text
    assert "Finalize" in bad.text or "finaliz" in bad.text.lower()
