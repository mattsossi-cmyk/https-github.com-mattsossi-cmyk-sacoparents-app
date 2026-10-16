from core import BUILD_ID, client, db, logger, app_url, invite_link, PRO_ROLES, PRO_INVITE_TTL_HOURS, _pro_email_wrap, _log_lifecycle  # noqa: E402  (core loads .env first)

import os
import uuid

from datetime import datetime, timezone, timedelta



import hashlib
import re
import secrets
from html import escape



from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, EmailStr

from assessment_data import ASSESSMENT_TYPES, ORDERED_TYPE_KEYS, SCALE, demo_payload
from report_engine import generate_report
from joint_data import SUBJECTS, ORDERED_SUBJECT_KEYS, QUESTIONS, CONFIDENTIALITY_NOTICE, SAFETY_SUBJECT_KEYS, AGREEMENT_AREAS, AGREEMENT_SECTIONS, new_case_code
from agreement_ai import draft_agreement_clauses, answers_signature
from joint_engine import SAMPLE_SCENARIOS, generate_agreement, sample_mediation_report, sample_report, sample_list
from joint_pause import assert_joint_open as _assert_joint_open, parent_view as _pause_view


from sample_professional_report import sample_judicial_case, sample_professional_report

from pdf_report import build_joint_pdf, build_agreement_pdf, build_case_pdf, build_methodology_pdf, build_session_prep_pdf, build_communications_log_pdf, verify_qr_png

from auth_utils import hash_password, verify_password
from email_utils import send_email, EMAIL_FROM_NAME, MINIMAL_NOTIFICATIONS
from starlette.middleware.cors import CORSMiddleware
from auth import get_current_user, is_pro, require_approved_professional
from joint_ai import effective_joint_report as generate_joint_report
from joint_helpers import get_joint_report_doc, report_role, invite_expired, _pending_public, joint_public, InviteSpec, send_invite_email, create_invitation, _actor_label
import auth, admin_routes, integrations, cron_jobs

app = FastAPI()
api = APIRouter(prefix="/api")

@api.get("/assessment-types")
async def list_types():
    return [
        {
            "key": k,
            "title": ASSESSMENT_TYPES[k]["title"],
            "description": ASSESSMENT_TYPES[k]["description"],
            "topic_count": len(ASSESSMENT_TYPES[k]["topics"]),
        }
        for k in ORDERED_TYPE_KEYS
    ]


@api.get("/assessment-types/{key}")
async def get_type(key: str):
    cfg = ASSESSMENT_TYPES.get(key)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown assessment type")
    return {
        "key": cfg["key"],
        "title": cfg["title"],
        "description": cfg["description"],
        "central_question": cfg["central_question"],
        "scale": SCALE,
        "shared_goal_options": cfg["shared_goal_options"],
        "topics": [{"key": t["key"], "label": t["label"], "question": t["question"]} for t in cfg["topics"]],
    }


def case_public(c: dict) -> dict:
    return {
        "id": c["id"],
        "type": c["type"],
        "type_title": ASSESSMENT_TYPES[c["type"]]["title"],
        "child_name": c.get("child_name", ""),
        "parent_a_name": c.get("parent_a_name", "Parent A"),
        "parent_b_name": c.get("parent_b_name", "Parent B"),
        "has_a": bool(c.get("responses", {}).get("a")),
        "has_b": bool(c.get("responses", {}).get("b")),
        "is_demo": c.get("is_demo", False),
        "created_at": c["created_at"],
    }


class CaseIn(BaseModel):
    type: str
    child_name: str = ""
    parent_a_name: str = "Parent A"
    parent_b_name: str = "Parent B"


class ResponsesIn(BaseModel):
    answers: dict
    primary_concern: str = ""
    goals: list[str] = []


@api.post("/cases")
async def create_case(body: CaseIn, user=Depends(get_current_user)):
    if body.type not in ASSESSMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unknown assessment type")
    cid = str(uuid.uuid4())
    doc = {
        "id": cid,
        "user_id": user["_id"],
        "type": body.type,
        "child_name": body.child_name.strip(),
        "parent_a_name": body.parent_a_name.strip() or "Parent A",
        "parent_b_name": body.parent_b_name.strip() or "Parent B",
        "responses": {},
        "is_demo": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cases.insert_one(doc)
    return case_public(doc)


@api.get("/cases")
async def list_cases(user=Depends(get_current_user)):
    cases = await db.cases.find({"user_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [case_public(c) for c in cases]


async def get_owned_case(case_id: str, user: dict) -> dict:
    c = await db.cases.find_one({"id": case_id, "user_id": user["_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return c


@api.get("/cases/{case_id}")
async def get_case(case_id: str, user=Depends(get_current_user)):
    return case_public(await get_owned_case(case_id, user))


@api.put("/cases/{case_id}/responses/{parent}")
async def save_responses(case_id: str, parent: str, body: ResponsesIn, user=Depends(get_current_user)):
    if parent not in ("a", "b"):
        raise HTTPException(status_code=400, detail="Parent must be 'a' or 'b'")
    c = await get_owned_case(case_id, user)
    cfg = ASSESSMENT_TYPES[c["type"]]
    valid_keys = {t["key"] for t in cfg["topics"]}
    answers = {k: v for k, v in body.answers.items() if k in valid_keys and v in SCALE}
    if set(answers.keys()) != valid_keys:
        raise HTTPException(status_code=400, detail="All questions must be answered")
    payload = {
        "answers": answers,
        "primary_concern": body.primary_concern.strip(),
        "goals": body.goals,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cases.update_one({"id": case_id}, {"$set": {f"responses.{parent}": payload, "is_demo": False}})
    c = await get_owned_case(case_id, user)
    return case_public(c)


@api.post("/cases/{case_id}/demo")
async def fill_demo(case_id: str, user=Depends(get_current_user)):
    c = await get_owned_case(case_id, user)
    demo = demo_payload(c["type"])
    await db.cases.update_one(
        {"id": case_id},
        {
            "$set": {
                "responses.a": {**demo["a"], "completed_at": datetime.now(timezone.utc).isoformat()},
                "responses.b": {**demo["b"], "completed_at": datetime.now(timezone.utc).isoformat()},
                "child_name": c.get("child_name") or demo["child_name"],
                "is_demo": True,
            }
        },
    )
    return case_public(await get_owned_case(case_id, user))


@api.get("/cases/{case_id}/report")
async def get_report(case_id: str, user=Depends(get_current_user)):
    c = await get_owned_case(case_id, user)
    if not (c.get("responses", {}).get("a") and c.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="Both parents must complete the assessment before the report can be generated")
    return generate_report(c)


@api.get("/cases/{case_id}/pdf")
async def case_report_pdf(case_id: str, user=Depends(get_current_user)):
    c = await get_owned_case(case_id, user)
    if not (c.get("responses", {}).get("a") and c.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="Both parents must complete the assessment before the PDF can be generated")
    child = re.sub(r"[^a-z0-9-]", "", (c.get("child_name") or "child").lower().replace(" ", "-")) or "child"
    return Response(
        content=build_case_pdf(generate_report(c)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="alignment-report-{child}.pdf"'},
    )


@api.delete("/cases/{case_id}")
async def delete_case(case_id: str, user=Depends(get_current_user)):
    result = await db.cases.delete_one({"id": case_id, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"ok": True}


ADMIN_PROFILE = {
    "name": "Matt Sossi",
    "pro_role": "Attorney, Family Law Mediator, Parent Facilitator & Amicus Attorney",
    "organization": "Law Office of Matt Sossi",
    "address": "16607 Blanco #703",
    "city": "San Antonio",
    "state": "Texas 78232",
    "phone": "210-224-1667",
    "license_number": "Texas Attorney",
}

SEEDED_PROFESSIONALS = [
    {
        "email": "joy@bsossi.com",
        "name": "Joy Curbow, MS",
        "password_env": "JOY_TEMP_PASSWORD",
        "profile": {
            "pro_role": "Family Law Mediator",
            "organization": "Law Office of Matt Sossi",
            "address": "16607 Blanco #703",
            "city": "San Antonio",
            "state": "Texas 78232",
            "phone": "210-224-1667",
            "license_number": "",
        },
    },
    {
        "email": "dralsmith@gmail.com",
        "name": "Albert W. Smith, PhD",
        "password_env": "ALSMITH_TEMP_PASSWORD",
        "profile": {
            "pro_role": "Psychologist",
            "organization": "Law Office of Matt Sossi",
            "address": "16607 Blanco #703",
            "city": "San Antonio",
            "state": "Texas 78232",
            "phone": "210-854-8964",
            "license_number": "",
        },
    },
]


async def seed_auto_approvals():
    """Approve accounts listed in AUTO_APPROVE_EMAILS (comma-separated) at startup; idempotent, env-driven, no HTTP surface."""
    emails = [e.strip().lower() for e in os.environ.get("AUTO_APPROVE_EMAILS", "").split(",") if e.strip()]
    if not emails:
        return
    now = datetime.now(timezone.utc).isoformat()
    res = await db.users.update_many({"email": {"$in": emails}, "role": {"$in": ["professional", "judge"]}},
                                     {"$set": {"approved": True, "declined": False, "verification_level": "credentials_verified", "credentials_verified_at": now, "auto_approved_at": now}})
    logger.info("AUTO_APPROVE_EMAILS: %s account(s) approved", res.modified_count)


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return
    existing = await db.users.find_one({"email": admin_email.lower()})
    if existing is None:
        await db.users.insert_one({
            "_id": str(uuid.uuid4()),
            "email": admin_email.lower(),
            "name": ADMIN_PROFILE["name"],
            "role": "admin",
            "approved": True,
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif (os.environ.get("ADMIN_PASSWORD_RESYNC") == "1" or not existing.get("password_reset_by_user")) and not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email.lower()},
            {"$set": {"password_hash": hash_password(admin_password)}, "$unset": {"password_reset_by_user": ""}},
        )
        logger.info("Admin password re-synced from ADMIN_PASSWORD env")
    if not (existing or {}).get("profile", {}).get("pro_role"):
        await db.users.update_one(
            {"email": admin_email.lower()},
            {"$set": {"name": ADMIN_PROFILE["name"], "approved": True, "verification_level": "credentials_verified",
                      "credentials_verified_at": datetime.now(timezone.utc).isoformat(),
                      "profile": {k: v for k, v in ADMIN_PROFILE.items() if k != "name"}}},
        )


async def seed_professionals():
    for spec in SEEDED_PROFESSIONALS:
        temp_password = os.environ.get(spec["password_env"])
        if not temp_password or await db.users.find_one({"email": spec["email"]}):
            continue
        now = datetime.now(timezone.utc).isoformat()
        await db.users.insert_one({
            "_id": str(uuid.uuid4()),
            "email": spec["email"],
            "name": spec["name"],
            "role": "professional",
            "approved": True,
            "approved_at": now,
            "verification_level": "credentials_verified",
            "credentials_verified_at": now,
            "profile": spec["profile"],
            "must_change_password": True,
            "password_hash": hash_password(temp_password),
            "created_at": now,
        })


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.cases.create_index("user_id")
    await db.joint_reports.create_index("created_by")
    await db.invitations.create_index("code")
    await db.invitations.create_index("token")
    await db.account_links.create_index("user_id", unique=True)
    await seed_admin()
    from providers import seed_providers
    await seed_providers(db)
    await seed_auto_approvals()
    await seed_professionals()
    try:
        from storage import init_storage
        init_storage()
    except Exception as exc:
        logger.warning("object storage init failed: %s", exc)


# ---------- Joint Report Builder ----------

class JointReportIn(BaseModel):
    subject: str
    custom_subject: str = ""
    subjects: list[str] = []
    child_name: str
    co_parent_name: str
    co_parent_email: EmailStr
    mediator_email: EmailStr | None = None


class ProJointReportIn(BaseModel):
    subject: str
    custom_subject: str = ""
    subjects: list[str] = []
    child_name: str
    parent_a_name: str
    parent_a_email: EmailStr
    parent_b_name: str
    parent_b_email: EmailStr
    parent_a_gender: str = ""
    parent_b_gender: str = ""
    case_reference: str = ""
    court_referral_id: str = ""


class JointResponsesIn(BaseModel):
    answers: dict
    foundation: list | None = None


class AcceptIn(BaseModel):
    code: str


class ShareIn(BaseModel):
    email: EmailStr


class PatchInvitationIn(BaseModel):
    subject: str
    custom_subject: str = ""


@api.get("/joint/config")
async def joint_config():
    return {
        "subjects": [{"key": k, "label": SUBJECTS[k]["label"]} for k in ORDERED_SUBJECT_KEYS],
        "questions": [{"key": k, "area": a, "question": q} for k, a, q in QUESTIONS],
        "confidentiality_notice": CONFIDENTIALITY_NOTICE,
        "agreement_areas": [{"key": k, "label": l, "question": q} for k, l, q in AGREEMENT_AREAS],
        "agreement_sections": [{"key": s["key"], "num": s["num"], "label": s["label"], "goal": s["goal"], "question": s["question"],
                                "follow_ups": [{"key": f"{s['key']}__{fk}", "prompt": p} for fk, p in s["follow_ups"]]} for s in AGREEMENT_SECTIONS],
    }


def _multi_label(subject_keys: list) -> str:
    label = "Customized Report: " + " + ".join(SUBJECTS[k]["label"] for k in subject_keys[:3])
    return label + ("…" if len(subject_keys) > 3 else "")


def resolve_subjects(body_subject: str, body_subjects: list, custom: str) -> tuple:
    subject_keys = body_subjects or [body_subject]
    if not subject_keys or any(k not in SUBJECTS for k in subject_keys):
        raise HTTPException(status_code=400, detail="Unknown subject")
    if len(subject_keys) > 1:
        return "multi", subject_keys, _multi_label(subject_keys)
    subject = subject_keys[0]
    label = (custom.strip() or "Custom Subject") if subject == "custom" else SUBJECTS[subject]["label"]
    return subject, subject_keys, label


async def _resolve_mediator(body: JointReportIn, user: dict) -> dict | None:
    if not body.mediator_email:
        raise HTTPException(status_code=400, detail="Family violence reports are prepared with a third-party mediator. Please provide the mediator's email.")
    mediator = await db.users.find_one({"email": body.mediator_email.lower(), "role": "professional"})
    if not mediator:
        raise HTTPException(status_code=404, detail="No professional account found with that email. Ask your mediator to create a free professional account first.")
    if mediator["_id"] == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot designate yourself as the mediator.")
    return mediator


async def _notify_mediator(mediator: dict, user: dict, doc: dict, label: str) -> None:
    try:
        await send_email(
            to=mediator["email"],
            subject=(f"Facilitation requested - {EMAIL_FROM_NAME}" if MINIMAL_NOTIFICATIONS else f"Family violence Joint Report facilitation requested - {EMAIL_FROM_NAME}"),
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(mediator.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has requested your third-party "
                f"facilitation of a family-violence Joint Report regarding "
                f"<strong>{escape(doc['child_name'])}</strong> ({escape(label)}).</p>"
                "<p>Both parents' individual responses remain confidential and are not shared between the "
                "parties. You will see the completed comparison once both parents finish.</p>"
                f'<p><a href="{app_url()}/dashboard" style="color:#5B2A86">Open your dashboard</a></p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Mediator notification not sent to {mediator['email']}")


@api.post("/joint/reports")
async def create_joint_report(body: JointReportIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Joint reports are initiated by an authorized professional. Parents participate through a secure invitation.")
    subject, subject_keys, label = resolve_subjects(body.subject, body.subjects, body.custom_subject)
    is_safety = all(k in SAFETY_SUBJECT_KEYS for k in subject_keys)
    mediator = await _resolve_mediator(body, user) if is_safety else None
    rid = str(uuid.uuid4())
    case_code = new_case_code(subject)
    doc = {
        "id": rid,
        "subject": subject,
        "subjects": subject_keys,
        "subject_label": label,
        "is_safety": is_safety,
        "case_code": case_code,
        "child_name": body.child_name.strip(),
        "created_by": user["_id"],
        "creator_role": "parent",
        "professional_id": mediator["_id"] if mediator else None,
        "professional_name": (mediator.get("name") or mediator["email"]) if mediator else None,
        "shared_with": [],
        "participants": {
            "a": {"user_id": user["_id"], "name": user.get("name", ""), "email": user["email"]},
            "b": {"user_id": None, "name": body.co_parent_name.strip(), "email": body.co_parent_email.lower()},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.joint_reports.insert_one(doc)
    inv = await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=body.co_parent_name, invitee_email=body.co_parent_email, inviter_name=user.get("name", "Your co-parent"), child_name=doc["child_name"], subject_label=label, code=case_code))
    if mediator:
        await _notify_mediator(mediator, user, doc, label)
    return {**joint_public(doc, user), "invitation": {"id": inv["id"], "code": inv["code"], "link": invite_link(inv["token"]), "invitee_email": inv["invitee_email"], "status": "pending"}}


@api.post("/joint/reports/{rid}/safety-case")
async def start_safety_case(rid: str, user=Depends(get_current_user)):
    """One-click Family Violence / Safety assessment case for the same parents when a safety screen is flagged."""
    doc = await get_joint_report_doc(rid, user)
    if doc.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the professional on this case can start a safety assessment")
    p = doc.get("participants") or {}
    if not (p.get("a", {}).get("email") and p.get("b", {}).get("email")):
        raise HTTPException(status_code=400, detail="Both parents must be on the case before starting a safety assessment")
    body = ProJointReportIn(subject="safety", subjects=["safety", "risk", "safety_communication", "safeguards"], child_name=doc.get("child_name") or "Child",
                            parent_a_name=p["a"].get("name") or "Parent A", parent_a_email=p["a"]["email"], parent_b_name=p["b"].get("name") or "Parent B", parent_b_email=p["b"]["email"],
                            case_reference=f"Safety pathway from {doc.get('case_code') or rid[:8]}", court_referral_id=doc.get("court_referral_id") or "")
    created = await create_pro_joint_report(body, user)
    await db.joint_reports.update_one({"id": rid}, {"$set": {"safety_case_id": created["id"]}})
    return created


@api.post("/joint/reports/professional")
async def create_pro_joint_report(body: ProJointReportIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Only professional accounts can create reports for two parents")
    subject, subject_keys, label = resolve_subjects(body.subject, body.subjects, body.custom_subject)
    rid = str(uuid.uuid4())
    case_code = new_case_code(subject)
    if body.court_referral_id:
        pre = await db.court_referrals.find_one({"id": body.court_referral_id, "professional_id": user["_id"]}, {"case_code": 1, "case_id": 1})
        if pre and pre.get("case_code") and not pre.get("case_id"):
            case_code = pre["case_code"]
    doc = {
        "id": rid,
        "subject": subject,
        "subjects": subject_keys,
        "subject_label": label,
        "is_safety": all(k in SAFETY_SUBJECT_KEYS for k in subject_keys),
        "kind": "foundation" if subject == "foundation" else "joint_report",
        "case_code": case_code,
        "case_reference": body.case_reference.strip()[:120],
        "child_name": body.child_name.strip(),
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": body.parent_a_name.strip(), "email": body.parent_a_email.lower(), "gender": body.parent_a_gender.strip().lower()[:20]},
            "b": {"user_id": None, "name": body.parent_b_name.strip(), "email": body.parent_b_email.lower(), "gender": body.parent_b_gender.strip().lower()[:20]},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.court_referral_id:
        ref = await db.court_referrals.find_one({"id": body.court_referral_id, "professional_id": user["_id"], "status": {"$in": ["accepted", "pending"]}}, {"_id": 0})
        if not ref:
            raise HTTPException(status_code=404, detail="Court referral not found")
        doc["court_referral_id"] = ref["id"]
        doc["court"] = {k: ref.get(k, "") for k in ("judge_id", "judge_name", "judge_email", "court_name", "cause_number")}
        if not doc["case_reference"]:
            doc["case_reference"] = f"Cause No. {ref['cause_number']}"
        await db.court_referrals.update_one({"id": ref["id"]}, {"$set": {"status": "accepted", "case_id": rid, "responded_at": ref.get("responded_at") or doc["created_at"]}})
    await db.joint_reports.insert_one(doc)
    inv_a = await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=body.parent_a_name, invitee_email=body.parent_a_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label=label, code=case_code, via_professional=True))
    inv_b = await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=body.parent_b_name, invitee_email=body.parent_b_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label=label, code=case_code, via_professional=True))
    return {**joint_public(doc, user), "invitations": [
        {"role": i["role"], "code": i["code"], "link": invite_link(i["token"]), "invitee_email": i["invitee_email"], "invitee_name": i["invitee_name"], "status": "pending"}
        for i in (inv_a, inv_b)
    ]}


@api.post("/joint/reports/professional/sample")
async def create_sample_joint_case(user=Depends(get_current_user)):
    require_approved_professional(user, "Only approved professional accounts can load a sample case")
    existing = await db.joint_reports.find_one({"professional_id": user["_id"], "is_demo": True, "closed_at": {"$exists": False}}, {"_id": 0})
    if existing:
        return {**joint_public(existing, user), "already_existed": True}
    sc = SAMPLE_SCENARIOS["communication"]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "subject": sc["subject"],
        "subjects": [sc["subject"]],
        "subject_label": sc["label"],
        "is_safety": False,
        "is_demo": True,
        "case_code": new_case_code(sc["subject"]),
        "case_reference": "Sample case (fictional family)",
        "child_name": sc["child"],
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": sc["pa"], "email": ""},
            "b": {"user_id": None, "name": sc["pb"], "email": ""},
        },
        "responses": {
            "a": {"answers": sc["answers_a"], "completed_at": now},
            "b": {"answers": sc["answers_b"], "completed_at": now},
        },
        "status": "ready",
        "created_at": now,
    }
    await db.joint_reports.insert_one(doc)
    return {**joint_public(doc, user), "already_existed": False}


@api.get("/joint/reports")
async def list_joint_reports(user=Depends(get_current_user)):
    uid = user["_id"]
    docs = await db.joint_reports.find(
        {"$or": [
            {"created_by": uid},
            {"participants.a.user_id": uid},
            {"participants.b.user_id": uid},
            {"professional_id": uid},
            {"shared_with": uid},
        ]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    own_ids = [d["id"] for d in docs if d.get("created_by") == uid]
    inv_map = {}
    if own_ids:
        async for i in db.invitations.find({"report_id": {"$in": own_ids}, "status": "pending"}, {"_id": 0}):
            inv_map.setdefault(i["report_id"], []).append(i)
    return [
        joint_public(
            d, user,
            (inv_map.get(d["id"]) or [None])[0] if d.get("created_by") == uid else None,
            pending=inv_map.get(d["id"]) if d.get("created_by") == uid else None,
        )
        for d in docs
    ]


def _verify_info(doc: dict) -> dict | None:
    code = doc.get("case_code")
    if not code:
        return None
    return {"case_code": code, "url": f"{app_url()}/verify?code={code}"}


async def _report_professional(doc: dict) -> dict | None:
    pid = doc.get("professional_id") or doc.get("created_by")
    pro = await db.users.find_one({"_id": pid, "role": "professional"}, {"name": 1, "verification_level": 1}) if pid else None
    if not pro:
        return None
    return {"name": pro.get("name", ""), "credentials_verified": pro.get("verification_level") == "credentials_verified"}


@api.get("/joint/reports/{rid}")
async def get_joint_report(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    pend = await db.invitations.find({"report_id": rid, "status": "pending"}, {"_id": 0}).to_list(10)
    out = joint_public(doc, user, pend[0] if pend else None, pending=pend)
    out.update(_pause_view(doc, user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))))
    return out


def _foundation_payload(body: JointResponsesIn) -> list:
    return [
        {"title": str(s.get("title", "Foundation Statement"))[:120], "content": str(s.get("content", ""))[:5000]}
        for s in (body.foundation or []) if isinstance(s, dict)
    ]


def _validated_answers(doc: dict, body: JointResponsesIn) -> dict:
    if doc.get("kind") == "agreement":
        required = {s["key"] for s in AGREEMENT_SECTIONS}
        optional = {f"{s['key']}__{fk}" for s in AGREEMENT_SECTIONS for fk, _p in s["follow_ups"]}
        answers = {k: (body.answers.get(k) or "").strip()[:3000] for k in required}
        if any(not v for v in answers.values()):
            raise HTTPException(status_code=400, detail="Please answer the main question in every section")
        answers.update({k: (body.answers.get(k) or "").strip()[:2000] for k in optional if (body.answers.get(k) or "").strip()})
        payload = {"answers": answers, "completed_at": datetime.now(timezone.utc).isoformat()}
        if body.foundation:
            payload["foundation"] = _foundation_payload(body)
        return payload
    valid = {k for k, _, _ in QUESTIONS}
    answers = {k: (body.answers.get(k) or "").strip() for k in valid}
    if any(not v for v in answers.values()):
        raise HTTPException(status_code=400, detail="Please answer all questions")
    payload = {"answers": answers, "completed_at": datetime.now(timezone.utc).isoformat()}
    if body.foundation:
        payload["foundation"] = _foundation_payload(body)
    return payload


async def ensure_agreement_ai(doc: dict) -> dict:
    """Draft concrete clauses once per answer-set with gpt-5.4-mini; cached on the case. Rule-based output is used when unavailable."""
    if doc.get("kind") != "agreement" or not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        return doc
    sig = answers_signature(doc)
    cached = doc.get("agreement_ai") or {}
    if cached.get("signature") == sig:
        return doc
    ra, rb = doc["responses"]["a"]["answers"], doc["responses"]["b"]["answers"]
    payload = [{"key": s["key"], "label": s["label"], "shared_goal": s["goal"], "parent_a_proposal": ra.get(s["key"], ""), "parent_b_proposal": rb.get(s["key"], ""),
                "follow_ups": [{"id": f"{s['key']}__{fk}", "question": p, "parent_a": ra.get(f"{s['key']}__{fk}", ""), "parent_b": rb.get(f"{s['key']}__{fk}", "")} for fk, p in s["follow_ups"]
                               if ra.get(f"{s['key']}__{fk}") or rb.get(f"{s['key']}__{fk}")]}
               for s in AGREEMENT_SECTIONS]
    sections = await draft_agreement_clauses(payload, doc["id"])
    if sections is None:
        return doc
    ai = {"signature": sig, "sections": sections, "model": "gpt-5.4-mini", "at": datetime.now(timezone.utc).isoformat()}
    await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {"agreement_ai": ai}})
    return {**doc, "agreement_ai": ai}


@api.put("/joint/reports/{rid}/responses")
async def save_joint_responses(rid: str, body: JointResponsesIn, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    role = report_role(doc, user["_id"])
    if role is None:
        raise HTTPException(status_code=403, detail="Only invited parents can submit responses")
    from safety_screening import safety_step_satisfied
    if not safety_step_satisfied(doc, role):
        raise HTTPException(status_code=403, detail="Please go through the Start with Safety step before answering the assessment.")
    _assert_joint_open(doc)
    payload = _validated_answers(doc, body)
    existing_foundation = (doc.get("responses", {}).get(role) or {}).get("foundation")
    if existing_foundation and not payload.get("foundation"):
        payload["foundation"] = existing_foundation
    updates = {f"responses.{role}": payload}
    other = "b" if role == "a" else "a"
    if doc.get("responses", {}).get(other):
        updates["status"] = "ready"
    await db.joint_reports.update_one({"id": rid}, {"$set": updates})
    doc = await get_joint_report_doc(rid, user)
    if updates.get("status") == "ready" and not doc.get("both_complete_notified_at"):
        await _notify_both_complete(doc)
    return joint_public(doc, user)


async def _notify_both_complete(doc: dict) -> None:
    """Tell the case professional both parents have finished, with direct links to the Joint Report and Professional Report."""
    pro = await db.users.find_one({"_id": doc.get("professional_id") or doc.get("created_by"), "role": {"$in": ["professional", "admin"]}}, {"email": 1, "name": 1})
    await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {"both_complete_notified_at": datetime.now(timezone.utc).isoformat()}})
    if not pro or doc.get("is_demo"):
        return
    code = doc.get("case_code") or doc["id"][:8]
    try:
        await send_email(
            to=pro["email"], subject=(f"Case {code} update - {EMAIL_FROM_NAME}" if MINIMAL_NOTIFICATIONS else f"Both parents have completed — Case {code} - {EMAIL_FROM_NAME}"),
            html=_pro_email_wrap(
                f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                f"<p>Both parents have completed their individual assessments for <strong>{escape(doc.get('child_name') or 'the child')}</strong> "
                f"(<strong>{escape(doc.get('subject_label') or '')}</strong>, Case {escape(code)}). The Joint Report is ready for your review, and the Professional Report can now be drafted.</p>"
                f'<p><a href="{app_url()}/joint/{doc["id"]}" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Open Joint Report</a> &nbsp; '
                f'<a href="{app_url()}/cases/{doc["id"]}/professional-report" style="display:inline-block;background:#1F6FB2;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Open Professional Report</a></p>'
                "<p style=\"color:#666;font-size:13px\">Individual answers stay private to each parent; the Joint Report shows only the neutral comparison.</p>"
            ),
        )
    except Exception:
        logger.warning(f"Both-complete notification not sent for case {doc['id']}")



async def _log_report_access(doc: dict, user: dict, action: str, kind: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.access_events.insert_one({
        "report_id": doc["id"], "action": action, "kind": kind, "at": now,
        "by": user["_id"], "by_name": user.get("name", ""), "by_role": _actor_label(doc, user),
    })
    if not doc.get("report_generated_at"):
        await db.joint_reports.update_one({"id": doc["id"], "report_generated_at": {"$exists": False}}, {"$set": {"report_generated_at": now}})


@api.get("/joint/reports/{rid}/report")
async def get_joint_report_output(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if not (user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))):
        _assert_joint_open(doc)
    if not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="The Joint Report becomes available when both parents have completed their assessments")
    await _log_report_access(doc, user, "Viewed report on screen", "view")
    if doc.get("kind") == "agreement":
        return generate_agreement(await ensure_agreement_ai(doc))
    if doc.get("kind") == "foundation":
        return {"kind": "foundation", "foundation_statements": joint_public(doc, user).get("foundation_statements", [])}
    rep = generate_joint_report(doc)
    rep.pop("options", None)  # options/resources live only in the Professional Report
    return rep


@api.get("/joint/reports/{rid}/foundation/{side}/pdf")
async def joint_foundation_pdf(rid: str, side: str, user=Depends(get_current_user)):
    from pdf_foundation import build_foundation_pdf
    doc = await get_joint_report_doc(rid, user)
    if side not in ("a", "b") or (doc.get("created_by") != user["_id"] and report_role(doc, user["_id"]) != side):
        raise HTTPException(status_code=403, detail="Not authorized to view this Foundation Statement")
    stmts = (doc.get("responses", {}).get(side) or {}).get("foundation") or []
    if not stmts:
        raise HTTPException(status_code=404, detail="No Foundation Statement on file for this parent")
    parent = (doc.get("participants", {}).get(side) or {}).get("name") or f"Parent {side.upper()}"
    await _log_report_access(doc, user, f"Downloaded Foundation Statement ({parent})", "download")
    structured = next((s["structured"] for s in stmts if isinstance(s.get("structured"), dict)), None)
    if structured:
        from foundation import to_pdf_data
        pdf = build_foundation_pdf(to_pdf_data({"fields": structured, "updated_at": stmts[0].get("shared_at", "")}, parent, bool(doc.get("is_demo"))))
    else:
        pdf = build_foundation_pdf({"freeform": stmts, "parent_name": parent, "child_name": doc.get("child_name") or "—", "child_short": doc.get("child_name") or "my child",
                                    "statement_date": ((doc.get("responses", {}).get(side) or {}).get("completed_at") or "")[:10], "is_sample": bool(doc.get("is_demo"))})
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="foundation-statement-{side}.pdf"'})


@api.get("/joint/reports/{rid}/pdf")
async def joint_report_pdf(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if not (user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))):
        _assert_joint_open(doc)
    if not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="The Joint Report PDF becomes available when both parents have completed their assessments")
    await _log_report_access(doc, user, "Downloaded PDF", "download")
    child = re.sub(r"[^a-z0-9-]", "", (doc.get("child_name") or "child").lower().replace(" ", "-")) or "child"
    if doc.get("kind") == "agreement":
        from safety_gate import safety_status
        em = {(doc.get("participants", {}).get(s) or {}).get("email", "").lower() for s in ("a", "b")} - {""}
        safety = await safety_status(db, em, doc.get("created_by"))
        return Response(
            content=build_agreement_pdf(generate_agreement(await ensure_agreement_ai(doc)), doc=doc, is_sample=bool(doc.get("is_demo")), safety=safety),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="coparenting-agreement-{child}.pdf"'},
        )
    if doc.get("kind") == "foundation":
        raise HTTPException(status_code=400, detail="Foundation Statement cases have one PDF per parent — use the Foundation Statement download buttons")
    pdf_bytes = build_joint_pdf({**generate_joint_report(doc), "is_sample": bool(doc.get("is_demo")), "professional": await _report_professional(doc), "verify": _verify_info(doc)})
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="joint-report-{child}.pdf"'},
    )


@api.get("/joint/reports/{rid}/session-prep.pdf")
async def session_prep_pdf(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if doc.get("professional_id") != user["_id"] and user["_id"] not in doc.get("shared_with", []):
        raise HTTPException(status_code=403, detail="The Session Prep Sheet is available to the case professional only")
    if doc.get("kind") == "agreement" or not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="The Session Prep Sheet becomes available when both parents have completed their assessments")
    await _log_report_access(doc, user, "Downloaded Session Prep Sheet", "download")
    code = re.sub(r"[^A-Za-z0-9-]", "", doc.get("case_code") or rid[:8])
    return Response(
        content=build_session_prep_pdf({**generate_joint_report(doc), "case_code": doc.get("case_code")}),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="session-prep-{code}.pdf"'},
    )


@api.get("/joint/sample/mediation")
async def sample_mediation():
    return {k: v for k, v in sample_mediation_report().items() if k != "options"}


@api.get("/joint/sample/mediation/pdf")
async def sample_mediation_pdf():
    return Response(
        content=build_joint_pdf(sample_mediation_report()),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="sample-mediation-statement.pdf"'},
    )


@api.get("/joint/samples")
async def list_sample_reports():
    return sample_list()


class EmailSampleIn(BaseModel):
    email: EmailStr


@api.get("/joint/sample-professional-report")
async def sample_professional_report_json():
    return sample_professional_report()


@api.get("/joint/sample-professional-report/pdf")
async def sample_professional_report_pdf():
    from pdf_report import build_professional_statement_pdf
    return Response(content=build_professional_statement_pdf(sample_professional_report()), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="sample-professional-report.pdf"'})


@api.post("/joint/sample-professional-report/email")
async def email_sample_professional_report(body: EmailSampleIn):
    await send_email(
        to=str(body.email).lower(),
        subject=f"Sample Professional Report (legal) - {EMAIL_FROM_NAME}",
        html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
              "<p>Hello,</p><p>Here is the sample <strong>Professional Report</strong> from SA CoParents Align — the single legal deliverable a professional submits to the court, "
              "with the parents' Joint Report findings infused, the Co-Parenting Ability Level, Parent Alignment, options and resources, and conflict-management techniques.</p>"
              f'<p><a href="{app_url()}/samples/legal-lens-report" style="color:#5B2A86">View the sample online</a></p>'
              f'<p><a href="{app_url()}/api/joint/sample-legal-lens/pdf" style="color:#5B2A86">Download the sample PDF</a></p>'
              f'<p style="font-size:12px;color:#888">Sample uses fictional data. Sent by {escape(EMAIL_FROM_NAME)} via the public sample-sharing form.</p></td></tr></table>'))
    return {"ok": True}


@api.get("/joint/sample-foundation-statement")
async def sample_foundation_json():
    from sample_foundation import sample_foundation_statement
    return sample_foundation_statement()


@api.get("/joint/sample-foundation-statement/pdf")
async def sample_foundation_pdf(inline: int = 0):
    from pdf_foundation import build_foundation_pdf
    from sample_foundation import sample_foundation_statement
    disposition = "inline" if inline else "attachment"
    return Response(content=build_foundation_pdf(sample_foundation_statement()), media_type="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="sample-foundation-statement.pdf"'})


@api.get("/joint/sample-agreement")
async def sample_agreement_json():
    from sample_agreement import sample_agreement
    return sample_agreement()


@api.get("/joint/sample-agreement/pdf")
async def sample_agreement_pdf(inline: int = 0):
    from sample_agreement import sample_agreement, sample_agreement_doc
    disposition = "inline" if inline else "attachment"
    return Response(content=build_agreement_pdf(sample_agreement(), doc=sample_agreement_doc(), is_sample=True), media_type="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="sample-coparenting-agreement.pdf"'})


@api.get("/joint/sample-legal-lens")
async def sample_legal_lens_json():
    from sample_legal_lens import sample_legal_lens
    return sample_legal_lens()


@api.get("/joint/sample-legal-lens/pdf")
async def sample_legal_lens_pdf(inline: int = 0):
    from pdf_lens import build_legal_lens_pdf
    from sample_legal_lens import sample_legal_lens
    disposition = "inline" if inline else "attachment"
    return Response(content=build_legal_lens_pdf(sample_legal_lens()), media_type="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="sample-professional-report-legal-lens.pdf"'})


@api.post("/joint/sample-legal-lens/email")
async def email_sample_legal_lens(body: EmailSampleIn):
    await send_email(
        to=str(body.email).lower(),
        subject=f"Sample Legal Lens Review and Report to Court - {EMAIL_FROM_NAME}",
        html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
              "<p>Hello,</p><p>Here is the sample <strong>SA CoParents Legal Lens Review and Report to Court</strong> from SA CoParents Align — a fully completed, fictional example "
              "of the professional legal report: Safety First, individual and joint co-parenting ratings, resources, Parent Alignment, Conflict Management, Roadmap and Professional Summary.</p>"
              f'<p><a href="{app_url()}/samples/legal-lens-report" style="color:#5B2A86">View the sample online</a></p>'
              f'<p><a href="{app_url()}/api/joint/sample-legal-lens/pdf" style="color:#5B2A86">Download the sample PDF</a></p>'
              f'<p style="font-size:12px;color:#888">Sample uses fictional data. Sent by {escape(EMAIL_FROM_NAME)} via the public sample-sharing form.</p></td></tr></table>'))
    return {"ok": True}


_EXTRA_SAMPLES = {
    "foundation-statement": ("Child-Focused Foundation Statement", "a parent's statement of shared purpose, vision, priorities, the child's strengths and needs, concerns, commitments and 12-month goals", "/samples/foundation-statement", "/api/joint/sample-foundation-statement/pdf"),
    "coparenting-agreement": ("Co-Parenting Agreement", "a joint agreement built from both parents' private proposals across 10 areas, with specific agreements and issues still requiring resolution", "/samples/coparenting-agreement", "/api/joint/sample-agreement/pdf"),
}


@api.post("/joint/sample-extra/{key}/email")
async def email_extra_sample(key: str, body: EmailSampleIn):
    if key not in _EXTRA_SAMPLES:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    label, desc, view, pdf = _EXTRA_SAMPLES[key]
    await send_email(
        to=str(body.email).lower(),
        subject=f"Sample {label} - {EMAIL_FROM_NAME}",
        html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
              f"<p>Hello,</p><p>Here is the sample <strong>SA CoParents {escape(label)}</strong> — {escape(desc)}.</p>"
              f'<p><a href="{app_url()}{view}" style="color:#5B2A86">View the sample online</a></p>'
              f'<p><a href="{app_url()}{pdf}" style="color:#5B2A86">Download the sample PDF</a></p>'
              f'<p style="font-size:12px;color:#888">Sample uses fictional data. Sent by {escape(EMAIL_FROM_NAME)} via the public sample-sharing form.</p></td></tr></table>'))
    return {"ok": True}


@api.get("/court-dashboard/sample-case")
async def judicial_sample_case():
    return sample_judicial_case()


@api.get("/joint/sample/{key}")
async def sample_report_json(key: str):
    report = sample_report(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    report.pop("options", None)
    return report


@api.get("/joint/sample/{key}/pdf")
async def sample_report_pdf(key: str):
    report = sample_report(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    return Response(
        content=build_joint_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sample-{key}-report.pdf"'},
    )


@api.get("/methodology/pdf")
async def methodology_pdf():
    return Response(
        content=build_methodology_pdf(app_url()),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="sa-coparents-align-methodology.pdf"'},
    )



@api.post("/joint/sample/{key}/email")
async def email_sample_report(key: str, body: EmailSampleIn):
    report = sample_report(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown sample report")
    label = report["subject_label"]
    view_link = f"{app_url()}/samples/{key}"
    pdf_link = f"{app_url()}/api/joint/sample/{key}/pdf"
    await send_email(
        to=str(body.email).lower(),
        subject=f"Sample report: {label} - {EMAIL_FROM_NAME}",
        html=(
            '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            "<p>Hello,</p>"
            f"<p>Here is the sample <strong>{escape(label)}</strong> report from SA CoParents Align — an example of the "
            "neutral, child-focused format professionals use to compare parent perspectives.</p>"
            f'<p><a href="{view_link}" style="color:#5B2A86">View the sample report online</a></p>'
            f'<p><a href="{pdf_link}" style="color:#5B2A86">Download the sample PDF</a></p>'
            f'<p style="font-size:12px;color:#888">Sample uses fictional data. Sent by {escape(EMAIL_FROM_NAME)} via the public sample-sharing form.</p>'
            "</td></tr></table>"
        ),
    )
    return {"ok": True}

@api.post("/joint/reports/{rid}/share")
async def share_joint_report(rid: str, body: ShareIn, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    if report_role(doc, user["_id"]) is None:
        raise HTTPException(status_code=403, detail="Only a participating parent can share this report")
    pro = await db.users.find_one({"email": body.email.lower(), "role": "professional"})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional account found with that email")
    await db.joint_reports.update_one({"id": rid}, {"$addToSet": {"shared_with": pro["_id"]}})
    try:
        await send_email(
            to=pro["email"],
            subject=f"A joint report has been shared with you - {EMAIL_FROM_NAME}",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has shared the "
                f"{escape(doc.get('subject_label', 'Joint Report'))} for <strong>{escape(doc.get('child_name') or 'their child')}</strong> with you.</p>"
                f'<p><a href="{app_url()}/joint/{rid}" style="color:#5B2A86">Open the shared report</a></p>'
                f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Share notification not sent to {pro['email']}")
    return {"ok": True, "shared_with": pro.get("name", body.email.lower())}


@api.get("/joint/connections")
async def list_connections(user=Depends(get_current_user)):
    uid = user["_id"]
    docs = await db.connections.find({"user_ids": uid}, {"_id": 0}).to_list(100)
    other_of = {c["id"]: next((u for u in c["user_ids"] if u != uid), None) for c in docs}
    other_ids = [oid for oid in other_of.values() if oid]
    user_map = {u["_id"]: u async for u in db.users.find({"_id": {"$in": other_ids}}, {"name": 1, "email": 1})} if other_ids else {}
    return [
        {
            "id": c["id"],
            "other_name": user_map.get(other_of[c["id"]], {}).get("name", "Co-parent"),
            "other_email": user_map.get(other_of[c["id"]], {}).get("email", ""),
            "child_name": c.get("child_name", ""),
        }
        for c in docs
    ]


@api.get("/joint/invitations/lookup/{token}")
async def lookup_invitation(token: str):
    inv = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not inv or inv["status"] != "pending":
        raise HTTPException(status_code=404, detail="This invitation is no longer valid")
    if invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired. Please ask the professional to send a fresh invitation.")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    pro = await db.users.find_one({"_id": report["created_by"]}, {"verification_level": 1}) if report and report.get("created_by") else None
    return {
        "inviter_name": inv["inviter_name"],
        "invitee_name": inv["invitee_name"],
        "invitee_email": inv["invitee_email"],
        "child_name": report["child_name"] if report else "",
        "subject_label": report["subject_label"] if report else "",
        "professional_verified": bool(pro and pro.get("verification_level") == "credentials_verified"),
        "assessment_url": invite_link(token),
    }


@api.post("/joint/invitations/accept")
async def accept_invitation(body: AcceptIn, user=Depends(get_current_user)):
    raw = body.code.strip()
    inv = await db.invitations.find_one({"status": "pending", "token": raw})
    if not inv:
        inv = await db.invitations.find_one({"status": "pending", "code": raw.upper(), "invitee_email": user["email"].lower()})
    if not inv:
        other = await db.invitations.find_one({"status": "pending", "code": raw.upper()})
        if other:
            raise HTTPException(status_code=403, detail="This invitation was sent to a different email address. Sign in with the email the invitation was sent to.")
        raise HTTPException(status_code=404, detail="Invalid or expired invitation code")
    if inv["invitee_email"] != user["email"].lower():
        raise HTTPException(status_code=403, detail="This invitation was sent to a different email address. Sign in with the email the invitation was sent to.")
    if invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired. Please ask the professional to send a fresh invitation.")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Joint report not found")
    role = inv["role"]
    await db.joint_reports.update_one(
        {"id": report["id"]},
        {"$set": {
            f"participants.{role}.user_id": user["_id"],
            f"participants.{role}.name": user.get("name") or inv["invitee_name"],
            "status": "in_progress",
        }},
    )
    await db.invitations.update_one(
        {"id": inv["id"]},
        {"$set": {"status": "accepted", "accepted_by": user["_id"], "accepted_at": datetime.now(timezone.utc).isoformat()}},
    )
    other_role = "b" if role == "a" else "a"
    other = report["participants"][other_role]
    if other.get("user_id"):
        pair = sorted([user["_id"], other["user_id"]])
        await db.connections.update_one(
            {"user_ids": pair},
            {"$setOnInsert": {"id": str(uuid.uuid4()), "user_ids": pair, "child_name": report["child_name"], "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return {"ok": True, "report_id": report["id"]}


@api.post("/joint/invitations/{iid}/resend")
async def resend_invitation(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can resend the invitation")
    if inv["status"] != "pending":
        raise HTTPException(status_code=400, detail="This invitation is no longer pending")
    if invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired. Reissue a fresh invitation instead.")
    if (await db.joint_reports.find_one({"id": inv["report_id"]}, {"joint_paused": 1}) or {}).get("joint_paused"):
        raise HTTPException(status_code=423, detail="This step isn't available right now. Your professional will follow up.")
    try:
        await send_invite_email(InviteSpec(
            report_id=inv["report_id"], role=inv["role"], invitee_name=inv["invitee_name"],
            invitee_email=inv["invitee_email"], inviter_name=inv["inviter_name"],
            child_name=report["child_name"], subject_label=report["subject_label"], code=inv["code"],
        ), inv["token"])
    except Exception:
        logger.warning(f"Invitation resend email not sent to {inv['invitee_email']}")
    return {"ok": True}


@api.post("/joint/invitations/{iid}/reissue")
async def reissue_invitation(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can reissue the invitation")
    if inv["status"] != "pending":
        raise HTTPException(status_code=400, detail="This invitation is no longer pending")
    now = datetime.now(timezone.utc).isoformat()
    await db.invitations.update_one({"id": iid}, {"$set": {"status": "expired", "expired_at": now}})
    new_inv = await create_invitation(InviteSpec(
        report_id=inv["report_id"], role=inv["role"], invitee_name=inv["invitee_name"],
        invitee_email=inv["invitee_email"], inviter_name=inv["inviter_name"],
        child_name=report["child_name"], subject_label=report["subject_label"], code=inv["code"],
    ))
    await db.access_events.insert_one({"report_id": report["id"], "action": f"Invitation reissued to Parent {'1' if inv['role'] == 'a' else '2'}", "at": now, "by": user["_id"]})
    return {"ok": True, **_pending_public([new_inv])[0]}


@api.get("/joint/invitations/{iid}/reminder-preview")
async def reminder_preview(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can preview the reminder")
    from safety_invites import build_invite_email
    subject, html, reply_to = await build_invite_email(inv["report_id"], inv["invitee_name"], inv["inviter_name"], inv["code"], inv["token"])
    return {"to": inv["invitee_email"], "subject": subject, "html": html, "reply_to": reply_to}


class NoteIn(BaseModel):
    text: str


class SessionOutcomeIn(BaseModel):
    chosen_steps: list[str] = []
    summary: str = ""
    follow_up_date: str = ""


@api.put("/joint/reports/{rid}/session-outcome")
async def save_session_outcome(rid: str, body: SessionOutcomeIn, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can record the session outcome")
    if not (report.get("responses", {}).get("a") and report.get("responses", {}).get("b")):
        raise HTTPException(status_code=400, detail="Record the outcome once both parents have completed and the session has taken place")
    follow_up = body.follow_up_date.strip()
    if follow_up and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", follow_up):
        raise HTTPException(status_code=400, detail="Follow-up date must be YYYY-MM-DD")
    steps = [s.strip()[:200] for s in body.chosen_steps if s.strip()][:12]
    now = datetime.now(timezone.utc).isoformat()
    outcome = {"chosen_steps": steps, "summary": body.summary.strip()[:2000], "follow_up_date": follow_up, "recorded_at": now, "recorded_by": user.get("name", "")}
    prev = report.get("session_outcome") or {}
    updates = {"session_outcome": outcome}
    if follow_up != prev.get("follow_up_date"):
        updates["follow_up_reminder_sent"] = None
    await db.joint_reports.update_one({"id": rid}, {"$set": updates})
    action = f"Session outcome recorded ({len(steps)} next step{'s' if len(steps) != 1 else ''} chosen"
    action += f", follow-up {follow_up})" if follow_up else ")"
    await db.access_events.insert_one({
        "report_id": rid, "kind": "lifecycle", "action": action,
        "at": now, "by": user["_id"], "by_name": user.get("name", ""), "by_role": "Assigned professional",
    })
    return {"ok": True, "session_outcome": outcome}


@api.post("/joint/reports/{rid}/notes")
async def add_professional_note(rid: str, body: NoteIn, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can add notes")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Note text is required")
    note = {"id": str(uuid.uuid4()), "report_id": rid, "author_id": user["_id"],
            "text": body.text.strip(), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.professional_notes.insert_one(note)
    return {"ok": True, "id": note["id"]}


@api.get("/joint/reports/{rid}/notes")
async def list_professional_notes(rid: str, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can view notes")
    return await db.professional_notes.find(
        {"report_id": rid, "author_id": user["_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)


@api.put("/joint/reports/{rid}/notes/{nid}")
async def edit_professional_note(rid: str, nid: str, body: NoteIn, user=Depends(get_current_user)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Note text is required")
    note = await db.professional_notes.find_one({"id": nid, "report_id": rid, "author_id": user["_id"]}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note["text"] == text:
        return {"ok": True, "unchanged": True}
    now = datetime.now(timezone.utc).isoformat()
    revision = {"text": note["text"], "at": note.get("updated_at") or note["created_at"]}
    await db.professional_notes.update_one({"id": nid}, {"$set": {"text": text, "updated_at": now}, "$push": {"revisions": revision}})
    return {"ok": True, "updated_at": now}


@api.delete("/joint/reports/{rid}/notes/{nid}")
async def delete_professional_note(rid: str, nid: str, user=Depends(get_current_user)):
    res = await db.professional_notes.delete_one({"id": nid, "report_id": rid, "author_id": user["_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@api.get("/verify/{case_code}/qr.png")
async def public_verify_qr(case_code: str):
    code = re.sub(r"[^A-Z0-9-]", "", case_code.strip().upper())[:20]
    if len(code) < 6:
        raise HTTPException(status_code=400, detail="Invalid case code")
    return Response(content=verify_qr_png(f"{app_url()}/verify?code={code}"), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@api.get("/verify/{case_code}")
async def public_verify_case(case_code: str):
    code = re.sub(r"[^A-Z0-9-]", "", case_code.strip().upper())[:20]
    if len(code) < 6:
        raise HTTPException(status_code=400, detail="Enter the case code from your invitation (e.g. SA-EDU-123456)")
    report = await db.joint_reports.find_one({"case_code": code}, {"_id": 0, "created_by": 1, "professional_id": 1, "subject_label": 1, "archived": 1, "created_at": 1})
    if not report:
        raise HTTPException(status_code=404, detail="No Professional Alignment Case matches that code. Check the code in your invitation email.")
    pro_id = report.get("professional_id") or report.get("created_by")
    pro = await db.users.find_one({"_id": pro_id, "role": "professional"}, {"name": 1, "approved": 1, "verification_level": 1, "profile": 1})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional is assigned to this case.")
    profile = pro.get("profile") or {}
    return {
        "case_code": code,
        "subject_label": report.get("subject_label", ""),
        "case_active": not report.get("archived"),
        "professional_name": pro.get("name", ""),
        "professional_role": profile.get("pro_role", ""),
        "organization": profile.get("organization", ""),
        "account_approved": bool(pro.get("approved")),
        "credentials_verified": pro.get("verification_level") == "credentials_verified",
    }


@api.get("/notes/search")
async def search_professional_notes(q: str = "", user=Depends(get_current_user)):
    needle = q.strip()
    if len(needle) < 2:
        return []
    notes = await db.professional_notes.find(
        {"author_id": user["_id"], "text": {"$regex": re.escape(needle), "$options": "i"}}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    rids = list({n["report_id"] for n in notes})
    reports = {r["id"]: r async for r in db.joint_reports.find({"id": {"$in": rids}}, {"_id": 0, "id": 1, "case_code": 1, "subject_label": 1, "child_name": 1, "archived": 1})}
    out = []
    for n in notes:
        r = reports.get(n["report_id"], {})
        child = (r.get("child_name") or "").strip()
        out.append({**n, "case_code": r.get("case_code", ""), "subject_label": r.get("subject_label", ""), "child_ref": f"{child[0].upper()}." if child else "", "archived": bool(r.get("archived"))})
    return out


COURT_COMM_KINDS = ("court_referral", "court_referral_declined", "court_submission", "hearing_date", "hearing_reminder", "court_packet", "court_packet_code", "court_response", "court_message")


def _comm_public(c: dict) -> dict:
    return {k: c.get(k) for k in ("id", "at", "kind", "to", "to_role", "subject", "provider")}


@api.get("/joint/reports/{rid}/communications")
async def case_communications(rid: str, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"] and report.get("professional_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the case professional can view the communications log")
    docs = await db.communications.find({"case_id": rid}, {"_id": 0}).sort("at", -1).to_list(500)
    return [_comm_public(c) for c in docs]


@api.get("/court-dashboard/referrals/{ref_id}/communications")
async def court_referral_communications(ref_id: str, user=Depends(get_current_user)):
    if user.get("role") != "judge" or not user.get("approved"):
        raise HTTPException(status_code=403, detail="Court accounts only")
    ref = await db.court_referrals.find_one({"id": ref_id, "judge_id": user["_id"]}, {"_id": 0})
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")
    ids = [ref_id] + ([ref["case_id"]] if ref.get("case_id") else [])
    docs = await db.communications.find({"case_id": {"$in": ids}, "kind": {"$in": list(COURT_COMM_KINDS)}}, {"_id": 0}).sort("at", -1).to_list(200)
    return [_comm_public(c) for c in docs]


COMM_KIND_LABELS = {
    "invitation": "Parent invitation", "completion_nudge": "Completion nudge", "report_ready": "Report ready notice", "follow_up_reminder": "Follow-up reminder",
    "court_referral": "Court referral", "court_referral_declined": "Referral declined", "court_submission": "Submission to court", "hearing_date": "Hearing date notice",
    "hearing_reminder": "Hearing reminder", "court_packet": "Court Packet sent", "court_packet_code": "Court Packet access code", "court_response": "Court response", "court_message": "Court–professional message",
}


def _mask_email(e: str) -> str:
    return f"{e[:2]}…@{e.split('@', 1)[1]}" if e and "@" in e else (e or "")


@api.get("/joint/reports/{rid}/communications.pdf")
async def case_communications_pdf(rid: str, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"] and report.get("professional_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the case professional can export the communications log")
    docs = await db.communications.find({"case_id": rid}, {"_id": 0}).sort("at", 1).to_list(1000)
    items = [{"at": c.get("at", ""), "kind_label": COMM_KIND_LABELS.get(c.get("kind"), c.get("kind") or "Email"), "subject": c.get("subject", ""),
              "to_role": c.get("to_role") or "", "to_masked": _mask_email(c.get("to", ""))} for c in docs]
    await _log_report_access(report, user, "Downloaded Communications Log", "download")
    code = re.sub(r"[^A-Za-z0-9-]", "", report.get("case_code") or rid[:8])
    pdf = build_communications_log_pdf({"case_code": report.get("case_code"), "subject_label": report.get("subject_label"), "child_name": report.get("child_name"),
                                        "professional_name": user.get("name"), "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "items": items})
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="communications-log-{code}.pdf"'})


@api.get("/joint/reports/{rid}/activity")
async def report_activity(rid: str, user=Depends(get_current_user)):
    report = await get_joint_report_doc(rid, user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the assigned professional can view activity")
    invs = await db.invitations.find({"report_id": rid}, {"_id": 0, "token": 0}).to_list(20)
    events = await db.access_events.find({"report_id": rid}, {"_id": 0}).sort("at", -1).to_list(300)
    access_log = [e for e in events if e.get("kind") in ("view", "download")]
    return {
        "invitations": invs, "access_events": [e for e in events if e.get("kind") not in ("view", "download", "lifecycle")],
        "lifecycle": [e for e in events if e.get("kind") == "lifecycle"],
        "access_log": access_log,
        "download_count": sum(1 for e in access_log if e["kind"] == "download"),
        "view_count": sum(1 for e in access_log if e["kind"] == "view"),
        "created_at": report.get("created_at"), "status": report.get("status"),
    }


@api.post("/joint/invitations/{iid}/cancel")
async def cancel_invitation(iid: str, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can cancel the invitation")
    await db.invitations.update_one({"id": iid}, {"$set": {"status": "cancelled"}})
    return {"ok": True}


@api.patch("/joint/invitations/{iid}")
async def change_invitation_subject(iid: str, body: PatchInvitationIn, user=Depends(get_current_user)):
    inv = await db.invitations.find_one({"id": iid}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    report = await get_joint_report_doc(inv["report_id"], user)
    if report.get("created_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the report creator can change the subject")
    if body.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail="Unknown subject")
    if report["subject"] == "multi":
        raise HTTPException(status_code=400, detail="Subject change is not available for customized reports")
    if report["status"] == "ready":
        raise HTTPException(status_code=400, detail="The subject cannot be changed after both parents have completed")
    label = body.custom_subject.strip() if body.subject == "custom" else SUBJECTS[body.subject]["label"]
    if body.subject == "custom" and not label:
        label = "Custom Subject"
    await db.joint_reports.update_one({"id": report["id"]}, {"$set": {"subject": body.subject, "subject_label": label}})
    return {"ok": True, "subject_label": label}


class AgreementIn(BaseModel):
    child_name: str
    parent_a_name: str
    parent_a_email: EmailStr
    parent_b_name: str
    parent_b_email: EmailStr


@api.post("/joint/agreements")
async def create_agreement(body: AgreementIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Co-parenting agreements are initiated by an authorized professional. Parents participate through a secure invitation.")
    rid = str(uuid.uuid4())
    case_code = new_case_code("co_parenting", kind="agreement")
    pa_email = str(body.parent_a_email).lower()
    pb_email = str(body.parent_b_email).lower()
    doc = {
        "id": rid,
        "kind": "agreement",
        "subject": "co_parenting",
        "subjects": ["co_parenting"],
        "subject_label": "Co-Parenting Agreement",
        "is_safety": False,
        "case_code": case_code,
        "child_name": body.child_name.strip(),
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": body.parent_a_name.strip(), "email": pa_email},
            "b": {"user_id": None, "name": body.parent_b_name.strip(), "email": pb_email},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.joint_reports.insert_one(doc)
    inv_a = await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=body.parent_a_name, invitee_email=pa_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label="Co-Parenting Agreement", code=case_code, via_professional=True))
    inv_b = await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=body.parent_b_name, invitee_email=pb_email, inviter_name=user.get("name", "A professional"), child_name=doc["child_name"], subject_label="Co-Parenting Agreement", code=case_code, via_professional=True))
    return {**joint_public(doc, user), "invitations": [
        {"id": inv_a["id"], "role": "a", "code": inv_a["code"], "link": invite_link(inv_a["token"]), "invitee_email": inv_a["invitee_email"], "email": inv_a["invitee_email"], "status": "pending"},
        {"id": inv_b["id"], "role": "b", "code": inv_b["code"], "link": invite_link(inv_b["token"]), "invitee_email": inv_b["invitee_email"], "email": inv_b["invitee_email"], "status": "pending"},
    ]}


class InvitePreviewIn(BaseModel):
    child_name: str
    subject: str = ""
    subjects: list[str] = []
    custom_subject: str = ""
    parent_a_name: str
    parent_a_email: str = ""
    parent_b_name: str
    parent_b_email: str = ""


@api.post("/joint/invitations/preview")
async def preview_invitations(body: InvitePreviewIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Only approved professionals can preview invitations")
    _subject, _keys, label = resolve_subjects(body.subject, body.subjects, body.custom_subject)
    inviter = user.get("name", "A professional")
    out = []
    for role, name, email in (("a", body.parent_a_name, body.parent_a_email), ("b", body.parent_b_name, body.parent_b_email)):
        spec = InviteSpec(report_id="preview", role=role, invitee_name=name.strip() or f"Parent {role.upper()}", invitee_email=email.strip().lower(),
                          inviter_name=inviter, child_name=body.child_name.strip(), subject_label=label, code="SA-26-XXX-PREVIEW", via_professional=True)
        from safety_invites import professional_template
        subject, html = professional_template(spec.invitee_name, inviter, spec.code, "PREVIEW-TOKEN")
        out.append({"role": role, "to": spec.invitee_email, "subject": subject, "html": html, "reply_to": user.get("email")})
    return {"previews": out}


class ProRequestIn(BaseModel):
    professional_email: EmailStr
    child_name: str
    co_parent_name: str = ""
    co_parent_email: EmailStr | None = None


class PrepareIn(BaseModel):
    parent_a_email: EmailStr | None = None
    parent_b_email: EmailStr | None = None
    parent_b_name: str | None = None


@api.get("/professionals")
async def list_professionals(user=Depends(get_current_user)):
    return await db.users.find({"role": "professional", "approved": {"$ne": False}}, {"_id": 0, "name": 1, "email": 1, "verification_level": 1}).sort("name", 1).to_list(5000)


def _directory_entry(u: dict) -> dict:
    p = u.get("profile") or {}
    return {
        "id": u["_id"], "name": u.get("name", ""), "email": u["email"],
        "pro_role": p.get("pro_role", ""), "organization": p.get("organization", ""),
        "phone": p.get("phone", ""), "city": p.get("city", ""), "state": p.get("state", ""),
        "credentials_verified": u.get("verification_level") == "credentials_verified",
    }


@api.get("/professionals/directory")
async def professionals_directory(user=Depends(get_current_user)):
    require_approved_professional(user, "The professional directory is available to approved professionals")
    docs = await db.users.find(
        {"role": {"$in": list(PRO_ROLES)}, "approved": True},
        {"password_hash": 0},
    ).sort("name", 1).to_list(5000)
    return [_directory_entry(u) for u in docs]


class ReferIn(BaseModel):
    message: str = ""
    report_id: str | None = None


async def _referral_matter_line(user: dict, report_id: str | None) -> tuple[str, str]:
    if not report_id:
        return "", ""
    rep = await db.joint_reports.find_one({"id": report_id, "created_by": user["_id"]}, {"_id": 0, "case_code": 1, "subject_label": 1})
    if not rep:
        raise HTTPException(status_code=404, detail="Matter not found")
    code = rep.get("case_code", "")
    return f"<p><strong>Matter:</strong> {escape(rep.get('subject_label', 'Joint Report'))} — Alignment Case {escape(code)}</p>", code


def _referral_html(user: dict, colleague: dict, matter_line: str, message: str) -> str:
    p = user.get("profile") or {}
    contact = ", ".join(x for x in (user["email"], p.get("phone", "")) if x)
    credentials = f" ({escape(p.get('pro_role'))}, {escape(p.get('organization'))})" if p.get("pro_role") and p.get("organization") else ""
    quote = f"<blockquote style=\"border-left:3px solid #5B2A86;padding-left:12px;color:#333\">{escape(message)}</blockquote>" if message else ""
    return _pro_email_wrap(
        f"<p>Hi {escape(colleague.get('name') or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'A colleague'))}</strong>{credentials}"
        " would like to refer a family matter to you through the SA CoParents Align professional directory.</p>"
        + matter_line + quote
        + f"<p>Reply directly to the referring professional: {escape(contact)}.</p>"
        "<p style=\"font-size:13px;color:#555\">No parent information or report content is shared by this message. "
        "Report access is granted only through the professional's secure case invitation.</p>")


@api.post("/professionals/{pro_id}/refer")
async def refer_to_professional(pro_id: str, body: ReferIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Only approved professionals can refer cases")
    if pro_id == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot refer a case to yourself")
    colleague = await db.users.find_one({"_id": pro_id, "role": {"$in": list(PRO_ROLES)}, "approved": True})
    if not colleague:
        raise HTTPException(status_code=404, detail="Professional not found")
    matter_line, case_code = await _referral_matter_line(user, body.report_id)
    message = body.message.strip()
    await send_email(
        to=colleague["email"],
        subject=f"Case referral from {user.get('name', 'a colleague')} - {EMAIL_FROM_NAME}",
        html=_referral_html(user, colleague, matter_line, message),
        reply_to=user["email"],
    )
    now = datetime.now(timezone.utc).isoformat()
    await db.referrals.insert_one({"id": str(uuid.uuid4()), "from_id": user["_id"], "from_name": user.get("name", ""), "to_id": pro_id, "to_name": colleague.get("name", ""),
                                   "report_id": body.report_id, "case_code": case_code, "message": message[:1000], "status": "pending", "at": now})
    return {"ok": True, "to": colleague.get("name", colleague["email"])}


def _referral_public(r: dict) -> dict:
    return {k: r.get(k) for k in ("id", "from_id", "from_name", "to_id", "to_name", "report_id", "case_code", "message", "status", "at", "responded_at", "response_note")}


@api.get("/professionals/referrals")
async def list_referrals(user=Depends(get_current_user)):
    require_approved_professional(user, "Only approved professionals can view referrals")
    received = await db.referrals.find({"to_id": user["_id"]}, {"_id": 0}).sort("at", -1).to_list(200)
    sent = await db.referrals.find({"from_id": user["_id"]}, {"_id": 0}).sort("at", -1).to_list(200)
    return {"received": [_referral_public(r) for r in received], "sent": [_referral_public(r) for r in sent]}


class ReferralRespondIn(BaseModel):
    accept: bool
    note: str = ""


@api.post("/professionals/referrals/{ref_id}/respond")
async def respond_referral(ref_id: str, body: ReferralRespondIn, user=Depends(get_current_user)):
    require_approved_professional(user, "Only approved professionals can respond to referrals")
    ref = await db.referrals.find_one({"id": ref_id, "to_id": user["_id"]})
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")
    if ref.get("status", "pending") != "pending":
        raise HTTPException(status_code=400, detail="This referral has already been answered")
    now = datetime.now(timezone.utc).isoformat()
    status = "accepted" if body.accept else "declined"
    note = body.note.strip()[:500]
    await db.referrals.update_one({"id": ref_id}, {"$set": {"status": status, "responded_at": now, "response_note": note}})
    referrer = await db.users.find_one({"_id": ref["from_id"]}, {"email": 1, "name": 1})
    if referrer:
        await send_email(
            to=referrer["email"],
            subject=f"Referral {status} by {user.get('name', 'a colleague')} - {EMAIL_FROM_NAME}",
            html=_pro_email_wrap(
                f"<p>Hi {escape(referrer.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'Your colleague'))}</strong> has <strong>{status}</strong> the case referral you sent"
                + (f" regarding Alignment Case {escape(ref['case_code'])}" if ref.get("case_code") else "") + ".</p>"
                + (f"<blockquote style=\"border-left:3px solid #5B2A86;padding-left:12px;color:#333\">{escape(note)}</blockquote>" if note else "")
                + f"<p>Reply directly: {escape(user['email'])}.</p>"),
            reply_to=user["email"],
        )
    return {"ok": True, "status": status}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _pro_req_status(d: dict) -> str:
    if d["status"] == "pending" and d.get("expires_at") and d["expires_at"] < datetime.now(timezone.utc).isoformat():
        return "expired"
    return d["status"]


def _pro_req_public(d: dict) -> dict:
    return {
        "id": d["id"], "child_name": d["child_name"], "parent_name": d["parent_name"],
        "parent_email": d["parent_email"], "co_parent_name": d["co_parent_name"],
        "co_parent_email": d.get("co_parent_email"), "professional_name": d.get("professional_name", ""),
        "status": _pro_req_status(d), "created_at": d["created_at"], "expires_at": d.get("expires_at"),
        "decided_at": d.get("decided_at"), "events": d.get("events", []),
    }




async def _notify_parent(req: dict, subject: str, inner_html: str) -> None:
    try:
        await send_email(to=req["parent_email"], subject=f"{subject} - {EMAIL_FROM_NAME}", html=_pro_email_wrap(inner_html))
    except Exception:
        logger.warning(f"Parent notification not sent to {req['parent_email']}")


@api.post("/joint/professional-requests")
async def create_pro_request(body: ProRequestIn, user=Depends(get_current_user)):
    pro = await db.users.find_one({"email": body.professional_email.lower(), "role": "professional"})
    if not pro:
        raise HTTPException(status_code=404, detail="No professional account found with that email")
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    req = {
        "id": str(uuid.uuid4()),
        "parent_id": user["_id"],
        "parent_name": user.get("name", ""),
        "parent_email": user["email"],
        "co_parent_name": body.co_parent_name.strip(),
        "co_parent_email": body.co_parent_email.lower() if body.co_parent_email else None,
        "child_name": body.child_name.strip(),
        "professional_id": pro["_id"],
        "professional_email": pro["email"].lower(),
        "professional_name": pro.get("name", ""),
        "status": "pending",
        "token_hash": _hash_token(token),
        "token_used_at": None,
        "expires_at": (now + timedelta(hours=PRO_INVITE_TTL_HOURS)).isoformat(),
        "events": [{"type": "sent", "at": now.isoformat(), "by": "parent"}],
        "created_at": now.isoformat(),
    }
    await db.professional_requests.insert_one(req)
    try:
        await send_email(
            to=pro["email"],
            subject=f"Family violence assessment facilitation request - {EMAIL_FROM_NAME}",
            html=_pro_email_wrap(
                f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
                f"<p><strong>{escape(user.get('name', 'A parent'))}</strong> has asked you to facilitate a joint "
                f"family violence co-parenting assessment regarding <strong>{escape(req['child_name'])}</strong>.</p>"
                "<p>Full parent details are shown after you open the secure invitation while signed in with your "
                f"verified professional account (<strong>{escape(pro['email'])}</strong>).</p>"
                f'<p><a href="{app_url()}/accept-invite?token={token}" style="color:#5B2A86;font-weight:bold">Review this invitation</a></p>'
                f"<p style=\"font-size:13px;color:#555\">This link is single-use and expires in {PRO_INVITE_TTL_HOURS} hours. "
                "Please do not forward it — it is tied to your professional email address. You may accept, decline, "
                "request more information, or report a conflict of interest.</p>"
            ),
        )
    except Exception:
        logger.warning(f"Professional request email not sent to {pro['email']}")
    return {"ok": True, "id": req["id"]}


@api.get("/joint/professional-requests/lookup")
async def lookup_pro_request(token: str, user=Depends(get_current_user)):
    req = await db.professional_requests.find_one({"token_hash": _hash_token(token)}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="This invitation link is not valid")
    if (user.get("email") or "").lower() != req.get("professional_email"):
        raise HTTPException(status_code=403, detail="This invitation was sent to a different professional email address. Sign in with the invited account.")
    status = _pro_req_status(req)
    if status == "expired":
        raise HTTPException(status_code=410, detail=f"This invitation expired after {PRO_INVITE_TTL_HOURS} hours. Ask the parent to send a new one.")
    if req.get("token_used_at") or status != "pending":
        raise HTTPException(status_code=410, detail="This invitation link has already been used")
    return {"id": req["id"], "parent_name": req["parent_name"], "child_name": req["child_name"],
            "created_at": req["created_at"], "expires_at": req["expires_at"], "status": status}


@api.get("/joint/professional-requests")
async def list_pro_requests(user=Depends(get_current_user)):
    if is_pro(user):
        docs = await db.professional_requests.find({"professional_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    else:
        docs = await db.professional_requests.find({"parent_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [_pro_req_public(d) for d in docs]


class DecisionIn(BaseModel):
    reason: str = ""


async def _load_pending_pro_request(req_id: str, user: dict) -> dict:
    require_approved_professional(user, "Only professional accounts can respond to invitations")
    req = await db.professional_requests.find_one({"id": req_id, "professional_id": user["_id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    status = _pro_req_status(req)
    if status == "expired":
        raise HTTPException(status_code=410, detail=f"This invitation expired after {PRO_INVITE_TTL_HOURS} hours")
    if status != "pending":
        raise HTTPException(status_code=400, detail="This invitation has already been answered")
    return req


async def _decide_pro_request(req: dict, new_status: str, event: str, reason: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.professional_requests.update_one(
        {"id": req["id"]},
        {"$set": {"status": new_status, "decided_at": now, "token_used_at": now},
         "$push": {"events": {"type": event, "at": now, "by": "professional", "note": reason[:500]}}},
    )


@api.post("/joint/professional-requests/{req_id}/decline")
async def decline_pro_request(req_id: str, body: DecisionIn | None = None, user=Depends(get_current_user)):
    req = await _load_pending_pro_request(req_id, user)
    reason = (body.reason if body else "").strip()
    await _decide_pro_request(req, "declined", "declined", reason)
    await _notify_parent(req, "Professional unable to accept your request",
        f"<p>Hi {escape(req['parent_name'] or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'The professional'))}</strong> is unable to facilitate the assessment you requested "
        f"regarding <strong>{escape(req['child_name'])}</strong>.</p>"
        + (f"<p><strong>Note from the professional:</strong> {escape(reason)}</p>" if reason else "")
        + "<p>You may invite a different professional from your dashboard.</p>")
    return {"ok": True, "status": "declined"}


@api.post("/joint/professional-requests/{req_id}/request-info")
async def request_info_pro_request(req_id: str, body: DecisionIn, user=Depends(get_current_user)):
    req = await _load_pending_pro_request(req_id, user)
    message = body.reason.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please describe what additional information you need")
    now = datetime.now(timezone.utc).isoformat()
    await db.professional_requests.update_one(
        {"id": req["id"]},
        {"$push": {"events": {"type": "info_requested", "at": now, "by": "professional", "note": message[:1000]}}},
    )
    await _notify_parent(req, "A professional has a question about your request",
        f"<p>Hi {escape(req['parent_name'] or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'The professional'))}</strong> needs more information before deciding on your "
        f"request regarding <strong>{escape(req['child_name'])}</strong>:</p>"
        f"<blockquote style=\"border-left:3px solid #5B2A86;padding-left:12px;color:#333\">{escape(message)}</blockquote>"
        f"<p>Reply to this email or contact the professional directly. The invitation remains open until {escape(str(req['expires_at'])[:16].replace('T', ' '))} UTC.</p>")
    return {"ok": True, "status": "pending"}


@api.post("/joint/professional-requests/{req_id}/conflict")
async def conflict_pro_request(req_id: str, body: DecisionIn | None = None, user=Depends(get_current_user)):
    req = await _load_pending_pro_request(req_id, user)
    await _decide_pro_request(req, "declined_conflict", "conflict_reported", (body.reason if body else "").strip())
    await _notify_parent(req, "Professional unable to accept your request",
        f"<p>Hi {escape(req['parent_name'] or 'there')},</p>"
        f"<p><strong>{escape(user.get('name', 'The professional'))}</strong> is unable to facilitate the assessment you requested "
        f"regarding <strong>{escape(req['child_name'])}</strong> because of a potential conflict of interest.</p>"
        "<p>This is a routine professional safeguard. You may invite a different professional from your dashboard.</p>")
    return {"ok": True, "status": "declined_conflict"}


def _first_email(*candidates) -> str:
    for c in candidates:
        if c:
            return str(c).lower()
    return ""


def _resolve_prepare_parties(req: dict, body: "PrepareIn | None") -> tuple:
    pa_email = _first_email(body.parent_a_email if body else None, req["parent_email"])
    pb_email = _first_email(body.parent_b_email if body else None, req.get("co_parent_email"))
    pb_name = ((body.parent_b_name or "").strip() if body else "") or req.get("co_parent_name") or "Co-parent"
    if not pb_email:
        raise HTTPException(status_code=400, detail="Please provide both parents' email addresses so each receives their private assessment")
    return pa_email, pb_email, pb_name


def _safety_case_doc(user: dict, req: dict, pa_email: str, pb_email: str, pb_name: str) -> dict:
    rid = str(uuid.uuid4())
    return {
        "id": rid,
        "kind": "joint_report",
        "subject": "multi",
        "subjects": sorted(SAFETY_SUBJECT_KEYS),
        "subject_label": "Family Violence & Safety Assessment",
        "is_safety": True,
        "case_code": new_case_code("safety"),
        "child_name": req["child_name"],
        "created_by": user["_id"],
        "creator_role": "professional",
        "professional_id": user["_id"],
        "professional_name": user.get("name", ""),
        "shared_with": [],
        "participants": {
            "a": {"user_id": None, "name": req["parent_name"], "email": pa_email},
            "b": {"user_id": None, "name": pb_name, "email": pb_email},
        },
        "responses": {},
        "status": "pending_invite",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@api.post("/joint/professional-requests/{req_id}/prepare")
async def prepare_pro_request(req_id: str, body: PrepareIn | None = None, user=Depends(get_current_user)):
    require_approved_professional(user, "Only professional accounts can prepare assessments")
    req = await _load_pending_pro_request(req_id, user)
    pa_email, pb_email, pb_name = _resolve_prepare_parties(req, body)
    doc = _safety_case_doc(user, req, pa_email, pb_email, pb_name)
    rid = doc["id"]
    case_code = doc["case_code"]
    await db.joint_reports.insert_one(doc)
    await create_invitation(InviteSpec(report_id=rid, role="a", invitee_name=req["parent_name"], invitee_email=pa_email, inviter_name=user.get("name", "A professional"), child_name=req["child_name"], subject_label=doc["subject_label"], code=case_code, via_professional=True))
    await create_invitation(InviteSpec(report_id=rid, role="b", invitee_name=pb_name, invitee_email=pb_email, inviter_name=user.get("name", "A professional"), child_name=req["child_name"], subject_label=doc["subject_label"], code=case_code, via_professional=True))
    now = datetime.now(timezone.utc).isoformat()
    await db.professional_requests.update_one(
        {"id": req_id},
        {"$set": {"status": "prepared", "report_id": rid, "prepared_at": now, "decided_at": now, "token_used_at": now},
         "$push": {"events": {"type": "accepted", "at": now, "by": "professional"}}},
    )
    return {"ok": True, "report_id": rid}


@api.get("/health")
async def api_health():
    return {"status": "healthy", "build": BUILD_ID}


api.include_router(auth.router)
api.include_router(admin_routes.router)
import pro_invites as _pro_invites  # noqa: E402
api.include_router(_pro_invites.router)
api.include_router(integrations.router)
api.include_router(cron_jobs.router)
app.include_router(api)
from court_packets import build_router as _build_court_router  # noqa: E402
app.include_router(_build_court_router(db, get_current_user, app_url, send_email, EMAIL_FROM_NAME, logger), prefix="/api")
from court_workflow import build_router as _build_workflow_router  # noqa: E402




app.include_router(_build_workflow_router(db, get_current_user, app_url, send_email, EMAIL_FROM_NAME, logger, _log_lifecycle), prefix="/api")
from legal_report import build_router as _build_legal_router  # noqa: E402
app.include_router(_build_legal_router(db, get_current_user, _log_lifecycle), prefix="/api")
from legal_lens import build_router as _build_lens_router  # noqa: E402
app.include_router(_build_lens_router(db, get_current_user, _log_lifecycle), prefix="/api")
from providers import build_router as _build_providers_router  # noqa: E402
app.include_router(_build_providers_router(db, get_current_user), prefix="/api")
from safety_screening import build_router as _build_safety_router  # noqa: E402
app.include_router(_build_safety_router(db, get_current_user, get_joint_report_doc, report_role, _log_report_access), prefix="/api")
from privacy_notice import build_router as _build_privacy_router  # noqa: E402
app.include_router(_build_privacy_router(db, get_current_user), prefix="/api")
from professional_notice import build_router as _build_pro_notice_router  # noqa: E402
app.include_router(_build_pro_notice_router(db, get_current_user), prefix="/api")
from bridge_views import build_router as _build_bridge_views  # noqa: E402
app.include_router(_build_bridge_views(_log_report_access), prefix="/api")
from joint_pause import build_router as _build_pause_router  # noqa: E402
app.include_router(_build_pause_router(db, get_current_user, get_joint_report_doc, _log_report_access), prefix="/api")
from safety_screening import comm_router as _comm_router  # noqa: E402
app.include_router(_comm_router(db, get_current_user, get_joint_report_doc, report_role), prefix="/api")
from safety_pathway import build_router as _build_pathway_router  # noqa: E402
from safety_invites import build_router as _build_invites_router  # noqa: E402
from safety_status_webhook import build_router as _build_webhook_router  # noqa: E402
from safety_review import build_router as _build_review_router  # noqa: E402
from pro_training import build_router as _build_training_router  # noqa: E402
app.include_router(_build_training_router(db, get_current_user), prefix="/api")
from safety_screening import _status as _screening_status  # noqa: E402
_is_case_pro = lambda doc, user: user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))  # noqa: E731
app.include_router(_build_invites_router(get_current_user, get_joint_report_doc, _log_report_access, _is_case_pro), prefix="/api")
app.include_router(_build_webhook_router(get_current_user), prefix="/api")
app.include_router(_build_review_router(get_current_user, get_joint_report_doc, _log_report_access, _is_case_pro, _screening_status), prefix="/api")
app.include_router(_build_pathway_router(db, get_current_user, get_joint_report_doc, _log_report_access, lambda doc, user: user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))), prefix="/api")
from foundation import build_router as _build_foundation_router  # noqa: E402
app.include_router(_build_foundation_router(db, get_current_user, get_joint_report_doc, report_role), prefix="/api")
from ai_tools import build_router as _build_ai_tools_router  # noqa: E402
from legal_lens import LensStore as _LensStore  # noqa: E402
app.include_router(_build_ai_tools_router(db, get_current_user, _LensStore(db, _log_lifecycle).own_case, get_joint_report_doc, report_role), prefix="/api")
from assistant import build_router as _build_assistant_router  # noqa: E402
app.include_router(_build_assistant_router(get_current_user), prefix="/api")
from pro_profile import build_router as _build_pro_profile_router  # noqa: E402
app.include_router(_build_pro_profile_router(get_current_user), prefix="/api")

from research import build_router as _build_research_router  # noqa: E402
app.include_router(_build_research_router(db, get_current_user), prefix="/api")
from tts import build_router as _build_tts_router  # noqa: E402
app.include_router(_build_tts_router(db), prefix="/api")
from public_listing import build_router as _build_public_listing_router  # noqa: E402
app.include_router(_build_public_listing_router(db, get_current_user), prefix="/api")
from joint_ai import build_router as _build_joint_ai_router  # noqa: E402
app.include_router(_build_joint_ai_router(db, get_current_user, get_joint_report_doc), prefix="/api")


@app.get("/health")
async def health():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://assets.emergent.sh; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; "
        "font-src 'self' data:; connect-src 'self' https: wss:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", _CSP)
    return response


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

