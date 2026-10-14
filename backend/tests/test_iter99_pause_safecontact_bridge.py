# ruff: noqa: F811
"""Iter 99 — professional-decides pause/resume, safe contact channel, neutral notifications, redaction notice, bridge requester context.
Live E2E against preview (reuses the iter88 fixtures: pro + two invited parents on a fresh case)."""
import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_iter88_safety_e2e import BASE, MONGO, pro_session, pro_case, parent_a_session, parent_b_session, parents_accepted  # noqa: F401,E402

import integrations  # noqa: E402
from email_utils import MINIMAL_NOTIFICATIONS  # noqa: E402
from joint_engine import REDACTION_NOTICE, generate_joint_report  # noqa: E402
from joint_pause import NEUTRAL_MESSAGE  # noqa: E402
from safety_screening import clean_safe_contact, public_record, receipt, spec_export  # noqa: E402

FORBIDDEN = ("safety", "violence", "abuse", "screening", "flag", "assessment result", "tier")


# ---------------- 1. Pause / resume ----------------
class TestJointPause:
    def test_parent_cannot_pause(self, pro_case, parent_a_session, parents_accepted):
        r = parent_a_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/joint-pause", json={"paused": True}, timeout=15)
        assert r.status_code == 403

    def test_pro_pauses_with_note_and_it_is_logged(self, pro_case, pro_session):
        before = MONGO.communications.count_documents({})
        r = pro_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/joint-pause", json={"paused": True, "note": "QA private note"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["joint_paused"]["note"] == "QA private note" and d["joint_paused"]["at"] and d["history"][-1]["action"] == "pause"
        ev = MONGO.access_events.find_one({"report_id": pro_case["id"], "kind": "joint_pause"}, sort=[("at", -1)]) or MONGO.access_events.find_one({"kind": "joint_pause"}, sort=[("at", -1)])
        assert ev and "Paused joint features" in ev.get("action", "") and "QA private note" in ev.get("action", "")
        assert MONGO.communications.count_documents({}) == before, "pause must not send any email/notification"

    def test_parents_see_only_neutral_message(self, pro_case, parent_a_session, parent_b_session):
        for s in (parent_a_session, parent_b_session):
            d = s.get(f"{BASE}/api/joint/reports/{pro_case['id']}", timeout=15).json()
            assert d["joint_blocked"] is True and d["joint_blocked_message"] == NEUTRAL_MESSAGE and "joint_paused" not in d
            low = str(d).lower()
            assert "paused" not in low and "flag" not in low.replace("safety_flags", "")
            r = s.put(f"{BASE}/api/joint/reports/{pro_case['id']}/responses", json={"answers": {"routines": "x"}}, timeout=15)
            assert r.status_code == 423 and r.json()["detail"] == NEUTRAL_MESSAGE
            r = s.get(f"{BASE}/api/joint/reports/{pro_case['id']}/report", timeout=15)
            assert r.status_code == 423 and r.json()["detail"] == NEUTRAL_MESSAGE

    def test_parent_can_still_do_individual_work(self, pro_case, parent_a_session):
        r = parent_a_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}/safety-screening", timeout=15)
        assert r.status_code == 200

    def test_joint_invitation_blocked_while_paused(self, pro_case, pro_session):
        inv = MONGO.invitations.find_one({"report_id": pro_case["id"]})
        if inv and inv.get("status") == "pending":
            r = pro_session.post(f"{BASE}/api/joint/invitations/{inv['id']}/resend", timeout=15)
            assert r.status_code == 423

    def test_pro_resumes_and_it_is_logged(self, pro_case, pro_session, parent_a_session):
        r = pro_session.put(f"{BASE}/api/joint/reports/{pro_case['id']}/joint-pause", json={"paused": False, "note": "resume"}, timeout=15)
        assert r.status_code == 200 and r.json()["joint_paused"] is None and r.json()["history"][-1]["action"] == "resume"
        d = parent_a_session.get(f"{BASE}/api/joint/reports/{pro_case['id']}", timeout=15).json()
        assert d["joint_blocked"] is False


# ---------------- 3a. Safe contact channel ----------------
class TestSafeContact:
    def test_clean_and_optional(self):
        assert clean_safe_contact(None) is None and clean_safe_contact({}) is None and clean_safe_contact({"method": ""}) is None
        sc = clean_safe_contact({"method": "text", "address": "210-555-0100", "safe_times": "weekdays", "voicemail_ok": "No", "code_word": "blue"})
        assert sc["method"] == "text" and sc["code_word"] == "blue"
        assert clean_safe_contact({"method": "carrier pigeon", "address": "x"})["method"] == "Prefer not to say"

    def test_stored_visible_to_pro_only_and_never_in_projections(self, pro_case, pro_session, parent_a_session, parents_accepted):
        rid = pro_case["id"]
        parent_a_session.put(f"{BASE}/api/joint/reports/{rid}/safety-screening/choose", json={"version": "A"}, timeout=15)
        r = parent_a_session.put(f"{BASE}/api/joint/reports/{rid}/safety-screening", json={"responses": {"a1": "Never", "safe": "Very safe"},
                                 "safe_contact": {"method": "text", "address": "210-555-0100", "safe_times": "weekdays 9-3", "voicemail_ok": "No", "code_word": "QA-BLUE"}}, timeout=20)
        assert r.status_code == 200, r.text
        assert "QA-BLUE" not in r.text and "210-555-0100" not in r.text
        doc = MONGO.joint_reports.find_one({"id": rid})
        scr = doc["safety_screenings"]["a"]
        assert scr["safe_contact"]["code_word"] == "QA-BLUE"
        assert "safe_contact" not in (public_record(scr) or {}) and "QA-BLUE" not in receipt(scr, "Parent A")
        pro = pro_session.get(f"{BASE}/api/joint/reports/{rid}/safety-screening/a/responses", timeout=15).json()
        assert pro["safe_contact"]["code_word"] == "QA-BLUE"
        parent_view = parent_a_session.get(f"{BASE}/api/joint/reports/{rid}", timeout=15).text
        assert "QA-BLUE" not in parent_view and "210-555-0100" not in parent_view
        assert "safe_contact" not in str(spec_export()).lower()
        for p in ("/api/joint/reports/{rid}/report",):
            rr = pro_session.get(f"{BASE}{p.format(rid=rid)}", timeout=20)
            assert "QA-BLUE" not in rr.text

    def test_no_safe_contact_in_pdf_or_email_code_paths(self):
        for f in ("pdf_lens.py", "pdf_agreement.py", "pdf_foundation.py", "pdf_report.py", "legal_lens.py", "email_utils.py", "joint_helpers.py", "cron_jobs.py", "integrations.py", "safety_import.py"):
            assert "safe_contact" not in open(f"/app/backend/{f}", encoding="utf-8").read(), f


# ---------------- 3b. Neutral notifications ----------------
class TestNeutralNotifications:
    def test_flag_default_on(self):
        assert MINIMAL_NOTIFICATIONS is True

    def test_parent_facing_subjects_and_bodies_neutral(self):
        from joint_helpers import InviteSpec, _invite_email_content
        subj, html = _invite_email_content(InviteSpec(report_id="r", role="a", invitee_name="P", invitee_email="p@x", inviter_name="Pro", via_professional=True, child_name="Kid", subject_label="Communication"), "tok")
        low = (subj + " " + html).lower()
        for w in FORBIDDEN:
            assert w not in low, (w, subj)
        assert REDACTION_NOTICE in html and "/join/" in html or "invite" in html
        from cron_jobs import _neutral_email_html
        body = _neutral_email_html("Sam", "https://x/joint/1").lower()
        for w in FORBIDDEN + ("case", "report"):
            assert w not in body, w
        src = open("/app/backend/safety_screening.py", encoding="utf-8").read()
        assert "You have an optional step waiting in your SA CoParents account" in src and "Priority follow-up" in src

    def test_redaction_notice_in_report_output(self):
        doc = {"id": "x", "subject": "communication", "subject_label": "Communication", "child_name": "Ava", "participants": {"a": {"name": "A"}, "b": {"name": "B"}},
               "responses": {"a": {"answers": {"routines": "early"}}, "b": {"answers": {"routines": "late"}}}}
        rep = generate_joint_report(doc)
        assert rep["redaction_notice"] == REDACTION_NOTICE
        low = REDACTION_NOTICE.lower()
        assert all(w not in low for w in FORBIDDEN) and "policy" not in low and "http" not in low


# ---------------- Parent-app link contract (replaces the provisional requester context) ----------------
class TestParentAppContract:
    def test_flag_off_by_default_sends_only_shared_key(self, monkeypatch):
        import parent_app_contract as pac
        monkeypatch.setattr(pac, "PARENT_APP_LINK_CONTRACT", False)
        assert set(pac.contract_headers("p1", "c1")) == {"X-Integration-Key"}

    def test_flag_on_sends_contract_headers_only(self, monkeypatch):
        import parent_app_contract as pac
        monkeypatch.setattr(pac, "PARENT_APP_LINK_CONTRACT", True)
        h = pac.contract_headers("p1", "c1")
        assert h["X-Professional-Id"] == "p1" and h["X-Case-Id"] == "c1" and "X-Integration-Key" in h and len(h) == 3
        assert pac.contract_headers("p1", "c1", "pro@x")["X-Professional-Email"] == "pro@x"

    def test_denial_from_parent_app_is_graceful(self, monkeypatch):
        import asyncio
        import httpx
        import parent_app_contract as pac
        from fastapi import HTTPException

        class FakeClient:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def request(self, m, url, **k): return httpx.Response(404, json={"detail": "Not found"})
        monkeypatch.setattr(pac.httpx, "AsyncClient", FakeClient)
        monkeypatch.setattr(pac, "PARENT_APP_LINK_CONTRACT", True)
        with pytest.raises(HTTPException) as ei:
            asyncio.run(pac.export_assessments("p@x", "p1", "c1"))
        assert ei.value.status_code == 404 and ei.value.detail == integrations.DENIED_DETAIL
        assert not any(w in ei.value.detail.lower() for w in ("secret", "safety", "screening", "flag"))

    def test_secret_only_from_env_and_never_logged(self):
        for path in ("/app/backend/integrations.py", "/app/backend/parent_app_contract.py"):
            src = open(path, encoding="utf-8").read()
            assert "logger.info(f\"{INTEGRATION_SECRET" not in src and "print(INTEGRATION_SECRET" not in src
        core = open("/app/backend/core.py", encoding="utf-8").read()
        assert 'os.environ["INTEGRATION_SHARED_SECRET"]' in core or "os.environ.get(\"INTEGRATION_SHARED_SECRET\"" in core
