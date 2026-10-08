"""Backend tests: Parallel Parenting Option Builder (plan, tip, chat, PDF)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
PP = f"{API}/parallel-parenting"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def tok1():
    return _login("parent1@test.com", "TestPass123!")


@pytest.fixture(scope="module")
def tok2():
    return _login("parent2@test.com", "TestPass123!")


def _h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module", autouse=True)
def _cleanup(tok1, tok2):
    # best effort cleanup via a dedicated reset if available; else leave to teardown via Mongo in main agent env
    yield


class TestAuth:
    def test_get_me_requires_auth(self):
        r = requests.get(f"{PP}/me", timeout=15)
        assert r.status_code in (401, 403)

    def test_get_me_authed(self, tok1):
        r = requests.get(f"{PP}/me", headers=_h(tok1), timeout=15)
        assert r.status_code == 200
        data = r.json()
        for k in ("answers", "notes", "tips", "step"):
            assert k in data


class TestSavePlan:
    def test_put_filters_unknown_ids(self, tok1):
        body = {
            "answers": {
                "communication_channel": "app",   # valid
                "communication_channel_bad": "app",  # unknown qid
                "communication_timing": "nope",   # invalid option
            },
            "notes": {"communication": "keep it brief", "bogus": "x"},
            "step": 1,
            "completed": False,
        }
        r = requests.put(f"{PP}/me", headers=_h(tok1), json=body, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["answers"] == {"communication_channel": "app"}
        assert d["notes"] == {"communication": "keep it brief"}
        assert d["step"] == 1

    def test_step_out_of_range(self, tok1):
        r = requests.put(f"{PP}/me", headers=_h(tok1), json={"step": 99}, timeout=15)
        assert r.status_code == 422

    def test_persistence_get(self, tok1):
        r = requests.get(f"{PP}/me", headers=_h(tok1), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["answers"].get("communication_channel") == "app"
        assert d["step"] == 1

    def test_completed_sets_completed_at(self, tok1):
        r = requests.put(f"{PP}/me", headers=_h(tok1), json={
            "answers": {"communication_channel": "app"},
            "notes": {},
            "step": 6,
            "completed": True,
        }, timeout=15)
        assert r.status_code == 200
        first = r.json().get("completed_at")
        assert first
        # Idempotent: calling again keeps same completed_at
        r2 = requests.put(f"{PP}/me", headers=_h(tok1), json={
            "answers": {"communication_channel": "email"},
            "notes": {},
            "step": 6,
            "completed": True,
        }, timeout=15)
        assert r2.json().get("completed_at") == first


class TestTip:
    def test_tip_unknown_step(self, tok1):
        r = requests.post(f"{PP}/ai/tip", headers=_h(tok1),
                          json={"step": "nope", "answers": {}, "notes": "", "safety_flagged": False}, timeout=30)
        assert r.status_code == 400

    def test_tip_no_valid_answers(self, tok1):
        r = requests.post(f"{PP}/ai/tip", headers=_h(tok1),
                          json={"step": "communication", "answers": {}, "notes": "", "safety_flagged": False}, timeout=30)
        assert r.status_code == 400

    def test_tip_success_and_saved(self, tok1):
        r = requests.post(f"{PP}/ai/tip", headers=_h(tok1), json={
            "step": "communication",
            "answers": {"communication_channel": "app"},
            "notes": "",
            "safety_flagged": True,  # parent1 is flagged; should produce grey-rock tip
        }, timeout=60)
        assert r.status_code == 200, r.text
        tip = r.json().get("tip", "")
        assert tip and "**" not in tip and "*" not in tip
        # Saved on plan
        g = requests.get(f"{PP}/me", headers=_h(tok1), timeout=15).json()
        assert g.get("tips", {}).get("communication")


class TestChat:
    def test_chat_memory_multiturn(self, tok2):
        r1 = requests.post(f"{PP}/ai/chat", headers=_h(tok2),
                           json={"message": "My child's name is Zuko.", "safety_flagged": False}, timeout=60)
        assert r1.status_code == 200, r1.text
        sid = r1.json()["session_id"]
        reply1 = r1.json()["reply"]
        assert reply1 and "**" not in reply1
        r2 = requests.post(f"{PP}/ai/chat", headers=_h(tok2),
                           json={"message": "What's my child's name?", "session_id": sid, "safety_flagged": False}, timeout=60)
        assert r2.status_code == 200
        reply2 = r2.json()["reply"].lower()
        assert "zuko" in reply2, f"expected name recall, got: {reply2}"

    def test_chat_history_get(self, tok2):
        r = requests.get(f"{PP}/ai/chat", headers=_h(tok2), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("session_id")
        assert len(data.get("messages", [])) >= 2


class TestPDF:
    def test_pdf_requires_data(self, tok2):
        # parent2 may have no plan — ensure empty gives 400
        requests.put(f"{PP}/me", headers=_h(tok2), json={"answers": {}, "notes": {}, "step": 0}, timeout=15)
        r = requests.post(f"{PP}/pdf", headers=_h(tok2), timeout=30)
        assert r.status_code == 400

    def test_pdf_success(self, tok1):
        r = requests.post(f"{PP}/pdf", headers=_h(tok1), timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 2000
