"""Iteration 69: sample Research Base footer, court packet research sources (explicit opt-in), provider freshness check."""
import os

import pymupdf
import pytest
import requests

from test_legal_report import API


def test_sample_report_has_research_base_json_and_pdf() -> None:
    r = requests.get(f"{API}/joint/sample-legal-lens", timeout=30)
    assert r.status_code == 200
    rb = r.json()["report"]["research_base"]
    assert rb["citations"] and "example.org" in rb["citations"][0]["url"]
    pdf = requests.get(f"{API}/joint/sample-legal-lens/pdf", timeout=60)
    text = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "RESEARCH BASE" in text and "example.org" in text


def test_court_sources_only_when_ticked() -> None:
    from casekit import complete_both
    from test_judicial_portal import _flow as flow
    judge, pro, ref, case = flow()
    rid = case["id"]
    complete_both(API, pro, rid, case["invitations"])
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready", "dynamic_score": 5})
    assert pro.put(f"{API}/cases/{rid}/professional-report", json={"fields": {"signature_name": "Portal Pro", "joint_rating": 5}, "status": "final"}).status_code == 200
    rb = {"text": "Sample research.", "citations": [{"index": 1, "url": "https://example.org/src"}], "model": "perplexity-agent", "fetched_at": "2026-09-26T00:00:00"}
    import pymongo
    c = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    c.professional_reports.update_one({"case_id": rid}, {"$set": {"research_base": rb}})
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "include_legal_report": True, "include_research_sources": False})
    assert r.status_code == 200, r.text
    d1 = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert not (d1["statement"]["legal_summary"] or {}).get("research_sources")
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "include_legal_report": True, "include_research_sources": True})
    assert r.status_code == 200, r.text
    d2 = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert d2["statement"]["legal_summary"]["research_sources"]["citations"][0]["url"] == "https://example.org/src"


@pytest.mark.skipif(not os.environ.get("PERPLEXITY_API_KEY"), reason="live Perplexity required")
def test_provider_freshness_check_live() -> None:
    s = requests.Session()
    if s.post(f"{API}/auth/login", json={"email": os.environ.get("ADMIN_EMAIL", "mattsossi@bsossi.com"), "password": os.environ.get("ADMIN_PASSWORD", "CoParents2026!")}).status_code != 200:
        pytest.skip("admin login unavailable")
    provs = s.get(f"{API}/admin/providers").json()
    p = next((x for x in provs if "KidShare" in x["name"]), provs[0])
    r = s.post(f"{API}/research/providers/{p['id']}/verify", timeout=120)
    assert r.status_code == 200, r.text
    v = r.json()["verification"]
    assert set(v["checks"]) == {"phone", "website"} and v["citations"]
    assert s.post(f"{API}/research/providers/{p['id']}/apply-verification").status_code == 200
    pro = requests.Session(); pro.post(f"{API}/auth/login", json={"email": "approval.test.pro1@gmail.com", "password": "TestPass2026!"})
    assert pro.post(f"{API}/research/providers/{p['id']}/verify").status_code == 403
