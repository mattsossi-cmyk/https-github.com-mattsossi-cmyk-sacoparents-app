"""Version B (CDC NISVS-adapted, temporary) replaces Velonis/HITS by config flag; Version C credit + external resource link; import source handling."""
import safety_pathway
import safety_screening as ss
from safety_import import extract_safety_screening
from safety_screening import B_VARIANTS, RESOURCES, RESOURCES_C, SOURCES, SOURCES_B, VERSIONS, build_record, compute_tier, configure_version_b, item_view, public_spec, spec_export

CDC_Q = ["insult, humiliate, or make fun of you in front of others?", "keep you from having your own money?", "try to keep you from seeing or talking to family or friends?",
         "keep track of you by demanding to know where you were and what you were doing?", "make threats to physically harm you?",
         "threaten to hurt themselves or commit suicide because they were upset with you?", "make decisions that should have been yours to make?", "destroy something important to you?",
         "slap, push, or shove you?", "hit you with a fist or something hard, kick you, pull your hair, or slam you against something?",
         "try to hurt you by choking or suffocating you, burn you on purpose, or use a knife or gun?", "pressure you into unwanted sex, force you, or make you penetrate them?",
         "touch your sexual body parts when you didn't want them to?", "follow, watch, or repeatedly contact you in ways that made you feel afraid?"]


def test_version_b_cdc_content_is_live():
    assert ss.VERSION_B_SOURCE == "cdc" and VERSIONS["B"] is B_VARIANTS["cdc"]
    items = VERSIONS["B"]["items"]
    assert [i["text"] for i in items[:14]] == CDC_Q and items[14]["text"] == "How often do you feel afraid of them?" and items[14]["kind"] == "freq"
    assert [i["id"] for i in items[15:]] == ["c1", "c2", "c3", "safe"] and items[17]["text"] == "Do you worry about losing contact with your children if you ask for help?"
    assert items[18]["text"] == "How safe do you feel going home today?"
    assert "Partner violence can happen to anyone, including men." in VERSIONS["B"]["intro"]
    assert {i["id"] for i in items if i["tier3"]} == {"b_5", "b_10", "b_11", "b_12", "b_13"}
    assert SOURCES["B"] == "Adapted from the CDC National Intimate Partner and Sexual Violence Survey (NISVS) behavior categories. Screening questions, not a diagnostic tool; not a validated instrument. Temporary version."
    assert "permission" not in SOURCES["B"].lower() and "Velonis" not in SOURCES["B"]


def test_version_b_tiers():
    assert compute_tier("B", {f"b_{n}": "Never" for n in range(1, 16)} | {"safe": "Very safe"}) == 1
    assert compute_tier("B", {"b_1": "Rarely", "safe": "Somewhat safe"}) == 2
    assert compute_tier("B", {"b_7": "Sometimes", "safe": "Very safe"}) == 2
    for q in ("b_5", "b_10", "b_11", "b_12", "b_13"):
        assert compute_tier("B", {q: "Sometimes"}) == 3 and compute_tier("B", {q: "Frequently"}) == 3
    assert compute_tier("B", {"safe": "Not safe"}) == 3
    assert compute_tier("B", {"b_11": "Prefer not to say"}) == 1


def test_version_b_flag_mapping():
    fm = safety_pathway.FLAG_MAP["B"]
    assert {k for k, v in fm.items() if v == "threatsOrIntimidation"} == {"b_5", "b_6", "b_14", "b_15"}
    assert {k for k, v in fm.items() if v == "physicalOrSexualViolence"} == {"b_9", "b_10", "b_11", "b_12", "b_13"}
    assert {k for k, v in fm.items() if v == "coerciveControl"} == {"b_2", "b_3", "b_4", "b_7", "b_8"}
    f = safety_pathway.compute_flags("B", {"b_6": "Sometimes", "b_8": "Frequently", "b_9": "Rarely", "b_12": "Prefer not to say"})
    assert f["threatsOrIntimidation"] and f["coerciveControl"] and not f["physicalOrSexualViolence"]


def test_config_flag_toggles_back_to_velonis_and_forward():
    try:
        configure_version_b("velonis")
        assert VERSIONS["B"] is B_VARIANTS["velonis"] and [i["id"] for i in VERSIONS["B"]["items"]][:9] == [f"b{n}" for n in range(1, 10)]
        assert SOURCES["B"] == SOURCES_B["velonis"] and "Velonis" in SOURCES["B"]
        assert safety_pathway.FLAG_MAP["B"] == safety_pathway.FLAG_MAP_B["velonis"]
        assert compute_tier("B", {"b6": "Sometimes"}) == 3 and spec_export()["version_b_source"] == "velonis"
        rec = build_record("B", {"b4": "Sometimes"})
        assert rec["b_source"] == "velonis" and rec["flags"]["coerciveControl"]
    finally:
        configure_version_b("cdc")
    assert VERSIONS["B"] is B_VARIANTS["cdc"] and safety_pathway.FLAG_MAP["B"] == safety_pathway.FLAG_MAP_B["cdc"] and spec_export()["version_b_source"] == "cdc"


def test_import_accepts_cdc_source_and_legacy_fallback():
    rec = extract_safety_screening({"safety_screening": {"version": "B", "source": "cdc_nisvs_adapted", "responses": {"b_10": "Sometimes", "safe": "Very safe"}}})
    assert rec["b_source"] == "cdc" and rec["tier"] == 3 and rec["flags"]["physicalOrSexualViolence"]
    old = extract_safety_screening({"safety_screening": {"version": "B", "responses": {"b7": "Sometimes", "b4": "Frequently"}}})
    assert old["b_source"] == "velonis" and old["tier"] == 3 and old["flags"]["coerciveControl"]
    q = [i["question"] for i in item_view(old)]
    assert any("physically hurt you?" in x for x in q) and not any("slap, push" in x for x in q)
    assert any("slap, push" in x for x in [i["question"] for i in item_view(rec)])


def test_version_c_credit_and_external_resource():
    assert SOURCES["C"].endswith("Informed by guidance from the National LGBTQ Institute on Intimate Partner Violence (lgbtqipvinstitute.org).")
    spec = public_spec("C")
    names = [r["name"] for r in spec["resources"]]
    assert any("1-800-832-1901" == r["contact"] for r in spec["resources"]) and any("Los Angeles" not in n for n in names) and not any("323-" in (r.get("contact") or "") for r in spec["resources"])
    ext = next(r for r in spec["resources"] if r.get("external"))
    assert ext["url"] == "https://lgbtqipvinstitute.org/resources-for-survivors/" and ext["name"] == "LGBTQ+ survivor resources from the National LGBTQ Institute on IPV, including a personal safety planning tool"
    assert spec["external_link_note"] == "Opens in a new tab and leaves SA CoParents."
    assert not any(r.get("external") for r in public_spec("A")["resources"]) and public_spec("B")["resources"] == RESOURCES and RESOURCES_C[0]["contact"] == "1-800-832-1901"
    assert all(r["verified"] for r in RESOURCES)


def test_frontend_external_link_attributes():
    src = open("/app/frontend/src/pages/SafetyScreening.jsx", encoding="utf-8").read()
    assert 'target="_blank" rel="noopener noreferrer"' in src and "screening-external-note" in src and "window.location" not in src.split("const Hotline")[1].split("const Item")[0]
