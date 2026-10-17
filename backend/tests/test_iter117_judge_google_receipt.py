"""Iter-117: Google sign-in for judges; AI-assistance line in submission receipt + court email."""
import os

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
import court_workflow as cw  # noqa: E402
import google_auth as ga  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_judge_role_allowed_via_google_and_parent_still_refused():
    assert "judge" in ga.GOOGLE_ROLES and requests.get(f"{API}/auth/google/config").json()["roles"] == ["professional", "admin", "judge"]
    import asyncio

    from fastapi import HTTPException
    judge = _db.users.find_one({"role": "judge"}, {"email": 1})
    parent = _db.users.find_one({"role": "parent"}, {"email": 1})
    assert judge and parent

    async def run():
        j = await ga.resolve_google_user(judge["email"])
        try:
            await ga.resolve_google_user(parent["email"])
            return j, 200
        except HTTPException as ex:
            return j, ex.status_code
    j, code = asyncio.run(run())
    assert j["role"] == "judge" and code == 403
    src = open("/app/frontend/src/components/GoogleAuth.jsx").read()
    assert '"/court-dashboard"' in src and 'role === "judge"' in src


def test_submission_email_and_receipt_carry_ai_disclosure():
    html = cw._submission_email_html({"name": "Pro"}, {"cause_number": "C-1"}, 2, lambda: "https://x", "SA CoParents", None, "AI drafting assistance: none. All enclosed text was written by the professional.")
    assert "AI drafting assistance: none" in html and "font-style:italic" in html
    html2 = cw._submission_email_html({"name": "Pro"}, {"cause_number": "C-1"}, 2, lambda: "https://x", "SA CoParents", "Summary line", "AI drafting assistance: GPT-5.5.")
    assert html2.index("Summary line") < html2.index("AI drafting assistance: GPT-5.5.")
    assert 'sub["ai_disclosure"] = _ai_disclosure(doc)' in open("/app/backend/court_workflow.py").read()
    assert "receipt-ai-disclosure" in open("/app/frontend/src/components/SubmissionReceipt.jsx").read()
