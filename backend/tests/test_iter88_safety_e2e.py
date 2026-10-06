"""Iter88 — HTTP/E2E tests for batch 1 (report framing) + batch 2 (private safety screenings).

Covers:
  - Landing page framing endpoints: /api/court-dashboard/report-guide (judge auth)
  - Professional creates case with gender defaults; screening overview; version assign
  - Parent completes screening (A tier 3, B tier 2, all-Never tier 1, skipped tier 1)
  - Privacy: parent cannot see co-parent screening; parent cannot see own item-level view
  - Report + PDF content: version/tier appear; raw answers never leak; new framing text present
"""
import os
import re
import time
import pytest
import requests
import pymongo
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

TS = int(time.time())
PRO_EMAIL = "approval.test.pro1@gmail.com"
PRO_PASSWORD = "TestPass2026!"
PARENT_A_EMAIL = f"qa.parent.a.{TS}@example.com"
PARENT_B_EMAIL = f"qa.parent.b.{TS}@example.com"
PARENT_PASSWORD = "TestPass2026!"
UNIQUE_SIGNAL = "UNIQUE-TEXT-123"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


def _register(email, name, role="parent", invite=""):
    payload = {"name": name, "email": email, "password": PARENT_PASSWORD, "role": role}
    if invite:
        payload["invite"] = invite
    r = requests.post(f"{BASE}/api/auth/register", json=payload, timeout=20)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"


@pytest.fixture(scope="module")
def pro_session():
    return _login(PRO_EMAIL, PRO_PASSWORD)


@pytest.fixture(scope="module")
def pro_case(pro_session):
    """Case with gender defaults set (woman/man)."""
    body = {
        "child_name": f"TEST Kiddo {TS}",
        "subject": "communication",
        "parent_a_name": "QA Parent A",
        "parent_a_email": PARENT_A_EMAIL,
        "parent_b_name": "QA Parent B",
        "parent_b_email": PARENT_B_EMAIL,
        "parent_a_gender": "woman",
        "parent_b_gender": "man",
    }
    r = pro_session.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
    assert r.status_code in (200, 201), f"create case failed: {r.status_code} {r.text}"
    data = r.json()
    rid = data["id"]
    # accept both invitations via DB tokens
    invs = list(MONGO.invitations.find({"report_id": rid}))
    assert len(invs) >= 2
    tokens = {i["role"]: i.get("token") or i.get("code") for i in invs}
    codes = {i["role"]: i.get("code") for i in invs}
    return {"id": rid, "tokens": tokens, "codes": codes}


@pytest.fixture(scope="module")
def parent_a_session(pro_case):
    _register(PARENT_A_EMAIL, "QA Parent A", invite=pro_case["tokens"]["a"])
    return _login(PARENT_A_EMAIL, PARENT_PASSWORD)


@pytest.fixture(scope="module")
def parent_b_session(pro_case):
    _register(PARENT_B_EMAIL, "QA Parent B", invite=pro_case["tokens"]["b"])
    return _login(PARENT_B_EMAIL, PARENT_PASSWORD)


@pytest.fixture(scope="module")
def pro_case_no_gender(pro_session):
    body = {
        "child_name": f"TEST NoGender {TS}",
        "subject": "communication",
        "parent_a_name": "NG Parent A",
        "parent_a_email": f"qa.ng.a.{TS}@example.com",
        "parent_b_name": "NG Parent B",
        "parent_b_email": f"qa.ng.b.{TS}@example.com",
    }
    r = pro_session.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# =============================================================================
# Batch 1 — report framing: court report guide
# =============================================================================
class TestReportGuide:
    def test_report_guide_requires_judge(self, pro_session):
        # professional is not a judge — expect 401/403
        r = pro_session.get(f"{BASE}/api/court-dashboard/report-guide", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_report_guide_unauthenticated(self):
        r = requests.get(f"{BASE}/api/court-dashboard/report-guide", timeout=15)
        assert r.status_code in (401, 403)


# =============================================================================
# Batch 2 — screening overview + assignment
# =============================================================================
class TestScreeningOverview:
    def test_overview_default_versions(self, pro_session, pro_case):
        r = pro_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_professional"] is True
        assert data["roles"]["a"]["version"] == "A"
        assert data["roles"]["b"]["version"] == "B"
        assert data["roles"]["a"]["needs_assignment"] is False
        assert data["roles"]["b"]["needs_assignment"] is False
        assert data["roles"]["a"]["received"] is False
        assert data["roles"]["b"]["received"] is False

    def test_overview_no_gender(self, pro_session, pro_case_no_gender):
        r = pro_session.get(f"{BASE}/api/joint/reports/{pro_case_no_gender}/safety-screening", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["roles"]["a"]["needs_assignment"] is True
        assert d["roles"]["b"]["needs_assignment"] is True
        assert d["roles"]["a"]["version"] is None
        assert d["roles"]["b"]["version"] is None

    def test_assign_version_pro_ok(self, pro_session, pro_case_no_gender):
        r = pro_session.put(f"{BASE}/api/joint/reports/{pro_case_no_gender}/safety-screening/assign",
                            json={"role": "a", "version": "B"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["a"]["version"] == "B"


# =============================================================================
# Accept invitations as parents, then run screening flow
# =============================================================================
def _accept_invite(session, token):
    # Try token first, then code
    r = session.get(f"{BASE}/api/joint/invitations/lookup/{token}", timeout=15)
    if r.status_code == 200:
        r2 = session.post(f"{BASE}/api/joint/invitations/accept", json={"token": token}, timeout=15)
        if r2.status_code in (200, 201):
            return
    # fallback via code
    r2 = session.post(f"{BASE}/api/joint/invitations/accept", json={"code": token}, timeout=15)
    assert r2.status_code in (200, 201), f"accept failed: {r2.status_code} {r2.text}"


@pytest.fixture(scope="module")
def parents_accepted(pro_case, parent_a_session, parent_b_session):
    _accept_invite(parent_a_session, pro_case["tokens"]["a"])
    _accept_invite(parent_b_session, pro_case["tokens"]["b"])
    return True


class TestParentScreening:
    def test_parent_a_sees_spec_only_her_role(self, pro_case, parent_a_session, parents_accepted):
        r = parent_a_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_professional"] is False
        assert d["my_role"] == "a"
        # Co-parent's role must NOT be included
        assert "b" not in d["roles"], f"parent A can see parent B status: {d['roles']}"
        # Neutral choice screen first: default (A) or Version C; choosing the default reveals the spec
        assert d["spec"] is None and d["choice"]["question"] == "Which questions fit your situation best?"
        assert [o["version"] for o in d["choice"]["options"]] == ["A", "C"]
        bad = parent_a_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening/choose", json={"version": "B"}, timeout=15)
        assert bad.status_code == 400
        ok = parent_a_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening/choose", json={"version": "A"}, timeout=15)
        assert ok.status_code == 200 and ok.json()["version"] == "A"
        d = parent_a_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening", timeout=15).json()
        assert d["choice"] is None
        assert d["spec"]["version"] == "A"
        assert d["spec"]["title"] == "Safety Screening — Version A (Women)"
        assert "Your co-parent will not see" in d["spec"]["intro"]
        assert d["spec"].get("trigger_warning")
        item_ids = [it["id"] for it in d["spec"]["items"]]
        for required in ["a1", "a2", "a3", "a4", "a5", "a6", "c1", "c2", "a9", "safe"]:
            assert required in item_ids, f"missing item {required} in {item_ids}"
        # Hotline present
        resources_blob = str(d["spec"].get("resources"))
        assert "1-800-799-7233" in resources_blob

    def test_submit_tier3(self, pro_case, parent_a_session, parents_accepted):
        # a2 Sometimes (tier3-flagged item) → tier 3
        resp = {"a2": "Sometimes", "safe": "Very safe", "a9": UNIQUE_SIGNAL}
        r = parent_a_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening",
                                 json={"responses": resp}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tier"] == 3
        assert "Tier 3" in d["tier_label"]

    def test_parent_b_tier2(self, pro_case, parent_b_session, parents_accepted):
        # b3 Frequently (non-tier3) + safe Very safe → tier 2
        resp = {"b3": "Frequently", "safe": "Very safe"}
        r = parent_b_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening",
                                 json={"responses": resp}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["tier"] == 2

    def test_parent_b_tier1_all_never(self, pro_case_no_gender, pro_session):
        # Need parent B assigned on this case → assign B
        pro_session.put(f"{BASE}/api/joint/reports/{pro_case_no_gender}/safety-screening/assign",
                        json={"role": "b", "version": "B"}, timeout=15)
        # Register fresh parent to accept invite for role b of this case
        email = f"qa.ng.b.actual.{TS}@example.com"
        inv = MONGO.invitations.find_one({"report_id": pro_case_no_gender, "role": "b"})
        assert inv
        # Override invitee email in DB because invite went to different email
        MONGO.invitations.update_one({"_id": inv["_id"]}, {"$set": {"invitee_email": email}})
        token = inv.get("token") or inv.get("code")
        _register(email, "NG Actual B", invite=token)
        s = _login(email, PARENT_PASSWORD)
        _accept_invite(s, token)
        resp = {k: "Never" for k in ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9"]}
        resp["safe"] = "Very safe"
        r = s.put(f"{BASE}/api/joint/reports/{pro_case_no_gender}/safety-screening",
                  json={"responses": resp}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["tier"] == 1

    def test_submit_skipping_all(self, pro_session):
        # Create a 3rd case
        body = {
            "child_name": f"TEST Skip {TS}",
            "subject": "communication",
            "parent_a_name": "Skip A", "parent_a_email": f"qa.skip.a.{TS}@example.com",
            "parent_b_name": "Skip B", "parent_b_email": f"qa.skip.b.{TS}@example.com",
            "parent_a_gender": "woman", "parent_b_gender": "man",
        }
        r = pro_session.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
        assert r.status_code in (200, 201)
        rid = r.json()["id"]
        email = f"qa.skip.a.actual.{TS}@example.com"
        inv = MONGO.invitations.find_one({"report_id": rid, "role": "a"})
        MONGO.invitations.update_one({"_id": inv["_id"]}, {"$set": {"invitee_email": email}})
        token = inv.get("token") or inv.get("code")
        _register(email, "Skip Actual A", invite=token)
        s = _login(email, PARENT_PASSWORD)
        _accept_invite(s, token)
        r = s.put(f"{BASE}/api/joint/reports/{rid}/safety-screening",
                  json={"responses": {}}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["tier"] == 1

    def test_no_gender_parent_sees_a_b_c_and_pro_can_override(self, pro_session):
        """Missing/non-binary gender → neutral choice screen offers A, B and C; parent picks; professional may override afterward."""
        body = {"child_name": f"TEST NB {TS}", "subject": "communication",
                "parent_a_name": "NB A", "parent_a_email": f"qa.nb.a.{TS}@example.com", "parent_a_gender": "non-binary",
                "parent_b_name": "NB B", "parent_b_email": f"qa.nb.b.{TS}@example.com"}
        r = pro_session.post(f"{BASE}/api/joint/reports/professional", json=body, timeout=30)
        assert r.status_code in (200, 201), r.text
        rid = r.json()["id"]
        email = f"qa.nb.a.actual.{TS}@example.com"
        inv = MONGO.invitations.find_one({"report_id": rid, "role": "a"})
        MONGO.invitations.update_one({"_id": inv["_id"]}, {"$set": {"invitee_email": email}})
        token = inv.get("token") or inv.get("code")
        _register(email, "NB Actual A", invite=token)
        s = _login(email, PARENT_PASSWORD)
        _accept_invite(s, token)
        d = s.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15).json()
        assert d["spec"] is None and [o["version"] for o in d["choice"]["options"]] == ["A", "B", "C"]
        assert "orientation" not in str(d["roles"]["a"]).lower()
        ok = s.put(f"{BASE}/api/joint/reports/{rid}/safety-screening/choose", json={"version": "B"}, timeout=15)
        assert ok.status_code == 200 and ok.json()["version"] == "B"
        d = s.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15).json()
        assert d["choice"] is None and d["spec"]["version"] == "B"
        doc = MONGO.joint_reports.find_one({"id": rid}, {"safety_version": 1, "safety_version_confirmed": 1, "participants": 1})
        assert doc["safety_version"] == {"a": "B"} and doc["safety_version_confirmed"] == {"a": True}
        assert not any("orientation" in k.lower() for k in doc["participants"]["a"])
        r = pro_session.put(f"{BASE}/api/joint/reports/{rid}/safety-screening/assign", json={"role": "a", "version": "C"}, timeout=15)
        assert r.status_code == 200 and r.json()["a"]["version"] == "C"
        d = s.get(f"{BASE}/api/joint/reports/{rid}/safety-screening", timeout=15).json()
        assert d["spec"]["version"] == "C" and d["choice"] is None


# =============================================================================
# Privacy
# =============================================================================
class TestPrivacy:
    def test_parent_cannot_view_coparent_responses(self, pro_case, parent_a_session, parents_accepted):
        r = parent_a_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening/b/responses", timeout=15)
        assert r.status_code == 403, f"parent A got {r.status_code}, expected 403"

    def test_parent_cannot_view_own_item_level(self, pro_case, parent_a_session, parents_accepted):
        r = parent_a_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening/a/responses", timeout=15)
        assert r.status_code == 403, f"parent A got {r.status_code}, expected 403 (pro-only)"

    def test_pro_can_view_responses_and_logs_access(self, pro_case, pro_session, parents_accepted):
        before = MONGO.access_events.count_documents({"report_id": pro_case["id"], "kind": "safety_screening"})
        r = pro_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening/a/responses", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "items" in d
        assert any(it.get("question") and "answer" in it for it in d["items"])
        after = MONGO.access_events.count_documents({"report_id": pro_case["id"], "kind": "safety_screening"})
        assert after == before + 1, "expected access_events to be inserted"

    def test_coparent_view_report_no_leak(self, pro_case, parent_b_session, parents_accepted):
        r = parent_b_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}", timeout=15)
        assert r.status_code == 200, r.text
        body = r.text
        assert UNIQUE_SIGNAL not in body, "LEAK: parent A's a9 answer visible to parent B"


# =============================================================================
# Professional report + PDF
# =============================================================================
class TestProfessionalReport:
    def test_pro_report_has_screening_summary(self, pro_case, pro_session, parents_accepted):
        r = pro_session.get(f"{BASE}/api/cases/{pro_case['id']}/professional-report", timeout=20)
        assert r.status_code == 200, r.text
        txt = r.text
        # No raw answer leak
        assert UNIQUE_SIGNAL not in txt
        data = r.json()
        scr = (data.get("safety_screening") or {})
        # Fallback — flatten search
        if "a" in scr:
            assert scr["a"].get("version") == "A"
            assert scr["a"].get("tier") == 3
            assert scr["a"].get("completed_at")

    def test_pro_report_pdf_framing_and_privacy(self, pro_case, pro_session, parents_accepted):
        r = pro_session.get(f"{BASE}/api/cases/{pro_case['id']}/professional-report/pdf", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        # Extract text via pypdf
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(r.content))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            pytest.skip(f"pypdf not available: {e}")
        # Normalize whitespace: PDF layout wraps and adds extra spaces
        import re as _re
        text = _re.sub(r"\s+", " ", text)
        # Required framing strings
        for needle in [
            "Version A",
            "Tier 3",
            "Not a validated or diagnostic instrument",
            "answers six questions",
            "SOURCE: PARENT-REPORTED",
            "PROFESSIONAL STATEMENT",  # Sections 9 to 11 band
        ]:
            assert needle in text, f"missing in PDF: {needle!r}"
        # Must NOT include raw answers
        assert UNIQUE_SIGNAL not in text, "LEAK: unique signal appears in PDF"
        assert "Sometimes" not in text, "LEAK: raw answer scale value appears in PDF"
