"""iter222 backend tests: Coparent Snapshot PDF + Voice Transcribe + Draft Sync."""

import io
import math
import os
import struct
import wave

import pytest
import requests

from ai_ready import ai_headers

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
_AI = {}


def _ai():
    if not _AI:
        _AI.update(ai_headers(API))
    return _AI

TOPICS = ["foundation", "coparenting", "safety", "medical", "educational", "psychological"]


# ------------------------------ Fixtures ------------------------------ #
@pytest.fixture(scope="session")
def parent1_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": "parent1@test.com", "password": "TestPass123!"},
        timeout=15,
    )
    if r.status_code != 200:
        # Try register (idempotent-ish)
        requests.post(
            f"{API}/auth/register",
            json={"email": "parent1@test.com", "password": "TestPass123!", "name": "Sam Parent"},
            timeout=15,
        )
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "parent1@test.com", "password": "TestPass123!"},
            timeout=15,
        )
    assert r.status_code == 200, f"parent1 login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def parent2_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": "parent2@test.com", "password": "TestPass123!"},
        timeout=15,
    )
    if r.status_code != 200:
        requests.post(
            f"{API}/auth/register",
            json={"email": "parent2@test.com", "password": "TestPass123!", "name": "Riley Parent"},
            timeout=15,
        )
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "parent2@test.com", "password": "TestPass123!"},
            timeout=15,
        )
    assert r.status_code == 200, f"parent2 login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def _tiny_wav_bytes(seconds: float = 1.0, freq: int = 440, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(int(rate * seconds)):
            val = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / rate))
            w.writeframes(struct.pack("<h", val))
    return buf.getvalue()


# =============================================================== #
# Feature 1: /portal/guided-snapshot-pdf
# =============================================================== #
class TestGuidedSnapshotPdf:
    @pytest.mark.parametrize("topic", TOPICS)
    def test_valid_topic_returns_pdf(self, topic):
        payload = {
            "topic": topic,
            "answers": [
                {"question": "What matters most for your child?", "answer": "Stability and safety."},
                {"question": "How would you describe your co-parenting today?", "answer": "Improving."},
            ],
            "parent_name": "Sam Parent",
            "case_ref": "TEST_CASE_123",
        }
        r = requests.post(f"{API}/portal/guided-snapshot-pdf", json=payload, timeout=30)
        assert r.status_code == 200, f"{topic}: {r.status_code} {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd and f"coparent-snapshot-{topic}.pdf" in cd
        assert r.content[:4] == b"%PDF", f"{topic}: missing PDF magic bytes"

    def test_empty_answers_returns_stub_pdf(self):
        r = requests.post(
            f"{API}/portal/guided-snapshot-pdf",
            json={"topic": "foundation", "answers": []},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_invalid_topic_returns_422(self):
        r = requests.post(
            f"{API}/portal/guided-snapshot-pdf",
            json={"topic": "bogus_topic", "answers": []},
            timeout=15,
        )
        assert r.status_code == 422
        detail_str = str(r.json().get("detail", ""))
        assert "pattern" in detail_str.lower() or "string_pattern_mismatch" in detail_str.lower()

    def test_safety_flagged_meta_row(self):
        import re
        import zlib

        r = requests.post(
            f"{API}/portal/guided-snapshot-pdf",
            json={
                "topic": "safety",
                "answers": [{"question": "Q1", "answer": "A1"}],
                "safety_flagged": True,
            },
            timeout=15,
        )
        assert r.status_code == 200
        # PDF streams are FlateDecoded; decompress each and search decoded text.
        decoded = b""
        for m in re.finditer(rb"stream\r?\n(.+?)\r?\nendstream", r.content, re.DOTALL):
            try:
                decoded += zlib.decompress(m.group(1))
            except Exception:
                pass
        assert (b"Grey-rock" in decoded) or (b"safety flagged" in decoded), (
            "Grey-rock meta row missing when safety_flagged=true"
        )


# =============================================================== #
# Feature 2: /portal/voice-transcribe
# =============================================================== #
class TestVoiceTranscribe:
    def test_valid_wav_returns_text(self):
        wav = _tiny_wav_bytes()
        files = {"audio": ("voice.wav", wav, "audio/wav")}
        r = requests.post(f"{API}/portal/voice-transcribe", files=files, headers=_ai(), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert "text" in data
        assert isinstance(data["text"], str)

    def test_empty_payload_returns_400(self):
        files = {"audio": ("voice.wav", b"", "audio/wav")}
        r = requests.post(f"{API}/portal/voice-transcribe", files=files, headers=_ai(), timeout=15)
        assert r.status_code == 400
        assert "empty" in r.text.lower()

    def test_text_plain_content_type_returns_415(self):
        files = {"audio": ("note.txt", b"hello world", "text/plain")}
        r = requests.post(f"{API}/portal/voice-transcribe", files=files, headers=_ai(), timeout=15)
        assert r.status_code == 415

    def test_audio_webm_accepted(self):
        # We don't need valid webm bytes to prove content-type is accepted;
        # a valid content-type + non-empty bytes gets past the 415 guard.
        # Whisper may 502, but the accept check is what we're testing.
        files = {"audio": ("voice.webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 128, "audio/webm;codecs=opus")}
        r = requests.post(f"{API}/portal/voice-transcribe", files=files, headers=_ai(), timeout=30)
        assert r.status_code != 415, "audio/webm;codecs=opus should be accepted"

    def test_rate_limit_returns_429(self):
        # Shared bucket. Push past 40/hr from same IP → expect 429.
        # Wrong-type uploads still count against the quota but never reach Whisper.
        saw_429 = False
        for _ in range(50):
            files = {"audio": ("v.txt", b"x", "text/plain")}
            r = requests.post(f"{API}/portal/voice-transcribe", files=files, headers=_ai(), timeout=15)
            if r.status_code == 429:
                saw_429 = True
                break
        assert saw_429, "Expected 429 after 40+ rapid POSTs from same IP"


# =============================================================== #
# Feature 3: guided_drafts on /portal/state
# =============================================================== #
class TestGuidedDraftsSync:
    def test_put_filters_unknown_topics(self, parent1_token):
        payload = {
            "guided_drafts": {
                "foundation": {"answers": [{"q": "Q1", "a": "A1"}], "step": 1},
                "unknown_topic": {"blah": "should be filtered"},
            }
        }
        r = requests.put(f"{API}/portal/state", headers=_auth(parent1_token), json=payload, timeout=15)
        assert r.status_code == 200
        # Verify persistence
        g = requests.get(f"{API}/portal/state", headers=_auth(parent1_token), timeout=15)
        assert g.status_code == 200
        drafts = g.json().get("state", {}).get("guided_drafts") or {}
        assert "foundation" in drafts
        assert "unknown_topic" not in drafts

    def test_put_null_clears_drafts(self, parent1_token):
        # Seed one first
        requests.put(
            f"{API}/portal/state",
            headers=_auth(parent1_token),
            json={"guided_drafts": {"medical": {"answers": [{"q": "?", "a": "!"}]}}},
            timeout=15,
        )
        r = requests.put(
            f"{API}/portal/state",
            headers=_auth(parent1_token),
            json={"guided_drafts": None},
            timeout=15,
        )
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_auth(parent1_token), timeout=15)
        drafts = g.json().get("state", {}).get("guided_drafts")
        assert drafts is None or drafts == {} or drafts == None

    def test_per_topic_byte_cap_drops_massive(self, parent1_token):
        # Clear first
        requests.put(f"{API}/portal/state", headers=_auth(parent1_token), json={"guided_drafts": None}, timeout=15)
        huge = "x" * 20000  # 20KB > 12KB cap
        payload = {
            "guided_drafts": {
                "safety": {"answers": [{"q": "Q1", "a": huge}]},
                "foundation": {"answers": [{"q": "small", "a": "small"}]},
            }
        }
        r = requests.put(f"{API}/portal/state", headers=_auth(parent1_token), json=payload, timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_auth(parent1_token), timeout=15)
        drafts = g.json().get("state", {}).get("guided_drafts") or {}
        assert "safety" not in drafts, "Oversized safety draft should have been dropped"
        assert "foundation" in drafts

    def test_two_user_isolation(self, parent1_token, parent2_token):
        # Parent1 writes a marker
        marker = "PARENT1_SECRET_MARKER"
        requests.put(
            f"{API}/portal/state",
            headers=_auth(parent1_token),
            json={"guided_drafts": {"educational": {"answers": [{"q": "x", "a": marker}]}}},
            timeout=15,
        )
        # Parent2 GETs their own state
        g = requests.get(f"{API}/portal/state", headers=_auth(parent2_token), timeout=15)
        assert g.status_code == 200
        drafts2 = g.json().get("state", {}).get("guided_drafts") or {}
        as_text = str(drafts2)
        assert marker not in as_text, "Parent1's draft leaked to Parent2"


# =============================================================== #
# Regression: existing PDF endpoints + other portal endpoints
# =============================================================== #
class TestRegressionEndpoints:
    @pytest.mark.parametrize(
        "path,payload",
        [
            ("/portal/foundation-pdf", {"foundation_text": "Test foundation statement.", "parent_name": "Sam"}),
            ("/portal/legal-report-pdf", {"foundation_text": "F", "sigA": "Sam", "sigB": "Riley", "sigMed": "Med"}),
            ("/portal/weekly-progress-pdf", {"health_index": {"s1": 7, "s2": 6, "s3": 5}, "align_records": [], "milestones": []}),
            ("/portal/complete-report-pdf", {"foundation_text": "F", "align_records": [], "milestones": [], "biff_logs": [], "health_index": {"s1": 7, "s2": 6, "s3": 5}}),
        ],
    )
    def test_pdf_endpoints_still_200(self, path, payload):
        r = requests.post(f"{API}{path}", json=payload, timeout=30)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_biff_refine_200(self):
        from ai_ready import client_address
        # Own client address: the per-address AI quota is shared with the earlier tests in this file.
        r = requests.post(
            f"{API}/portal/biff-refine", headers={**_ai(), **client_address()},
            json={"raw": "You never respond on time and it makes me angry.", "safety_flagged": False},
            timeout=45,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        for k in ("biff", "flags", "risk"):
            assert k in data, f"missing key {k} in biff-refine response"

    def test_state_roundtrip_preserves_fields(self, parent1_token):
        payload = {
            "foundation_text": "Roundtrip test foundation.",
            "court_key": "TEST-CT-1",
            "health_index": {"s1": 8, "s2": 7, "s3": 6},
            "safety_ack": {"cleared": True, "flagged": False, "date": "2026-01-15"},
        }
        r = requests.put(f"{API}/portal/state", headers=_auth(parent1_token), json=payload, timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{API}/portal/state", headers=_auth(parent1_token), timeout=15)
        st = g.json().get("state", {})
        assert st.get("foundation_text") == "Roundtrip test foundation."
        assert st.get("court_key") == "TEST-CT-1"
        assert st.get("health_index", {}).get("s1") == 8
        # The in-app quick safety check is retired: a client can't write its result any more.
        assert (st.get("safety_ack") or {}).get("date") != "2026-01-15"
