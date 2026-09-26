"""Iteration 66: Jev checks, Claude parallel summary, attachments, research config, TTS, ZIP profile."""
import io

import pytest

from casekit import new_case, new_user
from test_legal_report import API


@pytest.fixture(scope="module")
def ctx():
    pro, pa, pb, d = new_case(API)
    return pro, pa, pb, d["id"]


def test_claude_listed_in_ai_models(ctx) -> None:
    pro, _, _, rid = ctx
    r = pro.get(f"{API}/cases/{rid}/professional-report")
    assert r.status_code == 200
    assert {m["key"] for m in r.json()["library"]["ai_models"]} >= {"gemini", "openai", "claude"}


def test_neutrality_check_flags_custody_sentence(ctx) -> None:
    pro, _, _, rid = ctx
    r = pro.post(f"{API}/cases/{rid}/professional-report/neutrality-check", json={"fields": {"professional_summary": "Parent A reports difficulty obtaining timely responses. The father is clearly lying and should lose custody of the child."}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "professional_summary" in body["checked_fields"]
    assert any(f["issue"] in ("custody_recommendation", "credibility_judgment") for f in body["flags"])


def test_blame_check_categorizes_lines(ctx) -> None:
    pro = ctx[0]
    r = pro.post(f"{API}/foundation/mine/blame-check", json={"lines": ["My child needs calm transitions between homes.", "Her father never shows up on time and does not care about her."]})
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    assert res[0]["focus"] == "child_focused" and res[1]["focus"] == "blaming"


def test_parallel_summary_draft(ctx) -> None:
    pro, _, _, rid = ctx
    r = pro.post(f"{API}/cases/{rid}/parallel-summary-draft")
    assert r.status_code == 200, r.text
    assert r.json()["text"].lower().startswith("ai-assisted draft")
    assert "safety" in r.json()


def test_attachments_roundtrip_and_privacy(ctx) -> None:
    pro, pa, _, rid = ctx
    r = pa.post(f"{API}/foundation/mine/attachments", files={"file": ("note.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")})
    assert r.status_code == 200, r.text
    fid = r.json()["id"]
    assert fid in {f["id"] for f in pa.get(f"{API}/foundation/mine/attachments").json()["files"]}
    assert pa.get(f"{API}/files/{fid}").status_code == 200
    assert pro.get(f"{API}/files/{fid}").status_code == 403
    assert pro.get(f"{API}/files/{fid}?case={rid}").status_code == 403  # nothing shared into the case yet
    assert pa.post(f"{API}/foundation/mine/attachments", files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")}).status_code == 400
    assert pa.delete(f"{API}/foundation/mine/attachments/{fid}").status_code == 200
    assert pa.get(f"{API}/files/{fid}").status_code == 404


def test_research_config_and_zip(ctx) -> None:
    pro = ctx[0]
    assert pro.put(f"{API}/me/profile/zip", json={"zip": "78205"}).status_code == 200
    r = pro.get(f"{API}/research/config")
    assert r.status_code == 200 and r.json()["zip"] == "78205" and r.json()["categories"]
    assert pro.post(f"{API}/research/local-resources", json={"category": "dv_advocacy"}).status_code in (200, 503)


def test_tts_generates_and_serves_audio(ctx) -> None:
    pro = ctx[0]
    r = pro.post(f"{API}/tts", json={"text": "Welcome to SA CoParents Align."})
    assert r.status_code == 200, r.text
    a = pro.get(f"{API}{r.json()['url'].removeprefix('/api')}")
    assert a.status_code == 200 and a.headers["content-type"].startswith("audio/mpeg") and len(a.content) > 1000
