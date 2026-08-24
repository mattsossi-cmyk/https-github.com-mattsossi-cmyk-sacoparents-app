"""FastAPI entrypoint for SA CoParents Relational Mediation Prep App."""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Response
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import router as auth_router  # noqa: E402
from mediation_routes import router as mediation_router  # noqa: E402
from analytics_routes import router as analytics_router  # noqa: E402
from journal_routes import router as journal_router  # noqa: E402
from mediator_routes import router as mediator_router  # noqa: E402
from email_webhook_routes import router as email_webhook_router  # noqa: E402
from survey_routes import router as survey_router, survey_scheduler_loop  # noqa: E402
from invite_routes import router as invite_router  # noqa: E402
from checkin_routes import checkin_scheduler_loop, router as checkin_router  # noqa: E402
from legal_routes import router as legal_router  # noqa: E402
from safety_assessment_routes import router as safety_assessment_router  # noqa: E402
from gmail_routes import router as gmail_router  # noqa: E402
from coparenting_routes import router as coparenting_router  # noqa: E402
from snc2_routes import router as snc2_router  # noqa: E402
from snc2_comparison_routes import router as snc2_compare_router  # noqa: E402
from edu_deep_routes import router as edu_deep_router  # noqa: E402
from edu_deep_comparison_routes import router as edu_deep_compare_router  # noqa: E402
from psych_deep_comparison_routes import router as psych_deep_compare_router  # noqa: E402
from med_deep_comparison_routes import router as med_deep_compare_router  # noqa: E402
from psych_deep_routes import router as psych_deep_router  # noqa: E402
from med_deep_routes import router as med_deep_router  # noqa: E402
from deep_dives_routes import router as deep_dives_router  # noqa: E402
from progress_dashboard_routes import router as progress_dashboard_router  # noqa: E402
from wall_routes import router as wall_router  # noqa: E402
from signature_verify_routes import router as signature_verify_router  # noqa: E402
from briefing_verify_routes import router as briefing_verify_router  # noqa: E402
from pathway_verify_routes import router as pathway_verify_router  # noqa: E402
from court_report_verify_routes import router as court_report_verify_router  # noqa: E402
from pathway_report_routes import router as pathway_report_router  # noqa: E402
from joint_professional_report_routes import router as joint_professional_report_router  # noqa: E402
from joint_agreement_routes import router as joint_agreement_router  # noqa: E402
from phi_access_routes import router as phi_access_router  # noqa: E402
from hb300_routes import router as hb300_router  # noqa: E402
from admin_nd_coordinator_routes import router as admin_nd_coordinator_router  # noqa: E402
from nd_risk_routes import router as nd_risk_router  # noqa: E402
from dimension_companion_routes import router as dimension_companion_router  # noqa: E402
from intervention_compliance_routes import router as intervention_compliance_router  # noqa: E402
from reviewer_panel_routes import router as reviewer_panel_router  # noqa: E402
from share_routes import router as share_router  # noqa: E402
from coach_routes import router as coach_router  # noqa: E402
from next_steps_routes import router as next_steps_router  # noqa: E402
from learning_routes import router as learning_router  # noqa: E402
from insights_routes import (  # noqa: E402
    router as insights_router,
    admin_briefing_scheduler_loop,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SA CoParents Mediation Prep API")

# Mongo — keep connection limits modest so production Atlas free-tier (max ~500
# concurrent conns) is never exhausted. maxPoolSize defaults to 100 per client
# which combined with multiple pod replicas can blow past Atlas limits.
mongo_client = AsyncIOMotorClient(
    os.environ["MONGO_URL"],
    maxPoolSize=20,
    minPoolSize=1,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    retryWrites=True,
)
app.state.db = mongo_client[os.environ["DB_NAME"]]

# Routers under /api
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "sa-coparents", "status": "ok"}


@api_router.get("/health")
async def health():
    """Lightweight liveness probe — must NOT touch the database so Kubernetes
    keeps the pod alive even during transient DB hiccups."""
    return {"status": "ok"}


@api_router.get("/ready")
async def ready(response: Response):
    """Readiness probe — runs a cheap Mongo ping with a tight timeout.
    Returns 503 if the pod cannot reach MongoDB so k8s removes it from
    the service endpoints and stops routing traffic to it. This is what
    prevents the 'one bad replica leaks 502s' production pattern."""
    if app.state.db is None:
        response.status_code = 503
        return {"status": "db-not-ready"}
    try:
        # 1.5s budget — fast enough to not block the probe, slow enough
        # to ride out transient blips without flapping.
        await asyncio.wait_for(app.state.db.command("ping"), timeout=1.5)
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        logger.warning("Readiness probe DB ping failed: %s", exc)
        response.status_code = 503
        return {"status": "db-unreachable"}
    return {"status": "ready"}


api_router.include_router(auth_router)
api_router.include_router(mediation_router)
api_router.include_router(analytics_router)
api_router.include_router(journal_router)
api_router.include_router(mediator_router)
api_router.include_router(email_webhook_router)
api_router.include_router(survey_router)
api_router.include_router(invite_router)
api_router.include_router(checkin_router)
api_router.include_router(legal_router)
api_router.include_router(safety_assessment_router)
api_router.include_router(gmail_router)
api_router.include_router(coparenting_router)
api_router.include_router(snc2_router)
api_router.include_router(snc2_compare_router)
api_router.include_router(edu_deep_router)
api_router.include_router(edu_deep_compare_router)
api_router.include_router(psych_deep_compare_router)
api_router.include_router(med_deep_compare_router)
api_router.include_router(psych_deep_router)
api_router.include_router(med_deep_router)
api_router.include_router(deep_dives_router)
api_router.include_router(progress_dashboard_router)
api_router.include_router(wall_router)
api_router.include_router(share_router)
api_router.include_router(insights_router)
api_router.include_router(coach_router)
api_router.include_router(next_steps_router)
api_router.include_router(learning_router)
api_router.include_router(signature_verify_router)
api_router.include_router(briefing_verify_router)
api_router.include_router(pathway_verify_router)
api_router.include_router(court_report_verify_router)
api_router.include_router(pathway_report_router)
api_router.include_router(joint_professional_report_router)
api_router.include_router(joint_agreement_router)
api_router.include_router(phi_access_router)
api_router.include_router(hb300_router)
api_router.include_router(admin_nd_coordinator_router)
api_router.include_router(nd_risk_router)
api_router.include_router(dimension_companion_router)
api_router.include_router(intervention_compliance_router)
api_router.include_router(reviewer_panel_router)
app.include_router(api_router)

# CORS — allow credentials for cookie-based auth.
#
# Browsers (per CORS spec) reject `Access-Control-Allow-Origin: *` when the
# request has credentials. Pairing a reflected/wildcard origin with
# `allow_credentials=True` also enables cross-site PHI theft — any site
# a signed-in parent visits could `fetch(..., {credentials:'include'})` our
# API and read the response. So: NEVER reflect wildcard origins alongside
# credentials. Require an explicit allowlist via CORS_ORIGINS.
cors_origins_raw = os.environ.get("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip() and o.strip() != "*"]
if not cors_origins:
    # Safe default — the production origin plus the current preview origin.
    # Adjust CORS_ORIGINS in the environment for additional trusted origins.
    cors_origins = [
        "https://sacoparentsapp.online",
        "https://www.sacoparentsapp.online",
    ]
    preview_origin = os.environ.get("REACT_APP_BACKEND_URL")
    if preview_origin and preview_origin not in cors_origins:
        cors_origins.append(preview_origin)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_log():
    logger.info("SA CoParents backend ready. DB=%s", os.environ.get("DB_NAME"))
    # Compare-snapshot dedupe: unique per (share_id, snapshot_key). Idempotent
    # if the index already exists.
    try:
        await app.state.db["deep_dive_compare_snapshots"].create_index(
            [("share_id", 1), ("snapshot_key", 1)],
            unique=True,
            name="share_snapshot_key_unique",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create deep_dive_compare_snapshots unique index")
    # Kick off the post-event survey scheduler. It sleeps internally so it
    # won't run before the DB is warm.
    asyncio.create_task(survey_scheduler_loop(app))
    asyncio.create_task(checkin_scheduler_loop(app))
    asyncio.create_task(admin_briefing_scheduler_loop(app))
    from weekly_compliance_reminder import weekly_compliance_reminder_loop
    asyncio.create_task(weekly_compliance_reminder_loop(app))
    from compare_invite_nudge import compare_invite_nudge_loop
    asyncio.create_task(compare_invite_nudge_loop(app))


@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
