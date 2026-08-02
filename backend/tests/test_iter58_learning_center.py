"""Iteration 58 tests — Learning Center (hubs, articles, read tracking).

We skip the AI expansion endpoint here (would consume LLM credits every
CI run) — it's smoke-tested via curl instead. Everything else is covered:

* GET  /api/learning/hubs                              → 3 hubs · 15 articles
* GET  /api/learning/hub/.../article/...               → full body + read state
* POST /api/learning/hub/.../article/.../read          → marks read + returns
                                                         progress
* DELETE /api/learning/hub/.../article/.../read        → undo
* GET  /api/learning/progress                          → per-hub summary
* 404 for unknown hub / article
* GET  /api/learning/search?q=...                       → keyword match
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from motor.motor_asyncio import AsyncIOMotorClient

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1,
    _client, _ensure_account, _run,
    MONGO_URL, DB_NAME,
)


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


def _reset_reads():
    async def _r():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["learning_reads"].delete_many({})
            # We keep learning_ai_expansions across tests to avoid burning
            # LLM credit on the smoke curl already run in dev.
        finally:
            c.close()
    _run(_r())


@pytest.fixture(autouse=True)
def _cleanup():
    _reset_reads()
    yield
    _reset_reads()


class TestHubsIndex:
    def test_lists_all_three_hubs(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/learning/hubs", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_articles"] == 15
        slugs = {h["slug"] for h in body["hubs"]}
        assert slugs == {"communication", "boundaries", "mediation"}
        for h in body["hubs"]:
            assert h["article_count"] == 5
            assert len(h["articles"]) == 5
            assert h["progress"]["read"] == 0
            assert h["progress"]["total"] == 5

    def test_progress_reflects_reads(self, p1_client):
        p1_client.post(
            f"{BASE_URL}/api/learning/hub/communication/article/the-two-inbox-rule/read",
            timeout=15,
        )
        body = p1_client.get(f"{BASE_URL}/api/learning/hubs", timeout=15).json()
        comm_hub = next(h for h in body["hubs"] if h["slug"] == "communication")
        assert comm_hub["progress"]["read"] == 1
        # Article stub carries the per-user read flag.
        stub = next(a for a in comm_hub["articles"] if a["slug"] == "the-two-inbox-rule")
        assert stub["read"] is True


class TestArticleFetch:
    def test_returns_full_body_and_takeaways(self, p1_client):
        r = p1_client.get(
            f"{BASE_URL}/api/learning/hub/communication/article/the-two-inbox-rule",
            timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        art = body["article"]
        assert art["slug"] == "the-two-inbox-rule"
        assert art["hub_slug"] == "communication"
        assert len(art["takeaways"]) == 3
        assert len(art["body"]) > 300
        assert body["read"] is False

    def test_404_on_unknown(self, p1_client):
        r = p1_client.get(
            f"{BASE_URL}/api/learning/hub/communication/article/no-such-thing",
            timeout=15,
        )
        assert r.status_code == 404
        r2 = p1_client.get(
            f"{BASE_URL}/api/learning/hub/bogus/article/anything", timeout=15,
        )
        assert r2.status_code == 404


class TestReadTracking:
    def test_mark_and_unmark_round_trip(self, p1_client):
        slug = "the-two-inbox-rule"
        url = f"{BASE_URL}/api/learning/hub/communication/article/{slug}/read"

        r = p1_client.post(url, timeout=15)
        assert r.status_code == 200
        assert r.json()["read"] is True
        assert r.json()["hub_progress"]["read"] == 1

        # Idempotent — second POST doesn't double-count.
        r2 = p1_client.post(url, timeout=15)
        assert r2.json()["hub_progress"]["read"] == 1

        # Article endpoint reflects the state.
        art = p1_client.get(
            f"{BASE_URL}/api/learning/hub/communication/article/{slug}",
            timeout=15,
        ).json()
        assert art["read"] is True
        assert art["read_at"] is not None

        r3 = p1_client.delete(url, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["read"] is False
        assert r3.json()["hub_progress"]["read"] == 0

    def test_progress_endpoint_aggregates_across_hubs(self, p1_client):
        # Read one from each hub.
        p1_client.post(
            f"{BASE_URL}/api/learning/hub/communication/article/the-two-inbox-rule/read",
            timeout=15,
        )
        p1_client.post(
            f"{BASE_URL}/api/learning/hub/boundaries/article/boundaries-are-doors-not-walls/read",
            timeout=15,
        )
        p1_client.post(
            f"{BASE_URL}/api/learning/hub/mediation/article/what-mediators-actually-do/read",
            timeout=15,
        )
        prog = p1_client.get(f"{BASE_URL}/api/learning/progress", timeout=15).json()
        assert prog["read_count"] == 3
        assert prog["total_articles"] == 15
        assert prog["started"] is True
        for hub in prog["per_hub"]:
            assert hub["read"] == 1
            assert hub["total"] == 5


class TestSearch:
    def test_search_matches_title_or_body(self, p1_client):
        r = p1_client.get(
            f"{BASE_URL}/api/learning/search?q=inbox", timeout=15,
        ).json()
        slugs = {row["slug"] for row in r["results"]}
        assert "the-two-inbox-rule" in slugs

    def test_search_empty_returns_empty(self, p1_client):
        r = p1_client.get(
            f"{BASE_URL}/api/learning/search?q=", timeout=15,
        ).json()
        assert r["results"] == []
