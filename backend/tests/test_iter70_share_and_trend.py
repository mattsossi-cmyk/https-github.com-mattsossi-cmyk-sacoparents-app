"""Backend tests for iter70: /api/portal/share* + Weekly Progress Trend section."""
import os
import re
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"


# ---- Share: foundation ----
class TestShareFoundation:
    def test_create_share_and_fetch(self):
        r = requests.post(
            f"{API}/portal/share",
            json={
                "artefact_type": "foundation",
                "payload": {"foundation_text": "Our child comes first."},
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "share_id" in d and "url" in d and "expires_at" in d
        # URL should be built from request host (preview URL)
        assert d["url"].endswith(f"/api/portal/share/{d['share_id']}.pdf")
        assert d["url"].startswith("http")
        # expires ~30 days out
        exp = datetime.fromisoformat(d["expires_at"])
        delta = exp - datetime.now(timezone.utc)
        assert 29 <= delta.days <= 30

        # Fetch PDF
        r2 = requests.get(d["url"], timeout=30)
        assert r2.status_code == 200, r2.text
        assert r2.headers["content-type"].startswith("application/pdf")
        assert r2.content[:4] == b"%PDF"
        cd = r2.headers.get("content-disposition", "")
        assert "inline" in cd.lower()
        assert "sacoparents-foundation-statement.pdf" in cd

        # hit_count increments — fetch again & confirm no error
        r3 = requests.get(d["url"], timeout=30)
        assert r3.status_code == 200

    def test_share_404_unknown(self):
        r = requests.get(f"{API}/portal/share/NONEXISTENT.pdf", timeout=30)
        assert r.status_code == 404

    def test_share_404_invalid_chars(self):
        r = requests.get(f"{API}/portal/share/bad$id.pdf", timeout=30)
        assert r.status_code == 404

    def test_share_expired_returns_410(self):
        """Create a share, expire it directly in Mongo, then fetch."""
        r = requests.post(
            f"{API}/portal/share",
            json={"artefact_type": "foundation", "payload": {"foundation_text": "X."}},
            timeout=30,
        )
        assert r.status_code == 200
        share_id = r.json()["share_id"]

        # Manipulate Mongo
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _expire():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            res = await db["portal_pdf_shares"].update_one(
                {"share_id": share_id}, {"$set": {"expires_at": past}}
            )
            client.close()
            return res.modified_count

        modified = asyncio.run(_expire())
        assert modified == 1

        r2 = requests.get(f"{API}/portal/share/{share_id}.pdf", timeout=30)
        assert r2.status_code == 410, r2.text

    def test_invalid_artefact_type(self):
        r = requests.post(
            f"{API}/portal/share",
            json={"artefact_type": "bogus", "payload": {}},
            timeout=30,
        )
        # Pydantic pattern rejects → 422
        assert r.status_code in (400, 422), r.text

    def test_empty_foundation_payload_rejected(self):
        r = requests.post(
            f"{API}/portal/share",
            json={"artefact_type": "foundation", "payload": {"foundation_text": ""}},
            timeout=30,
        )
        assert r.status_code == 400, r.text


# ---- Share: legal ----
class TestShareLegal:
    def test_legal_share_roundtrip(self):
        r = requests.post(
            f"{API}/portal/share",
            json={
                "artefact_type": "legal",
                "payload": {
                    "health_index": {"s1": 7, "s2": 6, "s3": 5},
                    "signatures": {"sigA": "Alice", "sigB": "Bob", "sigMed": "Matt Sossi"},
                    "foundation_text": "Anchor.",
                },
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        r2 = requests.get(d["url"], timeout=30)
        assert r2.status_code == 200
        assert r2.content[:4] == b"%PDF"
        cd = r2.headers.get("content-disposition", "")
        assert "sacoparents-legal-report.pdf" in cd


# ---- Share: weekly ----
class TestShareWeekly:
    def test_weekly_share_with_trend(self):
        r = requests.post(
            f"{API}/portal/share",
            json={
                "artefact_type": "weekly",
                "payload": {
                    "health_index": {"s1": 7, "s2": 6, "s3": 5},
                    "reassessments": [
                        {"avg": 5, "date": "2026-01-01"},
                        {"avg": 6, "date": "2026-01-15"},
                        {"avg": 7, "date": "2026-02-01"},
                    ],
                },
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        r2 = requests.get(d["url"], timeout=30)
        assert r2.status_code == 200
        assert r2.content[:4] == b"%PDF"
        cd = r2.headers.get("content-disposition", "")
        assert "sacoparents-weekly-progress.pdf" in cd


# ---- Weekly PDF direct: Trend section ----
class TestWeeklyTrendPdf:
    def test_trend_section_present(self):
        payload = {
            "health_index": {"s1": 7, "s2": 6, "s3": 5},
            "reassessments": [
                {"avg": 5, "date": "2026-01-01"},
                {"avg": 6, "date": "2026-01-15"},
                {"avg": 7, "date": "2026-02-01"},
            ],
        }
        r = requests.post(f"{API}/portal/weekly-progress-pdf", json=payload, timeout=60)
        assert r.status_code == 200, r.text
        assert r.content[:4] == b"%PDF"
        # With trend section, PDF should be larger than baseline
        assert len(r.content) > 2000

    def test_no_reassessments_still_ok(self):
        r = requests.post(
            f"{API}/portal/weekly-progress-pdf",
            json={"health_index": {"s1": 5, "s2": 5, "s3": 5}},
            timeout=60,
        )
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
