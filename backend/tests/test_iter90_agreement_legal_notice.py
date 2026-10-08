"""The verbatim LEGAL NOTICE & DISCLAIMER is the single legal notice and the LAST block of every Co-Parenting Agreement (PDF + on-screen model)."""
import pymupdf

from agreement_model import DISCLAIMER, LEGAL_NOTICE_HEADING, court_agreement_model
from joint_engine import generate_agreement
from pdf_agreement import build_agreement_pdf
from sample_agreement import sample_agreement, sample_agreement_doc

VERBATIM = ("This Co-Parenting Assessment / Agreement generated through SA CoParents is intended solely as an informal framework to assist parents in alignment and good-faith communication. "
            "It is not a legally binding court order or enforceable contract. However, this document may be presented in legal proceedings, mediation, or court hearings as admissible evidence of the parties' mutual intent, "
            "good-faith efforts, and negotiated understanding regarding the best interests of the child. To make any agreement legally enforceable, it must be formally submitted to and approved by a court of competent jurisdiction.")


def _norm(s: str) -> str:
    return " ".join(s.replace("’", "'").split())


def test_constant_is_verbatim():
    assert DISCLAIMER == VERBATIM and LEGAL_NOTICE_HEADING == "LEGAL NOTICE & DISCLAIMER:"


def test_pdf_notice_is_last_and_only_notice():
    doc = sample_agreement_doc()
    text = _norm("\n".join(p.get_text() for p in pymupdf.open(stream=build_agreement_pdf(sample_agreement(), doc=doc, is_sample=True), filetype="pdf")))
    assert text.count("LEGAL NOTICE & DISCLAIMER:") == 1
    body = text.split("LEGAL NOTICE & DISCLAIMER:")[1].split(" SAMPLE ")[0].split(" SA CoParents Co-Parenting Agreement ·")[0]
    assert body.strip().endswith("approved by a court of competent jurisdiction.")  # last content block; only the page footer follows
    assert text.index("LEGAL NOTICE & DISCLAIMER:") > text.index("Our Shared Commitment")
    assert "does not modify a court order" not in text and "consult an attorney" not in text


def test_models_carry_notice_for_on_screen_rendering():
    doc = sample_agreement_doc()
    for m in (court_agreement_model(doc), generate_agreement(doc)):
        assert m["disclaimer"] == VERBATIM and m["legal_notice_heading"] == LEGAL_NOTICE_HEADING
