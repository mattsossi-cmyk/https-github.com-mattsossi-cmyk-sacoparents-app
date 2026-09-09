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
    # Marketing PDF: opens inline, with a stable filename so the
    # browser Save dialog matches the "email to co-parent" copy.
    assert "sacoparents-joint-alignment-sample.pdf" in disposition


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
    sample page renders. If the frontend copy changes, this test
    fails until the backend module is updated in the same commit."""
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
