"""Iteration 183 — Public Joint Alignment Sample PDF.

Covers `/api/insights/samples/joint-alignment-preview.pdf`:
  * Returns 200 without auth (this is a marketing artefact).
  * Content-Type is application/pdf.
  * Payload starts with the PDF magic bytes.
  * The PDF builder module can construct bytes hermetically.
  * The sample script keeps all four Align verbs so the frontend copy
    and the PDF do not drift.
"""
from __future__ import annotations

import sys

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


def test_sample_pdf_is_public_and_valid():
    r = requests.get(
        f"{BASE_URL}/api/insights/samples/joint-alignment-preview.pdf",
        timeout=20,
    )
    assert r.status_code == 200, r.text[:400]
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF", "response is not a real PDF"
    # Marketing pages produce compact PDFs; guard against a 100-byte
    # empty payload so we don't ship a broken artefact.
    assert len(r.content) > 1500, f"pdf too small: {len(r.content)}"


def test_sample_pdf_response_has_download_filename():
    r = requests.get(
        f"{BASE_URL}/api/insights/samples/joint-alignment-preview.pdf",
        timeout=20,
    )
    assert r.status_code == 200
    disposition = r.headers.get("content-disposition", "")
    # Marketing PDF: opens inline, with a scenario-suffixed filename
    # so the browser Save dialog matches the "email to co-parent" copy.
    assert "sacoparents-joint-alignment-sample-low-conflict.pdf" in disposition

    r_high = requests.get(
        f"{BASE_URL}/api/insights/samples/joint-alignment-preview.pdf"
        f"?scenario=high-conflict",
        timeout=20,
    )
    assert r_high.status_code == 200
    disposition_high = r_high.headers.get("content-disposition", "")
    assert "sacoparents-joint-alignment-sample-high-conflict.pdf" in disposition_high


def test_sample_pdf_can_be_built_hermetically():
    """Build the PDF straight from the module — bypasses the ingress
    entirely so a failing route (proxy, TLS, etc.) can't mask a bug
    in the PDF builder itself."""
    from joint_alignment_sample_pdf import build_joint_alignment_sample_pdf
    data = build_joint_alignment_sample_pdf()
    assert isinstance(data, (bytes, bytearray))
    assert data[:4] == b"%PDF"
    assert len(data) > 1500


def test_sample_pdf_topics_stay_in_lockstep_with_frontend_copy():
    """The PDF must render the same six topic titles that the React
    sample page renders on the LOW-CONFLICT default. If the frontend
    copy changes, this test fails until the backend module is updated
    in the same commit."""
    from joint_alignment_sample_pdf import SAMPLE_TOPICS
    titles = [t["title"] for t in SAMPLE_TOPICS]
    assert "School morning routines" in titles
    assert "Screen time on weeknights" in titles
    assert "Extracurricular activities" in titles
    assert "Handover timing on Fridays" in titles
    assert "Winter holidays" in titles
    assert "Healthcare decisions" in titles
    # Status coverage — one agree, one differ, one incomplete at minimum.
    statuses = {t["status"] for t in SAMPLE_TOPICS}
    assert {"agree", "differ", "incomplete"}.issubset(statuses)
    # Notes must be Latin-1 safe. The FPDF renderer accepts em-dashes
    # only with a Unicode-aware font, which we don't ship — so a stray
    # em-dash in a note would render as "?" in the printed PDF. Guard
    # against that: no em-dashes anywhere in the sample notes.
    for topic in SAMPLE_TOPICS:
        assert "\u2014" not in topic["note"], (
            f"em-dash found in topic note: {topic!r}"
        )


def test_sample_pdf_scenarios_are_distinct_and_neutral():
    """Both scenarios must ship the same six topic titles (so a parent
    toggling low-conflict ↔ high-conflict sees the SAME subjects but
    different alignment flags), the status mixes must be distinct, and
    both must be Latin-1 safe."""
    from joint_alignment_sample_pdf import SAMPLE_TOPICS_LOW, SAMPLE_TOPICS_HIGH
    low_titles = sorted(t["title"] for t in SAMPLE_TOPICS_LOW)
    high_titles = sorted(t["title"] for t in SAMPLE_TOPICS_HIGH)
    assert low_titles == high_titles, (
        "low and high scenarios must ship the same six topic titles"
    )
    low_counts = {"agree": 0, "differ": 0, "incomplete": 0}
    high_counts = {"agree": 0, "differ": 0, "incomplete": 0}
    for t in SAMPLE_TOPICS_LOW:
        low_counts[t["status"]] += 1
    for t in SAMPLE_TOPICS_HIGH:
        high_counts[t["status"]] += 1
    # Low-conflict must have MORE agrees than high-conflict; high must
    # have MORE differs. Otherwise the toggle is misleading.
    assert low_counts["agree"] > high_counts["agree"]
    assert high_counts["differ"] > low_counts["differ"]
    for t in SAMPLE_TOPICS_HIGH:
        assert "\u2014" not in t["note"], (
            f"em-dash in high-conflict note: {t!r}"
        )


def test_sample_pdf_scenario_query_switches_dataset_bytes():
    """Ingress-level check: `?scenario=high-conflict` must return a
    different PDF payload length than the low-conflict default; a
    bogus scenario key must fall back silently to the default (same
    layout as low-conflict)."""
    r_low = requests.get(
        f"{BASE_URL}/api/insights/samples/joint-alignment-preview.pdf",
        timeout=20,
    )
    r_high = requests.get(
        f"{BASE_URL}/api/insights/samples/joint-alignment-preview.pdf"
        f"?scenario=high-conflict",
        timeout=20,
    )
    r_bogus = requests.get(
        f"{BASE_URL}/api/insights/samples/joint-alignment-preview.pdf"
        f"?scenario=totally-not-a-scenario",
        timeout=20,
    )
    for r in (r_low, r_high, r_bogus):
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
    # High-conflict has more differ rows (longer notes on average) —
    # the layout differs and the payload length must differ.
    assert len(r_low.content) != len(r_high.content), (
        f"low({len(r_low.content)}) and high({len(r_high.content)}) "
        "must produce different-sized PDFs"
    )
    # Bogus scenario falls back to default → same content layout as
    # low. PDF `/CreationDate` changes between renders so the byte
    # hashes differ, but the length is deterministic per scenario.
    assert len(r_bogus.content) == len(r_low.content), (
        "unknown scenario must fall back to the low-conflict default"
    )


def test_sample_pdf_normalise_scenario_falls_back_to_default():
    from joint_alignment_sample_pdf import (
        normalise_scenario,
        DEFAULT_SCENARIO,
    )
    assert normalise_scenario("low-conflict") == "low-conflict"
    assert normalise_scenario("HIGH-CONFLICT") == "high-conflict"
    assert normalise_scenario(" high-conflict ") == "high-conflict"
    assert normalise_scenario("unknown") == DEFAULT_SCENARIO
    assert normalise_scenario(None) == DEFAULT_SCENARIO
    assert normalise_scenario("") == DEFAULT_SCENARIO
    assert normalise_scenario(12345) == DEFAULT_SCENARIO
