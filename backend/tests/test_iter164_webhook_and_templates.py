"""Iteration 164 — Accept-webhook + reminder-note templates.

Covers:
  * `POST /api/professional/directory/invite/accept-webhook`
      - happy path flips invite to accepted
      - idempotent (second call returns applied=false)
      - bad HMAC signature → 401
      - missing signature header → 401
      - unknown token → 404
      - case-bound invite pushes an event to the case doc
  * `GET  /api/professional/directory/invites` (mediator audit list)
      - returns only own invites, redacts invite_token
  * `GET/POST/DELETE /api/professional/reminder-note-templates`
      - create + list round-trip, alphabetical order
      - 240-char cap
      - duplicate label 409
      - foreign delete 404
      - 12-template hard cap
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid
from typing import Tuple

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


WEBHOOK_URL = f"{BASE_URL}/api/professional/directory/invite/accept-webhook"
INVITES_LIST_URL = f"{BASE_URL}/api/professional/directory/invites"
TEMPLATES_URL = f"{BASE_URL}/api/professional/reminder-note-templates"

# Same value seeded in /app/backend/.env for this test env — the code
# reads os.environ inside the server process, so we mirror it here to
# sign the outgoing test payloads.
WEBHOOK_SECRET = os.environ.get(
    "SACOPARENTSALIGN_WEBHOOK_SECRET",
    "whsec_sacpa_test_a1b2c3d4e5f6",
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _register(prefix: str) -> Tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"Pro {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256,
    ).hexdigest()


def _mint_invite(prof_id: str = "sacpa-004") -> Tuple[str, str, str]:
    """Register a mediator, dispatch an invite, and pull the raw
    invite_token back out of the join_url so we can exercise the
    webhook end-to-end. Returns (mediator_token, invite_id,
    invite_token)."""
    _email, mediator_token = _register("wh-inv")
    r = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": prof_id, "personal_note": "Hi!"},
        headers=_headers(mediator_token), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # The join_url looks like https://sacoparentsalign.com/join?token=<tok>
    # (or `case=SA-...&token=<tok>` when bound). Grab the token.
    join_url = data["join_url"]
    token = join_url.split("token=", 1)[-1]
    return mediator_token, data["invite_id"], token


# ---------------------------------------------------------------------
# Webhook — signature guardrails
# ---------------------------------------------------------------------

def test_webhook_requires_signature_header():
    _mtok, _iid, invite_token = _mint_invite()
    body = json.dumps({"token": invite_token}).encode("utf-8")
    r = requests.post(WEBHOOK_URL, data=body, timeout=30,
                      headers={"Content-Type": "application/json"})
    assert r.status_code == 401


def test_webhook_rejects_bad_signature():
    _mtok, _iid, invite_token = _mint_invite()
    body = json.dumps({"token": invite_token}).encode("utf-8")
    r = requests.post(
        WEBHOOK_URL, data=body, timeout=30,
        headers={
            "Content-Type": "application/json",
            "X-Sacoparentsalign-Signature": "sha256=deadbeef",
        },
    )
    assert r.status_code == 401


def test_webhook_404s_unknown_token():
    body = json.dumps({"token": "unknown-token-xyz-123"}).encode("utf-8")
    r = requests.post(
        WEBHOOK_URL, data=body, timeout=30,
        headers={
            "Content-Type": "application/json",
            "X-Sacoparentsalign-Signature": _sign(body),
        },
    )
    assert r.status_code == 404


def test_webhook_happy_path_flips_invite_and_is_idempotent():
    mediator_token, invite_id, invite_token = _mint_invite("sacpa-001")
    body = json.dumps({
        "token": invite_token,
        "accepted_at": "2026-09-07T21:20:00Z",
        "professional_id": "sacpa-001",
        "professional_name": "Adele Van Wyk",
        "professional_email": "adele@sacoparentsalign.com",
    }).encode("utf-8")
    sig = _sign(body)
    r1 = requests.post(WEBHOOK_URL, data=body, timeout=30, headers={
        "Content-Type": "application/json",
        "X-Sacoparentsalign-Signature": sig,
    })
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert j1["ok"] is True and j1["status"] == "accepted"
    assert j1["applied"] is True
    # Second call → idempotent.
    r2 = requests.post(WEBHOOK_URL, data=body, timeout=30, headers={
        "Content-Type": "application/json",
        "X-Sacoparentsalign-Signature": sig,
    })
    assert r2.status_code == 200
    assert r2.json()["applied"] is False

    # Mediator now sees the invite as accepted on their audit list.
    r3 = requests.get(INVITES_LIST_URL, headers=_headers(mediator_token), timeout=30)
    assert r3.status_code == 200
    invites = r3.json()["invites"]
    matched = [i for i in invites if i["invite_id"] == invite_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "accepted"
    assert matched[0]["accepted_at"] is not None
    assert matched[0]["accepted_professional_name"] == "Adele Van Wyk"
    # invite_token must NEVER be leaked back to the mediator (would let
    # them forge webhook calls).
    assert "invite_token" not in matched[0]


def test_webhook_case_bound_appends_acceptance_to_case_doc():
    # Register a mediator + mint a case.
    _email, mediator_token = _register("whcase")
    case_body = {
        "assessment_type": "communication",
        "parents": [
            {"email": f"pa-{uuid.uuid4().hex[:6]}@example.com", "name": "PA"},
            {"email": f"pb-{uuid.uuid4().hex[:6]}@example.com", "name": "PB"},
        ],
    }
    case_res = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json=case_body, headers=_headers(mediator_token), timeout=30,
    ).json()
    case_id = case_res["case_id"]

    # Dispatch a case-bound invite for that mediator.
    inv = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-002", "case_id": case_id},
        headers=_headers(mediator_token), timeout=30,
    )
    assert inv.status_code == 200, inv.text
    invite_token = inv.json()["join_url"].split("token=", 1)[-1]

    # Fire the webhook.
    body = json.dumps({
        "token": invite_token,
        "professional_id": "sacpa-002",
        "professional_name": "Dr. Nomsa Dlamini",
        "professional_email": "nomsa@sacoparentsalign.com",
    }).encode("utf-8")
    r = requests.post(WEBHOOK_URL, data=body, timeout=30, headers={
        "Content-Type": "application/json",
        "X-Sacoparentsalign-Signature": _sign(body),
    })
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["case_id"] == case_id
    assert j["applied"] is True

    # /cases-i-created now shows the acceptance on the case doc.
    r_cases = requests.get(
        f"{BASE_URL}/api/professional/joint-alignment/cases-i-created",
        headers=_headers(mediator_token), timeout=30,
    )
    assert r_cases.status_code == 200
    matched = [c for c in r_cases.json()["cases"] if c["case_id"] == case_id]
    assert len(matched) == 1
    accepts = matched[0].get("directory_invite_acceptances") or []
    assert len(accepts) == 1
    assert accepts[0]["professional_name"] == "Dr. Nomsa Dlamini"
    assert accepts[0]["accepted_at"]


def test_invites_audit_list_is_scoped_to_caller():
    _e_a, tok_a = _register("audit-a")
    _e_b, tok_b = _register("audit-b")
    # A dispatches an invite.
    requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-005"},
        headers=_headers(tok_a), timeout=30,
    )
    # B lists their invites — must not see A's row.
    r_b = requests.get(INVITES_LIST_URL, headers=_headers(tok_b), timeout=30)
    assert r_b.status_code == 200
    assert r_b.json()["invites"] == []
    # A lists their invites — sees exactly one.
    r_a = requests.get(INVITES_LIST_URL, headers=_headers(tok_a), timeout=30)
    assert r_a.status_code == 200
    assert len(r_a.json()["invites"]) == 1


# ---------------------------------------------------------------------
# Reminder-note templates
# ---------------------------------------------------------------------

def test_templates_require_auth():
    r = requests.get(TEMPLATES_URL, timeout=30)
    assert r.status_code == 401
    r2 = requests.post(TEMPLATES_URL, json={"label": "x", "body": "y"}, timeout=30)
    assert r2.status_code == 401


def test_template_create_and_list_round_trip():
    _e, tok = _register("tpl1")
    # Empty list to start.
    r0 = requests.get(TEMPLATES_URL, headers=_headers(tok), timeout=30)
    assert r0.status_code == 200 and r0.json()["templates"] == []
    # Create two templates.
    r1 = requests.post(
        TEMPLATES_URL,
        json={"label": "Zebra intake", "body": "See you Thursday!"},
        headers=_headers(tok), timeout=30,
    )
    assert r1.status_code == 200
    assert r1.json()["label"] == "Zebra intake"
    r2 = requests.post(
        TEMPLATES_URL,
        json={"label": "Alpha follow-up", "body": "Gentle nudge — no rush."},
        headers=_headers(tok), timeout=30,
    )
    assert r2.status_code == 200
    # Alphabetical order.
    r_list = requests.get(TEMPLATES_URL, headers=_headers(tok), timeout=30).json()
    labels = [t["label"] for t in r_list["templates"]]
    assert labels == ["Alpha follow-up", "Zebra intake"]


def test_template_rejects_duplicate_label():
    _e, tok = _register("tpl2")
    body = {"label": "Dup", "body": "one"}
    r1 = requests.post(TEMPLATES_URL, json=body, headers=_headers(tok), timeout=30)
    assert r1.status_code == 200
    r2 = requests.post(TEMPLATES_URL, json=body, headers=_headers(tok), timeout=30)
    assert r2.status_code == 409


def test_template_rejects_240_char_body():
    _e, tok = _register("tpl3")
    r = requests.post(
        TEMPLATES_URL,
        json={"label": "Too long", "body": "x" * 241},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 422


def test_template_delete_is_owner_scoped():
    _e_a, tok_a = _register("tpldel-a")
    _e_b, tok_b = _register("tpldel-b")
    # A creates a template.
    r = requests.post(
        TEMPLATES_URL,
        json={"label": "A's template", "body": "A body"},
        headers=_headers(tok_a), timeout=30,
    )
    assert r.status_code == 200
    tid = r.json()["template_id"]
    # B tries to delete → 404.
    r_del_b = requests.delete(
        f"{TEMPLATES_URL}/{tid}", headers=_headers(tok_b), timeout=30,
    )
    assert r_del_b.status_code == 404
    # A deletes → 200 and the row is gone.
    r_del_a = requests.delete(
        f"{TEMPLATES_URL}/{tid}", headers=_headers(tok_a), timeout=30,
    )
    assert r_del_a.status_code == 200
    r_after = requests.get(TEMPLATES_URL, headers=_headers(tok_a), timeout=30)
    assert not any(t["template_id"] == tid for t in r_after.json()["templates"])


def test_template_hard_cap_at_12_per_user():
    _e, tok = _register("tplcap")
    for i in range(12):
        r = requests.post(
            TEMPLATES_URL,
            json={"label": f"tpl-{i:02d}", "body": f"body {i}"},
            headers=_headers(tok), timeout=30,
        )
        assert r.status_code == 200, r.text
    # 13th → 409.
    r_over = requests.post(
        TEMPLATES_URL,
        json={"label": "tpl-13", "body": "too many"},
        headers=_headers(tok), timeout=30,
    )
    assert r_over.status_code == 409
