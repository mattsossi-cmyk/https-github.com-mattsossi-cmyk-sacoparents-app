from joint_data import AGREEMENT_DISCLAIMER, AGREEMENT_LEGAL_NOTICE_HEADING, agreement_legal_notice

"""Maps a ready Co-Parenting Agreement case into the 16-section 'Child-Focused Co-Parenting Agreement' model (PDF + court card)."""
from joint_engine import generate_agreement

TBD = "To be discussed by the parents."
CONFLICT_STEPS = [("Step 1", "Parent-to-parent discussion"), ("Step 2", "Structured written communication"), ("Step 3", "Communication or co-parenting tool"), ("Step 4", "Professional consultation"), ("Step 5", "Child-focused mediation"), ("Step 6", "Legal process if necessary")]
OPTIONS = ["BIFF communication principles.", "SA CoParents Communication Coach.", "Structured co-parenting applications.", "Parent education programs.", "Child-focused mediation.", "Parenting facilitator or other professional assistance when appropriate."]
SHARED_COMMITMENT = ["We recognize that successful co-parenting does not require us to agree on every issue.", "Our goal is to understand our child's needs, identify areas where we can align, establish clear expectations, and use constructive methods to address future disagreements."]
_INFO_WORDS = ("share", "record", "portal", "inform", "notice", "update", "report card", "appointment")


def _structured(doc: dict) -> list:
    return [s["structured"] for side in ("a", "b") for s in (doc.get("responses", {}).get(side) or {}).get("foundation") or [] if isinstance(s.get("structured"), dict)]


def _union(structs: list, key: str) -> list:
    seen, out = set(), []
    for st in structs:
        for x in (st.get(key) or []) if isinstance(st.get(key), list) else ([st.get(key)] if st.get(key) else []):
            k = x.strip().lower().rstrip(".")
            if k and k not in seen:
                seen.add(k)
                out.append(x.strip())
    return out


def _sec(rep: dict, key: str) -> dict:
    return next((s for s in rep.get("sections") or [] if s["key"] == key), {})


def _clean(x: str) -> str:
    """Drop the follow-up question prefix ('Where do exchanges happen?: At school' -> 'At school')."""
    if "?" in x:
        head, _, tail = x.partition("?")
        tail = tail.lstrip(": ").strip()
        if tail:
            return tail[0].upper() + tail[1:]
    return x


def _agreed(rep: dict, *keys: str) -> list:
    out = []
    for k in keys:
        out += [_clean(x) for x in _sec(rep, k).get("specific_agreements") or []]
    return out


def _first(items: list) -> str:
    return items[0] if items else TBD


def _short_open(x: str) -> str:
    label, _, rest = x.partition(": ")
    q = rest.split("?")[0].strip()
    return f"{label} — {q[0].lower() + q[1:]}" if q and rest else label


def court_agreement_model(doc: dict, safety: dict | None = None) -> dict:
    from safety_gate import apply_parallel
    return apply_parallel(_base_model(doc), safety or {})


def _base_model(doc: dict) -> dict:
    rep = generate_agreement(doc)
    structs = _structured(doc)
    sm = rep.get("summary") or {"alignment": [], "specific": [], "resolution": []}
    return {**_identity(doc, rep), **_needs(rep, sm), **_practical(rep), **_wellness(rep, structs), **_conflict_and_commitments(rep, structs), **_appendix(rep, sm)}


def _identity(doc: dict, rep: dict) -> dict:
    return {"title": "Child-Focused Co-Parenting Agreement", "subtitle": "Turning shared priorities, child needs and parent commitments into practical co-parenting agreements.",
            "parent_a_name": rep["parent_a_name"], "parent_b_name": rep["parent_b_name"], "child_name": rep["child_name"], "date": rep["date"], "case_code": doc.get("case_code") or "",
            "purpose": "This agreement builds from the parents' Foundation Statements and identifies practical ways the parents intend to support their child's emotional, educational, medical and developmental needs.",
            "shared_commitment": SHARED_COMMITMENT, "disclaimer": AGREEMENT_DISCLAIMER, "legal_notice_heading": AGREEMENT_LEGAL_NOTICE_HEADING, "legal_notice": agreement_legal_notice()}


def _needs(rep: dict, sm: dict) -> dict:
    aligned = list(dict.fromkeys(x.partition(":")[0].strip() for x in sm["alignment"]))
    fnd = _sec(rep, "foundation")
    return {"shared_purpose": [_clean(x) for x in (fnd.get("current_alignment") or []) + _agreed(rep, "foundation")] or [fnd.get("shared_goal") or TBD],
            "needs_aligned": aligned or [TBD], "needs_open": [_short_open(x) for x in sm["resolution"]] or ["None identified — every answered item is aligned."]}


def _practical(rep: dict) -> dict:
    comm, rev = _sec(rep, "communication"), _sec(rep, "review")
    info = [x for x in _agreed(rep, "education", "medical", "communication") if any(w in x.lower() for w in _INFO_WORDS)]
    return {"communication": _agreed(rep, "communication") or [TBD],
            "communication_choices": [("Primary Method", comm.get("communication_method") or TBD), ("Decision Process", comm.get("decision_process") or _sec(rep, "decisions").get("decision_process") or TBD),
                                      ("Open Items", _first(comm.get("open_issues") or []) if comm.get("open_issues") else "None")],
            "transitions": _agreed(rep, "transitions") or [TBD],
            "routines": [("Emotional Continuity", _first(_agreed(rep, "psychological"))), ("School", _first(_agreed(rep, "education"))), ("Activities", _first(_agreed(rep, "activities")))],
            "information": info or [TBD], "education": _agreed(rep, "education") or [TBD], "medical": _agreed(rep, "medical", "psychological") or [TBD],
            "review": _agreed(rep, "review") or [TBD],
            "review_choices": [("Review Trigger", rev.get("review_trigger") or TBD), ("Review Frequency", "Every 6 or 12 months"), ("Earlier Review", "If significant circumstances change")]}


def _wellness(rep: dict, structs: list) -> dict:
    sec = _sec(rep, "wellness_tech")
    return {"wellness": _agreed(rep, "wellness_tech") or [TBD],
            "wellness_choices": [("Communication of Concerns", sec.get("communication_method") or TBD), ("Decision Process", sec.get("decision_process") or TBD),
                                 ("Open Items", _first(sec.get("open_issues") or []) if sec.get("open_issues") else "None")],
            "wellness_foundation": _union(structs, "wellness_tech")}


def _conflict_and_commitments(rep: dict, structs: list) -> dict:
    diff = _sec(rep, "differences")
    return {"conflict_intro": diff.get("shared_goal") or "When a disagreement occurs, we will try to resolve it at the lowest appropriate level.",
            "conflict_agreed": _agreed(rep, "differences"), "conflict_steps": CONFLICT_STEPS, "options": OPTIONS,
            "strengths": _union(structs, "strengths") or [TBD], "commitments": _union(structs, "commitments") or [TBD], "goals": _union(structs, "goals") or [TBD]}


def _appendix(rep: dict, sm: dict) -> dict:
    return {"foundation_statements": [{"parent": f["parent"], "title": f["title"], "content": f["content"]} for f in rep.get("foundation_statements") or []],
            "counts": {"alignment": len(sm["alignment"]), "specific": len(sm["specific"]), "resolution": len(sm["resolution"])},
            "statuses": [(s["label"], s["status"]) for s in rep.get("sections") or []]}


def court_agreement_card(doc: dict, safety: dict | None = None) -> dict:
    """Neutral, judge-facing snapshot (no per-parent answers)."""
    m = court_agreement_model(doc, safety)
    return {"case_code": m["case_code"], "child_name": m["child_name"], "date": m["date"], "counts": m["counts"], "statuses": m["statuses"], "needs_aligned": m["needs_aligned"][:8], "needs_open": m["needs_open"][:8],
            "safety_override": m.get("safety_override")}
