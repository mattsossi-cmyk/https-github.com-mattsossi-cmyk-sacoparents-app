"""Court compare agreement tracker + celebration tests (iteration 105)."""
import os
import re
import zlib
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    with open("/app/frontend/.env") as _f:
        for _line in _f:
            if _line.startswith("REACT_APP_BACKEND_URL="):
                BASE = _line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"

PASS = "TestPass123!"
P3 = "parent3@test.com"
P4 = "parent4@test.com"
P1 = "parent1@test.com"
P2 = "parent2@test.com"

INTENT_NOTICE = (
    "By marking an area as agreed, the parties have evidenced their intent to make an agreement. "
    "This document does not reflect a binding agreement on the parties."
)


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASS}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module", autouse=True)
def _reseed_and_share():
    # Reseed before and after
    import subprocess
    subprocess.run(
        ["python", "-c",
         "from dotenv import load_dotenv; load_dotenv('.env'); "
         "from seed_court_compare_pair import run; import asyncio; print(asyncio.run(run()))"],
        cwd="/app/backend", check=True, capture_output=True,
    )
    t3 = _login(P3); t4 = _login(P4)
    for tok in (t3, t4):
        r = requests.post(f"{API}/court-path/compare/share", json={"shared": True}, headers=_h(tok), timeout=20)
        assert r.status_code == 200
    yield {"t3": t3, "t4": t4}
    subprocess.run(
        ["python", "-c",
         "from dotenv import load_dotenv; load_dotenv('.env'); "
         "from seed_court_compare_pair import run; import asyncio; print(asyncio.run(run()))"],
        cwd="/app/backend", check=True, capture_output=True,
    )


def _compare(tok):
    r = requests.get(f"{API}/court-path/compare", headers=_h(tok), timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def _diff_key(data, idx=0):
    return data["difference"][idx]["key"]


class TestComparePayload:
    def test_payload_shape(self, _reseed_and_share):
        data = _compare(_reseed_and_share["t3"])
        assert data["state"] == "ready"
        assert data["intent_notice"] == INTENT_NOTICE
        assert "progress" in data
        prog = data["progress"]
        for k in ("agreed", "total", "all_agreed", "celebrated"):
            assert k in prog
        assert prog["total"] == 6
        for r in data["difference"]:
            for k in ("key", "agreed", "by_me", "by_them", "note", "agreed_at"):
                assert k in r
            assert r["key"] == f"{r['source']}|{r['area']}"


class TestAgreeFlow:
    def test_agree_and_shared_state(self, _reseed_and_share):
        t3, t4 = _reseed_and_share["t3"], _reseed_and_share["t4"]
        # clean slate from any prior test ordering is fine; just pick an area not yet marked
        d3 = _compare(t3)
        area = _diff_key(d3, 0)

        # Ensure unmarked (undo for safety by both)
        for tok in (t3, t4):
            requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(tok), timeout=20)

        # parent3 agrees
        r = requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t3), timeout=20)
        assert r.status_code == 200
        row3 = next(x for x in r.json()["difference"] if x["key"] == area)
        assert row3["agreed"] and row3["by_me"] and not row3["by_them"]

        # parent4 sees agreed=True, by_me=False, by_them=True
        d4 = _compare(t4)
        row4 = next(x for x in d4["difference"] if x["key"] == area)
        assert row4["agreed"] and row4["by_them"] and not row4["by_me"]

        # parent4 undo (agreed:false) must NOT remove parent3's mark
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(t4), timeout=20)
        d3b = _compare(t3)
        row3b = next(x for x in d3b["difference"] if x["key"] == area)
        assert row3b["agreed"] and row3b["by_me"]

        # parent4 "I agree too"
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t4), timeout=20)
        d3c = _compare(t3); d4c = _compare(t4)
        r3 = next(x for x in d3c["difference"] if x["key"] == area)
        r4 = next(x for x in d4c["difference"] if x["key"] == area)
        assert r3["by_me"] and r3["by_them"]
        assert r4["by_me"] and r4["by_them"]

        # parent3 undo own -> still agreed via parent4
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(t3), timeout=20)
        d3d = _compare(t3)
        r3d = next(x for x in d3d["difference"] if x["key"] == area)
        assert r3d["agreed"] and not r3d["by_me"] and r3d["by_them"]

        # parent4 undo own -> not agreed
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(t4), timeout=20)
        d3e = _compare(t3)
        r3e = next(x for x in d3e["difference"] if x["key"] == area)
        assert not r3e["agreed"] and not r3e["by_me"] and not r3e["by_them"]

    def test_bogus_area_400(self, _reseed_and_share):
        r = requests.post(f"{API}/court-path/compare/agree",
                          json={"area": "bogus|nope", "agreed": True},
                          headers=_h(_reseed_and_share["t3"]), timeout=20)
        assert r.status_code == 400
        assert "aren't" in r.json()["detail"] or "isn't" in r.json()["detail"]

    def test_409_when_not_ready(self):
        tok = _login(P2)
        r = requests.post(f"{API}/court-path/compare/agree",
                          json={"area": "x|y", "agreed": True},
                          headers=_h(tok), timeout=20)
        assert r.status_code == 409


class TestNote:
    def test_note_requires_agreed(self, _reseed_and_share):
        t3 = _reseed_and_share["t3"]
        d = _compare(t3)
        area = _diff_key(d, 1)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(t3), timeout=20)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(_reseed_and_share["t4"]), timeout=20)
        r = requests.put(f"{API}/court-path/compare/agree/note",
                         json={"area": area, "note": "hello"}, headers=_h(t3), timeout=20)
        assert r.status_code == 400
        assert "Mark this area as agreed first" in r.json()["detail"]

    def test_note_saved_whitespace_and_visible(self, _reseed_and_share):
        t3, t4 = _reseed_and_share["t3"], _reseed_and_share["t4"]
        d = _compare(t3)
        area = _diff_key(d, 1)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t3), timeout=20)
        # whitespace collapsed
        noisy = "hello   world  \n\t  friends"
        r = requests.put(f"{API}/court-path/compare/agree/note",
                         json={"area": area, "note": noisy}, headers=_h(t3), timeout=20)
        assert r.status_code == 200
        row = next(x for x in r.json()["difference"] if x["key"] == area)
        assert row["note"] == "hello world friends"
        # other parent sees it
        d4 = _compare(t4)
        r4 = next(x for x in d4["difference"] if x["key"] == area)
        assert r4["note"] == "hello world friends"

    def test_note_max_300(self, _reseed_and_share):
        t3 = _reseed_and_share["t3"]
        d = _compare(t3)
        area = _diff_key(d, 2)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t3), timeout=20)
        long_note = "a" * 500  # within 600 pydantic limit but set_note truncates to 300
        r = requests.put(f"{API}/court-path/compare/agree/note",
                         json={"area": area, "note": long_note}, headers=_h(t3), timeout=20)
        assert r.status_code == 200
        row = next(x for x in r.json()["difference"] if x["key"] == area)
        assert len(row["note"]) == 300

    def test_note_kept_through_undo_reagree(self, _reseed_and_share):
        t3, t4 = _reseed_and_share["t3"], _reseed_and_share["t4"]
        d = _compare(t3)
        area = _diff_key(d, 3)
        # clean
        for tok in (t3, t4):
            requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(tok), timeout=20)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t3), timeout=20)
        requests.put(f"{API}/court-path/compare/agree/note",
                     json={"area": area, "note": "keepnote"}, headers=_h(t3), timeout=20)
        # undo own -> note should still be stored (invisible since not agreed)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": False}, headers=_h(t3), timeout=20)
        # re-agree -> note comes back
        r = requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t3), timeout=20)
        row = next(x for x in r.json()["difference"] if x["key"] == area)
        assert row["note"] == "keepnote"


class TestCelebration:
    def test_celebrated_endpoint(self, _reseed_and_share):
        t3, t4 = _reseed_and_share["t3"], _reseed_and_share["t4"]
        # mark all differing areas agreed by parent3
        d = _compare(t3)
        for row in d["difference"]:
            requests.post(f"{API}/court-path/compare/agree",
                          json={"area": row["key"], "agreed": True}, headers=_h(t3), timeout=20)
        d2 = _compare(t3)
        assert d2["progress"]["all_agreed"] is True
        assert d2["progress"]["celebrated"] is False

        r = requests.post(f"{API}/court-path/compare/celebrated", headers=_h(t3), timeout=20)
        assert r.status_code == 200 and r.json() == {"ok": True}

        d3 = _compare(t3)
        assert d3["progress"]["celebrated"] is True

        # parent4 still not celebrated
        d4 = _compare(t4)
        assert d4["progress"]["all_agreed"] is True
        assert d4["progress"]["celebrated"] is False


def _pdf_text(content: bytes) -> str:
    out = []
    for stream in re.findall(rb"stream\n(.*?)\nendstream", content, re.S):
        try:
            out.append(zlib.decompress(stream).decode("latin-1", errors="ignore"))
        except Exception:
            pass
    return "\n".join(out)


class TestPdf:
    def test_pdf_with_agreements(self, _reseed_and_share):
        t3 = _reseed_and_share["t3"]
        # Ensure at least one is agreed with a note
        d = _compare(t3)
        area = _diff_key(d, 0)
        requests.post(f"{API}/court-path/compare/agree", json={"area": area, "agreed": True}, headers=_h(t3), timeout=20)
        requests.put(f"{API}/court-path/compare/agree/note",
                     json={"area": area, "note": "pdftest note"}, headers=_h(t3), timeout=20)
        r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(t3), timeout=30)
        assert r.status_code == 200
        text = _pdf_text(r.content)
        # progress line
        assert re.search(r"\d+ of \d+ differing areas marked agreed", text)
        # intent notice (allow for line breaks/kerning; check two chunks)
        assert "evidenced their intent" in text
        # multi_cell wraps the notice — look for key phrases that survive wrapping
        assert "binding agreement" in text or "not reflect" in text
        assert "Marked agreed by" in text
        assert "What we agreed:" in text
        assert "pdftest note" in text

    def test_pdf_without_agreements(self, _reseed_and_share):
        t3, t4 = _reseed_and_share["t3"], _reseed_and_share["t4"]
        # Undo all for both
        d = _compare(t3)
        for row in d["difference"]:
            for tok in (t3, t4):
                requests.post(f"{API}/court-path/compare/agree",
                              json={"area": row["key"], "agreed": False}, headers=_h(tok), timeout=20)
        r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(t3), timeout=30)
        assert r.status_code == 200
        text = _pdf_text(r.content)
        assert "Marked agreed by" not in text
        assert "evidenced their intent" not in text
