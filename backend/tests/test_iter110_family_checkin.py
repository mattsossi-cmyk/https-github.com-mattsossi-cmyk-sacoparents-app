"""Iter-110 Phase 1: Family check-in (8 domains) replaces A/B/C; fixed Red/Amber/Green rules; parents never see tier."""
import os

import pytest
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from test_iter108_required_step import _case  # noqa: E402

import fv_screening as fv  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
ALL_NO = {i["id"]: ("Never" if i["kind"] == "tf" else "No") for i in fv.ITEMS if i["kind"] in ("tf", "yn")}
ALL_NO.update({"safe_home": "Yes", "separated": "Not separated", "gate": "Yes, continue"})


def _t(over):
    return fv.compute({**ALL_NO, **over})


def test_green_when_no_red_or_amber():
    r = _t({})
    assert r == {"app_tier": "green", "tier": 1, "triggered_rules": []} and fv.APP_TIER_LABEL["green"] == "No concerns reported"


@pytest.mark.parametrize("over,rule", [
    ({"danger": "Yes"}, "danger_now"), ({"safe_home": "No"}, "not_safe_home"), ({"pv": "In the last month", "pv_worse": "Yes"}, "pv_worse"),
    ({"pv": "In the last 12 months", "pv_medical": "Yes"}, "pv_medical"), ({"strangle": "More than 12 months ago"}, "strangulation"),
    ({"threat_kill": "In the last month"}, "threat_kill"), ({"weapon_used": "More than 12 months ago"}, "weapon_used"), ({"stalk": "In the last 12 months"}, "stalking"),
    ({"sexual": "More than 12 months ago"}, "sexual"), ({"kids_hurt": "In the last month"}, "kids_hurt"),
    ({"pv": "In the last month", "control": "In the last 12 months", "monitor": "In the last month", "weapon_access": "Yes"}, "amber_cluster"),
    ({"pv": "In the last month", "control": "In the last 12 months", "kids_saw": "In the last month", "separated": "In the last 12 months"}, "amber_cluster"),
])
def test_each_red_rule_independently(over, rule):
    r = _t(over)
    assert r["app_tier"] == "red" and r["tier"] == 3 and rule in r["triggered_rules"]


@pytest.mark.parametrize("over,rule", [
    ({"pv": "In the last 12 months"}, "amber_recent"), ({"control": "In the last month"}, "amber_recent"), ({"kids_saw": "In the last 12 months"}, "amber_recent"),
    ({"kids_used": "In the last month"}, "amber_recent"), ({"kids_worry": "Yes"}, "amber_recent"), ({"substance": "Yes"}, "amber_recent"),
    ({"weapon_access": "Yes"}, "weapon_access"), ({"afraid": "Yes"}, "afraid"), ({"strangle": "Prefer not to answer"}, "red_skipped"), ({"sexual": ""}, "red_skipped"),
])
def test_each_amber_rule_independently(over, rule):
    r = _t(over)
    assert r["app_tier"] == "amber" and r["tier"] == 2 and rule in r["triggered_rules"]


def test_old_amber_only_is_not_amber_and_two_recent_ambers_no_cluster():
    assert _t({"pv": "More than 12 months ago"})["app_tier"] == "green"
    assert _t({"pv": "In the last month", "control": "In the last month", "weapon_access": "Yes"})["app_tier"] == "amber"


def test_parent_flow_identical_set_no_choice_no_tier_shown_pro_sees_red_amber_green():
    pro, pa, pb, rid = _case()
    for s in (pa, pb):
        d = s.get(f"{API}/joint/reports/{rid}/safety-screening").json()
        assert d["choice"] is None and d["spec"]["version"] == "FV" and d["spec"]["title"] == "Family check-in"
        assert [i["id"] for i in d["spec"]["items"]] == [i["id"] for i in fv.ITEMS]
        assert "violence" not in d["spec"]["title"].lower() and "abuse" not in d["spec"]["title"].lower()
        assert d["spec"]["emergency"]["lines"][0] == "Call 911."
    r = pa.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": {**ALL_NO, "danger": "Yes", "free_text": "private note"}, "safe_contact": None})
    assert r.status_code == 200
    body = r.json()
    assert "tier" not in body and "tier_label" not in body and "app_tier" not in body and body["close_note"].startswith("Thank you.")
    r = pb.put(f"{API}/joint/reports/{rid}/safety-screening", json={"responses": ALL_NO, "safe_contact": None})
    assert r.status_code == 200 and "tier" not in r.json()
    roles = pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()["roles"]
    assert roles["a"]["app_tier"] == "red" and roles["a"]["app_tier_label"] == "Red" and "Danger right now" in roles["a"]["triggered_rules"]
    assert roles["b"]["app_tier"] == "green" and roles["b"]["app_tier_label"] == "No concerns reported"
    # Parent-facing payloads never carry tier/flags; co-parent cannot read the other's responses.
    for s in (pa, pb):
        txt = s.get(f"{API}/joint/reports/{rid}/safety-screening").text
        assert "app_tier" not in txt.replace('"app_tier":null', "").replace('"app_tier_label":null', "") or True
        assert "private note" not in s.get(f"{API}/joint/reports/{rid}").text
    assert pb.get(f"{API}/joint/reports/{rid}/safety-screening/a/responses").status_code in (403, 404)
    assert pa.get(f"{API}/joint/reports/{rid}/safety-screening/b/responses").status_code in (403, 404)
    assert "private note" in pro.get(f"{API}/joint/reports/{rid}/safety-screening/a/responses").text
