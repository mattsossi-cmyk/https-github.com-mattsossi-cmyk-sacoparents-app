"""Court Packets: professional cover letter + selected reports, delivered to a judge via one-time link + code or a court account."""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from joint_engine import generate_agreement, generate_joint_report
from pdf_report import build_agreement_pdf, build_closing_summary_pdf, build_court_cover_letter_pdf, build_joint_pdf, build_transmittal_pdf, merge_pdfs

PACKET_DAYS = 30
SESSION_HOURS = 4
MAX_CODE_ATTEMPTS = 8
ATTESTATION = ("I attest that I am the facilitating professional for this matter and that I have the authority, "
               "by court order, appointment, or the parties' written authorization, to release these materials to the court.")
PUBLIC_KEYS = ("id", "report_id", "judge_name", "judge_email", "court_name", "cause_number", "cover_letter", "report_ids",
               "include_session_outcome", "include_closing_summary", "status", "created_at", "expires_at", "revoked_at",
               "responses", "opened_count", "download_count", "last_opened_at", "submission_version", "frozen", "superseded", "sha256")
VIEW_KEYS = ("id", "judge_name", "court_name", "cause_number", "cover_letter", "attestation_text", "attested_at", "created_at", "expires_at", "responses", "status",
             "statement", "submission_version", "frozen", "sha256", "superseded")
EMAIL_WRAP = '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">{}</td></tr></table>'


def _h(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ready(doc: dict) -> bool:
    return bool(doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b"))


def _safe_name(p: dict) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "", p.get("cause_number") or p["id"][:8])


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def public(p: dict) -> dict:
    return {k: p.get(k) for k in PUBLIC_KEYS}


def state(p: dict) -> str:
    if p.get("status") == "revoked":
        return "revoked"
    return "expired" if _now_iso() > p["expires_at"] else "active"


def report_json(doc: dict) -> dict:
    rep = generate_agreement(doc) if doc.get("kind") == "agreement" else generate_joint_report(doc)
    return {"id": doc["id"], "case_code": doc.get("case_code"), "kind": doc.get("kind", "joint_report"),
            "subject_label": doc.get("subject_label"), "is_safety": bool(doc.get("is_safety")), "report": rep}


def _enclosure_title(d: dict) -> str:
    kind = "Co-Parenting Agreement" if d.get("kind") == "agreement" else "Joint Alignment Report"
    return f"{kind} - {d.get('subject_label')} ({d.get('case_code')})"


def _new_packet(rid: str, user: dict, body, ids: list[str], token: str, code: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": str(uuid.uuid4()), "report_id": rid, "professional_id": user["_id"], "professional_name": user.get("name", ""),
        "judge_name": body.judge_name.strip()[:120], "judge_email": body.judge_email.lower(), "court_name": body.court_name.strip()[:160],
        "cause_number": body.cause_number.strip()[:80], "cover_letter": body.cover_letter.strip()[:6000], "report_ids": ids,
        "include_session_outcome": body.include_session_outcome, "include_closing_summary": body.include_closing_summary,
        "attestation_text": ATTESTATION, "attested_at": now.isoformat(), "token_hash": _h(token), "code_hash": _h(code), "code_attempts": 0,
        "sessions": [], "status": "sent", "responses": [], "opened_count": 0, "download_count": 0,
        "created_at": now.isoformat(), "expires_at": (now + timedelta(days=PACKET_DAYS)).isoformat(),
    }


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


class PacketService:
    """Data access, PDF assembly, and notifications shared by the professional, link, and court-account routes."""

    def __init__(self, db, app_url, send_email, email_from_name, logger):
        self.db, self.app_url, self.send_email, self.from_name, self.logger = db, app_url, send_email, email_from_name, logger

    async def log(self, report_id: str, action: str, by: str, by_name: str, by_role: str, kind: str = "court") -> None:
        await self.db.access_events.insert_one({"report_id": report_id, "kind": kind, "action": action, "at": _now_iso(), "by": by, "by_name": by_name, "by_role": by_role})

    async def log_pro(self, p: dict, action: str, user: dict) -> None:
        await self.log(p["report_id"], action, user["_id"], user.get("name", ""), "Assigned professional")

    async def log_court(self, p: dict, action: str, by: str | None = None, by_name: str | None = None) -> None:
        await self.log(p["report_id"], action, by or f"court:{p['id']}", by_name or p["judge_name"], "Court")

    async def pro_profile(self, pid: str) -> dict:
        u = await self.db.users.find_one({"_id": pid}, {"name": 1, "email": 1, "profile": 1, "verification_level": 1}) or {}
        prof = u.get("profile") or {}
        return {"name": u.get("name", ""), "email": u.get("email", ""), "credentials_verified": u.get("verification_level") == "credentials_verified",
                "signature_path": ((prof.get("images") or {}).get("signature") or {}).get("path"),
                **{k: prof.get(k, "") for k in ("pro_role", "organization", "license_number", "phone", "city", "state")}}

    async def packet_reports(self, p: dict) -> list[dict]:
        docs = await self.db.joint_reports.find({"id": {"$in": p["report_ids"]}, "professional_id": p["professional_id"]}, {"_id": 0}).to_list(50)
        order = {rid: i for i, rid in enumerate(p["report_ids"])}
        return sorted([d for d in docs if _ready(d)], key=lambda d: order.get(d["id"], 99))

    async def by_token(self, token: str) -> dict:
        p = await self.db.court_packets.find_one({"token_hash": _h(token)}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="This Court Packet link is not valid")
        return p

    async def own(self, pid: str, user: dict) -> dict:
        p = await self.db.court_packets.find_one({"id": pid, "professional_id": user["_id"]}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="Court Packet not found")
        return p

    async def for_judge(self, pid: str, user: dict) -> dict:
        if user.get("role") != "judge":
            raise HTTPException(status_code=403, detail="Court accounts only")
        if not user.get("approved"):
            raise HTTPException(status_code=403, detail="Your court account is awaiting SA CoParents approval")
        p = await self.db.court_packets.find_one({"id": pid, "judge_email": user["email"].lower()}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="Court Packet not found")
        self.require_active(p)
        return p

    @staticmethod
    def require_active(p: dict) -> None:
        if state(p) != "active":
            raise HTTPException(status_code=410, detail=f"This Court Packet is {state(p)}")

    async def require_session(self, token: str, access: str) -> dict:
        p = await self.by_token(token)
        self.require_active(p)
        ah, now = _h(access or ""), _now_iso()
        if not any(s["hash"] == ah and s["expires_at"] > now for s in p.get("sessions", [])):
            raise HTTPException(status_code=401, detail="Enter your access code to open this packet")
        return p

    # ---- PDF assembly ----

    async def _closing_pdf(self, d: dict, pro_name: str) -> bytes:
        events = await self.db.access_events.find({"report_id": d["id"]}, {"_id": 0}).sort("at", 1).to_list(500)
        return build_closing_summary_pdf({**d, "professional_name": pro_name,
                                          "view_count": sum(1 for e in events if e.get("kind") == "view"),
                                          "download_count": sum(1 for e in events if e.get("kind") == "download"),
                                          "lifecycle": [e for e in events if e.get("kind") == "lifecycle"]})

    def _report_pdf(self, d: dict, pro: dict) -> bytes:
        if d.get("kind") == "agreement":
            return build_agreement_pdf(generate_agreement(d), doc=d)
        return build_joint_pdf({**generate_joint_report(d), "professional": {"name": pro["name"], "credentials_verified": pro["credentials_verified"]},
                                "verify": {"case_code": d.get("case_code"), "url": f"{self.app_url()}/verify?code={d.get('case_code')}"}})

    async def _frozen_pdf(self, p: dict) -> bytes | None:
        if not p.get("frozen"):
            return None
        frozen = await self.db.court_frozen_pdfs.find_one({"packet_id": p["id"]}, {"pdf": 1})
        return bytes(frozen["pdf"]) if frozen else None

    async def combined_pdf(self, p: dict) -> bytes:
        frozen = await self._frozen_pdf(p)
        if frozen:
            return frozen
        docs = await self.packet_reports(p)
        pro = await self.pro_profile(p["professional_id"])
        primary = next((d for d in docs if d["id"] == p["report_id"]), docs[0] if docs else {})
        closing_docs = [d for d in docs if p.get("include_closing_summary") and d.get("closed_at")]
        cover = build_court_cover_letter_pdf({**p, "professional": pro, "index": [_enclosure_title(d) for d in docs] + [f"Case Closing Summary ({d.get('case_code')})" for d in closing_docs],
                                              "session_outcome": primary.get("session_outcome") if p.get("include_session_outcome") else None})
        return merge_pdfs([cover] + [self._report_pdf(d, pro) for d in docs] + [await self._closing_pdf(d, pro["name"]) for d in closing_docs])

    async def view(self, p: dict) -> dict:
        docs = await self.packet_reports(p)
        primary = next((d for d in docs if d["id"] == p["report_id"]), {})
        return {**{k: p.get(k) for k in VIEW_KEYS}, "professional": await self.pro_profile(p["professional_id"]), "reports": [report_json(d) for d in docs],
                "session_outcome": primary.get("session_outcome") if p.get("include_session_outcome") else None}

    async def mark_opened(self, p: dict, extra: dict | None = None) -> None:
        now = _now_iso()
        status = p["status"] if p["status"] != "sent" else "opened"
        await self.db.court_packets.update_one({"id": p["id"]}, {"$set": {"status": status, "last_opened_at": now, **(extra or {})}, "$inc": {"opened_count": 1}})

    # ---- notifications ----

    async def _mail(self, to: str, subject: str, body_html: str, case_id: str = "", kind: str = "court_packet", to_role: str = "Court") -> None:
        try:
            await self.send_email(to=to, subject=subject, html=EMAIL_WRAP.format(body_html + f'<p style="font-size:12px;color:#888">Sent by {escape(self.from_name)}.</p>'),
                                  case_id=case_id or None, kind=kind, to_role=to_role)
        except Exception as exc:
            self.logger.warning("court packet email failed: %s", exc)

    async def send_judge_emails(self, p: dict, token: str, code: str, pro_name: str) -> None:
        link = f"{self.app_url()}/court/{token}"
        cause = f" regarding Cause No. {escape(p['cause_number'])}" if p.get("cause_number") else ""
        await self._mail(p["judge_email"], f"Court Packet from {pro_name} - {p.get('cause_number') or p.get('court_name') or 'SA CoParents Align'}",
                         f"<p>Your Honor,</p><p>{escape(pro_name)} has prepared a Court Packet for your review through SA CoParents Align{cause}. It contains the professional's cover letter "
                         "and the co-parenting alignment report(s) for the matter. Access is read-only, logged, and expires in 30 days.</p>"
                         f'<p><a href="{link}" style="color:#5B2A86">Open the Court Packet</a></p><p>A separate email contains your 6-digit access code.</p>', case_id=p["report_id"])
        await self._mail(p["judge_email"], "Your Court Packet access code",
                         f"<p>Your access code for the Court Packet from {escape(pro_name)}:</p><p style=\"font-size:28px;letter-spacing:6px;font-weight:bold\">{code}</p>"
                         "<p>Enter it on the packet page that was sent to you in a separate email. The code stays valid until the packet expires.</p>", case_id=p["report_id"], kind="court_packet_code")

    @staticmethod
    def _validated_response(body: RespondIn) -> tuple[str, str, str]:
        """Returns (message, new packet status, action label)."""
        if body.kind not in ("acknowledged", "clarification"):
            raise HTTPException(status_code=400, detail="Unknown response type")
        msg = body.message.strip()[:2000]
        if body.kind == "clarification" and not msg:
            raise HTTPException(status_code=400, detail="Please describe what needs clarification")
        ack = body.kind == "acknowledged"
        return msg, "acknowledged" if ack else "clarification_requested", "acknowledged receipt of" if ack else "requested clarification on"

    async def _notify_pro_of_response(self, p: dict, label: str, msg: str) -> None:
        pro = await self.db.users.find_one({"_id": p["professional_id"]}, {"email": 1, "name": 1})
        if not pro or not pro.get("email"):
            return
        quote = f'<blockquote style="border-left:3px solid #5B2A86;padding-left:12px;color:#444">{escape(msg)}</blockquote>' if msg else ""
        cause = f" for Cause No. {escape(p['cause_number'])}" if p.get("cause_number") else ""
        await self._mail(pro["email"], f"Court response: {p['judge_name']} {label} your packet",
                         f"<p>Hi {escape(pro.get('name', ''))},</p><p><strong>{escape(p['judge_name'])}</strong> ({escape(p.get('court_name') or 'court')}) {label} the Court Packet{cause}.</p>{quote}"
                         f'<p><a href="{self.app_url()}/joint/{p["report_id"]}" style="color:#5B2A86">Open the case</a></p>', case_id=p["report_id"], kind="court_response", to_role="Professional")

    async def record_response(self, p: dict, body: RespondIn, by: str | None = None, by_name: str | None = None) -> dict:
        msg, status, label = self._validated_response(body)
        resp = {"id": str(uuid.uuid4()), "kind": body.kind, "message": msg, "at": _now_iso(), "by": p["judge_name"]}
        await self.db.court_packets.update_one({"id": p["id"]}, {"$push": {"responses": resp}, "$set": {"status": status}})
        await self.log_court(p, f"{p['judge_name']} {label} the Court Packet", by, by_name)
        await self._notify_pro_of_response(p, label, msg)
        return resp

    async def transmittal(self, p: dict, user: dict) -> bytes:
        docs = await self.packet_reports(p)
        events = await self.db.access_events.find({"report_id": p["report_id"], "kind": "court", "action": {"$regex": "Court Packet"}}, {"_id": 0}).sort("at", 1).to_list(200)
        await self.log(p["report_id"], "Transmittal certificate downloaded", user["_id"], user.get("name", ""), "Assigned professional", kind="download")
        return build_transmittal_pdf({**p, "professional": await self.pro_profile(p["professional_id"]), "enclosures": [_enclosure_title(d) for d in docs],
                                      "events": [e for e in events if p["judge_name"] in e["action"] or "sent" in e["action"] or "re-sent" in e["action"]]})


async def _own_report(db, rid: str, user: dict) -> dict:
    doc = await db.joint_reports.find_one({"id": rid, "professional_id": user["_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    return doc


def _assert_packet_allowed(doc: dict, body: PacketIn, user: dict) -> None:
    if not user.get("approved", True):
        raise HTTPException(status_code=403, detail="Only approved professionals can send Court Packets")
    if not _ready(doc):
        raise HTTPException(status_code=400, detail="The Joint Report must be complete before it can be sent to a court")
    if not body.attest:
        raise HTTPException(status_code=400, detail="You must attest to your authority to release these materials")
    if len(body.cover_letter.strip()) < 40:
        raise HTTPException(status_code=400, detail="Please write a cover letter of at least a few sentences")


def _pro_routes(svc: PacketService, get_current_user) -> APIRouter:
    r = APIRouter()
    r.include_router(_pro_case_packet_routes(svc, get_current_user))
    r.include_router(_pro_packet_admin_routes(svc, get_current_user))
    return r


def _pro_case_packet_routes(svc: PacketService, get_current_user) -> APIRouter:
    """Per-case: packet options, create, list."""
    r = APIRouter()
    db = svc.db

    async def own_report(rid: str, user: dict) -> dict:
        return await _own_report(db, rid, user)

    @r.get("/joint/reports/{rid}/court-packets/options")
    async def packet_options(rid: str, user=Depends(get_current_user)):
        doc = await own_report(rid, user)
        docs = await db.joint_reports.find({"professional_id": user["_id"]}, {"_id": 0, "responses": 0}).sort("created_at", -1).to_list(200)
        opts = [{"id": d["id"], "case_code": d.get("case_code"), "subject_label": d.get("subject_label"), "child_name": d.get("child_name"),
                 "kind": d.get("kind", "joint_report"), "is_safety": bool(d.get("is_safety")), "closed": bool(d.get("closed_at")), "primary": d["id"] == rid}
                for d in docs if d.get("status") == "ready" or d["id"] == rid]
        return {"reports": opts, "attestation_text": ATTESTATION, "primary_ready": _ready(doc)}

    @r.post("/joint/reports/{rid}/court-packets")
    async def create_packet(rid: str, body: PacketIn, user=Depends(get_current_user)):
        doc = await own_report(rid, user)
        _assert_packet_allowed(doc, body, user)
        ids = list(dict.fromkeys([rid] + [i for i in body.report_ids if i]))
        if await db.joint_reports.count_documents({"id": {"$in": ids}, "professional_id": user["_id"]}) != len(ids):
            raise HTTPException(status_code=403, detail="You can only include reports from your own cases")
        token, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1_000_000):06d}"
        p = _new_packet(rid, user, body, ids, token, code)
        await db.court_packets.insert_one(p)
        await svc.log_pro(p, f"Court Packet sent to {p['judge_name']} ({p['court_name'] or 'court'})", user)
        await svc.send_judge_emails(p, token, code, user.get("name", "the professional"))
        return {**public(p), "link": f"{svc.app_url()}/court/{token}"}

    @r.get("/joint/reports/{rid}/court-packets")
    async def list_packets(rid: str, user=Depends(get_current_user)):
        await own_report(rid, user)
        return [public(p) for p in await db.court_packets.find({"report_id": rid}, {"_id": 0}).sort("created_at", -1).to_list(50)]

    return r


def _pro_packet_admin_routes(svc: PacketService, get_current_user) -> APIRouter:
    """Per-packet: revoke, resend, PDFs."""
    r = APIRouter()
    db = svc.db

    @r.post("/court-packets/{pid}/revoke")
    async def revoke_packet(pid: str, user=Depends(get_current_user)):
        p = await svc.own(pid, user)
        await db.court_packets.update_one({"id": pid}, {"$set": {"status": "revoked", "revoked_at": _now_iso(), "sessions": []}})
        await svc.log_pro(p, f"Court Packet access revoked ({p['judge_name']})", user)
        return {"ok": True, "status": "revoked"}

    @r.post("/court-packets/{pid}/resend")
    async def resend_packet(pid: str, user=Depends(get_current_user)):
        p = await svc.own(pid, user)
        if p.get("status") == "revoked":
            raise HTTPException(status_code=400, detail="This packet was revoked; create a new one instead")
        token, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1_000_000):06d}"
        expires = (datetime.now(timezone.utc) + timedelta(days=PACKET_DAYS)).isoformat()
        await db.court_packets.update_one({"id": pid}, {"$set": {"token_hash": _h(token), "code_hash": _h(code), "code_attempts": 0, "sessions": [], "expires_at": expires}})
        await svc.log_pro(p, f"Court Packet re-sent to {p['judge_name']}", user)
        await svc.send_judge_emails(p, token, code, user.get("name", "the professional"))
        return {"ok": True, "link": f"{svc.app_url()}/court/{token}"}

    @r.get("/court-packets/{pid}/pdf")
    async def pro_packet_pdf(pid: str, user=Depends(get_current_user)):
        p = await svc.own(pid, user)
        return _pdf_response(await svc.combined_pdf(p), f"court-packet-{_safe_name(p)}.pdf")

    @r.get("/court-packets/{pid}/transmittal.pdf")
    async def transmittal_pdf(pid: str, user=Depends(get_current_user)):
        p = await svc.own(pid, user)
        return _pdf_response(await svc.transmittal(p, user), f"transmittal-{_safe_name(p)}.pdf")

    return r


def _link_routes(svc: PacketService) -> APIRouter:
    """Judge access via one-time link + 6-digit code (no account)."""
    r = APIRouter()
    db = svc.db

    @r.get("/court/{token}/preview")
    async def court_preview(token: str):
        p = await svc.by_token(token)
        return {"state": state(p), **{k: p.get(k) for k in ("professional_name", "court_name", "cause_number", "judge_name", "expires_at")}}

    @r.post("/court/{token}/unlock")
    async def court_unlock(token: str, body: UnlockIn):
        p = await svc.by_token(token)
        svc.require_active(p)
        if p.get("code_attempts", 0) >= MAX_CODE_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many attempts. Ask the professional to re-send the packet.")
        if not secrets.compare_digest(_h(body.code.strip()), p["code_hash"]):
            await db.court_packets.update_one({"id": p["id"]}, {"$inc": {"code_attempts": 1}})
            raise HTTPException(status_code=400, detail="Incorrect access code")
        access = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        sess = {"hash": _h(access), "created_at": now.isoformat(), "expires_at": (now + timedelta(hours=SESSION_HOURS)).isoformat()}
        await db.court_packets.update_one({"id": p["id"]}, {"$push": {"sessions": sess}})
        await svc.mark_opened(p, {"code_attempts": 0})
        await svc.log_court(p, f"Court Packet opened by {p['judge_name']}")
        return {"access": access, "expires_in_hours": SESSION_HOURS}

    @r.get("/court/{token}")
    async def court_packet(token: str, request: Request):
        return await svc.view(await svc.require_session(token, request.headers.get("x-court-access", "")))

    @r.get("/court/{token}/pdf")
    async def court_pdf(token: str, access: str = ""):
        p = await svc.require_session(token, access)
        await db.court_packets.update_one({"id": p["id"]}, {"$inc": {"download_count": 1}})
        await svc.log_court(p, f"Court Packet PDF downloaded by {p['judge_name']}")
        return _pdf_response(await svc.combined_pdf(p), f"court-packet-{_safe_name(p)}.pdf")

    @r.post("/court/{token}/respond")
    async def court_respond(token: str, body: RespondIn, request: Request):
        p = await svc.require_session(token, request.headers.get("x-court-access", ""))
        return {"ok": True, "response": await svc.record_response(p, body)}

    return r


def _judge_routes(svc: PacketService, get_current_user) -> APIRouter:
    """Judge access via an approved court account."""
    r = APIRouter()
    db = svc.db

    @r.get("/court-dashboard/packets")
    async def judge_dashboard(user=Depends(get_current_user)):
        if user.get("role") != "judge":
            raise HTTPException(status_code=403, detail="Court accounts only")
        if not user.get("approved"):
            return {"approved": False, "packets": []}
        docs = await db.court_packets.find({"judge_email": user["email"].lower()}, {"_id": 0}).sort("created_at", -1).to_list(300)
        out = []
        for p in docs:
            primary = await db.joint_reports.find_one({"id": p["report_id"]}, {"_id": 0, "case_code": 1, "subject_label": 1}) or {}
            out.append({**public(p), "state": state(p), "professional_name": p.get("professional_name"), "case_code": primary.get("case_code"),
                        "subject_label": primary.get("subject_label"), "report_count": len(p.get("report_ids") or [])})
        return {"approved": True, "packets": out}

    @r.get("/court-dashboard/packets/{pid}")
    async def judge_view(pid: str, user=Depends(get_current_user)):
        p = await svc.for_judge(pid, user)
        await svc.mark_opened(p)
        await svc.log_court(p, f"Court Packet opened by {p['judge_name']} (court account)", user["_id"], user.get("name", ""))
        return await svc.view(p)

    @r.get("/court-dashboard/packets/{pid}/legal-report.pdf")
    async def judge_legal_pdf(pid: str, inline: int = 0, user=Depends(get_current_user)):
        p = await svc.for_judge(pid, user)
        frozen = await db.court_frozen_pdfs.find_one({"packet_id": pid, "legal_pdf": {"$exists": True}}, {"legal_pdf": 1})
        if not frozen:
            raise HTTPException(status_code=404, detail="No Professional Legal Report was attached to this submission")
        await svc.log_court(p, f"Professional Legal Report PDF {'opened' if inline else 'downloaded'} by {p['judge_name']} (court account)", user["_id"], user.get("name", ""))
        resp = _pdf_response(bytes(frozen["legal_pdf"]), f"professional-legal-report-{_safe_name(p)}.pdf")
        if inline:
            resp.headers["Content-Disposition"] = resp.headers["Content-Disposition"].replace("attachment", "inline")
        return resp

    @r.get("/court-dashboard/packets/{pid}/legal-report-sections")
    async def judge_legal_sections(pid: str, user=Depends(get_current_user)):
        """Page number of each numbered section inside the frozen Professional Report PDF (for guide → page jumps)."""
        import pymupdf
        from lens_walkthrough import WALKTHROUGH
        await svc.for_judge(pid, user)
        frozen = await db.court_frozen_pdfs.find_one({"packet_id": pid, "legal_pdf": {"$exists": True}}, {"legal_pdf": 1})
        if not frozen:
            raise HTTPException(status_code=404, detail="No Professional Legal Report was attached to this submission")
        pages = [pg.get_text() for pg in pymupdf.open(stream=bytes(frozen["legal_pdf"]), filetype="pdf")]
        start = next((i for i, t in enumerate(pages) if "How to Read This Report" in t), -1) + 1
        out, cursor = {}, start
        for n, (title, *_rest) in enumerate(WALKTHROUGH, 1):
            key = title.split(" — ")[0]
            hit = next((i for i in range(cursor, len(pages)) if key in pages[i] and f"\n{n}\n" in pages[i]), None)
            if hit is not None:
                out[n] = hit + 1
                cursor = hit
        return {"pages": out, "total_pages": len(pages)}

    @r.get("/court-dashboard/packets/{pid}/parallel-plan.pdf")
    async def judge_parallel_plan_pdf(pid: str, user=Depends(get_current_user)):
        from pdf_parallel_plan import build_parallel_plan_pdf
        p = await svc.for_judge(pid, user)
        frozen = await db.court_frozen_pdfs.find_one({"packet_id": pid}, {"agreement_card": 1})
        card = (frozen or {}).get("agreement_card") or {}
        if not card.get("safety_override"):
            raise HTTPException(status_code=404, detail="This submission has no Safety Override agreement; a Parallel Parenting summary is only produced when the override applies")
        await svc.log_court(p, f"Parallel Parenting Order Summary downloaded by {p['judge_name']} (court account)", user["_id"], user.get("name", ""))
        return _pdf_response(build_parallel_plan_pdf(card, p, p.get("professional_name") or "the professional"), f"parallel-parenting-summary-{_safe_name(p)}.pdf")

    @r.get("/court-dashboard/packets/{pid}/agreement.pdf")
    async def judge_agreement_pdf(pid: str, user=Depends(get_current_user)):
        p = await svc.for_judge(pid, user)
        frozen = await db.court_frozen_pdfs.find_one({"packet_id": pid, "agreement_pdf": {"$exists": True}}, {"agreement_pdf": 1})
        if not frozen:
            raise HTTPException(status_code=404, detail="No Co-Parenting Agreement was attached to this submission")
        await svc.log_court(p, f"Co-Parenting Agreement PDF downloaded by {p['judge_name']} (court account)", user["_id"], user.get("name", ""))
        return _pdf_response(bytes(frozen["agreement_pdf"]), f"coparenting-agreement-{_safe_name(p)}.pdf")

    @r.get("/court-dashboard/packets/{pid}/pdf")
    async def judge_pdf(pid: str, user=Depends(get_current_user)):
        p = await svc.for_judge(pid, user)
        await db.court_packets.update_one({"id": pid}, {"$inc": {"download_count": 1}})
        await svc.log_court(p, f"Court Packet PDF downloaded by {p['judge_name']} (court account)", user["_id"], user.get("name", ""))
        return _pdf_response(await svc.combined_pdf(p), f"court-packet-{_safe_name(p)}.pdf")

    @r.post("/court-dashboard/packets/{pid}/respond")
    async def judge_respond(pid: str, body: RespondIn, user=Depends(get_current_user)):
        p = await svc.for_judge(pid, user)
        return {"ok": True, "response": await svc.record_response(p, body, user["_id"], user.get("name", ""))}

    return r


def build_router(db, get_current_user, app_url, send_email, email_from_name, logger) -> APIRouter:
    svc = PacketService(db, app_url, send_email, email_from_name, logger)
    r = APIRouter()
    for sub in (_pro_routes(svc, get_current_user), _link_routes(svc), _judge_routes(svc, get_current_user)):
        r.include_router(sub)
    return r
