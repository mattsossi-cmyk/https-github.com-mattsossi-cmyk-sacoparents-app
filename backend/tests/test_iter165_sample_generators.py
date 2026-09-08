"""Iteration 165 — sample-library PDF generators.

The `/samples` public catalog exposes anonymised sample PDFs so
mediators can preview each artefact before committing. `generate_samples.py`
renders them via the LIVE production renderers with hard-coded
fictitious fixtures. This module guarantees each renderer produces a
valid PDF (starts with `%PDF-`) without touching the network or DB.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/app/backend")

import generate_samples as gs  # noqa: E402


def _looks_like_pdf(data: bytes) -> bool:
    return isinstance(data, (bytes, bytearray)) and data[:5] == b"%PDF-"


def test_foundation_statement_sample_renders():
    filename, data = gs.sample_foundation_statement()
    assert filename.endswith(".pdf")
    assert _looks_like_pdf(data)
    # Sanity — the fixture is chunky enough that a valid PDF is >
    # 2KB.
    assert len(data) > 1500


def test_case_status_report_sample_renders():
    filename, data = gs.sample_case_status_report()
    assert filename.endswith(".pdf")
    assert _looks_like_pdf(data)
    assert len(data) > 1500


def test_cost_splitter_sample_renders():
    filename, data = gs.sample_cost_ledger()
    assert filename.endswith(".pdf")
    assert _looks_like_pdf(data)
    # The cost splitter embeds the org logo so the byte count is
    # dominated by the image, but the PDF header check is what
    # matters.
    assert len(data) > 1500


def test_generate_all_writes_three_files(tmp_path, monkeypatch):
    """Run the full pipeline against a tmp directory so we don't
    scribble on /app/frontend/public/downloads/ during CI."""
    monkeypatch.setattr(gs, "OUT_DIR", str(tmp_path))
    paths = gs.generate_all()
    assert len(paths) == 3
    for p in paths:
        assert os.path.exists(p)
        with open(p, "rb") as f:
            head = f.read(8)
        assert head.startswith(b"%PDF-"), f"{p} is not a PDF"


def test_public_downloads_contains_freshly_generated_samples():
    """The build already ran locally — check the shipping copies are
    present so the /samples page links never 404."""
    downloads = "/app/frontend/public/downloads"
    for expected in (
        "sacoparents-foundation-statement-sample.pdf",
        "sacoparents-case-status-report-sample.pdf",
        "sacoparents-cost-splitter-sample.pdf",
    ):
        path = os.path.join(downloads, expected)
        assert os.path.exists(path), f"missing sample PDF: {expected}"
        with open(path, "rb") as f:
            head = f.read(8)
        assert head.startswith(b"%PDF-"), f"{expected} is not a PDF"
