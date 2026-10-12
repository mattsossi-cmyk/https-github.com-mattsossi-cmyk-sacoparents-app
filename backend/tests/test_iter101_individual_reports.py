"""Iter 101 — Individual Perspective Reports: content rules, one packet/two sections, default under pause, switch logging, neutral label/filename, no leakage."""
import pytest
from fastapi import HTTPException

import fitz  # PyMuPDF

from court_workflow import SubmitIn, resolve_packet_mode
from pdf_individual import FILENAME_STEM, PACKET_LABEL, build_individual_reports_pdf

DOC = {
    "id": "case1", "case_code": "ABC-123", "child_name": "Ava Example",
    "participants": {"a": {"name": "Jamie Rivera"}, "b": {"name": "Robin Rivera"}},
    "responses": {"a": {"answers": {"needs_most": "RAW-A-ANSWER bedtime chaos at 123 Oak Street", "working_well": ""}},
                  "b": {"answers": {"needs_most": "RAW-B-ANSWER", "working_well": "RAW-B-COMM"}}},
    "safety_screenings": {"a": {"version": "C", "tier": 2, "completed_at": "2026-10-01T00:00:00+00:00", "responses": {"c1": "Sometimes"},
                                "flags": {"coerciveControl": True}, "safe_contact": {"method": "text", "address": "210-555-0100", "code_word": "QA-BLUE"}},
                          "b": None},
    "safety_pathway": {"a": {"status": "confirmed", "confirmed": "structured", "note": "PRIVATE-PATHWAY-NOTE"}},
    "professional_statement": {"status": "ready", "observations": "Both parents engaged respectfully with the process."},
}
PRO = {"name": "Dr. Pat Lee", "credentials_verified": True}


def _text(pdf_bytes: bytes) -> str:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as d:
        return " ".join("\n".join(p.get_text() for p in d).split())


def test_one_packet_two_separate_sections_with_neutral_covers():
    t = _text(build_individual_reports_pdf(DOC, PRO))
    assert t.count(PACKET_LABEL) == 2 and "Individual Perspective Report — Jamie Rivera" in t and "Individual Perspective Report — Robin Rivera" in t
    assert "does not quote, compare with, or reference the other parent" in t
    low = t.lower()
    for w in ("pause", "paused", "flag", "why", "reason", "family violence", "lgbtq"):
        assert w not in low, w


def test_content_rules_and_no_leakage():
    t = _text(build_individual_reports_pdf(DOC, PRO))
    assert "Parent A: safety screening" in t and "Received" in t and "Version C" in t and "2026-10-01" in t
    assert "Structured communication recommended" in t and "Both parents engaged respectfully" in t
    assert "Child's Primary Need" in t and "Concerns" in t
    assert "Perspective provided" in t and "Not provided" in t
    for leak in ("RAW-A-ANSWER", "RAW-B-ANSWER", "RAW-B-COMM", "123 Oak Street", "QA-BLUE", "210-555-0100", "PRIVATE-PATHWAY-NOTE", "Sometimes", "coerciveControl"):
        assert leak not in t, leak


def test_sections_do_not_cross_reference():
    with fitz.open(stream=build_individual_reports_pdf(DOC, PRO), filetype="pdf") as d:
        pages = [p.get_text() for p in d]
    a = "\n".join(p for p in pages if "Jamie Rivera" in p)
    b = "\n".join(p for p in pages if "Robin Rivera" in p)
    assert "Robin" not in a and "Jamie" not in b and "Parent B" not in a and "Parent A" not in b


def test_defaults_under_pause_and_block_joint():
    paused = {**DOC, "joint_paused": {"by": "p", "at": "now"}}
    assert resolve_packet_mode(paused, None) == "individual"
    with pytest.raises(HTTPException) as ei:
        resolve_packet_mode(paused, "joint")
    assert ei.value.status_code == 423 and "safety" not in ei.value.detail.lower() and "pause" not in ei.value.detail.lower()
    assert resolve_packet_mode(DOC, None) == "joint" and resolve_packet_mode(DOC, "individual") == "individual"
    assert resolve_packet_mode({**DOC, "joint_paused": None}, "joint") == "joint"  # resumed → may switch back
    assert SubmitIn().packet_mode is None


def test_switch_is_logged_and_label_filename_neutral():
    src = open("/app/backend/court_workflow.py", encoding="utf-8").read()
    assert 'Court packet format switched from {prev} to {bundle[\'mode\']}' in src and '"packet_label": ("Individual Perspective Reports"' in src
    assert 'filename="court-packet-PREVIEW.pdf"' in src and FILENAME_STEM == "court-packet"
    pi = open("/app/backend/pdf_individual.py", encoding="utf-8").read().lower()
    assert "safe_contact" not in pi.replace("never:", "").split("\"\"\"", 2)[2]  # body code never touches safe_contact
    assert "lgbtq" not in pi.split("\"\"\"", 2)[2]
