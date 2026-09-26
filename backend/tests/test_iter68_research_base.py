"""Iteration 68: Perplexity 'Research Base' in the Professional Alignment Report — resilient when unconfigured, rendered in PDF."""
import asyncio
import os

import pymupdf
import pytest

from casekit import new_case
from research import _insight_question, research_insight
from test_legal_report import API


def test_insight_question_uses_report_context() -> None:
    q = _insight_question({"joint_rating": 4, "child_focus": {"educational": {"checked": True}}, "conflict_pathways": ["Parenting Coordination"]}, "78205")
    assert "Educational needs" in q and "Parenting Coordination" in q and "78205" in q and "legal advice" in q


def test_research_insight_never_raises_without_key(monkeypatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    assert asyncio.run(research_insight({"joint_rating": 5}, {"profile": {"zip": "78205"}})) is None


def test_research_insight_swallows_upstream_errors(monkeypatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-invalid-test-key")
    import research
    async def boom(*a, **k):
        raise RuntimeError("unreachable")
    monkeypatch.setattr(research, "_sonar_call", boom)
    assert asyncio.run(research_insight({"joint_rating": 5}, {"profile": {}})) is None


def test_pdf_renders_research_base_footer() -> None:
    from pdf_report import build_legal_lens_pdf
    from legal_lens import _new_report, _lens_view
    doc = {"id": "x", "professional_id": "p", "participants": {"a": {"name": "A"}, "b": {"name": "B"}}, "responses": {}, "child_name": "Kid", "subject": "education", "subject_label": "Education"}
    rep = _new_report(doc, {"name": "Pro"})
    rep["research_base"] = {"text": "Research indicates structured communication reduces conflict exposure [1].", "citations": [{"index": 1, "url": "https://example.org/study"}], "model": "sonar", "zip": "78205", "fetched_at": "2026-09-26T00:00:00"}
    v = asyncio.run(_lens_view(_FakeDb(), rep, doc))
    text = "".join(p.get_text() for p in pymupdf.open(stream=build_legal_lens_pdf(v), filetype="pdf"))
    assert "RESEARCH BASE" in text and "example.org/study" in text and "Perplexity sonar" in text


class _FakeDb:
    class providers:
        @staticmethod
        def find(*a, **k):
            class _C:
                def sort(self, *a, **k):
                    return self
                async def to_list(self, n):
                    return []
            return _C()


@pytest.mark.skipif(bool(os.environ.get("PERPLEXITY_API_KEY")), reason="only meaningful when Perplexity is unconfigured")
def test_endpoint_503_when_unconfigured_and_ai_draft_still_works() -> None:
    pro, _, _, d = new_case(API)
    rid = d["id"]
    assert pro.post(f"{API}/cases/{rid}/professional-report/research-insight").status_code == 503
    r = pro.post(f"{API}/cases/{rid}/professional-report/ai-draft", json={"fields": {}, "model": "gemini"})
    assert r.status_code == 200 and r.json()["research_base"] is None and r.json()["fields"]
    assert pro.get(f"{API}/cases/{rid}/professional-report/pdf").status_code == 200
