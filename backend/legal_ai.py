"""AI-assisted draft for the Professional Legal Lens section (drafting aid only; rule-based fallback)."""
import json
import logging
import os

logger = logging.getLogger("legal_ai")

AI_LABEL = "AI-ASSISTED DRAFT — PROFESSIONAL REVIEW REQUIRED"

SYSTEM = """You are assisting an authorized professional in preparing a draft SA CoParents Align Professional Legal Report.
You are an organizational and drafting tool. You are NOT the final decision-maker.
RULES:
1. Distinguish parent-reported information from verified facts.
2. Never convert an allegation into a finding of fact.
3. Do not diagnose a parent or child.
4. Do not characterize a person as abusive, narcissistic, alienating, unstable, dangerous, deceptive, or mentally ill unless accurately summarizing a specifically identified source.
5. Describe disagreements neutrally. AVOID: "The father refuses to cooperate." USE: "Parent A reports difficulty obtaining timely responses concerning school-related decisions."
6. Identify areas of agreement separately from areas of disagreement.
7. Focus on the child's practical needs.
8. Do not make legal conclusions. 9. Do not predict how a judge will rule. 10. Do not recommend a custody outcome.
11. Options and resources may be identified, but the professional must independently determine whether they are appropriate.
12. Any professional-analysis section you generate must begin: "AI-Assisted Draft — Professional Review Required".
13. Safety-related information must be handled according to the professional's access permissions.
14. Do not suggest joint communication, mediation, or other direct interaction without acknowledging known safety concerns when they exist.
15. Use neutral, professional, court-appropriate language.
Return ONLY JSON with keys: professional_observations, issues_requiring_attention, existing_agreements, agreement_building_opportunities, procedural_considerations. Each value is 2-4 sentences."""

LENS_KEYS = ("professional_observations", "issues_requiring_attention", "existing_agreements", "agreement_building_opportunities", "procedural_considerations")


def rule_based_lens(draft: dict) -> dict:
    j = draft["joint"]
    n_al, n_df = len(j["alignment"]), len(j["differences"])
    safety = " Known safety-related subjects are present; any option involving direct interaction should be considered in light of those concerns." if draft["safety_notice"] else ""
    return {
        "professional_observations": f"{AI_LABEL}. Parent-reported information shows {n_al} area(s) of alignment and {n_df} area(s) of difference in the joint assessment. Both parents identified child-focused priorities; disagreements are described in the parents' own framing and are not verified facts.{safety}",
        "issues_requiring_attention": f"{AI_LABEL}. " + (" ".join(j["unresolved"][:3]) if j["unresolved"] else "No unresolved areas were identified in the available records."),
        "existing_agreements": f"{AI_LABEL}. " + (" ".join(j["alignment"][:3]) if j["alignment"] else "No completed Joint Assessment was available at the time this draft was generated."),
        "agreement_building_opportunities": f"{AI_LABEL}. " + (" ".join(j["potential_agreement"][:3]) if j["potential_agreement"] else "Potential areas for agreement could not be identified from the available records."),
        "procedural_considerations": f"{AI_LABEL}. Records reviewed are listed in Section 3. Parent-reported statements remain identified as parent-reported information. The professional determines which options, if any, are appropriate.",
    }


MODELS = {"gemini": ("gemini", "gemini-3.1-pro-preview", "Gemini 3.1 Pro"), "openai": ("openai", "gpt-5.4-mini", "GPT-5.4 Mini"), "claude": ("anthropic", "claude-sonnet-4-6", "Claude Sonnet 4.6")}
DEFAULT_MODEL = "gemini"
LENS_REPORT_KEYS = ("safety_takeaway", "parent_a_growth", "parent_b_growth", "joint_notes", "shared_concerns", "pathway_rationale", "conflict_management_rationale", "short_term_goals", "long_term_goals")
LENS_REPORT_SYSTEM = SYSTEM.split("Return ONLY JSON")[0] + (
    "You are drafting narrative sections of the SA CoParents Align Professional Evaluation Report from the structured report data provided (1-10 ratings, classifications, "
    "prefilled strengths/gaps, risk screening levels, resource rows and the recommended conflict-resolution pathway). Ratings describe the co-parenting context, never fitness or credibility. "
    "Return ONLY JSON with keys: safety_takeaway, parent_a_growth, parent_b_growth, joint_notes, shared_concerns, pathway_rationale, conflict_management_rationale, short_term_goals, long_term_goals. pathway_rationale must explain WHY a pathway fits the type of conflict identified (communication-based, defined parenting disagreement, subject-matter disagreement, persistent high conflict, safety concern). "
    "parent_a_growth and parent_b_growth are exactly 3 newline-separated 'Key Growth Areas' starting with 'Focus on'; short_term_goals and long_term_goals are 3-4 newline-separated "
    "goals in the form 'Title: concrete action'; other values are 2-4 sentences.")


def _label(v: str) -> str:
    return v if v.lower().startswith("ai-assisted draft") else f"{AI_LABEL}. {v}"


def _v(rep: dict, key: str, default: str = "not yet recorded") -> str:
    return str(rep.get(key) or default)


def rule_based_lens_report(rep: dict, cls: dict) -> dict:
    j = cls.get("joint") or {}
    lbl = f"joint rating {rep.get('joint_rating')} ({j.get('label')}, {j.get('mode')})" if j else "no joint rating entered yet"
    guidance = ", ".join(j.get("guidance") or []) or "enter a joint rating for guidance"
    pathway = (j.get("pathway") or {}).get("name") or "to be selected"
    risk = ", ".join(f"{k.replace('_', ' ')}: {d.get('level')}" for k, d in (rep.get("risk_screening") or {}).items() if isinstance(d, dict)) or "not yet recorded"
    return {k: _label(v) for k, v in {
        "safety_takeaway": f"Risk screening summary — {risk}. Whether an emergency safety override or restriction on direct negotiation is needed is for the professional to state after review; no allegation is treated as a verified finding.",
        "parent_a_growth": "Focus on sending calm, strictly factual messages instead of reactive replies.\nFocus on sharing child information openly and early.\nFocus on separating personal feelings about the other parent from that parent's role with the child.",
        "parent_b_growth": "Focus on being consistently on time for all scheduled transitions.\nFocus on keeping written messages brief, clear, and non-repetitive.\nFocus on accessing school and medical information independently.",
        "joint_notes": f"The Joint Report reflects {lbl}. Areas where the parents do well together: {_v(rep, 'joint_strengths')}. Areas of difficulty: {_v(rep, 'joint_gaps')}. These statements are parent-reported and are not verified findings.",
        "conflict_management_rationale": f"Recommended pathway for this rating band: {pathway}. Neutral guidance suggests: {guidance}. Safety screening, court orders and the child's needs remain controlling.",
        "short_term_goals": "Transition Handoff Protocol: Shift transitions to neutral locations or school pickup/drop-off; keep greetings brief.\nApp-Only Communication Window: Move all non-emergency messaging to SA CoParents Align with a defined response window.\nShared Information Access: Both parents hold direct login access to school and medical portals.",
        "long_term_goals": "Step Down Monitoring: Reduce facilitator check-ins from weekly to monthly as promptness and calm messaging hold.\nFlexible Schedule Swaps: After 90 days of consistency, introduce a structured Right of First Refusal policy.\nUnified Two-Household Expectations: Complete parent education to align major household rules across homes.",
    }.items()}


async def draft_lens_report(rep: dict, cls: dict, session_id: str, model: str = DEFAULT_MODEL) -> tuple[dict, str, str]:
    """Drafts Legal Lens narrative fields. Returns (fields, source 'ai'|'rule_based', model label)."""
    provider, name, label = MODELS.get(model) or MODELS[DEFAULT_MODEL]
    fallback = rule_based_lens_report(rep, cls)
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return fallback, "rule_based", label
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=f"legal-lens-report-{session_id}", system_message=LENS_REPORT_SYSTEM).with_model(provider, name)
        skip = ("id", "case_id", "professional_id", "joint_report_id", "parent_a_assessment_id", "parent_b_assessment_id", "created_at", "updated_at", "signature_name")
        payload = {"report": {k: v for k, v in rep.items() if k not in skip and v not in ("", None, [])}, "classification": cls}
        text = (await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False)))).strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[1] if "\n" in text else text.strip("`")
            text = text.removeprefix("json").strip()
        data = json.loads(text)
        out = {k: _label(str(data.get(k, "")).strip()) for k in LENS_REPORT_KEYS if str(data.get(k, "")).strip()}
        if len(out) < len(LENS_REPORT_KEYS):
            return {**fallback, **out}, "ai", label
        return out, "ai", label
    except Exception as exc:
        logger.warning("legal lens report AI drafting unavailable (%s): %s", name, exc)
        return fallback, "rule_based", label


async def draft_lens(draft: dict, session_id: str) -> tuple[dict, str]:
    """Returns (lens_fields, source) where source is 'ai' or 'rule_based'."""
    fallback = rule_based_lens(draft)
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return fallback, "rule_based"
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=f"legal-lens-{session_id}", system_message=SYSTEM).with_model("openai", "gpt-5.4-mini")
        payload = {k: draft[k] for k in ("parent_a_summary", "parent_b_summary", "joint", "child_focused_summary", "communication_summary", "safety_notice")}
        text = await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False)))
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[1] if "\n" in text else text.strip("`")
            text = text.removeprefix("json").strip()
        data = json.loads(text)
        out = {}
        for k in LENS_KEYS:
            v = str(data.get(k, "")).strip()
            if not v:
                return fallback, "rule_based"
            out[k] = v if v.lower().startswith("ai-assisted draft") else f"{AI_LABEL}. {v}"
        return out, "ai"
    except Exception as exc:
        logger.warning("legal lens AI drafting unavailable: %s", exc)
        return fallback, "rule_based"
