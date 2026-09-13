"""Demo sample case: approved pro loads a fictional two-parent case that is immediately report-ready."""
import os

import pytest

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def loaded() -> tuple:
    pro = new_user(API, "professional", "Sample Pro")
    r = pro.post(f"{API}/joint/reports/professional/sample")
    assert r.status_code == 200, r.text
    return pro, r.json()


def test_sample_case_is_ready_and_flagged(loaded) -> None:
    _pro, d = loaded
    assert d["is_demo"]
    assert not d["already_existed"]
    assert d["case_status"] == "READY_FOR_ALIGNMENT"
    assert d["participants"]["a"]["completed"] and d["participants"]["b"]["completed"]
    assert d["case_code"].startswith("SA-")


def test_sample_case_report_renders(loaded) -> None:
    pro, d = loaded
    r = pro.get(f"{API}/joint/reports/{d['id']}/report")
    assert r.status_code == 200, r.text
    assert r.json()["subject_label"] == d["subject_label"]
    pdf = pro.get(f"{API}/joint/reports/{d['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_sample_case_is_idempotent(loaded) -> None:
    pro, d = loaded
    r = pro.post(f"{API}/joint/reports/professional/sample")
    assert r.status_code == 200
    assert r.json()["already_existed"] and r.json()["id"] == d["id"]
    mine = pro.get(f"{API}/joint/reports").json()
    assert sum(1 for j in mine if j.get("is_demo")) == 1


def test_unapproved_pro_cannot_load_sample() -> None:
    import requests, uuid
    s = requests.Session()
    s.post(f"{API}/auth/register", json={"name": "P", "email": f"t_{uuid.uuid4().hex[:8]}@example.com", "password": "testpass123", "role": "professional", "agreements_accepted": True})
    assert s.post(f"{API}/joint/reports/professional/sample").status_code == 403
