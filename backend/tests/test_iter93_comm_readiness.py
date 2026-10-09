"""Communication Readiness: record sanitization, flag input, import from parent app, spec export."""
from safety_screening import COMM_ITEMS, comm_items_view, comm_record, spec_export


def test_comm_record_validates_and_flags():
    r = comm_record({"cr_conflict": "High", "cr_direct": "bogus", "cr_channel": "Direct messaging", "cr_child": "  worried about handoffs  "})
    assert r["responses"] == {"cr_conflict": "High", "cr_channel": "Direct messaging", "cr_child": "worried about handoffs"}
    assert r["answered_count"] == 3 and r["flag_for_professional"] is True
    assert comm_record({"cr_conflict": "Low", "cr_direct": "Yes"})["flag_for_professional"] is False
    assert comm_record({"cr_direct": "Not comfortable"})["flag_for_professional"] is True
    assert comm_record({})["answered_count"] == 0
    assert [x["answer"] for x in comm_items_view(comm_record({"cr_direct": "Only in writing"}))] == ["Skipped", "Only in writing", "Skipped", "Skipped"]


def test_comm_items_wording_is_neutral():
    blob = " ".join(i["text"] + " " + " ".join(i["options"] or []) for i in COMM_ITEMS).lower()
    for banned in ("parallel parenting", "low-contact", "healthiest"):
        assert banned not in blob


def test_spec_export_includes_comm_contract():
    spec = spec_export()
    assert spec["communication_readiness"]["export_field"] == "communication_readiness"
    assert [i["id"] for i in spec["communication_readiness"]["items"]] == ["cr_conflict", "cr_direct", "cr_channel", "cr_child"]


def test_hub_banner_copy_is_current():
    src = open("/app/frontend/src/pages/SafetyHub.jsx", encoding="utf-8").read()
    assert "Designed for All Co-Parents" in src
    assert "Private, behavior-focused safety questions for every family structure, including non-binary and LGBTQ+ co-parents." in src
    assert "tailored safety questions for men, women" not in src and "Non-Judgmental" not in src
