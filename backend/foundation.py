"""Parent-authored Child-Focused Foundation Statement (collection: foundation_statements) + share-into-case."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

TEXT_FIELDS = ("child_name", "shared_purpose", "vision", "strengths", "child_may_need", "future", "parent_commitment")
LIST_FIELDS = ("priorities", "needs", "concerns", "wellness_tech", "commitments", "goals")
SECTIONS = [("shared_purpose", "Shared Purpose"), ("vision", "My Vision for My Child"), ("priorities", "Parenting Priorities"), ("strengths", "My Child's Strengths"), ("needs", "My Child's Current Needs"),
            ("concerns", "Areas of Concern"), ("wellness_tech", "Wellness, Phones & Social Media"), ("child_may_need", "What My Child May Need"), ("commitments", "Commitments I Am Making"), ("goals", "Goals for the Next 12 Months"), ("future", "My Child's Future"), ("parent_commitment", "Parent Commitment")]
PURPOSE = "This Foundation Statement organizes the parent's child-focused reflections into priorities, needs, concerns (including wellness, phones and social media), goals and personal commitments."


class FoundationIn(BaseModel):
    fields: dict
    safety: dict | None = None


def _lines(t) -> list:
    if isinstance(t, list):
        return [str(x).strip() for x in t if str(x).strip()]
    return [g.strip() for g in str(t or "").split("\n") if g.strip()]


def _clean(fields: dict) -> dict:
    out = {k: str(fields.get(k) or "").strip()[:4000] for k in TEXT_FIELDS}
    out.update({k: _lines(fields.get(k))[:12] for k in LIST_FIELDS})
    return out


def _complete(f: dict) -> bool:
    return all(f.get(k) for k in ("child_name", "shared_purpose", "vision", "parent_commitment")) and all(f.get(k) for k in ("priorities", "commitments"))


def _public(doc: dict) -> dict:
    from safety_gate import parent_safety_flag
    return {"id": doc["id"], "fields": doc["fields"], "safety": doc.get("safety") or {}, "safety_flagged": parent_safety_flag(doc), "safety_language": doc.get("safety_language"), "complete": _complete(doc["fields"]), "updated_at": doc.get("updated_at"), "created_at": doc.get("created_at")}


async def _language_screen(fields: dict) -> dict | None:
    """Jev safety-language score over the free text (surfaces the safety pathway; never a finding)."""
    try:
        from jev import safety_language
        return await safety_language(to_text(fields))
    except Exception:
        return None


def _clean_safety(safety: dict | None) -> dict:
    from safety_gate import FOUNDATION_SAFETY_QUESTIONS
    return {k: (safety or {}).get(k) for k, _ in FOUNDATION_SAFETY_QUESTIONS if isinstance((safety or {}).get(k), bool)}


def to_pdf_data(doc: dict, parent_name: str, is_sample: bool = False) -> dict:
    f = doc["fields"]
    child = f.get("child_name") or "my child"
    return {**f, "parent_name": parent_name, "child_name": child, "child_short": child.split(" ")[0], "statement_date": (doc.get("updated_at") or "")[:10], "purpose": PURPOSE, "is_sample": is_sample}


def to_text(f: dict) -> str:
    parts = []
    for k, label in SECTIONS:
        v = f.get(k)
        if v:
            parts.append(f"{label}:\n" + ("\n".join(f"- {x}" for x in v) if isinstance(v, list) else v))
    return "\n\n".join(parts)


def build_router(db, get_current_user, get_joint_report_doc, report_role) -> APIRouter:
    r = APIRouter()

    async def _mine(user):
        return await db.foundation_statements.find_one({"user_id": user["_id"]}, {"_id": 0})

    @r.get("/foundation/mine")
    async def get_mine(user=Depends(get_current_user)):
        from safety_gate import FOUNDATION_SAFETY_QUESTIONS
        doc = await _mine(user)
        return {"statement": _public(doc) if doc else None, "sections": SECTIONS, "safety_questions": [{"key": k, "text": t} for k, t in FOUNDATION_SAFETY_QUESTIONS]}

    @r.put("/foundation/mine")
    async def save_mine(body: FoundationIn, user=Depends(get_current_user)):
        now = datetime.now(timezone.utc).isoformat()
        doc = await _mine(user)
        fields = _clean(body.fields)
        safety = _clean_safety(body.safety) if body.safety is not None else (doc or {}).get("safety") or {}
        lang = await _language_screen(fields)
        if doc:
            await db.foundation_statements.update_one({"id": doc["id"]}, {"$set": {"fields": fields, "safety": safety, "safety_language": lang, "updated_at": now}})
            doc = {**doc, "fields": fields, "safety": safety, "safety_language": lang, "updated_at": now}
        else:
            doc = {"id": str(uuid.uuid4()), "user_id": user["_id"], "fields": fields, "safety": safety, "safety_language": lang, "created_at": now, "updated_at": now}
            await db.foundation_statements.insert_one(dict(doc))
        return {"statement": _public(doc)}

    @r.get("/foundation/mine/pdf")
    async def my_pdf(inline: int = 0, user=Depends(get_current_user)):
        from pdf_foundation import build_foundation_pdf
        doc = await _mine(user)
        if not doc:
            raise HTTPException(status_code=404, detail="You have not written a Foundation Statement yet")
        pdf = build_foundation_pdf(to_pdf_data(doc, user.get("name") or user["email"]))
        return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'{"inline" if inline else "attachment"}; filename="my-foundation-statement.pdf"'})

    @r.post("/joint/reports/{rid}/foundation/share")
    async def share_into_case(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        side = report_role(doc, user["_id"])
        if not side:
            raise HTTPException(status_code=403, detail="Only a parent on this case can share a Foundation Statement into it")
        from safety_gate import parent_safety_flag, SAFETY_ROUTE_NOTE, FOUNDATION_SAFETY_QUESTIONS
        mine = await _mine(user)
        if mine and len(mine.get("safety") or {}) < len(FOUNDATION_SAFETY_QUESTIONS):
            raise HTTPException(status_code=400, detail="Please answer the three safety questions before sharing your Foundation Statement")
        if parent_safety_flag(mine):
            await db.joint_reports.update_one({"id": rid}, {"$set": {f"responses.{side}.safety_route": True}})
            raise HTTPException(status_code=409, detail=SAFETY_ROUTE_NOTE)
        if not mine or not _complete(mine["fields"]):
            raise HTTPException(status_code=400, detail="Complete your Foundation Statement (child, shared purpose, vision, priorities, commitments and parent commitment) before sharing it")
        await db.joint_reports.update_one({"id": rid}, {"$set": _share_updates(doc, side, mine["fields"])})
        return {"ok": True, "side": side}

    @r.post("/joint/reports/{rid}/foundation/use-import")
    async def use_imported_statement(rid: str, user=Depends(get_current_user)):
        """Parent's explicit choice to include the Foundation Statement that the parent app sent for THEM (role from the case, never from the request)."""
        doc = await get_joint_report_doc(rid, user)
        side = report_role(doc, user["_id"])
        if not side:
            raise HTTPException(status_code=403, detail="Only a parent on this case can include a Foundation Statement in it")
        imp = (doc.get("foundation_imports") or {}).get(side)
        if not imp:
            raise HTTPException(status_code=404, detail="No Foundation Statement from the SA CoParents app is on file for you on this case")
        if case_side_safety_flagged(doc, side):
            from safety_gate import SAFETY_ROUTE_NOTE
            raise HTTPException(status_code=409, detail=SAFETY_ROUTE_NOTE)
        await db.joint_reports.update_one({"id": rid}, {"$set": _share_entry_updates(doc, side, import_share_entry(imp))})
        return {"ok": True, "side": side}

    return r


def case_side_safety_flagged(doc: dict, side: str) -> bool:
    return bool((doc.get("safety_flags") or {}).get(side) or ((doc.get("responses") or {}).get(side) or {}).get("safety_route"))


def import_share_entry(imp: dict) -> dict:
    """Shared-statement entry built from the stored import (server copy — the client never supplies the text)."""
    return {"title": imp.get("title") or "Child-Focused Foundation Statement", "content": str(imp.get("content") or "")[:5000], "structured": imp.get("structured"),
            "shared_at": datetime.now(timezone.utc).isoformat(), "source": imp.get("source") or "sacoparentsapp.online", "received_at": imp.get("received_at")}


def _share_updates(doc: dict, side: str, fields: dict) -> dict:
    """Mongo $set payload for sharing a Foundation Statement into a case (Foundation-kind cases also complete the side)."""
    entry = {"title": "Child-Focused Foundation Statement", "content": to_text(fields)[:5000], "structured": fields, "shared_at": datetime.now(timezone.utc).isoformat(), "source": "align"}
    return _share_entry_updates(doc, side, entry)


def _share_entry_updates(doc: dict, side: str, entry: dict) -> dict:
    if doc.get("kind") != "foundation":
        return {f"responses.{side}.foundation": [entry]}
    updates = {f"responses.{side}": {"answers": {}, "completed_at": entry["shared_at"], "foundation": [entry]}}
    if doc.get("responses", {}).get("b" if side == "a" else "a"):
        updates["status"] = "ready"
    return updates
