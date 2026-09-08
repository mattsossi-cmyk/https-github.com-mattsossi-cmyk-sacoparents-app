"""Session-level cleanup: remove fixture accounts the suite creates so admin panels and digests stay clean."""
import os
import re

import pytest

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

FIXTURE_EMAIL = re.compile(r"@(example\.com|x\.com)$", re.I)


def _purge_fixture_accounts() -> None:
    import pymongo

    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    ids = [u["_id"] for u in db.users.find({"email": FIXTURE_EMAIL}, {"_id": 1})]
    if ids:
        rids = [r["id"] for r in db.joint_reports.find({"created_by": {"$in": ids}}, {"id": 1})]
        db.professional_notes.delete_many({"report_id": {"$in": rids}})
        db.access_events.delete_many({"report_id": {"$in": rids}})
        db.invitations.delete_many({"$or": [{"report_id": {"$in": rids}}, {"invitee_email": FIXTURE_EMAIL}]})
        db.joint_reports.delete_many({"$or": [{"created_by": {"$in": ids}}, {"participants.a.user_id": {"$in": ids}}, {"participants.b.user_id": {"$in": ids}}]})
        db.cases.delete_many({"user_id": {"$in": ids}})
        db.connections.delete_many({"user_ids": {"$in": ids}})
        db.cron_runs.delete_many({"pro_id": {"$in": ids}})
        db.users.delete_many({"_id": {"$in": ids}})
    db.login_attempts.delete_many({"identifier": FIXTURE_EMAIL})
    client.close()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Under pytest-xdist only the controller runs this (workers carry `workerinput`), so cleanup happens once, after all workers finish.
    if hasattr(session.config, "workerinput"):
        return
    _purge_fixture_accounts()
