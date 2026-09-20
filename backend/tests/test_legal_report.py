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


def test_legal_report_sample_public() -> None:
    s = requests.get(f"{API}/professional-legal-report/sample").json()
    assert s["is_sample"] and s["case"]["case_code"] == "SAMPLE-2026-001" and s["professional"]["name"] == "Jordan Taylor, J.D."
    r = requests.get(f"{API}/professional-legal-report/sample/pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
