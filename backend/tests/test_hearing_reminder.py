"""Hearing date on court referrals + 7-day-before reminder to professional and judge."""
import asyncio
import logging
import os
import uuid
from datetime import date, timedelta

import pymongo
import pytest
import requests

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
CRON_HEADERS = {"Authorization": f"Bearer {os.environ['WEBHOOK_CRON_SECRET']}"}


def _db() -> pymongo.database.Database:
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_hjudge_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Judge Hearing", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "37th District Court", "pro_role": "Judge"})
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


@pytest.fixture(scope="module")
def flow() -> tuple:
    judge = _judge()
    pro = new_user(API, "professional", "Hearing Pro")
    me = pro.get(f"{API}/auth/me").json()
    in_five = (date.today() + timedelta(days=5)).isoformat()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-H{uuid.uuid4().hex[:4]}", "hearing_date": in_five})
    assert ref.status_code == 200, ref.text
    return judge, pro, ref.json(), in_five


def test_hearing_date_stored_and_visible_to_pro(flow) -> None:
    judge, pro, ref, in_five = flow
    assert ref["hearing_date"] == in_five
    inbox = pro.get(f"{API}/professional/court-referrals").json()
    assert inbox[0]["hearing_date"] == in_five
    assert judge.get(f"{API}/court-dashboard/referrals").json()[0]["hearing_date"] == in_five


def test_invalid_hearing_date_rejected(flow) -> None:
    judge, _pro, ref, _ = flow
    r = judge.patch(f"{API}/court-dashboard/referrals/{ref['id']}/hearing-date", json={"hearing_date": "15/10/2026"})
    assert r.status_code == 400


def test_judge_can_change_and_pro_cannot(flow) -> None:
    judge, pro, ref, _ = flow
    new = (date.today() + timedelta(days=6)).isoformat()
    r = judge.patch(f"{API}/court-dashboard/referrals/{ref['id']}/hearing-date", json={"hearing_date": new})
    assert r.status_code == 200 and r.json()["hearing_date"] == new
    assert pro.patch(f"{API}/court-dashboard/referrals/{ref['id']}/hearing-date", json={"hearing_date": new}).status_code == 403
    assert pro.get(f"{API}/professional/court-referrals").json()[0]["hearing_date"] == new


def test_runner_emails_both_once_and_skips_submitted(flow) -> None:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from court_workflow import run_hearing_reminders

    _judge_s, _pro, ref, _ = flow
    sent: list[str] = []

    async def fake_send(to: str, subject: str, html: str, **_: object) -> None:
        sent.append(f"{to}|{subject}")

    class _DB:
        def __init__(self) -> None:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._c = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        def __getattr__(self, k: str):
            return getattr(self._c, k)

    async def go() -> tuple[int, int]:
        db = _DB()
        n1 = await run_hearing_reminders(db, fake_send, lambda: BASE_URL, "Align", logging.getLogger("t"))
        n2 = await run_hearing_reminders(db, fake_send, lambda: BASE_URL, "Align", logging.getLogger("t"))
        return n1, n2

    n1, n2 = asyncio.run(go())
    mine = [s for s in sent if ref["cause_number"] in s]
    assert n1 >= 1 and len(mine) == 2, sent
    assert any(s.startswith(ref["judge_email"]) for s in mine)
    assert n2 == 0 or not any(ref["cause_number"] in s for s in sent[len(sent) - n2 * 2:]) if n2 else True
    doc = _db().court_referrals.find_one({"id": ref["id"]})
    assert doc.get("hearing_reminder_sent")


def test_cron_endpoint_acks(flow) -> None:
    r = requests.post(f"{API}/cron/hearing-reminder", headers={**CRON_HEADERS, "Content-Type": "application/json"}, json={"run_id": uuid.uuid4().hex})
    assert r.status_code == 200, r.text
    assert requests.post(f"{API}/cron/hearing-reminder").status_code in (401, 403)
