"""Judicial Portal: case view, court–professional thread + AI summary, extended statement, Case ID assigned at referral."""
import os
import uuid

import pymongo
import requests

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_pjudge_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={"name": "Judge Portal", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "Court", "pro_role": "Judge"}).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


def _flow() -> tuple:
    judge = _judge()
    pro = new_user(API, "professional", "Portal Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-P{uuid.uuid4().hex[:4]}", "requested_reports": ["education"]}).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").status_code == 200
    case = pro.post(f"{API}/joint/reports/professional", json={"subject": "education", "child_name": "Kai", "parent_a_name": "A", "parent_a_email": f"t_a{uuid.uuid4().hex[:6]}@example.com",
                                                             "parent_b_name": "B", "parent_b_email": f"t_b{uuid.uuid4().hex[:6]}@example.com", "court_referral_id": ref["id"]})
    assert case.status_code == 200, case.text
    return judge, pro, ref, case.json()


def test_case_id_assigned_at_referral_and_reused_by_case() -> None:
    judge, _pro, ref, case = _flow()
    assert ref["case_code"] and ref["case_code"].startswith("SA-") and "-EDU-" in ref["case_code"]
    assert case["case_code"] == ref["case_code"]
    view = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert view["case_code"] == ref["case_code"]


def test_judicial_case_view_is_procedural_until_submission() -> None:
    judge, pro, ref, case = _flow()
    v = judge.get(f"{API}/court-dashboard/cases/{ref['id']}")
    assert v.status_code == 200, v.text
    d = v.json()
    assert [c["label"] for c in d["checklist"]][:3] == ["Court referral sent", "Professional accepted", "Parents invited"]
    assert d["checklist"][1]["done"] is True and d["reports"] == [] and d["statement"] is None
    assert d["parents_participating"] == 0 and d["counts"]["completion_pct"] == 0
    assert "responses" not in d and "answers'" not in str(d)
    assert pro.get(f"{API}/court-dashboard/cases/{ref['id']}").status_code == 403
    other = _judge()
    assert other.get(f"{API}/court-dashboard/cases/{ref['id']}").status_code == 404


def test_court_thread_both_directions_with_summary_and_permissions() -> None:
    judge, pro, ref, _case = _flow()
    r = judge.post(f"{API}/court-dashboard/cases/{ref['id']}/messages", json={"text": "Please provide an updated status concerning completion of the educational assessments."})
    assert r.status_code == 200, r.text
    assert r.json()["message"]["from_role"] == "court" and r.json()["summary"]["message_count"] == 1
    r2 = pro.post(f"{API}/professional/court-referrals/{ref['id']}/messages", json={"text": "Both parents have been invited. The Joint Educational Report will follow completion."})
    assert r2.status_code == 200, r2.text
    s = r2.json()["summary"]
    assert s["message_count"] == 2 and s["summary"] and s["disclaimer"]
    th = judge.get(f"{API}/court-dashboard/cases/{ref['id']}/messages").json()
    assert [m["from_role"] for m in th["messages"]] == ["court", "professional"]
    assert judge.post(f"{API}/court-dashboard/cases/{ref['id']}/messages", json={"text": "  "}).status_code == 400
    stranger = new_user(API, "professional", "Stranger")
    assert stranger.get(f"{API}/professional/court-referrals/{ref['id']}/messages").status_code == 404
    log = judge.get(f"{API}/court-dashboard/referrals/{ref['id']}/communications").json()
    assert any(c["kind"] == "court_message" for c in log)
    view = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert view["communication_summary"]["message_count"] == 2


def test_statement_role_and_materials_persist() -> None:
    _judge_s, pro, _ref, case = _flow()
    cfg = pro.get(f"{API}/joint/reports/{case['id']}/professional-statement").json()
    assert "Amicus Attorney" in cfg["roles"] and "Parent A Assessment" in cfg["materials"]
    body = {"role": "Mediator", "materials_reviewed": ["Parent A Assessment", "Joint Report", "Bogus"], "role_basis": "Court referral", "alignment_areas": "School stability", "status": "draft"}
    r = pro.put(f"{API}/joint/reports/{case['id']}/professional-statement", json=body)
    assert r.status_code == 200, r.text
    st = r.json()["statement"]
    assert st["role"] == "Mediator" and st["materials_reviewed"] == ["Parent A Assessment", "Joint Report"] and st["alignment_areas"] == "School stability"


def test_framework_from_dynamic_scale_in_statement_and_pdf() -> None:
    import io
    import fitz
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from coparenting_tiers import tier_for, framework_block

    assert tier_for(1)["key"] == "high_risk" and tier_for(6)["key"] == "moderate" and tier_for(10)["key"] == "collaborative"
    fb = framework_block(2, {"techniques": [tier_for(2)["techniques"][0]]})
    assert len(fb["techniques"]) == 1 and fb["safety_alert"] is True and len(fb["resources"]) == 4

    _judge_s, pro, _ref, case = _flow()
    cfg = pro.get(f"{API}/joint/reports/{case['id']}/professional-statement").json()
    assert len(cfg["tiers"]) == 3 and cfg["suggested_score"] is None  # parents not done yet
    body = {"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "dynamic_score": 5,
            "framework_choices": {"tools": [tier_for(5)["tools"][0]]}, "status": "draft"}
    st = pro.put(f"{API}/joint/reports/{case['id']}/professional-statement", json=body).json()["statement"]
    assert st["framework"]["label"].startswith("Level 4-6") and st["framework"]["tools"] == [tier_for(5)["tools"][0]] and len(st["framework"]["techniques"]) == 4
    pdf = pro.get(f"{API}/joint/reports/{case['id']}/professional-statement.pdf")
    assert pdf.status_code == 200
    text = "".join(pg.get_text() for pg in fitz.open(stream=io.BytesIO(pdf.content), filetype="pdf"))
    assert "CO-PARENTING ABILITY LEVEL" in text and "Level 5 / 10" in text and "24-Hour Cooling-Off Rule" in text and "Professional Report" in text
    assert "CONFLICT-MANAGEMENT TECHNIQUES" in text and "OPTIONS & RESOURCES" in text


def test_professional_report_infuses_joint_findings_and_hides_options_from_parents() -> None:
    import io
    import fitz
    from casekit import completed_case
    pro, pa, _pb, case = completed_case(API, "education")[:4]
    rid = case["id"]
    rep = pa.get(f"{API}/joint/reports/{rid}/report").json()
    assert "options" not in rep and rep["alignment_map"]
    cfg = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()
    f = cfg["findings"]
    assert f is not None and cfg["suggested_score"]["score"] >= 1 and "Level" in cfg["suggested_score"]["label"]
    assert all(d.startswith("Parents expressed different perspectives") for d in f["differences"])
    assert (cfg["subject_options"] == []) == (len(f["differences"]) == 0)
    body = {"role": "Mediator", "role_basis": "Agreement of the parties", "process_summary": "Both parents completed the education assessment.", "observations": "Neutral.",
            "next_steps": "One facilitated session.", "dynamic_score": cfg["suggested_score"]["score"], "framework_custom": {"resources": ["Local parenting class (Tuesdays)"]}, "status": "ready"}
    st = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=body).json()["statement"]
    assert st["dynamic_score"] == body["dynamic_score"] and st["framework_custom"] == body["framework_custom"]
    got = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()["statement"]
    assert got["dynamic_score"] == body["dynamic_score"] and got["framework_custom"]["resources"] == ["Local parenting class (Tuesdays)"]
    assert "Local parenting class (Tuesdays)" in st["framework"]["resources"] and st["framework"]["subject_options"] == cfg["subject_options"]
    text = "".join(pg.get_text() for pg in fitz.open(stream=io.BytesIO(pro.get(f"{API}/joint/reports/{rid}/professional-statement.pdf").content), filetype="pdf"))
    assert "JOINT ASSESSMENT FINDINGS" in text and "Local parenting class" in text and "CASE & REFERRAL" in text
    assert "6. PARENT ALIGNMENT" in text and "7. CONFLICT MANAGEMENT" in text and "8. ROADMAP" in text and "9. PROFESSIONAL SUMMARY" in text
    st_pa = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**body, "partial_alignment": "Both value routine.", "alignment_summary": "Aligned on routine; differ on tutoring."}).json()["statement"]
    assert st_pa["partial_alignment"] == "Both value routine." and st_pa["alignment_summary"].startswith("Aligned")
    for c in (pa, _pb):
        assert c.get(f"{API}/joint/reports/{rid}/professional-statement").status_code == 404
    # personal resource library auto-appears in the framework and can be unticked
    lib = pro.put(f"{API}/me/resource-library", json={"resources": ["Westside Family Center (Tuesdays)", " "], "tools": [], "bogus": ["x"]}).json()
    assert lib == {"resources": ["Westside Family Center (Tuesdays)"], "tools": [], "techniques": []}
    assert pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()["library"] == lib
    st2 = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**body, "framework_custom": {}}).json()["statement"]
    assert "Westside Family Center (Tuesdays)" in st2["framework"]["resources"]
    st3 = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**body, "framework_custom": {}, "framework_choices": {"resources": []}}).json()["statement"]
    assert st3["framework"]["resources"] == []
    assert pa.get(f"{API}/me/resource-library").status_code == 403
    joint_pdf = "".join(pg.get_text() for pg in fitz.open(stream=io.BytesIO(pa.get(f"{API}/joint/reports/{rid}/pdf").content), filetype="pdf"))
    assert "Options and Resources" not in joint_pdf


def test_level_change_note_and_org_library() -> None:
    from casekit import complete_both
    judge, pro, ref, case = _flow()
    rid = case["id"]
    complete_both(API, pro, rid, case["invitations"])
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    me = pro.get(f"{API}/auth/me").json()
    org = f"Org {uuid.uuid4().hex[:6]}"
    db.users.update_one({"_id": me["id"]}, {"$set": {"profile.organization": org}})
    # org library shared with a colleague in the same organization
    assert pro.put(f"{API}/org/resource-library", json={"resources": ["Shared county mediation clinic"]}).json()["resources"] == ["Shared county mediation clinic"]
    colleague = new_user(API, "professional", "Colleague")
    cid = colleague.get(f"{API}/auth/me").json()["id"]
    db.users.update_one({"_id": cid}, {"$set": {"profile.organization": org.upper()}})
    lib = colleague.get(f"{API}/me/resource-library").json()
    assert lib["org_library"]["resources"] == ["Shared county mediation clinic"] and lib["organization"] == org.upper()
    stranger = new_user(API, "professional", "Stranger")
    assert stranger.put(f"{API}/org/resource-library", json={"resources": ["x"]}).status_code == 400
    base = {"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready"}
    st = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**base, "dynamic_score": 3}).json()["statement"]
    assert "Shared county mediation clinic" in st["framework"]["resources"] and st["level_changed_from"] is None
    assert pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True}).status_code == 200
    # level change without a note is blocked when marking ready
    r = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**base, "dynamic_score": 6})
    assert r.status_code == 400 and "changed from 3 to 6" in r.json()["detail"]
    st = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**base, "dynamic_score": 6, "level_change_note": "Parents completed two facilitated sessions; written-only scheduling in use."}).json()["statement"]
    assert st["level_changed_from"] == 3
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True}).json()["submission"]
    assert sub["level_changed_from"] == 3 and sub["level_change_note"].startswith("Parents completed")
    hist = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()["level_history"]
    assert [(h["version"], h["score"], h["changed_from"]) for h in hist] == [(1, 3, None), (2, 6, 3)] and hist[1]["note"].startswith("Parents completed")
    # same level again → no note required
    assert pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**base, "dynamic_score": 6}).status_code == 200
