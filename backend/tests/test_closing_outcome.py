"""Closing Summary PDF includes the recorded session outcome."""
import os

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_closing_summary_contains_session_outcome() -> None:
    pro, _pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    r = pro.put(f"{API}/joint/reports/{rid}/session-outcome", json={"chosen_steps": ["Continue Parent Discussion"], "summary": "Try the shared log."})
    assert r.status_code == 200, r.text
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Done"}).status_code == 200
    pdf = pro.get(f"{API}/joint/reports/{rid}/closing-summary.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    import pymupdf
    text = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "Session outcome" in text and "Continue Parent Discussion" in text and "Try the shared log." in text
