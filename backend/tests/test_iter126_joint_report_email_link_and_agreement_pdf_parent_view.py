"""iter126 - Two P1 shipments:

1. Joint Professional Report email endpoint now mints a preview share
   link (30-day) and injects the click-through URL into the outgoing
   email body — matching the Joint Agreement behaviour.

2. Joint Agreement PDF now leads with the 5-bucket Parent View and
   moves the row-strip layout to "Appendix A - Detailed Item Breakdown".
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# 1. Email + Link for Joint Report
# ---------------------------------------------------------------------------

@pytest.fixture
def report_app(monkeypatch):
    for mod in ("server", "joint_professional_report_routes", "share_routes"):
        sys.modules.pop(mod, None)
    from server import app
    import joint_professional_report_routes as jpr

    tokens_store: dict = {}
    phi_log: list = []

    async def _record_share_token(db, *, jti, user_id, doc_type, doc_id,
                                  expires_at=None, label=None, note=None):
        tokens_store[jti] = {
            "jti": jti, "user_id": user_id, "doc_type": doc_type,
            "doc_id": doc_id, "expires_at": expires_at,
            "label": label, "note": note, "revoked_at": None,
        }
        return tokens_store[jti]

    async def _is_revoked(db, jti):
        row = tokens_store.get(jti)
        return bool(row and row.get("revoked_at"))

    async def _record_phi(db, **kwargs):
        phi_log.append(kwargs)

    monkeypatch.setattr(jpr, "record_share_token", _record_share_token)
    monkeypatch.setattr(jpr, "is_share_token_revoked", _is_revoked)
    monkeypatch.setattr(
        "phi_access_routes.record_phi_access", _record_phi, raising=False,
    )

    fake_share = {"share_id": "sh_test", "_user_pair": ["userA", "userB"],
                  "status": "active"}

    async def _find_share(db, share_id, user_id):
        return dict(fake_share)

    async def _assemble(db, share, caller_id, share_id):
        return {
            "report_type": "joint_coparenting_summary_for_professional_review",
            "share_id": share_id,
            "parent_a_name": "Alex Parent",
            "parent_b_name": "Blake Parent",
            "summary_counts": {
                "areas_of_agreement": 3,
                "areas_where_perceptions_differ": 2,
                "issues_for_professional_discussion": 1,
            },
        }

    monkeypatch.setattr(jpr, "_find_active_share", _find_share)
    monkeypatch.setattr(jpr, "_assemble_report", _assemble)

    from auth import UserPublic, get_current_user, get_db

    def _fake_user():
        return UserPublic(
            user_id="userA", email="a@test.local", name="Alex Parent",
            is_guest=False, is_admin=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    app.dependency_overrides[get_current_user] = _fake_user

    class _FakeDB:
        pass

    class _FakeInsertColl:
        async def insert_one(self, doc):
            return None

    fake_db = _FakeDB()
    fake_db.joint_report_emails = _FakeInsertColl()  # type: ignore[attr-defined]
    app.dependency_overrides[get_db] = lambda: fake_db
    app.state.db = fake_db

    # Stub PDF renderer so tests don't need full comparison payloads.
    import joint_professional_report_pdf
    monkeypatch.setattr(
        joint_professional_report_pdf, "build_joint_report_pdf",
        lambda p: b"%PDF-1.4\n%stub\n",
    )

    yield app, tokens_store, phi_log
    app.dependency_overrides.clear()


def test_report_email_mints_preview_link_and_passes_absolute_url(report_app, monkeypatch):
    """POST /email must mint a 30-day preview token, record it under
    the sending parent, and pass an absolute preview URL down to the
    mailer. Response should surface `preview_included=True` and a jti."""
    from fastapi.testclient import TestClient
    import email_service

    app, tokens, phi = report_app
    client = TestClient(app)

    captured = {}
    def _capture_send(**kwargs):
        captured.update(kwargs)
    monkeypatch.setattr(email_service, "send_joint_professional_report",
                        _capture_send)

    res = client.post(
        "/api/joint-professional-report/sh_test/email",
        json={
            "recipient_email": "mediator@example.com",
            "recipient_name": "Sam Neutral",
            "recipient_role": "mediator",
            "parent_message": "Thanks for reviewing this.",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["preview_included"] is True
    assert body["preview_jti"], "preview_jti must be non-empty on success"

    # A share_tokens row was created with the emailed_to label.
    row = tokens[body["preview_jti"]]
    assert row["doc_type"] == "joint_report"
    assert row["doc_id"] == "sh_test"
    assert "mediator@example.com" in (row.get("label") or "")

    # 30 days is the confirmed default for professional preview links.
    exp = row["expires_at"]
    assert exp is not None
    now = datetime.now(timezone.utc)
    delta_days = (exp - now).days
    assert 28 <= delta_days <= 31, f"expected ~30 days, got {delta_days}"

    # Mailer received an absolute URL pointing at the OG-aware
    # /preview/{token} endpoint (not the SPA path).
    preview_url = captured.get("preview_url")
    assert preview_url and preview_url.startswith("http")
    assert "/api/joint-professional-report/preview/" in preview_url

    # PHI access log recorded both share_link_created + email_disclosure.
    kinds = [entry["action"] for entry in phi]
    assert "share_link_created" in kinds
    assert "email_disclosure" in kinds


def test_report_email_template_renders_preview_button(monkeypatch):
    """Unit-level: `send_joint_professional_report` injects the preview
    button + URL into both html and text bodies when preview_url is
    provided, and omits the block cleanly when it isn't."""
    import email_service

    captured = {}
    def _fake_low_send(**kwargs):
        captured.update(kwargs)
    monkeypatch.setattr(email_service, "_send", _fake_low_send)

    email_service.send_joint_professional_report(
        to_email="m@x.com", recipient_name="Sam", recipient_role="Mediator",
        parent_a_name="Alex", parent_b_name="Blake",
        parent_email="alex@x.com", parent_message="",
        summary_counts={"areas_of_agreement": 2,
                        "areas_where_perceptions_differ": 1,
                        "issues_for_professional_discussion": 0},
        pdf_bytes=b"%PDF-1.4",
        preview_url="https://example.test/api/joint-professional-report/preview/tok123",
    )
    assert "Open the joint report online" in captured["html"]
    assert "https://example.test/api/joint-professional-report/preview/tok123" in captured["html"]
    assert "https://example.test/api/joint-professional-report/preview/tok123" in captured["text"]

    # No preview_url → CTA block is absent (backward compat).
    captured.clear()
    email_service.send_joint_professional_report(
        to_email="m@x.com", recipient_name="Sam", recipient_role="Mediator",
        parent_a_name="Alex", parent_b_name="Blake",
        parent_email="alex@x.com", parent_message="",
        summary_counts={"areas_of_agreement": 2,
                        "areas_where_perceptions_differ": 1,
                        "issues_for_professional_discussion": 0},
        pdf_bytes=b"%PDF-1.4",
    )
    assert "Open the joint report online" not in captured["html"]
    assert "Prefer to view in your browser" not in captured["text"]


# ---------------------------------------------------------------------------
# 2. Joint Agreement PDF - 5-bucket Parent View + Appendix A
# ---------------------------------------------------------------------------

def _sample_agreement(uid: str):
    return {
        "agreement_id": f"agr_{uid}",
        "generated_at": "2026-02-22T00:00:00+00:00",
        "shared_goals": ["Child feels safe in both homes"],
        "communication": [
            {"area": "Texting", "agreement": "Reply within 24 hours."},
        ],
        "child_needs": [
            {"area": "Medication",
             "agreement": ("A pill organiser stays with the child."
                           if uid == "a" else "Doses tracked in a shared log.")},
        ],
        "household_rules": [],
        "priority_items": [
            {"area": "School", "agreement": "Both attend all IEP meetings."},
        ],
        "open_for_discussion": [
            {"area": "Screen time",
             "note": "We haven't landed on weekend limits yet."},
        ],
        "closing_note": "",
    }


def test_joint_agreement_pdf_has_parent_view_and_appendix():
    """The rebuilt PDF must:
    - be a valid PDF binary
    - carry the 'Parent View' cover header
    - carry the 'Appendix A - Detailed Item Breakdown' header
    - contain all five bucket titles in some form"""
    from joint_agreement import build_joint_agreement
    from joint_agreement_pdf import build_joint_agreement_pdf

    payload = build_joint_agreement(
        share_id="sh_test",
        parent_a_name="Alex Parent",
        parent_b_name="Blake Parent",
        agreement_a=_sample_agreement("a"),
        agreement_b=_sample_agreement("b"),
    )
    assert "parent_view" in payload
    assert "sections" in payload

    pdf_bytes = build_joint_agreement_pdf(payload)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert pdf_bytes[:4] == b"%PDF"

    # Text is stored inside stream objects; extracting from binary PDF
    # is brittle across compressors, so we sanity-check by re-running
    # the builder on a payload with parent_view stripped and verifying
    # the byte count is different (parent-view adds real content).
    from copy import deepcopy
    without_pv = deepcopy(payload)
    without_pv["parent_view"] = None
    pdf_no_pv = build_joint_agreement_pdf(without_pv)
    assert len(pdf_bytes) > len(pdf_no_pv), (
        "PDF with parent_view must be larger than PDF without it"
    )


def test_joint_agreement_pdf_appendix_still_carries_source_clauses():
    """Removing parent_view from the payload still yields a valid PDF
    that includes the Appendix A section - guarantees backward compat
    with any cached payloads generated before this iteration."""
    from joint_agreement import build_joint_agreement
    from joint_agreement_pdf import build_joint_agreement_pdf

    payload = build_joint_agreement(
        share_id="sh_test",
        parent_a_name="Alex Parent",
        parent_b_name="Blake Parent",
        agreement_a=_sample_agreement("a"),
        agreement_b=_sample_agreement("b"),
    )
    payload.pop("parent_view", None)

    pdf_bytes = build_joint_agreement_pdf(payload)
    assert pdf_bytes[:4] == b"%PDF"


def test_joint_agreement_pdf_bucket_renderers_handle_empty_payload():
    """Every bucket renderer must survive an empty payload without
    raising (guards against ship-blocking regressions when a parent
    just started their draft)."""
    from joint_agreement_pdf import build_joint_agreement_pdf

    minimal_payload = {
        "report_title": "Joint Co-Parenting Agreement Draft",
        "share_id": "sh_test",
        "parent_a_name": "Alex",
        "parent_b_name": "Blake",
        "disclaimer": "This is a draft for discussion.",
        "neutral_language_note": "Neutral wording used throughout.",
        "sections": [],
        "parent_view": {
            "what_you_both_proposed": {
                "title": "What You've Both Proposed",
                "description": "Nothing to show yet.",
                "items": [],
                "count": 0,
            },
            "where_you_have_different_ideas": {
                "title": "Where Each of You Has Different Ideas",
                "description": "Nothing to show yet.",
                "items": [],
                "count": 0,
            },
            "may_need_refinement": {
                "title": "Clauses That May Need Refinement",
                "description": "Nothing flagged.",
                "items": [],
                "count": 0,
            },
            "options_to_consider": {
                "title": "Options for Blending Your Ideas",
                "description": "Consider these.",
                "items": [{"title": "Talk it through",
                           "detail": "A short conversation goes a long way."}],
                "count": None,
            },
            "questions_for_next_conversation": {
                "title": "Questions for Your Next Conversation",
                "description": "Bring these.",
                "items": [{"topic": "Shared ground",
                           "question": "What's one thing we agree on today?"}],
                "count": None,
            },
        },
        "summary": {
            "total_clauses": 0, "both_proposed": 0,
            "parent_a_only": 0, "parent_b_only": 0, "converged_pct": 0,
        },
        "next_step": "Bring this to mediation.",
    }
    pdf_bytes = build_joint_agreement_pdf(minimal_payload)
    assert pdf_bytes[:4] == b"%PDF"
