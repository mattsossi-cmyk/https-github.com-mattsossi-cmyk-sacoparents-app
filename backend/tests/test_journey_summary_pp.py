"""Backend tests for Self Journey summary celebration + PDF, Journey Guide chat,
and Parallel Parenting plan + checks. Covers iteration 110 review requests."""
import os
import time
import uuid
import pytest
import requests
from io import BytesIO
import pypdf


def _pdf_text(data: bytes) -> str:
    try:
        reader = pypdf.PdfReader(BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        return f"__PDF_PARSE_FAIL__ {e}"

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PASS = "TestPass123!"


def _register_fresh():
    email = f"TEST_j110_{uuid.uuid4().hex[:10]}@test.com"
    name = f"Test {email[:14]}"
    r = requests.post(f"{API}/auth/register", json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": PASS, "name": name}, timeout=20)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in register: {data}"
    from ai_ready import accept_ai_notice
    accept_ai_notice(API, {"Authorization": f"Bearer {tok}"})
    return email, tok


@pytest.fixture(scope="module")
def fresh_user():
    email, tok = _register_fresh()
    return {"email": email, "token": tok, "headers": {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}}


@pytest.fixture(scope="module")
def parent1():
    r = requests.post(f"{API}/auth/login", json={"email": "parent1@test.com", "password": PASS}, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    return {"token": tok, "headers": {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}}


# ---------------- Journey Summary PDF ----------------
class TestJourneySummary:
    def test_celebrated_default_false(self, fresh_user):
        r = requests.get(f"{API}/journey-summary/celebrated", headers=fresh_user["headers"], timeout=20)
        assert r.status_code == 200, r.text
        assert r.json() == {"celebrated": False}

    def test_pdf_download_fresh_user_shows_not_completed(self, fresh_user):
        r = requests.get(f"{API}/journey-summary/pdf", headers=fresh_user["headers"], timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")
        text = _pdf_text(r.content)
        assert "Journey Summary" in text, f"missing title; got: {text[:400]}"
        assert "not legal advice" in text.lower() or "not legal" in text.lower(), text[:600]
        assert "safety" in text.lower(), text[:600]
        assert "Not completed yet" in text, f"expected 'Not completed yet' for fresh user. Got: {text[:800]}"

    def test_mark_celebrated_persists(self, fresh_user):
        r = requests.post(f"{API}/journey-summary/celebrated", headers=fresh_user["headers"], timeout=20)
        assert r.status_code == 200
        assert r.json() == {"celebrated": True}
        r2 = requests.get(f"{API}/journey-summary/celebrated", headers=fresh_user["headers"], timeout=20)
        assert r2.json() == {"celebrated": True}

    def test_pdf_requires_auth(self):
        r = requests.get(f"{API}/journey-summary/pdf", timeout=20)
        assert r.status_code in (401, 403)


# ---------------- Journey Guide chat ----------------
class TestJourneyGuide:
    def test_coparenting_chat_empty_default(self, fresh_user):
        r = requests.get(f"{API}/journey-guide/coparenting/chat", headers=fresh_user["headers"], timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "messages" in body

    def test_child_needs_chat_empty_default(self, fresh_user):
        r = requests.get(f"{API}/journey-guide/child-needs/chat", headers=fresh_user["headers"], timeout=20)
        assert r.status_code == 200, r.text
        assert "messages" in r.json()

    def test_unknown_topic_404(self, fresh_user):
        r = requests.get(f"{API}/journey-guide/not-a-topic/chat", headers=fresh_user["headers"], timeout=20)
        assert r.status_code == 404

    def test_coparenting_chat_post_and_new(self, fresh_user):
        r = requests.post(
            f"{API}/journey-guide/coparenting/chat",
            headers=fresh_user["headers"],
            json={"message": "What should I write in a short BIFF message?"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # chat POST returns reply (and session_id); GET then should have messages
        assert body.get("reply"), f"no reply: {body}"
        g = requests.get(f"{API}/journey-guide/coparenting/chat", headers=fresh_user["headers"], timeout=20)
        assert g.status_code == 200
        msgs = g.json().get("messages") or []
        assert len(msgs) >= 2, f"expected persisted history, got {msgs}"
        # New chat
        n = requests.post(f"{API}/journey-guide/coparenting/chat/new", headers=fresh_user["headers"], timeout=20)
        assert n.status_code == 200
        # confirm cleared
        r2 = requests.get(f"{API}/journey-guide/coparenting/chat", headers=fresh_user["headers"], timeout=20)
        msgs = r2.json().get("messages") or []
        assert len(msgs) == 0


# ---------------- Parallel Parenting ----------------
class TestParallelParenting:
    def test_get_me_default(self, fresh_user):
        r = requests.get(f"{API}/parallel-parenting/me", headers=fresh_user["headers"], timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("checks") == {} or isinstance(d.get("checks"), dict)
        assert d.get("step") == 0

    def test_put_checks_persist_and_ignore_unknown(self, fresh_user):
        payload = {
            "answers": {},
            "notes": {},
            "checks": {
                "child_focus": ["cf1", "cf2", "NOT_AN_ITEM"],
                "court_check": ["cc1"],
                "FAKE_KEY": ["x"],
            },
            "step": 1,
            "completed": False,
        }
        r = requests.put(f"{API}/parallel-parenting/me", headers=fresh_user["headers"], json=payload, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        # unknown keys dropped
        assert "FAKE_KEY" not in d.get("checks", {})
        # verify via GET
        r2 = requests.get(f"{API}/parallel-parenting/me", headers=fresh_user["headers"], timeout=20)
        checks = r2.json().get("checks", {})
        # child_focus should still exist and NOT_AN_ITEM removed
        if "child_focus" in checks:
            assert "NOT_AN_ITEM" not in checks["child_focus"]

    def test_pdf_download(self, fresh_user):
        # PP PDF requires at least one chosen option
        payload = {
            "answers": {"communication_channel": "app"},
            "notes": {},
            "checks": {"child_focus": ["cf1"], "court_check": ["cc1"]},
            "step": 2,
            "completed": False,
        }
        pr = requests.put(f"{API}/parallel-parenting/me", headers=fresh_user["headers"], json=payload, timeout=20)
        assert pr.status_code == 200, pr.text
        r = requests.post(f"{API}/parallel-parenting/pdf", headers=fresh_user["headers"], json={}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.content.startswith(b"%PDF")
        text = _pdf_text(r.content)
        assert "Quick check" in text, f"missing Quick check section: {text[:1200]}"


# ---------------- Full celebration flow ----------------
class TestCelebrationFlow:
    def test_complete_all_five_then_celebrated_flag(self):
        email, tok = _register_fresh()
        H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
        # 1) Self-Assessment: 20 keys at value 3
        import json as _json
        content = _json.load(open("/app/backend/self_assessment_content.json"))
        keys = [f"{s['key']}_{i+1}" for s in content["sections"] for i in range(len(s["questions"]))]
        answers = {k: 3 for k in keys}
        sa = requests.post(
            f"{API}/self-assessment/complete",
            headers=H,
            json={"answers": answers, "reflections": {}, "tips": {}, "goal": "Be patient", "parent_name": "Test"},
            timeout=30,
        )
        assert sa.status_code == 200, sa.text

        # 2) Co-Parenting: fetch schema, answer all questions value 3, complete
        schema = requests.get(f"{API}/coparenting/schema", timeout=20).json()
        qids = [q["id"] for s in schema["sections"] for q in s["questions"]]
        cp_ans = {qid: 3 for qid in qids}
        br = requests.post(f"{API}/coparenting/answers/bulk", headers=H, json={"answers": cp_ans}, timeout=30)
        assert br.status_code == 200, br.text
        cc = requests.post(f"{API}/coparenting/complete", headers=H, timeout=20)
        assert cc.status_code == 200, cc.text

        # 3) Child Needs: 3 categories
        for cat in ("educational", "medical", "psychological"):
            # pick any field - use content
            cn_content = _json.load(open("/app/backend/child_needs_content.json"))
            fields = {c["key"]: c["fields"] for c in cn_content["categories"]}[cat]
            answers_cat = {}
            for f in fields[:2]:
                if f["type"] == "select":
                    answers_cat[f["id"]] = f["options"][0]
                else:
                    answers_cat[f["id"]] = "Test content"
            r = requests.put(f"{API}/child-needs/me/{cat}", headers=H, json={"answers": answers_cat, "acknowledged": True}, timeout=20)
            assert r.status_code == 200, f"{cat}: {r.status_code} {r.text}"

        # 4) Verify PDF now does NOT say "Not completed yet" (loose check)
        pdf = requests.get(f"{API}/journey-summary/pdf", headers=H, timeout=30)
        assert pdf.status_code == 200
        text = _pdf_text(pdf.content)
        assert "Progress:" in text, text[:800]
        assert "5" in text  # loose check for 5 of 5
        assert "Not completed yet" not in text, "No category should say Not completed yet after full flow"

        # 5) celebrated starts false, mark true, persists
        cel = requests.get(f"{API}/journey-summary/celebrated", headers=H, timeout=20)
        assert cel.json()["celebrated"] is False
        requests.post(f"{API}/journey-summary/celebrated", headers=H, timeout=20)
        cel2 = requests.get(f"{API}/journey-summary/celebrated", headers=H, timeout=20)
        assert cel2.json()["celebrated"] is True
