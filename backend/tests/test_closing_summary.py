"""Close/reopen audit trail + closing summary PDF."""
import os
from io import BytesIO

from pypdf import PdfReader

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_lifecycle_events_and_closing_summary() -> None:
    pro, _pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    assert pro.get(f"{API}/joint/reports/{rid}/closing-summary.pdf").status_code == 400
    assert pro.post(f"{API}/joint/reports/{rid}/pdf").status_code in (200, 405)
    pro.get(f"{API}/joint/reports/{rid}/pdf")
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Mediation concluded"}).status_code == 200
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": False}).status_code == 200
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Final"}).status_code == 200

    act = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    life = act["lifecycle"]
    assert [e["action"] for e in life] == ["Case closed", "Case reopened", "Case closed"]
    assert life[0]["note"] == "Final" and life[0]["by_name"] == pro.name and life[0]["by_role"] == "Assigned professional"
    assert all(e.get("kind") != "lifecycle" for e in act["access_events"])

    r = pro.get(f"{API}/joint/reports/{rid}/closing-summary.pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    reader = PdfReader(BytesIO(r.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for needle in ("Case Closing Summary", d["case_code"], "Parent participation", "Final", "Case reopened", "PDF downloads: 1"):
        assert needle in text, needle
