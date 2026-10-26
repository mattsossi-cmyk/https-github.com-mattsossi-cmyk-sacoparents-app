"""The owner-supplied IMPORTANT LEGAL NOTICE AND DISCLAIMER + Acknowledgment is the single legal notice and the LAST block of every Co-Parenting Agreement (PDF + on-screen model)."""
import pymupdf

from agreement_model import court_agreement_model
from joint_data import AGREEMENT_DISCLAIMER, AGREEMENT_LEGAL_NOTICE_HEADING, AGREEMENT_LEGAL_NOTICE_PARAGRAPHS, agreement_legal_notice
from joint_engine import generate_agreement
from pdf_agreement import build_agreement_pdf
from sample_agreement import sample_agreement, sample_agreement_doc

FIRST = "This Co-Parenting Agreement is intended to assist parents in identifying areas of agreement, establishing parenting expectations, improving communication, and developing child-focused arrangements."
LAST = "Parents are encouraged to have this Agreement reviewed by a licensed Texas attorney before seeking to incorporate its provisions into a court order."
ACK = "By signing below, the parents acknowledge that they understand the purpose and potential legal limitations of this Agreement and that not all provisions are necessarily legally enforceable."


def _norm(s: str) -> str:
    return " ".join(s.replace("’", "'").split())


def test_constants_are_verbatim():
    assert AGREEMENT_LEGAL_NOTICE_HEADING == "IMPORTANT LEGAL NOTICE AND DISCLAIMER"
    assert len(AGREEMENT_LEGAL_NOTICE_PARAGRAPHS) == 6 and AGREEMENT_LEGAL_NOTICE_PARAGRAPHS[0] == FIRST and AGREEMENT_LEGAL_NOTICE_PARAGRAPHS[-1] == LAST
    assert "the court order controls unless modified through appropriate legal procedures" in AGREEMENT_DISCLAIMER
    n = agreement_legal_notice()
    assert n["subheading"] == "SA CoParents – Co-Parenting Agreement" and n["acknowledgment_heading"] == "Acknowledgment" and n["acknowledgment"] == ACK
    assert n["signature_labels"] == ["Parent 1", "Parent 2"]


def test_pdf_notice_is_last_block_with_acknowledgment_signatures():
    doc = sample_agreement_doc()
    text = _norm("\n".join(p.get_text() for p in pymupdf.open(stream=build_agreement_pdf(sample_agreement(), doc=doc, is_sample=True), filetype="pdf")))
    assert text.count("IMPORTANT LEGAL NOTICE AND DISCLAIMER") == 1
    assert "LEGAL NOTICE & DISCLAIMER:" not in text and "informal framework" not in text  # old notice gone
    i = text.index("IMPORTANT LEGAL NOTICE AND DISCLAIMER")
    assert i > text.index("Our Shared Commitment") and i > text.index("Wellness, Phones & Social Media")
    tail = text[i:]
    for needle in (FIRST, LAST, "Acknowledgment", ACK, "Parent 1:", "Parent 2:", "Date:"):
        assert needle in tail, needle
    assert tail.index("Parent 2:") > tail.index("Parent 1:") > tail.index(ACK) > tail.index(LAST)
    assert "S I G N A T U R E" not in text  # the old signature block is not duplicated


def test_models_carry_notice_for_on_screen_rendering():
    doc = sample_agreement_doc()
    for m in (court_agreement_model(doc), generate_agreement(doc)):
        assert m["disclaimer"] == AGREEMENT_DISCLAIMER and m["legal_notice_heading"] == AGREEMENT_LEGAL_NOTICE_HEADING
        assert m["legal_notice"]["paragraphs"] == AGREEMENT_LEGAL_NOTICE_PARAGRAPHS and m["legal_notice"]["acknowledgment"] == ACK


def test_wellness_section_in_agreement_and_pdf():
    doc = sample_agreement_doc()
    rep = generate_agreement(doc)
    keys = [s["key"] for s in rep["sections"]]
    assert keys == ["foundation", "transitions", "communication", "education", "medical", "psychological", "activities", "wellness_tech", "decisions", "differences", "review"]
    assert [s["num"] for s in rep["sections"]] == list(range(1, 12))
    w = next(s for s in rep["sections"] if s["key"] == "wellness_tech")
    assert w["label"] == "Wellness, Phones & Social Media" and w["specific_agreements"] and w["communication_method"]
    m = court_agreement_model(doc)
    assert m["wellness"] and m["wellness_foundation"] and "smartphone" in " ".join(m["wellness_foundation"]).lower()
    text = _norm("\n".join(p.get_text() for p in pymupdf.open(stream=build_agreement_pdf(rep, doc=doc, is_sample=True), filetype="pdf")))
    assert "Wellness, Phones & Social Media" in text and "RAISED IN THE PARENTS' FOUNDATION STATEMENTS" in text.upper()
    assert text.index("Wellness, Phones & Social Media") < text.index("Information Sharing") < text.index("Our Shared Commitment")
