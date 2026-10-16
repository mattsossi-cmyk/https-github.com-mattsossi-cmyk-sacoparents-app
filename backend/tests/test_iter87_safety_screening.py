"""Version A / B private safety screenings: tiering, skips, assignment defaults, import parsing (new + legacy), PDF never prints answers."""
import pymupdf

from safety_import import extract_safety_screening, screening_summary
from safety_screening import VERSIONS, build_record, compute_tier, default_version, item_view, receipt

RAW_A = {"a1": "Frequently", "a2": "Sometimes", "a3": "Never", "a4": "Never", "a5": "Rarely", "a6": "Sometimes", "c1": "Yes", "c2": "Not sure", "a9": "fear of losing custody UNIQUE-FREETEXT-XYZ", "safe": "Somewhat safe"}


def test_versions_have_required_items_and_no_lethality_items():
    assert [i["id"] for i in VERSIONS["A"]["items"]] == ["a1", "a2", "a3", "a4", "a5", "a6", "c1", "c2", "a9", "safe"]
    assert [i["id"] for i in VERSIONS["B"]["items"]] == [f"b_{n}" for n in range(1, 16)] + ["c1", "c2", "c3", "safe"]
    text = " ".join(i["text"] for v in VERSIONS.values() for i in v["items"]).lower()
    assert "kill" not in text and "jealous" not in text
    assert "including men" in VERSIONS["B"]["intro"]


def test_tiering_version_a():
    assert compute_tier("A", {"a1": "Never", "a2": "Rarely", "safe": "Very safe"}) == 1
    assert compute_tier("A", {"a1": "Sometimes", "safe": "Very safe"}) == 2
    assert compute_tier("A", {"a5": "Rarely", "safe": "Somewhat safe"}) == 2
    assert compute_tier("A", {"a2": "Sometimes", "safe": "Very safe"}) == 3
    assert compute_tier("A", {"a4": "Frequently"}) == 3
    assert compute_tier("A", {"safe": "Not safe"}) == 3


def test_tiering_version_b():
    assert compute_tier("B", {"b_1": "Rarely", "b_3": "Rarely", "safe": "Very safe"}) == 1
    assert compute_tier("B", {"b_3": "Frequently", "safe": "Very safe"}) == 2
    assert compute_tier("B", {"b_9": "Frequently"}) == 2
    for k in ("b_5", "b_10", "b_11", "b_12", "b_13"):
        assert compute_tier("B", {k: "Sometimes"}) == 3


def test_skips_and_prefer_not_to_say_never_raise_tier():
    assert compute_tier("A", {}) == 1
    assert compute_tier("B", {"b_11": "Prefer not to say", "safe": "Prefer not to say"}) == 1
    rec = build_record("A", {"a1": "Never", "a2": "Prefer not to say", "a9": ""})
    assert rec["answered_count"] == 1 and rec["skipped_count"] == 14 and rec["tier"] == 1 and "a9" not in rec["responses"]


def test_default_version_by_gender():
    # 2026-10-16: no profile/gender inference — every parent sees the same four options.
    assert default_version("Woman") is None and default_version("man") is None
    assert default_version("non-binary") is None and default_version(None) is None and default_version("") is None


def test_import_new_structured_format():
    rec = extract_safety_screening({"safety_screening": {"version": "b", "completed_at": "2026-06-02T10:00:00Z", "tier": 3, "answered_count": 12, "source": "cdc_nisvs_adapted", "responses": {"b_5": "Sometimes", "safe": "Very safe"}}})
    assert rec["version"] == "B" and rec["tier"] == 3 and rec["completed_at"] == "2026-06-02" and rec["answered_count"] == 12 and rec["source"] == "sacoparentsapp.online"
    assert rec["responses"] == {"b_5": "Sometimes", "safe": "Very safe"} and rec["b_source"] == "cdc"
    rec2 = extract_safety_screening({"safety_screening": {"version": "A", "responses": {"a2": "Frequently"}}})
    assert rec2["tier"] == 3


def test_import_legacy_formats_still_work():
    legacy = extract_safety_screening({"assessments": [{"title": "Family Violence & Safety Screening", "completed_at": "2026-05-02", "responses": {"Afraid?": "Yes", "Orders?": "No"}}]})
    assert legacy and legacy["version"] is None and legacy["tier"] is None and legacy["concern_count"] == 1 and legacy["item_count"] == 2
    old_struct = extract_safety_screening({"safety_screening": {"completed_at": 1718000000, "responses": {"Do you feel safe?": "no"}}})
    assert old_struct and old_struct["version"] is None and "legacy" in receipt(old_struct, "P")


def test_receipt_and_summary_have_no_answers():
    rec = build_record("A", RAW_A)
    line = screening_summary(rec, "Parent A")
    assert "Received" in line and "Version A" in line and "women" not in line and "Tier 3" in line
    assert "Frequently" not in line and "UNIQUE-FREETEXT-XYZ" not in line
    assert "Not started" in screening_summary(None, "Parent B")
    assert any(i["id"] == "a9" and "UNIQUE-FREETEXT-XYZ" in i["answer"] for i in item_view(rec))


def test_pdf_shows_receipt_tier_but_never_raw_answers():
    from pdf_lens import build_legal_lens_pdf
    from sample_legal_lens import sample_legal_lens
    v = sample_legal_lens()
    v["safety_screening"] = {"a": build_record("A", RAW_A), "b": None}
    text = " ".join("\n".join(p.get_text() for p in pymupdf.open(stream=build_legal_lens_pdf(v), filetype="pdf")).split())
    assert "Version A" in text and "women" not in text and "Tier 3" in text and "Not started" in text
    assert "not a validated or diagnostic instrument" in text.lower()
    assert "UNIQUE-FREETEXT-XYZ" not in text and "humiliate" not in text.lower() and "Frequently" not in text
