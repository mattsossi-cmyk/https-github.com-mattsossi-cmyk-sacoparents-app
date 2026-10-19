"""Family check-in (owner spec 2026-10-16, amended 2026-10-18): 6-domain questionnaire, identical for every parent, with fixed transparent Red/Amber/Green rules.
No AI. Skipped items never raise a tier except: a skipped Red-weighted question makes the result at least Amber.
Owner 2026-10-18: former parts 3 (Strangulation and threats) and 4 (Weapons) removed from the live set (see LEGACY_ITEMS); mandatory-reporting sentence
removed from the intro pending the owner's decision (see MANDATORY_REPORTING_NOTE)."""

TF = ["Never", "More than 12 months ago", "In the last 12 months", "In the last month", "Prefer not to answer"]
RECENT = {"In the last 12 months", "In the last month"}
EVER = {"More than 12 months ago", "In the last 12 months", "In the last month"}
YN_PNA = ["Yes", "No", "Prefer not to answer"]
GATE = ["Yes, continue", "Not now (remind me in the app later)", "Quick exit"]
SAFE_HOME = ["Yes", "No", "Not sure", "Prefer not to answer"]

TITLE = "Family check-in"
# Owner (attorney) 2026-10-18 20:1x CDT: mandatory-reporting sentence restored to the live intro.
MANDATORY_REPORTING_NOTE = "If your answers suggest a child has been abused or neglected, the professional who reads them is required by law to report it (in Texas, any person must report)."
PRIVACY_NOTE = f"Only professionals assigned to your case see your answers. They are not shared with the other parent. {MANDATORY_REPORTING_NOTE}"
EMERGENCY = {"title": "If you are in danger right now", "lines": ["Call 911.", "National Domestic Violence Hotline: 1-800-799-7233, or text START to 88788."],
             "note": "You can continue the check-in or leave. Quick exit takes you to a neutral page."}
CLOSE_NOTE = "Thank you. Your check-in has been saved. You can update your answers at any time from your home screen."


def _q(i, text, kind, part, weight="info", stem=None, follow=None):
    return {"id": i, "text": text, "kind": kind, "part": part, "weight": weight, "stem": stem, "follow": follow, "tier3": weight == "red"}


P1, P2, P3, P4, P5, P6 = ("1 · Immediate safety", "2 · Physical violence", "3 · Coercive control and monitoring", "4 · Sexual violence", "5 · Children", "6 · Context")
ITEMS = [
    _q("gate", "Is it safe for you to answer these questions right now? Is anyone able to see your screen?", "gate", "Before you start"),
    _q("danger", "Are you or your children in danger right now?", "yn", P1, "red"),
    _q("safe_home", "Do you feel safe going home today?", "safe_home", P1, "red"),
    _q("pv", "Has the other parent pushed, hit, kicked, or physically hurt you?", "tf", P2, "amber"),
    _q("pv_worse", "Has it happened more often or got worse recently?", "yn", P2, "red", follow="pv"),
    _q("pv_medical", "Have you needed medical care because of it?", "yn", P2, "red", follow="pv"),
    _q("control", "Does the other parent control your money, phone, movements, or who you see?", "tf", P3, "amber"),
    _q("monitor", "Have they tracked your location, read your messages, or used apps or devices to watch you?", "tf", P3, "amber"),
    _q("stalk", "Have they followed you or shown up uninvited since you separated?", "tf", P3, "red"),
    _q("sexual", "Has the other parent pressured or forced you into sexual activity you did not want?", "tf", P4, "red"),
    _q("kids_saw", "Have the children seen or heard violence or threats?", "tf", P5, "amber"),
    _q("kids_hurt", "Has the other parent hurt or threatened the children?", "tf", P5, "red"),
    _q("kids_used", "Have they used the children to pass messages, spy, or threaten you?", "tf", P5, "amber"),
    _q("kids_worry", "Are you worried about the children's safety during parenting time?", "yn", P5, "amber"),
    _q("separated", "When did you separate (or plan to)?", "tf_sep", P6, "info"),
    _q("legal", "Are there current protective orders, police reports, or CPS involvement?", "yn", P6, "info"),
    _q("substance", "Does the other parent's drinking or drug use make things more dangerous?", "yn", P6, "amber"),
    _q("afraid", "Are you afraid of the other parent?", "yn", P6, "amber"),
    _q("free_text", "Is there anything else you want the professional to know?", "text", "Optional"),
]
# Removed from the live set by the owner (no lethality/danger-sign section 2026-10-06; no firearms questions 2026-10-14; applied 2026-10-18).
# Kept only so legacy records can be read; never served to parents.
LEGACY_ITEMS = [
    _q("strangle", "Has the other parent ever put their hands, arm or an object on your neck or blocked your breathing?", "tf", "Strangulation and threats", "red"),
    _q("threat_kill", "Have they threatened to kill you, your children, or themselves?", "tf", "Strangulation and threats", "red"),
    _q("weapon_access", "Does the other parent own or have easy access to a gun or other weapon?", "yn", "Weapons", "amber"),
    _q("weapon_used", "Have they used or threatened you with one?", "tf", "Weapons", "red"),
]
SEP = ["Not separated", "More than 12 months ago", "In the last 12 months", "In the last month", "Planning to", "Prefer not to answer"]
SCALES = {"tf": TF, "yn": YN_PNA, "gate": GATE, "safe_home": SAFE_HOME, "tf_sep": SEP}
SKIP = {"Prefer not to answer", "", None}
AMBER_TF = ("pv", "control", "monitor", "kids_saw", "kids_used")
RED_IDS = [i["id"] for i in ITEMS if i["weight"] == "red"]

SPEC = {"version": "FV", "title": TITLE, "intro": PRIVACY_NOTE, "source": None, "items": ITEMS,
        "emergency": EMERGENCY, "close_note": CLOSE_NOTE}

RULE_LABEL = {
    "danger_now": "Danger right now", "not_safe_home": "Does not feel safe going home", "pv_worse": "Physical violence worsening", "pv_medical": "Medical care needed",
    "strangulation": "Strangulation (ever)", "threat_kill": "Threat to kill", "weapon_used": "Weapon used or threatened", "stalking": "Followed / showed up since separation",
    "sexual": "Sexual violence", "kids_hurt": "Children hurt or threatened", "amber_cluster": "3+ Amber items in last 12 months with recent separation",
    "amber_recent": "Amber item in the last 12 months", "weapon_access": "Weapon access", "afraid": "Afraid of the other parent", "red_skipped": "A Red-weighted question was not answered",
    "kids_worry": "Worried about children during parenting time", "substance": "Substance use makes things more dangerous",
}  # strangulation / threat_kill / weapon_* labels kept only for legacy records


def compute(responses: dict) -> dict:
    """Fixed rules → {app_tier, tier (3/2/1), triggered_rules}. Transparent, no scoring, no AI."""
    r = {k: (v or "") for k, v in (responses or {}).items()}
    red, amber = [], []
    if r.get("danger") == "Yes": red.append("danger_now")
    if r.get("safe_home") == "No": red.append("not_safe_home")
    if r.get("pv_worse") == "Yes": red.append("pv_worse")
    if r.get("pv_medical") == "Yes": red.append("pv_medical")
    if r.get("stalk") in EVER: red.append("stalking")
    if r.get("sexual") in EVER: red.append("sexual")
    if r.get("kids_hurt") in EVER: red.append("kids_hurt")
    recent_amber = [i for i in AMBER_TF if r.get(i) in RECENT] + [i for i in ("kids_worry", "substance", "afraid") if r.get(i) == "Yes"]
    if len(recent_amber) >= 3 and r.get("separated") in RECENT: red.append("amber_cluster")
    if any(r.get(i) in RECENT for i in AMBER_TF) or r.get("kids_worry") == "Yes" or r.get("substance") == "Yes": amber.append("amber_recent")
    if r.get("afraid") == "Yes": amber.append("afraid")
    if any(r.get(i) in SKIP for i in RED_IDS): amber.append("red_skipped")
    if red:
        return {"app_tier": "red", "tier": 3, "triggered_rules": red}
    if amber:
        return {"app_tier": "amber", "tier": 2, "triggered_rules": amber}
    return {"app_tier": "green", "tier": 1, "triggered_rules": []}


APP_TIER_LABEL = {"red": "Red", "amber": "Amber", "green": "No concerns reported"}
