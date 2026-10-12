"""Iter-103: profile contact (bar/license/title) endpoint, individual topic summaries, packet-mode payload, signature upload."""
import io
import os

import fitz
import pytest
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from casekit import completed_case  # noqa: E402
from pdf_individual import build_individual_reports_pdf  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"


def _text(b: bytes) -> str:
    with fitz.open(stream=b, filetype="pdf") as d:
        return " ".join("\n".join(p.get_text() for p in d).split())


def _png() -> bytes:
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\xff\xff\xff\xff" * 4 for _ in range(4))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


@pytest.fixture(scope="module")
def flow():
    pro, _pa, _pb, d, _ = completed_case(API)
    return pro, d["id"]


def test_profile_contact_bar_license_title_fill_cover(flow):
    pro, rid = flow
    r = pro.put(f"{API}/me/profile/contact", json={"pro_role": "Attorney-Mediator", "bar_number": "TX 2401", "license_number": "LIC-9", "phone": "210-555-0199", "city": "San Antonio", "state": "TX", "zip": "78205"})
    assert r.status_code == 200, r.text
    g = pro.get(f"{API}/me/profile/contact").json()
    assert (g["bar_number"], g["license_number"], g["pro_role"]) == ("TX 2401", "LIC-9", "Attorney-Mediator")
    v = pro.get(f"{API}/cases/{rid}/professional-report").json()["professional"]
    assert (v["bar_number"], v["license_number"], v["title"]) == ("TX 2401", "LIC-9", "Attorney-Mediator")


def test_signature_upload_and_fetch(flow):
    pro, _ = flow
    r = pro.post(f"{API}/me/profile/image/signature", files={"file": ("sig.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    assert pro.get(f"{API}/me/profile/image/signature").status_code == 200
    assert pro.get(f"{API}/me/profile/contact").json()["images"]["signature"] is True


def test_individual_summaries_roundtrip_and_pdf(flow):
    pro, rid = flow
    g = pro.get(f"{API}/joint/reports/{rid}/individual-summaries").json()
    assert [t["key"] for t in g["topics"]][:2] == ["needs_most", "working_well"]
    bad = pro.put(f"{API}/joint/reports/{rid}/individual-summaries", json={"a": {"needs_most": "Parent A should be awarded custody"}})
    assert bad.status_code == 400
    r = pro.put(f"{API}/joint/reports/{rid}/individual-summaries", json={"a": {"needs_most": "Emphasis on a predictable school-week routine.", "bogus": "x"}, "b": {"concerns": "  Focus on   handoff timing. "}})
    assert r.status_code == 200, r.text
    s = r.json()["summaries"]
    assert s == {"a": {"needs_most": "Emphasis on a predictable school-week routine."}, "b": {"concerns": "Focus on handoff timing."}}
    doc = {"id": rid, "case_code": "X", "participants": {"a": {"name": "Pat"}, "b": {"name": "Sam"}}, "responses": {"a": {"answers": {"needs_most": "RAW"}}, "b": {"answers": {}}},
           "individual_summaries": s, "professional_statement": {"observations": "ok"}}
    t = _text(build_individual_reports_pdf(doc, {"name": "Pro"}))
    assert "Child's Primary Need: Emphasis on a predictable school-week routine." in t and "Concerns: Focus on handoff timing." in t
    assert "RAW" not in t and "Not provided" in t
    assert pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()["packet"] == {"joint_paused": False, "mode": "joint"}
