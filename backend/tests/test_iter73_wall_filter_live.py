"""Iteration 73 — Live API tests for wall feed category filter.

Tests against the running backend via REACT_APP_BACKEND_URL.
Verifies:
- GET /api/wall/feed?category=milestones returns 200 with proper shape
- category_counts includes {all, milestones, streaks, foundations, alignment}
- unknown/blank category values fall back to 'all'
- events (if any) in ?category=streaks are only streak badges
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
CREDS = {"email": "parent1@test.com", "password": "TestPass123!"}
STREAK_BADGES = {"week_streak_7", "month_streak_30", "hundred_day_streak"}
MILESTONE_BADGES = STREAK_BADGES | {"foundation_ready", "first_compare", "communication_master", "high_alignment_90"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=CREDS, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_feed_default_no_category(headers):
    r = requests.get(f"{BASE_URL}/api/wall/feed", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("category") == "all"
    cc = data.get("category_counts") or {}
    for key in ("all", "milestones", "streaks", "foundations", "alignment"):
        assert key in cc, f"missing category count key: {key}"


def test_feed_category_milestones(headers):
    r = requests.get(f"{BASE_URL}/api/wall/feed", params={"category": "milestones"}, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("category") == "milestones"
    for ev in data.get("events", []):
        assert ev["badge_type"] in MILESTONE_BADGES, f"unexpected badge: {ev['badge_type']}"


def test_feed_category_streaks_only(headers):
    r = requests.get(f"{BASE_URL}/api/wall/feed", params={"category": "streaks"}, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("category") == "streaks"
    for ev in data.get("events", []):
        assert ev["badge_type"] in STREAK_BADGES


def test_feed_category_bogus_falls_back(headers):
    r = requests.get(f"{BASE_URL}/api/wall/feed", params={"category": "bogus"}, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("category") == "all"


def test_feed_category_blank_falls_back(headers):
    r = requests.get(f"{BASE_URL}/api/wall/feed", params={"category": ""}, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("category") == "all"


def test_category_counts_are_ints_and_all_gte_subs(headers):
    r = requests.get(f"{BASE_URL}/api/wall/feed", headers=headers, timeout=15)
    assert r.status_code == 200
    cc = r.json().get("category_counts") or {}
    for k, v in cc.items():
        assert isinstance(v, int), f"{k} count not int"
    # all >= milestones since milestones is subset
    assert cc["all"] >= cc["milestones"]
    # milestones >= each sub-group
    for sub in ("streaks", "foundations", "alignment"):
        assert cc["milestones"] >= cc[sub], f"milestones ({cc['milestones']}) < {sub} ({cc[sub]})"


def test_feed_requires_auth():
    r = requests.get(f"{BASE_URL}/api/wall/feed", timeout=15)
    assert r.status_code in (401, 403)
