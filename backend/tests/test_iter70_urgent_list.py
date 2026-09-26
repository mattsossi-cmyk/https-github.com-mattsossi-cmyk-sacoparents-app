"""Iteration 70: judge urgent-messages list (clears when the Court replies)."""
from casekit import complete_both
from test_judicial_portal import _flow
from test_legal_report import API


def test_urgent_list_shows_unanswered_urgent_then_clears() -> None:
    judge, pro, ref, case = _flow()
    complete_both(API, pro, case["id"], case["invitations"])
    r = pro.post(f"{API}/professional/court-referrals/{ref['id']}/messages", json={"text": "URGENT: the child disclosed a credible threat of physical harm at today's exchange; a protective order is being requested immediately."})
    assert r.status_code == 200, r.text
    assert (r.json()["message"].get("triage") or {}).get("category") == "urgent_safety"
    items = judge.get(f"{API}/court-dashboard/urgent-messages").json()["items"]
    assert any(i["referral_id"] == ref["id"] for i in items)
    assert judge.post(f"{API}/court-dashboard/cases/{ref['id']}/messages", json={"text": "Received. Set for emergency hearing tomorrow 9am."}).status_code == 200
    items = judge.get(f"{API}/court-dashboard/urgent-messages").json()["items"]
    assert not any(i["referral_id"] == ref["id"] for i in items)
    assert pro.get(f"{API}/court-dashboard/urgent-messages").status_code == 403
