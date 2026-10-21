"""Pydantic models for SA CoParents Mediation Prep App."""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Literal, Optional, Dict, Any
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
    ack_privacy_notice: bool = False
    consent_sensitive_info: bool = False


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
    is_guest: bool = False
    guest_expires_at: Optional[str] = None
    email_verified: bool = False
    email_bounced: bool = False
    email_complained: bool = False
    consent_current: bool = False
    ai_notice_current: bool = False
    journey_path: Optional[str] = None


class JourneyPathIn(BaseModel):
    path: Literal["court_ordered", "self_journey", "mediation_prep"]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class GuestClaimPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    ack_privacy_notice: bool = False
    consent_sensitive_info: bool = False


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkConsume(BaseModel):
    token: str


class SignupFromToken(BaseModel):
    token: str
    name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    ack_privacy_notice: bool = False
    consent_sensitive_info: bool = False


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=8)


class EmailVerifyConfirm(BaseModel):
    token: str


class EmailCodeSend(BaseModel):
    email: EmailStr


class EmailCodeConfirm(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class PasswordResetCodeConfirm(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)
    password: str = Field(min_length=8)


# ============ Prep Data Models ============
class ChildGoalsPayload(BaseModel):
    selected_goals: List[str] = []
    consistency_text: str = ""
    feel_text: str = ""
    strength_text: str = ""
    priority_order: List[str] = []


class IssuesPayload(BaseModel):
    items: Dict[str, str] = {}  # issue_id -> parent's note (empty = not applicable)
    other: str = ""  # free-text "anything else" field


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
    """Personal Reflection journal entries — private to the user.

    Stored as free-text strings keyed by prompt id. Frontend uses the
    `child_lens`, `own_part`, `best_outcome`, `release` keys but additional
    keys are accepted (`Config.extra = "allow"`) so the prompt set can
    evolve without database migrations.
    """
    child_lens: str = ""
    own_part: str = ""
    best_outcome: str = ""
    coparent_feedback: str = ""
    release: str = ""  # Older prompt — kept for back-compat with historical saves.
    # Legacy keys retained for backward compatibility with older clients.
    worry: str = ""
    triggers: str = ""
    calm_strategy: str = ""
    appreciation: str = ""
    private: bool = True

    class Config:
        extra = "allow"


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
