"""sacoparentsapp.online integration + external account linking + complete alignment report."""







import os
import secrets
import uuid
from datetime import datetime, timezone

from html import escape



import httpx  # noqa: F401  (patched by tests)
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel









from pdf_report import build_complete_pdf
from complete_engine import build_complete_report

from email_utils import send_email, EMAIL_FROM_NAME
from core import db, logger, app_url, INTEGRATION_SECRET

# --- Parent-app link contract (2026-10-14). Flag PARENT_APP_LINK_CONTRACT defaults OFF = current behaviour. -----------
from parent_app_contract import (case_context, verify_link_code as _verify_link_code,  # noqa: E402
                                 export_assessments as _export_assessments)
DENIED_DETAIL = "The SA CoParents service did not release information for this link. Ask the parent to confirm the link for this case, then try again."
from auth import get_current_user
from joint_helpers import get_joint_report_doc, report_role, invite_expired, joint_public

router = APIRouter()


# ---------- Joint Alignment Case integration (sacoparentsapp.online → Align) ----------


def check_integration_key(request: Request):
    if not secrets.compare_digest(request.headers.get("x-integration-key") or "", INTEGRATION_SECRET):
        raise HTTPException(status_code=401, detail="Invalid integration key")


async def _alert_bridge_write(report: dict, role: str, request: Request, fields: list[str]) -> None:
    """Every bridge write is logged (no PII) and surfaced to the admin inbox so a leaked key cannot act silently."""
    now = datetime.now(timezone.utc).isoformat()
    await db.access_events.insert_one({"id": str(uuid.uuid4()), "report_id": report["id"], "kind": "integration_write", "role": role, "fields": fields, "ip": request.client.host if request.client else None, "at": now})
    logger.info("integration write case=%s role=%s fields=%s", report["id"], role, ",".join(fields))
    admin = os.environ.get("ADMIN_EMAIL")
    if not admin:
        return
    try:
        await send_email(to=admin, subject=f"Bridge write on Case {report.get('case_code') or report['id'][:8]} - {EMAIL_FROM_NAME}",
                         html=f"<p>The sacoparentsapp.online bridge wrote to Parent {role.upper()} on case {escape(report.get('case_code') or report['id'][:8])} at {now[:19]}Z.</p><p>Fields: {escape(', '.join(fields))}. No answer content is included in this alert.</p><p>If this was not expected, rotate INTEGRATION_SHARED_SECRET immediately.</p>",
                         case_id=report["id"], kind="integration_write_alert", to_role="Admin")
    except Exception:
        logger.warning("Bridge write alert not sent for case %s", report["id"])


@router.get("/integrations/safety-screening-spec")
async def integration_safety_spec(request: Request):
    """Server-to-server: the parent app pulls the canonical Version A/B/C spec so wording and tiers stay identical."""
    check_integration_key(request)
    from safety_screening import spec_export
    return spec_export()


@router.get("/integrations/case-invite/{token}")
async def integration_case_invite(token: str, request: Request):
    check_integration_key(request)
    inv = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation token")
    if inv["status"] == "pending" and invite_expired(inv):
        raise HTTPException(status_code=410, detail="This invitation has expired")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "case_id": report.get("case_code") or report["id"],
        "report_id": report["id"],
        "assessment_type": report["subject_label"],
        "child_name": report.get("child_name", ""),
        "parent_role": inv["role"],
        "parent_name": inv.get("invitee_name", ""),
        "parent_email": inv["invitee_email"],
        "professional_name": report.get("professional_name"),
        "professional_id": report.get("professional_id") or report.get("created_by"),
        "requested_by": inv.get("inviter_name", ""),
        "invitation_status": inv["status"],
        "case_status": report["status"],
    }


class CaseUpdateIn(BaseModel):
    token: str
    status: str = "readiness"
    assessment_id: str = ""
    responses: dict | None = None
    communication_readiness: dict | None = None
    foundation_statement: dict | None = None  # parent/role/email fields in the body are ignored: the invitation record decides


FOUNDATION_SOURCE = "sacoparentsapp.online"


def _foundation_update(role: str, body: "CaseUpdateIn", now: str, invitation_id: str | None = None) -> dict:
    """Foundation Statement pushed by the parent app. Held privately for THIS parent (foundation_imports.<role>) until they include it themselves."""
    fs = body.foundation_statement
    if not isinstance(fs, dict):
        raise HTTPException(status_code=400, detail="foundation_statement (object) is required")
    from foundation import _clean, to_text
    from safety_import import _date
    structured = _clean(fs["fields"]) if isinstance(fs.get("fields"), dict) else None
    if structured and not any(v for k, v in structured.items() if k != "child_name"):
        structured = None
    content = str(fs.get("content") or "").strip()[:5000] or (to_text(structured)[:5000] if structured else "")
    if not content:
        raise HTTPException(status_code=400, detail="foundation_statement needs 'content' (text) or 'fields' with at least one Foundation section")
    entry = {"title": (str(fs.get("title") or "").strip() or "Child-Focused Foundation Statement")[:120], "content": content, "structured": structured,
             "completed_at": _date(fs.get("completed_at")) or None, "received_at": now, "source": FOUNDATION_SOURCE, "invitation_id": invitation_id}
    return {f"foundation_imports.{role}": entry}


def _readiness_update(role: str, body: "CaseUpdateIn") -> dict:
    """Communication Style results pushed by the parent app (parent chose to share). Only the four readiness ids are kept."""
    comm = body.communication_readiness
    if not isinstance(comm, dict) or not isinstance(comm.get("responses"), dict):
        raise HTTPException(status_code=400, detail="communication_readiness.responses (object) is required")
    from safety_import import _date
    from safety_screening import comm_record
    rec = comm_record(comm["responses"], source="sacoparentsapp.online", completed_at=_date(comm.get("completed_at")) or None)
    if not rec["responses"]:
        raise HTTPException(status_code=400, detail="No recognised readiness answers (cr_conflict, cr_direct, cr_channel, cr_child)")
    return {f"communication_readiness.{role}": rec}


def _compute_case_updates(report: dict, role: str, body: "CaseUpdateIn", now: str, invitation_id: str | None = None) -> dict:
    if body.status == "foundation" or (body.foundation_statement is not None and body.responses is None and body.communication_readiness is None):
        return _foundation_update(role, body, now, invitation_id)
    if body.status == "readiness" or (body.communication_readiness is not None and body.responses is None):
        return _readiness_update(role, body)
    if body.status == "started":
        return {"status": "in_progress"} if report["status"] == "pending_invite" else {}
    if body.status != "completed":
        raise HTTPException(status_code=400, detail="Unknown status — use 'started', 'completed', 'readiness' or 'foundation'")
    answers = {k: str(v)[:5000] for k, v in (body.responses or {}).items()}
    updates = {
        f"responses.{role}": {
            "answers": answers,
            "completed_at": now,
            "imported": True,
            "external": {
                "assessment_id": body.assessment_id,
                "source": "sacoparentsapp.online",
                "assessments": [{"title": report["subject_label"], "responses": answers}],
            },
        }
    }
    other = "b" if role == "a" else "a"
    if (report.get("responses") or {}).get(other):
        updates["status"] = "ready"
    elif report["status"] == "pending_invite":
        updates["status"] = "in_progress"
    return updates


async def _notify_case_ready(report: dict) -> None:
    notify_id = report.get("professional_id") or report.get("created_by")
    notify = await db.users.find_one({"_id": notify_id}) if notify_id else None
    if not notify:
        return
    try:
        await send_email(
            to=notify["email"],
            subject=f"Joint Alignment Report ready - {report.get('case_code') or report['id']} - {EMAIL_FROM_NAME}",
            case_id=report["id"], kind="report_ready", to_role="Professional",
            html=(
                '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Hi {escape(notify.get('name') or 'there')},</p>"
                f"<p>Both parents have completed their private assessments for case "
                f"<strong>{escape(report.get('case_code') or report['id'])}</strong> "
                f"({escape(report['subject_label'])}, {escape(report.get('child_name') or 'child')}).</p>"
                f'<p><a href="{app_url()}/joint/{report["id"]}" style="display:inline-block;background:#5B2A86;color:#ffffff;'
                'padding:12px 24px;text-decoration:none;border-radius:6px">Generate Joint Alignment Report</a></p>'
                f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}.</p>'
                "</td></tr></table>"
            ),
        )
    except Exception:
        logger.warning(f"Case-ready notification not sent for {report['id']}")


@router.post("/integrations/case-update")
async def integration_case_update(body: CaseUpdateIn, request: Request):
    check_integration_key(request)
    inv = await db.invitations.find_one({"token": body.token}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    report = await db.joint_reports.find_one({"id": inv["report_id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Case not found")
    now = datetime.now(timezone.utc).isoformat()
    updates = _compute_case_updates(report, inv["role"], body, now, inv.get("id"))
    if inv["status"] == "pending":
        await db.invitations.update_one({"id": inv["id"]}, {"$set": {"status": "accepted", "accepted_at": now}})
    if updates:
        await db.joint_reports.update_one({"id": report["id"]}, {"$set": updates})
        await _alert_bridge_write(report, inv["role"], request, sorted(k.split(".")[0] for k in updates))
    if any(k.startswith("foundation_imports.") for k in updates):
        await _notify_foundation_arrival(report, inv)
    if updates.get("status") == "ready":
        await _notify_case_ready(report)
    return {"ok": True, "case_status": updates.get("status", report["status"])}


FOUNDATION_ARRIVAL_SUBJECT = "Something you sent has arrived - SA CoParents"
FOUNDATION_ARRIVAL_HTML = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                           "<p>Hi {name},</p>"
                           "<p>The statement you sent from the SA CoParents app has arrived in your SA CoParents account. It is private to you: nobody else can see it until you choose to include it in your case.</p>"
                           '<p><a href="{link}" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Sign in to review it</a></p>'
                           '<p style="font-size:12px;color:#888">Sent by {from_name}. We never ask for your password by email.</p></td></tr></table>')


async def _notify_foundation_arrival(report: dict, inv: dict) -> None:
    """Neutral, content-free arrival email to the invitation address (same tone as the check-in reminder)."""
    try:
        await send_email(to=inv["invitee_email"], subject=FOUNDATION_ARRIVAL_SUBJECT, case_id=report["id"], kind="foundation_arrival", to_role=f"Parent {inv['role'].upper()}",
                         html=FOUNDATION_ARRIVAL_HTML.format(name=escape(inv.get("invitee_name") or "there"), link=f"{app_url()}/joint/{report['id']}", from_name=escape(EMAIL_FROM_NAME)))
    except Exception:
        logger.warning("Foundation arrival email not sent for case %s", report["id"])


# ---------- External account linking (sacoparentsapp.online) ----------

class LinkIn(BaseModel):
    code: str
    report_id: str | None = None


@router.post("/external/link")
async def link_external_account(body: LinkIn, user=Depends(get_current_user)):
    code = body.code.strip().upper()
    professional_id, case_id = None, None
    if body.report_id:
        doc = await get_joint_report_doc(body.report_id, user)
        professional_id, case_id = case_context(doc)
    ext_email = await _verify_link_code(code, professional_id, case_id)
    await db.account_links.update_one(
        {"user_id": user["_id"]},
        {"$set": {"external_email": ext_email, "linked_at": datetime.now(timezone.utc).isoformat(), "case_id": case_id, "professional_id": professional_id}},
        upsert=True,
    )
    return {"ok": True, "external_email": ext_email}


@router.get("/external/link")
async def get_external_link(user=Depends(get_current_user)):
    link = await db.account_links.find_one({"user_id": user["_id"]}, {"_id": 0})
    if not link:
        return {"linked": False}
    return {"linked": True, "external_email": link["external_email"], "linked_at": link["linked_at"]}


@router.delete("/external/link")
async def unlink_external_account(user=Depends(get_current_user)):
    await db.account_links.delete_one({"user_id": user["_id"]})
    return {"ok": True}


async def fetch_external_export(email: str, ctx: dict | None = None):
    pid, cid = (ctx or {}).get("professional_id"), (ctx or {}).get("case_id")
    return await _export_assessments(email, pid, cid)


@router.get("/external/assessments")
async def get_external_assessments(user=Depends(get_current_user)):
    link = await db.account_links.find_one({"user_id": user["_id"]})
    if not link:
        raise HTTPException(status_code=400, detail="Link your sacoparentsapp.online account first")
    payload = await fetch_external_export(link["external_email"], {"professional_id": link.get("professional_id"), "case_id": link.get("case_id")})
    return {"assessments": payload.get("assessments", []), "statements": payload.get("statements", []), "access_scope": payload.get("access_scope")}


@router.post("/joint/reports/{rid}/import")
async def import_external_assessment(rid: str, user=Depends(get_current_user)):
    doc = await get_joint_report_doc(rid, user)
    role = report_role(doc, user["_id"])
    if role is None:
        raise HTTPException(status_code=403, detail="Only invited parents can import an assessment")
    link = await db.account_links.find_one({"user_id": user["_id"]})
    if not link:
        raise HTTPException(status_code=400, detail="Link your sacoparentsapp.online account first")
    payload = await fetch_external_export(link["external_email"], {"professional_id": case_context(doc)[0], "case_id": doc["id"]})
    from safety_import import extract_safety_screening
    screening = extract_safety_screening(payload) if payload.get("access_scope") == "case" else None
    updates = {
        f"responses.{role}": {
            "answers": {},
            "imported": True,
            "external": payload,
            "safety_route": bool(screening and ((screening.get("tier") or 0) >= 2 or screening.get("concern_count"))),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    if screening:
        updates[f"safety_screenings.{role}"] = screening
        updates[f"safety_flags.{role}"] = updates[f"responses.{role}"]["safety_route"]
    comm = payload.get("communication_readiness") if isinstance(payload, dict) else None
    if isinstance(comm, dict) and isinstance(comm.get("responses"), dict):
        from safety_import import _date
        from safety_screening import comm_record
        updates[f"communication_readiness.{role}"] = comm_record(comm["responses"], source="sacoparentsapp.online", completed_at=_date(comm.get("completed_at")) or None)
    other = "b" if role == "a" else "a"
    if doc.get("responses", {}).get(other):
        updates["status"] = "ready"
    await db.joint_reports.update_one({"id": rid}, {"$set": updates})
    doc = await get_joint_report_doc(rid, user)
    return joint_public(doc, user)


@router.get("/reports/complete")
async def complete_alignment_report(user=Depends(get_current_user)):
    uid = user["_id"]
    cases = await db.cases.find({"user_id": uid}, {"_id": 0}).to_list(200)
    joints = await db.joint_reports.find(
        {"$or": [
            {"created_by": uid},
            {"participants.a.user_id": uid},
            {"participants.b.user_id": uid},
            {"professional_id": uid},
            {"shared_with": uid},
        ]},
        {"_id": 0},
    ).to_list(200)
    return build_complete_report(cases, joints, user.get("name", ""))


@router.get("/reports/complete/pdf")
async def complete_alignment_report_pdf(user=Depends(get_current_user)):
    uid = user["_id"]
    cases = await db.cases.find({"user_id": uid}, {"_id": 0}).to_list(200)
    joints = await db.joint_reports.find(
        {"$or": [
            {"created_by": uid},
            {"participants.a.user_id": uid},
            {"participants.b.user_id": uid},
            {"professional_id": uid},
            {"shared_with": uid},
        ]},
        {"_id": 0},
    ).to_list(200)
    report = build_complete_report(cases, joints, user.get("name", ""))
    if report["is_empty"]:
        raise HTTPException(status_code=400, detail="The Complete Report PDF becomes available once at least one assessment or joint report is complete")
    return Response(
        content=build_complete_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="complete-alignment-report.pdf"'},
    )
