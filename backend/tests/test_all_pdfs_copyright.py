"""Every PDF download: must return a real PDF, and every page must carry the copyright line.

Runs against REACT_APP_BACKEND_URL. Endpoints that legitimately have nothing to print for an account
(404/409/400 with a JSON detail) are reported as "empty" and not failures.
Run: python -m pytest -q -s tests/test_all_pdfs_copyright.py
"""
import io
import os
import subprocess
import tempfile
import zipfile

import pytest
import requests

API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
LINE = "SA CoParents \u00b7 sacoparentsapp.online \u00b7 All rights reserved."
ACCOUNTS = {
    "parent1": ("parent1@test.com", "TestPass123!"),
    "parent2": ("parent2@test.com", "TestPass123!"),
    "journey6": ("journey6@test.com", "TestPass123!"),
    "admin": ("mattsossi@bsossi.com", "AdminPass123!"),
}
_tokens = {}


def _hdr(who):
    if who is None:
        return {}
    if who not in _tokens:
        r = requests.post(f"{API}/auth/login", json=dict(zip(("email", "password"), ACCOUNTS[who])), timeout=30)
        assert r.status_code == 200, f"login {who}: {r.status_code}"
        _tokens[who] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens[who]}"}


def _pages_missing_line(pdf_bytes):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
        fh.write(pdf_bytes)
        fh.flush()
        info = subprocess.run(["pdfinfo", fh.name], capture_output=True, text=True).stdout
        pages = int(next(l.split()[-1] for l in info.splitlines() if l.startswith("Pages:")))
        missing = []
        for i in range(1, pages + 1):
            txt = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), fh.name, "-"], capture_output=True, text=True).stdout
            if LINE not in " ".join(txt.split()):
                missing.append(i)
        return pages, missing


SA_ITEM = {"id": "t1", "completed_at": "2026-10-01T00:00:00Z", "parent_name": "Test", "answers": {"q1": 3},
           "scores": {"overall": 3}}
CASES = [
    # (who, method, path, json)
    (None, "POST", "/portal/guided-snapshot-pdf", {"topic": "coparenting", "answers": [{"q": "How?", "a": "Calm"}], "parent_name": "Test"}),
    (None, "POST", "/portal/guided-snapshot-pdf", {"topic": "coparenting", "answers": [{"q": "How?", "a": "Calm"}], "variant": "fridge"}),
    (None, "POST", "/portal/guided-snapshot-pdf", {"topic": "coparenting", "answers": [{"q": "How?", "a": "Calm"}], "variant": "fridge_pair"}),
    (None, "POST", "/portal/foundation-pdf", {"foundation_text": "We agree to put our child first.", "author_name": "Test"}),
    (None, "POST", "/portal/legal-report-pdf", {"health_index": {"communication": 3}, "foundation_text": "We agree."}),
    (None, "POST", "/portal/weekly-progress-pdf", {"health_index": {"communication": 3}, "author_name": "Test"}),
    (None, "POST", "/portal/complete-report-pdf", {"foundation_text": "We agree.", "author_name": "Test"}),
    (None, "POST", "/coparenting/preview-profile/pdf", {"parent_name": "Test", "scores": [{"domain": "Communication", "score": 3}]}),
    (None, "POST", "/child-needs/pdf", {"parent_name": "Test", "answers": {"medical": {"med_provider": "Dr. Lee", "med_conditions": "Asthma inhaler"}}}),
    (None, "POST", "/foundation-builder/pdf", {"fields": {"parent_names": "Test"}, "esign_name": "Test"}),
    (None, "POST", "/self-assessment/pdf", {"entry": SA_ITEM, "history": []}),
    (None, "GET", "/insights/brochure/mediator.pdf", None),
    (None, "GET", "/insights/flyer/access.pdf", None),
    (None, "GET", "/insights/foundation-statement.pdf", None),
    (None, "GET", "/insights/family-violence-report.pdf", None),
    (None, "GET", "/insights/coparenting-report.pdf", None),
    (None, "GET", "/insights/coparenting-options.pdf", None),
    (None, "GET", "/insights/coparenting-dynamic-sample.pdf", None),
    (None, "GET", "/insights/samples/co-parenting-alignment-report.pdf", None),
    (None, "GET", "/insights/samples/coparenting-self-assessment.pdf", None),
    (None, "GET", "/insights/samples/joint-alignment-preview.pdf", None),
    (None, "GET", "/insights/samples/deep-dive-educational.pdf", None),
    (None, "GET", "/insights/samples/deep-dive-medical.pdf", None),
    (None, "GET", "/insights/samples/deep-dive-psychological.pdf", None),
    ("admin", "GET", "/insights/admin/brochure/mediator.pdf", None),
    ("parent1", "POST", "/parallel-parenting/pdf", {}),
    ("parent1", "POST", "/parallel-parenting/court-notes/pdf", {}),
    ("parent1", "POST", "/court-path/checklist/pdf", {}),
    ("parent1", "GET", "/court-path/compare/pdf", None),
    ("parent1", "GET", "/court-path/completion-summary.pdf", None),
    ("journey6", "GET", "/self-journey/pdf", None),
    ("journey6", "GET", "/self-journey/certificate", None),
    ("journey6", "GET", "/journey-summary/pdf", None),
    ("journey6", "POST", "/journey-summary/certificate", {"name": "Test Parent"}),
    ("parent1", "POST", "/mediation/certificate/download", {"name": "Test Parent"}),
    ("parent1", "GET", "/complete-report/mine.pdf", None),
    ("parent1", "GET", "/complete-report/joint/SA-DEMO01.pdf", None),
    ("parent1", "GET", "/coparenting/report/progress/pdf", None),
    ("parent1", "GET", "/coparenting/report/pdf", None),
    ("parent1", "GET", "/edu-deep/report/pdf", None),
    ("parent1", "GET", "/med-deep/report/pdf", None),
    ("parent2", "GET", "/med-deep/report/pdf", None),
    ("parent2", "GET", "/edu-deep/report/pdf", None),
    ("parent2", "GET", "/coparenting/report/pdf", None),
    ("parent1", "GET", "/psych-deep/report/pdf", None),
    ("parent1", "GET", "/snc2/report/pdf", None),
    ("parent1", "GET", "/activities-costs/compare.pdf", None),
    ("parent1", "GET", "/dimension-companion/four-dimension-briefing/pdf", None),
    ("parent1", "GET", "/mediation/foundation-statement.pdf", None),
    ("parent1", "GET", "/pathway-report/preview/pdf", None),
    ("parent1", "GET", "/pathway-report/dual/seed_edu_deep_share/pdf", None),
    ("parent1", "GET", "/joint-agreement/seed_edu_deep_share/pdf", None),
    ("parent1", "GET", "/joint-professional-report/seed_edu_deep_share/pdf", None),
    ("parent1", "GET", "/joint-professional-report/professional-intro.pdf", None),
    ("parent1", "GET", "/edu-deep/compare/seed_edu_deep_share/pdf", None),
    ("parent1", "GET", "/med-deep/compare/seed_med_deep_share/pdf", None),
    ("parent1", "GET", "/psych-deep/compare/seed_psych_deep_share/pdf", None),
    ("parent1", "GET", "/professional/joint-alignment/cases/SA-DEMO01/status-report.pdf", None),
    ("parent1", "GET", "/professional/joint-alignment/cases/SA-DEMO01/progress.pdf", None),
    ("parent1", "GET", "/reviewer-panel/packet", None),
    ("admin", "GET", "/reviewer-panel/packet", None),
]


def _check(r):
    if r.status_code != 200:
        try:
            detail = r.json()
        except ValueError:
            detail = None
        if r.status_code in (400, 404, 409, 410, 422) and isinstance(detail, dict):
            return "empty", f"{r.status_code} {str(detail)[:100]}"
        return "bug", f"{r.status_code} {r.text[:160]}"
    body = r.content
    if body[:4] != b"%PDF":
        return "bug", f"200 but not a PDF: {body[:16]!r}"
    pages, missing = _pages_missing_line(body)
    return ("ok", f"{pages}p") if not missing else ("bug", f"{pages}p, copyright missing on pages {missing}")


@pytest.mark.parametrize("who,method,path,body", CASES, ids=[f"{c[1]} {c[2]}" for c in CASES])
def test_pdf_download_has_copyright(who, method, path, body):
    r = requests.request(method, f"{API}{path}", headers=_hdr(who), json=body, timeout=120)
    verdict, note = _check(r)
    print(f"\n  {verdict:6} {method} {path} [{who}] {note}")
    assert verdict != "bug", note


def test_bundle_pdfs_have_copyright():
    r = requests.get(f"{API}/bundle/my-completed.zip", headers=_hdr("parent1"), timeout=180)
    if r.status_code in (404, 409):
        pytest.skip(f"empty bundle {r.status_code}")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    bad = {}
    for name in [n for n in z.namelist() if n.lower().endswith(".pdf")]:
        pages, missing = _pages_missing_line(z.read(name))
        if missing:
            bad[name] = missing
    assert not bad, bad
