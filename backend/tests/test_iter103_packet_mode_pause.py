"""Iter-103 extra: packet-mode behavior when joint_paused — mode defaults to individual, joint request returns 423, GET professional-statement reflects packet.mode."""
import os
import sys

import pytest
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case  # noqa: E402

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"


@pytest.fixture(scope="module")
def flow():
    pro, _pa, _pb, d, _ = completed_case(API)
    return pro, d["id"]


def test_default_packet_mode_is_joint(flow):
    pro, rid = flow
    r = pro.get(f"{API}/joint/reports/{rid}/professional-statement")
    assert r.status_code == 200
    assert r.json()["packet"] == {"joint_paused": False, "mode": "joint"}


def test_pause_switches_mode_to_individual_and_blocks_joint(flow):
    pro, rid = flow
    r = pro.put(f"{API}/joint/reports/{rid}/joint-pause", json={"paused": True, "note": "test pause"})
    assert r.status_code == 200, r.text
    g = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()
    assert g["packet"]["joint_paused"] is not False and g["packet"]["mode"] == "individual", g["packet"]
    # resolve_packet_mode raises 423 for joint while paused (unit-level — court-referred case needed for live route)
    from fastapi import HTTPException
    from court_workflow import resolve_packet_mode
    with pytest.raises(HTTPException) as exc:
        resolve_packet_mode({"joint_paused": True}, "joint")
    assert exc.value.status_code == 423
    # Resume
    r = pro.put(f"{API}/joint/reports/{rid}/joint-pause", json={"paused": False, "note": ""})
    assert r.status_code == 200
    g = pro.get(f"{API}/joint/reports/{rid}/professional-statement").json()
    assert g["packet"]["joint_paused"] is False and g["packet"]["mode"] == "joint"


def test_invalid_packet_mode_rejected(flow):
    pro, rid = flow
    r = pro.post(f"{API}/joint/reports/{rid}/court-packet-preview", json={"packet_mode": "banana", "attest": True})
    assert r.status_code == 400
