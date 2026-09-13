"""Iteration 39: verify PDF copyright footer on all PDFs, transmittal 404 for non-owner, /api/health build,
judge dashboard revoked chip, and the 400 responses for the admin decline/register-without-organization endpoints."""
import hashlib
import os
import uuid

import pymongo
import pymupdf
import pytest
import requests

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
LETTER = "Your Honor, this iteration-39 packet accompanies the co-parenting alignment report. Please review the enclosed documents at your convenience and reply if you require clarification."
FOOTER = "\u00a9 2026 sacoparentsalign.com"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _admin():
    s = requests.Session()
    email = f"t_admin39_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Admin39", "email": email, "password": "testpass123",
                                             "role": "professional", "agreements_accepted": True})
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": email}, {"$set": {"role": "admin", "approved": True}})
    return s


def _assert_footer_all_pages(content: bytes, label: str) -> None:
    doc = pymupdf.open(stream=content, filetype="pdf")
    assert len(doc) >= 1, f"{label}: no pages"
    for i, page in enumerate(doc):
        txt = page.get_text()
        assert FOOTER in txt, f"{label}: page {i + 1} missing footer copyright. Text head: {txt[:200]!r}"


# ---------- /api/health build ----------
def test_health_build() -> None:
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["build"] .startswith("2026-")


# ---------- Register a judge without organization ----------
def test_register_judge_without_org_400() -> None:
    e = f"t_jnoorg_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": "J", "email": e, "password": "testpass123",
                                                    "role": "judge", "agreements_accepted": True})
    assert r.status_code == 400


def test_register_judge_ok_unapproved() -> None:
    e = f"t_jok_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": "Judge OK", "email": e, "password": "testpass123",
                                                    "role": "judge", "agreements_accepted": True,
                                                    "organization": "285th District Court", "pro_role": "Judge"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["role"] == "judge" and not d["approved"]


# ---------- Court-dashboard as professional -> 403 ----------
@pytest.fixture(scope="module")
def bundle():
    """Create case → send packet → approved judge sees it. Returns everything for later tests."""
    pro, _pa, _pb, d, _ = completed_case(API)
    rid = d["id"]
    judge_email = f"t_j39_{uuid.uuid4().hex[:8]}@example.com"
    judge = requests.Session()
    reg = judge.post(f"{API}/auth/register", json={"name": "Judge39", "email": judge_email, "password": "testpass123",
                                                    "role": "judge", "agreements_accepted": True,
                                                    "organization": "285th District Court", "pro_role": "Judge"})
    assert reg.status_code == 200, reg.text
    jid = reg.json()["id"]

    # Unapproved judge dashboard
    r = judge.get(f"{API}/court-dashboard/packets").json()
    assert not r["approved"] and r["packets"] == []

    # Pro cannot access court-dashboard
    assert pro.get(f"{API}/court-dashboard/packets").status_code == 403

    admin = _admin()
    lst = admin.get(f"{API}/admin/judges").json()
    assert any(j["id"] == jid for j in lst)
    # Decline without reason -> 400
    assert admin.post(f"{API}/admin/judges/{jid}/decline", json={}).status_code == 400
    # Now approve
    ap = admin.post(f"{API}/admin/judges/{jid}/approve")
    assert ap.status_code == 200 and ap.json()["approved"]

    # Pro sends the packet
    p = pro.post(f"{API}/joint/reports/{rid}/court-packets", json={
        "judge_name": "Judge39", "judge_email": judge_email, "court_name": "285th District Court",
        "cause_number": "2026-CI-00939", "cover_letter": LETTER, "attest": True})
    assert p.status_code == 200, p.text
    packet = p.json()
    return {"pro": pro, "judge": judge, "rid": rid, "packet": packet, "admin": admin}


def test_transmittal_pdf_404_for_non_owner(bundle) -> None:
    pid = bundle["packet"]["id"]
    # Register a stranger pro
    other = requests.Session()
    e = f"t_other39_{uuid.uuid4().hex[:8]}@example.com"
    other.post(f"{API}/auth/register", json={"name": "Other", "email": e, "password": "testpass123",
                                             "role": "professional", "agreements_accepted": True})
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    r = other.get(f"{API}/court-packets/{pid}/transmittal.pdf")
    assert r.status_code == 404


def test_transmittal_pdf_owner_has_footer_and_cause(bundle) -> None:
    pid = bundle["packet"]["id"]
    r = bundle["pro"].get(f"{API}/court-packets/{pid}/transmittal.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    assert len(doc) == 1
    text = doc[0].get_text()
    assert "Certificate of Transmittal" in text
    assert "2026-CI-00939" in text
    assert FOOTER in text


# ---------- Judge PDF footer on every page ----------
def test_judge_packet_pdf_footer(bundle) -> None:
    pid = bundle["packet"]["id"]
    r = bundle["judge"].get(f"{API}/court-dashboard/packets/{pid}/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    _assert_footer_all_pages(r.content, "judge-packet-pdf")


# ---------- Joint report PDF footer ----------
def test_joint_report_pdf_footer(bundle) -> None:
    r = bundle["pro"].get(f"{API}/joint/reports/{bundle['rid']}/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    _assert_footer_all_pages(r.content, "joint-report-pdf")


# ---------- Session prep PDF footer ----------
def test_session_prep_pdf_footer(bundle) -> None:
    r = bundle["pro"].get(f"{API}/joint/reports/{bundle['rid']}/session-prep.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    _assert_footer_all_pages(r.content, "session-prep-pdf")


# ---------- Methodology PDF footer ----------
def test_methodology_pdf_footer() -> None:
    r = requests.get(f"{API}/methodology/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    _assert_footer_all_pages(r.content, "methodology-pdf")


# ---------- Token flow after revoke: preview state 'revoked' + judge dashboard chip Revoked ----------
def test_revoke_updates_preview_and_judge_dashboard(bundle) -> None:
    pid = bundle["packet"]["id"]
    token = bundle["packet"]["link"].rsplit("/court/", 1)[1]

    # Reset code so we can unlock (proves token flow works pre-revoke)
    _db().court_packets.update_one({"id": pid}, {"$set": {"code_hash": hashlib.sha256(b"123456").hexdigest()}})
    pv = requests.get(f"{API}/court/{token}/preview").json()
    assert pv["state"] == "active"
    u = requests.post(f"{API}/court/{token}/unlock", json={"code": "123456"})
    assert u.status_code == 200
    access = u.json()["access"]
    view = requests.get(f"{API}/court/{token}", headers={"X-Court-Access": access})
    assert view.status_code == 200

    # Revoke
    rv = bundle["pro"].post(f"{API}/court-packets/{pid}/revoke")
    assert rv.status_code == 200 and rv.json()["status"] == "revoked"

    # Preview shows revoked
    pv2 = requests.get(f"{API}/court/{token}/preview").json()
    assert pv2["state"] == "revoked"

    # Judge dashboard should show state 'revoked' (chip Revoked)
    dash = bundle["judge"].get(f"{API}/court-dashboard/packets").json()
    row = next((x for x in dash["packets"] if x["id"] == pid), None)
    assert row is not None
    assert row["state"] == "revoked"


# ---------- Judge isolation: unrelated judge sees no packet ----------
def test_second_judge_isolation(bundle) -> None:
    pid = bundle["packet"]["id"]
    other = requests.Session()
    e = f"t_j39b_{uuid.uuid4().hex[:8]}@example.com"
    other.post(f"{API}/auth/register", json={"name": "Judge39B", "email": e, "password": "testpass123",
                                             "role": "judge", "agreements_accepted": True,
                                             "organization": "Court", "pro_role": "Judge"})
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    dash = other.get(f"{API}/court-dashboard/packets").json()
    assert dash["approved"] and dash["packets"] == []
    assert other.get(f"{API}/court-dashboard/packets/{pid}").status_code == 404
