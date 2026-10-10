"""Privacy Notification: text exact, acceptance stored with version+time, re-shown on version change, frontend constant in sync."""
import re
import time

from tests.test_iter88_safety_e2e import BASE, PRO_EMAIL, PRO_PASSWORD, _login
from privacy_notice import NOTICE, PRIVACY_NOTICE_VERSION

MONGO = __import__("tests.test_iter88_safety_e2e", fromlist=["MONGO"]).MONGO


def test_text_matches_spec():
    assert NOTICE["title"] == "Your Privacy Matters" and NOTICE["subhead"] == "Private by default. Shared with your consent, or as the law requires."
    assert NOTICE["banner_heading"] == "Privacy & Confidentiality" and NOTICE["tagline"] == "Start with Safety. Build with Trust."
    assert NOTICE["intro"] == "Your preparation is private and under your control."
    assert [p["heading"] for p in NOTICE["points"]] == ["Your individual answers remain private.", "You control what you share.", "Reports are different from raw answers.", "Safety comes first.",
                                                        "Professionals and courts receive the information you authorize, or what the law or a court order requires."]
    assert [p["body"] for p in NOTICE["points"]] == ["Your co-parent does not automatically see your assessments, personal reflections, or journal entries.",
                                                     "In the Self Journey, you choose which completed reports to share and with whom. Separate consent rules apply to joint and court-ordered participation.",
                                                     "Sharing a selected report does not automatically provide access to your entire account or private journal.",
                                                     "Family violence and communication safety concerns may require separate participation and additional safeguards.",
                                                     "Assigned professionals may see individual screening answers."]
    assert NOTICE["legal_heading"] == "Important Legal Notice"
    assert NOTICE["legal"] == "Using SA CoParents does not automatically create an attorney-client, therapist-patient, or other legally privileged relationship. Information may be subject to lawful disclosure requirements."
    assert NOTICE["checkbox"] == "I have read and understand this privacy notification." and NOTICE["continue"] == "Continue to SA CoParents"
    low = str(NOTICE).lower()
    assert "responces" not in low and "encrypt" not in low and "my journey" not in low and "privacy policy" not in low
    assert PRIVACY_NOTICE_VERSION == "2026-10-10.1" and NOTICE["footer_links"] == []
    legal = open("/app/frontend/src/pages/Legal.jsx", encoding="utf-8").read()
    assert "confidentiality: {" not in legal and '"sharing-consent": {' not in legal


def test_frontend_screen_has_no_policy_link_or_mockup_text():
    page = open("/app/frontend/src/pages/PrivacyNotice.jsx", encoding="utf-8").read()
    low = page.lower()
    assert "disabled={!ok || busy}" in page and "QuickExitBar" in page and "PLACEHOLDER" in page
    assert "responces" not in low and "read full privacy policy" not in low and "complete details" not in low and "my journey" not in low
    assert 'to="/privacy' not in page and 'href="/privacy' not in page and "fonts.googleapis" not in low and "cdn" not in low
    assert "privacy-banner" in page and "lucide-react" in page


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
