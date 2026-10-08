"""Backend tests for the Self-Assessment AI endpoints.

Covers /api/self-assessment/ai/tip and /api/self-assessment/ai/framing:
- validation (incomplete / unknown section / overall gate / short text)
- at least one live Claude call per endpoint
"""
import os
from pathlib import Path

import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not configured"
API = f"{BASE_URL}/api/self-assessment/ai"

SECTIONS = ["child_focus", "self_awareness", "communication", "differences"]


def _full_answers(section: str, value: int = 4) -> dict:
    return {f"{section}_{i}": value for i in range(1, 6)}


def _all_twenty(value: int = 4) -> dict:
    out = {}
    for sec in SECTIONS:
        out.update(_full_answers(sec, value))
    return out


# ---------- /ai/tip ----------
class TestAiTip:
    def test_incomplete_section_returns_400(self):
        r = requests.post(
            f"{API}/tip",
            json={"section": "child_focus", "answers": {"child_focus_1": 3}},
        )
        assert r.status_code == 400, r.text
        assert "finish" in r.json()["detail"].lower()

    def test_unknown_section_returns_400(self):
        r = requests.post(
            f"{API}/tip",
            json={"section": "not_a_section", "answers": {}},
        )
        assert r.status_code == 400, r.text
        assert "unknown" in r.json()["detail"].lower()

    def test_overall_requires_all_twenty(self):
        # Only one section filled -> others missing -> 400
        r = requests.post(
            f"{API}/tip",
            json={"section": "overall", "answers": _full_answers("child_focus")},
        )
        assert r.status_code == 400, r.text

    def test_tip_bad_payload_422(self):
        r = requests.post(f"{API}/tip", json={"answers": {}})
        assert r.status_code == 422

    def test_live_tip_returns_text(self):
        """Live Claude call: complete child_focus section -> non-empty tip."""
        r = requests.post(
            f"{API}/tip",
            json={"section": "child_focus", "answers": _full_answers("child_focus", 4)},
            timeout=45,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tip" in data
        assert isinstance(data["tip"], str)
        assert len(data["tip"].strip()) >= 20, f"tip too short: {data['tip']!r}"
        # no quotes per prompt
        assert '"' not in data["tip"]


# ---------- /ai/framing ----------
class TestAiFraming:
    def test_short_text_returns_422(self):
        r = requests.post(f"{API}/framing", json={"text": "hi"})
        assert r.status_code == 422

    def test_missing_text_returns_422(self):
        r = requests.post(f"{API}/framing", json={})
        assert r.status_code == 422

    def test_live_framing_returns_advice(self):
        """Live Claude call: real situation -> advice + suggested fields present."""
        r = requests.post(
            f"{API}/framing",
            json={
                "text": (
                    "My co-parent keeps changing pickup times at the last minute. "
                    "I want to ask them to confirm by Thursday without starting a fight."
                )
            },
            timeout=45,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(data.keys()) >= {"advice", "suggested"}
        assert isinstance(data["advice"], str)
        assert isinstance(data["suggested"], str)
        assert len(data["advice"].strip()) >= 10, f"advice empty: {data!r}"

    def test_live_framing_grey_rock_hint(self):
        """safety_flagged=true should still return a valid shape (grey-rock voice)."""
        r = requests.post(
            f"{API}/framing",
            json={
                "text": "The other parent sent a long angry message. I need to reply only about Saturday's drop-off time at 5pm.",
                "safety_flagged": True,
            },
            timeout=45,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "advice" in data and "suggested" in data
        assert len(data["advice"].strip()) >= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
