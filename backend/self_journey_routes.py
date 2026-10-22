"""Self Journey guide (/self-journey/:step): one private progress doc per parent.

Nothing here is exported, shared, emailed, printed by another feature or sent to the AI. The safety pick
("clear" / "concern") is the parent's own choice after their SACOparentsAlign Family check-in; it only shapes
which steps the guide shows them.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator

from auth import UserPublic, get_current_user, get_db

router = APIRouter(prefix="/self-journey", tags=["self-journey"])
_COLL = "self_journey_progress"
_TEXT = 3000
LAST_STEP = 7  # safety, situation, self-assessment, coparenting, child-needs, foundation, mediation, summary

SITUATION_KEYS = {"currentSituation", "topConcerns", "workingWell", "toImprove"}
FOUNDATION_KEYS = {"childNeedsMost", "values", "stability", "commitments", "success"}
MEDIATION_KEYS = {"issues", "childConcerns", "options", "flexibility", "questions", "boundaries"}


def _keep(allowed: set, v: Dict[str, str]) -> Dict[str, str]:
    return {k: val[:_TEXT] for k, val in (v or {}).items() if k in allowed and isinstance(val, str)}


class Safety(BaseModel):
    status: Literal["none", "clear", "concern"] = "none"
    completedAt: Optional[str] = Field(default=None, max_length=40)


class Coparenting(BaseModel):
    approach: Optional[Literal["cooperative", "parallel", "unsure"]] = None
    agree: str = Field(default="", max_length=_TEXT)
    disagree: str = Field(default="", max_length=_TEXT)


class ChildNeeds(BaseModel):
    opened: List[Literal["educational", "medical", "emotional", "developmental"]] = Field(default_factory=list, max_length=4)


class Foundation(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)
    draft: str = Field(default="", max_length=_TEXT)
    approved: bool = False
    approvedAt: Optional[str] = Field(default=None, max_length=40)

    @field_validator("answers")
    @classmethod
    def _answers(cls, v):
        return _keep(FOUNDATION_KEYS, v)


class Progress(BaseModel):
    maxStepReached: int = Field(default=0, ge=0, le=LAST_STEP)
    safety: Safety = Field(default_factory=Safety)
    situation: Dict[str, str] = Field(default_factory=dict)
    coparenting: Coparenting = Field(default_factory=Coparenting)
    childNeeds: ChildNeeds = Field(default_factory=ChildNeeds)
    foundation: Foundation = Field(default_factory=Foundation)
    mediation: Dict[str, str] = Field(default_factory=dict)
    updatedAt: Optional[str] = None

    @field_validator("situation")
    @classmethod
    def _situation(cls, v):
        return _keep(SITUATION_KEYS, v)

    @field_validator("mediation")
    @classmethod
    def _mediation(cls, v):
        return _keep(MEDIATION_KEYS, v)

    @model_validator(mode="after")
    def _no_working_together_on_safety_path(self):
        # Working together isn't offered once the parent says there are safety concerns.
        if self.safety.status == "concern" and self.coparenting.approach == "cooperative":
            self.coparenting.approach = None
        return self


class ProgressOut(BaseModel):
    progress: Optional[Progress] = None


@router.get("/me", response_model=ProgressOut)
async def get_progress(user: UserPublic = Depends(get_current_user), db=Depends(get_db)) -> ProgressOut:
    doc = await db[_COLL].find_one({"user_id": user.user_id}, {"_id": 0, "progress": 1})
    return ProgressOut(progress=Progress(**doc["progress"]) if doc else None)


@router.put("/me", response_model=ProgressOut)
async def save_progress(body: Progress, user: UserPublic = Depends(get_current_user), db=Depends(get_db)) -> ProgressOut:
    body.updatedAt = datetime.now(timezone.utc).isoformat()
    await db[_COLL].update_one(
        {"user_id": user.user_id}, {"$set": {"user_id": user.user_id, "progress": body.model_dump()}}, upsert=True
    )
    return ProgressOut(progress=body)
