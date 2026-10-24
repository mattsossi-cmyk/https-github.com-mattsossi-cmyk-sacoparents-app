"""Court page checklist: what's done and what's left, as JSON (live card) and a one-page PDF."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fpdf import FPDF
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from case_safety import safety_step_text, setup_complete_for
from court_summary import build_summary
from pdf_base import _safe, render_pdf_copyright

router = APIRouter(prefix="/court-path", tags=["court-path"])

PURPLE = (76, 40, 137)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
EMERALD = (56, 161, 105)
AMBER = (217, 119, 6)
CN_NAMES = {"medical": "Medical", "educational": "Educational", "psychological": "Psychological"}
DISCLAIMER = ("Personal progress summary from SA CoParents. It is not a legal document "
              "or proof of compliance with a court order.")


REQUESTABLE = ("coparent", "self", "educational", "medical", "psychological", "foundation", "parallel")
# Professional case invite step -> Court page option.
CASE_STEP_TO_KEY = {"co-parenting": "coparent", "communication": "self", "educational": "educational",
                    "medical": "medical", "psychological": "psychological"}
RequestKey = Literal["coparent", "self", "educational", "medical", "psychological", "foundation", "parallel"]


class RequestedBody(BaseModel):
    # Which Court-page options the parent's professional asked them to complete.
    keys: List[RequestKey] = Field(default_factory=list, max_length=7)


def _day(iso: Optional[str]) -> str:
    try:
        d = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _item(key: str, label: str, status: str, detail: str, hint: str) -> Dict[str, str]:
    return {"key": key, "label": label, "status": status, "detail": detail, "hint": hint}


TITLES = {"coparent": "Co-Parenting Assessment", "self": "Self-Assessment", "educational": "Educational Assessment",
          "medical": "Medical Assessment", "psychological": "Psychological Assessment",
          "foundation": "Foundation Statement", "parallel": "Parallel Parenting Plan"}


def _st(done_at: Optional[str], started: bool = False) -> Dict[str, Optional[str]]:
    return {"status": "done" if done_at else "in_progress" if started else "todo", "finished_at": done_at or None}


async def assessment_statuses(db: AsyncIOMotorDatabase, uid: str) -> Dict[str, Dict[str, Optional[str]]]:
    """Done / in progress / not started + finish date for each Court-menu option. Status only, never answers."""
    sa = await db.self_assessment_history.find({"user_id": uid}, {"_id": 0, "completed_at": 1}).sort("completed_at", -1).to_list(1)
    cp = await db.cp_report_history.find_one({"_id": uid}, {"snapshots.submitted_at": 1}) or {}
    cn = await db.child_needs_assessments.find_one({"user_id": uid}, {"_id": 0, "completed_at": 1, "answers": 1}) or {}
    fb = await db.foundation_builder.find_one({"user_id": uid}, {"_id": 0, "updated_at": 1})
    pp = await db.parallel_parenting_plans.find_one({"user_id": uid}, {"_id": 0, "completed_at": 1, "answers": 1}) or {}
    snaps = sorted(s["submitted_at"] for s in cp.get("snapshots") or [] if s.get("submitted_at"))
    out = {
        "coparent": _st(snaps[-1] if snaps else None),
        "self": _st(sa[0]["completed_at"] if sa else None),
        "foundation": {"status": "done", "finished_at": fb.get("updated_at")} if fb else _st(None),
        "parallel": _st(pp.get("completed_at"), bool(pp.get("answers"))),
    }
    cn_at, cn_ans = cn.get("completed_at") or {}, cn.get("answers") or {}
    for k in CN_NAMES:
        out[k] = _st(cn_at.get(k), any(str(v).strip() for v in (cn_ans.get(k) or {}).values()))
    return out


async def progress_rows(db: AsyncIOMotorDatabase, uid: Optional[str], keys: List[str]) -> List[Dict[str, Optional[str]]]:
    """Professional-facing: status + finish date per requested option. Never answers."""
    st = await assessment_statuses(db, uid) if uid else {}
    return [{"key": k, "title": TITLES[k], **(st.get(k) or _st(None))} for k in REQUESTABLE if k in keys]


def case_requested_keys(case: Dict[str, Any]) -> List[str]:
    """Court-page options a professional's joint case asks for (required assigned steps, else the case type)."""
    steps = [s["assessment_type"] for s in case.get("assigned_steps") or [] if s.get("required")] or [case.get("assessment_type")]
    return [CASE_STEP_TO_KEY[t] for t in steps if t in CASE_STEP_TO_KEY]


async def _requested_items(db: AsyncIOMotorDatabase, uid: str, keys: List[str]) -> List[Dict[str, str]]:
    """One row per assessment the parent ticked as asked for, in Court-menu order."""
    st = await assessment_statuses(db, uid)
    detail = lambda s: f"Finished {_day(s['finished_at'])}".strip() if s["status"] == "done" else "In progress" if s["status"] == "in_progress" else ""  # noqa: E731
    return [_item(k, TITLES[k], st[k]["status"], detail(st[k]), "Open it from the menu on your Court page.")
            for k in REQUESTABLE if k in keys]


async def build_checklist(db: AsyncIOMotorDatabase, user: UserPublic, requested: Optional[List[str]] = None) -> Dict[str, Any]:
    uid = user.user_id
    ps = await db.portal_state.find_one(
        {"user_id": uid}, {"_id": 0, "court_key": 1, "court_legal_name": 1, "biff_logs": 1}
    ) or {}
    sa = await db.self_assessment_history.find({"user_id": uid}, {"_id": 0, "completed_at": 1}).sort("completed_at", -1).to_list(100)
    cp = await db.cp_report_history.find_one({"_id": uid}, {"snapshots.submitted_at": 1}) or {}
    cn = await db.child_needs_assessments.find_one({"user_id": uid}, {"_id": 0, "completed_at": 1}) or {}
    fb = await db.foundation_builder.find_one({"user_id": uid}, {"_id": 0, "updated_at": 1})

    case = (ps.get("court_key") or "").strip()
    snaps = sorted(s["submitted_at"] for s in cp.get("snapshots") or [] if s.get("submitted_at"))
    cn_done = [name for k, name in CN_NAMES.items() if (cn.get("completed_at") or {}).get(k)]
    cn_left = [name for name in CN_NAMES.values() if name not in cn_done]
    # id 1 is the demo entry every new portal is seeded with.
    biff = [b for b in ps.get("biff_logs") or [] if isinstance(b, dict) and b.get("id") != 1]

    items = [
        _item("case", "Case code verified", "done" if case else "todo", f"Case {case}" if case else "",
              "Enter the code from your court order on the Court page."),
    ]
    checkin = await setup_complete_for(db, uid)
    items.append(_item("family_checkin", "Safety First", "done" if checkin else "todo", "Done" if checkin else "",
                       "Open Safety First at the top of your Court page."))
    items += [
        _item("card1", "Self-Assessment", "done" if sa else "todo",
              f"{len(sa)} completed · latest {_day(sa[0]['completed_at'])}" if sa else "",
              "Take your Self-Assessment in Self Journey (Card 1)."),
        _item("card2", "Co-Parenting Relationship assessment", "done" if snaps else "todo",
              f"{len(snaps)} saved · latest {_day(snaps[-1])}" if snaps else "",
              "Complete Card 2 in Self Journey."),
        _item("card3", "Child Needs (Medical, Educational, Psychological)",
              "done" if not cn_left else "in_progress" if cn_done else "todo",
              ", ".join(cn_done) + " done" + (f" · {', '.join(cn_left)} left" if cn_left else "") if cn_done else "",
              "Fill in your child's needs in Self Journey (Card 3)."),
        _item("card4", "Foundation Statement", "done" if fb else "todo",
              f"Saved {_day(fb.get('updated_at'))}" if fb and fb.get("updated_at") else "Saved" if fb else "",
              "Write your Foundation Statement in Self Journey (Card 4)."),
        _item("biff", "BIFF messages saved", "done" if biff else "todo", f"{len(biff)} saved" if biff else "",
              "Rewrite a message in the Communication Builder and save it."),
    ]
    if requested:
        items = items[:2] + await _requested_items(db, uid, requested)
    return {
        "items": items,
        "requested_only": bool(requested),
        "done": sum(i["status"] == "done" for i in items),
        "total": len(items),
        "case_ref": case or None,
        "legal_name": (ps.get("court_legal_name") or "").strip() or None,
        "parent_name": (ps.get("court_legal_name") or "").strip() or user.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class _ChecklistPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 4, _safe(DISCLAIMER), align="C")
        render_pdf_copyright(self)


def _box(pdf: FPDF, x: float, y: float, status: str) -> None:
    s = 4.6
    if status == "done":
        pdf.set_fill_color(*EMERALD)
        pdf.rect(x, y, s, s, "F")
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.55)
        pdf.line(x + 1.0, y + 2.4, x + 2.0, y + 3.5)
        pdf.line(x + 2.0, y + 3.5, x + 3.7, y + 1.1)
    else:
        pdf.set_draw_color(*(AMBER if status == "in_progress" else MUTED))
        pdf.set_line_width(0.35)
        pdf.rect(x, y, s, s, "D")
        if status == "in_progress":
            pdf.set_fill_color(*AMBER)
            pdf.rect(x + 0.9, y + 0.9, s / 2 - 0.9, s - 1.8, "F")
    pdf.set_line_width(0.2)


def _header(pdf: FPDF, data: Dict[str, Any]) -> None:
    pdf.set_fill_color(*PURPLE)
    pdf.rect(0, 0, pdf.w, 25, "F")
    pdf.set_xy(16, 6.5)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "Court Path Checklist", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(16)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(221, 214, 254)
    pdf.cell(0, 5, _safe("SA CoParents  ·  Start with Alignment, End with Agreement"))
    pdf.set_xy(16, 30)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    meta = [f"Parent: {data['parent_name'] or '-'}", f"Case: {data['case_ref'] or 'Not entered yet'}",
            f"Prepared: {_day(data['generated_at'])}"]
    pdf.cell(0, 5, _safe("     ".join(meta)), new_x="LMARGIN", new_y="NEXT")
    if data.get("requested_only"):
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 4.6, "Showing your case, your safety step and the assessments your professional asked for.",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _safe(f"{data['done']} of {data['total']} done"), new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 0.5
    pdf.set_fill_color(238, 233, 242)
    pdf.rect(pdf.l_margin, y, pdf.epw, 2.4, "F")
    pdf.set_fill_color(*PURPLE)
    pdf.rect(pdf.l_margin, y, pdf.epw * data["done"] / max(1, data["total"]), 2.4, "F")
    pdf.set_y(y + 6)


def _rows(pdf: FPDF, items: List[Dict[str, str]]) -> None:
    for it in items:
        y = pdf.get_y()
        _box(pdf, pdf.l_margin, y + 0.6, it["status"])
        pdf.set_xy(pdf.l_margin + 8, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*INK)
        # The Family check-in row is the safety step: one fixed line, nothing else.
        step = it["key"] == "family_checkin"
        label = safety_step_text(it["status"] == "done") if step else it["label"]
        pdf.cell(95, 5.8, _safe(label))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*(EMERALD if it["status"] == "done" else AMBER if it["status"] == "in_progress" else MUTED))
        detail = "" if step else it["detail"] or "Not started"
        pdf.cell(0, 5.8, _safe(detail), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(236, 232, 245)
        pdf.line(pdf.l_margin, pdf.get_y() + 1.2, pdf.w - pdf.r_margin, pdf.get_y() + 1.2)
        pdf.set_y(pdf.get_y() + 2.6)


def _section(pdf: FPDF, title: str) -> None:
    pdf.ln(2.5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.5)


def build_checklist_pdf(data: Dict[str, Any]) -> bytes:
    pdf = _ChecklistPDF(format="Letter")
    pdf.set_auto_page_break(False)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    _header(pdf, data)
    _rows(pdf, data["items"])

    # This app can't know whether the safety step is left (only SACOparentsAlign can), so it isn't listed.
    left = [i for i in data["items"] if i["status"] != "done" and i["key"] != "family_checkin"]
    _section(pdf, "What's left")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    if not left:
        pdf.cell(0, 5, "Everything on this checklist is done. Bring it to your next meeting.", new_x="LMARGIN", new_y="NEXT")
    for it in left:
        pdf.cell(0, 4.8, _safe(f"-  {it['label']}: {it['hint']}"), new_x="LMARGIN", new_y="NEXT")

    _section(pdf, "Notes for my mediator meeting")
    pdf.set_draw_color(203, 196, 222)
    y = pdf.get_y() + 6
    while y < pdf.h - 20 and y < pdf.get_y() + 6 + 8 * 5:
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        y += 8
    return bytes(pdf.output())


@router.get("/summary")
async def get_summary(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    return await build_summary(db, user.user_id)


@router.post("/checklist")
async def get_checklist(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    return await build_checklist(db, user)


@router.post("/checklist/pdf")
async def checklist_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> StreamingResponse:
    req = _requested_shape(await _sync_professional_requests(db, user.user_id))["keys"]
    pdf_bytes = build_checklist_pdf(await build_checklist(db, user, req))
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="SA_CoParents_Court_Checklist.pdf"'},
    )


async def _sync_professional_requests(db: AsyncIOMotorDatabase, uid: str) -> Dict[str, Any]:
    """Auto-tick what a professional asked for (case invite assigned steps, or a court code's list) once per source."""
    doc = await db.court_requested.find_one({"user_id": uid}, {"_id": 0}) or {}
    applied = set(doc.get("applied") or [])
    found = []  # (source, keys, professional name)
    ps = await db.portal_state.find_one({"user_id": uid}, {"_id": 0, "court_key": 1}) or {}
    ck = (ps.get("court_key") or "").strip()
    if ck and f"court:{ck}" not in applied:
        kd = await db.portal_court_keys.find_one({"case_id": ck, "revoked_at": None}, {"_id": 0, "requested": 1, "mediator_name": 1})
        if kd and kd.get("requested"):
            found.append((f"court:{ck}", kd["requested"], kd.get("mediator_name")))
    async for case in db.joint_alignment_cases.find(
        {"parents.user_id": uid, "status": {"$ne": "cancelled"}},
        {"_id": 0, "case_id": 1, "assigned_steps": 1, "assessment_type": 1, "professional.name": 1},
    ):
        if f"case:{case['case_id']}" in applied:
            continue
        keys = case_requested_keys(case)
        if keys:
            found.append((f"case:{case['case_id']}", keys, (case.get("professional") or {}).get("name")))
    if not found:
        return doc
    keys = [k for _, ks, _ in found for k in ks if k in REQUESTABLE]
    await db.court_requested.update_one(
        {"user_id": uid},
        {
            "$addToSet": {"keys": {"$each": keys}, "pro_keys": {"$each": keys}, "applied": {"$each": [src for src, _, _ in found]}},
            "$set": {"pro_name": found[-1][2] or doc.get("pro_name"), "updated_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True,
    )
    return await db.court_requested.find_one({"user_id": uid}, {"_id": 0}) or {}


def _requested_shape(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "keys": [k for k in REQUESTABLE if k in (doc.get("keys") or [])],
        "professional_keys": [k for k in REQUESTABLE if k in (doc.get("pro_keys") or [])],
        "professional_name": doc.get("pro_name"),
    }


@router.get("/reminders/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_requested_reminders(token: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> HTMLResponse:
    from requested_reminders import read_unsubscribe_token
    from self_assessment_routes import _UNSUB_PAGE

    uid = read_unsubscribe_token(token)
    if not uid:
        return HTMLResponse(_UNSUB_PAGE.format(title="Link not valid", body="This unsubscribe link isn't valid."), status_code=400)
    await db.court_requested.update_one({"user_id": uid}, {"$set": {"reminders_off": True}}, upsert=True)
    return HTMLResponse(_UNSUB_PAGE.format(
        title="You're unsubscribed",
        body="You won't get weekly reminders about waiting assessments anymore. Everything stays saved in your account.",
    ))


class RemindersBody(BaseModel):
    enabled: bool


@router.get("/reminders")
async def get_reminder_setting(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db.court_requested.find_one({"user_id": user.user_id}, {"_id": 0, "reminders_off": 1}) or {}
    return {"enabled": not doc.get("reminders_off")}


@router.put("/reminders")
async def put_reminder_setting(
    body: RemindersBody, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    await db.court_requested.update_one({"user_id": user.user_id}, {"$set": {"reminders_off": not body.enabled}}, upsert=True)
    return {"enabled": body.enabled}


@router.get("/requested")
async def get_requested(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    return _requested_shape(await _sync_professional_requests(db, user.user_id))


@router.put("/requested")
async def put_requested(
    body: RequestedBody, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    keys = [k for k in REQUESTABLE if k in body.keys]
    await db.court_requested.update_one(
        {"user_id": user.user_id},
        {"$set": {"keys": keys, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return _requested_shape(await db.court_requested.find_one({"user_id": user.user_id}, {"_id": 0}) or {})
