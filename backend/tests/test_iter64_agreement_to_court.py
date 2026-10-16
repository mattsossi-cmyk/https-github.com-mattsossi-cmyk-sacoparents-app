"""Iter 64: Co-Parenting Agreement explicitly attached to a court submission; judge sees card + PDF."""
import pymupdf
import requests
from casekit import complete_both, new_user
from test_judicial_portal import _flow
from test_legal_report import API

AGR_FIELDS = {"child_name": "Emma", "shared_purpose": "Calm.", "vision": "Safe.", "priorities": ["Protect Emma"], "strengths": "Curious and kind.", "needs": ["Calm transitions"],
              "commitments": ["Stay calm"], "goals": ["Fewer disputes"], "parent_commitment": "Emma first."}


def _agreement_answers() -> dict:
    secs = requests.get(f"{API}/joint/config").json().get("agreement_sections") or []
    out = {}
    for s in secs:
        out[s["key"]] = f"Clear child-focused plan for {s['label'].lower()} using the app with 24-hour notice."
        for fu in s.get("follow_ups") or []:
            out[fu["key"]] = "Use the SA CoParents app with 24-hour notice; exchanges at school."
    return out


def test_agreement_attached_to_court_submission() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    pa, pb = complete_both(API, pro, rid, case["invitations"])
    emails = {i["role"]: i["invitee_email"] for i in case["invitations"]}
    # professional creates an agreement case for the same parents; both parents complete it
    ag = pro.post(f"{API}/joint/agreements", json={"child_name": case.get("child_name") or "Emma", "parent_a_name": "Parent A", "parent_a_email": emails["a"], "parent_b_name": "Parent B", "parent_b_email": emails["b"]}).json()
    assert ag.get("id"), ag
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in ag["invitations"]}
    answers = _agreement_answers()
    for s, role in ((pa, "a"), (pb, "b")):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]}).json().get("ok")
        s.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS, "safety": {"fear": False, "threats": False, "control": False}})
        s.post(f"{API}/joint/reports/{ag['id']}/foundation/share")
        s.post(f"{API}/joint/reports/{ag['id']}/safety-screening/decline")  # required Start with Safety step (iter108)
        r = s.put(f"{API}/joint/reports/{ag['id']}/responses", json={"answers": answers})
        assert r.status_code == 200, r.text[:200]
    assert pro.get(f"{API}/joint/reports/{ag['id']}").json()["status"] == "ready"
    # picker shows it
    ps = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()
    assert any(o["id"] == ag["id"] for o in ps["agreement_options"]), ps.get("agreement_options")
    base = {"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready", "dynamic_score": 5}
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=base)
    # wrong id rejected
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "agreement_report_id": "nope"})
    assert r.status_code == 400
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "agreement_report_id": ag["id"]})
    assert sub.status_code == 200, sub.text[:300]
    s = sub.json()["submission"]
    assert s["agreement_included"] and s["agreement_sha256"] and s["agreement_card"]["counts"]["specific"] >= 1
    # judge view
    cd = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    st = cd["statement"]
    assert st["agreement_included"] and st["agreement_card"]["case_code"] == ag.get("case_code")
    pdf = judge.get(f"{API}/court-dashboard/packets/{st['packet_id']}/agreement.pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf")
    text = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    for h in ("Child-Focused Co-Parenting Agreement", "Our Child's Strengths", "Conflict Resolution Plan", "Our Parenting Commitments", "Alignment Before Agreement"):
        assert h in text, h
    assert "Curious and kind" in text and "Stay calm" in text
    # submission without agreement has no card
    sub2 = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True}).json()["submission"]
    assert not sub2["agreement_included"]
    other = new_user(API, "professional", "Other Pro")
    assert other.get(f"{API}/court-dashboard/packets/{st['packet_id']}/agreement.pdf").status_code in (403, 404)
