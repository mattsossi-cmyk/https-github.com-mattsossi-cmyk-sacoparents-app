"""Tests for public sample report endpoints (no auth)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://align-report.preview.emergentagent.com").rstrip("/")

KEYS = ["co_parenting", "communication", "education", "medical", "psychological", "safety", "mediation"]


def test_samples_list() -> None:
    r = requests.get(f"{BASE_URL}/api/joint/samples", timeout=30)
    assert r.status_code == 200
    data = r.json()
    # allow either list or {samples: [...]}
    items = data if isinstance(data, list) else data.get("samples") or data.get("items")
    assert items is not None, f"Unexpected shape: {data}"
    keys = {i["key"] for i in items}
    assert keys == set(KEYS), f"Missing keys: expected {set(KEYS)} got {keys}"
    safety = next(i for i in items if i["key"] == "safety")
    assert safety.get("is_safety")


def test_sample_bogus_404() -> None:
    r = requests.get(f"{BASE_URL}/api/joint/sample/bogus", timeout=30)
    assert r.status_code == 404


@pytest.mark.parametrize("key", KEYS)
def test_sample_report_json(key):
    r = requests.get(f"{BASE_URL}/api/joint/sample/{key}", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("report_title")
    assert data.get("subject_label")
    assert data.get("child_name")
    assert isinstance(data.get("alignment_statements"), list)
    if key == "safety":
        assert data.get("is_safety")
        assert data.get("confidentiality_note")
        assert data.get("parent_a_name") == "Parent A"
        assert data.get("parent_b_name") == "Parent B"
        assert data.get("child_name") == "the child"


@pytest.mark.parametrize("key", KEYS)
def test_sample_pdf(key):
    r = requests.get(f"{BASE_URL}/api/joint/sample/{key}/pdf", timeout=60)
    assert r.status_code == 200, r.text[:200]
    ct = r.headers.get("content-type", "")
    assert "application/pdf" in ct, f"Bad content-type: {ct}"
    assert len(r.content) > 1000, f"PDF too small: {len(r.content)}"
    assert r.content[:4] == b"%PDF", "Not a valid PDF header"
