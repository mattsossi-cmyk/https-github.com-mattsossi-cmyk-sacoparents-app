"""Iter 98 — Pathway Report Reviewer Comments (closed-loop feedback).

Covers the public POST/GET endpoints on the verify router + the
parent-facing feed on the pathway-report router:

    * POST /verify/pathway/{sig_id}/comments      — public, no auth
    * GET  /verify/pathway/{sig_id}/comments      — public, no auth
    * GET  /pathway-report/comments/mine          — authed, parent only

Key invariants pinned by this suite:
    * Unknown sig_id → 404 on POST (clean signal, not silent success).
    * Validation: name required, comment text required with min-length.
    * Public GET never leaks the internal `ip_hash` or `parent_user_id`.
    * Parent-side feed only returns comments left on sig_ids issued to
      that user (audit-safe isolation).
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pathway_verify_routes import (  # noqa: E402
    list_comments_for_user, record_pathway_signature,
)


BACKEND = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND:
    try:
        with open("/app/frontend/.env") as fh:
            for ln in fh:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND = ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BACKEND = None
API = f"{BACKEND}/api" if BACKEND else None

PARENT_EMAIL = "parent1@test.com"
PARENT_PASSWORD = "TestPass123!"  # noqa: S105  test fixture


def _mongo_client_and_db():
    with open("/app/backend/.env") as fh:
        env = {}
        for ln in fh:
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    client = AsyncIOMotorClient(env["MONGO_URL"])
    return client, client[env.get("DB_NAME", "test_database")]


# ---------- Unit-level: list_comments_for_user isolation ----------

def test_list_comments_for_user_only_returns_own_rows():
    """Parents A and B each issue a signature. A comment is left on
    each. The parent-side fetch for A must only return A's comment."""
    async def scenario():
        client, db = _mongo_client_and_db()
        uid_a = f"tst_iter98_a_{uuid.uuid4().hex[:6]}"
        uid_b = f"tst_iter98_b_{uuid.uuid4().hex[:6]}"
        try:
            sig_a = await record_pathway_signature(
                db, user_id=uid_a, is_dual_party=False, share_id=None,
            )
            sig_b = await record_pathway_signature(
                db, user_id=uid_b, is_dual_party=False, share_id=None,
            )
            # Simulate a comment on each signature.
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.pathway_report_comments.insert_many([
                {
                    "comment_id":     uuid.uuid4().hex[:16],
                    "sig_id":         sig_a["sig_id"],
                    "parent_user_id": uid_a,
                    "reviewer_name":  "Reviewer A",
                    "reviewer_role":  "mediator",
                    "comment_text":   "For parent A.",
                    "ip_hash":        "hash-a",
                    "created_at":     now_iso,
                },
                {
                    "comment_id":     uuid.uuid4().hex[:16],
                    "sig_id":         sig_b["sig_id"],
                    "parent_user_id": uid_b,
                    "reviewer_name":  "Reviewer B",
                    "reviewer_role":  "attorney",
                    "comment_text":   "For parent B.",
                    "ip_hash":        "hash-b",
                    "created_at":     now_iso,
                },
            ])

            rows_a = await list_comments_for_user(db, uid_a)
            rows_b = await list_comments_for_user(db, uid_b)
            assert len(rows_a) == 1
            assert rows_a[0]["reviewer_name"] == "Reviewer A"
            assert len(rows_b) == 1
            assert rows_b[0]["reviewer_name"] == "Reviewer B"
            # Isolation: A never sees B's row and vice versa.
            assert rows_a[0]["comment_id"] != rows_b[0]["comment_id"]
            # Privacy: the projection never returns ip_hash / parent_user_id.
            for row in rows_a + rows_b:
                assert "ip_hash" not in row
                assert "parent_user_id" not in row
        finally:
            # Cleanup so the suite is idempotent.
            await db.pathway_report_comments.delete_many(
                {"parent_user_id": {"$in": [uid_a, uid_b]}},
            )
            await db.pathway_signatures.delete_many(
                {"user_id": {"$in": [uid_a, uid_b]}},
            )
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())


# ---------- Live endpoint ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_public_post_comment_on_unknown_sig_id_is_404():
    r = requests.post(
        f"{API}/verify/pathway/deadbeef00000000/comments",
        json={
            "reviewer_name": "Jamie",
            "reviewer_role": "mediator",
            "comment_text":  "won't land",
        },
        timeout=10,
    )
    assert r.status_code == 404


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_public_post_comment_validates_body():
    # Missing name → 422 from pydantic.
    r = requests.post(
        f"{API}/verify/pathway/deadbeef00000000/comments",
        json={"reviewer_role": "mediator", "comment_text": "abcd"},
        timeout=10,
    )
    assert r.status_code in (400, 422)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_public_get_list_unknown_sig_id_returns_empty_list():
    r = requests.get(
        f"{API}/verify/pathway/deadbeef00000000/comments", timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("issued") is False
    assert body.get("comments") == []


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_authed_mine_requires_auth():
    r = requests.get(f"{API}/pathway-report/comments/mine", timeout=10)
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_full_loop_parent_sees_public_comment():
    """Parent logs in, generates a preview PDF (creates a signature),
    the public POST endpoint accepts a reviewer comment on that
    sig_id, and the parent-authed feed returns it."""
    login = requests.post(
        f"{API}/auth/login",
        json={"email": PARENT_EMAIL, "password": PARENT_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip("parent1 login unavailable")
    tok = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}

    # 1. Generate a fresh signature via the preview PDF.
    r = requests.get(
        f"{API}/pathway-report/preview/pdf", headers=headers, timeout=30,
    )
    assert r.status_code == 200 and r.content.startswith(b"%PDF-")

    # 2. Look up parent1's newest sig_id (auth/me).
    me = requests.get(f"{API}/auth/me", headers=headers, timeout=10).json()
    uid = me.get("user_id") or me.get("id")
    assert uid

    async def _newest_sig():
        client, db = _mongo_client_and_db()
        try:
            row = await db.pathway_signatures.find_one(
                {"user_id": uid}, sort=[("generated_at", -1)],
            )
            return row["sig_id"] if row else None
        finally:
            client.close()

    sig_id = asyncio.get_event_loop().run_until_complete(_newest_sig())
    assert sig_id

    # 3. Public POST a comment.
    unique_marker = uuid.uuid4().hex[:8]
    post = requests.post(
        f"{API}/verify/pathway/{sig_id}/comments",
        json={
            "reviewer_name": f"Iter98 Reviewer {unique_marker}",
            "reviewer_role": "mediator",
            "reviewer_org":  "Southside Mediation Group",
            "comment_text":  f"Automated iter98 comment {unique_marker}",
        },
        timeout=15,
    )
    assert post.status_code == 200, post.text
    body = post.json()
    assert body["ok"] is True
    assert body["comment"]["reviewer_name"].endswith(unique_marker)
    # Privacy: response never leaks ip_hash.
    assert "ip_hash" not in body["comment"]

    # 4. Public GET returns the same row.
    lst = requests.get(f"{API}/verify/pathway/{sig_id}/comments", timeout=10)
    assert lst.status_code == 200
    lst_body = lst.json()
    assert lst_body.get("issued") is True
    assert any(
        c["reviewer_name"].endswith(unique_marker) for c in lst_body["comments"]
    )
    # Privacy again — public list never exposes ip_hash.
    for c in lst_body["comments"]:
        assert "ip_hash" not in c

    # 5. Parent-side authed fetch returns the same row.
    mine = requests.get(
        f"{API}/pathway-report/comments/mine", headers=headers, timeout=10,
    )
    assert mine.status_code == 200
    mine_body = mine.json()
    assert mine_body["total"] >= 1
    assert any(
        c["reviewer_name"].endswith(unique_marker) for c in mine_body["comments"]
    )
