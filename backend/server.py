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
from privacy_consent_routes import router as privacy_consent_router  # noqa: E402
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
from report_deliveries import router as report_deliveries_router  # noqa: E402
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
from integration_routes import router as integration_router  # noqa: E402
from professionals_routes import router as professionals_router  # noqa: E402
from joint_alignment_routes import router as joint_alignment_router  # noqa: E402
from communication_alignment_routes import router as communication_alignment_router  # noqa: E402
from parenting_schedule_alignment_routes import router as parenting_schedule_alignment_router  # noqa: E402
from activities_alignment_routes import router as activities_alignment_router  # noqa: E402
from activities_costs_routes import router as activities_costs_router  # noqa: E402
from parent_professional_invitations import router as parent_professional_invitations_router  # noqa: E402
from complete_alignment_report_routes import router as complete_alignment_report_router  # noqa: E402
from admin_maintenance_routes import router as admin_maintenance_router  # noqa: E402
from nudge_copy_routes import router as nudge_copy_router  # noqa: E402
from alignment_reflection_routes import router as alignment_reflection_router  # noqa: E402
from alignment_reflection_analytics import router as alignment_reflection_analytics_router  # noqa: E402
from professional_bundle_templates import router as professional_bundle_templates_router  # noqa: E402
from bundle_routes import router as bundle_router  # noqa: E402
from coach_demo_routes import router as coach_demo_router  # noqa: E402
from portal_routes import router as portal_router  # noqa: E402
from grey_rock_audit import router as grey_rock_audit_router  # noqa: E402
from self_assessment_routes import router as self_assessment_router  # noqa: E402
from self_assessment_ai import router as self_assessment_ai_router  # noqa: E402
from court_path_ai import router as court_path_ai_router  # noqa: E402
from court_checklist import router as court_checklist_router  # noqa: E402
from court_codes_routes import router as court_codes_router  # noqa: E402
from completion_summary_routes import router as completion_summary_router  # noqa: E402
from progress_pdf import router as progress_pdf_router  # noqa: E402
from professional_nudges import router as professional_nudges_router  # noqa: E402
from professional_digest import router as professional_digest_router  # noqa: E402
from court_compare import router as court_compare_router  # noqa: E402
from parallel_parenting_routes import router as parallel_parenting_router  # noqa: E402
from child_needs_routes import router as child_needs_router  # noqa: E402
from child_needs_share_routes import router as child_needs_share_router  # noqa: E402
from journey_certificate_routes import router as journey_certificate_router  # noqa: E402
from secure_doc_routes import router as secure_doc_router  # noqa: E402
from journey_summary_routes import router as journey_summary_router  # noqa: E402
from journey_guide_routes import router as journey_guide_router  # noqa: E402
from foundation_builder_routes import router as foundation_builder_router  # noqa: E402
from cron_routes import router as cron_router  # noqa: E402
from release_check_routes import router as release_check_router  # noqa: E402
from self_journey_weekly_routes import router as self_journey_weekly_router  # noqa: E402
from self_journey_weekly_routes import admin_router as self_journey_weekly_admin_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SA CoParents Mediation Prep API")


# Kubernetes deployment probes hit the pod on the un-prefixed URLs
# `/health` and `/ready`. Those requests never go through the ingress
# path-rewrite, so the same endpoints ALSO have to live at the FastAPI
# root — separate from the `/api/health` and `/api/ready` routes below
# which are what the frontend and internal callers use.
@app.get("/health", include_in_schema=False)
async def root_health():
    """Liveness probe (root path, for k8s). Never touches the DB."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def root_ready(response: Response):
    """Readiness probe (root path, for k8s). Runs a cheap Mongo ping
    with a tight timeout; returns 503 on failure so the pod is pulled
    from the service endpoints."""
    try:
        await asyncio.wait_for(
            app.state.db.command("ping"), timeout=1.5,
        )
        return {"status": "ready"}
    except Exception:  # noqa: BLE001
        response.status_code = 503
        return {"status": "not_ready"}

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
api_router.include_router(privacy_consent_router)
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
api_router.include_router(report_deliveries_router)
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
api_router.include_router(integration_router)
api_router.include_router(professionals_router)
api_router.include_router(joint_alignment_router)
api_router.include_router(communication_alignment_router)
api_router.include_router(parenting_schedule_alignment_router)
api_router.include_router(activities_alignment_router)
api_router.include_router(activities_costs_router)
api_router.include_router(parent_professional_invitations_router)
api_router.include_router(complete_alignment_report_router)
api_router.include_router(admin_maintenance_router)
api_router.include_router(nudge_copy_router)
api_router.include_router(alignment_reflection_router)
api_router.include_router(alignment_reflection_analytics_router)
api_router.include_router(professional_bundle_templates_router)
api_router.include_router(bundle_router)
api_router.include_router(coach_demo_router)
api_router.include_router(portal_router)
api_router.include_router(grey_rock_audit_router)
api_router.include_router(self_assessment_ai_router)
api_router.include_router(court_path_ai_router)
api_router.include_router(court_checklist_router)
api_router.include_router(court_codes_router)
api_router.include_router(progress_pdf_router)
api_router.include_router(completion_summary_router)
api_router.include_router(professional_nudges_router)
api_router.include_router(professional_digest_router)
api_router.include_router(court_compare_router)
api_router.include_router(parallel_parenting_router)
api_router.include_router(self_assessment_router)
api_router.include_router(child_needs_router)
api_router.include_router(child_needs_share_router)
api_router.include_router(journey_certificate_router)
api_router.include_router(secure_doc_router)
api_router.include_router(journey_summary_router)
api_router.include_router(journey_guide_router)
api_router.include_router(foundation_builder_router)
api_router.include_router(cron_router)
api_router.include_router(release_check_router)
api_router.include_router(self_journey_weekly_router)
api_router.include_router(self_journey_weekly_admin_router)
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
    preview_origin = (
        os.environ.get("PUBLIC_APP_URL")
        or os.environ.get("PUBLIC_API_URL")
        or os.environ.get("REACT_APP_BACKEND_URL")
    )
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
    # Contract sanity: every duration advertised by the joint-artefact
    # share-link dialogs MUST be in `auth.SHARE_TOKEN_WINDOWS`. If not,
    # `create_share_token` silently downgrades to the 7-day default and
    # parents get a shorter link than they were promised (iter128).
    try:
        from auth import SHARE_TOKEN_WINDOWS
        from joint_agreement_routes import _SHARE_LINK_EXPIRE_CHOICES as _jae
        from joint_professional_report_routes import (
            _REPORT_LINK_EXPIRE_CHOICES as _jre,
        )
        drift = (_jae | _jre) - SHARE_TOKEN_WINDOWS
        if drift:
            logger.error(
                "Share-link duration drift: routes offer %s but "
                "auth.SHARE_TOKEN_WINDOWS is missing these values. "
                "Tokens minted with those durations will silently "
                "downgrade. Add them to SHARE_TOKEN_WINDOWS.", drift,
            )
    except Exception:  # noqa: BLE001 - never block boot on a diag check
        logger.exception("Failed to verify share-link duration contract")
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
    # Child medical/educational/psychological records are switched off: purge any saved copies.
    try:
        res = await app.state.db["portal_state"].update_many(
            {"align_records.0": {"$exists": True}}, {"$set": {"align_records": []}}
        )
        if res.modified_count:
            logger.info("Purged child alignment records from %d accounts", res.modified_count)
        res = await app.state.db["portal_pdf_shares"].update_many(
            {"payload.align_records": {"$exists": True}}, {"$unset": {"payload.align_records": ""}}
        )
        if res.modified_count:
            logger.info("Purged child alignment records from %d share links", res.modified_count)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to purge child alignment records")
    try:
        from portal_routes import purge_sample_history
        n = await purge_sample_history(app.state.db)
        if n:
            logger.info("Removed built-in sample history from %d saved documents", n)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to purge sample history")
    try:
        from integration_routes import migrate_verified_links
        n = await migrate_verified_links(app.state.db)
        if n:
            logger.info("Recorded %d existing Align links", n)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to record existing Align links")
    # Kick off the post-event survey scheduler. It sleeps internally so it
    # won't run before the DB is warm.
    asyncio.create_task(survey_scheduler_loop(app))
    asyncio.create_task(checkin_scheduler_loop(app))
    asyncio.create_task(admin_briefing_scheduler_loop(app))
    from weekly_compliance_reminder import weekly_compliance_reminder_loop
    asyncio.create_task(weekly_compliance_reminder_loop(app))
    from compare_invite_nudge import compare_invite_nudge_loop
    asyncio.create_task(compare_invite_nudge_loop(app))
    from silent_reviewer_nudge import silent_reviewer_nudge_loop
    asyncio.create_task(silent_reviewer_nudge_loop(app))
    from joint_alignment_invite_nudge import joint_alignment_invite_nudge_loop
    asyncio.create_task(joint_alignment_invite_nudge_loop(app))
    from weekly_case_analytics_email import weekly_case_analytics_loop
    asyncio.create_task(weekly_case_analytics_loop(app))
    from parent_share_digest import parent_share_digest_loop
    asyncio.create_task(parent_share_digest_loop(app))
    from access_expiring_sweep import access_expiring_sweep_loop
    asyncio.create_task(access_expiring_sweep_loop(app))
    from consent_adoption_digest import consent_adoption_digest_loop
    asyncio.create_task(consent_adoption_digest_loop(app))
    from alignment_reflection_reminder import alignment_reflection_reminder_loop
    asyncio.create_task(alignment_reflection_reminder_loop(app))
    from case_completion_nudge import case_completion_nudge_loop
    asyncio.create_task(case_completion_nudge_loop(app))
    from release_check import post_boot_release_check
    asyncio.create_task(post_boot_release_check(app))

    # Seed the two demo court keys for SacoparentsPortal (Door 2 flow).
    # Idempotent — only inserts on first boot; subsequent boots are no-ops.
    try:
        from portal_routes import seed_court_keys
        await seed_court_keys(app.state.db)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to seed portal court keys")


@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
