"""Family-violence / safety screening imported from sacoparentsapp.online: extraction, storage shape, report surfacing."""
import asyncio

from legal_lens import readiness
from safety_import import extract_safety_screening, screening_summary

PAYLOAD = {"email": "p@example.com", "assessments": [
    {"title": "Co-Parenting Communication", "completed_at": "2026-05-01T00:00:00Z", "responses": {"How do you share updates?": "Text messages"}},
    {"title": "Family Violence & Safety Screening", "completed_at": "2026-05-02T00:00:00Z", "responses": {
        "Have you felt afraid of the other parent in the last 12 months?": "Yes, during exchanges",
        "Has the other parent threatened you or the child?": "No",
        "Are there protective orders in place?": "No"}}],
    "statements": []}


def test_extracts_screening_from_free_text_export():
    s = extract_safety_screening(PAYLOAD)
    assert s and s["source"] == "sacoparentsapp.online" and s["title"].startswith("Family Violence")
    assert s["item_count"] == 3 and s["concern_count"] == 1 and s["items"][0]["concern"] is True


def test_structured_field_supported_and_absent_returns_none():
    s = extract_safety_screening({"assessments": [], "family_violence_assessment": {"title": "FV Screen", "responses": {"q1": "yes", "q2": "no"}}})
    assert s and s["item_count"] == 2 and s["concern_count"] == 1
    assert extract_safety_screening({"assessments": [{"title": "Education", "responses": {"Homework?": "Daily"}}]}) is None


def test_summary_is_neutral_and_never_leaks_answers():
    s = extract_safety_screening(PAYLOAD)
    line = screening_summary(s, "Parent A")
    assert "received from sacoparentsapp.online" in line and "3 screening items" in line and "1 item(s) indicated a concern" in line
    assert "afraid" not in line and "exchanges" not in line and "not findings" in line


def test_readiness_marks_fv_received_when_screening_imported():
    doc = {"id": "x", "subject": "education", "participants": {"a": {}, "b": {}},
           "responses": {"a": {"answers": {}, "imported": True, "safety_screening": extract_safety_screening(PAYLOAD)}, "b": {"answers": {"q": "a"}}}}
    rd = {r["key"]: r for r in readiness(doc)}
    assert rd["fv_a"]["done"] is True and rd["fv_a"]["na"] is False and rd["fv_b"]["done"] is False


def test_completed_at_non_string_does_not_crash():
    from safety_import import extract_safety_screening, screening_summary
    for bad in (1718000000, 1718000000000, {"x": 1}, ["a"], True, None, "2026-06-01T10:00:00Z"):
        scr = extract_safety_screening({"safety_screening": {"completed_at": bad, "responses": {"Do you feel safe?": "no"}}})
        out = screening_summary(scr, "Parent A")
        assert "safety screening received" in out
    assert screening_summary({"completed_at": 1718000000, "source": "x", "item_count": 1, "concern_count": 0}, "P") .startswith("P:")


def test_other_parent_not_required_when_only_one_screening_imported():
    doc = {"subject": "communication", "subject_label": "Communication", "responses": {"a": {"answers": {"q": "x"}, "safety_screening": {"items": [], "item_count": 0, "concern_count": 0, "source": "s"}}, "b": {"answers": {"q": "y"}}}}
    rd = {r["key"]: r for r in readiness(doc)}
    assert rd["fv_b"]["not_required"] is True and rd["fv_a"]["not_required"] is False
    from unittest.mock import patch
    import legal_lens
    with patch.object(legal_lens, "suggested_score", lambda d: None):
        hdr = legal_lens._prefill_header(doc, {}, rd)
    assert hdr["fv_a_received"] == "Received" and hdr["fv_b_received"] == "Not Required"
