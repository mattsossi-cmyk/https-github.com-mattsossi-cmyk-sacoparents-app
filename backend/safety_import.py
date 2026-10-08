"""Extract a family-violence / safety screening from a sacoparentsapp.online export payload (neutral, non-adjudicative).

New structured format: payload["safety_screening"] = {version: "A"|"B"|"C", completed_at, tier, answered_count, responses: {...}}.
Legacy free-text formats (family_violence_assessment / titled assessment) are still accepted.
"""
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


def _date(v) -> str:
    """Safe YYYY-MM-DD (or '') from whatever the bridge sends: str, number, datetime, dict, None."""
    if v is None or isinstance(v, (dict, list, bool)):
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10]
    s = str(v).strip()
    if re.fullmatch(r"\d{10,13}(\.\d+)?", s):
        from datetime import datetime, timezone
        ts = float(s) / (1000 if len(s.split(".")[0]) == 13 else 1)
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    m = re.match(r"\d{4}-\d{2}-\d{2}", s)
    return m.group(0) if m else s[:10]


def _legacy(title: str, completed_at, resp: dict) -> dict:
    items = _items(resp)
    return {"source": SOURCE, "version": None, "tier": None, "title": title[:120] or "Family Violence / Safety Screening", "completed_at": _date(completed_at), "items": items,
            "responses": {i["question"]: i["answer"] for i in items}, "item_count": len(items), "answered_count": len(items), "concern_count": sum(i["concern"] for i in items)}


def _structured(s: dict) -> dict | None:
    from safety_screening import VERSIONS, build_record
    ver = str(s.get("version") or "").strip().upper()
    if ver not in VERSIONS or not isinstance(s.get("responses"), dict):
        return None
    tier = s.get("tier")
    try:
        tier = int(tier) if tier is not None else None
    except (TypeError, ValueError):
        tier = None
    ac = s.get("answered_count")
    from safety_pathway import normalize_import
    fl, pw = normalize_import(s.get("safety_flags"), s.get("safety_pathway"))
    rec = build_record(ver, s["responses"], source=SOURCE, completed_at=_date(s.get("completed_at")) or None, tier=tier, answered_count=ac if isinstance(ac, int) else None, flags=fl, pathway=pw)
    rec["items"] = []
    return rec


def extract_safety_screening(payload: dict) -> dict | None:
    """Returns the stored screening record, or None when the export has no screening."""
    if not isinstance(payload, dict):
        return None
    structured = payload.get("safety_screening")
    if isinstance(structured, dict):
        # bridge may place flags/pathway at top level or inside safety_screening
        structured = {**structured, "safety_flags": structured.get("safety_flags", payload.get("safety_flags")), "safety_pathway": structured.get("safety_pathway", payload.get("safety_pathway"))}
        rec = _structured(structured)
        if rec:
            return rec
    structured = payload.get("family_violence_assessment") or payload.get("safety_screening")
    if isinstance(structured, dict):
        resp = structured.get("responses") if isinstance(structured.get("responses"), dict) else {k: v for k, v in structured.items() if k not in ("title", "completed_at", "version", "tier", "answered_count")}
        return _legacy(str(structured.get("title") or "Family Violence / Safety Screening"), structured.get("completed_at"), resp)
    for a in payload.get("assessments") or []:
        if not isinstance(a, dict):
            continue
        title = str(a.get("title") or "")
        resp = a.get("responses") if isinstance(a.get("responses"), dict) else {}
        if _SAFETY_RE.search(title) or sum(1 for q in resp if _SAFETY_RE.search(str(q))) >= 2:
            return _legacy(title, a.get("completed_at"), resp)
    return None


def screening_summary(scr: dict | None, parent_label: str) -> str:
    """Court-safe one-liner: receipt, version, tier, date — never answer text, never a finding."""
    from safety_screening import receipt
    return receipt(scr, parent_label)
