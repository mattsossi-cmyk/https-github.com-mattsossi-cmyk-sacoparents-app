# Iteration 161: Self Journey milestone awards, monthly check-ins, certificate, PDF privacy.
import io
import os
import uuid

import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
SA_KEYS = [f"{s}_{i}" for s in ("child_focus", "self_awareness", "communication", "differences") for i in range(1, 6)]
CHECKIN_SECRET = "TEST_PRIVATE_CHECKIN_hardest_xyz"


def _register():
    email = f"test_iter161_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "Tessa Award",
        "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


def _progress(**kw):
    base = {"maxStepReached": 2, "safety": {"status": "clear", "completedAt": "2026-01-01T00:00:00Z"},
            "situation": {}, "coparenting": {}, "childNeeds": {"opened": []},
            "foundation": {"answers": {}, "draft": "", "approved": False}, "mediation": {},
            "checkIns": [], "awards": {}}
    base.update(kw)
    return base


@pytest.fixture(scope="module")
def parent():
    return _register()


# Awards: server only keeps an award whose milestone is really done
class TestAwards:
    def test_unearned_awards_are_stripped(self, parent):
        now = "2026-01-10T00:00:00Z"
        r = parent.put(f"{API}/self-journey/me", json=_progress(
            awards={"selfAssessment": now, "coparenting": now, "foundation": now, "journey": now}))
        assert r.status_code == 200
        aw = r.json()["progress"]["awards"]
        assert all(aw[k] is None for k in ("selfAssessment", "coparenting", "foundation", "journey")), aw
        g = parent.get(f"{API}/self-journey/me").json()["progress"]["awards"]
        assert g["journey"] is None

    def test_certificate_409_before_finish(self, parent):
        r = parent.get(f"{API}/self-journey/certificate")
        assert r.status_code == 409

    def test_certificate_401_without_auth(self):
        assert requests.get(f"{API}/self-journey/certificate").status_code == 401

    def test_self_assessment_award_kept_after_completion(self, parent):
        r = parent.post(f"{API}/self-assessment/complete", json={"answers": {k: 3 for k in SA_KEYS}, "parent_name": "Tessa"})
        assert r.status_code == 200, r.text
        now = "2026-01-11T00:00:00Z"
        r = parent.put(f"{API}/self-journey/me", json=_progress(awards={"selfAssessment": now}))
        assert r.json()["progress"]["awards"]["selfAssessment"] == now

    def test_award_sticks_when_client_omits_it(self, parent):
        r = parent.put(f"{API}/self-journey/me", json=_progress(awards={}))
        assert r.json()["progress"]["awards"]["selfAssessment"] == "2026-01-11T00:00:00Z"

    def test_coparenting_award_after_cp_completion(self, parent):
        a = parent.post(f"{API}/coparenting/answer", json={"question_id": "s1q1", "value": 2})
        assert a.status_code == 200, a.text
        c = parent.post(f"{API}/coparenting/complete")
        assert c.status_code == 200, c.text
        now = "2026-01-12T00:00:00Z"
        r = parent.put(f"{API}/self-journey/me", json=_progress(awards={"coparenting": now}))
        aw = r.json()["progress"]["awards"]
        assert aw["coparenting"] == now and aw["selfAssessment"] == "2026-01-11T00:00:00Z"

    def test_foundation_award_requires_approved(self, parent):
        now = "2026-01-13T00:00:00Z"
        fd = {"answers": {}, "draft": "We put our child first.", "approved": True, "approvedAt": now}
        r = parent.put(f"{API}/self-journey/me", json=_progress(foundation=fd, awards={"foundation": now}))
        assert r.json()["progress"]["awards"]["foundation"] == now

    def test_journey_award_and_certificate(self, parent):
        now = "2026-01-14T00:00:00Z"
        fd = {"answers": {}, "draft": "We put our child first.", "approved": True, "approvedAt": now}
        checkin = {"date": now, "hardest": CHECKIN_SECRET, "wentWell": "TEST_went", "helpNext": "", "planFits": "somewhat"}
        r = parent.put(f"{API}/self-journey/me", json=_progress(maxStepReached=7, foundation=fd,
                                                                checkIns=[checkin], awards={"journey": now}))
        assert r.status_code == 200
        assert r.json()["progress"]["awards"]["journey"] == now
        c = parent.get(f"{API}/self-journey/certificate")
        assert c.status_code == 200
        assert c.headers["content-type"].startswith("application/pdf")
        assert "SA_CoParents_Self_Journey_Certificate.pdf" in c.headers.get("content-disposition", "")
        text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(c.content)).pages)
        assert "Tessa" in text

    def test_checkins_persist(self, parent):
        p = parent.get(f"{API}/self-journey/me").json()["progress"]
        assert p["checkIns"][-1]["hardest"] == CHECKIN_SECRET
        assert p["checkIns"][-1]["planFits"] == "somewhat"

    def test_pdf_excludes_checkins_and_keeps_sections(self, parent):
        r = parent.get(f"{API}/self-journey/pdf")
        assert r.status_code == 200
        pages = [p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages]
        full = "\n".join(pages)
        assert CHECKIN_SECRET not in full and "TEST_went" not in full
        # each numbered section heading should not be the last line of a page (heading orphaned from body)
        for t in pages:
            lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
            if lines:
                assert not any(lines[-1].startswith(f"{n}.") for n in range(1, 8)), lines[-3:]

    def test_invalid_planfits_rejected(self, parent):
        bad = {"date": "2026-01-15T00:00:00Z", "planFits": "maybe"}
        r = parent.put(f"{API}/self-journey/me", json=_progress(checkIns=[bad]))
        assert r.status_code == 422

    def test_old_progress_without_checkins_loads(self, parent):
        legacy = _progress()
        legacy.pop("checkIns"); legacy.pop("awards")
        r = parent.put(f"{API}/self-journey/me", json=legacy)
        assert r.status_code == 200
        p = parent.get(f"{API}/self-journey/me").json()["progress"]
        assert p["checkIns"] == [] and p["awards"]["journey"] == "2026-01-14T00:00:00Z"
