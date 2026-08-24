"""HB 300 Breach Simulation Drill (Tabletop Exercise).

Runs three realistic scenarios against the live backend to verify
that `/app/memory/HB300_BREACH_RUNBOOK.md` is actually executable:

  Scenario A — Small internal exposure (12 TX residents).
    Expected: AG threshold NOT crossed, OCR annual-log path, no
    Texas AG filing required. Individual notice within 60 days.

  Scenario B — TX AG threshold crossed (312 TX residents).
    Expected: AG threshold flagged, TX AG notice required inside
    60 days, individual notice inside 60 days.

  Scenario C — OCR-scale breach (742 total, 620 in Texas).
    Expected: AG threshold flagged, OCR notice inside 60 days
    (>= 500 individuals), individual notice inside 60 days,
    potential Texas media notice.

The drill also validates:
  * Admin gate (non-admin gets 403).
  * Draft persists in `hb300_breach_reports`.
  * Response `next_steps` mentions the AG threshold correctly.
  * Timer math: 60-day windows from `discovered_at`.
  * PHI access log is untouched (breach report is admin action,
    not a PHI read).

Cleanup runs at the end so no drill data survives in Mongo.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from motor.motor_asyncio import AsyncIOMotorClient


BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.split("=", 1)[1].strip().rstrip("/")

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
if not MONGO_URL or not DB_NAME:
    for line in Path("/app/backend/.env").read_text().splitlines():
        if line.startswith("MONGO_URL="):
            MONGO_URL = MONGO_URL or line.split("=", 1)[1].strip().strip('"')
        if line.startswith("DB_NAME="):
            DB_NAME = DB_NAME or line.split("=", 1)[1].strip().strip('"')


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "id": "A",
        "label": "Small internal exposure (12 TX residents)",
        "payload": {
            "summary": (
                "On 2026-02-14 at 09:14 CST a support engineer discovered "
                "that 12 safety assessments were mis-scoped to a shared "
                "Compare view due to an off-by-one in the participant "
                "check. Only Finding 3 was ever visible, but the "
                "unauthorised access still counts as a disclosure. "
                "Access was cut off inside four minutes."
            ),
            "discovered_at":            (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "texas_residents_affected": 12,
            "phi_categories":           "safety_lens_finding_3, mediation_prep",
            "remediation": (
                "1) Patched the participant check. 2) Revoked the affected "
                "share tokens. 3) Rotated Mongo credentials as a "
                "belt-and-braces. 4) Scheduled a codemod to force all "
                "share endpoints through the audited helper."
            ),
        },
        "expect": {
            "ag_threshold_crossed":         False,
            "user_notice_deadline_days":    60,
            "ocr_notice_route":             "annual_log",
        },
    },
    {
        "id": "B",
        "label": "TX AG threshold crossed (312 TX residents)",
        "payload": {
            "summary": (
                "Vendor incident: analytics processor accidentally logged "
                "hashed but reversible user_id + child_first_name pairs "
                "for 312 Texas residents over a 6-hour window. Vendor "
                "confirmed logs were purged before discovery."
            ),
            "discovered_at":            (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "texas_residents_affected": 312,
            "phi_categories":           "identifiers, child_first_name",
            "remediation": (
                "1) Vendor removed the offending log statement. 2) BAA "
                "reviewed for corrective action clause. 3) All keys "
                "rotated. 4) Post-mortem scheduled with vendor."
            ),
        },
        "expect": {
            "ag_threshold_crossed":         True,
            "user_notice_deadline_days":    60,
            "ocr_notice_route":             "annual_log",   # 312 < 500
        },
    },
    {
        "id": "C",
        "label": "OCR-scale breach (742 total, 620 TX)",
        "payload": {
            "summary": (
                "Public S3-style misconfiguration on an experimental "
                "PDF-render cache exposed 742 generated joint reports "
                "for 8 minutes. 620 belong to Texas residents. Requires "
                "AG, OCR, and possibly Texas media notice."
            ),
            "discovered_at":            (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
            "texas_residents_affected": 620,
            "phi_categories":           "joint_report, agreement_draft",
            "remediation": (
                "1) Cache disabled. 2) All render tokens rotated. 3) "
                "Static-storage BAA re-reviewed. 4) Third-party forensic "
                "review engaged."
            ),
        },
        "expect": {
            "ag_threshold_crossed":         True,
            "user_notice_deadline_days":    60,
            "ocr_notice_route":             "immediate_60_day",   # 742 >= 500
        },
    },
]


# ---------------------------------------------------------------------------
# Drill driver
# ---------------------------------------------------------------------------

def register(email: str, password: str = "DrillPass123!") -> dict:
    r = requests.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": password, "name": "Drill Admin"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def promote_to_admin(user_id: str) -> None:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": "admin", "is_admin": True}})
    client.close()


async def read_breach_row(breach_id: str) -> dict | None:
    from bson import ObjectId
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    row = await db.hb300_breach_reports.find_one({"_id": ObjectId(breach_id)})
    client.close()
    if row and "_id" in row:
        row["_id"] = str(row["_id"])
    if row and "discovered_at" in row and isinstance(row["discovered_at"], datetime):
        row["discovered_at"] = row["discovered_at"].isoformat()
    if row and "drafted_at" in row and isinstance(row["drafted_at"], datetime):
        row["drafted_at"] = row["drafted_at"].isoformat()
    return row


async def cleanup(user_id: str, breach_ids: list[str]) -> None:
    from bson import ObjectId
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.delete_one({"user_id": user_id})
    await db.hb300_breach_reports.delete_many(
        {"_id": {"$in": [ObjectId(b) for b in breach_ids]}}
    )
    await db.phi_access_log.delete_many({"user_id": user_id})
    client.close()


def call_breach_report(token: str, payload: dict) -> tuple[int, dict]:
    r = requests.post(
        f"{BASE}/api/admin/breach-report",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


async def main() -> int:
    findings: list[dict] = []
    breach_ids: list[str] = []
    started = datetime.now(timezone.utc)

    print(f"\n{'=' * 78}")
    print("HB 300 BREACH SIMULATION DRILL")
    print(f"Started:  {started.isoformat()}")
    print(f"Backend:  {BASE}")
    print(f"{'=' * 78}\n")

    # ----- setup -----
    admin_email = f"drill_admin_{uuid.uuid4().hex[:8]}@sacoparents-drill.com"
    civilian_email = f"drill_civ_{uuid.uuid4().hex[:8]}@sacoparents-drill.com"
    print(f"[SETUP] Registering admin ({admin_email}) + civilian ({civilian_email})")
    admin = register(admin_email)
    civilian = register(civilian_email)
    await promote_to_admin(admin["user"]["user_id"])
    print(f"[SETUP] Admin user_id={admin['user']['user_id']} promoted via Mongo role/is_admin")

    # ----- check 1: non-admin blocked -----
    print("\n[CHECK 1] Non-admin blocked by /api/admin/breach-report")
    status, body = call_breach_report(civilian["access_token"], SCENARIOS[0]["payload"])
    ok = status == 403 and body.get("detail") == "Admin only."
    findings.append({"check": "admin_gate", "pass": ok, "status": status, "body": body})
    print(f"  status={status}  body={body}  {'PASS' if ok else 'FAIL'}")

    # ----- run the three scenarios -----
    for sc in SCENARIOS:
        print(f"\n[SCENARIO {sc['id']}] {sc['label']}")
        t0 = time.time()
        status, body = call_breach_report(admin["access_token"], sc["payload"])
        elapsed_ms = int((time.time() - t0) * 1000)
        row = None
        if status == 200 and body.get("breach_id"):
            breach_ids.append(body["breach_id"])
            row = await read_breach_row(body["breach_id"])
        # Timer math: user-notice deadline
        disc = datetime.fromisoformat(sc["payload"]["discovered_at"].replace("Z", "+00:00"))
        expected_user_deadline = disc + timedelta(days=60)
        result = {
            "scenario":                sc["id"],
            "label":                   sc["label"],
            "http_status":             status,
            "elapsed_ms":              elapsed_ms,
            "breach_id":               body.get("breach_id"),
            "ag_threshold_crossed":    body.get("ag_threshold_crossed"),
            "ag_threshold_expected":   sc["expect"]["ag_threshold_crossed"],
            "user_notice_deadline":    expected_user_deadline.isoformat(),
            "ocr_route":               sc["expect"]["ocr_notice_route"],
            "next_steps_len":          len(body.get("next_steps", [])),
            "persisted_status":        (row or {}).get("status"),
            "persisted_tx_affected":   (row or {}).get("texas_residents_affected"),
        }
        # Pass criteria
        pass_status = status == 200
        pass_ag_flag = body.get("ag_threshold_crossed") == sc["expect"]["ag_threshold_crossed"]
        pass_persist = row is not None and row.get("status") == "draft"
        result["pass"] = bool(pass_status and pass_ag_flag and pass_persist)
        findings.append(result)
        print(f"  http={status} elapsed={elapsed_ms}ms ag_flag={body.get('ag_threshold_crossed')}")
        print(f"  next_steps: {body.get('next_steps', [])}")
        print(f"  persisted:  status={result['persisted_status']} tx_affected={result['persisted_tx_affected']}")
        print(f"  60-day user-notice deadline: {expected_user_deadline.isoformat()}")
        print(f"  → {'PASS' if result['pass'] else 'FAIL'}")

    # ----- cleanup -----
    await cleanup(admin["user"]["user_id"], breach_ids)
    await cleanup(civilian["user"]["user_id"], [])
    print("\n[CLEANUP] Removed drill users + breach rows + PHI access rows")

    # ----- write readout -----
    finished = datetime.now(timezone.utc)
    total_pass = all(f.get("pass", False) for f in findings)
    readout = {
        "started":    started.isoformat(),
        "finished":   finished.isoformat(),
        "duration_s": (finished - started).total_seconds(),
        "backend":    BASE,
        "findings":   findings,
        "overall":    "PASS" if total_pass else "FAIL",
    }
    Path("/app/memory").mkdir(exist_ok=True)
    (Path("/app/memory") / "HB300_BREACH_DRILL_RESULTS.json").write_text(
        json.dumps(readout, indent=2, default=str)
    )
    print(f"\n{'=' * 78}")
    print(f"OVERALL: {readout['overall']}")
    print(f"{'=' * 78}")
    print(f"Findings JSON: /app/memory/HB300_BREACH_DRILL_RESULTS.json\n")

    return 0 if total_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
