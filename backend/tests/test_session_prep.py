"""Session Prep Sheet: one-page facilitator agenda PDF from a ready joint report."""
import os

import pytest

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def ready():
    pro, pa, _pb, d, _detail = completed_case(API)
    return pro, pa, d["id"]


def test_pro_downloads_one_page_prep_sheet(ready) -> None:
    pro, _pa, rid = ready
    r = pro.get(f"{API}/joint/reports/{rid}/session-prep.pdf")
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"
    assert r.content.count(b"/Type /Page\n") <= 1 or r.content.count(b"/Type /Page") - r.content.count(b"/Type /Pages") == 1
    assert "session-prep-" in r.headers["Content-Disposition"]


def test_parent_cannot_download_prep_sheet(ready) -> None:
    _pro, pa, rid = ready
    assert pa.get(f"{API}/joint/reports/{rid}/session-prep.pdf").status_code == 403


def test_prep_sheet_logged_in_activity(ready) -> None:
    pro, _pa, rid = ready
    events = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    items = events.get("access_log", []) if isinstance(events, dict) else events
    assert any("Session Prep" in (e.get("action") or "") for e in items)
