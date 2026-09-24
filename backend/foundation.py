"""Parent-authored Child-Focused Foundation Statement (collection: foundation_statements) + share-into-case."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

TEXT_FIELDS = ("child_name", "shared_purpose", "vision", "strengths", "child_may_need", "future", "parent_commitment")
LIST_FIELDS = ("priorities", "needs", "concerns", "commitments", "goals")
SECTIONS = [("shared_purpose", "Shared Purpose"), ("vision", "My Vision for My Child"), ("priorities", "Parenting Priorities"), ("strengths", "My Child's Strengths"), ("needs", "My Child's Current Needs"),
            ("concerns", "Areas of Concern"), ("child_may_need", "What My Child May Need"), ("commitments", "Commitments I Am Making"), ("goals", "Goals for the Next 12 Months"), ("future", "My Child's Future"), ("parent_commitment", "Parent Commitment")]
PURPOSE = "This Foundation Statement organizes the parent's child-focused reflections into priorities, needs, concerns, goals and personal commitments."


class FoundationIn(BaseModel):
    fields: dict


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
    return {"id": doc["id"], "fields": doc["fields"], "complete": _complete(doc["fields"]), "updated_at": doc.get("updated_at"), "created_at": doc.get("created_at")}


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
        doc = await _mine(user)
        return {"statement": _public(doc) if doc else None, "sections": SECTIONS}

    @r.put("/foundation/mine")
    async def save_mine(body: FoundationIn, user=Depends(get_current_user)):
        now = datetime.now(timezone.utc).isoformat()
        doc = await _mine(user)
        fields = _clean(body.fields)
        if doc:
            await db.foundation_statements.update_one({"id": doc["id"]}, {"$set": {"fields": fields, "updated_at": now}})
            doc = {**doc, "fields": fields, "updated_at": now}
        else:
            doc = {"id": str(uuid.uuid4()), "user_id": user["_id"], "fields": fields, "created_at": now, "updated_at": now}
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
        mine = await _mine(user)
        if not mine or not _complete(mine["fields"]):
            raise HTTPException(status_code=400, detail="Complete your Foundation Statement (child, shared purpose, vision, priorities, commitments and parent commitment) before sharing it")
        entry = {"title": "Child-Focused Foundation Statement", "content": to_text(mine["fields"])[:5000], "structured": mine["fields"], "shared_at": datetime.now(timezone.utc).isoformat(), "source": "align"}
        if doc.get("kind") == "foundation":
            updates = {f"responses.{side}": {"answers": {}, "completed_at": entry["shared_at"], "foundation": [entry]}}
            if doc.get("responses", {}).get("b" if side == "a" else "a"):
                updates["status"] = "ready"
            await db.joint_reports.update_one({"id": rid}, {"$set": updates})
        else:
            await db.joint_reports.update_one({"id": rid}, {"$set": {f"responses.{side}.foundation": [entry]}})
        return {"ok": True, "side": side}

    return r
