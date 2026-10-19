"""Version C (LGBTQ+ relationship self-assessment): content, tiering, import, and identity-leak guards in report/PDF projections."""
from datetime import datetime, timezone
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
    assert "version c" in text and "tier 3" not in text and "not started" in text  # review fix 2026-10-18: receipt carries no tier; "Not started" wording
    assert not any(w in text for w in IDENTITY_WORDS) and "frequently" not in text and "somewhat safe" not in text


def test_spec_export_matches_runtime():
    from safety_screening import spec_export
    spec = spec_export()
    # 2026-10-18: the bridge exports the single offered Family check-in (no weights/tiers) plus A/B/C as read-only legacy versions
    assert spec["offered"]["version"] == "FV" and [i["id"] for i in spec["offered"]["items"]] == [i["id"] for i in VERSIONS["FV"]["items"]]
    assert not any("tier3" in i or "weight" in i for i in spec["offered"]["items"]) and "tiers" not in spec
    assert set(spec["legacy_versions"]["versions"]) == {"A", "B", "C"} and spec["assignment"]["choice_screen"] is None
    for k, v in spec["legacy_versions"]["versions"].items():
        assert [i["id"] for i in v["items"]] == [i["id"] for i in VERSIONS[k]["items"]]
    assert spec["export_contract"]["field"] == "safety_screening" and "never a tier" in spec["export_contract"]["privacy"]


def test_screening_reminder_nudges_once_after_seven_days():
    import asyncio, os, uuid, logging
    from datetime import timedelta
    from motor.motor_asyncio import AsyncIOMotorClient
    from safety_screening import run_screening_reminders
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    sent = []

    async def fake_send(**kw):
        sent.append(kw)
        return "id"

    async def go():
        uid, rid = str(uuid.uuid4()), str(uuid.uuid4())
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        await db.users.insert_one({"_id": uid, "email": "qa.remind@example.com", "name": "Remind Me", "role": "parent"})
        await db.joint_reports.insert_one({"id": rid, "case_code": "SA-REM", "created_at": old, "participants": {"a": {"user_id": uid, "name": "R"}, "b": {"user_id": None, "name": "S"}}, "responses": {}})
        await db.invitations.insert_one({"report_id": rid, "role": "a", "status": "accepted", "accepted_at": old, "token": "t-" + rid})
        try:
            n1 = await run_screening_reminders(db, fake_send, lambda: "https://x.test", "SA", logging.getLogger("t"))
            n2 = await run_screening_reminders(db, fake_send, lambda: "https://x.test", "SA", logging.getLogger("t"))
            mine = [s for s in sent if s["case_id"] == rid]
            assert len(mine) == 1 and n2 == 0 and n1 >= 1
            assert mine[0]["to"] == "qa.remind@example.com" and "/safety-hub" in mine[0]["html"]  # reminder lands on the Safety hub (Start-with-Safety first)
            low = (mine[0]["subject"] + mine[0]["html"]).lower()
            assert "lgbtq" not in low and "women" not in low and "version" not in low
            doc = await db.joint_reports.find_one({"id": rid})
            assert doc["safety_reminded_at"]["a"]
        finally:
            await db.users.delete_one({"_id": uid}); await db.joint_reports.delete_one({"id": rid}); await db.invitations.delete_many({"report_id": rid})
    asyncio.run(go())
