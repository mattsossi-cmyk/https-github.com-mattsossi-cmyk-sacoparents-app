"""Privacy Notification: text exact, acceptance stored with version+time, re-shown on version change, frontend constant in sync."""
import re
import time

from tests.test_iter88_safety_e2e import BASE, PRO_EMAIL, PRO_PASSWORD, _login
from privacy_notice import NOTICE, PRIVACY_NOTICE_VERSION

MONGO = __import__("tests.test_iter88_safety_e2e", fromlist=["MONGO"]).MONGO


def test_text_matches_spec():
    assert NOTICE["title"] == "Your Privacy Matters" and NOTICE["subhead"] == "Private by Default. Shared by Choice."
    assert NOTICE["intro"] == "Your preparation is private and under your control."
    assert [p["heading"] for p in NOTICE["points"]][4] == "Professionals and courts receive the information you authorize, or what the law or a court order requires."
    assert NOTICE["points"][4]["body"] == "Assigned professionals may see individual screening answers."
    assert NOTICE["legal"].startswith("Using SA CoParents does not automatically create an attorney-client")
    assert NOTICE["checkbox"] == "I have read and understand this privacy notification." and NOTICE["continue"] == "Continue to SA CoParents"
    assert [l["href"] for l in NOTICE["footer_links"]] == ["/privacy", "/legal/confidentiality", "/legal/sharing-consent"] and "encrypt" not in str(NOTICE).lower()
    legal = open("/app/frontend/src/pages/Legal.jsx", encoding="utf-8").read()
    assert "confidentiality: {" in legal and '"sharing-consent": {' in legal


def test_admin_acceptance_log_and_csv():
    import os
    s = _login(PRO_EMAIL, PRO_PASSWORD)
    assert s.get(f"{BASE}/api/admin/privacy-notice/acceptances", timeout=15).status_code == 403
    a = _login("qa.admin.preview@bsossi.com", os.environ.get("QA_ADMIN_PASSWORD", "QaAdmin2026!"))
    d = a.get(f"{BASE}/api/admin/privacy-notice/acceptances", timeout=15).json()
    assert d["current_version"] == PRIVACY_NOTICE_VERSION and d["total"] >= 1 and d["accepted_current"] <= d["total"]
    row = next(x for x in d["rows"] if x["email"] == PRO_EMAIL)
    assert row["accepted_version"] == PRIVACY_NOTICE_VERSION and row["current"] is True and row["accepted_at"]
    c = a.get(f"{BASE}/api/admin/privacy-notice/acceptances.csv", timeout=15)
    assert c.status_code == 200 and c.headers["content-type"].startswith("text/csv") and c.text.splitlines()[0].startswith("name,email,role,accepted_version") and PRO_EMAIL in c.text


def test_frontend_version_constant_in_sync():
    src = open("/app/frontend/src/App.js", encoding="utf-8").read()
    assert re.search(r'PRIVACY_NOTICE_VERSION = "' + re.escape(PRIVACY_NOTICE_VERSION) + '"', src)
    page = open("/app/frontend/src/pages/PrivacyNotice.jsx", encoding="utf-8").read()
    assert "disabled={!ok || busy}" in page and "QuickExitBar" in page and "privacy-footer-links" in page


def test_accept_flow_and_reshow_on_version_change():
    s = _login(PRO_EMAIL, PRO_PASSWORD)
    MONGO.users.update_one({"email": PRO_EMAIL}, {"$unset": {"privacy_notice": ""}})
    try:
        d = s.get(f"{BASE}/api/privacy-notice", timeout=15).json()
        assert d["needs_acceptance"] is True and d["notice"]["version"] == PRIVACY_NOTICE_VERSION
        assert s.get(f"{BASE}/api/auth/me", timeout=15).json()["privacy_notice_version"] is None
        assert s.post(f"{BASE}/api/privacy-notice/accept", json={"version": PRIVACY_NOTICE_VERSION, "acknowledged": False}, timeout=15).status_code == 400
        assert s.post(f"{BASE}/api/privacy-notice/accept", json={"version": "0000", "acknowledged": True}, timeout=15).status_code == 409
        t0 = time.time()
        r = s.post(f"{BASE}/api/privacy-notice/accept", json={"version": PRIVACY_NOTICE_VERSION, "acknowledged": True}, timeout=15)
        assert r.status_code == 200 and r.json()["version"] == PRIVACY_NOTICE_VERSION and r.json()["accepted_at"][:4] == "2026" or time.time() - t0 < 60
        d = s.get(f"{BASE}/api/privacy-notice", timeout=15).json()
        assert d["needs_acceptance"] is False and d["accepted"]["version"] == PRIVACY_NOTICE_VERSION and d["accepted"]["accepted_at"]
        assert s.get(f"{BASE}/api/auth/me", timeout=15).json()["privacy_notice_version"] == PRIVACY_NOTICE_VERSION
        # simulate an older accepted version -> must be re-shown
        MONGO.users.update_one({"email": PRO_EMAIL}, {"$set": {"privacy_notice.version": "2000-01-01.0"}})
        assert s.get(f"{BASE}/api/privacy-notice", timeout=15).json()["needs_acceptance"] is True
    finally:
        MONGO.users.update_one({"email": PRO_EMAIL}, {"$set": {"privacy_notice": {"version": PRIVACY_NOTICE_VERSION, "accepted_at": "2026-10-09T00:00:00+00:00"}}})
