"""Jev (TypeSafe) fast text decisions — review-gated helpers; never edits text, never decides custody/safety outcomes."""
import asyncio
import os
import re
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, RetryPolicy, Score, TypeSafeAPIError, TypeSafeError

from lens_data import CHILD_FOCUS_CATEGORIES

load_dotenv()
MODEL = "jev-latest"
_SEM = asyncio.Semaphore(3)


@lru_cache(maxsize=1)
def get_jev_client() -> AsyncTypeSafeClient:
    proxy = (os.getenv("INTEGRATION_PROXY_URL") or "https://integrations.emergentagent.com").rstrip("/")
    return AsyncTypeSafeClient(api_key=os.environ["EMERGENT_LLM_KEY"], base_url=f"{proxy}/llm/typesafe", retry=RetryPolicy(max_retries=2, respect_retry_after=False))


def jev_error_code(exc: TypeSafeAPIError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        code = (err.get("type") if isinstance(err, dict) else None) or body.get("code") or body.get("error_type") or str(err or "")
    else:
        code = str(body or exc).strip()
    known = {"CAPACITY_LIMIT", "USER_CONCURRENCY_LIMIT", "CONCURRENCY_REQUEST_LIMIT", "budget_exceeded"}
    return "RATE_LIMITED" if exc.status == 429 and code not in known else code


async def _ask(state, questions: dict):
    try:
        async with _SEM:
            return await get_jev_client().system_one(model=MODEL, state=state, questions=questions)
    except TypeSafeAPIError as exc:
        raise HTTPException(status_code=exc.status if exc.status < 500 else 502, detail={"code": jev_error_code(exc), "message": "Decision service error"})
    except TypeSafeError:
        raise HTTPException(status_code=503, detail={"code": "jev_unavailable", "message": "Decision service is busy, try again shortly."})


def sentences(text: str, limit: int = 40) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if len(p.strip()) > 12][:limit]


NEUTRALITY_ISSUES = {"none": "Neutral, procedural or descriptive; parent-reported framing preserved",
                     "custody_recommendation": "Recommends or implies who should have custody, possession or decision rights",
                     "diagnosis": "Assigns a mental-health diagnosis or clinical label to a parent or child",
                     "credibility_judgment": "States which parent is truthful, lying, exaggerating or believable",
                     "legal_conclusion": "Draws a legal conclusion or predicts how the court will or should rule",
                     "characterization": "Labels a parent as abusive, narcissistic, alienating, unstable or similar without citing a source"}


async def neutrality_check(fields: dict[str, str]) -> list[dict]:
    """Flags sentences in professional narrative fields that breach court-neutrality (warn-only)."""
    todo = [(k, s) for k, v in fields.items() for s in sentences(str(v or ""))]

    async def one(k, s):
        r = await _ask({"sentence": s, "context": "professional co-parenting report to a family court"},
                       {"issue": Choice(instructions="Which court-neutrality problem, if any, does this sentence contain?", criteria=NEUTRALITY_ISSUES)})
        c = r.choices["issue"]
        p_none = c.probabilities.get("none", 0.0)
        issue = max((k for k in c.probabilities if k != "none"), key=c.probabilities.get)
        return {"field": k, "sentence": s, "issue": issue, "confidence": round(1 - p_none, 2)}
    results = await asyncio.gather(*(one(k, s) for k, s in todo))
    return [x for x in results if x["confidence"] >= 0.6]


async def safety_language(text: str) -> dict:
    """Scores free text for threat / coercion / fear language. Surfaces the safety pathway; never a finding."""
    if not (text or "").strip():
        return {"level": "none", "score": 0.0, "ai_classified": False}
    r = await _ask({"text": text[:6000]}, {"safety": Score(instructions="How strongly does this text describe threats, intimidation, coercive control, stalking, physical harm or fear of the other parent?",
                                                            criteria=["none", "low", "moderate", "high"])})
    s = r.scores["safety"]
    level = max(s.probabilities, key=s.probabilities.get)
    return {"level": s.legend[level], "score": round(s.score, 2), "confidence": round(s.confidence, 2), "ai_classified": True}


async def blame_check(lines: list[str]) -> list[dict]:
    """Categorizes each concern line as child-focused vs blaming the other parent (nudge only)."""
    async def one(i, line):
        r = await _ask({"concern": line}, {"focus": Choice(instructions="Is this concern stated from the child's perspective, or does it blame or characterize the other parent?",
                                                            criteria={"child_focused": "Describes the child's need, experience or situation without attributing fault",
                                                                      "blaming": "Attributes fault, motive or character flaws to the other parent"})})
        c = r.choices["focus"]
        return {"index": i, "line": line, "focus": c.choice, "confidence": round(c.confidence, 2)}
    return list(await asyncio.gather(*(one(i, l) for i, l in enumerate([x for x in lines if x.strip()][:12]))))


async def child_focus_tags(text: str) -> list[dict]:
    """Suggests Child-Focused Issue categories from Joint Report text (professional accepts/rejects)."""
    qs = {k: Noul(instructions=f"Does the text raise an issue about the child's {label.lower()}?") for k, label in CHILD_FOCUS_CATEGORIES}
    r = await _ask({"joint_report_text": text[:8000]}, qs)
    return [{"key": k, "label": label, "probability": round(r.nouls[k].noul, 2), "suggested": r.nouls[k].noul >= 0.6} for k, label in CHILD_FOCUS_CATEGORIES]


TRIAGE = {"procedural": "Status updates, document requests, filings, general case administration",
          "scheduling": "Hearing dates, deadlines, appointments, availability",
          "urgent_safety": "Immediate risk to a child or parent, protective orders, emergencies"}


async def message_triage(text: str) -> dict | None:
    try:
        r = await _ask({"message": text[:3000]}, {"category": Choice(instructions="Which category best fits this court–professional message?", criteria=TRIAGE)})
    except HTTPException:
        return None
    c = r.choices["category"]
    return {"category": c.choice, "confidence": round(c.confidence, 2)}
