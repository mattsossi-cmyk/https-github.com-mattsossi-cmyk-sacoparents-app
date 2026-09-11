"""Close/reopen audit trail + closing summary PDF."""
import os
from io import BytesIO

import pytest
from pypdf import PdfReader

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def closed_case() -> dict:
    pro, _pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    pro.get(f"{API}/joint/reports/{rid}/pdf")
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Mediation concluded"}).status_code == 200
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": False}).status_code == 200
    assert pro.patch(f"{API}/joint/reports/{rid}/close", json={"closed": True, "note": "Final"}).status_code == 200
    return {"pro": pro, "rid": rid, "case_code": d["case_code"]}


def test_summary_requires_closed_case() -> None:
    pro, _pa, _pb, d, _detail = completed_case(API)
    assert pro.get(f"{API}/joint/reports/{d['id']}/closing-summary.pdf").status_code == 400


def test_lifecycle_events_recorded(closed_case: dict) -> None:
    act = closed_case["pro"].get(f"{API}/joint/reports/{closed_case['rid']}/activity").json()
    life = act["lifecycle"]
    assert [e["action"] for e in life] == ["Case closed", "Case reopened", "Case closed"]
    assert life[0]["note"] == "Final"
    assert life[0]["by_name"] == closed_case["pro"].name
    assert life[0]["by_role"] == "Assigned professional"
    assert all(e.get("kind") != "lifecycle" for e in act["access_events"])


@pytest.fixture(scope="module")
def summary_text(closed_case: dict) -> str:
    r = closed_case["pro"].get(f"{API}/joint/reports/{closed_case['rid']}/closing-summary.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    reader = PdfReader(BytesIO(r.content))
    assert len(reader.pages) == 1
    return reader.pages[0].extract_text()


@pytest.mark.parametrize("needle", ["Case Closing Summary", "Parent participation", "Final", "Case reopened", "PDF downloads: 1"])
def test_summary_contains(summary_text: str, needle: str) -> None:
    assert needle in summary_text


def test_summary_contains_case_code(summary_text: str, closed_case: dict) -> None:
    assert closed_case["case_code"] in summary_text
