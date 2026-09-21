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


MODELS = {"gemini": ("gemini", "gemini-3.1-pro-preview", "Gemini 3.1 Pro"), "openai": ("openai", "gpt-5.4-mini", "GPT-5.4 Mini")}
DEFAULT_MODEL = "gemini"
LENS_REPORT_KEYS = ("joint_notes", "alignment_summary", "conflict_management_rationale", "short_term_goals", "long_term_goals", "professional_summary")
LENS_REPORT_SYSTEM = SYSTEM.split("Return ONLY JSON")[0] + (
    "You are drafting narrative sections of the SA CoParents Legal Lens Review and Report to Court from the structured report data provided (ratings, classifications, "
    "prefilled strengths/gaps, alignment lists, selected resources and conflict-management options). Ratings describe the co-parenting context, never fitness or credibility. "
    "Return ONLY JSON with keys: joint_notes, alignment_summary, conflict_management_rationale, short_term_goals, long_term_goals, professional_summary. "
    "short_term_goals and long_term_goals are newline-separated concrete goals (3-4 lines each); other values are 3-5 sentences.")


def _label(v: str) -> str:
    return v if v.lower().startswith("ai-assisted draft") else f"{AI_LABEL}. {v}"


def _v(rep: dict, key: str, default: str = "not yet recorded") -> str:
    return str(rep.get(key) or default)


def rule_based_lens_report(rep: dict, cls: dict) -> dict:
    j = cls.get("joint") or {}
    lbl = f"joint rating {rep.get('joint_rating')} ({j.get('label')}, {j.get('mode')})" if j else "no joint rating entered yet"
    opts = ", ".join(rep.get("conflict_management_options") or []) or "no conflict-management approach selected yet"
    guidance = ", ".join(j.get("guidance") or []) or "enter a joint rating for guidance"
    return {k: _label(v) for k, v in {
        "joint_notes": f"The Joint Report reflects {lbl}. Areas where the parents do well together: {_v(rep, 'joint_strengths')}. Areas of difficulty: {_v(rep, 'joint_gaps')}. These statements are parent-reported and are not verified findings.",
        "alignment_summary": f"Aligned areas: {_v(rep, 'alignment_agreements', 'none recorded')}. Non-aligned areas: {_v(rep, 'alignment_disagreements', 'none recorded')}. Partial alignment: {_v(rep, 'partial_alignment', 'none recorded')}. This summary does not determine which parent's position is correct.",
        "conflict_management_rationale": f"Selected approaches: {opts}. Neutral guidance for this rating band suggests: {guidance}. Safety screening, court orders and the child's needs remain controlling.",
        "short_term_goals": "Adopt a single written communication channel with a defined response window.\nComplete the selected individual resources.\nSchedule the first session of the selected conflict-management approach.",
        "long_term_goals": "Reach a written co-parenting agreement on the non-aligned areas.\nMaintain or improve the joint co-parenting rating at reassessment.\nReduce court involvement in routine decisions.",
        "professional_summary": f"This report documents review of both individual assessments, family violence screenings ({_v(rep, 'fv_a_received', 'pending')} / {_v(rep, 'fv_b_received', 'pending')}) and the Joint Report, with individual ratings {_v(rep, 'parent_a_rating', '–')} and {_v(rep, 'parent_b_rating', '–')} and {lbl}. It contains no custody recommendation, credibility determination, diagnosis or legal conclusion.",
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
