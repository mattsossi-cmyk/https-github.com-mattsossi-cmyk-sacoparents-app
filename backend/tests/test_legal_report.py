"""Professional Legal Report: draft → review → certified finalize; professional-only access; parent-reported labelling."""
import io
import os

import pymupdf
import requests
from casekit import completed_case

def _base() -> str:
    env = os.environ.get("REACT_APP_BACKEND_URL")
    if env:
        return env.rstrip("/")
    with open(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")) as fh:
        return next(line.split("=", 1)[1].strip().strip('"') for line in fh if line.startswith("REACT_APP_BACKEND_URL="))


API = f"{_base()}/api"


def test_legal_report_flow() -> None:
    pro, pa, pb, case, _ = completed_case(API, "education")
    rid = case["id"]
    g = pro.get(f"{API}/cases/{rid}/professional-legal-report").json()
    assert g["status"] == "not_started" and {r["key"]: r["status"] for r in g["availability"]}["joint"] == "Complete"
    assert pa.get(f"{API}/cases/{rid}/professional-legal-report").status_code == 403
    d = pro.post(f"{API}/cases/{rid}/professional-legal-report/generate", json={}).json()
    st = d["report"]
    assert d["status"] == "draft" and st["legal_draft"]["parent_a_summary"]["label"] == "PARENT-REPORTED INFORMATION" and st["legal_draft"]["joint"]["available"]
    assert st["observations"].lower().startswith("ai-assisted draft") and st["ai_generated_content"]["source"] in ("ai", "rule_based")
    assert pro.patch(f"{API}/professional-legal-reports/{rid}", json={"fields": {"professional_comments": "Parent A is alienating the child"}}).status_code == 400
    p = pro.patch(f"{API}/professional-legal-reports/{rid}", json={"fields": {"options_resources": ["BIFF communication principles"], "conflict_resolution_paths": ["Structured Communication", "Child-Focused Mediation"], "professional_comments": "Reviewed."}}).json()
    assert p["status"] == "professional_review" and p["report"]["conflict_resolution_paths"] == ["Structured Communication", "Child-Focused Mediation"]
    draft_pdf = pro.get(f"{API}/professional-legal-reports/{rid}/pdf")
    text = "".join(pg.get_text() for pg in pymupdf.open(stream=io.BytesIO(draft_pdf.content), filetype="pdf"))
    assert "DRAFT - NOT CERT" in text and "NOT YET CERTIFIED" in text and "PARENT-REPORTED INFORMATION" in text
    assert pro.post(f"{API}/professional-legal-reports/{rid}/finalize", json={"certified": True, "certified_name": "", "certified_date": "2026-09-20"}).status_code == 400
    f = pro.post(f"{API}/professional-legal-reports/{rid}/finalize", json={"certified": True, "certified_name": "Test Pro, J.D.", "certified_date": "2026-09-20", "bar_number": "123"}).json()
    assert f["status"] == "finalized" and f["report"]["legal_version"] == 1 and len(f["versions"]) == 1 and f["report"]["status"] == "ready"
    text = "".join(pg.get_text() for pg in pymupdf.open(stream=io.BytesIO(pro.get(f"{API}/professional-legal-reports/{rid}/pdf").content), filetype="pdf"))
    assert "DRAFT - NOT CERT" not in text and "Test Pro, J.D." in text and "12. PROFESSIONAL STATEMENT" in text
    # edits after finalization never overwrite silently: a new version is created on the next finalize
    assert pro.patch(f"{API}/professional-legal-reports/{rid}", json={"fields": {"professional_comments": "Updated."}}).json()["status"] == "professional_review"
    f2 = pro.post(f"{API}/professional-legal-reports/{rid}/finalize", json={"certified": True, "certified_name": "Test Pro, J.D.", "certified_date": "2026-09-21"}).json()
    assert f2["report"]["legal_version"] == 2 and [v["version"] for v in f2["versions"]] == [1, 2] and "report" not in f2["versions"][0]
    diff = pro.get(f"{API}/professional-legal-reports/{rid}/diff", params={"from_version": 1, "to_version": 2}).json()
    pc = next(c for c in diff["changes"] if c["key"] == "professional_comments")
    assert pc["kind"] == "text" and any(s["op"] == "insert" and "Updated." in s["text"] for s in pc["segments"]) and any(s["op"] == "delete" for s in pc["segments"])
    assert pro.get(f"{API}/professional-legal-reports/{rid}/diff", params={"from_version": 2, "to_version": 0}).json()["changes"] == []
    assert pro.get(f"{API}/professional-legal-reports/{rid}/diff", params={"from_version": 9}).status_code == 404
    for c in (pa, pb):
        assert c.get(f"{API}/professional-legal-reports/{rid}/pdf").status_code == 403
    events = pro.get(f"{API}/joint/reports/{rid}/activity").json()["lifecycle"]
    acts = {e["action"] for e in events}
    assert {"LEGAL_REPORT_CREATED", "LEGAL_REPORT_EDITED", "LEGAL_REPORT_FINALIZED", "LEGAL_REPORT_EXPORTED", "LEGAL_REPORT_VIEWED"} <= acts


def test_legal_report_attached_to_court_submission() -> None:
    import pymongo
    from casekit import complete_both
    from test_judicial_portal import _flow
    judge, pro, ref, case = _flow()
    rid = case["id"]
    complete_both(API, pro, rid, case["invitations"])
    base = {"role": "Mediator", "role_basis": "Court referral", "process_summary": "x", "observations": "y", "next_steps": "z", "status": "ready", "dynamic_score": 5}
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=base)
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "include_legal_report": True})
    assert r.status_code == 400 and "Finalize the Professional Evaluation Report" in r.json()["detail"]
    pro.get(f"{API}/cases/{rid}/professional-report")
    growth = "Focus on calm messages.\nFocus on timely handoffs."
    fields = {"signature_name": "Court Pro, J.D.", "professional_summary": "sum", "joint_rating": 6, "parent_a_growth": growth, "parent_b_growth": growth,
              "growth_status": {"a": {"Focus on calm messages.": True}, "b": {}}, "risk_screening": {"hostility": {"level": "Moderate Risk", "note": "n"}}}
    assert pro.put(f"{API}/cases/{rid}/professional-report", json={"fields": fields, "status": "final"}).json()["report"]["status"] == "final"
    assert pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()["legal_lens"]["status"] == "final"
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True, "include_legal_report": True}).json()["submission"]
    assert sub["legal_report_included"] and len(sub["legal_sha256"]) == 64
    assert pro.get(f"{API}/cases/{rid}/professional-report").json()["report"]["status"] == "submitted_to_court"
    view = judge.get(f"{API}/court-dashboard/cases/{ref['id']}").json()
    assert view["statement"]["legal_report_included"]
    ls = view["statement"]["legal_summary"]
    assert ls["ratings"]["joint"]["score"] == 6 and ls["pathway"] == "Traditional Mediation"
    assert [g["met"] for g in ls["growth"]["a"]] == [True, False] and ls["risk_screening"][2]["level"] == "Moderate Risk"
    assert "parent_a_notes" not in ls and view["level_history"][-1]["growth"]["a"] == {"met": 1, "total": 2, "items": ls["growth"]["a"]}
    lp = judge.get(f"{API}/court-dashboard/packets/{sub['packet_id']}/legal-report.pdf")
    assert lp.status_code == 200 and lp.headers["content-type"].startswith("application/pdf")
    text = "".join(pg.get_text() for pg in pymupdf.open(stream=io.BytesIO(lp.content), filetype="pdf"))
    assert "Professional Alignment Report" in text and "Court Pro, J.D." in text and "MET at reassessment" in text and "Starting With Alignment" in text and "DRAFT" not in text
    secs = judge.get(f"{API}/court-dashboard/packets/{sub['packet_id']}/legal-report-sections")
    assert secs.status_code == 200, secs.text
    pages = secs.json()["pages"]
    assert pages.get("1") and pages.get("11") and pages["1"] <= pages["3"] <= pages["11"] <= secs.json()["total_pages"], pages
    inline = judge.get(f"{API}/court-dashboard/packets/{sub['packet_id']}/legal-report.pdf", params={"inline": 1})
    assert inline.status_code == 200 and inline.headers["content-disposition"].startswith("inline")
    assert pro.get(f"{API}/court-dashboard/packets/{sub['packet_id']}/legal-report-sections").status_code in (403, 404)
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    assert db.access_events.count_documents({"report_id": rid, "action": "LEGAL_REPORT_SHARED"}) == 1
    sub2 = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True}).json()["submission"]
    assert not sub2["legal_report_included"] and judge.get(f"{API}/court-dashboard/packets/{sub2['packet_id']}/legal-report.pdf").status_code == 404


def test_legal_report_sample_public() -> None:
    s = requests.get(f"{API}/professional-legal-report/sample").json()
    assert s["is_sample"] and s["case"]["case_code"] == "SAMPLE-2026-001" and s["professional"]["name"] == "Jordan Taylor, J.D."
    r = requests.get(f"{API}/professional-legal-report/sample/pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
