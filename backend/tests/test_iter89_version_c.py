"""Version C (LGBTQ+ relationship self-assessment): content, tiering, import, and identity-leak guards in report/PDF projections."""
import pymupdf

from safety_import import extract_safety_screening, screening_summary
from safety_screening import VERSIONS, VERSION_LABEL, build_record, compute_tier, item_view, public_record, public_spec, receipt

RAW_C = {"c_1": "Sometimes", "c_8": "Frequently", "c_9": "Never", "c_10": "Sometimes", "c1": "Yes", "c_15": "Yes", "safe": "Somewhat safe"}
IDENTITY_WORDS = ("lgbtq", "orientation", "gender identity", "hide your gender", "pronoun", "hiv", "out you")


def test_version_c_content():
    ids = [i["id"] for i in VERSIONS["C"]["items"]]
    assert ids == ["c_1", "c_2", "c_3", "c_4", "c_5", "c_6", "c_7", "c_8", "c_9", "c_10", "c_11", "c_12", "c1", "c2", "c_15", "safe"]
    spec = public_spec("C")
    assert "any gender or orientation" in spec["intro"] and "1-800-832-1901" in spec["intro"] and "not a validated instrument" in spec["label"]
    assert spec["trigger_warning"] == public_spec("A")["trigger_warning"]
    text = " ".join(i["text"] for i in VERSIONS["C"]["items"]).lower()
    assert "gun" not in text and "kill" not in text and "jealous" not in text
    assert {i["id"] for i in VERSIONS["C"]["items"] if i.get("tier3")} == {"c_4", "c_5", "c_6", "c_8", "c_9"}


def test_version_c_tiering():
    assert compute_tier("C", {"c_1": "Rarely", "c_7": "Never", "safe": "Very safe"}) == 1
    assert compute_tier("C", {"c_2": "Sometimes", "safe": "Very safe"}) == 2
    assert compute_tier("C", {"c_11": "Rarely", "safe": "Somewhat safe"}) == 2
    assert compute_tier("C", {"c_10": "Frequently"}) == 2
    for k in ("c_4", "c_5", "c_6", "c_8", "c_9"):
        assert compute_tier("C", {k: "Sometimes"}) == 3
    assert compute_tier("C", {"safe": "Not safe"}) == 3
    assert compute_tier("C", {"c_8": "Prefer not to say", "safe": "Prefer not to say"}) == 1


def test_import_version_c_and_legacy():
    rec = extract_safety_screening({"safety_screening": {"version": "c", "completed_at": "2026-06-03", "tier": 2, "answered_count": 10, "responses": {"c_8": "Sometimes"}}})
    assert rec["version"] == "C" and rec["tier"] == 2 and rec["source"] == "sacoparentsapp.online"
    assert extract_safety_screening({"safety_screening": {"version": "C", "responses": {"c_9": "Frequently"}}})["tier"] == 3
    legacy = extract_safety_screening({"family_violence_assessment": {"responses": {"Afraid?": "Yes"}}})
    assert legacy and legacy["version"] is None


def test_report_projections_never_identify_version_c():
    rec = build_record("C", RAW_C)
    assert VERSION_LABEL["C"] == "Version C"
    pub = public_record(rec)
    assert "responses" not in pub and "items" not in pub and "title" not in pub
    assert pub["version"] == "C" and not any(w in str(pub).lower() for w in IDENTITY_WORDS)
    for blob in (receipt(rec, "Parent A").lower(), screening_summary(rec, "Parent A").lower()):
        assert "version c" in blob and not any(w in blob for w in IDENTITY_WORDS), blob
    assert any(i["id"] == "c_8" and i["answer"] == "Frequently" for i in item_view(rec))


def test_pdf_shows_version_c_tier_only():
    from pdf_lens import build_legal_lens_pdf
    from sample_legal_lens import sample_legal_lens
    v = sample_legal_lens()
    v["safety_screening"] = {"a": public_record(build_record("C", RAW_C)), "b": None}
    text = " ".join("\n".join(p.get_text() for p in pymupdf.open(stream=build_legal_lens_pdf(v), filetype="pdf")).split()).lower()
    assert "version c" in text and "tier 3" in text and "not received" in text
    assert not any(w in text for w in IDENTITY_WORDS) and "frequently" not in text and "somewhat safe" not in text


def test_spec_export_matches_runtime():
    from safety_screening import spec_export
    spec = spec_export()
    assert set(spec["versions"]) == {"A", "B", "C"} and spec["assignment"]["no_gender_or_non_binary"] == ["A", "B", "C"]
    for k, v in spec["versions"].items():
        assert [i["id"] for i in v["items"]] == [i["id"] for i in VERSIONS[k]["items"]]
        assert all(compute_tier(k, {i: "Sometimes"}) == 3 for i in spec["tiers"]["tier3_items"][k])
    assert "orientation" in spec["assignment"]["store_only"] and spec["export_contract"]["field"] == "safety_screening"
