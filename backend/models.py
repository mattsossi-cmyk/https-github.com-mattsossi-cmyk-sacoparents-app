"""Pydantic models for SA Coparents Mediation Prep App."""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ User Models ============
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    children: Optional[List[Dict[str, Any]]] = []
    custody_situation: Optional[str] = ""
    mediation_date: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_method: str = "jwt"
    children: List[Dict[str, Any]] = []
    custody_situation: str = ""
    mediation_date: Optional[str] = None
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ============ Prep Data Models ============
class ChildGoalsPayload(BaseModel):
    selected_goals: List[str] = []
    consistency_text: str = ""
    feel_text: str = ""
    strength_text: str = ""
    priority_order: List[str] = []


class IssuesPayload(BaseModel):
    parenting_schedule: Dict[str, str] = {}
    communication: Dict[str, str] = {}
    child_needs: Dict[str, str] = {}
    financial: Dict[str, str] = {}
    household_rules: Dict[str, str] = {}
    safety_concerns: str = ""


class PriorityItem(BaseModel):
    id: str
    label: str
    bucket: str  # urgent | difficult | easy | compromise


class PriorityPayload(BaseModel):
    items: List[PriorityItem] = []


class CommStylePayload(BaseModel):
    answers: Dict[str, str] = {}  # questionId -> answer key
    free_text_sample: Optional[str] = ""


class ReadinessPayload(BaseModel):
    answers: Dict[str, int] = {}  # questionId -> 1-5


class ReflectionPayload(BaseModel):
    worry: str = ""
    triggers: str = ""
    calm_strategy: str = ""
    appreciation: str = ""
    private: bool = True


class PrepDataSnapshot(BaseModel):
    child_goals: Optional[ChildGoalsPayload] = None
    issues: Optional[IssuesPayload] = None
    priority: Optional[PriorityPayload] = None
    comm_style: Optional[CommStylePayload] = None
    readiness: Optional[ReadinessPayload] = None
    reflection: Optional[ReflectionPayload] = None


# ============ AI Models ============
class CommAnalysisRequest(BaseModel):
    text: str
    answers: Optional[Dict[str, str]] = None


class CommAnalysisResponse(BaseModel):
    style_label: str
    summary: str
    strengths: List[str]
    growth_areas: List[str]
    suggestions: List[str]
    score: int  # 1-10


class SummaryRequest(BaseModel):
    include_pdf: bool = False


class SummaryResponse(BaseModel):
    summary_id: str
    child_goals_summary: str
    top_concerns: List[str]
    priority_agenda: List[Dict[str, Any]]
    flexibility_areas: List[str]
    communication_goals: List[str]
    notes_for_mediator: str
    readiness_label: str
    readiness_score: int
    generated_at: str
