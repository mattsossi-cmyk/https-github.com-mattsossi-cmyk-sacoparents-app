"""Iter-115: Google sign-in (existing pro/admin only), assistant model switch, model disclosure lines."""
import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
from test_iter108_required_step import _case  # noqa: E402

import assistant as asst  # noqa: E402
import google_auth as ga  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_google_config_and_bad_session_rejected():
    r = requests.get(f"{API}/auth/google/config")
    assert r.status_code == 200 and r.json()["roles"] == ["professional", "admin", "judge"]
    r = requests.post(f"{API}/auth/google/session", json={"session_id": "not-a-real-session"})
    assert r.status_code in (401, 502) and "access_token" not in r.cookies
    assert requests.post(f"{API}/auth/google/session", json={"session_id": "  "}).status_code == 400


def test_google_matches_existing_pro_and_admin_only():
    import asyncio

    from fastapi import HTTPException
    pro, pa, pb, rid = _case()
    pro_email = pro.get(f"{API}/auth/me").json()["email"]
    pa_email = pa.get(f"{API}/auth/me").json()["email"]
    before = _db.users.count_documents({})

    async def run():
        ok = await ga.resolve_google_user(pro_email)
        out = {"pro": ok["email"]}
        for e in (pa_email, f"nobody-{uuid.uuid4().hex[:6]}@example.com"):
            try:
                await ga.resolve_google_user(e)
                out[e] = 200
            except HTTPException as ex:
                out[e] = (ex.status_code, ex.detail)
        return out
    res = asyncio.run(run())
    assert res["pro"] == pro_email
    assert res[pa_email][0] == 403 and "existing professional, court and admin" in res[pa_email][1]
    assert all(v[0] == 403 for k, v in res.items() if k != "pro")
    assert _db.users.count_documents({}) == before  # never creates accounts
    assert _db.login_attempts.count_documents({"email": pa_email, "method": "google", "ok": False}) >= 1
    assert pro.get(f"{API}/auth/me").status_code == 200  # password session unchanged


def test_assistant_model_switch_records_model_used():
    pro, pa, pb, rid = _case()
    assert set(asst.MODELS) == {"gpt", "claude"} and asst.MODELS["gpt"][1] == "gpt-5.5" and asst.MODELS["claude"][1] == "claude-sonnet-5-5"
    sid = str(uuid.uuid4())
    for m, name in (("claude", "claude-sonnet-5-5"), ("gpt", "gpt-5.5")):
        r = pro.post(f"{API}/assistant/chat", json={"session_id": sid, "case_id": rid, "message": "Reply with the single word OK.", "model": m}, stream=True, timeout=120)
        assert r.status_code == 200
        body = b"".join(r.iter_content(4096)).decode()
        assert '"done": true' in body
        last = _db.assistant_messages.find_one({"session_id": sid, "role": "assistant"}, sort=[("at", -1)])
        assert last and last["model"] == name
    assert pro.post(f"{API}/assistant/chat", json={"session_id": sid, "message": "hi", "model": "bogus"}, stream=True, timeout=120).status_code == 200  # falls back to gpt


def test_model_disclosure_fields_present_in_views():
    import inspect

    import agreement_ai
    import joint_ai
    import joint_engine
    assert "ai_disclosure" in inspect.getsource(joint_ai.effective_joint_report)
    assert '"ai_disclosure"' in inspect.getsource(joint_engine) and '"ai_model"' in inspect.getsource(joint_engine)
    assert agreement_ai.MODEL_NAME == "gpt-5.4-mini"
    import pdf_report
    assert "ai_disclosure" in inspect.getsource(pdf_report)
    for f, needle in (("/app/frontend/src/pages/JointReport.jsx", "jr-ai-disclosure"), ("/app/frontend/src/components/AgreementDocument.jsx", "agreement-ai-disclosure"), ("/app/frontend/src/pages/LegalLensReport.jsx", "Drafted with ${rep.ai_drafts[props.id].model}")):
        assert needle in open(f).read(), f

