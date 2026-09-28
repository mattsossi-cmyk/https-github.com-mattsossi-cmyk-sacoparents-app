"""Align Assistant: case brief buckets/steps + neutral system prompt guards (no LLM call)."""
import asyncio

from assistant import SYSTEM, TRIGGERS, _bucket, case_brief


def test_bucket_mapping() -> None:
    assert _bucket("Strong alignment") == "Agreed"
    assert _bucket("Moderate alignment") == "Minor Gap"
    assert _bucket("Needs discussion") == "High Discrepancy"


def test_system_prompt_guardrails() -> None:
    for phrase in ("Never recommend custody", "never judge credibility", "email only (no SMS)", "advisory only"):
        assert phrase in SYSTEM
    assert set(TRIGGERS) == {"invite", "review", "pathway", "report"}


def test_case_brief_steps_for_invited_case() -> None:
    doc = {"id": "brief-test-no-such-case", "case_code": "SA-TEST", "subject_label": "Education", "child_name": "Kid", "status": "invited", "kind": "joint_report",
           "participants": {"a": {"name": "A", "user_id": "u1"}, "b": {"name": "B"}}, "responses": {}}
    b = asyncio.run(case_brief(doc))
    assert b["case_status"] == "INVITED" and b["agreed_pct"] is None and b["report_status"] == "not_started"
    assert [s["state"] for s in b["steps"]] == ["active", "todo", "todo", "todo", "todo"]
    assert "⏳" in b["steps"][0]["detail"]
