"""Iter-112 Phase 5: training gate (428), supervisor sign-off to lower Red, admin safety audit CSV, export scan on Legal Lens / Individual / court packet."""
import os
import uuid

import pymongo
import pytest
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
from test_iter108_required_step import _case  # noqa: E402
from test_iter110_family_checkin import ALL_NO  # noqa: E402

import pro_training as pt  # noqa: E402
import safety_review as sr  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _ack(s):
    assert s.post(f"{API}/professional-training/acknowledge", json={"version": pt.TRAINING_VERSION, "acknowledged": True}).json()["ok"]


def _untrain(s):
    uid = s.get(f"{API}/auth/me").json()["id"]
    _db.users.update_one({"_id": uid}, {"$unset": {"safety_training": ""}})


def test_training_prompt_never_blocks_and_ack_is_recorded():
    pro, pa, pb, rid = _case()
    pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO, "stalk": "In the last 12 months"}, "safe_contact": None})
    _untrain(pro)
    t = pro.get(f"{API}/professional-training").json()
    assert t["current"] is False and len(t["training"]["modules"]) == 6 and t["training"]["version"] == pt.TRAINING_VERSION
    # Owner 2026-10-17: training is a prompt, never a gate — unacknowledged professionals are NOT blocked
    for path in (f"/joint/reports/{rid}/safety-screening/a/responses", f"/joint/reports/{rid}/safety-review", f"/joint/reports/{rid}/safety-review/provisions.pdf"):
        assert pro.get(f"{API}{path}").status_code == 200, path
    assert pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "green", "reasons": []}).status_code == 200
    assert pro.post(f"{API}/professional-training/acknowledge", json={"version": "old", "acknowledged": True}).status_code == 409
    assert pro.post(f"{API}/professional-training/acknowledge", json={"version": pt.TRAINING_VERSION, "acknowledged": False}).status_code == 400
    assert pa.post(f"{API}/professional-training/acknowledge", json={"version": pt.TRAINING_VERSION, "acknowledged": True}).status_code == 403
    _ack(pro)
    me = pro.get(f"{API}/auth/me").json()
    assert me["safety_training_version"] == pt.TRAINING_VERSION and me["is_supervisor"] is False
    assert pro.get(f"{API}/joint/reports/{rid}/safety-screening/a/responses").status_code == 200
    assert pro.get(f"{API}/joint/reports/{rid}/safety-review").status_code == 200
    # parents are never gated by training
    assert pa.get(f"{API}/joint/reports/{rid}/safety-screening").status_code == 200


def test_lowering_red_requires_second_supervising_professional():
    pro, pa, pb, rid = _case()
    _ack(pro)
    assert pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "red", "reasons": [sr.REASONS[0]]}).status_code == 200
    # raising / staying red never needs sign-off; lowering does
    r = pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "amber", "reasons": [sr.REASONS[7]]})
    assert r.status_code == 200 and r.json()["requires_supervisor"] is True and r.json()["concern_level"] == "red"
    doc = _db.joint_reports.find_one({"id": rid}, {"safety_review": 1, "safety_review_pending_lower": 1})
    assert doc["safety_review"]["concern_level"] == "red" and doc["safety_review_pending_lower"]["concern_level"] == "amber"
    # requester cannot sign off their own request, even if made supervisor
    pro_id = pro.get(f"{API}/auth/me").json()["id"]
    _db.users.update_one({"_id": pro_id}, {"$set": {"is_supervisor": True}})
    r = pro.post(f"{API}/joint/reports/{rid}/safety-review/supervisor-signoff", json={"approve": True, "note": "ok"})
    assert r.status_code == 403 and "second professional" in r.json()["detail"]
    _db.users.update_one({"_id": pro_id}, {"$set": {"is_supervisor": False}})
    # a second professional who is NOT a supervisor is refused; parents refused
    pro2, _a, _b, _rid2 = _case()
    _ack(pro2)
    p2 = pro2.get(f"{API}/auth/me").json()["id"]
    _db.joint_reports.update_one({"id": rid}, {"$addToSet": {"shared_with": p2}})  # share the case so pro2 can see it
    assert pro2.post(f"{API}/joint/reports/{rid}/safety-review/supervisor-signoff", json={"approve": True, "note": "ok"}).status_code == 403
    assert pa.post(f"{API}/joint/reports/{rid}/safety-review/supervisor-signoff", json={"approve": True, "note": "ok"}).status_code in (403, 404)
    _db.users.update_one({"_id": p2}, {"$set": {"is_supervisor": True}})
    d = pro2.get(f"{API}/joint/reports/{rid}/safety-review").json()
    assert d["pending_lower"]["requested_by"] == pro_id and d["can_sign_off"] is True
    assert pro2.post(f"{API}/joint/reports/{rid}/safety-review/supervisor-signoff", json={"approve": True, "note": ""}).status_code == 400
    r = pro2.post(f"{API}/joint/reports/{rid}/safety-review/supervisor-signoff", json={"approve": True, "note": "Reviewed with the assigned professional."})
    assert r.status_code == 200 and r.json()["concern_level"] == "amber"
    doc = _db.joint_reports.find_one({"id": rid}, {"safety_review": 1, "safety_review_pending_lower": 1})
    assert doc["safety_review"]["concern_level"] == "amber" and doc["safety_review"]["supervisor_signoff"]["by"] == p2 and "safety_review_pending_lower" not in doc
    kinds = [e["action"] for e in _db.access_events.find({"report_id": rid, "kind": "supervisor_signoff"})]
    assert any("Requested lowering" in k for k in kinds) and any("approved lowering" in k for k in kinds)
    # decline path keeps red
    pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "red", "reasons": [sr.REASONS[0]]})
    pro.put(f"{API}/joint/reports/{rid}/safety-review", json={"concern_level": "none", "reasons": [sr.REASONS[7]]})
    r = pro2.post(f"{API}/joint/reports/{rid}/safety-review/supervisor-signoff", json={"approve": False, "note": "Not yet."})
    assert r.status_code == 200, r.text
    assert r.json()["concern_level"] == "red"
    assert _db.joint_reports.find_one({"id": rid}, {"safety_review": 1})["safety_review"]["concern_level"] == "red"


def test_admin_audit_endpoints_admin_only_and_supervisor_patch():
    pro, pa, pb, rid = _case()
    for path in ("/admin/safety-audit", "/admin/safety-audit.csv"):
        assert pro.get(f"{API}{path}").status_code == 403 and pa.get(f"{API}{path}").status_code == 403
    assert pro.patch(f"{API}/admin/professionals/{uuid.uuid4()}/supervisor", json={"is_supervisor": True}).status_code == 403
    assert "safety_review" in pt.AUDIT_KINDS and "export_scan_block" in pt.AUDIT_KINDS and "supervisor_signoff" in pt.AUDIT_KINDS


def test_export_scan_wired_into_legal_lens_individual_and_court_packet():
    import inspect

    import court_packets
    import court_workflow
    import legal_lens
    assert "assert_export_clean" in inspect.getsource(court_packets._pdf_response)
    src = inspect.getsource(court_workflow)
    assert src.count("assert_export_clean(") >= 3 and "Individual Perspective Reports" in src
    assert inspect.getsource(legal_lens).count("assert_export_clean(") >= 2
    # a clean export passes; a Legal Lens export with screening wording is blocked
    pro, pa, pb, rid = _case()
    _ack(pro)
    pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO, "stalk": "In the last month"}, "safe_contact": None})
    r = pro.get(f"{API}/cases/{rid}/professional-report/pdf")
    assert r.status_code in (200, 400, 404), r.text  # 400/404 = report prerequisites, not a scan block
    assert r.status_code != 409
    with pytest.raises(Exception) as ei:
        sr.assert_export_clean(_pdf_with("Has the other parent pushed, hit, kicked, or physically hurt you? In the last month"), "x")
    assert getattr(ei.value, "status_code", None) == 409
    sr.assert_export_clean(_pdf_with("Parent A: safety screening - Received (Family check-in). Tier 3 - priority follow-up."), "x")


def _pdf_with(text: str) -> bytes:
    from pdf_common import _new_pdf, _s
    pdf = _new_pdf()
    pdf.add_page()
    pdf.set_font(pdf.font_family or "helvetica", "", 11)
    pdf.multi_cell(0, 6, _s(text))
    return bytes(pdf.output())
