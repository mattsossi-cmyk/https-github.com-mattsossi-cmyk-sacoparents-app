"""Self Journey Card 4 · Foundation Statement builder — save-to-account +
branded PDF with signature lines. Separate from the reflection-based
Foundation Statement report in mediation_routes (left untouched).

Copy lives in `foundation_builder_content.json`, mirrored at
`frontend/src/pages/portal/foundationBuilderContent.json` (lockstep test:
tests/test_foundation_builder.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from auth import UserPublic, get_current_user, get_db
import foundation_builder_pdf

CONTENT: Dict[str, Any] = json.loads(
    (Path(__file__).parent / "foundation_builder_content.json").read_text(encoding="utf-8")
)
FIELD_KEYS = [f["key"] for f in CONTENT["fields"]]

router = APIRouter(prefix="/foundation-builder", tags=["foundation-builder"])


class FBFields(BaseModel):
    fields: Dict[str, str] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def clean(cls, v: Dict[str, str]) -> Dict[str, str]:
        return {k: (val or "")[:3000] for k, val in (v or {}).items() if k in FIELD_KEYS and isinstance(val, str)}


class FBState(FBFields):
    updated_at: Optional[str] = None


@router.get("/me", response_model=FBState)
async def get_my_statement(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> FBState:
    doc = await db.foundation_builder.find_one({"user_id": user.user_id}, {"_id": 0, "user_id": 0})
    return FBState(**doc) if doc else FBState()


@router.put("/me", response_model=FBState)
async def save_my_statement(
    body: FBFields,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> FBState:
    saved = FBState(fields=body.fields, updated_at=datetime.now(timezone.utc).isoformat())
    await db.foundation_builder.update_one(
        {"user_id": user.user_id}, {"$set": {**saved.model_dump(), "user_id": user.user_id}}, upsert=True
    )
    return saved


def _safe_filename(name: str) -> str:
    out = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in (name or "").strip())
    return out[:60] or "me"


class FBPdfIn(FBFields):
    esign_name: Optional[str] = Field(default=None, min_length=2, max_length=120)


@router.post("/pdf")
async def download_statement_pdf(body: FBPdfIn):
    """Public on purpose (localStorage-first portal). Optional typed e-signature for Parent 1."""
    if not any((v or "").strip() for v in body.fields.values()):
        raise HTTPException(400, "Write at least one part of your statement first.")
    esign = {"name": body.esign_name.strip(), "at": datetime.now(timezone.utc).isoformat()} if body.esign_name else None
    pdf_bytes = foundation_builder_pdf.build_foundation_builder_pdf(content=CONTENT, fields=body.fields, esign=esign)
    name = _safe_filename(body.fields.get("parent_names", ""))
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="SA_CoParents_Foundation_Statement_{name}.pdf"'},
    )
