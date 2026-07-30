"""API integration tests for the SNC co-parent invite + comparison flow.

Covers /api/snc/invite/* and /api/snc/comparison/* including:
  * invite creation, self-invite rejection, listing (sent vs received)
  * public token lookup
  * accept flow (own → 400, second acceptor → 409)
  * resend cooldown (429)
  * delete
  * comparison lifecycle (missing b_accepted → missing b_report → ready → cached → regenerate)
  * guardrails: no s11, no verbatim narratives, no winner/right/correct-parent language
  * 3rd-party 403 authorisation
"""
from __future__ import annotations

import json
import re
import time
import uuid

import pytest
import requests


SECRET_NARRATIVE = "SECRET_NARRATIVE_XYZ"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------
def _register(base_url: str, tag: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_snc_{tag}_{suffix}@test.com"
    payload = {"email": email, "password": "TestPass123!", "name": f"Test {tag.capitalize()}"}
    r = requests.post(f"{base_url}/api/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"register {tag} failed: {r.status_code} {r.text}"
    data = r.json()
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {data['access_token']}",
    })
    return {"email": email, "token": data["access_token"], "user": data["user"], "session": s}


def _full_answers(strengths_text: str = "Curious. Kind. Loves dinosaurs.") -> dict:
    """Full 92-item answer set with narrative for s1_strengths."""
    from snc_questions import scored_items  # noqa: WPS433

    a: dict = {}
    likert_sections = {"s2": 8, "s3": 9, "s4": 10, "s5": 10,
                       "s7": 8, "s8": 8, "s9": 10, "s10": 7, "s12": 10}
    for sid, n in likert_sections.items():
        for i in range(1, n + 1):
            a[f"{sid}_q{i}"] = 4
    for it in scored_items("s6"):
        a[it["id"]] = 5
    a["s1_age"] = "8 years / 3rd grade"
    a["s1_strengths"] = strengths_text
    a["s1_joy"] = "Drawing, biking."
    a["s1_diagnosis_status"] = "Diagnosis or eligibility determination received"
    a["s1_needs"] = ["ADHD or executive functioning"]
    a["s1_needs_narrative"] = "ADHD-Combined."
    a["s11_flags"] = ["None of these apply."]
    a["s13_goals"] = "Predictable bedtime; shared homework."
    a["s13_concerns"] = "Homework meltdowns."
    a["s13_info_needed"] = "Medication dose review."
    a["s13_thirty_day"] = "Try shared parenting app."
    return a


def _generate_report_for(base_url: str, session: requests.Session, narrative: str) -> None:
    r = session.post(f"{base_url}/api/snc/answers/bulk",
                     json={"answers": _full_answers(narrative)})
    assert r.status_code == 200, r.text
    r = session.post(f"{base_url}/api/snc/report/generate")
    assert r.status_code == 200, r.text


@pytest.fixture(scope="module")
def parent_a(base_url):
    return _register(base_url, "a")


@pytest.fixture(scope="module")
def parent_b(base_url):
    return _register(base_url, "b")


@pytest.fixture(scope="module")
def parent_c(base_url):
    """Third unrelated user (used for 403 auth test + already-accepted 409 test)."""
    return _register(base_url, "c")


# ---------------------------------------------------------------------------
# Invite create / list / lookup
# ---------------------------------------------------------------------------
class TestInviteCreate:
    def test_rejects_self_invite(self, base_url, parent_a):
        r = parent_a["session"].post(
            f"{base_url}/api/snc/invite/coparent",
            json={"email": parent_a["email"]},
        )
        assert r.status_code == 400, r.text

    def test_rejects_invalid_email(self, base_url, parent_a):
        r = parent_a["session"].post(
            f"{base_url}/api/snc/invite/coparent",
            json={"email": "not-an-email"},
        )
        # EmailStr validation → 422 (FastAPI/Pydantic)
        assert r.status_code in (400, 422), r.text

    def test_create_invite_ok(self, base_url, parent_a, parent_b):
        r = parent_a["session"].post(
            f"{base_url}/api/snc/invite/coparent",
            json={"email": parent_b["email"]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "accept_url" in data
        assert re.search(r"/special-needs/invite/[A-Za-z0-9_\-]+$", data["accept_url"]), data["accept_url"]
        assert data["invite"]["status"] == "pending"
        assert data["invite"]["invitee_email"] == parent_b["email"].lower()
        assert data["invite"]["token"], "inviter should see the token"
        assert data["invite"]["direction"] == "sent"
        # Stash for later tests
        pytest._snc_invite = data["invite"]
        pytest._snc_accept_url = data["accept_url"]


class TestInviteList:
    def test_sender_sees_sent_with_token(self, base_url, parent_a):
        r = parent_a["session"].get(f"{base_url}/api/snc/invite/mine")
        assert r.status_code == 200, r.text
        data = r.json()
        assert any(row.get("token") for row in data["sent"]), "sender should see raw token in sent list"

    def test_receiver_view_before_accept_has_no_token(self, base_url, parent_b):
        # Before acceptance, receiver's own /invite/mine "received" list is empty
        # (received is keyed on accepted_by_user_id). This validates that the
        # sender's token is not leaked to arbitrary logged-in users.
        r = parent_b["session"].get(f"{base_url}/api/snc/invite/mine")
        assert r.status_code == 200, r.text
        data = r.json()
        for row in data.get("received", []):
            assert "token" not in row or not row["token"], "received rows must not expose token"


class TestPublicTokenLookup:
    def test_by_token_no_auth(self, base_url):
        token = pytest._snc_accept_url.rsplit("/", 1)[-1]
        r = requests.get(f"{base_url}/api/snc/invite/by-token/{token}", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "pending"
        assert data.get("from_name")
        assert data.get("invitee_email")
        # Must not leak the raw token back
        assert "token" not in data


# ---------------------------------------------------------------------------
# Accept flow
# ---------------------------------------------------------------------------
class TestAcceptFlow:
    def test_own_accept_rejected(self, base_url, parent_a):
        token = pytest._snc_accept_url.rsplit("/", 1)[-1]
        r = parent_a["session"].post(f"{base_url}/api/snc/invite/accept/{token}")
        assert r.status_code == 400, r.text

    def test_parent_b_accepts(self, base_url, parent_b):
        token = pytest._snc_accept_url.rsplit("/", 1)[-1]
        r = parent_b["session"].post(f"{base_url}/api/snc/invite/accept/{token}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["invite"]["status"] == "accepted"
        assert data["invite"]["accepted_by_user_id"]
        assert data["invite"]["accepted_at"]

    def test_third_party_accept_conflicts(self, base_url, parent_c):
        token = pytest._snc_accept_url.rsplit("/", 1)[-1]
        r = parent_c["session"].post(f"{base_url}/api/snc/invite/accept/{token}")
        assert r.status_code == 409, r.text


# ---------------------------------------------------------------------------
# Resend + delete
# ---------------------------------------------------------------------------
class TestResendCooldown:
    def test_resend_after_recent_send_returns_429(self, base_url, parent_a, parent_b):
        # Create a fresh pending invite to a NEW email so the cooldown check
        # is exercised without interfering with the accepted invite above.
        # But: create_snc_invite also updates last_sent_at. So first create,
        # then attempt resend immediately.
        fresh_email = f"TEST_snc_target_{uuid.uuid4().hex[:8]}@test.com"
        r = parent_a["session"].post(
            f"{base_url}/api/snc/invite/coparent",
            json={"email": fresh_email},
        )
        assert r.status_code == 200, r.text
        invite_id = r.json()["invite"]["invite_id"]
        # Immediate resend should hit the 5-minute cooldown
        rr = parent_a["session"].post(f"{base_url}/api/snc/invite/{invite_id}/resend")
        assert rr.status_code == 429, rr.text
        # Cleanup this ephemeral invite
        parent_a["session"].delete(f"{base_url}/api/snc/invite/{invite_id}")


class TestDeleteInvite:
    def test_only_inviter_can_delete(self, base_url, parent_a, parent_b):
        # Create an ephemeral invite from A → B (or arbitrary email)
        target = f"TEST_snc_del_{uuid.uuid4().hex[:8]}@test.com"
        r = parent_a["session"].post(
            f"{base_url}/api/snc/invite/coparent",
            json={"email": target},
        )
        assert r.status_code == 200, r.text
        invite_id = r.json()["invite"]["invite_id"]
        # A different user cannot delete
        rr = parent_b["session"].delete(f"{base_url}/api/snc/invite/{invite_id}")
        assert rr.status_code == 404, rr.text
        # Inviter can delete
        r_ok = parent_a["session"].delete(f"{base_url}/api/snc/invite/{invite_id}")
        assert r_ok.status_code == 200, r_ok.text
        assert r_ok.json()["ok"] is True


# ---------------------------------------------------------------------------
# Comparison lifecycle
# ---------------------------------------------------------------------------
class TestComparisonLifecycle:
    def test_regenerate_before_accept_would_have_failed_but_b_already_accepted(self, base_url, parent_a):
        # Sanity: after Parent B accepted (in TestAcceptFlow), comparison should
        # be blocked because neither report has been generated yet.
        invite_id = pytest._snc_invite["invite_id"]
        r = parent_a["session"].get(f"{base_url}/api/snc/comparison/{invite_id}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ready"] is False
        # After acceptance, b_accepted must be True (endpoint reports true when parent_b_id is set)
        assert data["missing"]["b_accepted"] is True
        assert data["missing"]["a_report"] is True
        assert data["missing"]["b_report"] is True

    def test_after_a_report_only_b_report_missing(self, base_url, parent_a):
        _generate_report_for(base_url, parent_a["session"], SECRET_NARRATIVE + "_A")
        invite_id = pytest._snc_invite["invite_id"]
        r = parent_a["session"].get(f"{base_url}/api/snc/comparison/{invite_id}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ready"] is False
        assert data["missing"]["a_report"] is False
        assert data["missing"]["b_report"] is True

    def test_ready_after_both_reports(self, base_url, parent_a, parent_b):
        _generate_report_for(base_url, parent_b["session"], SECRET_NARRATIVE + "_B")
        invite_id = pytest._snc_invite["invite_id"]
        r = parent_a["session"].get(f"{base_url}/api/snc/comparison/{invite_id}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ready"] is True
        assert data["comparison"] is not None
        assert data["generated_at"]
        # First call: not cached (freshly built)
        # Second call: cached
        r2 = parent_a["session"].get(f"{base_url}/api/snc/comparison/{invite_id}")
        assert r2.status_code == 200, r2.text
        assert r2.json()["cached"] is True

    def test_regenerate_returns_fresh(self, base_url, parent_a):
        invite_id = pytest._snc_invite["invite_id"]
        r = parent_a["session"].post(f"{base_url}/api/snc/comparison/{invite_id}/regenerate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ready"] is True
        assert data["cached"] is False


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------
class TestComparisonGuardrails:
    def _payload(self, base_url, parent_a):
        invite_id = pytest._snc_invite["invite_id"]
        r = parent_a["session"].get(f"{base_url}/api/snc/comparison/{invite_id}")
        assert r.status_code == 200, r.text
        return r.json()

    def test_no_section_11(self, base_url, parent_a):
        data = self._payload(base_url, parent_a)
        cmp = data["comparison"]
        cat_ids = [c["id"] for c in cmp["categories"]]
        assert "s11" not in cat_ids
        for bucket_key in ("agreement", "different_observations", "missing_information"):
            assert "s11" not in cmp["buckets"][bucket_key]

    def test_no_verbatim_narrative(self, base_url, parent_a):
        data = self._payload(base_url, parent_a)
        blob = json.dumps(data["comparison"])
        assert SECRET_NARRATIVE not in blob, "verbatim narrative leaked into comparison payload"

    def test_no_winner_language(self, base_url, parent_a):
        data = self._payload(base_url, parent_a)
        blob = json.dumps(data["comparison"]).lower()
        # The disclaimer contains the word "correct" surrounded by quotes so
        # we specifically look for the phrases these guardrails forbid.
        for phrase in ("correct parent", "wrong parent", "right parent", "winner"):
            assert phrase not in blob, f"forbidden phrase found in comparison: {phrase!r}"

    def test_safety_notice_present(self, base_url, parent_a):
        data = self._payload(base_url, parent_a)
        assert "safety" in (data["comparison"]["safety_notice"] or "").lower()


# ---------------------------------------------------------------------------
# Authorisation
# ---------------------------------------------------------------------------
class TestComparisonAuthorisation:
    def test_third_party_403(self, base_url, parent_c):
        invite_id = pytest._snc_invite["invite_id"]
        r = parent_c["session"].get(f"{base_url}/api/snc/comparison/{invite_id}")
        assert r.status_code == 403, r.text

    def test_unauthenticated_401(self, base_url):
        invite_id = pytest._snc_invite["invite_id"]
        r = requests.get(f"{base_url}/api/snc/comparison/{invite_id}", timeout=15)
        assert r.status_code in (401, 403), r.text
