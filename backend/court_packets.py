"""Court Packets: professional cover letter + selected reports, delivered to a judge via one-time link + code."""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from joint_engine import generate_agreement, generate_joint_report
from pdf_report import build_agreement_pdf, build_closing_summary_pdf, build_court_cover_letter_pdf, build_joint_pdf, merge_pdfs

PACKET_DAYS = 30
SESSION_HOURS = 4
MAX_CODE_ATTEMPTS = 8
ATTESTATION = ("I attest that I am the facilitating professional for this matter and that I have the authority, "
               "by court order, appointment, or the parties' written authorization, to release these materials to the court.")


def _h(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _ready(doc: dict) -> bool:
    return bool(doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b"))


class PacketIn(BaseModel):
    judge_name: str
    judge_email: EmailStr
    court_name: str = ""
    cause_number: str = ""
    cover_letter: str
    report_ids: list[str] = []
    include_session_outcome: bool = True
    include_closing_summary: bool = True
    attest: bool = False


class UnlockIn(BaseModel):
    code: str


class RespondIn(BaseModel):
    kind: str
    message: str = ""


def build_router(db, get_current_user, app_url, send_email, email_from_name, logger) -> APIRouter:
    r = APIRouter()

    def public(p: dict) -> dict:
        return {k: p.get(k) for k in (
            "id", "report_id", "judge_name", "judge_email", "court_name", "cause_number", "cover_letter", "report_ids",
            "include_session_outcome", "include_closing_summary", "status", "created_at", "expires_at", "revoked_at",
            "responses", "opened_count", "download_count", "last_opened_at")}

    async def log(report_id: str, action: str, by: str, by_name: str, by_role: str, kind: str = "court") -> None:
        await db.access_events.insert_one({"report_id": report_id, "kind": kind, "action": action, "at": _iso(_now()),
                                           "by": by, "by_name": by_name, "by_role": by_role})

    async def pro_profile(pid: str) -> dict:
        u = await db.users.find_one({"_id": pid}, {"name": 1, "email": 1, "profile": 1, "verification_level": 1}) or {}
        prof = u.get("profile") or {}
        return {"name": u.get("name", ""), "email": u.get("email", ""), "credentials_verified": u.get("verification_level") == "credentials_verified",
                **{k: prof.get(k, "") for k in ("pro_role", "organization", "license_number", "phone", "city", "state")}}

    async def packet_reports(p: dict) -> list[dict]:
        docs = await db.joint_reports.find({"id": {"$in": p["report_ids"]}, "professional_id": p["professional_id"]}, {"_id": 0}).to_list(50)
        order = {rid: i for i, rid in enumerate(p["report_ids"])}
        return sorted([d for d in docs if _ready(d)], key=lambda d: order.get(d["id"], 99))

    def report_json(doc: dict) -> dict:
        rep = generate_agreement(doc) if doc.get("kind") == "agreement" else generate_joint_report(doc)
        return {"id": doc["id"], "case_code": doc.get("case_code"), "kind": doc.get("kind", "joint_report"),
                "subject_label": doc.get("subject_label"), "is_safety": bool(doc.get("is_safety")), "report": rep}

    async def combined_pdf(p: dict) -> bytes:
        docs = await packet_reports(p)
        pro = await pro_profile(p["professional_id"])
        primary = next((d for d in docs if d["id"] == p["report_id"]), docs[0] if docs else {})
        index = [f"{'Co-Parenting Agreement' if d.get('kind') == 'agreement' else 'Joint Alignment Report'} - {d.get('subject_label')} ({d.get('case_code')})" for d in docs]
        closing_docs = [d for d in docs if p.get("include_closing_summary") and d.get("closed_at")]
        index += [f"Case Closing Summary ({d.get('case_code')})" for d in closing_docs]
        cover = build_court_cover_letter_pdf({**p, "professional": pro, "index": index,
                                              "session_outcome": primary.get("session_outcome") if p.get("include_session_outcome") else None})
        parts = [cover]
        for d in docs:
            if d.get("kind") == "agreement":
                parts.append(build_agreement_pdf(generate_agreement(d)))
            else:
                parts.append(build_joint_pdf({**generate_joint_report(d), "professional": {"name": pro["name"], "credentials_verified": pro["credentials_verified"]},
                                              "verify": {"case_code": d.get("case_code"), "url": f"{app_url()}/verify?code={d.get('case_code')}"}}))
        for d in closing_docs:
            events = await db.access_events.find({"report_id": d["id"]}, {"_id": 0}).sort("at", 1).to_list(500)
            parts.append(build_closing_summary_pdf({**d, "professional_name": pro["name"],
                                                    "view_count": sum(1 for e in events if e.get("kind") == "view"),
                                                    "download_count": sum(1 for e in events if e.get("kind") == "download"),
                                                    "lifecycle": [e for e in events if e.get("kind") == "lifecycle"]}))
        return merge_pdfs(parts)

    async def send_judge_emails(p: dict, token: str, code: str, pro_name: str) -> None:
        link = f"{app_url()}/court/{token}"
        await send_email(
            to=p["judge_email"],
            subject=f"Court Packet from {pro_name} - {p.get('cause_number') or p.get('court_name') or 'SA CoParents Align'}",
            html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                  f"<p>Your Honor,</p><p>{escape(pro_name)} has prepared a Court Packet for your review through SA CoParents Align"
                  f"{' regarding Cause No. ' + escape(p['cause_number']) if p.get('cause_number') else ''}. It contains the professional's cover letter and the co-parenting alignment "
                  "report(s) for the matter. Access is read-only, logged, and expires in 30 days.</p>"
                  f'<p><a href="{link}" style="color:#5B2A86">Open the Court Packet</a></p>'
                  "<p>A separate email contains your 6-digit access code.</p>"
                  f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)} on behalf of {escape(pro_name)}.</p></td></tr></table>'))
        await send_email(
            to=p["judge_email"],
            subject="Your Court Packet access code",
            html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                  f"<p>Your access code for the Court Packet from {escape(pro_name)}:</p>"
                  f'<p style="font-size:28px;letter-spacing:6px;font-weight:bold">{code}</p>'
                  "<p>Enter it on the packet page that was sent to you in a separate email. The code stays valid until the packet expires.</p>"
                  f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>'))

    # ---------- professional side ----------

    @r.get("/joint/reports/{rid}/court-packets/options")
    async def packet_options(rid: str, user=Depends(get_current_user)):
        doc = await db.joint_reports.find_one({"id": rid, "professional_id": user["_id"]}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Report not found")
        docs = await db.joint_reports.find({"professional_id": user["_id"]}, {"_id": 0, "responses": 0}).sort("created_at", -1).to_list(200)
        opts = [{"id": d["id"], "case_code": d.get("case_code"), "subject_label": d.get("subject_label"), "child_name": d.get("child_name"),
                 "kind": d.get("kind", "joint_report"), "is_safety": bool(d.get("is_safety")), "closed": bool(d.get("closed_at")), "primary": d["id"] == rid}
                for d in docs if d.get("status") == "ready" or d["id"] == rid]
        return {"reports": opts, "attestation_text": ATTESTATION, "primary_ready": _ready(doc)}

    @r.post("/joint/reports/{rid}/court-packets")
    async def create_packet(rid: str, body: PacketIn, user=Depends(get_current_user)):
        doc = await db.joint_reports.find_one({"id": rid, "professional_id": user["_id"]}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Report not found")
        if not user.get("approved", True):
            raise HTTPException(status_code=403, detail="Only approved professionals can send Court Packets")
        if not _ready(doc):
            raise HTTPException(status_code=400, detail="The Joint Report must be complete before it can be sent to a court")
        if not body.attest:
            raise HTTPException(status_code=400, detail="You must attest to your authority to release these materials")
        if len(body.cover_letter.strip()) < 40:
            raise HTTPException(status_code=400, detail="Please write a cover letter of at least a few sentences")
        ids = list(dict.fromkeys([rid] + [i for i in body.report_ids if i]))
        owned = await db.joint_reports.count_documents({"id": {"$in": ids}, "professional_id": user["_id"]})
        if owned != len(ids):
            raise HTTPException(status_code=403, detail="You can only include reports from your own cases")
        token, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1_000_000):06d}"
        now = _now()
        p = {
            "id": str(uuid.uuid4()), "report_id": rid, "professional_id": user["_id"], "professional_name": user.get("name", ""),
            "judge_name": body.judge_name.strip()[:120], "judge_email": body.judge_email.lower(), "court_name": body.court_name.strip()[:160],
            "cause_number": body.cause_number.strip()[:80], "cover_letter": body.cover_letter.strip()[:6000], "report_ids": ids,
            "include_session_outcome": body.include_session_outcome, "include_closing_summary": body.include_closing_summary,
            "attestation_text": ATTESTATION, "attested_at": _iso(now), "token_hash": _h(token), "code_hash": _h(code), "code_attempts": 0,
            "sessions": [], "status": "sent", "responses": [], "opened_count": 0, "download_count": 0,
            "created_at": _iso(now), "expires_at": _iso(now + timedelta(days=PACKET_DAYS)),
        }
        await db.court_packets.insert_one(p)
        await log(rid, f"Court Packet sent to {p['judge_name']} ({p['court_name'] or 'court'})", user["_id"], user.get("name", ""), "Assigned professional")
        try:
            await send_judge_emails(p, token, code, user.get("name", "the professional"))
        except Exception as exc:
            logger.warning("court packet email failed: %s", exc)
        return {**public(p), "link": f"{app_url()}/court/{token}"}

    @r.get("/joint/reports/{rid}/court-packets")
    async def list_packets(rid: str, user=Depends(get_current_user)):
        if not await db.joint_reports.find_one({"id": rid, "professional_id": user["_id"]}, {"_id": 1}):
            raise HTTPException(status_code=404, detail="Report not found")
        docs = await db.court_packets.find({"report_id": rid}, {"_id": 0}).sort("created_at", -1).to_list(50)
        return [public(p) for p in docs]

    async def own_packet(pid: str, user: dict) -> dict:
        p = await db.court_packets.find_one({"id": pid, "professional_id": user["_id"]}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="Court Packet not found")
        return p

    @r.post("/court-packets/{pid}/revoke")
    async def revoke_packet(pid: str, user=Depends(get_current_user)):
        p = await own_packet(pid, user)
        now = _iso(_now())
        await db.court_packets.update_one({"id": pid}, {"$set": {"status": "revoked", "revoked_at": now, "sessions": []}})
        await log(p["report_id"], f"Court Packet access revoked ({p['judge_name']})", user["_id"], user.get("name", ""), "Assigned professional")
        return {"ok": True, "status": "revoked"}

    @r.post("/court-packets/{pid}/resend")
    async def resend_packet(pid: str, user=Depends(get_current_user)):
        p = await own_packet(pid, user)
        if p.get("status") == "revoked":
            raise HTTPException(status_code=400, detail="This packet was revoked; create a new one instead")
        token, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1_000_000):06d}"
        now = _now()
        await db.court_packets.update_one({"id": pid}, {"$set": {"token_hash": _h(token), "code_hash": _h(code), "code_attempts": 0, "sessions": [],
                                                              "expires_at": _iso(now + timedelta(days=PACKET_DAYS))}})
        await log(p["report_id"], f"Court Packet re-sent to {p['judge_name']}", user["_id"], user.get("name", ""), "Assigned professional")
        try:
            await send_judge_emails(p, token, code, user.get("name", "the professional"))
        except Exception as exc:
            logger.warning("court packet resend failed: %s", exc)
        return {"ok": True, "link": f"{app_url()}/court/{token}"}

    @r.get("/court-packets/{pid}/pdf")
    async def pro_packet_pdf(pid: str, user=Depends(get_current_user)):
        p = await own_packet(pid, user)
        return Response(content=await combined_pdf(p), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="court-packet-{re.sub(r"[^A-Za-z0-9-]", "", p.get("cause_number") or p["id"][:8])}.pdf"'})

    # ---------- judge side ----------

    async def packet_by_token(token: str) -> dict:
        p = await db.court_packets.find_one({"token_hash": _h(token)}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="This Court Packet link is not valid")
        return p

    def state(p: dict) -> str:
        if p.get("status") == "revoked":
            return "revoked"
        if _iso(_now()) > p["expires_at"]:
            return "expired"
        return "active"

    async def require_session(token: str, access: str) -> dict:
        p = await packet_by_token(token)
        if state(p) != "active":
            raise HTTPException(status_code=410, detail=f"This Court Packet is {state(p)}")
        ah, now = _h(access or ""), _iso(_now())
        if not any(s["hash"] == ah and s["expires_at"] > now for s in p.get("sessions", [])):
            raise HTTPException(status_code=401, detail="Enter your access code to open this packet")
        return p

    @r.get("/court/{token}/preview")
    async def court_preview(token: str):
        p = await packet_by_token(token)
        return {"state": state(p), "professional_name": p.get("professional_name"), "court_name": p.get("court_name"),
                "cause_number": p.get("cause_number"), "judge_name": p.get("judge_name"), "expires_at": p["expires_at"]}

    @r.post("/court/{token}/unlock")
    async def court_unlock(token: str, body: UnlockIn, request: Request):
        p = await packet_by_token(token)
        if state(p) != "active":
            raise HTTPException(status_code=410, detail=f"This Court Packet is {state(p)}")
        if p.get("code_attempts", 0) >= MAX_CODE_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many attempts. Ask the professional to re-send the packet.")
        if not secrets.compare_digest(_h(body.code.strip()), p["code_hash"]):
            await db.court_packets.update_one({"id": p["id"]}, {"$inc": {"code_attempts": 1}})
            raise HTTPException(status_code=400, detail="Incorrect access code")
        access = secrets.token_urlsafe(32)
        now = _now()
        sess = {"hash": _h(access), "created_at": _iso(now), "expires_at": _iso(now + timedelta(hours=SESSION_HOURS))}
        await db.court_packets.update_one({"id": p["id"]}, {"$push": {"sessions": sess}, "$set": {"code_attempts": 0, "status": p["status"] if p["status"] != "sent" else "opened",
                                                                                                 "last_opened_at": _iso(now)}, "$inc": {"opened_count": 1}})
        await log(p["report_id"], f"Court Packet opened by {p['judge_name']}", f"court:{p['id']}", p["judge_name"], "Court")
        return {"access": access, "expires_in_hours": SESSION_HOURS}

    @r.get("/court/{token}")
    async def court_packet(token: str, request: Request):
        p = await require_session(token, request.headers.get("x-court-access", ""))
        docs = await packet_reports(p)
        primary = next((d for d in docs if d["id"] == p["report_id"]), {})
        return {**{k: p.get(k) for k in ("id", "judge_name", "court_name", "cause_number", "cover_letter", "attestation_text", "attested_at", "created_at", "expires_at", "responses", "status")},
                "professional": await pro_profile(p["professional_id"]),
                "reports": [report_json(d) for d in docs],
                "session_outcome": primary.get("session_outcome") if p.get("include_session_outcome") else None}

    @r.get("/court/{token}/pdf")
    async def court_pdf(token: str, access: str = ""):
        p = await require_session(token, access)
        await db.court_packets.update_one({"id": p["id"]}, {"$inc": {"download_count": 1}})
        await log(p["report_id"], f"Court Packet PDF downloaded by {p['judge_name']}", f"court:{p['id']}", p["judge_name"], "Court")
        return Response(content=await combined_pdf(p), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="court-packet-{re.sub(r"[^A-Za-z0-9-]", "", p.get("cause_number") or p["id"][:8])}.pdf"'})

    @r.post("/court/{token}/respond")
    async def court_respond(token: str, body: RespondIn, request: Request):
        p = await require_session(token, request.headers.get("x-court-access", ""))
        if body.kind not in ("acknowledged", "clarification"):
            raise HTTPException(status_code=400, detail="Unknown response type")
        msg = body.message.strip()[:2000]
        if body.kind == "clarification" and not msg:
            raise HTTPException(status_code=400, detail="Please describe what needs clarification")
        now = _iso(_now())
        resp = {"id": str(uuid.uuid4()), "kind": body.kind, "message": msg, "at": now, "by": p["judge_name"]}
        await db.court_packets.update_one({"id": p["id"]}, {"$push": {"responses": resp}, "$set": {"status": "acknowledged" if body.kind == "acknowledged" else "clarification_requested"}})
        label = "acknowledged receipt of" if body.kind == "acknowledged" else "requested clarification on"
        await log(p["report_id"], f"{p['judge_name']} {label} the Court Packet", f"court:{p['id']}", p["judge_name"], "Court")
        pro = await db.users.find_one({"_id": p["professional_id"]}, {"email": 1, "name": 1})
        quote = f'<blockquote style="border-left:3px solid #5B2A86;padding-left:12px;color:#444">{escape(msg)}</blockquote>' if msg else ""
        cause = f" for Cause No. {escape(p['cause_number'])}" if p.get("cause_number") else ""
        if pro and pro.get("email"):
            try:
                await send_email(
                    to=pro["email"], subject=f"Court response: {p['judge_name']} {label} your packet",
                    html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                          f"<p>Hi {escape(pro.get('name', ''))},</p><p><strong>{escape(p['judge_name'])}</strong> ({escape(p.get('court_name') or 'court')}) {label} the Court Packet{cause}.</p>"
                          f"{quote}"
                          f'<p><a href="{app_url()}/joint/{p["report_id"]}" style="color:#5B2A86">Open the case</a></p>'
                          f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>'))
            except Exception as exc:
                logger.warning("court response email failed: %s", exc)
        return {"ok": True, "response": resp}

    return r
