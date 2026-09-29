"""Both-complete notification + Joint/Professional report ZIP bundle."""
import io
import os
import zipfile

import pymupdf
import pytest
from casekit import completed_case, new_case

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def flow():
    pro, pa, pb, d, detail = completed_case(API, subject="education")
    return {"pro": pro, "rid": d["id"], "case_code": d["case_code"]}


def test_bundle_zip_contains_both_pdfs(flow):
    r = flow["pro"].get(f"{API}/cases/{flow['rid']}/professional-report/bundle.zip")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/zip"), r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = sorted(z.namelist())
    assert names == sorted([f"{flow['case_code']}-joint-report.pdf", f"{flow['case_code']}-professional-report.pdf"])
    for n in names:
        doc = pymupdf.open(stream=z.read(n), filetype="pdf")
        assert len(doc) >= 1
    assert "Professional Alignment Report" in pymupdf.open(stream=z.read(names[1]), filetype="pdf")[0].get_text()


def test_both_complete_flag_set(flow):
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    d = db.joint_reports.find_one({"id": flow["rid"]}, {"both_complete_notified_at": 1, "status": 1})
    assert d["status"] == "ready" and d.get("both_complete_notified_at")


def test_bundle_400_before_completion():
    pro, pa, pb, d = new_case(API, subject="education")
    r = pro.get(f"{API}/cases/{d['id']}/professional-report/bundle.zip")
    assert r.status_code == 400 and "both parents" in r.json()["detail"]
