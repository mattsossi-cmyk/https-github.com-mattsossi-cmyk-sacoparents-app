"""iter225 — Coparent Snapshot 'fridge_pair' variant tests."""
from __future__ import annotations

import io
import os
import re

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL must be set")

SNAPSHOT_URL = f"{BASE_URL}/api/portal/guided-snapshot-pdf"

TOPICS = [
    "foundation",
    "coparenting",
    "safety",
    "medical",
    "educational",
    "psychological",
]

SAMPLE_ANSWERS = [
    {"question": "Q1?", "answer": "We prioritize the kids first."},
    {"question": "Q2?", "answer": "We stick to written agreements."},
    {"question": "Q3?", "answer": "24-hour advance notice on schedule."},
    {"question": "Q4?", "answer": "Neutral handoff location."},
    {"question": "Q5?", "answer": "No conflict in front of the kids."},
]


def _post(payload):
    return requests.post(SNAPSHOT_URL, json=payload, timeout=30)


def _filename_from_headers(resp):
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r"filename=([^;]+)", cd)
    return m.group(1).strip().strip('"') if m else ""


# --- Filename & 200 checks for every topic (fridge_pair) --- #
@pytest.mark.parametrize("topic", TOPICS)
def test_fridge_pair_filename_per_topic(topic):
    resp = _post({"topic": topic, "answers": SAMPLE_ANSWERS, "variant": "fridge_pair"})
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"
    assert _filename_from_headers(resp) == f"coparent-snapshot-{topic}-fridge-pair.pdf"


# --- pair is larger than solo for same payload --- #
def test_fridge_pair_bigger_than_solo():
    payload_pair = {"topic": "foundation", "answers": SAMPLE_ANSWERS, "variant": "fridge_pair"}
    payload_solo = {"topic": "foundation", "answers": SAMPLE_ANSWERS, "variant": "fridge"}
    r_pair = _post(payload_pair)
    r_solo = _post(payload_solo)
    assert r_pair.status_code == 200 and r_solo.status_code == 200
    assert len(r_pair.content) > len(r_solo.content), (
        f"pair={len(r_pair.content)} solo={len(r_solo.content)}"
    )


# --- solo variant filename regression (iter223) --- #
def test_fridge_solo_filename_unchanged():
    resp = _post({"topic": "foundation", "answers": SAMPLE_ANSWERS, "variant": "fridge"})
    assert resp.status_code == 200
    assert _filename_from_headers(resp) == "coparent-snapshot-foundation-fridge.pdf"


# --- default variant unchanged --- #
def test_default_variant_filename_unchanged():
    resp = _post({"topic": "foundation", "answers": SAMPLE_ANSWERS})
    assert resp.status_code == 200
    assert _filename_from_headers(resp) == "coparent-snapshot-foundation.pdf"


# --- pattern rejects bogus & case sensitivity --- #
@pytest.mark.parametrize("bogus", ["bogus", "FRIDGE_PAIR", "Fridge", "fridge-pair"])
def test_variant_pattern_mismatch(bogus):
    resp = _post({"topic": "foundation", "answers": SAMPLE_ANSWERS, "variant": bogus})
    assert resp.status_code == 422
    body = resp.json()
    txt = str(body)
    assert "^(standard|fridge|fridge_pair)$" in txt or "pattern" in txt.lower()


# --- PDF layout: A5-landscape 210x148 mm --- #
def test_fridge_pair_pdf_dimensions_and_double_headline():
    pypdf = pytest.importorskip("pypdf")
    resp = _post({"topic": "foundation", "answers": SAMPLE_ANSWERS, "variant": "fridge_pair"})
    assert resp.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    assert len(reader.pages) >= 1
    page = reader.pages[0]
    # fpdf2 uses points internally. mediabox is in pt (1pt = 1/72 in).
    w_pt = float(page.mediabox.width)
    h_pt = float(page.mediabox.height)
    w_mm = w_pt * 25.4 / 72
    h_mm = h_pt * 25.4 / 72
    # A5-landscape: 210 x 148 mm  (allow +/- 1mm)
    assert abs(w_mm - 210) < 1.5, f"width {w_mm}mm not ~210mm"
    assert abs(h_mm - 148) < 1.5, f"height {h_mm}mm not ~148mm"
    # Both cards' headline should appear
    text = page.extract_text() or ""
    headline = "Our Foundation"
    assert text.count(headline) >= 2, f"headline not doubled: {text!r}"


# --- Solo variant dimensions still ~A6 portrait --- #
def test_fridge_solo_pdf_dimensions():
    pypdf = pytest.importorskip("pypdf")
    resp = _post({"topic": "foundation", "answers": SAMPLE_ANSWERS, "variant": "fridge"})
    assert resp.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    page = reader.pages[0]
    w_mm = float(page.mediabox.width) * 25.4 / 72
    h_mm = float(page.mediabox.height) * 25.4 / 72
    assert abs(w_mm - 105) < 1.5, f"width {w_mm}mm not ~105mm"
    assert abs(h_mm - 148) < 1.5, f"height {h_mm}mm not ~148mm"


# --- Empty answers on pair returns 200 with fallback on both cards --- #
def test_fridge_pair_empty_answers_returns_200():
    resp = _post({"topic": "foundation", "answers": [], "variant": "fridge_pair"})
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_fridge_solo_empty_answers_returns_200():
    resp = _post({"topic": "foundation", "answers": [], "variant": "fridge"})
    assert resp.status_code == 200


# --- safety_flagged=true on pair prints the meta on BOTH cards --- #
def test_fridge_pair_safety_flagged_meta_on_both_cards():
    pypdf = pytest.importorskip("pypdf")
    resp = _post({
        "topic": "safety",
        "answers": SAMPLE_ANSWERS,
        "variant": "fridge_pair",
        "safety_flagged": True,
    })
    assert resp.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    text = reader.pages[0].extract_text() or ""
    assert text.count("Grey-rock voice") >= 2, f"got: {text!r}"


# --- Regression: /api/portal/state guided_drafts round trip needs auth,
#     so we do a soft check: unauthenticated GET returns 401/403 (works). --- #
def test_portal_state_requires_auth():
    resp = requests.get(f"{BASE_URL}/api/portal/state", timeout=15)
    assert resp.status_code in (401, 403)


# --- Regression: /api/portal/voice-transcribe still exists (no file -> 422) --- #
def test_voice_transcribe_endpoint_alive():
    resp = requests.post(f"{BASE_URL}/api/portal/voice-transcribe", timeout=15)
    # Missing 'audio' field -> FastAPI validation error 422
    assert resp.status_code in (400, 422)
