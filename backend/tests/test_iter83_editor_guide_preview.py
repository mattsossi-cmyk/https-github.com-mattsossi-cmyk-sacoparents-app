"""Iteration 83: 1–11 editor sections, judge reader guide, court packet preview."""
import pymupdf

from casekit import complete_both
from test_judicial_portal import API, _flow


def test_judge_report_guide_and_packet_preview() -> None:
    judge, pro, ref, case = _flow()
    rid = case["id"]
    g = judge.get(f"{API}/court-dashboard/report-guide")
    assert g.status_code == 200 and len(g.json()["sections"]) == 11 and "custody recommendation" in g.json()["intro"]
    assert pro.get(f"{API}/court-dashboard/report-guide").status_code in (403, 404)

    # section-9 fields persist through the whitelist
    r = pro.put(f"{API}/cases/{rid}/professional-report", json={"fields": {"agreement_building_opportunities": "Exchange times\nSchool communication", "procedural_considerations": "Temporary orders in place"}})
    assert r.status_code == 200 and r.json()["report"]["agreement_building_opportunities"].startswith("Exchange times")

    complete_both(API, pro, rid, case["invitations"])
    assert pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready"}).status_code == 200
    before = len(pro.get(f"{API}/joint/reports/{rid}/professional-statement").json().get("submissions") or [])
    pv = pro.post(f"{API}/joint/reports/{rid}/court-packet-preview", json={"include_legal_report": False})
    assert pv.status_code == 200, pv.text
    assert pv.headers["content-type"] == "application/pdf" and pv.headers.get("x-packet-preview") == "1" and "PREVIEW" in pv.headers["content-disposition"]
    text = "".join(p.get_text() for p in pymupdf.open(stream=pv.content, filetype="pdf"))
    assert "Professional Assessment Statement" in text or "Professional Report" in text
    after = len(pro.get(f"{API}/joint/reports/{rid}/professional-statement").json().get("submissions") or [])
    assert after == before, "preview must not create a submission"
    assert judge.post(f"{API}/joint/reports/{rid}/court-packet-preview", json={}).status_code in (403, 404)
