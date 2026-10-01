"""Extract a family-violence / safety screening from a sacoparentsapp.online export payload (neutral, non-adjudicative)."""
import re

SOURCE = "sacoparentsapp.online"
_SAFETY_RE = re.compile(r"safety|family[\s_-]*violence|domestic|abuse|protective|intimate[\s_-]*partner|ipv|coerc|threat|fear|police|restrain", re.I)
_CONCERN_RE = re.compile(r"^\s*(yes|y|true|often|sometimes|frequently|always|occasionally|1|agree|strongly agree)\b", re.I)
MAX_ANSWER = 300


def _items(responses: dict) -> list[dict]:
    out = []
    for q, a in (responses or {}).items():
        text = str(a if a is not None else "").strip()
        if not text:
            continue
        out.append({"question": str(q)[:200], "answer": text[:MAX_ANSWER], "concern": bool(_CONCERN_RE.match(text))})
    return out


def extract_safety_screening(payload: dict) -> dict | None:
    """Returns {source, title, completed_at, items[], concern_count, item_count} or None when the export has no screening."""
    if not isinstance(payload, dict):
        return None
    structured = payload.get("family_violence_assessment") or payload.get("safety_screening")
    if isinstance(structured, dict):
        resp = structured.get("responses") if isinstance(structured.get("responses"), dict) else {k: v for k, v in structured.items() if k not in ("title", "completed_at")}
        items = _items(resp)
        return {"source": SOURCE, "title": str(structured.get("title") or "Family Violence / Safety Screening")[:120], "completed_at": structured.get("completed_at"),
                "items": items, "item_count": len(items), "concern_count": sum(i["concern"] for i in items)}
    for a in payload.get("assessments") or []:
        if not isinstance(a, dict):
            continue
        title = str(a.get("title") or "")
        resp = a.get("responses") if isinstance(a.get("responses"), dict) else {}
        if _SAFETY_RE.search(title) or sum(1 for q in resp if _SAFETY_RE.search(str(q))) >= 2:
            items = _items(resp)
            return {"source": SOURCE, "title": title[:120] or "Family Violence / Safety Screening", "completed_at": a.get("completed_at"), "items": items,
                    "item_count": len(items), "concern_count": sum(i["concern"] for i in items)}
    return None


def screening_summary(scr: dict | None, parent_label: str) -> str:
    """Court-safe one-liner: receipt + counts only, never answer text, never a finding."""
    if not scr:
        return f"{parent_label}: no imported safety screening on file."
    date = (scr.get("completed_at") or "")[:10]
    when = f" completed {date}" if date else ""
    return (f"{parent_label}: safety screening received from {scr['source']}{when} — {scr['item_count']} screening items; "
            f"{scr['concern_count']} item(s) indicated a concern for professional follow-up. Screening responses are parent-reported and are not findings.")
