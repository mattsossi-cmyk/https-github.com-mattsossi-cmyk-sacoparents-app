"""Iter 65: safety gate — parent safety screen blocks sharing (409) and flags the case; agreement renders Parallel Parenting variant for the court."""
import pymupdf
from casekit import complete_both
from test_judicial_portal import _flow
from test_legal_report import API
from test_iter64_agreement_to_court import AGR_FIELDS, _agreement_answers

SAFE = {"fear": False, "threats": False, "control": False}


def test_parent_safety_screen_routes_to_safety_pathway() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    pa, pb = complete_both(API, pro, rid, case["invitations"])
    # unanswered safety questions -> 400
    pa.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS})
    assert pa.post(f"{API}/joint/reports/{rid}/foundation/share").status_code == 400
    # flagged -> 409 + case flagged for the professional
    r = pa.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS, "safety": {"fear": True, "threats": False, "control": False}})
    assert r.json()["statement"]["safety_flagged"] is True
    r = pa.post(f"{API}/joint/reports/{rid}/foundation/share")
    assert r.status_code == 409 and "safety" in r.json()["detail"].lower()
    det = pro.get(f"{API}/joint/reports/{rid}").json()
    assert det["safety_route"] is True and det["foundation_statements"] == []
    # professional's submit payload flags the agreement safety gate
    ps = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()
    assert ps["agreement_safety"]["flagged"] is True and ps["agreement_safety"]["reasons"]
    # safe answers -> share works
    pb.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS, "safety": SAFE})
    assert pb.post(f"{API}/joint/reports/{rid}/foundation/share").status_code == 200


def test_agreement_uses_parallel_parenting_when_flagged() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    pa, pb = complete_both(API, pro, rid, case["invitations"])
    emails = {i["role"]: i["invitee_email"] for i in case["invitations"]}
    ag = pro.post(f"{API}/joint/agreements", json={"child_name": "Emma", "parent_a_name": "Parent A", "parent_a_email": emails["a"], "parent_b_name": "Parent B", "parent_b_email": emails["b"]}).json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in ag["invitations"]}
    answers = _agreement_answers()
    for s, role in ((pa, "a"), (pb, "b")):
        s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]})
        s.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS, "safety": SAFE})
        assert s.put(f"{API}/joint/reports/{ag['id']}/responses", json={"answers": answers}).status_code == 200
    # professional records high risk in the Legal Lens for the joint case
    assert pro.get(f"{API}/cases/{rid}/professional-report").status_code == 200
    r = pro.put(f"{API}/cases/{rid}/professional-report", json={"fields": {"risk_screening": {"threats": {"level": "High Risk", "note": "documented threats"}}, "joint_process_appropriate": "No — safety concerns"}})
    assert r.status_code == 200, r.text[:200]
    ps = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()
    assert ps["agreement_safety"]["flagged"] is True
    # own-case agreement PDF is the Parallel Parenting variant
    pdf = pro.get(f"{API}/joint/reports/{ag['id']}/pdf")
    text = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "Safety Override" in text and "Parallel Parenting" in text and "Parent-to-parent discussion" not in text
    # court submission carries the override to the judge
    base = {"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready", "dynamic_score": 3}
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=base)
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "agreement_report_id": ag["id"]})
    assert sub.status_code == 200, sub.text[:300]
    assert sub.json()["submission"]["agreement_card"]["safety_override"]["banner"].startswith("Safety Override")
    cd = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert cd["statement"]["agreement_card"]["safety_override"]
    jp = judge.get(f"{API}/court-dashboard/packets/{cd['statement']['packet_id']}/agreement.pdf")
    assert "Parallel Parenting" in "".join(p.get_text() for p in pymupdf.open(stream=jp.content, filetype="pdf"))
    pp = judge.get(f"{API}/court-dashboard/packets/{cd['statement']['packet_id']}/parallel-plan.pdf")
    plan = pymupdf.open(stream=pp.content, filetype="pdf")
    assert pp.status_code == 200 and len(plan) == 1 and "Parallel Parenting Order Summary" in plan[0].get_text()


def test_parallel_plan_summary_only_with_override() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    complete_both(API, pro, rid, case["invitations"])
    base = {"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready", "dynamic_score": 5}
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=base)
    pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True})
    cd = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert judge.get(f"{API}/court-dashboard/packets/{cd['statement']['packet_id']}/parallel-plan.pdf").status_code == 404


def test_safety_case_auto_start() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    pa, pb = complete_both(API, pro, rid, case["invitations"])
    r = pro.post(f"{API}/joint/reports/{rid}/safety-case")
    assert r.status_code == 200, r.text[:200]
    sc = r.json()
    assert sc["is_safety"] is True and "Safety" in sc["subject_label"]
    assert {i["invitee_email"] for i in sc["invitations"]} == {i["invitee_email"] for i in case["invitations"]}
    det = pro.get(f"{API}/joint/reports/{rid}").json()
    assert det["safety_case_id"] == sc["id"]
    assert pa.post(f"{API}/joint/reports/{rid}/safety-case").status_code == 403
