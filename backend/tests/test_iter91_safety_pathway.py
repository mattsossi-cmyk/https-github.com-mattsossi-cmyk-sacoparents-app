"""Safety Pathway Engine: flag mapping A/B/C, import with/without flags, priority rules, highest-wins, sanitized report/PDF, no custody-style labels."""
import re

import pymupdf

from safety_import import extract_safety_screening
from safety_pathway import FLAGS, LABEL, case_pathway, compute_flags, highest, normalize_import, pathway_from_flags, pathway_lines, public_pathway
from safety_screening import build_record, public_record, public_spec

BANNED = ("parallel parenting", "lgbtq", "orientation", "frequently", "sometimes", "not safe", "threatsorintimidation", "financialabuse", "123 main st")


def test_flag_mapping_a_b_c():
    a = compute_flags("A", {"a2": "Sometimes", "a3": "Frequently", "a5": "Sometimes", "x_1": "Frequently", "x_2": "Sometimes", "x_3": "Sometimes", "x_4": "Frequently", "x_5": "Yes", "safe": "Not safe"})
    assert all(a[f] for f in FLAGS)
    b = compute_flags("B", {"b5": "Sometimes", "b9": "Sometimes", "b4": "Frequently"})
    assert b["threatsOrIntimidation"] and b["physicalOrSexualViolence"] and b["coerciveControl"] and not b["financialAbuse"]
    c = compute_flags("C", {"c_4": "Frequently", "c_6": "Sometimes", "c_7": "Sometimes"})
    assert c["threatsOrIntimidation"] and c["physicalOrSexualViolence"] and c["coerciveControl"]
    never = compute_flags("A", {"a2": "Rarely", "a3": "Prefer not to say", "x_5": "Prefer not to say", "x_3": "", "safe": "Prefer not to say"})
    assert not any(never.values())


def test_priority_rules_and_highest_wins():
    assert pathway_from_flags({})["pathway"] == "standard"
    for f in ("imminentDangerReported", "physicalOrSexualViolence", "childRelatedThreats", "activeProtectiveOrder"):
        assert pathway_from_flags({f: True})["pathway"] == "protected_review"
    for f in ("coerciveControl", "threatsOrIntimidation", "technologyStalking", "fearOfRetaliation", "financialAbuse"):
        assert pathway_from_flags({f: True})["pathway"] == "structured"
    p = pathway_from_flags({"coerciveControl": True, "activeProtectiveOrder": True})
    assert p["pathway"] == "protected_review" and p["triggered"] == ["activeProtectiveOrder"]
    assert highest(["standard", "structured"]) == "structured" and highest(["protected_review", "structured"]) == "protected_review" and highest([None]) is None
    assert LABEL["protected_review"] == "Protected participation review recommended" and LABEL["structured"] == "Structured communication recommended"


def test_import_with_and_without_flags():
    with_flags = extract_safety_screening({"safety_screening": {"version": "A", "responses": {"a1": "Never"}}, "safety_flags": {"technologyStalking": True}, "safety_pathway": "structured"})
    assert with_flags["flags"]["technologyStalking"] and with_flags["pathway_suggested"]["pathway"] == "structured"
    computed = extract_safety_screening({"safety_screening": {"version": "C", "responses": {"c_5": "Sometimes"}}})
    assert computed["flags"]["physicalOrSexualViolence"] and computed["pathway_suggested"]["pathway"] == "protected_review"
    assert normalize_import({"financialAbuse": 1}, "Protected participation review recommended") == ({**{k: False for k in FLAGS}, "financialAbuse": True}, "protected_review")
    assert normalize_import("bad", "weird") == (None, None)


def _doc(confirm_a=None, confirm_b=None, order=False):
    sa = build_record("A", {"a3": "Sometimes", "x_5": "Yes" if order else "No", "a9": "we live at 123 Main St"})
    sb = build_record("B", {"b4": "Sometimes"})
    doc = {"subject": "communication", "safety_screenings": {"a": sa, "b": sb}, "safety_pathway": {}}
    if confirm_a:
        doc["safety_pathway"]["a"] = {"status": "confirmed", "confirmed": confirm_a}
    if confirm_b:
        doc["safety_pathway"]["b"] = {"status": "confirmed", "confirmed": confirm_b}
    return doc


def test_no_auto_restriction_until_professional_confirms():
    doc = _doc()
    assert doc["safety_screenings"]["a"]["pathway_suggested"]["pathway"] == "protected_review"
    assert case_pathway(doc) is None and public_pathway(doc) is None
    doc["safety_pathway"]["a"] = {"status": "dismissed", "confirmed": None, "suggested": "protected_review"}
    assert public_pathway(doc) is None
    doc = _doc(confirm_a="structured", confirm_b="protected_review")
    assert case_pathway(doc) == "protected_review"


def test_public_pathway_is_sanitized():
    doc = _doc(confirm_a="protected_review", order=True)
    pw = public_pathway(doc, {"child_focus": {"medical": {"checked": True, "note": "lives at 123 Main St"}, "routines": {"checked": True}, "medical2": {"checked": True}}})
    assert pw["label"] == LABEL["protected_review"] and pw["court_order_notice"] and pw["child_needs"] == ["Medical needs", "Parenting routines"]
    blob = " ".join(pathway_lines(pw)).lower()
    assert "written-only" in blob and "independent professional review" in blob and "remain restricted" in blob
    for w in BANNED:
        assert w not in blob, w
    assert not re.search(r"protected participation(?! review recommended)", blob)  # bare custody-style phrase never appears
    assert "flags" not in pw and "responses" not in pw
    assert public_pathway(_doc(confirm_a="structured"))["court_order_notice"] is None
    assert "flags" not in public_record(doc["safety_screenings"]["a"]) and "pathway_suggested" not in public_record(doc["safety_screenings"]["a"])


def test_pdf_shows_confirmed_label_only():
    from pdf_lens import build_legal_lens_pdf
    from sample_legal_lens import sample_legal_lens
    doc = _doc(confirm_a="protected_review", order=True)
    v = sample_legal_lens()
    v["safety_screening"] = {"a": public_record(doc["safety_screenings"]["a"]), "b": None}
    v["safety_pathway"] = public_pathway(doc, v["report"])
    text = " ".join("\n".join(p.get_text() for p in pymupdf.open(stream=build_legal_lens_pdf(v), filetype="pdf")).split()).lower()
    assert "protected participation review recommended" in text and "active court or protective orders reported" in text and "remain restricted" in text
    # Scope the sanitization check to the pathway card (the pre-existing 1-11 scale table legitimately names its levels elsewhere)
    card = text.split("safety pathway — professional's confirmed process consideration", 1)[1].split("parent a perspective", 1)[0]
    for w in BANNED:
        assert w not in card, w
    assert not re.search(r"protected participation(?! review recommended)", card)
    assert "flags" not in card and "version c (" not in text


def test_spec_contains_extra_questions_for_every_version():
    for ver in ("A", "B", "C"):
        ids = [i["id"] for i in public_spec(ver)["items"]]
        assert ids[-6:] == ["x_1", "x_2", "x_3", "x_4", "x_5", "safe"]
        assert public_spec(ver)["scales"]["yn3"] == ["Yes", "No", "Prefer not to say"] and public_spec(ver)["safe_device_notice"]
