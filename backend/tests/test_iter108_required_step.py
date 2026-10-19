"""Iter-108: Option A — the Start-with-Safety STEP is required, the ANSWERS are not."""
import os
import re
import uuid

from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from casekit import new_user  # noqa: E402

from pdf_individual import build_individual_reports_pdf  # noqa: E402
from safety_screening import receipt  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
ANSWERS = {k: "Neutral text." for k in ("needs_most", "working_well", "concerns", "improve", "options", "other_parent")}


def _case():
    pro = new_user(API, "professional", "Gate Pro", email=f"t_{uuid.uuid4().hex[:8]}@example.com")
    d = pro.post(f"{API}/joint/reports/professional", json={"subject": "education", "child_name": "G.", "parent_a_name": "Alex", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
                                                             "parent_b_name": "Blake", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com"}).json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    emails = {i["role"]: i["invitee_email"] for i in d["invitations"]}
    ses = {}
    for role in ("a", "b"):
        s = new_user(API, "parent", f"Parent {role.upper()}", email=emails[role], invite=toks[role])
        assert s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]}).json().get("ok")
        ses[role] = s
    pro.post(f"{API}/professional-training/acknowledge", json={"version": __import__("pro_training").TRAINING_VERSION, "acknowledged": True})
    return pro, ses["a"], ses["b"], d["id"]


def test_gate_blocks_assessment_until_step_satisfied_identically_for_both_parents():
    pro, pa, pb, rid = _case()
    for s in (pa, pb):
        r = s.put(f"{API}/joint/reports/{rid}/responses", json={"answers": ANSWERS})
        assert r.status_code == 403 and r.json()["detail"] == "Please go through the Start with Safety step before answering the assessment."
        assert s.get(f"{API}/joint/reports/{rid}").json()["safety_step_satisfied"] is False
    # Parent A declines → step satisfied, status Declined with date; assessment opens.
    assert pa.post(f"{API}/joint/reports/{rid}/safety-screening/decline").json()["entry_status"] == "declined"
    assert pa.get(f"{API}/joint/reports/{rid}").json()["safety_step_satisfied"] is True
    assert pa.put(f"{API}/joint/reports/{rid}/responses", json={"answers": ANSWERS}).status_code == 200
    # Parent B completes with every question skipped → Completed; assessment opens.
    assert pb.put(f"{API}/joint/reports/{rid}/safety-screening/choose", json={"version": "A"}).status_code == 200
    assert pb.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {}, "safe_contact": None}).status_code == 200
    assert pb.put(f"{API}/joint/reports/{rid}/responses", json={"answers": ANSWERS}).status_code == 200
    roles = pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()["roles"]
    assert roles["a"]["entry_status"] == "declined" and roles["a"]["entry_label"].startswith("Declined · ") and roles["a"]["received"] is False
    assert roles["b"]["entry_status"] == "completed" and roles["b"]["entry_label"].startswith("Received · ") and roles["b"]["received"] is True
    assert roles["a"]["receipt"].startswith(f"{roles['a']['name']}: safety screening — Declined (parent chose not to answer at this time, ")
    assert not re.search(r"refus|fail|non-?compl|fault|risk", roles["a"]["receipt"], re.I)
    # No leakage: each parent's own report view carries only their own step flag, never the other parent's status.
    for s, other in ((pa, "b"), (pb, "a")):
        body = s.get(f"{API}/joint/reports/{rid}").text
        assert "safety_declined" not in body and "entry_status" not in body and "entry_label" not in body
        assert s.get(f"{API}/joint/reports/{rid}/safety-screening/{other}/responses").status_code in (403, 404)
    # No notification of the decline to the other parent (no email record for the decline).
    assert pro.post(f"{API}/joint/reports/{rid}/safety-screening/decline").status_code == 403


def test_report_wording_neutral_for_declined_and_not_started():
    assert receipt(None, "Alex") == "Alex: safety screening — Not started."
    line = receipt(None, "Alex", "2026-10-14T10:00:00+00:00")
    assert line == "Alex: safety screening — Declined (parent chose not to answer at this time, 2026-10-14)."
    doc = {"id": "x", "case_code": "C", "participants": {"a": {"name": "Alex"}, "b": {"name": "Blake"}}, "responses": {"a": {"answers": {}}, "b": {"answers": {}}},
           "safety_declined": {"a": "2026-10-14T10:00:00+00:00"}, "professional_statement": {"observations": "ok"}}
    import fitz
    with fitz.open(stream=build_individual_reports_pdf(doc, {"name": "Pro"}), filetype="pdf") as pdf:
        t = " ".join("\n".join(p.get_text() for p in pdf).split())
    assert "Parent A: safety screening — Declined (parent chose not to answer at this time, 2026-10-14)" in t and "Parent B: safety screening — Not started." in t


def test_professional_access_notice_on_step_screen():
    from pathlib import Path

    from safety_screening import PROFESSIONAL_ACCESS_NOTICE, STEP_NOTICE_VERSION
    exact = PROFESSIONAL_ACCESS_NOTICE
    assert exact.startswith("Who can see your information") and "their supervisor" not in exact and "professionals assigned to your case" in exact
    assert exact in Path("/app/frontend/src/content/safetyEntry.js").read_text(encoding="utf-8")
    page = Path("/app/frontend/src/pages/StartWithSafety.jsx").read_text(encoding="utf-8")
    assert 'data-testid="professional-access-notice"' in page and page.index("professional-access-notice") < page.index("start-safety-decline-btn")
    pro, pa, pb, rid = _case()
    e = pa.get(f"{API}/me/safety-entry").json()
    assert e["notice"] == exact and e["needs_notice"] is True and e["notice_version"] == STEP_NOTICE_VERSION
    assert pa.post(f"{API}/me/safety-entry/ack-notice").json()["notice_version"] == STEP_NOTICE_VERSION
    assert pa.get(f"{API}/me/safety-entry").json()["needs_notice"] is False
    # Already-satisfied parent still gets the screen again after a version bump (needs_notice drives it), privacy notice untouched.
    assert pb.post(f"{API}/joint/reports/{rid}/safety-screening/decline").json()["entry_status"] == "declined"
    eb = pb.get(f"{API}/me/safety-entry").json()
    assert eb["status"] == "declined" and eb["needs_notice"] is True
    assert "2026-10-19.1" in Path("/app/backend/privacy_notice.py").read_text(encoding="utf-8")
